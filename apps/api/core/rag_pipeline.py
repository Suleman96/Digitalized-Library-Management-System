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
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

_RRF_K = 60  # higher = gentler rank weighting across lists


# ---------------------------------------------------------------------------
# Trace objects — surfaced to the API so the frontend can show what actually
# ran.  Without these the pipeline's work is invisible: a user sees a ranked
# list and has no evidence that HyDE fired, that three variants were fused by
# RRF, or that a cross-encoder reordered the result set.
# ---------------------------------------------------------------------------
@dataclass
class StageTrace:
    name:        str            # bm25+faiss | rrf | rerank
    candidates:  int
    duration_ms: float
    detail:      str = ""
    top_shift:   int | None = None   # positions the top result moved


@dataclass
class PipelineTrace:
    original_query: str
    hyde_document:  str | None = None
    query_variants: list[str] = field(default_factory=list)
    stages:         list[StageTrace] = field(default_factory=list)
    total_ms:       float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "originalQuery": self.original_query,
            "hydeDocument":  self.hyde_document,
            "queryVariants": self.query_variants,
            "stages": [
                {
                    "name":       st.name,
                    "candidates": st.candidates,
                    "durationMs": round(st.duration_ms, 1),
                    "detail":     st.detail,
                    "topShift":   st.top_shift,
                }
                for st in self.stages
            ],
            "totalMs": round(self.total_ms, 1),
        }




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
    ) -> tuple[list[dict[str, Any]], PipelineTrace]:
        """
        Run the advanced RAG pipeline.

        Returns
        -------
        (results, trace)
            `results` is a ranked list of book dicts (possibly empty).
            `trace` records which stages ran, how many candidates each saw,
            and how long each took — this is what the UI renders.

        Falls back gracefully at every stage when the LLM is off or a package
        is missing; the caller always receives a list.
        """
        t0 = time.perf_counter()
        trace = PipelineTrace(original_query=query)

        if not self._ret.is_ready:
            trace.total_ms = (time.perf_counter() - t0) * 1000
            return [], trace

        llm_on  = self._llm.is_enabled
        fetch_k = min(k * 4, len(self._ret._metadata))

        # ── Stage 1: build query set ──────────────────────────────────────
        queries: list[str] = [query]

        if use_multi_query and llm_on:
            t = time.perf_counter()
            variants = self._llm.generate_query_variants(query)
            seen: dict[str, None] = {query: None}
            for v in variants:
                if v and v not in seen:
                    queries.append(v)
                    seen[v] = None
            trace.query_variants = queries[1:]
            trace.stages.append(StageTrace(
                name="multi_query",
                candidates=len(queries) - 1,
                duration_ms=(time.perf_counter() - t) * 1000,
                detail=f"{len(queries) - 1} variants generated by the LLM",
            ))
            logger.debug("RAGPipeline: %d query variants generated", len(queries) - 1)

        if use_hyde and llm_on:
            t = time.perf_counter()
            hypo = self._llm.generate_hypothetical_doc(query)
            if hypo and hypo not in queries:
                queries.append(hypo)
                trace.hyde_document = hypo
                trace.stages.append(StageTrace(
                    name="hyde",
                    candidates=1,
                    duration_ms=(time.perf_counter() - t) * 1000,
                    detail=f"hypothetical document ({len(hypo)} chars) embedded as a query vector",
                ))
                logger.debug("RAGPipeline: HyDE doc added (%d chars)", len(hypo))

        # ── Stage 2: retrieve ─────────────────────────────────────────────
        t = time.perf_counter()
        result_lists = [self._ret.search(q, k=fetch_k) for q in queries]
        retrieve_ms  = (time.perf_counter() - t) * 1000
        trace.stages.append(StageTrace(
            name="hybrid_retrieve",
            candidates=sum(len(r) for r in result_lists),
            duration_ms=retrieve_ms,
            detail=f"BM25 + FAISS + knowledge graph over {len(queries)} quer"
                   f"{'y' if len(queries) == 1 else 'ies'}",
        ))

        if len(result_lists) == 1:
            results = result_lists[0]
        else:
            t = time.perf_counter()
            results = self._rrf_merge(result_lists, k=fetch_k)
            trace.stages.append(StageTrace(
                name="rrf",
                candidates=len(results),
                duration_ms=(time.perf_counter() - t) * 1000,
                detail=f"Reciprocal Rank Fusion merged {len(result_lists)} "
                       f"result lists (k={_RRF_K})",
            ))

        # ── Stage 3: cross-encoder re-rank ────────────────────────────────
        if use_rerank and results:
            reranker = self._get_reranker()
            if reranker is not None:
                t = time.perf_counter()
                pre_rerank_top = results[0].get("title") if results else None
                try:
                    pairs = [
                        (query, f"{r['title']} {r.get('description', '')[:300]}")
                        for r in results
                    ]
                    ce_scores = reranker.predict(pairs)
                    scored = sorted(zip(ce_scores, results), key=lambda x: x[0], reverse=True)
                    reranked: list[dict[str, Any]] = []
                    for ce_score, book in scored[:k]:
                        b = book.copy()
                        b["similarity"] = round(float(ce_score), 4)
                        reranked.append(b)

                    # How far did the previous #1 fall?
                    top_shift = None
                    if pre_rerank_top is not None:
                        for new_pos, b in enumerate(reranked):
                            if b.get("title") == pre_rerank_top:
                                top_shift = new_pos
                                break

                    trace.stages.append(StageTrace(
                        name="rerank",
                        candidates=len(pairs),
                        duration_ms=(time.perf_counter() - t) * 1000,
                        detail="cross-encoder/ms-marco-MiniLM-L-6-v2 scored "
                               f"{len(pairs)} (query, book) pairs jointly",
                        top_shift=top_shift,
                    ))
                    results = reranked
                except Exception as exc:
                    logger.warning("RAGPipeline: re-ranking failed, using hybrid order — %s", exc)
                    trace.stages.append(StageTrace(
                        name="rerank",
                        candidates=0,
                        duration_ms=(time.perf_counter() - t) * 1000,
                        detail=f"skipped — {exc}",
                    ))
                    results = results[:k]
            else:
                results = results[:k]
        else:
            results = results[:k]

        trace.total_ms = (time.perf_counter() - t0) * 1000
        logger.debug(
            "RAGPipeline '%s' → %d results in %.0fms  hyde=%s multi=%s rerank=%s",
            query, len(results), trace.total_ms, use_hyde, use_multi_query, use_rerank,
        )
        return results, trace

    @property
    def is_ready(self) -> bool:
        return self._ret.is_ready
