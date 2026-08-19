# =============================================================================
# reading_list.py — Iqra Digital Library v2
# =============================================================================
# ReadingList
# -----------
# JSON-backed bookmark manager stored at data/reading_list.json.
# Returns plain dicts only — rendering is the frontend's concern.
# =============================================================================

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from .config import settings

logger = logging.getLogger(__name__)

_RL_PATH: Path = settings.data_dir / "reading_list.json"


class ReadingList:
    """Persisted reading list backed by a JSON file."""

    def __init__(self) -> None:
        self._path = _RL_PATH
        self._books: list[dict[str, Any]] = self._load()

    # ── Persistence ───────────────────────────────────────────────────────
    def _load(self) -> list[dict[str, Any]]:
        if self._path.exists():
            try:
                return json.loads(self._path.read_text(encoding="utf-8"))
            except Exception as exc:
                logger.warning("reading_list: could not load %s — %s", self._path, exc)
        return []

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps(self._books, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    # ── Public API ────────────────────────────────────────────────────────
    def add(self, book: dict[str, Any]) -> str:
        title = str(book.get("title", "")).strip()
        if not title:
            return "Cannot save a book without a title."
        bid = book.get("id")
        if bid and any(b.get("id") == bid for b in self._books):
            return f"'{title}' is already in your reading list."
        if any(b.get("title") == title for b in self._books):
            return f"'{title}' is already in your reading list."
        entry = {**book, "added_at": datetime.now().isoformat()}
        self._books.append(entry)
        self._save()
        logger.info("Reading list: added '%s'", title)
        return f"'{title}' added to your reading list."

    def remove(self, identifier: str) -> str:
        """
        Remove by book id, falling back to a case-insensitive title match so
        entries saved before ids existed can still be removed.
        """
        identifier = (identifier or "").strip()
        if not identifier:
            return "No book specified."

        before = len(self._books)
        ident_lower = identifier.lower()
        self._books = [
            b for b in self._books
            if b.get("id") != identifier
            and str(b.get("title", "")).strip().lower() != ident_lower
        ]
        if len(self._books) == before:
            return f"'{identifier}' not found in reading list."
        self._save()
        logger.info("Reading list: removed '%s'", identifier)
        return f"Removed from reading list."

    def clear(self) -> str:
        self._books.clear()
        self._save()
        return "Reading list cleared."

    def get_all(self) -> list[dict[str, Any]]:
        return list(self._books)

    @property
    def count(self) -> int:
        return len(self._books)
