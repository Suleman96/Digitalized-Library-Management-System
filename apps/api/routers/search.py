# =============================================================================
# routers/search.py — discovery endpoints
# =============================================================================

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from ..core.config import settings
from ..core.rag_pipeline import PipelineTrace as CoreTrace
from ..core.recommender import book_id, clean_year, to_https
from ..deps import Engine, get_engine
from ..schemas import (
    Book,
    ExplainRequest,
    ExplainResponse,
    PipelineTrace,
    SearchRequest,
    SearchResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["search"])

_SCOPE_TO_LEGACY = {"both": "Both", "local": "Local Only", "external": "External Only"}
_SORT_TO_LEGACY  = {"similarity": "Similarity", "rating": "Rating", "year": "Year"}


def _empty_trace(query: str) -> PipelineTrace:
    return PipelineTrace(originalQuery=query, stages=[], totalMs=0.0)


def _finalise(books: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Books coming straight off HybridRetriever read from the metadata pickle and
    never pass through _normalise(), so they carry no id and their year is still
    a raw float string.  Fix both here.
    """
    for b in books:
        if not b.get("id"):
            b["id"] = book_id(str(b.get("title", "")), str(b.get("authors", "")))
        b["published_year"] = clean_year(b.get("published_year"))
        # Covers come out of the pickle as http:// URLs. Google Books refuses
        # those from a browser, so the card would show an empty box.
        if b.get("thumbnail"):
            b["thumbnail"] = to_https(str(b["thumbnail"]))
    return books


def _filter_candidates(
    candidates: list[dict[str, Any]],
    *,
    language: str,
    category: str,
    min_rating: float,
) -> list[dict[str, Any]]:
    """
    Apply language / category / rating filters.

    Each filter falls back to the unfiltered set when it would return nothing —
    an empty result page is worse than a slightly looser match, which is the
    behaviour v2 had and users expect.
    """
    lang_code = settings.languages.get(language, "")
    if lang_code:
        candidates = [b for b in candidates if b.get("language", "") in ("", lang_code)]

    if category and category != "Any":
        matched = [
            b for b in candidates
            if category in [c.strip() for c in str(b.get("categories", "")).split(",")]
        ]
        candidates = matched or candidates

    if min_rating > 0:
        rated = [b for b in candidates if float(b.get("average_rating", 0) or 0) >= min_rating]
        candidates = rated or candidates

    return candidates


@router.post("/search", response_model=SearchResponse)
def search(req: SearchRequest, engine: Engine = Depends(get_engine)) -> SearchResponse:
    """
    Run a discovery search.

    Local results go through the hybrid retriever by default (BM25 + FAISS +
    knowledge graph, no LLM required).  When any RAG toggle is on and an LLM is
    connected, the full pipeline runs instead and returns a populated trace.
    """
    if not engine.ready:
        raise HTTPException(503, "Retrieval engine is still starting. Try again shortly.")

    query = req.query.strip()
    if not query:
        raise HTTPException(422, "Query cannot be empty.")

    llm_on = engine.llm.is_enabled

    # ── Optional AI query expansion ───────────────────────────────────────
    effective_query = query
    expanded: str | None = None
    if req.useAiExpansion and llm_on:
        effective_query = engine.llm.expand_query(query) or query
        if effective_query != query:
            expanded = effective_query
            logger.info("Query expanded: %r -> %r", query, effective_query)

    # ── External sources (Google Books + OpenLibrary) ─────────────────────
    external: list[dict[str, Any]] = []
    if req.scope in ("both", "external") and req.externalLimit > 0:
        try:
            _, external = engine.recommender.recommend(
                effective_query, req.language, 0, req.externalLimit,
                req.minRating, "External Only", _SORT_TO_LEGACY[req.sortBy],
            )
        except Exception as exc:
            # An external API outage must not fail the whole search.
            logger.warning("External search failed: %s", exc)
            external = []

    # ── Local retrieval ───────────────────────────────────────────────────
    local: list[dict[str, Any]] = []
    trace = _empty_trace(query)

    wants_rag = req.useHyde or req.useMultiQuery or req.useRerank
    if req.scope in ("both", "local") and req.localLimit > 0:
        if wants_rag and llm_on and engine.pipeline.is_ready:
            results, core_trace = engine.pipeline.search(
                effective_query,
                k=req.localLimit,
                use_hyde=req.useHyde,
                use_multi_query=req.useMultiQuery,
                use_rerank=req.useRerank,
            )
            local = _filter_candidates(
                results, language=req.language, category=req.category, min_rating=req.minRating
            )[: req.localLimit]
            trace = PipelineTrace(**core_trace.to_dict())

        elif engine.retriever.is_ready:
            import time
            t0 = time.perf_counter()
            candidates = engine.retriever.search(effective_query, k=req.localLimit * 4)
            elapsed = (time.perf_counter() - t0) * 1000
            local = _filter_candidates(
                candidates, language=req.language, category=req.category, min_rating=req.minRating
            )[: req.localLimit]
            trace = PipelineTrace(
                originalQuery=query,
                stages=[{
                    "name": "hybrid_retrieve",
                    "candidates": len(candidates),
                    "durationMs": round(elapsed, 1),
                    "detail": "BM25 + FAISS + knowledge graph (no LLM stages requested)",
                    "topShift": None,
                }],
                totalMs=round(elapsed, 1),
            )
        else:
            local, _ = engine.recommender.recommend(
                effective_query, req.language, req.localLimit, 0,
                req.minRating, "Local Only", _SORT_TO_LEGACY[req.sortBy],
            )

    _finalise(local)
    _finalise(external)

    return SearchResponse(
        local=[Book(**b) for b in local],
        external=[Book(**b) for b in external],
        trace=trace,
        expandedQuery=expanded,
    )


@router.post("/explain", response_model=ExplainResponse)
def explain(req: ExplainRequest, engine: Engine = Depends(get_engine)) -> ExplainResponse:
    """Ask the connected LLM why a given book matches the query."""
    if not engine.llm.is_enabled:
        raise HTTPException(409, "No AI provider connected. Connect one via /api/llm/connect.")

    matches = engine.retriever.search(req.query, k=40)
    _finalise(matches)
    book = next((b for b in matches if b.get("id") == req.bookId), None)
    if book is None:
        raise HTTPException(404, "Book not found in the current result set.")

    explanation = engine.llm.explain_match(req.query, book)
    if not explanation:
        raise HTTPException(502, "The provider returned no explanation. Try again.")

    return ExplainResponse(
        explanation=explanation,
        provider=engine.llm._provider or None,
        model=engine.llm._model or None,
    )
