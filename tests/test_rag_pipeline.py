# =============================================================================
# tests/test_rag_pipeline.py — Iqra Digital Library v2
# =============================================================================
# Unit tests for RAGPipeline (HyDE, multi-query, cross-encoder re-ranking).
# All tests use mocked retriever and LLM — no network access, no real models.
# =============================================================================

from __future__ import annotations

from unittest.mock import MagicMock

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fake_book(title: str, score: float = 0.5) -> dict:
    return {
        "title":          title,
        "authors":        "Test Author",
        "description":    f"A book about {title}",
        "average_rating": 4.0,
        "published_year": "2020",
        "thumbnail":      "",
        "info_link":      "#",
        "source":         "📚 Local Library (Hybrid)",
        "similarity":     score,
        "ratings_count":  100,
        "num_pages":      300,
        "language":       "en",
    }


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_retriever():
    ret = MagicMock()
    ret.is_ready = True
    ret._metadata = [_fake_book(f"Book {i}") for i in range(10)]
    ret.search.return_value = [
        _fake_book(f"Book {i}", score=round(0.9 - i * 0.1, 1))
        for i in range(5)
    ]
    return ret


@pytest.fixture
def mock_llm_off():
    llm = MagicMock()
    llm.is_enabled = False
    return llm


@pytest.fixture
def mock_llm_on():
    llm = MagicMock()
    llm.is_enabled = True
    llm.generate_hypothetical_doc.return_value = (
        "A gripping mystery set in an ancient library full of secrets."
    )
    llm.generate_query_variants.return_value = [
        "crime thriller novels",
        "detective mystery books",
        "suspense fiction",
    ]
    return llm


# ---------------------------------------------------------------------------
# Basic pipeline
# ---------------------------------------------------------------------------

class TestRAGPipelineBasic:
    def test_returns_empty_when_retriever_not_ready(self, mock_llm_off):
        from apps.api.core.rag_pipeline import RAGPipeline
        ret = MagicMock()
        ret.is_ready = False
        pipeline = RAGPipeline(ret, mock_llm_off)
        results, trace = pipeline.search("anything")
        assert results == []
        assert trace.total_ms >= 0

    def test_passthrough_when_all_flags_off(self, mock_retriever, mock_llm_off):
        from apps.api.core.rag_pipeline import RAGPipeline
        pipeline = RAGPipeline(mock_retriever, mock_llm_off)
        results, _ = pipeline.search("mystery books", k=5)
        assert isinstance(results, list)
        assert mock_retriever.search.call_count == 1

    def test_is_ready_delegates_to_retriever(self, mock_retriever, mock_llm_off):
        from apps.api.core.rag_pipeline import RAGPipeline
        pipeline = RAGPipeline(mock_retriever, mock_llm_off)
        assert pipeline.is_ready is True

    def test_is_ready_false_when_retriever_not_ready(self, mock_llm_off):
        from apps.api.core.rag_pipeline import RAGPipeline
        ret = MagicMock()
        ret.is_ready = False
        pipeline = RAGPipeline(ret, mock_llm_off)
        assert pipeline.is_ready is False

    def test_respects_k_limit(self, mock_retriever, mock_llm_off):
        from apps.api.core.rag_pipeline import RAGPipeline
        mock_retriever.search.return_value = [_fake_book(f"Book {i}") for i in range(20)]
        pipeline = RAGPipeline(mock_retriever, mock_llm_off)
        results, _ = pipeline.search("query", k=3)
        assert len(results) <= 3

    def test_search_returns_list_of_dicts(self, mock_retriever, mock_llm_off):
        from apps.api.core.rag_pipeline import RAGPipeline
        pipeline = RAGPipeline(mock_retriever, mock_llm_off)
        results, _ = pipeline.search("query", k=5)
        assert all(isinstance(r, dict) for r in results)

    def test_empty_query_does_not_crash(self, mock_retriever, mock_llm_off):
        from apps.api.core.rag_pipeline import RAGPipeline
        pipeline = RAGPipeline(mock_retriever, mock_llm_off)
        results, _ = pipeline.search("", k=5)
        assert isinstance(results, list)


# ---------------------------------------------------------------------------
# HyDE
# ---------------------------------------------------------------------------

class TestHyDE:
    def test_hyde_adds_extra_search(self, mock_retriever, mock_llm_on):
        from apps.api.core.rag_pipeline import RAGPipeline
        pipeline = RAGPipeline(mock_retriever, mock_llm_on)
        pipeline.search("mystery", k=5, use_hyde=True)
        # original query + HyDE doc = 2 search calls
        assert mock_retriever.search.call_count == 2

    def test_hyde_skipped_when_llm_off(self, mock_retriever, mock_llm_off):
        from apps.api.core.rag_pipeline import RAGPipeline
        pipeline = RAGPipeline(mock_retriever, mock_llm_off)
        pipeline.search("mystery", k=5, use_hyde=True)
        assert mock_retriever.search.call_count == 1

    def test_hyde_skipped_when_hypothetical_doc_empty(self, mock_retriever, mock_llm_on):
        from apps.api.core.rag_pipeline import RAGPipeline
        mock_llm_on.generate_hypothetical_doc.return_value = ""
        pipeline = RAGPipeline(mock_retriever, mock_llm_on)
        pipeline.search("mystery", k=5, use_hyde=True)
        assert mock_retriever.search.call_count == 1

    def test_hyde_skipped_when_doc_same_as_query(self, mock_retriever, mock_llm_on):
        from apps.api.core.rag_pipeline import RAGPipeline
        mock_llm_on.generate_hypothetical_doc.return_value = "mystery"
        pipeline = RAGPipeline(mock_retriever, mock_llm_on)
        pipeline.search("mystery", k=5, use_hyde=True)
        assert mock_retriever.search.call_count == 1


# ---------------------------------------------------------------------------
# Multi-query
# ---------------------------------------------------------------------------

class TestMultiQuery:
    def test_multi_query_makes_extra_searches(self, mock_retriever, mock_llm_on):
        from apps.api.core.rag_pipeline import RAGPipeline
        pipeline = RAGPipeline(mock_retriever, mock_llm_on)
        pipeline.search("mystery", k=5, use_multi_query=True)
        # original + 3 variants = 4 calls
        assert mock_retriever.search.call_count == 4

    def test_multi_query_skipped_when_llm_off(self, mock_retriever, mock_llm_off):
        from apps.api.core.rag_pipeline import RAGPipeline
        pipeline = RAGPipeline(mock_retriever, mock_llm_off)
        pipeline.search("mystery", k=5, use_multi_query=True)
        assert mock_retriever.search.call_count == 1

    def test_multi_query_deduplicates_queries(self, mock_retriever, mock_llm_on):
        from apps.api.core.rag_pipeline import RAGPipeline
        # one variant duplicates the original
        mock_llm_on.generate_query_variants.return_value = [
            "mystery",        # duplicate of original
            "detective",
            "thriller",
        ]
        pipeline = RAGPipeline(mock_retriever, mock_llm_on)
        pipeline.search("mystery", k=5, use_multi_query=True)
        # 1 original + 2 unique variants = 3 calls
        assert mock_retriever.search.call_count == 3

    def test_multi_query_skipped_when_variants_empty(self, mock_retriever, mock_llm_on):
        from apps.api.core.rag_pipeline import RAGPipeline
        mock_llm_on.generate_query_variants.return_value = []
        pipeline = RAGPipeline(mock_retriever, mock_llm_on)
        pipeline.search("mystery", k=5, use_multi_query=True)
        assert mock_retriever.search.call_count == 1


# ---------------------------------------------------------------------------
# RRF merge
# ---------------------------------------------------------------------------

class TestRRFMerge:
    def test_rrf_deduplicates_titles(self, mock_retriever, mock_llm_off):
        from apps.api.core.rag_pipeline import RAGPipeline
        pipeline = RAGPipeline(mock_retriever, mock_llm_off)
        list1 = [_fake_book("A"), _fake_book("B"), _fake_book("C")]
        list2 = [_fake_book("B"), _fake_book("D"), _fake_book("A")]
        merged = pipeline._rrf_merge([list1, list2], k=10)
        titles = [r["title"] for r in merged]
        assert len(titles) == len(set(titles))

    def test_rrf_boosts_titles_appearing_in_multiple_lists(self, mock_retriever, mock_llm_off):
        from apps.api.core.rag_pipeline import RAGPipeline
        pipeline = RAGPipeline(mock_retriever, mock_llm_off)
        # "Shared" tops both lists — should rank first
        list1 = [_fake_book("Shared"), _fake_book("Only1")]
        list2 = [_fake_book("Shared"), _fake_book("Only2")]
        merged = pipeline._rrf_merge([list1, list2], k=10)
        assert merged[0]["title"] == "Shared"

    def test_rrf_single_list_passthrough(self, mock_retriever, mock_llm_off):
        from apps.api.core.rag_pipeline import RAGPipeline
        pipeline = RAGPipeline(mock_retriever, mock_llm_off)
        books = [_fake_book("X"), _fake_book("Y")]
        merged = pipeline._rrf_merge([books], k=10)
        assert [r["title"] for r in merged] == ["X", "Y"]

    def test_rrf_respects_k(self, mock_retriever, mock_llm_off):
        from apps.api.core.rag_pipeline import RAGPipeline
        pipeline = RAGPipeline(mock_retriever, mock_llm_off)
        list1 = [_fake_book(f"Book {i}") for i in range(10)]
        merged = pipeline._rrf_merge([list1], k=3)
        assert len(merged) <= 3


# ---------------------------------------------------------------------------
# Re-ranking
# ---------------------------------------------------------------------------

class TestReranking:
    def test_rerank_reorders_by_ce_score(self, mock_retriever, mock_llm_off):
        from apps.api.core.rag_pipeline import RAGPipeline
        pipeline = RAGPipeline(mock_retriever, mock_llm_off)
        mock_ce = MagicMock()
        n = 5
        # ascending scores — last book gets highest ce score
        mock_ce.predict.return_value = list(range(n))
        pipeline._reranker = mock_ce
        pipeline._reranker_tried = True
        results, _ = pipeline.search("query", k=n, use_rerank=True)
        scores = [r["similarity"] for r in results]
        assert scores == sorted(scores, reverse=True)

    def test_rerank_updates_similarity_to_ce_score(self, mock_retriever, mock_llm_off):
        from apps.api.core.rag_pipeline import RAGPipeline
        pipeline = RAGPipeline(mock_retriever, mock_llm_off)
        mock_ce = MagicMock()
        mock_ce.predict.return_value = [0.95, 0.80, 0.70, 0.60, 0.50]
        pipeline._reranker = mock_ce
        pipeline._reranker_tried = True
        results, _ = pipeline.search("query", k=5, use_rerank=True)
        assert results[0]["similarity"] == pytest.approx(0.95, abs=0.01)

    def test_rerank_gracefully_skips_on_error(self, mock_retriever, mock_llm_off):
        from apps.api.core.rag_pipeline import RAGPipeline
        pipeline = RAGPipeline(mock_retriever, mock_llm_off)
        mock_ce = MagicMock()
        mock_ce.predict.side_effect = RuntimeError("model error")
        pipeline._reranker = mock_ce
        pipeline._reranker_tried = True
        results, _ = pipeline.search("query", k=5, use_rerank=True)
        assert isinstance(results, list)

    def test_rerank_skipped_when_no_results(self, mock_retriever, mock_llm_off):
        from apps.api.core.rag_pipeline import RAGPipeline
        mock_retriever.search.return_value = []
        pipeline = RAGPipeline(mock_retriever, mock_llm_off)
        mock_ce = MagicMock()
        pipeline._reranker = mock_ce
        pipeline._reranker_tried = True
        pipeline.search("query", k=5, use_rerank=True)
        mock_ce.predict.assert_not_called()


# ---------------------------------------------------------------------------
# Combined flags
# ---------------------------------------------------------------------------

class TestCombinedFlags:
    def test_all_flags_on_with_llm(self, mock_retriever, mock_llm_on):
        from apps.api.core.rag_pipeline import RAGPipeline
        pipeline = RAGPipeline(mock_retriever, mock_llm_on)
        mock_ce = MagicMock()
        mock_ce.predict.return_value = [0.9] * 5
        pipeline._reranker = mock_ce
        pipeline._reranker_tried = True
        results, _ = pipeline.search(
            "mystery books", k=5,
            use_hyde=True, use_multi_query=True, use_rerank=True,
        )
        # 1 original + 3 multi-query variants + 1 HyDE = 5 retriever calls
        assert mock_retriever.search.call_count == 5
        assert isinstance(results, list)

    def test_all_flags_on_llm_off_behaves_as_plain_search(self, mock_retriever, mock_llm_off):
        from apps.api.core.rag_pipeline import RAGPipeline
        pipeline = RAGPipeline(mock_retriever, mock_llm_off)
        mock_ce = MagicMock()
        pipeline._reranker = mock_ce
        pipeline._reranker_tried = True
        pipeline.search(
            "mystery books", k=5,
            use_hyde=True, use_multi_query=True, use_rerank=True,
        )
        # LLM off → no expansion; re-ranker still applies if results exist
        assert mock_retriever.search.call_count == 1


# =============================================================================
# Pipeline trace — v3
# =============================================================================
class TestPipelineTrace:
    """The trace is what the frontend renders to make the RAG work visible."""

    def test_trace_records_hybrid_stage(self, mock_retriever, mock_llm_off):
        from apps.api.core.rag_pipeline import RAGPipeline
        pipeline = RAGPipeline(mock_retriever, mock_llm_off)
        _, trace = pipeline.search("mystery books", k=5)
        assert "hybrid_retrieve" in [st.name for st in trace.stages]

    def test_trace_reports_total_duration(self, mock_retriever, mock_llm_off):
        from apps.api.core.rag_pipeline import RAGPipeline
        pipeline = RAGPipeline(mock_retriever, mock_llm_off)
        _, trace = pipeline.search("mystery books", k=5)
        assert trace.total_ms >= 0.0
        assert trace.original_query == "mystery books"

    def test_trace_captures_hyde_document(self, mock_retriever, mock_llm_on):
        from apps.api.core.rag_pipeline import RAGPipeline
        pipeline = RAGPipeline(mock_retriever, mock_llm_on)
        _, trace = pipeline.search("mystery", k=5, use_hyde=True)
        assert trace.hyde_document
        assert "hyde" in [st.name for st in trace.stages]

    def test_trace_captures_query_variants(self, mock_retriever, mock_llm_on):
        from apps.api.core.rag_pipeline import RAGPipeline
        pipeline = RAGPipeline(mock_retriever, mock_llm_on)
        _, trace = pipeline.search("mystery", k=5, use_multi_query=True)
        assert len(trace.query_variants) == 3
        assert "multi_query" in [st.name for st in trace.stages]

    def test_trace_records_rrf_when_multiple_lists(self, mock_retriever, mock_llm_on):
        from apps.api.core.rag_pipeline import RAGPipeline
        pipeline = RAGPipeline(mock_retriever, mock_llm_on)
        _, trace = pipeline.search("mystery", k=5, use_multi_query=True)
        assert "rrf" in [st.name for st in trace.stages]

    def test_trace_serialises_to_camel_case(self, mock_retriever, mock_llm_off):
        """to_dict() feeds the API response directly, so keys must be camelCase."""
        from apps.api.core.rag_pipeline import RAGPipeline
        pipeline = RAGPipeline(mock_retriever, mock_llm_off)
        _, trace = pipeline.search("mystery books", k=5)
        payload = trace.to_dict()
        assert set(payload) >= {
            "originalQuery", "hydeDocument", "queryVariants", "stages", "totalMs"
        }
        for stage in payload["stages"]:
            assert set(stage) == {"name", "candidates", "durationMs", "detail", "topShift"}
