# =============================================================================
# routers/analytics.py — catalogue statistics
# =============================================================================

from __future__ import annotations

from fastapi import APIRouter

from ..core.analytics import build_analytics
from ..schemas import AnalyticsResponse

router = APIRouter(tags=["analytics"])


@router.get("/analytics", response_model=AnalyticsResponse)
def analytics() -> AnalyticsResponse:
    """
    Catalogue statistics as series data.

    v2 returned three server-rendered Matplotlib PNGs; the frontend now draws
    these with Recharts, so they are interactive and follow the active theme.
    """
    return AnalyticsResponse(**build_analytics())
