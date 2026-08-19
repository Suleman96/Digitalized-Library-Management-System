# =============================================================================
# hybrid_retriever.py — Iqra Digital Library v2
# =============================================================================
# KGRetriever  (public class name kept as HybridRetriever for API compatibility)
# -------------------------------------------------------------------------------
# Replaces BM25 keyword search with a NetworkX Knowledge Graph that encodes
# three relationship types between books:
#
#   • same_author   — books sharing one or more authors        (weight 1.00)
#   • same_category — books sharing one or more categories     (weight 0.75)
#   • co_semantic   — books whose embedding cosine sim ≥ 0.82  (weight = sim)
#
# Query flow:
#   1. FAISS semantic search → top pool candidates with cosine similarity scores
#   2. 1-hop knowledge-graph expansion → structurally related books not in pool
#   3. Min-max normalise both score vectors, then fuse:
#         score = FAISS_WEIGHT * faiss_norm + GRAPH_WEIGHT * graph_norm
#   4. Return top-k by fused score
#
# The graph is built once and cached to artifacts/book_graph.pkl.
# Subsequent startups load the cache in milliseconds.
#
# Public API (unchanged from the BM25 version — no edits needed in app.py):
#   hybrid = HybridRetriever()
#   hybrid.build(embed_fn=reco._embed)     # first run builds + caches graph
#   hybrid.search(query, k=10)             # returns list[dict]
#   hybrid.reload(embed_fn=reco._embed)    # call after manager.add/remove_book
#   hybrid.is_ready                        # bool property
# =============================================================================

from __future__ import annotations

import logging
import os
import pickle
from pathlib import Path
from typing import Any, Callable

import numpy as np

from .config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Scoring weights
# ---------------------------------------------------------------------------
_FAISS_WEIGHT = 0.65   # semantic similarity (dominant signal)
_GRAPH_WEIGHT = 0.35   # structural graph proximity

# Knowledge-graph edge weights
_W_AUTHOR   = 1.00
_W_CATEGORY = 0.75

# Semantic-edge parameters (used only during graph construction)
_SEM_THRESHOLD  = 0.82   # min inner-product score to add a semantic KG edge
_SEM_K_SEARCH   = 6      # FAISS kNN per book during build (includes self → skip [0])
_MAX_CAT_SIZE   = 150    # categories with more books than this are too generic; skip

# Runtime search parameters
_FAISS_POOL_MUL = 5      # FAISS retrieves k * this many candidates before graph expand


def _graph_cache_path() -> Path:
    return settings.artifact_dir / "book_graph.pkl"


class HybridRetriever:
    """
    Knowledge Graph + FAISS semantic hybrid retriever.

    Drop-in replacement for the old BM25 + FAISS HybridRetriever.
    Same public interface; richer results via structured book relationships.
    """

    def __init__(self) -> None:
        self._graph:      Any                  = None   # networkx.Graph
        self._faiss_idx:  Any                  = None   # faiss.IndexFlatIP
        self._metadata:   list[dict[str, Any]] = []
        self._embed_fn:   Callable | None      = None

    # ── Private helpers ───────────────────────────────────────────────────

    def _load_metadata(self) -> list[dict[str, Any]]:
        meta_path = settings.meta_path
        if not meta_path.exists():
            return []
        with open(meta_path, "rb") as fh:
            return pickle.load(fh)

    def _load_faiss(self) -> Any:
        import faiss
        return faiss.read_index(str(settings.index_path))

    def _default_embed(self, texts: list[str]) -> np.ndarray:
        """Fallback: load own SentenceTransformer when none is provided."""
        import torch
        from sentence_transformers import SentenceTransformer
        device = "cuda" if torch.cuda.is_available() else "cpu"
        model  = SentenceTransformer("all-MiniLM-L6-v2", device=device)
        embs   = model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
        norms  = np.linalg.norm(embs, axis=1, keepdims=True)
        return (embs / np.clip(norms, 1e-8, None)).astype(np.float32)

    @staticmethod
    def _minmax_norm(arr: np.ndarray) -> np.ndarray:
        lo, hi = arr.min(), arr.max()
        if hi - lo < 1e-9:
            return np.zeros_like(arr)
        return (arr - lo) / (hi - lo)

    def _build_graph(
        self,
        metadata:  list[dict[str, Any]],
        faiss_idx: Any,
    ) -> Any:
        """
        Construct a NetworkX undirected graph from book metadata + FAISS vectors.

        Three edge types are added in order of priority (earlier ones win when
        an edge between two nodes already exists):
            1. author   — strongest structural signal
            2. category — genre / topic clustering
            3. semantic — embedding similarity (from FAISS reconstruction)
        """
        import networkx as nx

        n = len(metadata)
        G = nx.Graph()
        G.add_nodes_from(range(n))

        # ── 1. Author edges ───────────────────────────────────────────────
        author_to_ids: dict[str, list[int]] = {}
        for i, m in enumerate(metadata):
            for raw_author in str(m.get("authors", "")).split(";"):
                a = raw_author.strip().lower()
                if a:
                    author_to_ids.setdefault(a, []).append(i)

        author_edges = 0
        for ids in author_to_ids.values():
            if len(ids) < 2:
                continue
            for j in range(len(ids)):
                for k in range(j + 1, len(ids)):
                    if not G.has_edge(ids[j], ids[k]):
                        G.add_edge(ids[j], ids[k], weight=_W_AUTHOR, rel="author")
                        author_edges += 1

        # ── 2. Category edges ─────────────────────────────────────────────
        cat_to_ids: dict[str, list[int]] = {}
        for i, m in enumerate(metadata):
            raw_cats = str(m.get("categories", "")).replace(";", ",")
            for raw_cat in raw_cats.split(","):
                c = raw_cat.strip().lower()
                if c:
                    cat_to_ids.setdefault(c, []).append(i)

        cat_edges = 0
        for ids in cat_to_ids.values():
            if len(ids) < 2 or len(ids) > _MAX_CAT_SIZE:
                # skip singletons (useless) and mega-categories (too noisy)
                continue
            for j in range(len(ids)):
                for k in range(j + 1, len(ids)):
                    if not G.has_edge(ids[j], ids[k]):
                        G.add_edge(ids[j], ids[k], weight=_W_CATEGORY, rel="category")
                        cat_edges += 1

        # ── 3. Semantic edges (via FAISS reconstruction) ──────────────────
        # IndexFlatIP stores all vectors → reconstruct is O(1) per vector.
        # We batch to avoid a Python-level loop overhead.
        sem_edges = 0
        batch_size = 256
        dim = faiss_idx.d

        for start in range(0, n, batch_size):
            end = min(start + batch_size, n)
            batch_len = end - start

            batch_vecs = np.zeros((batch_len, dim), dtype=np.float32)
            for bi in range(batch_len):
                faiss_idx.reconstruct(start + bi, batch_vecs[bi])

            # Search each vector against the full index
            dists, idxs = faiss_idx.search(batch_vecs, _SEM_K_SEARCH)

            for bi in range(batch_len):
                src = start + bi
                # Skip index 0 — that's the vector itself (sim ≈ 1.0)
                for sim, dst in zip(dists[bi][1:], idxs[bi][1:]):
                    if 0 <= dst < n and float(sim) >= _SEM_THRESHOLD:
                        if not G.has_edge(src, dst):
                            G.add_edge(src, dst, weight=float(sim), rel="semantic")
                            sem_edges += 1

        logger.info(
            "Knowledge Graph built — %d nodes | %d edges "
            "(author=%d, category=%d, semantic=%d)",
            G.number_of_nodes(),
            G.number_of_edges(),
            author_edges, cat_edges, sem_edges,
        )
        return G

    # ── Public API ────────────────────────────────────────────────────────

    def build(self, embed_fn: Callable | None = None) -> None:
        """
        Build the KG + FAISS hybrid index.

        On first call this takes ~30-60 s for 6 k books while the knowledge
        graph is constructed and cached.  All subsequent calls load the
        cached graph from disk in <1 s.

        Parameters
        ----------
        embed_fn : optional callable (list[str]) -> np.ndarray
            Reuse an already-loaded embedding model (e.g. ``reco._embed``).
            When omitted a fresh SentenceTransformer is loaded locally.
        """
        index_path = settings.index_path
        meta_path  = settings.meta_path
        cache_path = _graph_cache_path()

        if not index_path.exists() or not meta_path.exists():
            logger.warning(
                "HybridRetriever.build: FAISS index or metadata not found — skipped. "
                "Run the app once so the manager can build the index."
            )
            return

        try:
            import networkx as nx  # noqa: F401  — validate import up-front
            import faiss            # noqa: F401

            self._metadata  = self._load_metadata()
            if not self._metadata:
                logger.warning("HybridRetriever.build: metadata is empty — skipped.")
                return

            self._faiss_idx = self._load_faiss()
            self._embed_fn  = embed_fn or self._default_embed

            # ── Try loading the cached graph ──────────────────────────────
            if cache_path.exists():
                try:
                    with open(cache_path, "rb") as fh:
                        cached_graph = pickle.load(fh)
                    if cached_graph.number_of_nodes() == len(self._metadata):
                        self._graph = cached_graph
                        logger.info(
                            "HybridRetriever: loaded cached KG "
                            "(%d nodes, %d edges) from %s",
                            self._graph.number_of_nodes(),
                            self._graph.number_of_edges(),
                            cache_path,
                        )
                        return
                    logger.info(
                        "HybridRetriever: cached graph node count mismatch "
                        "(%d vs %d) — rebuilding.",
                        cached_graph.number_of_nodes(),
                        len(self._metadata),
                    )
                except Exception as exc:
                    logger.warning(
                        "HybridRetriever: could not load cached graph (%s) — rebuilding.",
                        exc,
                    )

            # ── Build the graph from scratch ──────────────────────────────
            logger.info(
                "HybridRetriever: building knowledge graph for %d books. "
                "This takes ~30-60 s on first run …",
                len(self._metadata),
            )
            self._graph = self._build_graph(self._metadata, self._faiss_idx)

            # Persist for future startups
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            with open(cache_path, "wb") as fh:
                pickle.dump(self._graph, fh, protocol=4)
            logger.info("HybridRetriever: knowledge graph cached → %s", cache_path)

        except ImportError as exc:
            logger.warning(
                "HybridRetriever.build: missing package (%s). "
                "Run: pip install networkx faiss-cpu",
                exc,
            )
            self._graph = self._faiss_idx = None
        except Exception as exc:
            logger.exception("HybridRetriever.build failed: %s", exc)
            self._graph = self._faiss_idx = None

    def reload(self, embed_fn: Callable | None = None) -> None:
        """
        Invalidate the cached graph and rebuild from scratch.

        Call this after ``manager.add_book()`` or ``manager.remove_book()``
        so the graph stays in sync with the FAISS index.
        """
        cache_path = _graph_cache_path()
        if cache_path.exists():
            try:
                os.remove(cache_path)
            except OSError as exc:
                logger.warning("HybridRetriever.reload: could not delete cache: %s", exc)

        self._graph     = None
        self._faiss_idx = None
        self._metadata  = []
        self.build(embed_fn=embed_fn or self._embed_fn)

    def search(self, query: str, k: int = 10) -> list[dict[str, Any]]:
        """
        Run Knowledge Graph + FAISS hybrid search.

        Retrieves ``k * _FAISS_POOL_MUL`` FAISS candidates, expands each
        one hop via the knowledge graph, then fuses both score vectors with
        min-max normalisation before returning the top-k results.

        Returns
        -------
        list[dict]
            Canonical book dicts (same schema as BookRecommender).
            Empty list when not ready or on error.
        """
        if not self.is_ready:
            return []

        n         = len(self._metadata)
        pool_size = min(k * _FAISS_POOL_MUL, n)

        try:
            # ── 1. FAISS semantic search ───────────────────────────────────
            q_vec = self._embed_fn([query])                         # (1, dim)
            distances, indices = self._faiss_idx.search(q_vec, pool_size)

            # Map: index → best cosine similarity score from FAISS
            faiss_scores: dict[int, float] = {}
            for sim, idx in zip(distances[0], indices[0]):
                if 0 <= idx < n:
                    faiss_scores[idx] = max(faiss_scores.get(idx, -1.0), float(sim))

            if not faiss_scores:
                return []

            # ── 2. Knowledge-graph 1-hop expansion ────────────────────────
            # For each FAISS seed, walk its neighbours.
            # A neighbour's graph-proximity score = best (seed_norm * edge_w)
            # across all seeds that connect to it.
            faiss_max   = max(faiss_scores.values())
            graph_scores: dict[int, float] = {}

            for seed_idx, seed_sim in faiss_scores.items():
                seed_norm = seed_sim / (faiss_max + 1e-9)
                # self._graph[seed_idx] is a dict {neighbor: {attr_dict}}
                for neighbor, attr in self._graph[seed_idx].items():
                    edge_w  = float(attr.get("weight", 0.5))
                    contrib = seed_norm * edge_w
                    if contrib > graph_scores.get(neighbor, 0.0):
                        graph_scores[neighbor] = contrib

            # ── 3. Fuse FAISS + graph scores ──────────────────────────────
            all_ids = list(set(faiss_scores) | set(graph_scores))

            faiss_vec = np.array([faiss_scores.get(i, 0.0) for i in all_ids], dtype=np.float32)
            graph_vec = np.array([graph_scores.get(i, 0.0) for i in all_ids], dtype=np.float32)

            faiss_norm = self._minmax_norm(faiss_vec)
            graph_norm = self._minmax_norm(graph_vec)

            combined = _FAISS_WEIGHT * faiss_norm + _GRAPH_WEIGHT * graph_norm

            # Sort descending and take top-k
            order = np.argsort(combined)[::-1][:k]

        except Exception as exc:
            logger.warning("HybridRetriever.search error: %s", exc)
            return []

        # ── 4. Build result dicts ──────────────────────────────────────────
        results: list[dict[str, Any]] = []
        for pos in order:
            score = float(combined[pos])
            if score < 1e-9:
                continue
            idx = all_ids[pos]
            m   = self._metadata[idx]

            # Tag the result with which graph edges contributed (informational)
            edge_types: set[str] = set()
            if idx in faiss_scores:
                edge_types.add("semantic")
            if idx in graph_scores:
                # Find which rel type the best edge came from
                best_w  = 0.0
                best_rel = ""
                for seed_idx in faiss_scores:
                    if self._graph.has_edge(seed_idx, idx):
                        a = self._graph[seed_idx][idx]
                        if a.get("weight", 0) > best_w:
                            best_w   = a["weight"]
                            best_rel = a.get("rel", "")
                if best_rel:
                    edge_types.add(best_rel)

            results.append({
                "title":          str(m.get("title",          "")),
                "authors":        str(m.get("authors",        "")),
                "description":    str(m.get("description",    "")),
                "average_rating": float(m.get("average_rating", 0.0) or 0.0),
                "published_year": str(m.get("published_year", "")),
                "thumbnail":      str(m.get("thumbnail",      "")),
                "info_link":      str(m.get("info_link",      "#") or "#"),
                "source":         "Local Library (KG + FAISS)",
                "similarity":     score,
                "ratings_count":  int(float(m.get("ratings_count", 0) or 0)),
                "num_pages":      int(float(m.get("num_pages",     0) or 0)),
                "language":       str(m.get("language",       "")),
            })

        logger.debug(
            "HybridRetriever: '%s' → %d results (pool=%d FAISS + %d graph)",
            query, len(results), len(faiss_scores), len(graph_scores),
        )
        return results

    @property
    def is_ready(self) -> bool:
        """True when both the knowledge graph and FAISS index are loaded."""
        return self._graph is not None and self._faiss_idx is not None
