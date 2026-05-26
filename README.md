# Iqra Digital Library — v2

> **مكتبة إقرأ الرقمية**
> Production-grade RAG-powered digital library with advanced semantic search, multi-provider AI, and a LangGraph conversational agent.

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![Gradio](https://img.shields.io/badge/Gradio-4.x-FF7C00)
![FAISS](https://img.shields.io/badge/FAISS-CPU-F59E0B)
![Tests](https://img.shields.io/badge/Tests-81%20passing-22C55E)
![License](https://img.shields.io/badge/License-MIT-6366F1)

---

## Documentation

| Document | Description |
| -------- | ----------- |
| [docs/system-architecture.html](./docs/system-architecture.html) | System architecture — v1 and v2 with data-flow diagrams |
| [docs/design-decisions.html](./docs/design-decisions.html) | Every design decision: rationale, alternatives, trade-offs |
| [docs/business-impact.html](./docs/business-impact.html) | Business case, cost analysis, ROI, competitive positioning |

---

## What's New in v2

| Area | v1 | v2 |
| ---- | -- | -- |
| **Search** | FAISS cosine only | Hybrid BM25 (40%) + FAISS (60%) with min-max fusion |
| **RAG pipeline** | None | HyDE · Multi-query + RRF · Cross-encoder re-ranking |
| **AI providers** | None | Claude · OpenAI · Gemini · Ollama (free, local) |
| **Agent** | None | LangGraph ReAct agent with 5 tools + conversation memory |
| **Reading list** | None | Per-session save / remove / export |
| **Analytics** | None | Search history, export to PDF / CSV / JSON |
| **Tests** | 56 | 81 (25 new RAG pipeline tests) |

---

## Features

| Feature | Description |
| ------- | ----------- |
| **Hybrid Search** | BM25 keyword + FAISS semantic, fused with weighted min-max normalisation |
| **HyDE** | LLM generates a hypothetical ideal book description; that text is embedded as the FAISS query vector |
| **Multi-Query RAG** | LLM produces 3 query variants; results merged via Reciprocal Rank Fusion (RRF) |
| **Cross-Encoder Re-ranking** | `ms-marco-MiniLM-L-6-v2` scores (query, book) pairs jointly for highest precision |
| **Google Books** | Simultaneous external search with semantic re-ranking |
| **Multi-Provider LLM** | Switch between Claude, OpenAI, Gemini, or local Ollama models at runtime |
| **LangGraph Agent** | Conversational assistant with search, recommend, reading-list, and explain tools |
| **Reading List** | Save books to a per-session list; export to PDF, CSV, or JSON |
| **Analytics** | Searchable history with one-click export |
| **Library Management** | Add / remove books; CSV and FAISS index updated atomically |
| **Browse & Filter** | Paginated catalogue with language, rating, and text filters |

---

## Project Structure

```text
Digitalized-Library-Management-System/
│
├── app.py                 ← Gradio UI entry point (5 tabs)
├── config.py              ← Settings dataclass, env var loading
├── manager.py             ← DynamicBookManager: CSV ↔ FAISS lifecycle
├── hybrid_retriever.py    ← BM25 + FAISS hybrid search with fusion
├── rag_pipeline.py        ← HyDE · Multi-query + RRF · Cross-encoder
├── llm_provider.py        ← Unified LLM interface (Claude/OpenAI/Gemini/Ollama)
├── agent.py               ← LangGraph ReAct conversational agent
├── recommender.py         ← HTML card renderer and Google Books client
├── reading_list.py        ← Per-session reading list with PDF/CSV/JSON export
├── exporter.py            ← Analytics export utilities
│
├── data/
│   └── books.csv          ← Local library dataset (~6 800 books)
│
├── artifacts/             ← Auto-generated on startup (gitignored)
│   ├── book_index.faiss   ← FAISS IndexFlatIP
│   └── books_metadata.pkl ← Metadata list parallel to FAISS rows
│
├── assets/
│   ├── logo.png
│   └── Diplotech_Logo_2.png
│
├── docs/
│   ├── architecture.html   ← System architecture (v1 + v2, versioned)
│   ├── decisions.html      ← Design decisions with alternatives
│   └── business-impact.html← Business case and ROI analysis
│
├── tests/
│   ├── test_config.py
│   ├── test_manager.py
│   ├── test_recommender.py
│   ├── test_hybrid_retriever.py
│   ├── test_rag_pipeline.py
│   └── test_llm_provider.py
│
├── archive/               ← Deprecated code (do not import)
├── .env.example           ← Copy to .env and fill in keys
├── .gitignore
└── requirements.txt
```

---

## Quick Start

### 1 — Clone

```bash
git clone <your-repo-url>
cd Digitalized-Library-Management-System
```

### 2 — Virtual environment

```bash
python -m venv .venv
.venv\Scripts\activate      # Windows
source .venv/bin/activate   # macOS / Linux
```

### 3 — Install dependencies

```bash
pip install -r requirements.txt
```

### 4 — Configure environment

```bash
cp .env.example .env
```

Edit `.env` and add your keys (all optional except `GOOGLE_API_KEY` for external search):

```env
# Required for Google Books external search
GOOGLE_API_KEY=your_key_here

# AI providers — add whichever you use; leave the rest blank
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=AI...

# Ollama — no key needed; runs locally (see below)
OLLAMA_HOST=http://localhost:11434   # default

# Server
SERVER_HOST=0.0.0.0
SERVER_PORT=7860
GRADIO_SHARE=false
```

### 5 — Run

```bash
python app.py
```

Open **<http://localhost:7860>** in your browser.

---

## Using Ollama (Free Local AI — No API Key)

Ollama runs LLMs on your machine. With an NVIDIA GPU (RTX 3060+) you get fast, free inference with no token costs.

### Install Ollama

Download from [ollama.com](https://ollama.com) and install.

### Pull a model

```bash
# Recommended — fast, instruction-tuned, only 2 GB
ollama pull llama3.2

# Alternatives already installed on this machine
# ollama pull qwen2.5:3b     # 1.9 GB — excellent structured output
# ollama pull qwen2.5:7b     # 4.7 GB — high quality
# ollama pull deepseek-r1:8b # 5.2 GB — strong reasoning
```

### Connect in the UI

1. Open the **AI Settings** panel in the app
2. Select provider: `ollama`
3. Select model: `llama3.2`
4. Click **Connect**

All RAG features (HyDE, multi-query, re-ranking explanations) will activate automatically.

---

## Architecture Overview

```text
┌─────────────────────────────────────────────────────────────────┐
│                         USER LAYER                              │
│       Browser  ──  HTTP :7860  ──  Gradio UI (app.py)          │
└──────────────────────────────┬──────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────┐
│                     APPLICATION LAYER                           │
│                                                                 │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────────┐   │
│  │  Gradio UI  │  │  LangGraph   │  │    BookRecommender   │   │
│  │  (app.py)   │  │  Agent       │  │    (recommender.py)  │   │
│  └──────┬──────┘  └──────┬───────┘  └──────────┬───────────┘   │
└─────────┼────────────────┼──────────────────────┼───────────────┘
          │                │                      │
┌─────────▼────────────────▼──────────────────────▼───────────────┐
│                      RAG PIPELINE LAYER                         │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  RAGPipeline (rag_pipeline.py)                          │    │
│  │                                                         │    │
│  │  Stage 1 — Query Expansion                              │    │
│  │    HyDE: LLM → hypothetical doc → embed as query        │    │
│  │    Multi-query: LLM → 3 variants → merge via RRF        │    │
│  │                                                         │    │
│  │  Stage 2 — Hybrid Retrieval                             │    │
│  │    BM25 (40%) + FAISS cosine (60%) → min-max fusion     │    │
│  │                                                         │    │
│  │  Stage 3 — Re-ranking                                   │    │
│  │    CrossEncoder ms-marco-MiniLM-L-6-v2                  │    │
│  └───────────────────────────────┬─────────────────────────┘    │
└───────────────────────────────────┼──────────────────────────────┘
                                   │
┌──────────────────────────────────▼──────────────────────────────┐
│                        DATA LAYER                               │
│                                                                 │
│   all-MiniLM-L6-v2 (384-dim)  ·  FAISS IndexFlatIP             │
│   BM25Okapi (rank_bm25)       ·  books.csv / books_metadata.pkl│
└──────────────────────────────────┬──────────────────────────────┘
                                   │
┌──────────────────────────────────▼──────────────────────────────┐
│                      EXTERNAL SERVICES                          │
│   Google Books API  ·  Anthropic  ·  OpenAI  ·  Gemini         │
│   Ollama (localhost — no internet required)                     │
└─────────────────────────────────────────────────────────────────┘
```

For full detail, see **[docs/architecture.html](./docs/architecture.html)**.

---

## RAG Pipeline Detail

Each stage is independent and falls back gracefully if the LLM is off or a package is missing.

### Stage 1 — Query Expansion

#### HyDE (Hypothetical Document Embeddings)

The LLM writes a 2-sentence description of the ideal book for the query. That text is embedded and used as the FAISS search vector instead of the raw query — it bridges the gap between short query language and rich document language.

#### Multi-Query RAG

The LLM produces 3 alternative phrasings of the query. Each is searched independently. Results from all queries are merged with **Reciprocal Rank Fusion**:

```text
score = Σ 1 / (rank + 60)   for each result list
```

Books appearing in multiple result sets get a boosted score; the constant `60` dampens rank differences at the top.

### Stage 2 — Hybrid Retrieval

```text
hybrid_score = 0.40 × norm(BM25) + 0.60 × norm(FAISS cosine)
```

Both scores are min-max normalised per query before combining, so neither scale dominates. BM25 catches exact keyword matches; FAISS catches semantic similarity.

### Stage 3 — Cross-Encoder Re-ranking

`cross-encoder/ms-marco-MiniLM-L-6-v2` sees `(query, title + description)` pairs jointly, producing a relevance score far more accurate than bi-encoder cosine similarity. The model is lazy-loaded on first use; if the package is missing the pipeline returns Stage 2 results unchanged.

---

## Configuration Reference

| Variable | Default | Description |
| -------- | ------- | ----------- |
| `GOOGLE_API_KEY` | *(optional)* | Google Books external search |
| `ANTHROPIC_API_KEY` | *(optional)* | Claude AI provider |
| `OPENAI_API_KEY` | *(optional)* | OpenAI provider |
| `GEMINI_API_KEY` | *(optional)* | Google Gemini provider |
| `OLLAMA_HOST` | `http://localhost:11434` | Ollama server address |
| `SERVER_HOST` | `0.0.0.0` | Gradio bind host |
| `SERVER_PORT` | `7860` | Gradio bind port |
| `GRADIO_SHARE` | `false` | `true` → public Gradio tunnel |

---

## Running Tests

```bash
# Install test dependencies (already in requirements.txt)
pip install pytest pytest-cov

# Run all 81 tests
pytest tests/ -v

# With coverage report
pytest tests/ --cov=. --cov-report=term-missing

# Run a specific module
pytest tests/test_rag_pipeline.py -v
```

### Test suite breakdown

| Module | Tests | What is covered |
| ------ | ----- | --------------- |
| `test_config.py` | 8 | Settings defaults and env var loading |
| `test_manager.py` | 18 | CSV CRUD, FAISS rebuild, edge cases |
| `test_recommender.py` | 15 | HTML card rendering, Google Books client |
| `test_hybrid_retriever.py` | 15 | BM25 + FAISS fusion, fallbacks |
| `test_rag_pipeline.py` | 25 | HyDE, multi-query, RRF, re-ranking, degradation |

---

## Server Deployment

```bash
export GOOGLE_API_KEY=<your_key>
export SERVER_HOST=0.0.0.0
export SERVER_PORT=7860

# Background process
nohup python app.py > app.log 2>&1 &
```

### Nginx reverse proxy

```nginx
server {
    listen 80;
    server_name library.yourdomain.com;
    location / {
        proxy_pass         http://127.0.0.1:7860;
        proxy_http_version 1.1;
        proxy_set_header   Upgrade    $http_upgrade;
        proxy_set_header   Connection "upgrade";
        proxy_set_header   Host       $host;
    }
}
```

### systemd service

```ini
[Unit]
Description=Iqra Digital Library v2
After=network.target

[Service]
WorkingDirectory=/opt/Digitalized-Library-Management-System
ExecStart=/opt/Digitalized-Library-Management-System/.venv/bin/python app.py
EnvironmentFile=/opt/Digitalized-Library-Management-System/.env
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable --now iqra-library
```

---

## Dependencies

| Package | Purpose |
| ------- | ------- |
| `gradio` | Web UI |
| `pandas` | CSV management |
| `numpy` | Embedding math |
| `faiss-cpu` | Nearest-neighbour vector search |
| `sentence-transformers` | `all-MiniLM-L6-v2` embedding + cross-encoder re-ranking |
| `rank_bm25` | BM25Okapi keyword retrieval |
| `langchain-core` | LangGraph agent framework |
| `langgraph` | ReAct agent with conversation memory |
| `anthropic` | Claude API client |
| `openai` | OpenAI API client |
| `google-generativeai` | Gemini API client |
| `requests` | Google Books API + Ollama HTTP client |
| `python-dotenv` | `.env` loading |
| `reportlab` | PDF export for reading list / analytics |

---

## License

MIT © 2025 [DiploTech Solutions](https://diplotech-solutions.com)

---

Built with DiploTech Solutions · Gradio · FAISS · BM25 · SentenceTransformers · LangGraph · Claude / OpenAI / Gemini / Ollama
