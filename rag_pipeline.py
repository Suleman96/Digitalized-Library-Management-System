# =============================================================================
# rag_pipeline.py — Iqra Digital Library v2
# =============================================================================
# Advanced RAG pipeline wrapping HybridRetriever with three optional passes:
#
#   1. HyDE          (pre-retrieval)  — embed a hypothetical ideal document
#   2. Multi-query   (pre-retrieval)  — run N query variants, RRF-merge results
#   3. Cross-encoder (post-retrieval) — re-rank top-k with a cross-encoder model
#
# Each pass is independently toggled so the app can expose granular UI controls.
# All three degrade gracefully: if the LLM is off or a package is missing, the
# pipeline falls back to plain hybrid search without raising.
# =============================================================================

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

_RRF_K = 60  # higher = gentler rank weighting across lists


class RAGPipeline:
    """
    Orchestrates HybridRetriever with optional HyDE, multi-query, and re-ranking.

    Parameters
    ----------
    retriever    : HybridRetriever (already built)
    llm_provider : LLMProvider singleton
    """

    def __init__(self, retriever: Any, llm_provider: Any) -> None:
        self._ret = retriever
        self._llm = llm_provider
        self._reranker: Any = None
        self._reranker_tried = False

    # ── Lazy cross-encoder loader ─────────────────────────────────────────
    def _get_reranker(self) -> Any | None:
        if self._reranker_tried:
            return self._reranker
        self._reranker_tried = True
        try:
            from sentence_transformers import CrossEncoder
            self._reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
            logger.info("RAGPipeline: cross-encoder loaded.")
        except Exception as exc:
            logger.warning("RAGPipeline: cross-encoder unavailable — %s", exc)
        return self._reranker

    # ── Reciprocal Rank Fusion ────────────────────────────────────────────
    def _rrf_merge(self, result_lists: list[list[dict]], k: int) -> list[dict]:
        """Merge multiple ranked result lists using Reciprocal Rank Fusion."""
        rrf_scores: dict[str, float] = {}
        book_by_title: dict[str, dict] = {}
        for ranked in result_lists:
            for rank, book in enumerate(ranked):
                title = book["title"]
                rrf_scores[title] = rrf_scores.get(title, 0.0) + 1.0 / (rank + 1 + _RRF_K)
                book_by_title[title] = book
        sorted_titles = sorted(rrf_scores, key=rrf_scores.__getitem__, reverse=True)
        out = []
        for title in sorted_titles[:k]:
            b = book_by_title[title].copy()
            b["similarity"] = round(rrf_scores[title], 6)
            out.append(b)
        return out

    # ── Main search ───────────────────────────────────────────────────────
    def search(
        self,
        query: str,
        k: int = 10,
        *,
        use_hyde: bool = False,
        use_multi_query: bool = False,
        use_rerank: bool = False,
    ) -> list[dict[str, Any]]:
        """
        Run the advanced RAG pipeline.

        Falls back gracefully at every stage when the LLM is off or a package
        is missing — the caller always receives a list (possibly empty).
        """
        if not self._ret.is_ready:
            return []

        llm_on  = self._llm.is_enabled
        fetch_k = min(k * 4, len(self._ret._metadata))

        # ── Stage 1: build query set ──────────────────────────────────────
        queries: list[str] = [query]

        if use_multi_query and llm_on:
            variants = self._llm.generate_query_variants(query)
            seen: dict[str, None] = {query: None}
            for v in variants:
                if v and v not in seen:
                    queries.append(v)
                    seen[v] = None
            logger.debug("RAGPipeline: %d query variants generated", len(queries) - 1)

        if use_hyde and llm_on:
            hypo = self._llm.generate_hypothetical_doc(query)
            if hypo and hypo not in queries:
                queries.append(hypo)
                logger.debug("RAGPipeline: HyDE doc added (%d chars)", len(hypo))

        # ── Stage 2: retrieve ─────────────────────────────────────────────
        result_lists = [self._ret.search(q, k=fetch_k) for q in queries]

        if len(result_lists) == 1:
            results = result_lists[0]
        else:
            results = self._rrf_merge(result_lists, k=fetch_k)

        # ── Stage 3: cross-encoder re-rank ────────────────────────────────
        if use_rerank and results:
            reranker = self._get_reranker()
            if reranker is not None:
                try:
                    pairs = [
                        (query, f"{r['title']} {r.get('description', '')[:300]}")
                        for r in results
                    ]
                    ce_scores = reranker.predict(pairs)
                    scored = sorted(zip(ce_scores, results), key=lambda x: x[0], reverse=True)
                    results = []
                    for ce_score, book in scored[:k]:
                        b = book.copy()
                        b["similarity"] = round(float(ce_score), 4)
                        results.append(b)
                except Exception as exc:
                    logger.warning("RAGPipeline: re-ranking failed, using hybrid order — %s", exc)
                    results = results[:k]
            else:
                results = results[:k]
        else:
            results = results[:k]

        logger.debug(
            "RAGPipeline '%s' → %d results  hyde=%s multi=%s rerank=%s",
            query, len(results), use_hyde, use_multi_query, use_rerank,
        )
        return results

    @property
    def is_ready(self) -> bool:
        return self._ret.is_ready
