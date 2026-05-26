# =============================================================================
# reading_list.py — Iqra Digital Library v2
# =============================================================================
# ReadingList
# -----------
# JSON-backed bookmark manager stored at data/reading_list.json.
# Thread-safe for single-user Gradio deployments (Gradio queues writes).
# =============================================================================

from __future__ import annotations

import html as html_mod
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from config import settings

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
        if any(b.get("title") == title for b in self._books):
            return f"'{title}' is already in your reading list."
        entry = {**book, "added_at": datetime.now().isoformat()}
        self._books.append(entry)
        self._save()
        logger.info("Reading list: added '%s'", title)
        return f"'{title}' added to your reading list."

    def remove(self, title: str) -> str:
        title = title.strip()
        before = len(self._books)
        self._books = [b for b in self._books if b.get("title") != title]
        if len(self._books) == before:
            return f"'{title}' not found in reading list."
        self._save()
        logger.info("Reading list: removed '%s'", title)
        return f"'{title}' removed from reading list."

    def clear(self) -> str:
        self._books.clear()
        self._save()
        return "Reading list cleared."

    def get_all(self) -> list[dict[str, Any]]:
        return list(self._books)

    @property
    def count(self) -> int:
        return len(self._books)

    # ── HTML rendering ────────────────────────────────────────────────────
    def to_html(self) -> str:
        """Render the reading list as a styled HTML table."""
        if not self._books:
            return (
                '<div class="empty-state">'
                "<h3>Your reading list is empty</h3>"
                "<p>Save shortlisted titles from the Discovery workspace to build a client-ready shortlist.</p>"
                "</div>"
            )

        latest_added = max(str(b.get("added_at", ""))[:10] for b in self._books)
        rows = ""
        for b in self._books:
            title   = html_mod.escape(str(b.get("title",   "")))
            authors = html_mod.escape(str(b.get("authors", "")))
            rating  = float(b.get("average_rating", 0.0) or 0.0)
            source  = html_mod.escape(str(b.get("source",  "")))
            added   = str(b.get("added_at", ""))[:10]
            info    = b.get("info_link", "#") or "#"
            safe_info = html_mod.escape(info) if info.startswith(("http://", "https://", "#")) else "#"
            thumb   = str(b.get("thumbnail", "") or "")
            safe_thumb = html_mod.escape(thumb) if thumb.startswith(("http://", "https://")) else ""
            cover = (
                f"<img src='{safe_thumb}' alt='{title}' class='table-cover-image' />"
                if safe_thumb else "<span class='table-placeholder'>No cover</span>"
            )
            rows += (
                f"<tr>"
                f"<td>"
                f"<div class='table-book'>"
                f"<div class='table-cover'>{cover}</div>"
                f"<div>"
                f"<div class='table-title'>{title}</div>"
                f"<div class='table-subtle'>{authors}</div>"
                f"</div>"
                f"</div>"
                f"</td>"
                f"<td>⭐ {rating:.1f}</td>"
                f"<td><span class='table-source'>{source}</span></td>"
                f"<td>{added}</td>"
                f"<td><a class='table-link' href='{safe_info}' target='_blank' rel='noopener noreferrer'>Open</a></td>"
                f"</tr>"
            )

        return (
            '<div class="results-overview reading-overview">'
            f"<div class='results-kpi'><span class='results-kpi-value'>{len(self._books)}</span><span class='results-kpi-label'>Saved titles</span></div>"
            f"<div class='results-kpi'><span class='results-kpi-value'>{latest_added}</span><span class='results-kpi-label'>Latest update</span></div>"
            f"<div class='results-kpi'><span class='results-kpi-value'>{len({b.get('source', '') for b in self._books})}</span><span class='results-kpi-label'>Content sources</span></div>"
            "</div>"
            '<div class="browse-wrap">'
            '<table class="browse-table"><thead><tr>'
            "<th>Book</th><th>Rating</th>"
            "<th>Source</th><th>Saved</th><th>Link</th>"
            f"</tr></thead><tbody>{rows}</tbody></table></div>"
        )
