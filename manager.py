# =============================================================================
# manager.py — Iqra Digital Library
# =============================================================================
# DynamicBookManager
# ------------------
# Owns the local book catalogue:
#   • CSV on disk  → source of truth for all book records
#   • FAISS index  → fast cosine-similarity search over title+description embeddings
#   • Pickle file  → metadata list parallel to FAISS index rows
#
# Thread safety: not designed for concurrent writes — Gradio's queue handles
# serialisation for the UI.  For multi-worker deployments add a file lock.
# =============================================================================

from __future__ import annotations

import logging
import os
import pickle
from pathlib import Path
from typing import Any

import faiss
import numpy as np
import pandas as pd
import torch
from sentence_transformers import SentenceTransformer

from config import settings

# ---------------------------------------------------------------------------
# Module logger
# ---------------------------------------------------------------------------
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Device selection
# ---------------------------------------------------------------------------
_DEVICE: str = "cuda" if torch.cuda.is_available() else "cpu"
logger.info("DynamicBookManager will use device: %s", _DEVICE)

# ---------------------------------------------------------------------------
# CSV column contract
# ---------------------------------------------------------------------------
_COLUMNS: list[str] = [
    "isbn13", "isbn10", "title", "subtitle", "authors",
    "categories", "thumbnail", "description",
    "published_year", "average_rating", "num_pages", "ratings_count",
]


# =============================================================================
class DynamicBookManager:
    """Manages the local book library: CSV ↔ FAISS index lifecycle."""

    # ── Construction ──────────────────────────────────────────────────────
    def __init__(self) -> None:
        self._ensure_directories()
        self.model = SentenceTransformer("all-MiniLM-L6-v2", device=_DEVICE)
        self.df:       pd.DataFrame          = pd.DataFrame(columns=_COLUMNS)
        self.metadata: list[dict[str, Any]]  = []
        self.index:    faiss.Index | None    = None
        self._load_or_build()

    # ── Private helpers ───────────────────────────────────────────────────
    def _ensure_directories(self) -> None:
        """Create data/ and artifacts/ directories if they don't exist."""
        settings.data_dir.mkdir(parents=True, exist_ok=True)
        settings.artifact_dir.mkdir(parents=True, exist_ok=True)
        # Ensure .gitkeep exists so artifacts/ is tracked by git as empty
        gitkeep = settings.artifact_dir / ".gitkeep"
        if not gitkeep.exists():
            gitkeep.touch()

    def _csv_path(self) -> Path:
        return settings.csv_path

    def _load_or_build(self) -> None:
        """Load CSV from disk; rebuild FAISS index and metadata pickle."""
        csv = self._csv_path()

        # Create empty CSV if it doesn't exist yet
        if not csv.exists():
            logger.info("No CSV found at %s — creating empty library.", csv)
            pd.DataFrame(columns=_COLUMNS).to_csv(csv, index=False)

        self.df = pd.read_csv(csv, dtype=str).fillna("")
        logger.info("Loaded %d books from %s", len(self.df), csv)
        self._rebuild_index()

    def _rebuild_index(self) -> None:
        """Rebuild FAISS index from current in-memory self.df, then persist all to disk."""
        texts: list[str] = (
            (self.df["title"] + ". " + self.df["description"])
            .tolist()
        )
        embeddings = self._encode(texts)

        dim = int(embeddings.shape[1]) if embeddings.size else 384
        index = faiss.IndexFlatIP(dim)
        if len(embeddings):
            index.add(embeddings)
        self.index = index
        self.metadata = self.df.to_dict(orient="records")
        logger.debug("FAISS index built with %d vectors (dim=%d)", index.ntotal, dim)
        self._persist()

    def _encode(self, texts: list[str]) -> np.ndarray:
        """Return L2-normalised float32 embeddings for a list of strings."""
        if not texts:
            # Return empty array with correct dimension
            return np.zeros((0, 384), dtype=np.float32)
        embs = self.model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
        norms = np.linalg.norm(embs, axis=1, keepdims=True)
        return (embs / np.clip(norms, 1e-8, None)).astype(np.float32)

    def _persist(self) -> None:
        """Write CSV, pickle, and FAISS index to disk."""
        csv = self._csv_path()
        self.df.to_csv(csv, index=False)

        with open(settings.meta_path, "wb") as fh:
            pickle.dump(self.metadata, fh)

        faiss.write_index(self.index, str(settings.index_path))
        logger.debug("Persisted %d books to disk.", len(self.df))

    # ── Public API ────────────────────────────────────────────────────────
    def add_book(self, details: dict[str, Any]) -> str:
        """
        Add one book record to the library and rebuild the index.

        Parameters
        ----------
        details : dict
            Must contain all keys listed in _COLUMNS.

        Returns
        -------
        str
            Human-readable result string starting with ✅ or ❌.
        """
        # Defensive: strip extra keys, fill missing ones
        row = {col: details.get(col, "") for col in _COLUMNS}
        new_row = pd.DataFrame([row])
        self.df = pd.concat([self.df, new_row], ignore_index=True)
        logger.info("Adding book: %s", row.get("title", "<untitled>"))
        self._rebuild_index()   # saves self.df to CSV first via _persist()
        return f"✅ \"{row.get('title', 'Book')}\" added to the library."

    def remove_book(self, title: str) -> str:
        """
        Remove a book by exact title match (case-insensitive).

        Parameters
        ----------
        title : str
            Title to match.

        Returns
        -------
        str
            Human-readable result string starting with ✅ or ❌.
        """
        title_clean = title.strip()
        mask = ~self.df["title"].str.strip().str.lower().eq(title_clean.lower())

        if mask.all():
            logger.warning("remove_book: no match for title '%s'", title_clean)
            return f"❌ No book found with title \"{title_clean}\"."

        removed_count = (~mask).sum()
        self.df = self.df[mask].reset_index(drop=True)
        logger.info("Removed %d book(s) titled '%s'.", removed_count, title_clean)
        self._rebuild_index()   # saves updated self.df to CSV first via _persist()
        return f"✅ \"{title_clean}\" has been removed from the library."

    # ── Properties ────────────────────────────────────────────────────────
    @property
    def book_count(self) -> int:
        """Return current number of books in the library."""
        return len(self.df)
