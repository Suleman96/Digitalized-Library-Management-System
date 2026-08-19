# =============================================================================
# schemas.py — Iqra Digital Library v3
# =============================================================================
# Pydantic models are the single source of truth for the API contract.
# FastAPI derives the OpenAPI spec from them; `pnpm gen:types` derives the
# TypeScript types from that spec.  Change a model here and the frontend's
# types change on the next generate — drift becomes a build error.
# =============================================================================

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Book
# ---------------------------------------------------------------------------
class Book(BaseModel):
    """Canonical book shape, produced by BookRecommender._normalise()."""

    id:             str   = Field(..., description="Deterministic sha1(title::first_author)[:16]")
    title:          str
    authors:        str
    subtitle:       str   = ""
    description:    str   = ""
    thumbnail:      str   = ""
    average_rating: float = 0.0
    ratings_count:  int   = 0
    info_link:      str   = "#"
    language:       str   = ""
    published_year: str   = ""
    num_pages:      int   = 0
    source:         str   = ""
    similarity:     float = 0.0
    categories:     str   = ""

    model_config = {"extra": "allow"}


# ---------------------------------------------------------------------------
# Pipeline trace
# ---------------------------------------------------------------------------
class StageTrace(BaseModel):
    name:       str   = Field(..., description="multi_query | hyde | hybrid_retrieve | rrf | rerank")
    candidates: int
    durationMs: float
    detail:     str = ""
    topShift:   int | None = Field(
        None, description="New position of the pre-rerank #1 result; shows how much re-ranking changed"
    )


class PipelineTrace(BaseModel):
    """What actually ran during a search. Rendered by the frontend."""

    originalQuery: str
    hydeDocument:  str | None = None
    queryVariants: list[str]  = []
    stages:        list[StageTrace] = []
    totalMs:       float = 0.0


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------
SearchScope = Literal["both", "local", "external"]
SortBy      = Literal["similarity", "rating", "year"]


class SearchRequest(BaseModel):
    query:       str  = Field(..., min_length=1, max_length=500)
    language:    str  = "Any"
    category:    str  = "Any"
    localLimit:  int  = Field(12, ge=0, le=48)
    externalLimit: int = Field(6, ge=0, le=24)
    minRating:   float = Field(0.0, ge=0.0, le=5.0)
    scope:       SearchScope = "both"
    sortBy:      SortBy = "similarity"

    # RAG toggles
    useAiExpansion: bool = False
    useHyde:        bool = False
    useMultiQuery:  bool = False
    useRerank:      bool = False


class SearchResponse(BaseModel):
    local:    list[Book]
    external: list[Book]
    trace:    PipelineTrace
    expandedQuery: str | None = None


# ---------------------------------------------------------------------------
# Catalogue
# ---------------------------------------------------------------------------
class BookPage(BaseModel):
    items:     list[Book]
    page:      int
    pageSize:  int
    total:     int
    pageCount: int


class AddBookRequest(BaseModel):
    title:          str = Field(..., min_length=1, max_length=300)
    authors:        str = Field("", max_length=300)
    description:    str = Field("", max_length=5000)
    categories:     str = Field("", max_length=200)
    thumbnail:      str = ""
    average_rating: float = Field(0.0, ge=0.0, le=5.0)
    published_year: str = ""
    num_pages:      int = Field(0, ge=0)
    language:       str = "en"


class MutationResult(BaseModel):
    ok:      bool
    message: str
    count:   int | None = None


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------
class ChatRequest(BaseModel):
    message:  str = Field(..., min_length=1, max_length=2000)
    threadId: str = Field(..., min_length=1, max_length=100)


# ---------------------------------------------------------------------------
# LLM provider
# ---------------------------------------------------------------------------
class ProviderInfo(BaseModel):
    provider:      str
    models:        list[str]
    requiresKey:   bool
    keyConfigured: bool


class ConnectRequest(BaseModel):
    provider:   str
    model:      str
    ollamaHost: str | None = None
    apiKey:     str | None = Field(
        None, description="Optional per-request key so public visitors can bring their own"
    )


class LLMStatus(BaseModel):
    connected: bool
    provider:  str | None = None
    model:     str | None = None
    message:   str = ""
    capabilities: dict[str, bool] = {}


# ---------------------------------------------------------------------------
# Explain
# ---------------------------------------------------------------------------
class ExplainRequest(BaseModel):
    query:  str = Field(..., min_length=1, max_length=500)
    bookId: str


class ExplainResponse(BaseModel):
    explanation: str
    provider:    str | None = None
    model:       str | None = None


# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------
class AnalyticsSummary(BaseModel):
    totalBooks:    int
    averageRating: float
    categoryCount: int
    totalPages:    int
    ratedBooks:    int
    earliestYear:  int | None = None
    latestYear:    int | None = None


class RatingBin(BaseModel):
    label:    str
    midpoint: float
    count:    int


class CategoryBin(BaseModel):
    label: str
    count: int


class YearPoint(BaseModel):
    year:  int
    count: int


class AnalyticsResponse(BaseModel):
    available:  bool
    summary:    AnalyticsSummary | None = None
    ratings:    list[RatingBin]   = []
    categories: list[CategoryBin] = []
    years:      list[YearPoint]   = []


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------
class HealthResponse(BaseModel):
    status:      Literal["ok", "starting", "degraded"]
    indexReady:  bool
    agentReady:  bool
    llmConnected: bool
    bookCount:   int
    version:     str


# ---------------------------------------------------------------------------
# Reading list
# ---------------------------------------------------------------------------
class SaveBookRequest(BaseModel):
    book: dict[str, Any]
