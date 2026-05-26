# Iqra Digital Library — Architecture v2

> **Who this is for:** developers, business owners, and anyone curious about how the system works.  
> It is written to be understood without needing a CS degree, while still being precise enough for engineers.

---

## 1. What Changed from v1 to v2

| Feature | v1 | v2 |
|---|---|---|
| Book search | FAISS semantic only | **Hybrid: BM25 keyword + FAISS semantic** |
| AI integration | None | Claude / OpenAI / Gemini / Ollama — user's choice |
| Conversational assistant | None | **LangGraph ReAct agent with memory** |
| Reading list | None | **JSON-backed bookmarks with PDF export** |
| Analytics | None | **Rating histogram, category chart, year trend** |
| PDF export | None | **fpdf2-powered export of results or reading list** |
| Query enhancement | None | **AI-powered query expansion** |
| CI/CD | None | **GitHub Actions pytest on every push** |

---

## 2. The Big Picture

```
User's Browser
     │
     ▼
┌─────────────────────────────────────────────────────────────────┐
│  Gradio UI (app.py)                                             │
│  ┌──────────┐ ┌────────────┐ ┌──────────┐ ┌────────────────┐  │
│  │ Recommend│ │AI Librarian│ │Analytics │ │ Reading List   │  │
│  └────┬─────┘ └─────┬──────┘ └────┬─────┘ └───────┬────────┘  │
└───────┼─────────────┼─────────────┼────────────────┼───────────┘
        │             │             │                │
        ▼             ▼             │                ▼
┌───────────────┐ ┌───────────┐    │        ┌───────────────┐
│ HybridRet +   │ │LibraryAgt │    │        │ ReadingList   │
│ BookRecommend │ │(LangGraph)│    │        │ (JSON file)   │
└───────┬───────┘ └─────┬─────┘    │        └───────────────┘
        │               │          │
        ▼               ▼          ▼
┌───────────────────────────────────────────────────────────────┐
│  Data Layer                                                   │
│  FAISS index (.faiss) ─ Metadata pickle (.pkl) ─ CSV (.csv)  │
│  Reading list JSON ─ Exported PDFs (artifacts/)              │
└───────────────────────────────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────┐
│  External APIs                │
│  Google Books API             │
│  Claude / OpenAI / Gemini /   │
│  Ollama (when AI is on)       │
└───────────────────────────────┘
```

---

## 3. Core Concept: RAG (Retrieval-Augmented Generation)

RAG is the most important idea in this system. Here is what it means in plain English:

> **Instead of asking an AI to answer from memory, we first retrieve relevant documents, then hand them to the AI as context.**

In Iqra, this works like this:

```
User query: "A gripping mystery set in the Middle East"
     │
     ├─ [RETRIEVE] Hybrid search finds the 10 most relevant books
     │     └─ BM25 matches keywords ("mystery", "Middle East")
     │     └─ FAISS matches meaning ("Cairo thriller", "Arab detective")
     │
     ├─ [AUGMENT] Top results are formatted and given to the AI agent
     │
     └─ [GENERATE] AI synthesises an answer:
           "Based on your local library, here are my top picks:
            1. **The Cairo Affair** by Olen Steinhauer…"
```

Without RAG, the AI would answer purely from its training data. With RAG, it answers based on *your actual library*, which may include books not in its training data.

---

## 4. File-by-File Breakdown

### `config.py` — The Settings Hub

**What it does:** A single frozen dataclass (`Settings`) that defines every path, API key, and option list. Everything else imports from here.

**Why frozen?** A frozen dataclass raises `FrozenInstanceError` if any code tries to change a setting at runtime. This prevents accidental config mutations.

**Key patterns:**
```python
@dataclass(frozen=True)
class Settings:
    @property
    def csv_path(self) -> Path:
        # Falls back to legacy location if primary not found
        ...
```

The `google_api_key` property checks three places in priority order:
1. Environment variable `GOOGLE_API_KEY`
2. `.env` file (loaded by `python-dotenv`)
3. `API.txt` file in the project root

---

### `manager.py` — The Catalogue Manager

**What it does:** Owns the local book collection: CSV on disk, FAISS index in memory, metadata pickle.

**Why three storage formats?**

| Format | Purpose | Who reads it |
|---|---|---|
| `books.csv` | Human-readable source of truth | pandas, admins |
| `book_index.faiss` | Fast vector search | FAISS, LangChain |
| `books_metadata.pkl` | Metadata parallel to FAISS rows | recommender, hybrid retriever |

**Add/Remove flow:**
```
add_book(record)
  → append row to self.df
  → _rebuild_index()
      → embed all titles+descriptions with SentenceTransformer
      → build new IndexFlatIP
      → _persist()
          → write CSV
          → write pickle
          → write FAISS index
```

**Critical fix (v1 → v2):** The old code called `_load_or_build()` in `add_book()`, which immediately reloaded the CSV from disk *before* the new row was saved — silently discarding additions. v2 separates `_load_or_build()` (startup only) from `_rebuild_index()` (works on the in-memory DataFrame).

---

### `recommender.py` — The Search Engine

**What it does:** Semantic search over the FAISS index + Google Books API, with result normalisation and HTML rendering.

**How cosine similarity works (simple explanation):**

Imagine every book is represented as a point in a 384-dimensional space. The `all-MiniLM-L6-v2` model converts text (title + description) into these 384-number vectors. Books with similar *meaning* end up close together, regardless of exact word matches. When you search, your query is also embedded and we find the closest book vectors.

**The `_normalise()` method** converts any data source (local CSV dict or Google Books JSON) into the same schema, so the rest of the code treats all books the same way.

**XSS prevention:** Every piece of text that came from outside (CSV data, API responses) is passed through `html.escape()` before being inserted into HTML strings. This prevents cross-site scripting attacks.

---

### `hybrid_retriever.py` — BM25 + FAISS Fusion *(new in v2)*

**What it does:** Combines two complementary search strategies into one via LangChain's `EnsembleRetriever`.

**Why two search types?**

| Strategy | Strengths | Weaknesses |
|---|---|---|
| BM25 (keyword) | Exact matches, author names, ISBNs | Misses synonyms and paraphrases |
| FAISS (semantic) | Understands meaning, synonyms | Can miss rare exact terms |
| **Hybrid** | **Gets the best of both** | Slightly more complex |

**Weights:** BM25 = 40%, FAISS = 60%. Semantic understanding takes priority, but keywords still matter.

**Key design decision:** Rather than re-embedding all 6,810 books at startup (which takes ~60 seconds), we reuse the FAISS index already built by `DynamicBookManager`. We wrap it with LangChain's FAISS adapter by sharing the raw index object in memory.

```python
raw_index = faiss.read_index(str(index_path))  # reuse existing
lc_faiss = LangChainFAISS(
    embedding_function=embeddings,
    index=raw_index,          # same index, zero re-embedding
    docstore=InMemoryDocstore(docstore_dict),
    index_to_docstore_id=index_to_id,
)
```

**Graceful degradation:** If `langchain-community` or `rank_bm25` are not installed, `build()` catches `ImportError` and sets `is_ready = False`. The rest of the app falls back to the standard FAISS-only search.

---

### `llm_provider.py` — AI Provider Abstraction *(new in v2)*

**What it does:** A single class (`LLMProvider`) that connects to Claude, OpenAI, Gemini, or Ollama — whichever the user picks. The rest of the app never talks to the provider directly.

**Why abstract it?**

Without abstraction, every feature (query expansion, explain match, agent) would need four separate code paths. With `LLMProvider`, they all call `llm._call(prompt)` and the correct API is used transparently.

**Two modes:**
1. **Direct calls** (`expand_query`, `explain_match`) — simple prompt → response, no history
2. **LangChain LLM** (`get_langchain_llm`) — returns a LangChain chat model for the agent

**Never raises:** All API calls are wrapped in try/except. Failures return empty strings and log warnings. The app continues working without AI.

---

### `agent.py` — The Conversational Library Agent *(new in v2)*

**What it does:** A LangGraph ReAct agent that can carry on a multi-turn conversation about books, using tools to search, filter, and save.

**ReAct loop (Reason + Act):**

```
User: "Find me a thriller about hacking"
Agent thinks: "I should search the local library"
Agent acts:   search_local_library("thriller about hacking")
Agent observes: "1. **Zero Day** by Mark Russinovich…"
Agent thinks: "I have good results, I'll present them"
Agent responds: "Here are some hacking thrillers in your library…"
```

**Why LangGraph over a simple chat loop?**

LangGraph maintains a conversation graph with state. Each turn appends to the message history. `MemorySaver` persists this state in memory, keyed by `thread_id`. This means:
- Each browser session gets a unique `thread_id`
- The agent remembers the last 10 messages
- Multiple users can chat simultaneously without sharing history

**The 5 tools:**

| Tool | What it does |
|---|---|
| `search_local_library` | BM25+FAISS hybrid search, or FAISS fallback |
| `search_google_books` | Live Google Books API search |
| `find_similar_books` | Semantic similarity by title |
| `save_to_reading_list` | Bookmarks a book by title |
| `filter_by_rating` | Instructs the agent to prefer higher-rated books |

---

### `reading_list.py` — Bookmarks *(new in v2)*

**What it does:** Stores a list of books the user wants to remember, in a human-readable JSON file at `data/reading_list.json`.

**Why JSON instead of the CSV?** The reading list is personal and ephemeral. JSON is simpler to read/write atomically. The CSV is the authoritative catalogue — it should not be polluted with personal data.

**Example entry:**
```json
{
  "title": "The Cairo Affair",
  "authors": "Olen Steinhauer",
  "average_rating": 3.8,
  "source": "🌐 Google Books",
  "added_at": "2026-05-25T14:32:11"
}
```

---

### `exporter.py` — PDF Generation *(new in v2)*

**What it does:** Converts any list of book dicts into a styled PDF report using `fpdf2`.

**Why fpdf2?** It is pure Python (no external binaries needed), actively maintained, and already in `requirements.txt`. Alternatives like `reportlab` are heavier; `weasyprint` requires system libraries.

**`_safe_str()`:** Book titles can contain Arabic, Chinese, or emoji characters not supported by Helvetica (the built-in font). `_safe_str()` encodes to latin-1 with `replace` error handling, so the PDF always renders without crashing. A future improvement could add a Unicode font (e.g., NotoSans).

---

### `app.py` — The Gradio Application *(heavily expanded in v2)*

**What it does:** Wires the entire system together as an interactive web application.

**Startup sequence:**
```python
manager          = DynamicBookManager()    # loads CSV, builds FAISS
reco             = BookRecommender()       # loads FAISS, loads model
reading_list_mgr = ReadingList()           # loads JSON
hybrid_ret       = HybridRetriever()
hybrid_ret.build()                         # wraps FAISS with BM25
agent_mgr        = LibraryAgent(...)       # ready, but agent not built yet
# agent only builds when user clicks "Connect" in the UI
```

**State management:** Gradio functions are stateless by design. `gr.State` components hold data between events:
- `results_state`: the last search results (list of dicts) — used by Save/Explain/Export buttons
- `thread_id_state`: unique UUID per session — used by the agent's memory

**`_do_recommend()` return signature:**
```python
def _do_recommend(...) -> tuple[str, gr.update, list]:
    #                              ↑ HTML  ↑ dropdown  ↑ state
```
All three outputs update simultaneously when the search button is clicked.

---

## 5. Data Flow: End-to-End Search

```
1. User types "Egyptian mythology fiction"
         ↓
2. [If AI on] llm.expand_query() adds synonyms:
   "Egyptian mythology fiction ancient gods Ra Osiris fantasy novel"
         ↓
3. reco.recommend() runs in parallel:
   ├── _search_local():   FAISS cosine similarity → top 25 local books
   └── _search_external(): Google Books API → top 25 online books
         ↓
4. [If AI on and hybrid ready] hybrid_ret.search():
   ├── BM25Retriever ranks by keyword overlap
   └── FAISS retriever ranks by meaning
   └── EnsembleRetriever merges (40% BM25 + 60% FAISS)
         ↓
5. Rating filter applied (if min_rating > 0)
         ↓
6. Sort by Rating / Similarity / Year
         ↓
7. reco.format_books() renders HTML book cards
         ↓
8. UI updates: results HTML + book selector dropdown + results state
```

---

## 6. Embedding Model: all-MiniLM-L6-v2

This is the AI model at the heart of the search system.

- **Size:** 22 MB (very small — no GPU needed)
- **Output:** 384-dimensional float32 vector per input text
- **Training:** Distilled from larger models on 1 billion sentence pairs
- **Speed:** ~1000 sentences/second on CPU

**Why L2-normalise?** After normalisation, cosine similarity equals inner product. `IndexFlatIP` (inner product) then computes cosine similarities directly — the highest scores are the most semantically similar books.

---

## 7. Security Considerations

| Risk | Mitigation |
|---|---|
| XSS from book data | `html.escape()` on all external strings before HTML insertion |
| API key leakage | Keys in `.env` (git-ignored); try/except wraps all key access |
| ISBN injection | Validated character-by-character before writing to CSV |
| Path traversal in PDF | Output always written to `artifacts/` subdirectory |
| Prompt injection via book descriptions | Agent system prompt is hardcoded; book data passed as tool output (not as instructions) |

---

## 8. Performance Characteristics

| Operation | Time (CPU, 6810 books) | Notes |
|---|---|---|
| Cold startup | ~15s | Model download cached after first run |
| Warm startup | ~4s | Model weights cached by sentence_transformers |
| FAISS index rebuild | ~3s | Called after add/remove book |
| Hybrid retriever build | ~2s | Reads existing FAISS; no re-embedding |
| Semantic search (local) | <50ms | FAISS in-memory inner product |
| Google Books search | 0.5–2s | Network latency |
| PDF export (100 books) | <1s | Pure Python, no rendering |
| AI query expand | 0.5–3s | Depends on provider and model |

---

## 9. How to Add a New AI Provider

1. Add the provider name to `PROVIDER_MODELS` in `llm_provider.py`
2. Add a `_connect_<provider>()` method (see `_connect_claude` as template)
3. Add the `if self._provider == "<provider>"` branch in `_call()`
4. Add the `get_langchain_llm()` branch for agent support
5. Add the optional package to `requirements.txt` (commented out)
6. Update `.env.example` with the new key name

---

## 10. Testing Strategy

Tests live in `tests/` and run with `pytest`:

```bash
pytest tests/ -v --cov=. --cov-report=term-missing
```

| Test file | What it covers |
|---|---|
| `test_config.py` | Settings paths, fallbacks, env vars |
| `test_manager.py` | add_book, remove_book, CSV/FAISS lifecycle |
| `test_recommender.py` | _normalise, _safe_float, _safe_int, _render_card |
| `test_hybrid_retriever.py` | Build/reload/search interface, graceful degradation |

**GitHub Actions** runs the full suite on every push to `main` — see `.github/workflows/tests.yml`.

---

## 11. Deployment Checklist

- [ ] Copy `.env.example` → `.env` and fill in `GOOGLE_API_KEY`
- [ ] (Optional) Add `ANTHROPIC_API_KEY` for Claude
- [ ] Run `pip install -r requirements.txt`
- [ ] Run `python app.py` — it creates `data/` and `artifacts/` automatically
- [ ] For public sharing: set `GRADIO_SHARE=true` in `.env`
- [ ] For production: set `SERVER_HOST=0.0.0.0` and `SERVER_PORT=7860`

---

## 12. Glossary

| Term | Plain English |
|---|---|
| **RAG** | Look up relevant documents first, then ask the AI to answer using them |
| **FAISS** | Facebook's library for finding similar vectors very fast |
| **BM25** | A classic keyword search algorithm used in Elasticsearch and search engines |
| **Embedding** | Converting text into a list of numbers that capture its meaning |
| **Cosine similarity** | How similar two vectors are, on a scale of 0 (unrelated) to 1 (identical) |
| **LangChain** | A framework for building apps powered by language models |
| **LangGraph** | A framework for building stateful, multi-step AI agents |
| **ReAct** | Agent strategy: Reason → Act (call a tool) → Observe result → repeat |
| **EnsembleRetriever** | LangChain component that combines multiple search algorithms |
| **MemorySaver** | LangGraph component that saves conversation history per session |
| **Gradio** | Python library for building interactive ML web apps without frontend code |
| **FAISS IndexFlatIP** | Exact inner-product search — finds vectors with highest dot product |

---

*Document version: 2.0 — Iqra Digital Library — DiploTech Solutions*
