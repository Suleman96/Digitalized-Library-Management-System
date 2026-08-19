# =============================================================================
# config.py — Iqra Digital Library
# =============================================================================
# Single source of truth for:
#   • File-system paths (data, artifacts, assets)
#   • External API credentials
#   • UI option lists exposed to Gradio
#
# Usage
# -----
#   from config import settings          # preferred — typed dataclass
#   from config import CSV_PATH, ...     # legacy flat-import still works
#
# Environment variables (highest priority):
#   GOOGLE_API_KEY   – required
#   SERVER_HOST      – default 0.0.0.0
#   SERVER_PORT      – default 7860
#   GRADIO_SHARE     – default false
#
# .env file (second priority, never commit to git):
#   Copy .env.example → .env and fill in values.
# =============================================================================

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Load .env  (safe no-op when file is absent)
# ---------------------------------------------------------------------------
def _find_project_root() -> Path:
    """
    Resolve the repository root from anywhere in the package tree.

    Order of precedence:
      1. IQRA_ROOT environment variable (used by the Docker image)
      2. Nearest ancestor directory containing a `data/` folder
      3. Nearest ancestor containing `.git` or `pyproject.toml`
      4. Three levels up (apps/api/core → repo root) as a last resort
    """
    override = os.getenv("IQRA_ROOT", "").strip()
    if override:
        return Path(override).resolve()

    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "data").is_dir():
            return parent
    for parent in here.parents:
        if (parent / ".git").exists() or (parent / "pyproject.toml").exists():
            return parent
    return here.parents[3]


_BASE = _find_project_root()
load_dotenv(dotenv_path=_BASE / ".env", override=False)


# ---------------------------------------------------------------------------
# Path helpers — resolve paths relative to project root
# ---------------------------------------------------------------------------
def _path(*parts: str) -> Path:
    return _BASE.joinpath(*parts)


# ---------------------------------------------------------------------------
# Settings dataclass  (frozen = immutable after construction)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Settings:
    # ── Paths ──────────────────────────────────────────────────────────────
    base_dir:    Path = field(default_factory=lambda: _BASE)
    data_dir:    Path = field(default_factory=lambda: _path("data"))
    artifact_dir: Path = field(default_factory=lambda: _path("artifacts"))
    asset_dir:   Path = field(default_factory=lambda: _path("assets"))

    @property
    def csv_path(self) -> Path:
        """Canonical dataset path.  Falls back to legacy location."""
        primary = self.data_dir / "books.csv"
        if primary.exists():
            return primary
        legacy = self.data_dir / "Kaggle_7k_books" / "books.csv"
        if legacy.exists():
            return legacy
        # Neither exists yet — return primary so manager can create it
        return primary

    @property
    def index_path(self) -> Path:
        return self.artifact_dir / "book_index.faiss"

    @property
    def meta_path(self) -> Path:
        return self.artifact_dir / "books_metadata.pkl"

    @property
    def logo_path(self) -> Path:
        return self.asset_dir / "logo.png"

    # ── API credentials ────────────────────────────────────────────────────
    @property
    def google_api_key(self) -> str:
        key = os.getenv("GOOGLE_API_KEY", "").strip()
        if not key:
            api_txt = self.base_dir / "API.txt"
            if api_txt.exists():
                key = api_txt.read_text(encoding="utf-8").strip()
        if not key:
            raise RuntimeError(
                "Google Books API key not found.\n"
                "  • Set the GOOGLE_API_KEY environment variable, OR\n"
                "  • Copy .env.example → .env and add GOOGLE_API_KEY=<key>, OR\n"
                "  • Create API.txt in the project root containing only the key.\n"
                "  Get a free key → https://console.cloud.google.com/apis/library/"
                "books.googleapis.com"
            )
        return key

    # ── Server settings ────────────────────────────────────────────────────
    @property
    def server_host(self) -> str:
        return os.getenv("SERVER_HOST", "0.0.0.0")

    @property
    def server_port(self) -> int:
        return int(os.getenv("SERVER_PORT", "7860"))

    @property
    def gradio_share(self) -> bool:
        return os.getenv("GRADIO_SHARE", "false").lower() == "true"

    # ── UI option lists ────────────────────────────────────────────────────
    languages: dict[str, str] = field(default_factory=lambda: {
        "Any":        "",
        "English":    "en",
        "Arabic":     "ar",
        "French":     "fr",
        "Spanish":    "es",
        "German":     "de",
        "Italian":    "it",
        "Portuguese": "pt",
        "Chinese":    "zh",
        "Japanese":   "ja",
        "Korean":     "ko",
        "Russian":    "ru",
        "Dutch":      "nl",
        "Swedish":    "sv",
        "Turkish":    "tr",
        "Hindi":      "hi",
    })

    search_modes: tuple[str, ...] = (
        "Both",           # local FAISS  +  Google Books
        "Local Only",
        "External Only",
    )

    sort_options: tuple[str, ...] = (
        "Rating",         # highest average_rating first
        "Similarity",     # highest cosine similarity first
        "Year",           # most recently published first
    )


# ---------------------------------------------------------------------------
# Module-level singleton  (import this everywhere)
# ---------------------------------------------------------------------------
settings = Settings()

# ---------------------------------------------------------------------------
# Flat aliases — backward-compat for older import style
# ---------------------------------------------------------------------------
CSV_PATH    = str(settings.csv_path)
INDEX_PATH  = str(settings.index_path)
META_PATH   = str(settings.meta_path)
LOGO_PATH   = str(settings.logo_path)

try:
    GOOGLE_API_KEY = settings.google_api_key
except RuntimeError:
    GOOGLE_API_KEY = ""
LANGUAGES       = settings.languages
SEARCH_MODES    = list(settings.search_modes)
SORT_BY_OPTIONS = list(settings.sort_options)
