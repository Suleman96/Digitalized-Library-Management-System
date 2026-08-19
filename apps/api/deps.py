# =============================================================================
# deps.py — Iqra Digital Library v3
# =============================================================================
# Engine lifecycle and dependency injection.
#
# v2 built every singleton at module scope in app.py, which meant importing the
# module paid a ~15 s model load — impossible to unit-test and impossible to
# import from a worker.  v3 builds them once inside FastAPI's lifespan and
# hands them out through Depends().
# =============================================================================

from __future__ import annotations

import logging
import os
import threading
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

VERSION = "3.0.0"


@dataclass
class Engine:
    """Every long-lived object the routers need."""

    manager:      Any = None
    recommender:  Any = None
    reading_list: Any = None
    retriever:    Any = None
    pipeline:     Any = None
    llm:          Any = None
    agent:        Any = None
    ready:        bool = False
    error:        str | None = None


_engine = Engine()
_build_lock = threading.Lock()


def build_engine() -> Engine:
    """
    Construct the retrieval engine.  Called once from the FastAPI lifespan.

    Ordering matters: the recommender loads all-MiniLM-L6-v2, and the retriever
    reuses that same loaded model via `embed_fn` rather than loading a second
    copy (which is what v2's startup did, costing ~2 s and ~90 MB).
    """
    global _engine
    with _build_lock:
        if _engine.ready:
            return _engine

        from .core.manager import DynamicBookManager
        from .core.recommender import BookRecommender
        from .core.reading_list import ReadingList
        from .core.hybrid_retriever import HybridRetriever
        from .core.rag_pipeline import RAGPipeline
        from .core.llm_provider import llm
        from .core.agent import LibraryAgent

        try:
            logger.info("Engine: building catalogue manager…")
            manager = DynamicBookManager()

            logger.info("Engine: loading embedding model…")
            recommender = BookRecommender()

            reading_list = ReadingList()

            logger.info("Engine: building hybrid retriever (BM25 + FAISS + graph)…")
            retriever = HybridRetriever()
            retriever.build(embed_fn=recommender._embed)

            pipeline = RAGPipeline(retriever, llm)
            agent = LibraryAgent(retriever, recommender, reading_list, llm)

            _engine = Engine(
                manager=manager,
                recommender=recommender,
                reading_list=reading_list,
                retriever=retriever,
                pipeline=pipeline,
                llm=llm,
                agent=agent,
                ready=True,
            )
            logger.info("Engine: ready — %d books indexed.", manager.book_count)

            _auto_connect_llm(_engine)

        except Exception as exc:  # pragma: no cover - startup failure path
            logger.exception("Engine: build failed")
            _engine = Engine(ready=False, error=str(exc))

        return _engine


def _auto_connect_llm(engine: Engine) -> None:
    """Connect an LLM at boot when LLM_PROVIDER / LLM_MODEL are set."""
    provider = os.getenv("LLM_PROVIDER", "").strip().lower()
    model = os.getenv("LLM_MODEL", "").strip()
    if not (provider and model):
        return

    status = engine.llm.configure(provider, model)
    logger.info("Engine: auto-connect LLM — %s", status)
    if engine.llm.is_enabled:
        engine.agent.build()
        logger.info("Engine: agent built.")


def get_engine() -> Engine:
    """FastAPI dependency. Returns the built engine."""
    if not _engine.ready:
        build_engine()
    return _engine
