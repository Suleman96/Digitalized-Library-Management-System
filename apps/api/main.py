# =============================================================================
# main.py — Iqra Digital Library v3 API
# =============================================================================
# Run locally:
#     uvicorn apps.api.main:app --reload --port 8000
#
# Interactive docs at http://localhost:8000/docs
# OpenAPI schema at  http://localhost:8000/openapi.json  (feeds gen:types)
# =============================================================================

from __future__ import annotations

import logging
import os
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .deps import VERSION, build_engine, get_engine
from .routers import agent, analytics, books, llm, reading_list, search
from .schemas import HealthResponse

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Lifespan — build the engine once, before the first request
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Iqra API v%s", VERSION)
    t0 = time.perf_counter()
    build_engine()
    logger.info("Engine build finished in %.1fs", time.perf_counter() - t0)
    yield
    logger.info("Shutting down.")


app = FastAPI(
    title="Iqra Digital Library API",
    version=VERSION,
    description=(
        "Hybrid retrieval (BM25 + FAISS + knowledge graph) with an optional "
        "advanced RAG pipeline (HyDE, multi-query RRF, cross-encoder re-ranking) "
        "and a LangGraph ReAct concierge."
    ),
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# CORS — explicit allowlist. ALLOWED_ORIGINS is a comma-separated env var.
# ---------------------------------------------------------------------------
_default_origins = "http://localhost:3000,http://127.0.0.1:3000"
_origins = [
    o.strip()
    for o in os.getenv("ALLOWED_ORIGINS", _default_origins).split(",")
    if o.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type"],
)
logger.info("CORS allowlist: %s", _origins)


# ---------------------------------------------------------------------------
# Rate limiting — the LLM-touching routes spend real money on a public deploy
# ---------------------------------------------------------------------------
_RATE_LIMITED_PREFIXES = ("/api/agent", "/api/explain", "/api/llm/connect")
_RATE_LIMIT = int(os.getenv("RATE_LIMIT_PER_MINUTE", "20"))
_hits: dict[str, deque[float]] = defaultdict(deque)


@app.middleware("http")
async def rate_limit(request: Request, call_next):
    path = request.url.path
    if not path.startswith(_RATE_LIMITED_PREFIXES):
        return await call_next(request)

    client = request.client.host if request.client else "unknown"
    now = time.time()
    window = _hits[client]

    while window and now - window[0] > 60:
        window.popleft()

    if len(window) >= _RATE_LIMIT:
        retry_after = int(60 - (now - window[0])) + 1
        return JSONResponse(
            status_code=429,
            content={
                "detail": (
                    f"Rate limit reached ({_RATE_LIMIT} AI requests per minute). "
                    f"Try again in {retry_after}s, or connect your own API key."
                )
            },
            headers={"Retry-After": str(retry_after)},
        )

    window.append(now)
    return await call_next(request)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
app.include_router(search.router,       prefix="/api")
app.include_router(books.router,        prefix="/api")
app.include_router(reading_list.router, prefix="/api")
app.include_router(analytics.router,    prefix="/api")
app.include_router(agent.router,        prefix="/api")
app.include_router(llm.router,          prefix="/api")


@app.get("/api/health", response_model=HealthResponse, tags=["meta"])
def health() -> HealthResponse:
    """
    Liveness and readiness.

    The frontend calls this on first paint to warm a sleeping Space and to show
    an honest "waking the retrieval engine" state rather than a bare spinner.
    """
    engine = get_engine()
    return HealthResponse(
        status="ok" if engine.ready else ("degraded" if engine.error else "starting"),
        indexReady=bool(engine.retriever and engine.retriever.is_ready),
        agentReady=bool(engine.agent and engine.agent.is_ready),
        llmConnected=bool(engine.llm and engine.llm.is_enabled),
        bookCount=engine.manager.book_count if engine.manager else 0,
        version=VERSION,
    )


@app.get("/", include_in_schema=False)
def root() -> dict[str, str]:
    return {
        "name": "Iqra Digital Library API",
        "version": VERSION,
        "docs": "/docs",
        "health": "/api/health",
    }
