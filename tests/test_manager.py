# =============================================================================
# tests/test_manager.py — Iqra Digital Library
# =============================================================================
# Unit tests for DynamicBookManager.
# Uses pytest's tmp_path fixture so no test touches the real library.
# Run:  pytest tests/test_manager.py -v
# =============================================================================

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

import pandas as pd
import pytest


# ---------------------------------------------------------------------------
# Minimal valid book record
# ---------------------------------------------------------------------------
def _book(title: str = "Test Book", **overrides: Any) -> dict[str, Any]:
    base = {
        "isbn13":         "9781234567890",
        "isbn10":         "1234567890",
        "title":          title,
        "subtitle":       "",
        "authors":        "Test Author",
        "categories":     "Fiction",
        "thumbnail":      "",
        "description":    f"A description for {title}.",
        "published_year": 2024,
        "average_rating": 4.0,
        "num_pages":      300,
        "ratings_count":  100,
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def manager(tmp_path: Path):
    """Return a DynamicBookManager wired to a temporary directory."""
    data_dir     = tmp_path / "data"
    artifact_dir = tmp_path / "artifacts"
    data_dir.mkdir()
    artifact_dir.mkdir()

    # SimpleNamespace avoids FrozenInstanceError from frozen Settings dataclass.
    # We replace the module-level 'settings' in manager.py with a plain object
    # whose attributes are real Path instances so all Path operations work.
    fake_settings = SimpleNamespace(
        data_dir     = data_dir,
        artifact_dir = artifact_dir,
        csv_path     = data_dir / "books.csv",
        index_path   = artifact_dir / "book_index.faiss",
        meta_path    = artifact_dir / "books_metadata.pkl",
    )

    with patch("manager.settings", fake_settings):
        from manager import DynamicBookManager
        mgr = DynamicBookManager()
        yield mgr


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
class TestDynamicBookManager:

    def test_initial_book_count_zero(self, manager) -> None:
        assert manager.book_count == 0

    def test_add_book_returns_ok_message(self, manager) -> None:
        result = manager.add_book(_book())
        assert result.startswith("✅")

    def test_add_book_increments_count(self, manager) -> None:
        manager.add_book(_book("Alpha"))
        assert manager.book_count == 1
        manager.add_book(_book("Beta"))
        assert manager.book_count == 2

    def test_remove_existing_book(self, manager) -> None:
        manager.add_book(_book("Remove Me"))
        result = manager.remove_book("Remove Me")
        assert result.startswith("✅")
        assert manager.book_count == 0

    def test_remove_nonexistent_book(self, manager) -> None:
        result = manager.remove_book("Nonexistent Title")
        assert result.startswith("❌")

    def test_remove_is_case_insensitive(self, manager) -> None:
        manager.add_book(_book("Case Test"))
        result = manager.remove_book("case test")
        assert result.startswith("✅")

    def test_csv_persisted_after_add(self, manager) -> None:
        manager.add_book(_book("Persist Me"))
        csv = manager._csv_path()
        assert csv.exists()
        df = pd.read_csv(csv)
        assert any(df["title"].str.contains("Persist Me"))

    def test_faiss_index_built(self, manager) -> None:
        manager.add_book(_book("Index Me"))
        assert manager.index is not None
        assert manager.index.ntotal == 1

    def test_metadata_aligned_with_index(self, manager) -> None:
        manager.add_book(_book("Aligned"))
        assert len(manager.metadata) == manager.index.ntotal
