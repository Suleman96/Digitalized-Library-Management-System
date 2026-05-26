# =============================================================================
# agent.py — Iqra Digital Library v2
# =============================================================================
# LibraryAgent
# ------------
# LangGraph ReAct agent that acts as a conversational library assistant.
# Uses MemorySaver for per-session conversation persistence.
#
# Tools available to the agent:
#   1. search_local_library  — hybrid BM25+FAISS search
#   2. search_google_books   — live Google Books API search
#   3. find_similar_books    — semantic similarity search by title
#   4. save_to_reading_list  — bookmark a book
#   5. filter_by_rating      — returns a guidance string for the agent
#
# Build sequence (in app.py, after LLM is connected):
#   agent_mgr.build()  → True if successful
# =============================================================================

from __future__ import annotations

import logging
from typing import Any

from config import settings

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are Iqra, a knowledgeable and friendly digital library assistant. \
Your job is to help users discover great books, get personalised recommendations, \
and manage their reading list. You have tools to search the local library and Google Books, \
find similar books, and save books for later.

Guidelines:
- Always search before answering book questions — don't rely on training knowledge alone.
- Keep responses concise and friendly.
- When listing books, use numbered lists with title, author, and a brief note.
- If a user wants to save a book, call save_to_reading_list immediately.
- Suggest related searches when results are limited."""


class LibraryAgent:
    """
    LangGraph ReAct agent with per-session conversation memory.

    Parameters
    ----------
    hybrid_retriever : HybridRetriever  — hybrid BM25+FAISS search
    book_recommender : BookRecommender  — FAISS + Google Books search
    reading_list_mgr : ReadingList      — bookmark manager
    llm_provider     : LLMProvider      — connected AI provider
    """

    def __init__(
        self,
        hybrid_retriever: Any,
        book_recommender: Any,
        reading_list_mgr: Any,
        llm_provider:     Any,
    ) -> None:
        self._hybrid   = hybrid_retriever
        self._reco     = book_recommender
        self._rl       = reading_list_mgr
        self._llm_prov = llm_provider
        self._agent:   Any = None

    # ── Tool factory ─────────────────────────────────────────────────────
    def _build_tools(self) -> list:
        from langchain_core.tools import tool

        hybrid = self._hybrid
        reco   = self._reco
        rl     = self._rl

        @tool
        def search_local_library(query: str) -> str:
            """Search the local library (BM25 + FAISS hybrid) for books matching the query."""
            if hybrid.is_ready:
                results = hybrid.search(query, k=6)
            else:
                local_r, _ = reco.recommend(
                    query, "Any", 6, 0, 0.0, "Local Only", "Similarity"
                )
                results = local_r
            if not results:
                return f"No local books found for '{query}'."
            lines = [
                f"{i+1}. **{b['title']}** by {b['authors']} "
                f"(⭐ {b['average_rating']:.1f})"
                for i, b in enumerate(results)
            ]
            return "Local library results:\n" + "\n".join(lines)

        @tool
        def search_google_books(query: str) -> str:
            """Search Google Books for books matching the query (live internet search)."""
            _, ext_r = reco.recommend(
                query, "Any", 0, 6, 0.0, "External Only", "Similarity"
            )
            if not ext_r:
                return f"No Google Books results for '{query}'."
            lines = [
                f"{i+1}. **{b['title']}** by {b['authors']} "
                f"(⭐ {b['average_rating']:.1f})"
                for i, b in enumerate(ext_r)
            ]
            return "Google Books results:\n" + "\n".join(lines)

        @tool
        def find_similar_books(title: str) -> str:
            """Find books semantically similar to the given title in the local library."""
            local_r, _ = reco.recommend(
                title, "Any", 6, 0, 0.0, "Local Only", "Similarity"
            )
            if not local_r:
                return f"No similar books found for '{title}'."
            lines = [
                f"{i+1}. **{b['title']}** by {b['authors']}"
                for i, b in enumerate(local_r)
            ]
            return f"Books similar to '{title}':\n" + "\n".join(lines)

        @tool
        def save_to_reading_list(title: str, authors: str = "", rating: float = 0.0) -> str:
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
        def filter_by_rating(min_rating: float) -> str:
            """Instruct filtering of search results to only show books rated >= min_rating."""
            return (
                f"Filter applied: showing only books rated {min_rating:.1f} or higher. "
                f"Please search again and I will focus on higher-rated results."
            )

        return [
            search_local_library,
            search_google_books,
            find_similar_books,
            save_to_reading_list,
            filter_by_rating,
        ]

    # ── Build / reset ─────────────────────────────────────────────────────
    def build(self) -> bool:
        """
        Build the LangGraph ReAct agent.

        Returns True on success, False if the LLM is not connected or
        a required package is missing.
        """
        lc_llm = self._llm_prov.get_langchain_llm()
        if lc_llm is None:
            logger.warning("LibraryAgent.build: no LangChain LLM available.")
            return False

        try:
            from langchain_core.messages import SystemMessage
            from langgraph.prebuilt import create_react_agent
            from langgraph.checkpoint.memory import MemorySaver

            memory = MemorySaver()
            tools  = self._build_tools()

            self._agent = create_react_agent(
                lc_llm,
                tools,
                checkpointer=memory,
                state_modifier=SystemMessage(content=_SYSTEM_PROMPT),
            )
            logger.info("LibraryAgent built successfully (%d tools).", len(tools))
            return True

        except TypeError:
            # Older langgraph versions use 'messages_modifier' instead of 'state_modifier'
            try:
                from langchain_core.messages import SystemMessage
                from langgraph.prebuilt import create_react_agent
                from langgraph.checkpoint.memory import MemorySaver

                memory = MemorySaver()
                tools  = self._build_tools()

                self._agent = create_react_agent(
                    lc_llm,
                    tools,
                    checkpointer=memory,
                    messages_modifier=SystemMessage(content=_SYSTEM_PROMPT),
                )
                logger.info("LibraryAgent built (legacy API).")
                return True

            except Exception as exc:
                logger.error("LibraryAgent.build fallback failed: %s", exc)
                return False

        except ImportError as exc:
            logger.error(
                "LibraryAgent.build: missing package — %s. "
                "Run: pip install langgraph langchain-core",
                exc,
            )
            return False

        except Exception as exc:
            logger.error("LibraryAgent.build failed: %s", exc)
            return False

    def reset(self) -> None:
        """Tear down the agent (call before re-configuring the LLM)."""
        self._agent = None

    # ── Chat ──────────────────────────────────────────────────────────────
    def chat(self, message: str, thread_id: str) -> str:
        """
        Send a user message and return the assistant's reply.

        Parameters
        ----------
        message   : user's text
        thread_id : unique session identifier (persists conversation history)

        Returns
        -------
        str  — assistant reply, or an error/instruction string.
        """
        if self._agent is None:
            return (
                "The AI agent is not active. "
                "Please open the AI Settings panel, select a provider, "
                "and click Connect."
            )

        config = {"configurable": {"thread_id": thread_id}}
        try:
            result = self._agent.invoke(
                {"messages": [{"role": "user", "content": message}]},
                config=config,
            )
            messages = result.get("messages", [])
            if messages:
                last = messages[-1]
                return last.content if hasattr(last, "content") else str(last)
        except Exception as exc:
            logger.error("LibraryAgent.chat error: %s", exc)
            return f"Agent error: {exc}"

        return "No response generated. Please try again."

    @property
    def is_ready(self) -> bool:
        return self._agent is not None
