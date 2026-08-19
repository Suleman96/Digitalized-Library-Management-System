# Iqra Digital Library

> **مكتبة إقرأ الرقمية**
> Hybrid-retrieval book discovery: BM25 + dense vectors + a knowledge graph, an advanced RAG pipeline, and a LangGraph concierge agent — behind a typed HTTP API.

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)
![FAISS](https://img.shields.io/badge/FAISS-IndexFlatIP-F59E0B)
![LangGraph](https://img.shields.io/badge/LangGraph-ReAct-1C3C3C)
![Tests](https://img.shields.io/badge/Tests-110%20passing-22C55E)
![License](https://img.shields.io/badge/License-MIT-6366F1)

---

## What this is

A book discovery system over ~6,800 titles that combines three independent retrieval channels and layers optional LLM-driven query expansion and re-ranking on top. It is built to demonstrate production RAG architecture, not to be a toy semantic search demo.

**Measured on the live API** (6,810 books, local CPU):

| | |
| --- | --- |
| Hybrid query latency | **71 ms** (BM25 + FAISS + graph) |
| Knowledge graph | **6,810** nodes, **69,116** edges |
| Vector index | FAISS `IndexFlatIP`, 384-dim, exact search |
| Cold engine build | ~120 s (pre-baked into the container image for deploys) |

---

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│  apps/web/          Next.js 15 · TypeScript · Tailwind       │
│                     types generated from the OpenAPI schema   │
└───────────────────────────┬──────────────────────────────────┘
                            │  JSON / SSE
┌───────────────────────────▼──────────────────────────────────┐
│  apps/api/          FastAPI — routers, Pydantic schemas       │
│    routers/         search · books · reading-list ·           │
│                     analytics · agent · llm                   │
│    deps.py          engine lifecycle (lifespan singletons)    │
│    schemas.py       the contract — OpenAPI source of truth    │
└───────────────────────────┬──────────────────────────────────┘
                            │
┌───────────────────────────▼──────────────────────────────────┐
│  apps/api/core/     framework-agnostic retrieval engine       │
│                                                               │
│    hybrid_retriever  BM25 (40%) + FAISS (60%) + NetworkX KG   │
│    rag_pipeline      HyDE · multi-query RRF · cross-encoder   │
│    agent + agents/   LangGraph supervisor → Search / Curator  │
│    llm_provider      Claude · OpenAI · Gemini · Groq · Ollama │
│    recommender       Google Books + OpenLibrary clients       │
│    manager           CSV ↔ FAISS lifecycle                    │
│    analytics         catalogue statistics as series data      │
└──────────────────────────────────────────────────────────────┘
```

The `core/` package knows nothing about HTTP. The routers are the only framework-aware layer, and the engine returns plain Python values — never rendered markup.

---

## The retrieval pipeline

```
query
  │
  ├─ [expand]   AI query expansion            (optional, LLM)
  ├─ [expand]   HyDE — hypothetical doc       (optional, LLM)
  ├─ [expand]   multi-query — 3 variants      (optional, LLM)
  │
  ├─ [retrieve] BM25Okapi        ─┐
  │             FAISS cosine      ├─ min-max fusion → 40/60 weighted
  │             knowledge graph  ─┘
  │
  ├─ [fuse]     Reciprocal Rank Fusion, k=60  (when >1 query)
  │
  └─ [rerank]   cross-encoder/ms-marco-MiniLM-L-6-v2  (optional)
```

Every stage degrades gracefully: if the LLM is off or a package is missing, the pipeline falls back to plain hybrid search rather than raising. Each search returns a **`trace`** object recording which stages ran, how many candidates each saw, and how long each took.

For a full assessment of these techniques against current practice, see **[docs/rag-assessment.html](./docs/rag-assessment.html)**.

---

## Quick start

```bash
git clone https://github.com/Suleman96/Digitalized-Library-Management-System.git
cd Digitalized-Library-Management-System

python -m venv .venv
.venv\Scripts\activate        # Windows
source .venv/bin/activate     # macOS / Linux

pip install -r requirements.txt
cp .env.example .env          # optional — all keys are optional

uvicorn apps.api.main:app --reload --port 8000
```

- **API docs** → <http://localhost:8000/docs>
- **Health** → <http://localhost:8000/api/health>
- **OpenAPI schema** → <http://localhost:8000/openapi.json>

The first boot builds the FAISS index and knowledge graph (~2 minutes) and caches both to `artifacts/`. Subsequent boots load from cache.

---

## API

| Route | | Returns |
| --- | --- | --- |
| `/api/search` | `POST` | `{ local, external, trace, expandedQuery }` |
| `/api/books` | `GET` | Paginated catalogue with filters |
| `/api/books` | `POST` | Add a book; rebuilds the index |
| `/api/books/{id}` | `GET` | One book by deterministic id |
| `/api/books/{id}` | `DELETE` | Remove a book; rebuilds the index |
| `/api/books/{id}/similar` | `GET` | Semantically closest titles |
| `/api/explain` | `POST` | LLM explanation of why a book matched |
| `/api/agent/chat` | `POST` | **SSE stream** — `token`, `tool_call`, `tool_result`, `done` |
| `/api/agent/thread/{id}` | `DELETE` | Drop a conversation thread |
| `/api/reading-list` | `GET` `POST` `DELETE` | Saved books |
| `/api/reading-list/{id}` | `DELETE` | Remove one saved book |
| `/api/reading-list/export` | `POST` | PDF download |
| `/api/analytics` | `GET` | Rating, category, and year series |
| `/api/llm/providers` | `GET` | Providers, models, key availability |
| `/api/llm/connect` | `POST` | Connect a provider (supports bring-your-own-key) |
| `/api/llm/status` | `GET` | Connection state and capabilities |
| `/api/health` | `GET` | Readiness, book count, version |

Books carry a deterministic `id` — `sha1(title::first_author)[:16]` — so the frontend can route to `/book/[id]` and key lists safely.

---

## AI providers

All optional. Without one, hybrid retrieval, browsing, analytics, and the reading list all work fully; only HyDE, multi-query, query expansion, explanations, and the concierge agent require a connected provider.

| Provider | Key | Notes |
| --- | --- | --- |
| **Groq** | `GROQ_API_KEY` | Free tier, fastest — the recommended public default |
| **Claude** | `ANTHROPIC_API_KEY` | Best reasoning for the agent |
| **OpenAI** | `OPENAI_API_KEY` | |
| **Gemini** | `GEMINI_API_KEY` | |
| **Ollama** | *none* | Fully local and free — `ollama pull llama3.2` |

Set `LLM_PROVIDER` and `LLM_MODEL` to auto-connect at boot.

---

## Testing

```bash
pytest tests/ -v
pytest tests/ --cov=apps --cov-report=term-missing
```

| Module | Tests | Covers |
| --- | --- | --- |
| `test_api_contract.py` | 22 | Every route's response shape; OpenAPI generation |
| `test_rag_pipeline.py` | 31 | HyDE, multi-query, RRF, re-ranking, trace, degradation |
| `test_manager.py` | 18 | CSV CRUD, FAISS rebuild |
| `test_hybrid_retriever.py` | 18 | Fusion, graph, fallbacks |
| `test_recommender.py` | 13 | Normalisation, stable ids, external clients |
| `test_config.py` | 8 | Settings and env resolution |
| **Total** | **110** | |

Contract tests run against a stubbed engine — no model loading, no network, no FAISS index.

---

## Documentation

| Document | |
| --- | --- |
| [docs/rag-assessment.html](./docs/rag-assessment.html) | RAG techniques audited against current practice, with gaps and trade-offs · [PDF](./docs/rag-assessment.pdf) |
| [docs/migration-v3.html](./docs/migration-v3.html) | The v2 → v3 migration plan and its rationale · [PDF](./docs/migration-v3.pdf) |
| [docs/system-architecture.html](./docs/system-architecture.html) | System architecture with data-flow diagrams |
| [docs/design-decisions.html](./docs/design-decisions.html) | Design decisions: rationale, alternatives, trade-offs |
| [docs/business-impact.html](./docs/business-impact.html) | Business case and cost analysis |

---

## Project layout

```
apps/
  api/
    main.py            FastAPI app, CORS, rate limiting
    deps.py            engine lifecycle
    schemas.py         Pydantic contract
    routers/           one module per resource
    core/              retrieval engine (no HTTP awareness)
      agents/          SearchWorker, CuratorWorker
  web/                 Next.js frontend (in progress)

data/books.csv         catalogue (~6,800 books)
artifacts/             FAISS index, metadata, graph cache (gitignored)
tests/                 110 tests
docs/                  architecture and assessment documents (HTML + PDF)
```

---

## License

MIT © 2025 [DiploTech Solutions](https://diplotech-solutions.com)
