"""
Iqra Digital Library — ReAct Agent Graph Visualizer
====================================================
Run from the project root after the app has been started at least once
(so the FAISS index exists):

    python scripts/visualize_agent.py

Outputs:
  • Mermaid diagram text (always)
  • agent_graph.png  (if mermaid-cli or playwright is installed)
  • agent_architecture.md  (full system architecture as Markdown)

Requirements (for PNG):
    pip install playwright && playwright install chromium
    OR
    npm install -g @mermaid-js/mermaid-cli
"""

from __future__ import annotations

import os
import sys

# Allow running from project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _connect_llm():
    from llm_provider import llm

    provider = os.getenv("LLM_PROVIDER", "ollama").strip().lower()
    model    = os.getenv("LLM_MODEL",    "llama3.2").strip()

    print(f"\n[1/4] Connecting LLM: {provider}/{model} …")
    status = llm.configure(provider, model)
    print(f"      {status}")

    if not llm.is_enabled:
        print("\n❌  LLM not connected — set LLM_PROVIDER and LLM_MODEL env vars.")
        sys.exit(1)

    return llm


def _build_agent(llm):
    print("[2/4] Loading services …")
    from manager          import DynamicBookManager
    from recommender      import BookRecommender
    from reading_list     import ReadingList
    from hybrid_retriever import HybridRetriever
    from rag_pipeline     import RAGPipeline
    from agent            import LibraryAgent

    manager  = DynamicBookManager()
    reco     = BookRecommender()
    rl       = ReadingList()
    hybrid   = HybridRetriever()
    hybrid.build(embed_fn=reco._embed)
    rag      = RAGPipeline(hybrid, llm)

    agent_mgr = LibraryAgent(hybrid, reco, rl, llm)

    print("[3/4] Building ReAct agent …")
    ok = agent_mgr.build()
    if not ok:
        print("❌  Agent build failed — check LangChain packages are installed.")
        sys.exit(1)

    print("      ✅  Agent built successfully")
    return agent_mgr


def _print_mermaid(agent_mgr):
    graph = agent_mgr._agent

    print("\n" + "=" * 60)
    print("  LangGraph ReAct — Mermaid Diagram")
    print("=" * 60)
    try:
        mermaid_text = graph.get_graph().draw_mermaid()
        print(mermaid_text)

        with open("agent_graph.mmd", "w", encoding="utf-8") as f:
            f.write(mermaid_text)
        print("  Saved → agent_graph.mmd")
    except Exception as exc:
        print(f"  Could not generate Mermaid: {exc}")
        return

    return graph


def _save_png(graph):
    print("\n[4/4] Saving PNG …")
    try:
        png_data = graph.get_graph().draw_mermaid_png()
        with open("agent_graph.png", "wb") as f:
            f.write(png_data)
        print("  ✅  Saved → agent_graph.png")
    except Exception as exc:
        print(f"  ⚠️   PNG export failed: {exc}")
        print("       Install playwright:  pip install playwright && playwright install chromium")


def _print_ascii(graph):
    print("\n" + "=" * 60)
    print("  LangGraph ReAct — ASCII Graph")
    print("=" * 60)
    try:
        ascii_repr = graph.get_graph().draw_ascii()
        print(ascii_repr)
    except Exception as exc:
        print(f"  (ASCII render unavailable: {exc})")


def _print_message_flow():
    print("""
========================================================
  Message Flow — what happens on each user message
========================================================

  User: "Find me a mystery book set in Cairo"
    │
    ▼  HumanMessage("Find me a mystery book set in Cairo")
  ┌─────────────────────────────────┐
  │        agent node (LLM)         │
  │  Input:  [SystemMsg, HumanMsg]  │
  │  Output: AIMessage with         │
  │          tool_calls=[           │
  │            search_local_library(│
  │              "mystery Cairo"    │
  │            )                    │
  │          ]                      │
  └────────────────┬────────────────┘
                   │ tool_calls present → go to tools node
                   ▼
  ┌─────────────────────────────────┐
  │        tools node               │
  │  Executes: search_local_library │
  │  Returns:  ToolMessage(         │
  │    "1. The Cairo Affair …       │
  │     2. Death on the Nile …"     │
  │  )                              │
  └────────────────┬────────────────┘
                   │ loop back to agent node
                   ▼
  ┌─────────────────────────────────┐
  │        agent node (LLM)         │
  │  Input: [Sys, Human, AI+tools,  │
  │          ToolMessage]           │
  │  Output: AIMessage(             │
  │   "Here are great mysteries …"  │
  │  )  ← no tool_calls             │
  └────────────────┬────────────────┘
                   │ no tool_calls → __end__
                   ▼
  Response returned to Gradio UI
""")


def _write_architecture_doc():
    doc = """\
# Iqra Digital Library — ReAct System Architecture

## Component Map

```
User (Browser)
    │
    ▼
Gradio UI  (app.py)
    ├── AI Settings Panel   → LLMProvider.configure()
    ├── AI Librarian Tab    → LibraryAgent.chat()
    ├── Recommend Tab       → RAGPipeline.search() / BookRecommender.recommend()
    ├── Analytics Tab       → pandas + matplotlib
    ├── Reading List Tab    → ReadingList
    ├── Browse Tab          → pandas CSV
    └── Manage Library Tab  → DynamicBookManager.add/remove_book()

LLMProvider  (llm_provider.py)
    ├── Providers: Claude | OpenAI | Gemini | Ollama
    ├── get_langchain_llm()  → used by LibraryAgent
    ├── expand_query()       → used by Recommend tab
    ├── explain_match()      → used by Recommend tab
    ├── generate_hypothetical_doc()  → HyDE in RAGPipeline
    └── generate_query_variants()   → Multi-query in RAGPipeline

LibraryAgent  (agent.py)
    ├── build()   → creates LangGraph ReAct graph + MemorySaver
    ├── chat()    → invokes the graph with thread_id for session memory
    └── tools:
        ├── search_local_library   → HybridRetriever.search()
        ├── search_google_books    → BookRecommender._search_google()
        ├── find_similar_books     → BookRecommender.recommend()
        ├── save_to_reading_list   → ReadingList.add()
        └── filter_by_rating       → ⚠️  no-op (bug)

HybridRetriever  (hybrid_retriever.py)
    ├── build()   → constructs NetworkX Knowledge Graph + loads FAISS
    ├── search()  → FAISS pool → KG 1-hop expansion → score fusion
    └── Graph edges:
        ├── SAME_AUTHOR   (weight 1.00)
        ├── SAME_CATEGORY (weight 0.75)
        └── SEMANTIC_SIM  (weight = cosine sim ≥ 0.82)

RAGPipeline  (rag_pipeline.py)
    ├── search()  → wraps HybridRetriever with optional stages:
    │   ├── [optional] HyDE        → LLM generates hypothetical doc
    │   ├── [optional] Multi-query → LLM generates 3 query variants + RRF merge
    │   └── [optional] Re-rank    → CrossEncoder scores each (query, book) pair
    └── Falls back gracefully when LLM is off

BookRecommender  (recommender.py)
    ├── recommend()          → FAISS + Google Books + OpenLibrary
    ├── _search_local()      → FAISS cosine similarity
    └── _search_external()   → Google Books API + OpenLibrary (parallel)

DynamicBookManager  (manager.py)
    ├── add_book()    → CSV append + FAISS rebuild
    └── remove_book() → CSV filter + FAISS rebuild

Data Layer
    ├── data/books.csv              → canonical book dataset
    ├── artifacts/book_index.faiss  → FAISS vector index
    ├── artifacts/books_metadata.pkl → metadata parallel to FAISS
    ├── artifacts/book_graph.pkl    → NetworkX KG cache
    └── data/reading_list.json      → user bookmarks
```

## Known Bugs

| # | Severity | File | Line | Description |
|---|---|---|---|---|
| 1 | CRITICAL | app.py | 82-86 | `agent_mgr.build()` never called on auto-connect |
| 2 | CRITICAL | llm_provider.py | 157 | Ollama model existence not verified |
| 3 | HIGH | agent.py | 135 | `filter_by_rating` tool is a no-op |
| 4 | HIGH | app.py | 785 | KG+FAISS never used without AI checkbox |
| 5 | MEDIUM | llm_provider.py | 32 | gemma models listed but don't support tool calling |
| 6 | LOW | llm_provider.py | 159 | Ollama connection timeout too short (5s) |
"""
    with open("agent_architecture.md", "w", encoding="utf-8") as f:
        f.write(doc)
    print("\n  Saved → agent_architecture.md")


if __name__ == "__main__":
    llm       = _connect_llm()
    agent_mgr = _build_agent(llm)
    graph     = _print_mermaid(agent_mgr)

    if graph:
        _print_ascii(graph)
        _save_png(graph)

    _print_message_flow()
    _write_architecture_doc()

    print("\n✅  Done. Files written:")
    print("    agent_graph.mmd        — Mermaid source")
    print("    agent_graph.png        — Visual graph (if playwright installed)")
    print("    agent_architecture.md  — Full architecture doc\n")
