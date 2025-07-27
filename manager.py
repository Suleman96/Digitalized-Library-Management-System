# manager.py

"""
DynamicBookManager:
- Loads library data from CSV
- Builds / rebuilds a FAISS index on title+description embeddings
- Adds & removes books (persisting CSV, pickles, FAISS)
"""

import os
import pickle
import pandas as pd
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from config import CSV_PATH, INDEX_PATH, META_PATH

import torch
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"


class DynamicBookManager:
    """Handles on-disk library data and FAISS index for fast semantic search."""

    def __init__(self):
        # Ensure data directory exists
        os.makedirs(os.path.dirname(CSV_PATH), exist_ok=True)

        # Load embedding model
        self.model = SentenceTransformer("all-MiniLM-L6-v2", device=DEVICE)
        # Initialize data structures
        self.df = None
        self.metadata = []
        self.index = None

        # Load or build artifacts
        self._load_or_build()

    def _load_or_build(self):
        # If CSV missing, create empty
        if not os.path.exists(CSV_PATH):
            pd.DataFrame(columns=[
                "isbn13","isbn10","title","subtitle","authors","categories",
                "thumbnail","description","published_year","average_rating",
                "num_pages","ratings_count"
            ]).to_csv(CSV_PATH, index=False)

        # Read CSV
        self.df = pd.read_csv(CSV_PATH).fillna("")
        self.metadata = self.df.to_dict(orient="records")

        # Build embeddings + index
        texts = (self.df["title"] + ". " + self.df["description"]).tolist()
        embs = self.model.encode(texts, convert_to_numpy=True)
        norms = np.linalg.norm(embs, axis=1, keepdims=True)
        embs = (embs / np.clip(norms, 1e-8, None)).astype(np.float32)

        dim = embs.shape[1]
        index = faiss.IndexFlatIP(dim)
        if len(embs):
            index.add(embs)
        self.index = index

        # Persist index & metadata for recommender
        self._save_meta()

    def _save_meta(self):
        self.df.to_csv(CSV_PATH, index=False)
        with open(META_PATH, "wb") as f:
            pickle.dump(self.metadata, f)
        faiss.write_index(self.index, INDEX_PATH)

    def add_book(self, details: dict) -> str:
        self.df = pd.concat([self.df, pd.DataFrame([details])], ignore_index=True)
        self.metadata.append(details)
        self._load_or_build()
        return "✅ Book successfully added."

    def remove_book(self, title: str) -> str:
        mask = ~self.df["title"].str.lower().eq(title.strip().lower())
        if mask.all():
            return f"❌ No book found with title “{title}”."
        self.df = self.df[mask].reset_index(drop=True)
        self.metadata = self.df.to_dict(orient="records")
        self._load_or_build()
        return f"✅ Book titled “{title}” removed."
