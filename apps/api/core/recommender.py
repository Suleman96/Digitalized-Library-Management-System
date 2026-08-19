# =============================================================================
# recommender.py — Iqra Digital Library
# =============================================================================
# BookRecommender
# ---------------
# Provides semantic + API-backed book recommendations:
#   1. Embeds the user query with all-MiniLM-L6-v2
#   2. Searches local FAISS index (cosine similarity)
#   3. Searches Google Books API (paginated; re-ranked by cosine sim)
#   4. Filters by language / min-rating
#   5. Sorts by rating / similarity / year
#   6. Returns plain dicts matching the canonical Book schema
#
# The recommender is read-only — it never modifies the index, and it never
# renders markup.  Presentation is entirely the frontend's concern.
# =============================================================================

from __future__ import annotations

import hashlib
import logging
import pickle
from typing import Any

import faiss
import numpy as np
import requests
import torch
from sentence_transformers import SentenceTransformer

from .config import settings

# ---------------------------------------------------------------------------
# Module logger
# ---------------------------------------------------------------------------
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Device selection
# ---------------------------------------------------------------------------
_DEVICE: str = "cuda" if torch.cuda.is_available() else "cpu"

# ---------------------------------------------------------------------------
# Fallback cover image (served from placeholder service)
# ---------------------------------------------------------------------------
_PLACEHOLDER_COVER = (
    "https://placehold.co/200x290/E2E8F0/94A3B8?text=No+Cover"
)

# ---------------------------------------------------------------------------
# External API endpoints
# ---------------------------------------------------------------------------
_GOOGLE_BOOKS_URL  = "https://www.googleapis.com/books/v1/volumes"
_OPENLIBRARY_URL   = "https://openlibrary.org/search.json"
_OPENLIBRARY_COVER = "https://covers.openlibrary.org/b/id/{cover_id}-L.jpg"


# =============================================================================
# Small utilities
# =============================================================================
def _safe_float(val: Any, default: float = 0.0) -> float:
    try:
        return float(val) if val not in (None, "", "N/A") else default
    except (ValueError, TypeError):
        return default


def _safe_int(val: Any, default: int = 0) -> int:
    try:
        return int(float(val)) if val not in (None, "", "N/A") else default
    except (ValueError, TypeError):
        return default


def book_id(title: str, authors: str) -> str:
    """
    Deterministic, URL-safe identifier for a book.

    Derived from title + first author so the same book always resolves to the
    same id across the local index, Google Books, and OpenLibrary.  This is what
    the frontend routes on (/book/[id]) and keys React lists by; matching on the
    raw title string breaks on duplicates and on punctuation.
    """
    first_author = (authors or "").split(",")[0].strip().lower()
    seed = f"{(title or '').strip().lower()}::{first_author}"
    return hashlib.sha1(seed.encode("utf-8")).hexdigest()[:16]


def _clean(value: Any) -> str:
    """Coerce any value to a stripped string."""
    return str(value or "").strip()


def _to_https(url: str) -> str:
    """Upgrade http thumbnail URLs to https (avoids mixed-content warnings)."""
    return url.replace("http://", "https://", 1) if url.startswith("http://") else url


# =============================================================================
class BookRecommender:
    """Read-only recommender: embed → search → rank → render."""

    # ── Construction ──────────────────────────────────────────────────────
    def __init__(self) -> None:
        index_path = settings.index_path
        meta_path  = settings.meta_path

        if not index_path.exists() or not meta_path.exists():
            raise FileNotFoundError(
                "FAISS index or metadata not found.  "
                "Run the app once via app.py to build them, "
                f"or check paths:\n  index → {index_path}\n  meta  → {meta_path}"
            )

        self.index:    faiss.Index          = faiss.read_index(str(index_path))
        with open(meta_path, "rb") as fh:
            self.metadata: list[dict[str, Any]] = pickle.load(fh)

        self.model = SentenceTransformer("all-MiniLM-L6-v2", device=_DEVICE)
        logger.info(
            "BookRecommender loaded — %d indexed books, device=%s",
            self.index.ntotal, _DEVICE,
        )

    def reload_index(self) -> None:
        """Reload FAISS index and metadata from disk after manager updates."""
        index_path = settings.index_path
        meta_path  = settings.meta_path
        if not index_path.exists() or not meta_path.exists():
            logger.warning("reload_index: index or metadata file missing — skipping.")
            return
        self.index = faiss.read_index(str(index_path))
        with open(meta_path, "rb") as fh:
            self.metadata = pickle.load(fh)
        logger.info("BookRecommender reloaded — %d indexed books", self.index.ntotal)

    # ── Embedding ─────────────────────────────────────────────────────────
    def _embed(self, texts: list[str]) -> np.ndarray:
        """Return L2-normalised float32 embeddings."""
        embs  = self.model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
        norms = np.linalg.norm(embs, axis=1, keepdims=True)
        return (embs / np.clip(norms, 1e-8, None)).astype(np.float32)

    # ── Data normalisation ────────────────────────────────────────────────
    def _normalise(self, raw: dict[str, Any], source: str) -> dict[str, Any]:
        """
        Convert a raw dict (local metadata or Google volumeInfo) to the
        canonical book schema used throughout the application.
        """
        # Authors — can be list (Google) or comma string (local)
        authors = raw.get("authors") or raw.get("authors_list") or ""
        if isinstance(authors, list):
            authors = ", ".join(authors)

        # Thumbnail — prefer larger Google image; ensure https
        thumbnail = _clean(
            raw.get("thumbnail")
            or (raw.get("imageLinks") or {}).get("thumbnail", "")
            or (raw.get("imageLinks") or {}).get("smallThumbnail", "")
        )
        thumbnail = _to_https(thumbnail) if thumbnail else _PLACEHOLDER_COVER

        # Publication year
        pub_year = str(
            raw.get("published_year")
            or str(raw.get("publishedDate") or "")[:4]
            or ""
        ).strip()

        title_val   = _clean(raw.get("title"))   or "Unknown Title"
        authors_val = _clean(authors)            or "Unknown Author"

        return {
            "id":             book_id(title_val, authors_val),
            "title":          title_val,
            "authors":        authors_val,
            "subtitle":       _clean(raw.get("subtitle")),
            "description":    _clean(raw.get("description")),
            "thumbnail":      thumbnail,
            "average_rating": _safe_float(
                raw.get("average_rating") or raw.get("averageRating")
            ),
            "ratings_count":  _safe_int(
                raw.get("ratings_count") or raw.get("ratingsCount")
            ),
            "info_link":      _clean(
                raw.get("info_link") or raw.get("infoLink")
            ) or "#",
            "language":       _clean(raw.get("language")).lower(),
            "published_year": pub_year,
            "num_pages":      _safe_int(
                raw.get("num_pages") or raw.get("pageCount")
            ),
            "source":         source,
            "similarity":     0.0,   # filled in by search methods
        }

    # ── Search: local FAISS ───────────────────────────────────────────────
    def _search_local(
        self, query: str, lang_code: str, pool_size: int
    ) -> list[dict[str, Any]]:
        """Cosine-similarity search over the FAISS index."""
        q_vec = self._embed([query])
        distances, indices = self.index.search(q_vec, pool_size)

        results: list[dict[str, Any]] = []
        for sim, idx in zip(distances[0], indices[0]):
            if idx < 0:
                continue
            if idx >= len(self.metadata):
                logger.warning("FAISS returned out-of-range index %d — skipping.", idx)
                continue
            book = self._normalise(self.metadata[idx], "📚 Local Library")
            if lang_code and book["language"] not in ("", lang_code):
                continue
            book["similarity"] = float(sim)
            results.append(book)

        logger.debug("Local search → %d candidates for query '%s'", len(results), query)
        return results

    # ── Search: Google Books API ──────────────────────────────────────────
    def _search_google(
        self, query: str, lang_code: str, pool_size: int
    ) -> list[dict[str, Any]]:
        """Paginated Google Books search. Returns [] on any error or missing key."""
        try:
            api_key = settings.google_api_key
        except RuntimeError:
            return []

        raw_items: list[dict[str, Any]] = []
        start = 0

        while len(raw_items) < pool_size:
            batch_n = min(40, pool_size - len(raw_items))
            params: dict[str, Any] = {
                "q": query, "maxResults": batch_n,
                "startIndex": start, "key": api_key, "orderBy": "relevance",
            }
            if lang_code:
                params["langRestrict"] = lang_code
            try:
                resp = requests.get(_GOOGLE_BOOKS_URL, params=params, timeout=8)
                resp.raise_for_status()
                data = resp.json()
            except requests.RequestException as exc:
                logger.warning("Google Books API error: %s", exc)
                break
            batch = data.get("items", [])
            if not batch:
                break
            raw_items.extend(batch)
            start += len(batch)
            if len(batch) < batch_n:
                break

        return [
            self._normalise(item.get("volumeInfo", {}), "Google Books")
            for item in raw_items
        ]

    # ── Search: OpenLibrary API (free, no key required) ───────────────────
    def _search_openlibrary(
        self, query: str, lang_code: str, pool_size: int
    ) -> list[dict[str, Any]]:
        """OpenLibrary full-text search — always available, no API key needed."""
        params: dict[str, Any] = {
            "q": query, "limit": min(pool_size, 20), "fields":
            "title,author_name,cover_i,first_publish_year,"
            "number_of_pages_median,subject,language,key,ratings_average,ratings_count",
        }
        if lang_code:
            params["lang"] = lang_code

        try:
            resp = requests.get(_OPENLIBRARY_URL, params=params, timeout=8)
            resp.raise_for_status()
            docs = resp.json().get("docs", [])
        except requests.RequestException as exc:
            logger.warning("OpenLibrary API error: %s", exc)
            return []

        books = []
        for doc in docs:
            cover_id = doc.get("cover_i")
            thumbnail = (
                _OPENLIBRARY_COVER.format(cover_id=cover_id)
                if cover_id else _PLACEHOLDER_COVER
            )
            authors = doc.get("author_name") or []
            subjects = doc.get("subject") or []
            books.append({
                "title":          _clean(doc.get("title")) or "Unknown Title",
                "authors":        ", ".join(authors[:3]) if authors else "Unknown Author",
                "subtitle":       "",
                "description":    ", ".join(subjects[:5]) if subjects else "",
                "thumbnail":      thumbnail,
                "average_rating": _safe_float(doc.get("ratings_average")),
                "ratings_count":  _safe_int(doc.get("ratings_count")),
                "info_link":      f"https://openlibrary.org{doc.get('key', '')}",
                "language":       (doc.get("language") or [""])[0].lower(),
                "published_year": str(doc.get("first_publish_year") or ""),
                "num_pages":      _safe_int(doc.get("number_of_pages_median")),
                "categories":     ", ".join(subjects[:3]) if subjects else "",
                "source":         "Open Library",
                "similarity":     0.0,
            })
        logger.debug("OpenLibrary → %d results for '%s'", len(books), query)
        return books

    # ── Search: external (Google Books + OpenLibrary, merged & re-ranked) ─
    def _search_external(
        self, query: str, lang_code: str, pool_size: int
    ) -> list[dict[str, Any]]:
        """
        Query Google Books and OpenLibrary in parallel, merge de-duplicated
        results, then re-rank the combined pool by cosine similarity.
        """
        import concurrent.futures

        half = max(pool_size, 20)
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:
            f_google = ex.submit(self._search_google,      query, lang_code, half)
            f_ol     = ex.submit(self._search_openlibrary, query, lang_code, half)
            google_books = f_google.result()
            ol_books     = f_ol.result()

        # De-duplicate by normalised title
        seen: set[str] = set()
        combined: list[dict[str, Any]] = []
        for book in google_books + ol_books:
            key = book["title"].lower().strip()
            if key not in seen:
                seen.add(key)
                combined.append(book)

        if not combined:
            return []

        # Re-rank by cosine similarity against the query embedding
        texts  = [f"{b['title']}. {b['description']}" for b in combined]
        embs   = self._embed(texts)
        q_vec  = self._embed([query])[0]
        scores = embs.dot(q_vec)
        for book, score in zip(combined, scores):
            book["similarity"] = float(score)

        combined.sort(key=lambda b: b["similarity"], reverse=True)
        logger.debug(
            "External merged → %d results (Google:%d, OL:%d) for '%s'",
            len(combined), len(google_books), len(ol_books), query,
        )
        return combined

    # ── Main recommend method ─────────────────────────────────────────────
    def recommend(
        self,
        prompt:      str,
        language:    str,
        local_n:     int,
        external_n:  int,
        min_rating:  float,
        search_mode: str,
        sort_by:     str,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """
        Return (local_results, external_results) after searching, filtering
        and sorting.

        Parameters
        ----------
        prompt      : free-text user query
        language    : display name from LANGUAGES dict (e.g. 'English')
        local_n     : max local results to return
        external_n  : max Google Books results to return
        min_rating  : minimum average_rating filter
        search_mode : 'Both' | 'Local Only' | 'External Only'
        sort_by     : 'Rating' | 'Similarity' | 'Year'
        """
        lang_code = settings.languages.get(language, "")

        local_results: list[dict[str, Any]]    = []
        external_results: list[dict[str, Any]] = []

        # ── Local search ──────────────────────────────────────────────────
        if search_mode in ("Both", "Local Only") and local_n > 0:
            pool = self._search_local(prompt, lang_code, local_n * 5)
            high = [b for b in pool if b["average_rating"] >= min_rating]
            local_results = (high or pool)[:local_n]

        # ── External search ────────────────────────────────────────────────
        if search_mode in ("Both", "External Only") and external_n > 0:
            pool = self._search_external(prompt, lang_code, external_n * 5)
            high = [b for b in pool if b["average_rating"] >= min_rating]
            external_results = (high or pool)[:external_n]

        # ── Sort ──────────────────────────────────────────────────────────
        def _sort_key(book: dict[str, Any]) -> tuple:
            if sort_by == "Rating":
                return (book["average_rating"], book["similarity"])
            if sort_by == "Year":
                return (_safe_int(book.get("published_year")), book["similarity"])
            return (book["similarity"],)  # "Similarity"

        local_results    = sorted(local_results,    key=_sort_key, reverse=True)
        external_results = sorted(external_results, key=_sort_key, reverse=True)
        return local_results, external_results
