# =============================================================================
# test_api_contract.py — Iqra Digital Library v3
# =============================================================================
# Contract tests for the FastAPI layer.
#
# These run against a stubbed engine, so they are fast and deterministic: no
# model loading, no FAISS index, no network.  They assert the *shape* of every
# response, which is what the generated TypeScript types depend on.
# =============================================================================

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from apps.api import deps
from apps.api.core.rag_pipeline import PipelineTrace as CoreTrace
from apps.api.core.rag_pipeline import StageTrace


def _fake_book(title: str = "Test Book", **overrides) -> dict:
    book = {
        "id": "abc123def456789a",
        "title": title,
        "authors": "Test Author",
        "subtitle": "",
        "description": "A book about testing.",
        "thumbnail": "https://example.com/cover.jpg",
        "average_rating": 4.2,
        "ratings_count": 100,
        "info_link": "https://example.com",
        "language": "en",
        "published_year": "2020",
        "num_pages": 300,
        "categories": "Fiction",
        "source": "Local Library",
        "similarity": 0.87,
    }
    book.update(overrides)
    return book


@pytest.fixture
def client(monkeypatch):
    """A TestClient backed by a fully stubbed engine."""
    llm = MagicMock()
    llm.is_enabled = False
    llm.status = "Not connected"
    llm._provider = ""
    llm._model = ""

    retriever = MagicMock()
    retriever.is_ready = True
    retriever.search.return_value = [_fake_book(f"Book {i}") for i in range(5)]

    pipeline = MagicMock()
    pipeline.is_ready = True
    pipeline.search.return_value = (
        [_fake_book("RAG Book")],
        CoreTrace(
            original_query="q",
            stages=[StageTrace(name="hybrid_retrieve", candidates=5, duration_ms=12.3)],
            total_ms=12.3,
        ),
    )

    recommender = MagicMock()
    recommender.recommend.return_value = (
        [],
        [_fake_book("External Book", source="Google Books")],
    )

    reading_list = MagicMock()
    reading_list.get_all.return_value = [_fake_book("Saved Book")]
    reading_list.count = 1
    reading_list.add.return_value = "Added to your reading list."
    reading_list.remove.return_value = "Removed from reading list."

    agent = MagicMock()
    agent.is_ready = False

    manager = MagicMock()
    manager.book_count = 6810

    engine = deps.Engine(
        manager=manager,
        recommender=recommender,
        reading_list=reading_list,
        retriever=retriever,
        pipeline=pipeline,
        llm=llm,
        agent=agent,
        ready=True,
    )

    monkeypatch.setattr(deps, "_engine", engine)
    monkeypatch.setattr(deps, "build_engine", lambda: engine)

    from apps.api.main import app

    app.dependency_overrides[deps.get_engine] = lambda: engine
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
class TestHealth:
    def test_health_returns_expected_shape(self, client):
        r = client.get("/api/health")
        assert r.status_code == 200
        assert set(r.json()) == {
            "status",
            "indexReady",
            "agentReady",
            "llmConnected",
            "bookCount",
            "version",
        }

    def test_root_advertises_docs(self, client):
        assert client.get("/").json()["docs"] == "/docs"


# ---------------------------------------------------------------------------
class TestSearch:
    def test_search_returns_local_external_and_trace(self, client):
        r = client.post("/api/search", json={"query": "mystery novels"})
        assert r.status_code == 200
        assert set(r.json()) == {"local", "external", "trace", "expandedQuery"}

    def test_search_rejects_empty_query(self, client):
        assert client.post("/api/search", json={"query": ""}).status_code == 422

    def test_search_rejects_oversized_limits(self, client):
        r = client.post("/api/search", json={"query": "x", "localLimit": 999})
        assert r.status_code == 422

    def test_every_book_carries_an_id(self, client):
        body = client.post("/api/search", json={"query": "mystery"}).json()
        for book in body["local"] + body["external"]:
            assert book["id"], "frontend routes and React keys depend on this"

    def test_trace_shape_matches_schema(self, client):
        trace = client.post("/api/search", json={"query": "mystery"}).json()["trace"]
        assert set(trace) == {
            "originalQuery",
            "hydeDocument",
            "queryVariants",
            "stages",
            "totalMs",
        }

    def test_no_html_leaks_into_the_payload(self, client):
        """v3 contract: the API returns data, the frontend renders it."""
        raw = client.post("/api/search", json={"query": "mystery"}).text
        assert "<div" not in raw
        assert "book-card" not in raw


# ---------------------------------------------------------------------------
class TestReadingList:
    def test_get_returns_a_list_of_books(self, client):
        r = client.get("/api/reading-list")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_save_requires_a_title(self, client):
        r = client.post("/api/reading-list", json={"book": {"title": ""}})
        assert r.status_code == 422

    def test_save_assigns_an_id_when_missing(self, client):
        r = client.post(
            "/api/reading-list", json={"book": {"title": "New", "authors": "A"}}
        )
        assert r.status_code == 201

    def test_clear_returns_204(self, client):
        assert client.delete("/api/reading-list").status_code == 204


# ---------------------------------------------------------------------------
class TestLLM:
    def test_providers_lists_all_backends(self, client):
        names = {p["provider"] for p in client.get("/api/llm/providers").json()}
        assert {"claude", "openai", "gemini", "groq", "ollama"} <= names

    def test_provider_entries_report_key_availability(self, client):
        for p in client.get("/api/llm/providers").json():
            assert set(p) == {"provider", "models", "requiresKey", "keyConfigured"}

    def test_status_shape(self, client):
        assert set(client.get("/api/llm/status").json()) == {
            "connected",
            "provider",
            "model",
            "message",
            "capabilities",
        }

    def test_connect_rejects_unknown_provider(self, client):
        r = client.post("/api/llm/connect", json={"provider": "nope", "model": "x"})
        assert r.status_code == 422

    def test_connect_rejects_model_not_in_catalogue(self, client):
        r = client.post("/api/llm/connect", json={"provider": "claude", "model": "gpt-4o"})
        assert r.status_code == 422


# ---------------------------------------------------------------------------
class TestAgent:
    def test_chat_409s_when_agent_not_built(self, client):
        r = client.post("/api/agent/chat", json={"message": "hi", "threadId": "t1"})
        assert r.status_code == 409

    def test_clear_thread_returns_204(self, client):
        assert client.delete("/api/agent/thread/t1").status_code == 204


# ---------------------------------------------------------------------------
class TestExplain:
    def test_explain_409s_without_a_connected_provider(self, client):
        r = client.post("/api/explain", json={"query": "q", "bookId": "abc"})
        assert r.status_code == 409


# ---------------------------------------------------------------------------
class TestOpenAPI:
    def test_schema_generates(self, client):
        """gen:types reads this; if it breaks, the frontend loses its types."""
        schema = client.get("/openapi.json").json()
        assert schema["info"]["title"] == "Iqra Digital Library API"

    def test_core_models_are_exported(self, client):
        schemas = client.get("/openapi.json").json()["components"]["schemas"]
        assert {"Book", "SearchRequest", "SearchResponse", "PipelineTrace"} <= set(schemas)
