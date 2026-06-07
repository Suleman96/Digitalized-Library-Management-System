# =============================================================================
# agents/search_agent.py — Iqra Digital Library v2
# =============================================================================
# SearchWorker
# ------------
# Focused ReAct agent for book discovery.
# Exposes 4 tools: local library search, Google Books, similarity search,
# and rating-filtered search.
# Called as a sub-agent by the Orchestrator in agent.py.
# =============================================================================

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

_SEARCH_SYSTEM_PROMPT = """You are a book search specialist inside the Iqra Digital Library. \
Your sole responsibility is to find books that match the user's request.

You have four tools:
- search_local_library: hybrid BM25+FAISS+Knowledge Graph search
- search_google_books: live Google Books search
- find_similar_books: semantic similarity to a specific title
- search_by_rating: search with a minimum rating filter

Guidelines:
- Always call at least one tool before responding.
- For general requests, start with search_local_library.
- For rating-filtered requests ("highly rated", "top rated"), use search_by_rating.
- For "books like X" or "similar to X", use find_similar_books.
- For requests beyond the local library, use search_google_books.
- Return a numbered list: title, author, rating. Be concise — no preamble."""


class SearchWorker:
    """
    Focused ReAct agent for book discovery.

    Parameters
    ----------
    hybrid_retriever : HybridRetriever
    book_recommender : BookRecommender
    llm_provider     : LLMProvider
    """

    def __init__(
        self,
        hybrid_retriever: Any,
        book_recommender: Any,
        llm_provider:     Any,
    ) -> None:
        self._hybrid   = hybrid_retriever
        self._reco     = book_recommender
        self._llm_prov = llm_provider
        self._agent:   Any = None

    # ── Tools ─────────────────────────────────────────────────────────────
    def _build_tools(self) -> list:
        from langchain_core.tools import tool

        hybrid = self._hybrid
        reco   = self._reco

        @tool
        def search_local_library(query: str) -> str:
            """Search the local library (BM25 + FAISS + Knowledge Graph) for books matching the query."""
            if hybrid.is_ready:
                results = hybrid.search(query, k=6)
            else:
                local_r, _ = reco.recommend(query, "Any", 6, 0, 0.0, "Local Only", "Similarity")
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
            _, ext_r = reco.recommend(query, "Any", 0, 6, 0.0, "External Only", "Similarity")
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
            local_r, _ = reco.recommend(title, "Any", 6, 0, 0.0, "Local Only", "Similarity")
            if not local_r:
                return f"No similar books found for '{title}'."
            lines = [
                f"{i+1}. **{b['title']}** by {b['authors']}"
                for i, b in enumerate(local_r)
            ]
            return f"Books similar to '{title}':\n" + "\n".join(lines)

        @tool
        def search_by_rating(query: str, min_rating: float = 4.0) -> str:
            """Search the local library and return only books rated >= min_rating (0.0–5.0)."""
            if hybrid.is_ready:
                candidates = hybrid.search(query, k=20)
            else:
                candidates, _ = reco.recommend(query, "Any", 20, 0, 0.0, "Local Only", "Rating")
            filtered = [b for b in candidates if float(b.get("average_rating", 0)) >= min_rating]
            results  = filtered[:6] if filtered else candidates[:6]
            if not results:
                return f"No books found for '{query}' with rating ≥ {min_rating}."
            lines = [
                f"{i+1}. **{b['title']}** by {b['authors']} "
                f"(⭐ {float(b.get('average_rating', 0)):.1f})"
                for i, b in enumerate(results)
            ]
            tag = f" (rating ≥ {min_rating})" if filtered else " (best available)"
            return f"Books matching '{query}'{tag}:\n" + "\n".join(lines)

        return [search_local_library, search_google_books, find_similar_books, search_by_rating]

    # ── Build ──────────────────────────────────────────────────────────────
    def build(self) -> bool:
        lc_llm = self._llm_prov.get_langchain_llm()
        if lc_llm is None:
            logger.warning("SearchWorker.build: no LangChain LLM available.")
            return False

        try:
            from langgraph.prebuilt import create_react_agent

            tools = self._build_tools()
            self._agent = create_react_agent(
                lc_llm,
                tools,
                prompt=_SEARCH_SYSTEM_PROMPT,
            )
            logger.info("SearchWorker built (%d tools).", len(tools))
            return True

        except Exception as exc:
            logger.error("SearchWorker.build failed: %s", exc)
            return False

    def reset(self) -> None:
        self._agent = None

    # ── Run ────────────────────────────────────────────────────────────────
    def run(self, query: str) -> str:
        if self._agent is None:
            return "Search worker is not available — agent not built."
        try:
            result = self._agent.invoke(
                {"messages": [{"role": "user", "content": query}]}
            )
            messages = result.get("messages", [])
            if messages:
                last = messages[-1]
                return last.content if hasattr(last, "content") else str(last)
        except Exception as exc:
            logger.error("SearchWorker.run error: %s", exc)
            return f"Search error: {exc}"
        return "No search results generated."

    @property
    def is_ready(self) -> bool:
        return self._agent is not None
