# =============================================================================
# routers/books.py — catalogue browse, detail, and admin
# =============================================================================

from __future__ import annotations

import logging
import math
from typing import Any

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query

from ..core.config import settings
from ..core.recommender import book_id, clean_year, to_https
from ..deps import Engine, get_engine
from ..schemas import AddBookRequest, Book, BookPage, MutationResult

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/books", tags=["books"])

_DEFAULT_PAGE_SIZE = 24
_PLACEHOLDER_COVER = "https://placehold.co/200x290/E2E8F0/94A3B8?text=No+Cover"


def _row_to_book(row: dict[str, Any]) -> dict[str, Any]:
    """Convert one CSV row to the canonical Book shape."""
    title   = str(row.get("title", "") or "Unknown Title").strip()
    authors = str(row.get("authors", "") or "Unknown Author").strip()
    thumb   = str(row.get("thumbnail", "") or "").strip()

    def _f(key: str) -> float:
        try:
            return float(row.get(key) or 0)
        except (TypeError, ValueError):
            return 0.0

    def _i(key: str) -> int:
        try:
            return int(float(row.get(key) or 0))
        except (TypeError, ValueError):
            return 0


    return {
        "id":             book_id(title, authors, row.get("isbn13") or row.get("isbn10") or ""),
        "title":          title,
        "authors":        authors,
        "subtitle":       str(row.get("subtitle", "") or ""),
        "description":    str(row.get("description", "") or ""),
        "thumbnail":      to_https(thumb) if thumb else _PLACEHOLDER_COVER,
        "average_rating": _f("average_rating"),
        "ratings_count":  _i("ratings_count"),
        "info_link":      str(row.get("info_link", "") or "#"),
        "language":       str(row.get("language", "") or "").lower(),
        "published_year": clean_year(row.get("published_year")),
        "num_pages":      _i("num_pages"),
        "categories":     str(row.get("categories", "") or ""),
        "source":         "Local Library",
        "similarity":     0.0,
    }


def _load_catalogue() -> pd.DataFrame:
    try:
        return pd.read_csv(settings.csv_path, dtype=str).fillna("")
    except FileNotFoundError:
        raise HTTPException(503, "Catalogue file not found on the server.")


@router.get("", response_model=BookPage)
def browse(
    q: str = Query("", max_length=200, description="Free-text filter over title and author"),
    page: int = Query(1, ge=1),
    pageSize: int = Query(_DEFAULT_PAGE_SIZE, ge=1, le=100),
    language: str = Query("", description="ISO language code filter"),
    minRating: float = Query(0.0, ge=0.0, le=5.0),
) -> BookPage:
    """Paginated catalogue browse with filtering."""
    df = _load_catalogue()

    if q.strip():
        needle = q.strip().lower()
        mask = (
            df["title"].str.lower().str.contains(needle, na=False, regex=False)
            | df["authors"].str.lower().str.contains(needle, na=False, regex=False)
        )
        df = df[mask]

    if language:
        df = df[df["language"].str.lower() == language.lower()]

    if minRating > 0:
        ratings = pd.to_numeric(df["average_rating"], errors="coerce").fillna(0.0)
        df = df[ratings >= minRating]

    total = len(df)
    page_count = max(1, math.ceil(total / pageSize))
    page = min(page, page_count)
    start = (page - 1) * pageSize

    items = [_row_to_book(r) for r in df.iloc[start : start + pageSize].to_dict("records")]

    return BookPage(
        items=[Book(**b) for b in items],
        page=page,
        pageSize=pageSize,
        total=total,
        pageCount=page_count,
    )


@router.get("/{book_ref}", response_model=Book)
def get_book(book_ref: str) -> Book:
    """Fetch one book by its deterministic id. Powers the /book/[id] route."""
    df = _load_catalogue()
    for row in df.to_dict("records"):
        candidate = _row_to_book(row)
        if candidate["id"] == book_ref:
            return Book(**candidate)
    raise HTTPException(404, "Book not found.")


@router.get("/{book_ref}/similar", response_model=list[Book])
def similar(
    book_ref: str,
    limit: int = Query(6, ge=1, le=24),
    engine: Engine = Depends(get_engine),
) -> list[Book]:
    """Books semantically closest to the given one."""
    if not engine.ready:
        raise HTTPException(503, "Retrieval engine is still starting.")

    target = get_book(book_ref)
    seed = f"{target.title} {target.authors} {target.description[:400]}".strip()

    results = engine.retriever.search(seed, k=limit + 5)
    out: list[Book] = []
    for b in results:
        if not b.get("id"):
            b["id"] = book_id(str(b.get("title", "")), str(b.get("authors", "")))
        if b["id"] == book_ref:
            continue  # never recommend the book itself
        out.append(Book(**b))
        if len(out) >= limit:
            break
    return out


@router.post("", response_model=MutationResult, status_code=201)
def add_book(req: AddBookRequest, engine: Engine = Depends(get_engine)) -> MutationResult:
    """Add a book to the catalogue and rebuild the FAISS index."""
    if not engine.ready:
        raise HTTPException(503, "Retrieval engine is still starting.")

    message = engine.manager.add_book(req.model_dump())
    engine.recommender.reload_index()
    engine.retriever.reload(embed_fn=engine.recommender._embed)

    return MutationResult(ok=True, message=message, count=engine.manager.book_count)


@router.delete("/{book_ref}", response_model=MutationResult)
def remove_book(book_ref: str, engine: Engine = Depends(get_engine)) -> MutationResult:
    """Remove a book by id and rebuild the FAISS index."""
    if not engine.ready:
        raise HTTPException(503, "Retrieval engine is still starting.")

    target = get_book(book_ref)
    message = engine.manager.remove_book(target.title)
    engine.recommender.reload_index()
    engine.retriever.reload(embed_fn=engine.recommender._embed)

    return MutationResult(ok=True, message=message, count=engine.manager.book_count)
