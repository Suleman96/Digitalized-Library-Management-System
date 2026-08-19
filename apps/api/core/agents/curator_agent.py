# =============================================================================
# agents/curator_agent.py — Iqra Digital Library v2
# =============================================================================
# CuratorWorker
# -------------
# Focused ReAct agent for reading list management.
# Exposes 4 tools: save, remove, view, count.
# Called as a sub-agent by the Orchestrator in agent.py.
# =============================================================================

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

_CURATOR_SYSTEM_PROMPT = """You are a reading list curator inside the Iqra Digital Library. \
Your sole responsibility is to manage the user's personal reading list.

You have four tools:
- save_book: add a book to the reading list by title
- remove_book: remove a book by its exact title
- view_reading_list: display all saved books
- count_reading_list: return the number of saved books

Guidelines:
- For save requests, extract the book title (and authors if mentioned) and call save_book.
- For removal requests, extract the exact title and call remove_book.
- For "show my list", "what have I saved", "my reading list", call view_reading_list.
- For "how many books", call count_reading_list.
- Always confirm the action you took. Be concise."""


class CuratorWorker:
    """
    Focused ReAct agent for reading list management.

    Parameters
    ----------
    reading_list_mgr : ReadingList
    llm_provider     : LLMProvider
    """

    def __init__(
        self,
        reading_list_mgr: Any,
        llm_provider:     Any,
    ) -> None:
        self._rl       = reading_list_mgr
        self._llm_prov = llm_provider
        self._agent:   Any = None

    # ── Tools ─────────────────────────────────────────────────────────────
    def _build_tools(self) -> list:
        from langchain_core.tools import tool

        rl = self._rl

        @tool
        def save_book(title: str, authors: str = "", rating: float = 0.0) -> str:
            """Save a book to the user's personal reading list by title."""
            book = {
                "title":          title,
                "authors":        authors,
                "average_rating": rating,
                "source":         "🤖 AI Agent",
                "info_link":      "#",
            }
            return rl.add(book)

        @tool
        def remove_book(title: str) -> str:
            """Remove a book from the reading list by its exact title."""
            return rl.remove(title)

        @tool
        def view_reading_list(placeholder: str = "") -> str:
            """Show all books currently saved in the reading list."""
            books = rl.get_all()
            if not books:
                return "Your reading list is empty."
            lines = [
                f"{i+1}. **{b['title']}** by {b.get('authors', 'Unknown')} "
                f"(⭐ {float(b.get('average_rating', 0)):.1f}) "
                f"— saved {str(b.get('added_at', ''))[:10]}"
                for i, b in enumerate(books)
            ]
            return f"Reading list ({len(books)} books):\n" + "\n".join(lines)

        @tool
        def count_reading_list(placeholder: str = "") -> str:
            """Return how many books are in the reading list."""
            n = rl.count
            return f"You have {n} book{'s' if n != 1 else ''} in your reading list."

        return [save_book, remove_book, view_reading_list, count_reading_list]

    # ── Build ──────────────────────────────────────────────────────────────
    def build(self) -> bool:
        lc_llm = self._llm_prov.get_langchain_llm()
        if lc_llm is None:
            logger.warning("CuratorWorker.build: no LangChain LLM available.")
            return False

        try:
            from langgraph.prebuilt import create_react_agent

            tools = self._build_tools()
            self._agent = create_react_agent(
                lc_llm,
                tools,
                prompt=_CURATOR_SYSTEM_PROMPT,
            )
            logger.info("CuratorWorker built (%d tools).", len(tools))
            return True

        except Exception as exc:
            logger.error("CuratorWorker.build failed: %s", exc)
            return False

    def reset(self) -> None:
        self._agent = None

    # ── Run ────────────────────────────────────────────────────────────────
    def run(self, instruction: str) -> str:
        if self._agent is None:
            return "Curator worker is not available — agent not built."
        try:
            result = self._agent.invoke(
                {"messages": [{"role": "user", "content": instruction}]}
            )
            messages = result.get("messages", [])
            if messages:
                last = messages[-1]
                return last.content if hasattr(last, "content") else str(last)
        except Exception as exc:
            logger.error("CuratorWorker.run error: %s", exc)
            return f"Curator error: {exc}"
        return "No response generated."

    @property
    def is_ready(self) -> bool:
        return self._agent is not None
