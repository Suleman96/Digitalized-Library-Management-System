# =============================================================================
# core/ — Iqra Digital Library retrieval engine
# =============================================================================
# Everything in this package is framework-agnostic: it knows nothing about
# FastAPI, HTTP, or the frontend.  It takes Python values and returns Python
# values.  The routers in apps/api/routers/ are the only HTTP-aware layer.
# =============================================================================

from .config import settings

__all__ = ["settings"]
