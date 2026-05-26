# =============================================================================
# tests/test_recommender.py — Iqra Digital Library
# =============================================================================
# Unit tests for BookRecommender.
# External API calls are mocked so tests run offline.
# Run:  pytest tests/test_recommender.py -v
# =============================================================================

from __future__ import annotations

import pickle
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock, patch

import faiss
import numpy as np
import pytest


# ---------------------------------------------------------------------------
# Helpers to build minimal test data
# ---------------------------------------------------------------------------
def _fake_book(title: str = "Fake Book") -> dict[str, Any]:
    return {
        "title":          title,
        "authors":        "Author Name",
        "subtitle":       "",
        "description":    f"Description of {title}.",
        "thumbnail":      "",
        "average_rating": 4.2,
        "ratings_count":  500,
        "info_link":      "https://example.com",
        "language":       "en",
        "published_year": "2022",
        "num_pages":      250,
    }


def _build_index(dim: int = 384, n: int = 3) -> faiss.Index:
    index = faiss.IndexFlatIP(dim)
    vecs  = np.random.randn(n, dim).astype(np.float32)
    norms = np.linalg.norm(vecs, axis=1, keepdims=True)
    index.add(vecs / norms)
    return index


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def recommender(tmp_path: Path):
    """Return a BookRecommender backed by ephemeral test data."""
    dim     = 384
    n_books = 3
    index   = _build_index(dim, n_books)
    meta    = [_fake_book(f"Book {i}") for i in range(n_books)]

    index_path = tmp_path / "book_index.faiss"
    meta_path  = tmp_path / "books_metadata.pkl"
    faiss.write_index(index, str(index_path))
    with open(meta_path, "wb") as fh:
        pickle.dump(meta, fh)

    # SimpleNamespace avoids FrozenInstanceError from frozen Settings dataclass.
    fake_settings = SimpleNamespace(
        index_path   = index_path,
        meta_path    = meta_path,
        languages    = {"Any": "", "English": "en", "Arabic": "ar"},
        google_api_key = "dummy-key",
    )

    with patch("recommender.settings", fake_settings):
        from recommender import BookRecommender
        rec = BookRecommender()
        yield rec


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
class TestBookRecommender:

    def test_local_search_returns_results(self, recommender) -> None:
        local, ext = recommender.recommend(
            "fiction adventure", "Any", 3, 0, 0.0, "Local Only", "Rating"
        )
        assert isinstance(local, list)
        assert len(local) <= 3

    def test_external_search_mocked(self, recommender) -> None:
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "items": [
                {"volumeInfo": {
                    "title": "External Book",
                    "authors": ["External Author"],
                    "description": "External description.",
                    "averageRating": 3.5,
                    "ratingsCount": 200,
                    "language": "en",
                    "publishedDate": "2021",
                    "pageCount": 180,
                    "imageLinks": {"thumbnail": "https://example.com/cover.jpg"},
                    "infoLink": "https://books.google.com/test",
                }}
            ]
        }
        with patch("recommender.requests.get", return_value=mock_response):
            local, ext = recommender.recommend(
                "fiction", "Any", 0, 3, 0.0, "External Only", "Similarity"
            )
        assert isinstance(ext, list)
        assert len(ext) >= 1
        assert ext[0]["title"] == "External Book"

    def test_min_rating_filter(self, recommender) -> None:
        """When threshold is achievable, results meet it; otherwise falls back gracefully."""
        # Test books all have rating 4.2 — an impossible threshold (5.0) triggers fallback
        local_fallback, _ = recommender.recommend(
            "test query", "Any", 3, 0, 5.0, "Local Only", "Rating"
        )
        assert isinstance(local_fallback, list)  # fallback: returns best available

        # Achievable threshold: all returned books must meet it
        local_ok, _ = recommender.recommend(
            "test query", "Any", 3, 0, 4.0, "Local Only", "Rating"
        )
        for book in local_ok:
            assert book["average_rating"] >= 4.0

    def test_sort_by_similarity(self, recommender) -> None:
        local, _ = recommender.recommend(
            "adventure", "Any", 3, 0, 0.0, "Local Only", "Similarity"
        )
        if len(local) > 1:
            sims = [b["similarity"] for b in local]
            assert sims == sorted(sims, reverse=True)

    def test_format_books_returns_html(self, recommender) -> None:
        local, ext = recommender.recommend(
            "test", "Any", 2, 0, 0.0, "Local Only", "Rating"
        )
        html = recommender.format_books(local, ext)
        assert "<div" in html
        assert "results-root" in html

    def test_format_books_empty_shows_no_results(self, recommender) -> None:
        html = recommender.format_books([], [])
        assert "No results found" in html

    def test_normalise_handles_missing_fields(self, recommender) -> None:
        raw    = {}
        result = recommender._normalise(raw, "Test")
        assert result["title"]          == "Unknown Title"
        assert result["authors"]        == "Unknown Author"
        assert result["average_rating"] == 0.0

    def test_card_renders_title(self, recommender) -> None:
        book = recommender._normalise(_fake_book("My Title"), "Test")
        card = recommender._render_card(book)
        assert "My Title" in card
