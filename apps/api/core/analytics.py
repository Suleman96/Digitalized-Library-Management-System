# =============================================================================
# analytics.py — Iqra Digital Library v3
# =============================================================================
# Catalogue statistics as plain data.
#
# v2 rendered three Matplotlib PNGs on the server and shipped them to the
# browser as images.  That made the charts static, theme-blind, and forced a
# ~60 MB plotting stack into the API image.  v3 returns the series and lets the
# frontend draw them.
# =============================================================================

from __future__ import annotations

import logging
from typing import Any

import pandas as pd

from .config import settings

logger = logging.getLogger(__name__)

_TOP_CATEGORIES = 12
_MIN_YEAR = 1900


def _numeric(df: pd.DataFrame, column: str) -> pd.Series:
    """Coerce a column to numeric, tolerating absence."""
    if column not in df.columns:
        return pd.Series(dtype="float64")
    return pd.to_numeric(df[column], errors="coerce")


def build_analytics() -> dict[str, Any]:
    """
    Compute catalogue analytics from the CSV.

    Returns a JSON-serialisable dict with headline figures and three series:
    rating distribution, top categories, and publication-year trend.
    """
    try:
        df = pd.read_csv(settings.csv_path, dtype=str).fillna("")
    except FileNotFoundError:
        logger.warning("analytics: catalogue not found at %s", settings.csv_path)
        return {
            "available": False,
            "summary": None,
            "ratings": [],
            "categories": [],
            "years": [],
        }

    ratings   = _numeric(df, "average_rating").dropna()
    years     = _numeric(df, "published_year").dropna()
    pages     = _numeric(df, "num_pages").dropna()

    # ── Rating distribution — 25 bins, matching the v2 histogram ─────────
    rating_bins: list[dict[str, Any]] = []
    if not ratings.empty:
        counts, edges = pd.cut(ratings, bins=25, retbins=True)
        binned = counts.value_counts().sort_index()
        for interval, count in binned.items():
            rating_bins.append({
                "label": f"{interval.left:.1f}–{interval.right:.1f}",
                "midpoint": round((interval.left + interval.right) / 2, 2),
                "count": int(count),
            })

    # ── Top categories ────────────────────────────────────────────────────
    category_bins: list[dict[str, Any]] = []
    if "categories" in df.columns:
        cats = (
            df["categories"]
            .dropna()
            .str.split(",")
            .explode()
            .str.strip()
        )
        cats = cats[cats != ""]
        for name, count in cats.value_counts().head(_TOP_CATEGORIES).items():
            category_bins.append({"label": str(name), "count": int(count)})

    # ── Publication-year trend ────────────────────────────────────────────
    year_points: list[dict[str, Any]] = []
    if not years.empty:
        valid = years.astype(int)
        valid = valid[valid > _MIN_YEAR]
        for year, count in valid.value_counts().sort_index().items():
            year_points.append({"year": int(year), "count": int(count)})

    distinct_categories = 0
    if "categories" in df.columns:
        distinct_categories = int(
            df["categories"].dropna().str.split(",").explode().str.strip().nunique()
        )

    return {
        "available": True,
        "summary": {
            "totalBooks":     int(len(df)),
            "averageRating":  round(float(ratings.mean()), 2) if not ratings.empty else 0.0,
            "categoryCount":  distinct_categories,
            "totalPages":     int(pages.sum()) if not pages.empty else 0,
            "ratedBooks":     int(len(ratings)),
            "earliestYear":   int(years.min()) if not years.empty else None,
            "latestYear":     int(years.max()) if not years.empty else None,
        },
        "ratings":    rating_bins,
        "categories": category_bins,
        "years":      year_points,
    }
