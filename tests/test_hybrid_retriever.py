# =============================================================================
# tests/test_hybrid_retriever.py — Iqra Digital Library v2
# =============================================================================
# Unit tests for HybridRetriever (BM25 + FAISS, no LangChain dependency).
# All tests run without network access and without touching the real library.
# =============================================================================

from __future__ import annotations

import pickle
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock, patch

import faiss as raw_faiss
import numpy as np
import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _make_mock_metadata(n: int = 5) -> list[dict]:
    return [
        {
            "title":          f"Book {i}",
            "authors":        f"Author {i}",
            "description":    f"Description about topic {i} with keywords",
            "average_rating": round(3.0 + i * 0.2, 1),
            "published_year": str(2000 + i),
            "thumbnail":      "",
            "info_link":      "#",
            "ratings_count":  i * 10,
            "num_pages":      200 + i * 10,
            "language":       "en",
        }
        for i in range(n)
    ]


def _make_faiss_index(n: int = 5, dim: int = 384) -> Any:
    index = raw_faiss.IndexFlatIP(dim)
    vecs = np.random.randn(n, dim).astype(np.float32)
    norms = np.linalg.norm(vecs, axis=1, keepdims=True)
    index.add(vecs / norms)
    return index


def _dummy_embed(texts: list[str]) -> np.ndarray:
    """Fast deterministic embedder for tests — returns unit vectors."""
    dim = 384
    embs = np.ones((len(texts), dim), dtype=np.float32) / np.sqrt(dim)
    return embs


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def built_retriever(tmp_path: Path):
    """A fully-built HybridRetriever wired to a temp directory."""
    n = 5
    meta = _make_mock_metadata(n)
    index = _make_faiss_index(n)

    index_path = tmp_path / "book_index.faiss"
    meta_path  = tmp_path / "books_metadata.pkl"
    raw_faiss.write_index(index, str(index_path))
    with open(meta_path, "wb") as fh:
        pickle.dump(meta, fh)

    fake_settings = SimpleNamespace(
        index_path=index_path,
        meta_path=meta_path,
        # The knowledge-graph cache writes here; without it build() raises.
        artifact_dir=tmp_path,
    )

    with patch("apps.api.core.hybrid_retriever.settings", fake_settings):
        from apps.api.core.hybrid_retriever import HybridRetriever
        hr = HybridRetriever()
        hr.build(embed_fn=_dummy_embed)
        yield hr


# ---------------------------------------------------------------------------
# Test: graceful degradation
# ---------------------------------------------------------------------------
class TestHybridRetrieverDegradation:
    def test_build_missing_files_does_not_raise(self):
        """build() must silently skip when index/metadata are absent."""
        with patch("apps.api.core.hybrid_retriever.settings") as mock_settings:
            mock_settings.index_path = Path("/nonexistent/index.faiss")
            mock_settings.meta_path  = Path("/nonexistent/meta.pkl")

            from apps.api.core.hybrid_retriever import HybridRetriever
            hr = HybridRetriever()
            hr.build()  # should not raise

            assert not hr.is_ready

    def test_search_before_build_returns_empty(self):
        """search() must return [] if build() was never called."""
        from apps.api.core.hybrid_retriever import HybridRetriever
        hr = HybridRetriever()
        assert hr.search("fantasy novels") == []

    def test_reload_does_not_raise_on_missing_files(self):
        """reload() wraps build() — must tolerate missing files."""
        with patch("apps.api.core.hybrid_retriever.settings") as mock_settings:
            mock_settings.index_path = Path("/nonexistent/index.faiss")
            mock_settings.meta_path  = Path("/nonexistent/meta.pkl")

            from apps.api.core.hybrid_retriever import HybridRetriever
            hr = HybridRetriever()
            hr.reload()  # should not raise


# ---------------------------------------------------------------------------
# Test: build and is_ready
# ---------------------------------------------------------------------------
class TestBuildAndReady:
    def test_is_ready_false_before_build(self):
        from apps.api.core.hybrid_retriever import HybridRetriever
        hr = HybridRetriever()
        assert hr.is_ready is False

    def test_is_ready_true_after_build(self, built_retriever):
        assert built_retriever.is_ready is True

    def test_is_ready_false_after_reload_with_missing_files(self, built_retriever):
        with patch("apps.api.core.hybrid_retriever.settings") as mock_settings:
            mock_settings.index_path = Path("/no/such/path.faiss")
            mock_settings.meta_path  = Path("/no/such/path.pkl")
            built_retriever.reload()
        assert built_retriever.is_ready is False


# ---------------------------------------------------------------------------
# Test: _make_docs (internal metadata → docstore)
# ---------------------------------------------------------------------------
class TestLoadMetadata:
    def test_load_metadata_from_pickle(self, tmp_path: Path):
        meta = _make_mock_metadata(3)
        pkl_path = tmp_path / "meta.pkl"
        with open(pkl_path, "wb") as fh:
            pickle.dump(meta, fh)

        with patch("apps.api.core.hybrid_retriever.settings") as mock_settings:
            mock_settings.meta_path  = pkl_path
            mock_settings.index_path = tmp_path / "nonexistent.faiss"

            from apps.api.core.hybrid_retriever import HybridRetriever
            hr     = HybridRetriever()
            loaded = hr._load_metadata()

        assert len(loaded) == 3
        assert loaded[0]["title"] == "Book 0"

    def test_load_metadata_returns_empty_when_file_missing(self, tmp_path: Path):
        with patch("apps.api.core.hybrid_retriever.settings") as mock_settings:
            mock_settings.meta_path  = tmp_path / "missing.pkl"
            mock_settings.index_path = tmp_path / "missing.faiss"

            from apps.api.core.hybrid_retriever import HybridRetriever
            hr = HybridRetriever()
            assert hr._load_metadata() == []


# ---------------------------------------------------------------------------
# Test: search result schema and behaviour
# ---------------------------------------------------------------------------
class TestSearch:
    _REQUIRED_KEYS = {
        "title", "authors", "description", "average_rating",
        "published_year", "thumbnail", "info_link", "source",
        "similarity", "ratings_count", "num_pages", "language",
    }

    def test_search_returns_list(self, built_retriever):
        results = built_retriever.search("Book 0 topic keywords")
        assert isinstance(results, list)

    def test_search_result_has_required_keys(self, built_retriever):
        results = built_retriever.search("Book topic")
        assert results, "Expected at least one result"
        missing = self._REQUIRED_KEYS - results[0].keys()
        assert not missing, f"Missing keys: {missing}"

    def test_search_source_is_hybrid(self, built_retriever):
        results = built_retriever.search("Book topic")
        for r in results:
            assert "Hybrid" in r["source"] or "Local" in r["source"]

    def test_search_respects_k_limit(self, built_retriever):
        results = built_retriever.search("topic", k=2)
        assert len(results) <= 2

    def test_search_deduplicates_titles(self, built_retriever):
        results = built_retriever.search("topic", k=10)
        titles = [r["title"] for r in results]
        assert len(titles) == len(set(titles)), "Duplicate titles found"

    def test_search_similarity_scores_in_range(self, built_retriever):
        results = built_retriever.search("topic", k=5)
        for r in results:
            assert 0.0 <= r["similarity"] <= 1.0, f"Score out of range: {r['similarity']}"

    def test_search_empty_query_does_not_crash(self, built_retriever):
        results = built_retriever.search("")
        assert isinstance(results, list)


# ---------------------------------------------------------------------------
# Test: BM25 normalisation
# ---------------------------------------------------------------------------
class TestMinMaxNorm:
    def test_all_zeros_returns_zeros(self):
        from apps.api.core.hybrid_retriever import HybridRetriever
        arr = np.zeros(5, dtype=np.float32)
        out = HybridRetriever._minmax_norm(arr)
        assert np.allclose(out, 0.0)

    def test_uniform_scores_normalise_to_zero(self):
        from apps.api.core.hybrid_retriever import HybridRetriever
        arr = np.ones(5, dtype=np.float32) * 3.7
        out = HybridRetriever._minmax_norm(arr)
        assert np.allclose(out, 0.0)

    def test_known_range(self):
        from apps.api.core.hybrid_retriever import HybridRetriever
        arr = np.array([0.0, 5.0, 10.0], dtype=np.float32)
        out = HybridRetriever._minmax_norm(arr)
        assert np.allclose(out, [0.0, 0.5, 1.0])
