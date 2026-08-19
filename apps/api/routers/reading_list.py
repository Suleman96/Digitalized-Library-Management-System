# =============================================================================
# routers/reading_list.py — saved books
# =============================================================================

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import FileResponse

from ..core.exporter import export_books_pdf
from ..core.recommender import book_id
from ..deps import Engine, get_engine
from ..schemas import Book, MutationResult, SaveBookRequest

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/reading-list", tags=["reading-list"])


@router.get("", response_model=list[Book])
def get_reading_list(engine: Engine = Depends(get_engine)) -> list[Book]:
    """The saved list as data. v2 returned a rendered HTML table here."""
    out: list[Book] = []
    for b in engine.reading_list.get_all():
        if not b.get("id"):
            b["id"] = book_id(str(b.get("title", "")), str(b.get("authors", "")))
        out.append(Book(**b))
    return out


@router.post("", response_model=MutationResult, status_code=201)
def save_book(req: SaveBookRequest, engine: Engine = Depends(get_engine)) -> MutationResult:
    """Save a book to the reading list."""
    book = req.book
    if not str(book.get("title", "")).strip():
        raise HTTPException(422, "Cannot save a book without a title.")

    if not book.get("id"):
        book["id"] = book_id(str(book.get("title", "")), str(book.get("authors", "")))

    message = engine.reading_list.add(book)
    return MutationResult(
        ok="already" not in message,
        message=message,
        count=engine.reading_list.count,
    )


@router.delete("/{book_ref}", response_model=MutationResult)
def remove(book_ref: str, engine: Engine = Depends(get_engine)) -> MutationResult:
    """Remove one book by id (falls back to a title match for legacy entries)."""
    message = engine.reading_list.remove(book_ref)
    return MutationResult(
        ok="not found" not in message,
        message=message,
        count=engine.reading_list.count,
    )


@router.delete("", status_code=204)
def clear(engine: Engine = Depends(get_engine)) -> Response:
    """Empty the reading list."""
    engine.reading_list.clear()
    return Response(status_code=204)


@router.post("/export", response_class=FileResponse)
def export_pdf(engine: Engine = Depends(get_engine)) -> FileResponse:
    """Export the reading list as a PDF download."""
    books = engine.reading_list.get_all()
    if not books:
        raise HTTPException(422, "Reading list is empty — nothing to export.")

    try:
        path = export_books_pdf(books, title="Iqra — Reading List")
    except Exception as exc:
        logger.error("PDF export failed: %s", exc)
        raise HTTPException(500, "Could not generate the PDF.")

    return FileResponse(
        path,
        media_type="application/pdf",
        filename="iqra-reading-list.pdf",
    )
