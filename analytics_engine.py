"""
Market analytics engine for the Land Tenders Dashboard.

Provides pure-function analytics over tender DataFrames for regional hotspot
analysis, supply pipeline metrics, seasonal patterns, price analytics, and
a composite scoring system.  Every public function accepts DataFrames (loaded
elsewhere) and returns DataFrames / dicts suitable for Plotly charting and
compatible with @st.cache_data (hashable args only).

Sections:
    1. Regional Hotspot Analysis
    2. Supply Pipeline Analysis
    3. Seasonal Patterns
    4. Price Analytics
    5. Competitive Intelligence
    6. Scoring System

Usage:
    from analytics_engine import score_all_tenders, regional_momentum
    scored = score_all_tenders(tenders_df)
    momentum = regional_momentum(tenders_df, window_months=3)
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Hebrew month names for display
_MONTH_NAMES_HE: Dict[int, str] = {
    1: "ינואר",
    2: "פברואר",
    3: "מרץ",
    4: "אפריל",
    5: "מאי",
    6: "יוני",
    7: "יולי",
    8: "אוגוסט",
    9: "ספטמבר",
    10: "אוקטובר",
    11: "נובמבר",
    12: "דצמבר",
}

# Hebrew day-of-week names (Monday=0 through Sunday=6)
_DOW_NAMES_HE: Dict[int, str] = {
    0: "שני",
    1: "שלישי",
    2: "רביעי",
    3: "חמישי",
    4: "שישי",
    5: "שבת",
    6: "ראשון",
}

# Scoring weights (fixed)
_SCORE_WEIGHTS: Dict[str, float] = {
    "urgency": 0.20,
    "size": 0.20,
    "readiness": 0.25,
    "location": 0.20,
    "freshness": 0.15,
}


# ============================================================================
# INTERNAL HELPERS
# ============================================================================

def _ensure_datetime(df: pd.DataFrame, col: str) -> pd.Series:
    """Coerce a column to tz-naive datetime, returning pd.NaT for failures.

    Supabase returns TZ-aware (UTC) timestamps.  The dashboard and scoring
    system compare against ``datetime.now()`` which is tz-naive, so we
    strip any timezone info here to prevent ``TypeError: Cannot compare
    tz-naive and tz-aware timestamps``.

    Args:
        df: Source DataFrame.
        col: Column name to coerce.

    Returns:
        pd.Series of tz-naive datetime64[ns].
    """
    if col not in df.columns:
        return pd.Series(pd.NaT, index=df.index)
    series = pd.to_datetime(df[col], errors="coerce", utc=True)
    return series.dt.tz_localize(None)


def _safe_freq(freq: str) -> str:
    """Normalise frequency alias to pandas-compatible offset string.

    Args:
        freq: User-supplied frequency string (e.g. 'M', 'Q', 'W').

    Returns:
        Pandas offset alias. Defaults to 'ME' (month-end) for unrecognised input.
    """
    mapping = {
        "M": "ME",
        "Q": "QE",
        "W": "W",
        "D": "D",
        "ME": "ME",
        "QE": "QE",
        "MS": "MS",
        "QS": "QS",
    }
    return mapping.get(freq.upper(), "ME")


# ============================================================================
# 1. REGIONAL HOTSPOT ANALYSIS
# ============================================================================

def regional_tender_volume(
    tenders_df: pd.DataFrame,
    freq: str = "M",
) -> pd.DataFrame:
    """Tender count by region over time (monthly/quarterly).

    Groups tenders by their publish_date (floored to the requested frequency)
    and region, counting how many tenders were published in each bucket.

    Args:
        tenders_df: DataFrame with at least 'publish_date' and 'region' columns.
        freq: Pandas offset alias — 'M' for month, 'Q' for quarter.

    Returns:
        DataFrame with columns: date, region, count.
        Empty DataFrame if input is empty or missing required columns.
    """
    if tenders_df.empty or "region" not in tenders_df.columns:
        logger.warning("regional_tender_volume: empty or missing 'region' column")
        return pd.DataFrame(columns=["date", "region", "count"])

    df = tenders_df.copy()
    df["_pub"] = _ensure_datetime(df, "publish_date")
    df = df.dropna(subset=["_pub", "region"])

    if df.empty:
        return pd.DataFrame(columns=["date", "region", "count"])

    offset = _safe_freq(freq)
    df["_period"] = df["_pub"].dt.to_period(offset[0])

    result = (
        df.groupby(["_period", "region"])
        .size()
        .reset_index(name="count")
    )
    result["date"] = result["_period"].dt.to_timestamp()
    result = result[["date", "region", "count"]].sort_values("date").reset_index(drop=True)

    logger.info(
        "regional_tender_volume: %d rows, %d regions, freq=%s",
        len(result), result["region"].nunique(), freq,
    )
    return result


def regional_units_volume(
    tenders_df: pd.DataFrame,
    freq: str = "M",
) -> pd.DataFrame:
    """Housing units by region over time.

    Sums the 'units' column per region per time bucket.

    Args:
        tenders_df: DataFrame with 'publish_date', 'region', and 'units' columns.
        freq: Pandas offset alias.

    Returns:
        DataFrame with columns: date, region, units.
    """
    if tenders_df.empty or "region" not in tenders_df.columns:
        logger.warning("regional_units_volume: empty or missing columns")
        return pd.DataFrame(columns=["date", "region", "units"])

    df = tenders_df.copy()
    df["_pub"] = _ensure_datetime(df, "publish_date")
    df = df.dropna(subset=["_pub", "region"])

    if "units" not in df.columns:
        df["units"] = 0
    df["units"] = pd.to_numeric(df["units"], errors="coerce").fillna(0)

    if df.empty:
        return pd.DataFrame(columns=["date", "region", "units"])

    offset = _safe_freq(freq)
    df["_period"] = df["_pub"].dt.to_period(offset[0])

    result = (
        df.groupby(["_period", "region"])["units"]
        .sum()
        .reset_index()
    )
    result["date"] = result["_period"].dt.to_timestamp()
    result = result[["date", "region", "units"]].sort_values("date").reset_index(drop=True)

    logger.info("regional_units_volume: %d rows", len(result))
    return result


def regional_momentum(
    tenders_df: pd.DataFrame,
    window_months: int = 3,
) -> pd.DataFrame:
    """Which regions are heating up/cooling down.

    Compares the tender count in the most recent *window_months* against the
    preceding window of the same length.

    Args:
        tenders_df: DataFrame with 'publish_date' and 'region'.
        window_months: Number of months for each comparison window.

    Returns:
        DataFrame with columns: region, recent_count, previous_count,
        change_pct, direction ('up' / 'down' / 'stable').
    """
    cols = ["region", "recent_count", "previous_count", "change_pct", "direction"]
    if tenders_df.empty or "region" not in tenders_df.columns:
        return pd.DataFrame(columns=cols)

    df = tenders_df.copy()
    df["_pub"] = _ensure_datetime(df, "publish_date")
    df = df.dropna(subset=["_pub", "region"])

    if df.empty:
        return pd.DataFrame(columns=cols)

    now = pd.Timestamp(datetime.now())
    recent_start = now - pd.DateOffset(months=window_months)
    previous_start = recent_start - pd.DateOffset(months=window_months)

    recent = df[(df["_pub"] >= recent_start) & (df["_pub"] < now)]
    previous = df[(df["_pub"] >= previous_start) & (df["_pub"] < recent_start)]

    recent_counts = recent.groupby("region").size().rename("recent_count")
    prev_counts = previous.groupby("region").size().rename("previous_count")

    merged = pd.DataFrame({"recent_count": recent_counts, "previous_count": prev_counts}).fillna(0)
    merged = merged.astype(int)

    merged["change_pct"] = np.where(
        merged["previous_count"] > 0,
        ((merged["recent_count"] - merged["previous_count"]) / merged["previous_count"] * 100).round(1),
        np.where(merged["recent_count"] > 0, 100.0, 0.0),
    )

    merged["direction"] = np.where(
        merged["change_pct"] > 10, "up",
        np.where(merged["change_pct"] < -10, "down", "stable"),
    )

    result = merged.reset_index().rename(columns={"index": "region"})
    if "region" not in result.columns and result.index.name == "region":
        result = result.reset_index()

    result = result[cols].sort_values("change_pct", ascending=False).reset_index(drop=True)
    logger.info("regional_momentum: %d regions analysed", len(result))
    return result


# ============================================================================
# 2. SUPPLY PIPELINE ANALYSIS
# ============================================================================

def supply_pipeline(
    tenders_df: pd.DataFrame,
    freq: str = "M",
) -> pd.DataFrame:
    """Active tenders over time: new published, closing, net change.

    For each time bucket counts how many tenders had their publish_date in
    that period (new_published), how many had their deadline in that period
    (closing), and the net change (new - closing).

    Args:
        tenders_df: DataFrame with 'publish_date' and 'deadline'.
        freq: Pandas offset alias.

    Returns:
        DataFrame with columns: date, new_published, closing, active_net.
    """
    out_cols = ["date", "new_published", "closing", "active_net"]
    if tenders_df.empty:
        return pd.DataFrame(columns=out_cols)

    df = tenders_df.copy()
    df["_pub"] = _ensure_datetime(df, "publish_date")
    df["_dead"] = _ensure_datetime(df, "deadline")

    offset = _safe_freq(freq)
    freq_char = offset[0]

    pub_valid = df.dropna(subset=["_pub"])
    dead_valid = df.dropna(subset=["_dead"])

    if pub_valid.empty and dead_valid.empty:
        return pd.DataFrame(columns=out_cols)

    new_series = pd.Series(dtype="int64")
    if not pub_valid.empty:
        pub_valid = pub_valid.copy()
        pub_valid["_period"] = pub_valid["_pub"].dt.to_period(freq_char)
        new_series = pub_valid.groupby("_period").size()

    close_series = pd.Series(dtype="int64")
    if not dead_valid.empty:
        dead_valid = dead_valid.copy()
        dead_valid["_period"] = dead_valid["_dead"].dt.to_period(freq_char)
        close_series = dead_valid.groupby("_period").size()

    all_periods = new_series.index.union(close_series.index) if len(new_series) > 0 or len(close_series) > 0 else pd.PeriodIndex([], freq=freq_char)
    result = pd.DataFrame({"_period": all_periods})
    result["new_published"] = result["_period"].map(new_series).fillna(0).astype(int)
    result["closing"] = result["_period"].map(close_series).fillna(0).astype(int)
    result["active_net"] = result["new_published"] - result["closing"]
    result["date"] = result["_period"].dt.to_timestamp()
    result = result[out_cols].sort_values("date").reset_index(drop=True)

    logger.info("supply_pipeline: %d periods", len(result))
    return result


def avg_time_to_close(tenders_df: pd.DataFrame) -> pd.DataFrame:
    """Average days from publish to close, by region and tender type.

    Only considers closed tenders (status_code == 5). Tenders without both
    publish_date and deadline are excluded.

    Args:
        tenders_df: DataFrame with 'publish_date', 'deadline', 'status_code',
            'region', and 'tender_type'.

    Returns:
        DataFrame with columns: region, tender_type, avg_days, median_days, count.
    """
    out_cols = ["region", "tender_type", "avg_days", "median_days", "count"]
    if tenders_df.empty:
        return pd.DataFrame(columns=out_cols)

    df = tenders_df.copy()

    # Filter to closed tenders (status_code 5)
    if "status_code" in df.columns:
        df["status_code"] = pd.to_numeric(df["status_code"], errors="coerce")
        df = df[df["status_code"] == 5]

    if df.empty:
        return pd.DataFrame(columns=out_cols)

    df["_pub"] = _ensure_datetime(df, "publish_date")
    df["_dead"] = _ensure_datetime(df, "deadline")
    df = df.dropna(subset=["_pub", "_dead"])

    if df.empty:
        return pd.DataFrame(columns=out_cols)

    df["_days"] = (df["_dead"] - df["_pub"]).dt.days

    # Ensure groupby columns exist
    if "region" not in df.columns:
        df["region"] = "unknown"
    if "tender_type" not in df.columns:
        df["tender_type"] = "unknown"

    result = (
        df.groupby(["region", "tender_type"])["_days"]
        .agg(["mean", "median", "count"])
        .reset_index()
    )
    result.columns = ["region", "tender_type", "avg_days", "median_days", "count"]
    result["avg_days"] = result["avg_days"].round(1)
    result["median_days"] = result["median_days"].round(1)

    logger.info("avg_time_to_close: %d groups", len(result))
    return result


def brochure_publication_rate(
    tenders_df: pd.DataFrame,
    freq: str = "M",
) -> pd.DataFrame:
    """Percentage of tenders with published brochure over time.

    Uses the 'published_booklet' boolean column to determine whether a
    tender has an associated brochure.

    Args:
        tenders_df: DataFrame with 'publish_date' and 'published_booklet'.
        freq: Pandas offset alias.

    Returns:
        DataFrame with columns: date, total, with_brochure, pct.
    """
    out_cols = ["date", "total", "with_brochure", "pct"]
    if tenders_df.empty:
        return pd.DataFrame(columns=out_cols)

    df = tenders_df.copy()
    df["_pub"] = _ensure_datetime(df, "publish_date")
    df = df.dropna(subset=["_pub"])

    if df.empty:
        return pd.DataFrame(columns=out_cols)

    if "published_booklet" not in df.columns:
        df["published_booklet"] = False

    # Coerce to boolean
    df["_has_brochure"] = df["published_booklet"].astype(bool)

    offset = _safe_freq(freq)
    df["_period"] = df["_pub"].dt.to_period(offset[0])

    totals = df.groupby("_period").size().rename("total")
    with_brochure = df[df["_has_brochure"]].groupby("_period").size().rename("with_brochure")

    result = pd.DataFrame({"total": totals, "with_brochure": with_brochure}).fillna(0).astype(int)
    result["pct"] = np.where(
        result["total"] > 0,
        (result["with_brochure"] / result["total"] * 100).round(1),
        0.0,
    )
    result = result.reset_index()
    result["date"] = result["_period"].dt.to_timestamp()
    result = result[out_cols].sort_values("date").reset_index(drop=True)

    logger.info("brochure_publication_rate: %d periods", len(result))
    return result


# ============================================================================
# 3. SEASONAL PATTERNS
# ============================================================================

def monthly_publication_distribution(tenders_df: pd.DataFrame) -> pd.DataFrame:
    """Monthly distribution of tender publications aggregated across years.

    For each calendar month (1-12), calculates the average and total number
    of tenders published in that month across all years in the dataset.

    Args:
        tenders_df: DataFrame with 'publish_date'.

    Returns:
        DataFrame with columns: month, month_name_he, avg_count, total_count.
    """
    out_cols = ["month", "month_name_he", "avg_count", "total_count"]
    if tenders_df.empty:
        return pd.DataFrame(columns=out_cols)

    df = tenders_df.copy()
    df["_pub"] = _ensure_datetime(df, "publish_date")
    df = df.dropna(subset=["_pub"])

    if df.empty:
        return pd.DataFrame(columns=out_cols)

    df["_month"] = df["_pub"].dt.month
    df["_year"] = df["_pub"].dt.year

    yearly = df.groupby(["_year", "_month"]).size().reset_index(name="count")
    n_years = yearly["_year"].nunique()

    monthly = yearly.groupby("_month")["count"].agg(["sum", "mean"]).reset_index()
    monthly.columns = ["month", "total_count", "avg_count"]
    monthly["avg_count"] = monthly["avg_count"].round(1)
    monthly["total_count"] = monthly["total_count"].astype(int)
    monthly["month_name_he"] = monthly["month"].map(_MONTH_NAMES_HE)

    result = monthly[out_cols].sort_values("month").reset_index(drop=True)
    logger.info(
        "monthly_publication_distribution: %d months, %d years",
        len(result), n_years,
    )
    return result


def closing_date_clustering(tenders_df: pd.DataFrame) -> pd.DataFrame:
    """Clustering of closing dates by day-of-week and month.

    Produces a count for each (month, day_of_week) pair, suitable for
    rendering as a heatmap.

    Args:
        tenders_df: DataFrame with 'deadline'.

    Returns:
        DataFrame with columns: month, day_of_week, count.
    """
    out_cols = ["month", "day_of_week", "count"]
    if tenders_df.empty:
        return pd.DataFrame(columns=out_cols)

    df = tenders_df.copy()
    df["_dead"] = _ensure_datetime(df, "deadline")
    df = df.dropna(subset=["_dead"])

    if df.empty:
        return pd.DataFrame(columns=out_cols)

    df["_month"] = df["_dead"].dt.month
    df["_dow"] = df["_dead"].dt.dayofweek  # Monday=0, Sunday=6

    result = (
        df.groupby(["_month", "_dow"])
        .size()
        .reset_index(name="count")
    )
    result.columns = ["month", "day_of_week", "count"]
    result = result.sort_values(["month", "day_of_week"]).reset_index(drop=True)

    logger.info("closing_date_clustering: %d cells", len(result))
    return result


def fiscal_year_effects(tenders_df: pd.DataFrame) -> pd.DataFrame:
    """Government fiscal year effects on tender volume.

    Israel's fiscal year is January-December. Breaks data into fiscal
    quarters (Q1=Jan-Mar, Q2=Apr-Jun, Q3=Jul-Sep, Q4=Oct-Dec) and
    counts tenders plus housing units per quarter per year.

    Args:
        tenders_df: DataFrame with 'publish_date' and optionally 'units'.

    Returns:
        DataFrame with columns: fiscal_quarter, year, count, units.
    """
    out_cols = ["fiscal_quarter", "year", "count", "units"]
    if tenders_df.empty:
        return pd.DataFrame(columns=out_cols)

    df = tenders_df.copy()
    df["_pub"] = _ensure_datetime(df, "publish_date")
    df = df.dropna(subset=["_pub"])

    if df.empty:
        return pd.DataFrame(columns=out_cols)

    if "units" not in df.columns:
        df["units"] = 0
    df["units"] = pd.to_numeric(df["units"], errors="coerce").fillna(0).astype(int)

    df["_year"] = df["_pub"].dt.year
    df["_quarter"] = df["_pub"].dt.quarter  # Q1=Jan-Mar (same as fiscal)

    result = (
        df.groupby(["_quarter", "_year"])
        .agg(count=("_pub", "size"), units=("units", "sum"))
        .reset_index()
    )
    result.columns = ["fiscal_quarter", "year", "count", "units"]
    result["units"] = result["units"].astype(int)
    result = result.sort_values(["year", "fiscal_quarter"]).reset_index(drop=True)

    logger.info("fiscal_year_effects: %d quarter-year buckets", len(result))
    return result


# ============================================================================
# 4. PRICE ANALYTICS
# ============================================================================

def price_trends_by_region(
    prices_df: pd.DataFrame,
    tenders_df: pd.DataFrame,
) -> pd.DataFrame:
    """Average winning price per sqm by region over time.

    Joins price data with tender metadata to get region and publish_date,
    then computes average price per square metre of land area per region
    per month.

    Args:
        prices_df: DataFrame from tender_prices table with 'tender_id',
            'winning_bid', 'land_area'.
        tenders_df: DataFrame with 'tender_id', 'region', 'publish_date'.

    Returns:
        DataFrame with columns: date, region, avg_price_per_sqm, count.
    """
    out_cols = ["date", "region", "avg_price_per_sqm", "count"]
    if prices_df.empty or tenders_df.empty:
        return pd.DataFrame(columns=out_cols)

    prices = prices_df.copy()
    # Select only the columns we need from tenders to avoid merge conflicts
    tender_cols = ["tender_id"]
    if "region" in tenders_df.columns:
        tender_cols.append("region")
    if "publish_date" in tenders_df.columns:
        tender_cols.append("publish_date")
    tenders = tenders_df[tender_cols].copy()

    # Filter to rows with valid winning_bid and land_area
    prices["winning_bid"] = pd.to_numeric(prices.get("winning_bid"), errors="coerce")
    prices["land_area"] = pd.to_numeric(prices.get("land_area"), errors="coerce")
    prices = prices.dropna(subset=["winning_bid", "land_area"])
    prices = prices[(prices["winning_bid"] > 0) & (prices["land_area"] > 0)]

    if prices.empty:
        return pd.DataFrame(columns=out_cols)

    prices["price_per_sqm"] = prices["winning_bid"] / prices["land_area"]

    # Drop any conflicting columns from prices before merging
    drop_cols = [c for c in ["region", "publish_date"] if c in prices.columns]
    if drop_cols:
        prices = prices.drop(columns=drop_cols)

    merged = prices.merge(tenders, on="tender_id", how="left")
    merged["_pub"] = _ensure_datetime(merged, "publish_date")

    if "region" not in merged.columns:
        return pd.DataFrame(columns=out_cols)

    merged = merged.dropna(subset=["_pub", "region"])

    if merged.empty:
        return pd.DataFrame(columns=out_cols)

    merged["_period"] = merged["_pub"].dt.to_period("M")

    result = (
        merged.groupby(["_period", "region"])
        .agg(avg_price_per_sqm=("price_per_sqm", "mean"), count=("price_per_sqm", "size"))
        .reset_index()
    )
    result["date"] = result["_period"].dt.to_timestamp()
    result["avg_price_per_sqm"] = result["avg_price_per_sqm"].round(2)
    result = result[out_cols].sort_values("date").reset_index(drop=True)

    logger.info("price_trends_by_region: %d rows", len(result))
    return result


def taba_analysis_summary(taba_df: pd.DataFrame) -> pd.DataFrame:
    """Summary of taba (zoning plan) analytics.

    Passes through key fields from the taba_analytics table and computes
    a tender_rate_per_year metric (tender_count / years between first_seen
    and last_seen).

    Args:
        taba_df: DataFrame from taba_analytics table.

    Returns:
        DataFrame with columns: plan_number, tender_count, total_units,
        total_land_area, avg_floor_price, avg_winning_bid, price_premium_pct,
        first_seen, last_seen, tender_rate_per_year.
    """
    out_cols = [
        "plan_number", "tender_count", "total_units", "total_land_area",
        "avg_appraisal_price", "avg_floor_price", "avg_winning_bid",
        "premium_vs_appraisal_pct", "premium_vs_floor_pct",
        "first_seen", "last_seen", "tender_rate_per_year",
    ]
    if taba_df.empty:
        return pd.DataFrame(columns=out_cols)

    df = taba_df.copy()

    # Compute tender_rate_per_year (strip TZ for Supabase compat)
    df["_first"] = pd.to_datetime(df.get("first_seen"), errors="coerce", utc=True).dt.tz_localize(None)
    df["_last"] = pd.to_datetime(df.get("last_seen"), errors="coerce", utc=True).dt.tz_localize(None)
    span_days = (df["_last"] - df["_first"]).dt.days.fillna(0)
    span_years = span_days / 365.25
    df["tender_count"] = pd.to_numeric(df.get("tender_count", 0), errors="coerce").fillna(0)
    df["tender_rate_per_year"] = np.where(
        span_years > 0,
        (df["tender_count"] / span_years).round(2),
        df["tender_count"],  # if span is 0, rate = count (published in same period)
    )

    # Ensure expected columns exist
    for col in out_cols:
        if col not in df.columns:
            df[col] = None

    result = df[out_cols].reset_index(drop=True)
    logger.info("taba_analysis_summary: %d plans", len(result))
    return result


def price_premium_analysis(prices_df: pd.DataFrame) -> pd.DataFrame:
    """Winning bid premium/discount vs RMI appraisal (שומה), with floor price.

    Primary benchmark is the appraisal price (מחיר שומה רמ"י) — the
    independent valuation.  Floor price (מחיר סף) is kept as a reference
    column but is NOT the premium benchmark.

    Args:
        prices_df: DataFrame from tender_prices with 'tender_id',
            'appraisal_price', 'winning_bid', 'floor_price'.
            Optionally 'region'.

    Returns:
        DataFrame with columns: tender_id, appraisal_price, floor_price,
        winning_price, premium_vs_appraisal_pct, premium_vs_floor_pct, region.
    """
    out_cols = [
        "tender_id", "appraisal_price", "floor_price", "winning_price",
        "premium_vs_appraisal_pct", "premium_vs_floor_pct", "region",
    ]
    if prices_df.empty:
        return pd.DataFrame(columns=out_cols)

    df = prices_df.copy()
    df["appraisal_price"] = pd.to_numeric(df.get("appraisal_price"), errors="coerce")
    df["floor_price"] = pd.to_numeric(df.get("floor_price"), errors="coerce")
    df["winning_bid"] = pd.to_numeric(df.get("winning_bid"), errors="coerce")

    # Require at least winning_bid and appraisal to compute primary premium
    df = df.dropna(subset=["winning_bid"])
    df = df[df["winning_bid"] > 0]

    if df.empty:
        return pd.DataFrame(columns=out_cols)

    # Primary premium: vs appraisal (שומה)
    df["premium_vs_appraisal_pct"] = np.where(
        df["appraisal_price"].notna() & (df["appraisal_price"] > 0),
        ((df["winning_bid"] - df["appraisal_price"]) / df["appraisal_price"] * 100).round(2),
        np.nan,
    )

    # Secondary: vs floor (מחיר סף)
    df["premium_vs_floor_pct"] = np.where(
        df["floor_price"].notna() & (df["floor_price"] > 0),
        ((df["winning_bid"] - df["floor_price"]) / df["floor_price"] * 100).round(2),
        np.nan,
    )

    if "region" not in df.columns:
        df["region"] = None

    result = df.rename(columns={"winning_bid": "winning_price"})

    for col in out_cols:
        if col not in result.columns:
            result[col] = None

    result = result[out_cols].reset_index(drop=True)
    logger.info("price_premium_analysis: %d rows with premium data", len(result))
    return result


# ============================================================================
# 5. COMPETITIVE INTELLIGENCE
# ============================================================================

def tender_lifecycle_analysis(
    tenders_df: pd.DataFrame,
    brochure_col: str = "published_booklet",
) -> pd.DataFrame:
    """Compute lifecycle duration statistics for closed tenders by region and type.

    For closed tenders (status_code == 5), calculates the average and median
    number of days from publish_date to deadline, grouped by region and
    tender_type.

    Args:
        tenders_df: DataFrame with 'publish_date', 'deadline', 'status_code',
            'region', and 'tender_type' columns.
        brochure_col: Name of the brochure availability column (unused in
            computation but accepted for interface consistency).

    Returns:
        DataFrame with columns: region, tender_type, avg_lifecycle_days,
        median_lifecycle_days, count.  Empty DataFrame if no closed tenders
        with valid dates exist.
    """
    out_cols = ["region", "tender_type", "avg_lifecycle_days", "median_lifecycle_days", "count"]
    if tenders_df.empty:
        logger.warning("tender_lifecycle_analysis: empty input")
        return pd.DataFrame(columns=out_cols)

    df = tenders_df.copy()

    # Filter to closed tenders
    if "status_code" in df.columns:
        df["status_code"] = pd.to_numeric(df["status_code"], errors="coerce")
        df = df[df["status_code"] == 5]

    if df.empty:
        logger.info("tender_lifecycle_analysis: no closed tenders found")
        return pd.DataFrame(columns=out_cols)

    df["_pub"] = _ensure_datetime(df, "publish_date")
    df["_dead"] = _ensure_datetime(df, "deadline")
    df = df.dropna(subset=["_pub", "_dead"])

    if df.empty:
        logger.info("tender_lifecycle_analysis: no valid date pairs in closed tenders")
        return pd.DataFrame(columns=out_cols)

    df["_lifecycle_days"] = (df["_dead"] - df["_pub"]).dt.days

    # Ensure groupby columns exist
    if "region" not in df.columns:
        df["region"] = "unknown"
    if "tender_type" not in df.columns:
        df["tender_type"] = "unknown"

    result = (
        df.groupby(["region", "tender_type"])["_lifecycle_days"]
        .agg(["mean", "median", "count"])
        .reset_index()
    )
    result.columns = out_cols
    result["avg_lifecycle_days"] = result["avg_lifecycle_days"].round(1)
    result["median_lifecycle_days"] = result["median_lifecycle_days"].round(1)

    logger.info("tender_lifecycle_analysis: %d groups computed", len(result))
    return result


def deadline_overlap_analysis(
    tenders_df: pd.DataFrame,
    window_days: int = 7,
) -> pd.DataFrame:
    """Identify weeks with overlapping tender deadlines and assess competition.

    Groups tenders by ISO week of their deadline date and counts how many
    deadlines fall in each week, along with which regions are involved.

    Args:
        tenders_df: DataFrame with 'deadline' and 'region' columns.
        window_days: Window size in days for grouping (used to define
            week-based bucketing; currently groups by ISO week).

    Returns:
        DataFrame with columns: week_start, tender_count, regions_involved,
        competition_level ('low' / 'medium' / 'high').
        low: 1-2 tenders, medium: 3-5, high: 6+.
    """
    out_cols = ["week_start", "tender_count", "regions_involved", "competition_level"]
    if tenders_df.empty:
        logger.warning("deadline_overlap_analysis: empty input")
        return pd.DataFrame(columns=out_cols)

    df = tenders_df.copy()
    df["_dead"] = _ensure_datetime(df, "deadline")
    df = df.dropna(subset=["_dead"])

    if df.empty:
        logger.info("deadline_overlap_analysis: no valid deadlines")
        return pd.DataFrame(columns=out_cols)

    if "region" not in df.columns:
        df["region"] = "unknown"

    # Bucket by week start (Monday)
    df["_week_start"] = df["_dead"].dt.to_period("W").apply(lambda p: p.start_time)

    grouped = df.groupby("_week_start").agg(
        tender_count=("_dead", "size"),
        regions_involved=("region", lambda x: ", ".join(sorted(x.dropna().unique()))),
    ).reset_index()

    grouped.rename(columns={"_week_start": "week_start"}, inplace=True)

    grouped["competition_level"] = np.where(
        grouped["tender_count"] >= 6, "high",
        np.where(grouped["tender_count"] >= 3, "medium", "low"),
    )

    result = grouped[out_cols].sort_values("week_start").reset_index(drop=True)
    logger.info("deadline_overlap_analysis: %d weeks analysed", len(result))
    return result


def region_saturation_index(
    tenders_df: pd.DataFrame,
    lookback_months: int = 6,
) -> pd.DataFrame:
    """Compute a saturation score per region based on active tender density.

    Looks at tenders published within the last *lookback_months* and counts
    active vs closed tenders per region.  The saturation_score is the
    region's active count normalised to 0-100 relative to the maximum active
    count across all regions.

    Trend is determined by comparing the first half of the lookback window
    to the second half:
        - 'saturating': second half has more active tenders
        - 'opening': second half has fewer active tenders
        - 'stable': roughly equal (within 20% tolerance)

    Args:
        tenders_df: DataFrame with 'publish_date', 'status_code', 'region',
            and optionally 'units'.
        lookback_months: Number of months to look back from today.

    Returns:
        DataFrame with columns: region, active_count, closed_count,
        total_units, saturation_score, trend.
    """
    out_cols = ["region", "active_count", "closed_count", "total_units",
                "saturation_score", "trend"]
    if tenders_df.empty or "region" not in tenders_df.columns:
        logger.warning("region_saturation_index: empty input or missing 'region'")
        return pd.DataFrame(columns=out_cols)

    df = tenders_df.copy()
    df["_pub"] = _ensure_datetime(df, "publish_date")
    df = df.dropna(subset=["_pub", "region"])

    if df.empty:
        return pd.DataFrame(columns=out_cols)

    # Filter to lookback window
    now = pd.Timestamp(datetime.now())
    cutoff = now - pd.DateOffset(months=lookback_months)
    df = df[df["_pub"] >= cutoff]

    if df.empty:
        return pd.DataFrame(columns=out_cols)

    # Classify active vs closed
    if "status_code" in df.columns:
        df["status_code"] = pd.to_numeric(df["status_code"], errors="coerce")
        df["_is_closed"] = df["status_code"] == 5
    else:
        df["_is_closed"] = False

    # Units
    if "units" not in df.columns:
        df["units"] = 0
    df["units"] = pd.to_numeric(df["units"], errors="coerce").fillna(0)

    # Group by region
    region_stats = df.groupby("region").agg(
        active_count=("_is_closed", lambda x: int((~x).sum())),
        closed_count=("_is_closed", lambda x: int(x.sum())),
        total_units=("units", "sum"),
    ).reset_index()

    region_stats["total_units"] = region_stats["total_units"].astype(int)

    # Saturation score: normalize active_count to 0-100
    max_active = region_stats["active_count"].max()
    region_stats["saturation_score"] = np.where(
        max_active > 0,
        (region_stats["active_count"] / max_active * 100).round(1),
        0.0,
    )

    # Trend: compare first half vs second half of lookback window
    midpoint = cutoff + (now - cutoff) / 2
    first_half = df[df["_pub"] < midpoint]
    second_half = df[df["_pub"] >= midpoint]

    first_counts = first_half[~first_half["_is_closed"]].groupby("region").size()
    second_counts = second_half[~second_half["_is_closed"]].groupby("region").size()

    trends: Dict[str, str] = {}
    for region in region_stats["region"]:
        fc = first_counts.get(region, 0)
        sc = second_counts.get(region, 0)
        if fc == 0 and sc == 0:
            trends[region] = "stable"
        elif fc == 0:
            trends[region] = "saturating"
        elif abs(sc - fc) / fc <= 0.2:
            trends[region] = "stable"
        elif sc > fc:
            trends[region] = "saturating"
        else:
            trends[region] = "opening"

    region_stats["trend"] = region_stats["region"].map(trends)

    result = region_stats[out_cols].sort_values("saturation_score", ascending=False).reset_index(drop=True)
    logger.info("region_saturation_index: %d regions scored", len(result))
    return result


def document_intelligence(tenders_df: pd.DataFrame) -> pd.DataFrame:
    """Analyse document availability and brochure rates per region.

    Computes average document count and brochure availability percentage
    per region.

    Args:
        tenders_df: DataFrame with 'region', 'docs_count', and
            'published_booklet' columns.

    Returns:
        DataFrame with columns: region, avg_docs, brochure_rate_pct,
        total_tenders.
    """
    out_cols = ["region", "avg_docs", "brochure_rate_pct", "total_tenders"]
    if tenders_df.empty or "region" not in tenders_df.columns:
        logger.warning("document_intelligence: empty input or missing 'region'")
        return pd.DataFrame(columns=out_cols)

    df = tenders_df.copy()
    df = df.dropna(subset=["region"])

    if df.empty:
        return pd.DataFrame(columns=out_cols)

    if "docs_count" not in df.columns:
        df["docs_count"] = 0
    df["docs_count"] = pd.to_numeric(df["docs_count"], errors="coerce").fillna(0)

    if "published_booklet" not in df.columns:
        df["published_booklet"] = False
    df["_has_brochure"] = df["published_booklet"].astype(bool)

    result = df.groupby("region").agg(
        avg_docs=("docs_count", "mean"),
        brochure_rate_pct=("_has_brochure", "mean"),
        total_tenders=("region", "size"),
    ).reset_index()

    result["avg_docs"] = result["avg_docs"].round(1)
    result["brochure_rate_pct"] = (result["brochure_rate_pct"] * 100).round(1)

    result = result[out_cols].sort_values("total_tenders", ascending=False).reset_index(drop=True)
    logger.info("document_intelligence: %d regions analysed", len(result))
    return result


def volume_moving_averages(
    tenders_df: pd.DataFrame,
    windows: Optional[List[int]] = None,
) -> pd.DataFrame:
    """Compute rolling tender publication counts for given day windows.

    For each calendar day in the dataset, counts how many tenders were
    published within the trailing N days for each window size.

    Args:
        tenders_df: DataFrame with 'publish_date'.
        windows: List of rolling window sizes in days. Defaults to
            [30, 60, 90].

    Returns:
        DataFrame with columns: date, ma_<N> for each window N.
        Empty DataFrame if no valid publish dates exist.
    """
    if windows is None:
        windows = [30, 60, 90]

    out_cols = ["date"] + [f"ma_{w}" for w in windows]

    if tenders_df.empty:
        logger.warning("volume_moving_averages: empty input")
        return pd.DataFrame(columns=out_cols)

    df = tenders_df.copy()
    df["_pub"] = _ensure_datetime(df, "publish_date")
    df = df.dropna(subset=["_pub"])

    if df.empty:
        return pd.DataFrame(columns=out_cols)

    # Create daily counts
    daily = df.groupby(df["_pub"].dt.date).size().rename("count")
    daily.index = pd.to_datetime(daily.index)

    # Fill in missing days with zero
    full_range = pd.date_range(start=daily.index.min(), end=daily.index.max(), freq="D")
    daily = daily.reindex(full_range, fill_value=0)

    result = pd.DataFrame({"date": daily.index})
    for w in windows:
        result[f"ma_{w}"] = daily.rolling(window=w, min_periods=1).sum().values.astype(int)

    result = result[out_cols].reset_index(drop=True)
    logger.info("volume_moving_averages: %d days, windows=%s", len(result), windows)
    return result


def yoy_comparison(tenders_df: pd.DataFrame) -> pd.DataFrame:
    """Compare tender publication volume: current year vs previous year by month.

    For each month, counts tenders published in the current calendar year
    and the previous calendar year, plus computes the percentage change.

    Args:
        tenders_df: DataFrame with 'publish_date'.

    Returns:
        DataFrame with columns: month, current_year_count,
        previous_year_count, change_pct.
        Months are 1-12.  change_pct is NaN when previous_year_count is 0.
    """
    out_cols = ["month", "current_year_count", "previous_year_count", "change_pct"]
    if tenders_df.empty:
        logger.warning("yoy_comparison: empty input")
        return pd.DataFrame(columns=out_cols)

    df = tenders_df.copy()
    df["_pub"] = _ensure_datetime(df, "publish_date")
    df = df.dropna(subset=["_pub"])

    if df.empty:
        return pd.DataFrame(columns=out_cols)

    current_year = df["_pub"].dt.year.max()
    previous_year = current_year - 1

    df["_year"] = df["_pub"].dt.year
    df["_month"] = df["_pub"].dt.month

    current = df[df["_year"] == current_year].groupby("_month").size().rename("current_year_count")
    previous = df[df["_year"] == previous_year].groupby("_month").size().rename("previous_year_count")

    all_months = pd.Index(range(1, 13), name="_month")
    result = pd.DataFrame({
        "month": all_months,
        "current_year_count": current.reindex(all_months, fill_value=0).values,
        "previous_year_count": previous.reindex(all_months, fill_value=0).values,
    })

    result["change_pct"] = np.where(
        result["previous_year_count"] > 0,
        ((result["current_year_count"] - result["previous_year_count"])
         / result["previous_year_count"] * 100).round(1),
        np.where(result["current_year_count"] > 0, np.nan, 0.0),
    )

    result = result[out_cols].reset_index(drop=True)
    logger.info(
        "yoy_comparison: current_year=%d, previous_year=%d",
        current_year, previous_year,
    )
    return result


# ============================================================================
# 6. SCORING SYSTEM
# ============================================================================

def _urgency_score(days_to_deadline: Optional[float]) -> float:
    """Compute urgency sub-score from days to deadline.

    Args:
        days_to_deadline: Calendar days until deadline. None/NaN yields 0.

    Returns:
        Score 0-100.
    """
    if days_to_deadline is None or (isinstance(days_to_deadline, float) and np.isnan(days_to_deadline)):
        return 0.0
    d = float(days_to_deadline)
    if d < 0:
        return 0.0
    if d <= 7:
        return 100.0
    if d <= 14:
        return 80.0
    if d <= 30:
        return 60.0
    if d <= 60:
        return 40.0
    return 20.0


def _size_score(units: Optional[float], percentile_rank: float) -> float:
    """Compute size sub-score from units percentile rank.

    Args:
        units: Number of housing units (may be None/0).
        percentile_rank: Percentile rank (0-1) of units across all tenders.

    Returns:
        Score 0-100.
    """
    if units is None or (isinstance(units, float) and np.isnan(units)) or units <= 0:
        return 0.0
    return round(percentile_rank * 100, 1)


def _readiness_score(
    has_brochure: bool,
    docs_count: int,
) -> float:
    """Compute readiness sub-score.

    Formula: brochure=60 pts + docs_count*10 (max 40) => max 100.

    Args:
        has_brochure: Whether the tender has a published brochure.
        docs_count: Number of documents available.

    Returns:
        Score 0-100.
    """
    score = 0.0
    if has_brochure:
        score += 60.0
    doc_bonus = min(docs_count * 10, 40)
    score += doc_bonus
    return min(score, 100.0)


def _freshness_score(publish_date: Optional[pd.Timestamp]) -> float:
    """Compute freshness sub-score based on how recently the tender was published.

    Args:
        publish_date: The tender's publish date. None yields 0.

    Returns:
        Score 0-100.
    """
    if publish_date is None or pd.isna(publish_date):
        return 0.0
    days_old = (pd.Timestamp(datetime.now()) - pd.Timestamp(publish_date)).days
    if days_old < 7:
        return 100.0
    if days_old < 30:
        return 80.0
    if days_old < 90:
        return 50.0
    if days_old < 180:
        return 30.0
    return 10.0


def _location_score(
    region: Optional[str],
    region_density: Dict[str, float],
) -> float:
    """Compute location sub-score based on regional tender density.

    Higher density = more market activity = higher score.

    Args:
        region: The tender's region name.
        region_density: Dict mapping region -> density percentile (0-1).

    Returns:
        Score 0-100.
    """
    if not region or region not in region_density:
        return 50.0  # neutral default
    return round(region_density[region] * 100, 1)


def calculate_tender_score(
    row: pd.Series,
    region_density: Optional[Dict[str, float]] = None,
    units_percentile: Optional[float] = None,
) -> dict:
    """Calculate composite score for a single tender.

    Uses fixed weights: urgency=20%, size=20%, readiness=25%,
    location=20%, freshness=15%.

    Args:
        row: A pandas Series representing one tender.
        region_density: Dict mapping region -> density percentile (0-1).
            If None, location_score defaults to 50.
        units_percentile: The percentile rank (0-1) of this tender's units.
            If None, size_score is based on raw units (0 or 50).

    Returns:
        Dict with keys: total_score, urgency_score, size_score,
        readiness_score, location_score, freshness_score.
    """
    if region_density is None:
        region_density = {}

    # Urgency
    days_to_deadline = row.get("days_to_deadline")
    if days_to_deadline is None and "deadline" in row.index:
        deadline = pd.to_datetime(row.get("deadline"), errors="coerce") if row.get("deadline") is not None else None
        if deadline is not None and not pd.isna(deadline):
            # Strip TZ if present (Supabase returns UTC-aware timestamps)
            if hasattr(deadline, "tzinfo") and deadline.tzinfo is not None:
                deadline = deadline.tz_convert(None)
            days_to_deadline = (deadline - pd.Timestamp(datetime.now())).days
    urg = _urgency_score(days_to_deadline)

    # Size
    units = pd.to_numeric(row.get("units"), errors="coerce") if row.get("units") is not None else None
    pct = units_percentile if units_percentile is not None else 0.5
    sz = _size_score(units, pct)

    # Readiness
    has_brochure = bool(row.get("published_booklet", False))
    docs_count = int(row.get("docs_count", 0) or 0)
    rdy = _readiness_score(has_brochure, docs_count)

    # Location
    region = row.get("region")
    loc = _location_score(region, region_density)

    # Freshness
    pub_date = row.get("publish_date")
    if pub_date is not None:
        pub_date = pd.to_datetime(pub_date, errors="coerce")
        # Strip TZ if present (Supabase returns UTC-aware timestamps)
        if pub_date is not None and not pd.isna(pub_date) and hasattr(pub_date, "tzinfo") and pub_date.tzinfo is not None:
            pub_date = pub_date.tz_convert(None)
    fresh = _freshness_score(pub_date)

    # Weighted total
    total = (
        urg * _SCORE_WEIGHTS["urgency"]
        + sz * _SCORE_WEIGHTS["size"]
        + rdy * _SCORE_WEIGHTS["readiness"]
        + loc * _SCORE_WEIGHTS["location"]
        + fresh * _SCORE_WEIGHTS["freshness"]
    )

    return {
        "total_score": round(total, 1),
        "urgency_score": urg,
        "size_score": sz,
        "readiness_score": rdy,
        "location_score": loc,
        "freshness_score": fresh,
    }


def score_all_tenders(tenders_df: pd.DataFrame) -> pd.DataFrame:
    """Score all tenders, returning the DataFrame with score columns added.

    Computes region density from tender counts and units percentile ranks
    before scoring each row.

    Args:
        tenders_df: DataFrame with tender data.

    Returns:
        Copy of tenders_df with columns added: total_score, urgency_score,
        size_score, readiness_score, location_score, freshness_score.
    """
    score_cols = [
        "total_score", "urgency_score", "size_score",
        "readiness_score", "location_score", "freshness_score",
    ]
    if tenders_df.empty:
        df = tenders_df.copy()
        for col in score_cols:
            df[col] = pd.Series(dtype="float64")
        return df

    df = tenders_df.copy()

    # Pre-compute region density (percentile rank of tender count per region)
    region_density: Dict[str, float] = {}
    if "region" in df.columns:
        counts = df["region"].value_counts()
        if len(counts) > 0:
            ranked = counts.rank(pct=True)
            region_density = ranked.to_dict()

    # Pre-compute units percentile rank
    units_pctile: Dict[int, float] = {}
    if "units" in df.columns:
        numeric_units = pd.to_numeric(df["units"], errors="coerce").fillna(0)
        ranked_units = numeric_units.rank(pct=True)
        units_pctile = ranked_units.to_dict()  # index -> percentile

    # Score each row
    scores: list[dict] = []
    for idx, row in df.iterrows():
        pct = units_pctile.get(idx, 0.5)
        score = calculate_tender_score(row, region_density, pct)
        scores.append(score)

    score_df = pd.DataFrame(scores, index=df.index)
    for col in score_cols:
        df[col] = score_df[col]

    logger.info(
        "score_all_tenders: scored %d tenders, mean=%.1f, median=%.1f",
        len(df),
        df["total_score"].mean(),
        df["total_score"].median(),
    )
    return df


def get_top_tenders(tenders_df: pd.DataFrame, n: int = 20) -> pd.DataFrame:
    """Get top N scored tenders.

    If the input DataFrame does not already have a 'total_score' column,
    runs score_all_tenders first.

    Args:
        tenders_df: DataFrame with tender data (with or without scores).
        n: Number of top tenders to return.

    Returns:
        Top N tenders sorted by total_score descending.
    """
    if tenders_df.empty:
        return tenders_df

    df = tenders_df.copy()
    if "total_score" not in df.columns:
        df = score_all_tenders(df)

    return df.nlargest(n, "total_score").reset_index(drop=True)


def get_score_distribution(tenders_df: pd.DataFrame) -> dict:
    """Returns histogram data for score distribution.

    If the input DataFrame does not already have a 'total_score' column,
    runs score_all_tenders first.

    Args:
        tenders_df: DataFrame with tender data.

    Returns:
        Dict with keys:
            bins: list of bin edge values
            counts: list of counts per bin
            mean: float
            median: float
            std: float
    """
    if tenders_df.empty:
        return {"bins": [], "counts": [], "mean": 0.0, "median": 0.0, "std": 0.0}

    df = tenders_df.copy()
    if "total_score" not in df.columns:
        df = score_all_tenders(df)

    scores = df["total_score"].dropna()
    if scores.empty:
        return {"bins": [], "counts": [], "mean": 0.0, "median": 0.0, "std": 0.0}

    counts_arr, bins_arr = np.histogram(scores, bins=10, range=(0, 100))

    return {
        "bins": bins_arr.tolist(),
        "counts": counts_arr.tolist(),
        "mean": round(float(scores.mean()), 1),
        "median": round(float(scores.median()), 1),
        "std": round(float(scores.std()), 1),
    }
