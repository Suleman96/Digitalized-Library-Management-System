# =============================================================================
# agent.py — Iqra Digital Library v2
# =============================================================================
# LibraryAgent (Orchestrator)
# ---------------------------
# LangGraph ReAct orchestrator that routes user requests to two specialist
# worker agents:
#
#   SearchWorker  (agents/search_agent.py)
#     tools: search_local_library, search_google_books,
#            find_similar_books, search_by_rating
#
#   CuratorWorker (agents/curator_agent.py)
#     tools: save_book, remove_book, view_reading_list, count_reading_list
#
# The orchestrator uses MemorySaver for per-session conversation persistence.
# Workers are stateless — each invocation is an independent ReAct loop.
#
# Build sequence (called from app.py after LLM connect):
#   agent_mgr.build()  → True if orchestrator is built (workers log warnings
#                         on failure but do not abort the build)
# =============================================================================

from __future__ import annotations

import logging
from typing import Any

from config import settings

logger = logging.getLogger(__name__)

_ORCHESTRATOR_SYSTEM_PROMPT = """You are Iqra, a knowledgeable and friendly digital library assistant. \
Your job is to help users discover great books, get personalised recommendations, \
and manage their reading list.

You have two specialist workers you MUST delegate to:
- search_worker: finds books — local library, Google Books, similar books, rating-filtered
- curator_worker: manages the reading list — save, remove, view, count

Rules:
- For any book discovery or recommendation request → call search_worker.
- For any reading list operation → call curator_worker.
- For compound requests ("find X and save it") → call search_worker first, then curator_worker.
- Always delegate — never answer book questions from memory alone.
- Synthesise the workers' responses into a single, friendly reply.
- Use numbered lists for book results. Keep responses concise."""


class LibraryAgent:
    """
    LangGraph ReAct orchestrator with two specialist worker agents.

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
        from agents.search_agent  import SearchWorker
        from agents.curator_agent import CuratorWorker

        self._search_worker  = SearchWorker(hybrid_retriever, book_recommender, llm_provider)
        self._curator_worker = CuratorWorker(reading_list_mgr, llm_provider)
        self._llm_prov       = llm_provider
        self._agent: Any     = None

    # ── Tool wrappers (orchestrator delegates to workers) ─────────────────
    def _build_tools(self) -> list:
        from langchain_core.tools import tool

        _search  = self._search_worker
        _curator = self._curator_worker

        @tool
        def search_worker(query: str) -> str:
            """Delegate any book discovery or recommendation request to the Search specialist.
            Use for: finding books by topic/genre/author, recommendations, similar books,
            Google Books search, and rating-filtered searches."""
            return _search.run(query)

        @tool
        def curator_worker(instruction: str) -> str:
            """Delegate any reading list operation to the Curator specialist.
            Use for: saving a book, removing a book, viewing the reading list,
            counting saved books."""
            return _curator.run(instruction)

        return [search_worker, curator_worker]

    # ── Build / reset ─────────────────────────────────────────────────────
    def build(self) -> bool:
        """
        Build SearchWorker, CuratorWorker, and the Orchestrator agent.

        Returns True once the orchestrator is up.
        Worker failures are logged as warnings — the orchestrator still starts
        and the tool functions return a graceful error string if a worker is down.
        """
        lc_llm = self._llm_prov.get_langchain_llm()
        if lc_llm is None:
            logger.warning("LibraryAgent.build: no LangChain LLM available.")
            return False

        search_ok  = self._search_worker.build()
        curator_ok = self._curator_worker.build()
        if not search_ok:
            logger.warning("LibraryAgent.build: SearchWorker failed to build.")
        if not curator_ok:
            logger.warning("LibraryAgent.build: CuratorWorker failed to build.")

        try:
            from langgraph.prebuilt import create_react_agent
            from langgraph.checkpoint.memory import MemorySaver

            memory = MemorySaver()
            tools  = self._build_tools()

            self._agent = create_react_agent(
                lc_llm,
                tools,
                checkpointer=memory,
                prompt=_ORCHESTRATOR_SYSTEM_PROMPT,
            )
            logger.info(
                "LibraryAgent orchestrator built — search=%s curator=%s",
                "✓" if search_ok else "✗",
                "✓" if curator_ok else "✗",
            )
            return True

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
        """Tear down all agents (call before re-configuring the LLM)."""
        self._agent = None
        self._search_worker.reset()
        self._curator_worker.reset()

    # ── Chat ──────────────────────────────────────────────────────────────
    def chat(self, message: str, thread_id: str) -> str:
        """
        Send a user message and return the assistant's reply.

        Parameters
        ----------
        message   : user's text
        thread_id : unique session identifier (persists conversation history)
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
