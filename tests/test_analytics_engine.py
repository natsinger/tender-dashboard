"""
Tests for the analytics_engine module.

Covers all six sections: regional hotspot analysis, supply pipeline,
seasonal patterns, price analytics, competitive intelligence, and
the scoring system.  Uses synthetic DataFrames to exercise normal cases,
edge cases (empty DFs, single row, missing columns), and scoring with
known expected outputs.
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from analytics_engine import (
    avg_time_to_close,
    brochure_publication_rate,
    calculate_tender_score,
    closing_date_clustering,
    deadline_overlap_analysis,
    document_intelligence,
    fiscal_year_effects,
    get_score_distribution,
    get_top_tenders,
    monthly_publication_distribution,
    price_premium_analysis,
    price_trends_by_region,
    region_saturation_index,
    regional_momentum,
    regional_tender_volume,
    regional_units_volume,
    score_all_tenders,
    supply_pipeline,
    taba_analysis_summary,
    tender_lifecycle_analysis,
    volume_moving_averages,
    yoy_comparison,
)


# ============================================================================
# FIXTURES — synthetic DataFrames
# ============================================================================

@pytest.fixture
def sample_tenders() -> pd.DataFrame:
    """Realistic tenders DataFrame with 20 rows spanning 6 months."""
    now = pd.Timestamp(datetime.now())
    regions = ["מרכז", "צפון", "דרום", "ירושלים", "מרכז"]
    rows = []
    for i in range(20):
        pub = now - pd.DateOffset(days=30 * (i % 6) + i)
        deadline = pub + pd.DateOffset(days=60 + i * 5)
        rows.append({
            "tender_id": 20260001 + i,
            "tender_name": f"מכרז {i + 1}/2026",
            "region": regions[i % len(regions)],
            "city": f"עיר {i % 5}",
            "publish_date": pub,
            "deadline": deadline,
            "status_code": 5 if i % 4 == 0 else 1,
            "status": "נסגר" if i % 4 == 0 else "פעיל",
            "tender_type": "פומבי רגיל" if i % 3 != 0 else "מחיר מטרה",
            "tender_type_code": 1 if i % 3 != 0 else 5,
            "units": 10 + i * 5,
            "published_booklet": i % 2 == 0,
            "docs_count": i % 5,
        })
    return pd.DataFrame(rows)


@pytest.fixture
def sample_prices() -> pd.DataFrame:
    """Synthetic price rows for 10 tenders."""
    rows = []
    for i in range(10):
        rows.append({
            "tender_id": 20260001 + i,
            "tik_id": f"T{i:03d}",
            "land_area": 1000 + i * 200,
            "appraisal_price": 550000 + i * 60000,
            "floor_price": 500000 + i * 50000,
            "winning_bid": 600000 + i * 70000 if i % 3 != 2 else None,
            "region": ["מרכז", "צפון", "דרום"][i % 3],
        })
    return pd.DataFrame(rows)


@pytest.fixture
def sample_taba() -> pd.DataFrame:
    """Synthetic taba analytics rows."""
    return pd.DataFrame([
        {
            "plan_number": "306-001",
            "tender_count": 5,
            "total_units": 200,
            "total_land_area": 50000,
            "avg_appraisal_price": 500000,
            "avg_floor_price": 400000,
            "avg_winning_bid": 520000,
            "premium_vs_appraisal_pct": 4.0,
            "premium_vs_floor_pct": 30.0,
            "first_seen": "2024-01-15",
            "last_seen": "2025-06-20",
        },
        {
            "plan_number": "306-002",
            "tender_count": 2,
            "total_units": 80,
            "total_land_area": 12000,
            "avg_appraisal_price": 320000,
            "avg_floor_price": 300000,
            "avg_winning_bid": 350000,
            "premium_vs_appraisal_pct": 9.38,
            "premium_vs_floor_pct": 16.67,
            "first_seen": "2025-03-01",
            "last_seen": "2025-03-01",
        },
    ])


# ============================================================================
# 1. REGIONAL HOTSPOT ANALYSIS
# ============================================================================

class TestRegionalTenderVolume:
    """Tests for regional_tender_volume()."""

    def test_basic_output_shape(self, sample_tenders: pd.DataFrame) -> None:
        """Should return DataFrame with date, region, count columns."""
        result = regional_tender_volume(sample_tenders)
        assert list(result.columns) == ["date", "region", "count"]
        assert len(result) > 0

    def test_counts_are_positive(self, sample_tenders: pd.DataFrame) -> None:
        """All counts should be >= 1."""
        result = regional_tender_volume(sample_tenders)
        assert (result["count"] > 0).all()

    def test_empty_df(self) -> None:
        """Empty DataFrame should return empty result."""
        result = regional_tender_volume(pd.DataFrame())
        assert result.empty
        assert list(result.columns) == ["date", "region", "count"]

    def test_missing_region_column(self) -> None:
        """DataFrame without 'region' should return empty."""
        df = pd.DataFrame({"publish_date": [datetime.now()], "units": [10]})
        result = regional_tender_volume(df)
        assert result.empty

    def test_quarterly_freq(self, sample_tenders: pd.DataFrame) -> None:
        """Quarterly frequency should produce fewer rows than monthly."""
        monthly = regional_tender_volume(sample_tenders, freq="M")
        quarterly = regional_tender_volume(sample_tenders, freq="Q")
        assert len(quarterly) <= len(monthly)


class TestRegionalUnitsVolume:
    """Tests for regional_units_volume()."""

    def test_basic_output(self, sample_tenders: pd.DataFrame) -> None:
        """Should return DataFrame with date, region, units columns."""
        result = regional_units_volume(sample_tenders)
        assert list(result.columns) == ["date", "region", "units"]
        assert len(result) > 0

    def test_units_sum_matches(self, sample_tenders: pd.DataFrame) -> None:
        """Total units in result should match input total."""
        result = regional_units_volume(sample_tenders)
        total_result = result["units"].sum()
        total_input = sample_tenders["units"].sum()
        assert total_result == total_input

    def test_empty_df(self) -> None:
        """Empty input returns empty output."""
        result = regional_units_volume(pd.DataFrame())
        assert result.empty


class TestRegionalMomentum:
    """Tests for regional_momentum()."""

    def test_output_columns(self, sample_tenders: pd.DataFrame) -> None:
        """Should have the expected columns."""
        result = regional_momentum(sample_tenders, window_months=3)
        expected_cols = ["region", "recent_count", "previous_count", "change_pct", "direction"]
        assert list(result.columns) == expected_cols

    def test_direction_values(self, sample_tenders: pd.DataFrame) -> None:
        """Direction should only be 'up', 'down', or 'stable'."""
        result = regional_momentum(sample_tenders)
        assert set(result["direction"].unique()).issubset({"up", "down", "stable"})

    def test_empty_df(self) -> None:
        """Empty input returns empty output."""
        result = regional_momentum(pd.DataFrame())
        assert result.empty


# ============================================================================
# 2. SUPPLY PIPELINE ANALYSIS
# ============================================================================

class TestSupplyPipeline:
    """Tests for supply_pipeline()."""

    def test_output_columns(self, sample_tenders: pd.DataFrame) -> None:
        """Should have date, new_published, closing, active_net."""
        result = supply_pipeline(sample_tenders)
        assert list(result.columns) == ["date", "new_published", "closing", "active_net"]

    def test_net_equals_new_minus_closing(self, sample_tenders: pd.DataFrame) -> None:
        """active_net should equal new_published - closing for each row."""
        result = supply_pipeline(sample_tenders)
        computed_net = result["new_published"] - result["closing"]
        pd.testing.assert_series_equal(
            result["active_net"].reset_index(drop=True),
            computed_net.reset_index(drop=True),
            check_names=False,
        )

    def test_empty_df(self) -> None:
        """Empty input returns empty output."""
        result = supply_pipeline(pd.DataFrame())
        assert result.empty


class TestAvgTimeToClose:
    """Tests for avg_time_to_close()."""

    def test_only_closed_tenders(self, sample_tenders: pd.DataFrame) -> None:
        """Should only include tenders with status_code == 5."""
        result = avg_time_to_close(sample_tenders)
        # We know the fixture has status_code=5 for i%4==0, so 5 tenders
        assert result["count"].sum() == (sample_tenders["status_code"] == 5).sum()

    def test_output_columns(self, sample_tenders: pd.DataFrame) -> None:
        """Should have expected columns."""
        result = avg_time_to_close(sample_tenders)
        assert list(result.columns) == ["region", "tender_type", "avg_days", "median_days", "count"]

    def test_empty_df(self) -> None:
        """Empty input returns empty output."""
        result = avg_time_to_close(pd.DataFrame())
        assert result.empty

    def test_no_closed_tenders(self) -> None:
        """DataFrame with no status_code=5 should return empty."""
        df = pd.DataFrame({
            "tender_id": [1, 2],
            "status_code": [1, 3],
            "publish_date": [datetime.now()] * 2,
            "deadline": [datetime.now() + timedelta(days=30)] * 2,
            "region": ["מרכז", "צפון"],
            "tender_type": ["פומבי", "פומבי"],
        })
        result = avg_time_to_close(df)
        assert result.empty


class TestBrochurePublicationRate:
    """Tests for brochure_publication_rate()."""

    def test_pct_range(self, sample_tenders: pd.DataFrame) -> None:
        """All pct values should be between 0 and 100."""
        result = brochure_publication_rate(sample_tenders)
        assert (result["pct"] >= 0).all()
        assert (result["pct"] <= 100).all()

    def test_with_brochure_le_total(self, sample_tenders: pd.DataFrame) -> None:
        """with_brochure should never exceed total."""
        result = brochure_publication_rate(sample_tenders)
        assert (result["with_brochure"] <= result["total"]).all()


# ============================================================================
# 3. SEASONAL PATTERNS
# ============================================================================

class TestMonthlyPublicationDistribution:
    """Tests for monthly_publication_distribution()."""

    def test_month_range(self, sample_tenders: pd.DataFrame) -> None:
        """Months should be between 1 and 12."""
        result = monthly_publication_distribution(sample_tenders)
        assert result["month"].min() >= 1
        assert result["month"].max() <= 12

    def test_hebrew_month_names(self, sample_tenders: pd.DataFrame) -> None:
        """month_name_he should be populated."""
        result = monthly_publication_distribution(sample_tenders)
        assert result["month_name_he"].notna().all()

    def test_empty_df(self) -> None:
        """Empty input returns empty output."""
        result = monthly_publication_distribution(pd.DataFrame())
        assert result.empty


class TestClosingDateClustering:
    """Tests for closing_date_clustering()."""

    def test_output_columns(self, sample_tenders: pd.DataFrame) -> None:
        """Should have month, day_of_week, count columns."""
        result = closing_date_clustering(sample_tenders)
        assert list(result.columns) == ["month", "day_of_week", "count"]

    def test_day_of_week_range(self, sample_tenders: pd.DataFrame) -> None:
        """day_of_week should be 0-6."""
        result = closing_date_clustering(sample_tenders)
        assert result["day_of_week"].min() >= 0
        assert result["day_of_week"].max() <= 6


class TestFiscalYearEffects:
    """Tests for fiscal_year_effects()."""

    def test_quarter_range(self, sample_tenders: pd.DataFrame) -> None:
        """fiscal_quarter should be 1-4."""
        result = fiscal_year_effects(sample_tenders)
        assert result["fiscal_quarter"].min() >= 1
        assert result["fiscal_quarter"].max() <= 4

    def test_total_count_matches(self, sample_tenders: pd.DataFrame) -> None:
        """Total count should equal number of tenders with valid publish_date."""
        result = fiscal_year_effects(sample_tenders)
        valid_tenders = sample_tenders.dropna(subset=["publish_date"])
        assert result["count"].sum() == len(valid_tenders)


# ============================================================================
# 4. PRICE ANALYTICS
# ============================================================================

class TestPriceTrendsByRegion:
    """Tests for price_trends_by_region()."""

    def test_basic_output(
        self, sample_prices: pd.DataFrame, sample_tenders: pd.DataFrame,
    ) -> None:
        """Should return DataFrame with expected columns."""
        result = price_trends_by_region(sample_prices, sample_tenders)
        assert list(result.columns) == ["date", "region", "avg_price_per_sqm", "count"]

    def test_empty_prices(self, sample_tenders: pd.DataFrame) -> None:
        """Empty prices should return empty result."""
        result = price_trends_by_region(pd.DataFrame(), sample_tenders)
        assert result.empty

    def test_empty_tenders(self, sample_prices: pd.DataFrame) -> None:
        """Empty tenders should return empty result."""
        result = price_trends_by_region(sample_prices, pd.DataFrame())
        assert result.empty


class TestPricePremiumAnalysis:
    """Tests for price_premium_analysis()."""

    def test_premium_vs_appraisal(self) -> None:
        """Primary premium: (winning - appraisal) / appraisal * 100."""
        df = pd.DataFrame({
            "tender_id": [1, 2],
            "appraisal_price": [100000, 250000],
            "floor_price": [80000, 200000],
            "winning_bid": [120000, 300000],
            "region": ["מרכז", "צפון"],
        })
        result = price_premium_analysis(df)
        assert len(result) == 2
        assert result.iloc[0]["premium_vs_appraisal_pct"] == pytest.approx(20.0, abs=0.01)
        assert result.iloc[1]["premium_vs_appraisal_pct"] == pytest.approx(20.0, abs=0.01)

    def test_premium_vs_floor(self) -> None:
        """Secondary premium: (winning - floor) / floor * 100."""
        df = pd.DataFrame({
            "tender_id": [1],
            "appraisal_price": [100000],
            "floor_price": [80000],
            "winning_bid": [120000],
            "region": ["מרכז"],
        })
        result = price_premium_analysis(df)
        assert result.iloc[0]["premium_vs_floor_pct"] == pytest.approx(50.0, abs=0.01)

    def test_appraisal_missing_floor_present(self) -> None:
        """When appraisal is missing, premium_vs_appraisal should be NaN but floor computed."""
        df = pd.DataFrame({
            "tender_id": [1],
            "appraisal_price": [None],
            "floor_price": [100000],
            "winning_bid": [120000],
        })
        result = price_premium_analysis(df)
        assert len(result) == 1
        assert pd.isna(result.iloc[0]["premium_vs_appraisal_pct"])
        assert result.iloc[0]["premium_vs_floor_pct"] == pytest.approx(20.0, abs=0.01)

    def test_null_winning_bid_excluded(self) -> None:
        """Rows with null winning_bid should be excluded."""
        df = pd.DataFrame({
            "tender_id": [1],
            "appraisal_price": [100000],
            "floor_price": [80000],
            "winning_bid": [None],
        })
        result = price_premium_analysis(df)
        assert result.empty

    def test_output_columns(self) -> None:
        """Should have the new dual-benchmark column layout."""
        df = pd.DataFrame({
            "tender_id": [1],
            "appraisal_price": [100000],
            "floor_price": [80000],
            "winning_bid": [120000],
        })
        result = price_premium_analysis(df)
        expected = [
            "tender_id", "appraisal_price", "floor_price", "winning_price",
            "premium_vs_appraisal_pct", "premium_vs_floor_pct", "region",
        ]
        assert list(result.columns) == expected

    def test_empty_df(self) -> None:
        """Empty input returns empty output."""
        result = price_premium_analysis(pd.DataFrame())
        assert result.empty


class TestTabaAnalysisSummary:
    """Tests for taba_analysis_summary()."""

    def test_tender_rate_per_year(self, sample_taba: pd.DataFrame) -> None:
        """Should compute tender_rate_per_year from date span."""
        result = taba_analysis_summary(sample_taba)
        # Plan 306-001: 5 tenders over ~1.43 years -> ~3.5/yr
        rate = result[result["plan_number"] == "306-001"]["tender_rate_per_year"].iloc[0]
        assert rate > 2.0  # roughly 5/1.43 ~ 3.5

    def test_same_date_span(self, sample_taba: pd.DataFrame) -> None:
        """When first_seen == last_seen, rate should equal count."""
        result = taba_analysis_summary(sample_taba)
        row = result[result["plan_number"] == "306-002"].iloc[0]
        assert row["tender_rate_per_year"] == row["tender_count"]

    def test_output_includes_dual_premium_columns(self, sample_taba: pd.DataFrame) -> None:
        """Should include both premium columns and appraisal price."""
        result = taba_analysis_summary(sample_taba)
        assert "avg_appraisal_price" in result.columns
        assert "premium_vs_appraisal_pct" in result.columns
        assert "premium_vs_floor_pct" in result.columns
        # Verify values pass through
        row = result[result["plan_number"] == "306-001"].iloc[0]
        assert row["avg_appraisal_price"] == 500000
        assert row["premium_vs_appraisal_pct"] == 4.0
        assert row["premium_vs_floor_pct"] == 30.0

    def test_empty_df(self) -> None:
        """Empty input returns empty output."""
        result = taba_analysis_summary(pd.DataFrame())
        assert result.empty


# ============================================================================
# 5. COMPETITIVE INTELLIGENCE
# ============================================================================

class TestTenderLifecycleAnalysis:
    """Tests for tender_lifecycle_analysis()."""

    def test_output_columns(self, sample_tenders: pd.DataFrame) -> None:
        """Should have expected columns."""
        result = tender_lifecycle_analysis(sample_tenders)
        expected = ["region", "tender_type", "avg_lifecycle_days", "median_lifecycle_days", "count"]
        assert list(result.columns) == expected

    def test_only_closed_tenders(self, sample_tenders: pd.DataFrame) -> None:
        """Should only include closed tenders (status_code == 5)."""
        result = tender_lifecycle_analysis(sample_tenders)
        closed_count = (sample_tenders["status_code"] == 5).sum()
        assert result["count"].sum() == closed_count

    def test_positive_lifecycle_days(self, sample_tenders: pd.DataFrame) -> None:
        """Lifecycle days should be positive (deadline > publish_date)."""
        result = tender_lifecycle_analysis(sample_tenders)
        if not result.empty:
            assert (result["avg_lifecycle_days"] > 0).all()
            assert (result["median_lifecycle_days"] > 0).all()

    def test_empty_df(self) -> None:
        """Empty input returns empty output."""
        result = tender_lifecycle_analysis(pd.DataFrame())
        assert result.empty
        assert list(result.columns) == [
            "region", "tender_type", "avg_lifecycle_days",
            "median_lifecycle_days", "count",
        ]

    def test_no_closed_tenders(self) -> None:
        """DataFrame with no closed tenders returns empty."""
        df = pd.DataFrame({
            "tender_id": [1, 2],
            "status_code": [1, 3],
            "publish_date": [datetime.now()] * 2,
            "deadline": [datetime.now() + timedelta(days=30)] * 2,
            "region": ["מרכז", "צפון"],
            "tender_type": ["פומבי", "פומבי"],
        })
        result = tender_lifecycle_analysis(df)
        assert result.empty

    def test_missing_region_column(self) -> None:
        """Should assign 'unknown' when region column is missing."""
        df = pd.DataFrame({
            "tender_id": [1],
            "status_code": [5],
            "publish_date": [datetime.now() - timedelta(days=30)],
            "deadline": [datetime.now()],
        })
        result = tender_lifecycle_analysis(df)
        assert len(result) == 1
        assert result.iloc[0]["region"] == "unknown"


class TestDeadlineOverlapAnalysis:
    """Tests for deadline_overlap_analysis()."""

    def test_output_columns(self, sample_tenders: pd.DataFrame) -> None:
        """Should have expected columns."""
        result = deadline_overlap_analysis(sample_tenders)
        expected = ["week_start", "tender_count", "regions_involved", "competition_level"]
        assert list(result.columns) == expected

    def test_competition_levels(self, sample_tenders: pd.DataFrame) -> None:
        """competition_level should only contain valid values."""
        result = deadline_overlap_analysis(sample_tenders)
        valid_levels = {"low", "medium", "high"}
        assert set(result["competition_level"].unique()).issubset(valid_levels)

    def test_competition_level_thresholds(self) -> None:
        """Verify low/medium/high thresholds: 1-2=low, 3-5=medium, 6+=high."""
        base_date = datetime(2026, 1, 5)  # A Monday
        # 2 tenders same week -> low
        df_low = pd.DataFrame({
            "deadline": [base_date, base_date + timedelta(days=1)],
            "region": ["מרכז", "צפון"],
        })
        result = deadline_overlap_analysis(df_low)
        assert result.iloc[0]["competition_level"] == "low"

        # 4 tenders same week -> medium
        df_med = pd.DataFrame({
            "deadline": [base_date + timedelta(days=i) for i in range(4)],
            "region": ["מרכז", "צפון", "דרום", "ירושלים"],
        })
        result = deadline_overlap_analysis(df_med)
        assert result.iloc[0]["competition_level"] == "medium"

        # 7 tenders same week -> high
        df_high = pd.DataFrame({
            "deadline": [base_date + timedelta(days=i % 5) for i in range(7)],
            "region": ["מרכז"] * 7,
        })
        result = deadline_overlap_analysis(df_high)
        assert result.iloc[0]["competition_level"] == "high"

    def test_regions_involved_comma_separated(self) -> None:
        """regions_involved should be a comma-separated string."""
        df = pd.DataFrame({
            "deadline": [datetime(2026, 1, 6), datetime(2026, 1, 7)],
            "region": ["מרכז", "צפון"],
        })
        result = deadline_overlap_analysis(df)
        regions = result.iloc[0]["regions_involved"]
        assert "," in regions or len(regions) > 0

    def test_empty_df(self) -> None:
        """Empty input returns empty output."""
        result = deadline_overlap_analysis(pd.DataFrame())
        assert result.empty
        assert list(result.columns) == [
            "week_start", "tender_count", "regions_involved", "competition_level",
        ]

    def test_no_valid_deadlines(self) -> None:
        """DataFrame with NaT deadlines returns empty."""
        df = pd.DataFrame({
            "deadline": [pd.NaT, pd.NaT],
            "region": ["מרכז", "צפון"],
        })
        result = deadline_overlap_analysis(df)
        assert result.empty


class TestRegionSaturationIndex:
    """Tests for region_saturation_index()."""

    def test_output_columns(self, sample_tenders: pd.DataFrame) -> None:
        """Should have expected columns."""
        result = region_saturation_index(sample_tenders)
        expected = ["region", "active_count", "closed_count", "total_units",
                     "saturation_score", "trend"]
        assert list(result.columns) == expected

    def test_saturation_score_range(self, sample_tenders: pd.DataFrame) -> None:
        """saturation_score should be between 0 and 100."""
        result = region_saturation_index(sample_tenders)
        if not result.empty:
            assert (result["saturation_score"] >= 0).all()
            assert (result["saturation_score"] <= 100).all()

    def test_max_region_has_score_100(self, sample_tenders: pd.DataFrame) -> None:
        """Region with most active tenders should have saturation_score 100."""
        result = region_saturation_index(sample_tenders)
        if not result.empty and result["active_count"].max() > 0:
            assert result["saturation_score"].max() == pytest.approx(100.0, abs=0.1)

    def test_trend_values(self, sample_tenders: pd.DataFrame) -> None:
        """trend should be one of 'saturating', 'stable', 'opening'."""
        result = region_saturation_index(sample_tenders)
        if not result.empty:
            valid = {"saturating", "stable", "opening"}
            assert set(result["trend"].unique()).issubset(valid)

    def test_empty_df(self) -> None:
        """Empty input returns empty output."""
        result = region_saturation_index(pd.DataFrame())
        assert result.empty

    def test_missing_region(self) -> None:
        """DataFrame without 'region' returns empty."""
        df = pd.DataFrame({
            "publish_date": [datetime.now()],
            "status_code": [1],
        })
        result = region_saturation_index(df)
        assert result.empty

    def test_all_tenders_outside_lookback(self) -> None:
        """Tenders older than lookback window return empty."""
        old_date = datetime.now() - timedelta(days=365)
        df = pd.DataFrame({
            "tender_id": [1, 2],
            "region": ["מרכז", "צפון"],
            "publish_date": [old_date, old_date],
            "status_code": [1, 5],
            "units": [10, 20],
        })
        result = region_saturation_index(df, lookback_months=1)
        assert result.empty


class TestDocumentIntelligence:
    """Tests for document_intelligence()."""

    def test_output_columns(self, sample_tenders: pd.DataFrame) -> None:
        """Should have expected columns."""
        result = document_intelligence(sample_tenders)
        expected = ["region", "avg_docs", "brochure_rate_pct", "total_tenders"]
        assert list(result.columns) == expected

    def test_brochure_rate_range(self, sample_tenders: pd.DataFrame) -> None:
        """brochure_rate_pct should be between 0 and 100."""
        result = document_intelligence(sample_tenders)
        assert (result["brochure_rate_pct"] >= 0).all()
        assert (result["brochure_rate_pct"] <= 100).all()

    def test_total_tenders_sum(self, sample_tenders: pd.DataFrame) -> None:
        """Sum of total_tenders should equal input row count."""
        result = document_intelligence(sample_tenders)
        assert result["total_tenders"].sum() == len(sample_tenders)

    def test_avg_docs_non_negative(self, sample_tenders: pd.DataFrame) -> None:
        """avg_docs should be non-negative."""
        result = document_intelligence(sample_tenders)
        assert (result["avg_docs"] >= 0).all()

    def test_empty_df(self) -> None:
        """Empty input returns empty output."""
        result = document_intelligence(pd.DataFrame())
        assert result.empty
        assert list(result.columns) == [
            "region", "avg_docs", "brochure_rate_pct", "total_tenders",
        ]

    def test_missing_docs_count(self) -> None:
        """Should default docs_count to 0 when column is missing."""
        df = pd.DataFrame({
            "region": ["מרכז", "צפון"],
            "published_booklet": [True, False],
        })
        result = document_intelligence(df)
        assert len(result) == 2
        assert (result["avg_docs"] == 0).all()

    def test_missing_brochure_column(self) -> None:
        """Should default brochure to False when column is missing."""
        df = pd.DataFrame({
            "region": ["מרכז", "צפון"],
            "docs_count": [3, 1],
        })
        result = document_intelligence(df)
        assert len(result) == 2
        assert (result["brochure_rate_pct"] == 0).all()


class TestVolumeMovingAverages:
    """Tests for volume_moving_averages()."""

    def test_output_columns_default_windows(self) -> None:
        """Should have date + ma_30, ma_60, ma_90 with default windows."""
        df = pd.DataFrame({
            "publish_date": pd.date_range("2025-01-01", periods=100, freq="D"),
        })
        result = volume_moving_averages(df)
        assert list(result.columns) == ["date", "ma_30", "ma_60", "ma_90"]

    def test_custom_windows(self) -> None:
        """Should respect custom window sizes."""
        df = pd.DataFrame({
            "publish_date": pd.date_range("2025-01-01", periods=50, freq="D"),
        })
        result = volume_moving_averages(df, windows=[7, 14])
        assert list(result.columns) == ["date", "ma_7", "ma_14"]

    def test_day_count_matches_range(self) -> None:
        """Number of rows should equal the day span of the data."""
        dates = pd.date_range("2025-01-01", periods=10, freq="D")
        df = pd.DataFrame({"publish_date": dates})
        result = volume_moving_averages(df)
        assert len(result) == 10

    def test_ma_values_non_negative(self) -> None:
        """All moving average values should be non-negative."""
        df = pd.DataFrame({
            "publish_date": pd.date_range("2025-01-01", periods=60, freq="D"),
        })
        result = volume_moving_averages(df)
        for col in ["ma_30", "ma_60", "ma_90"]:
            assert (result[col] >= 0).all()

    def test_larger_window_gte_smaller(self) -> None:
        """ma_60 should be >= ma_30 for any given day (cumulative counts)."""
        df = pd.DataFrame({
            "publish_date": pd.date_range("2025-01-01", periods=90, freq="D"),
        })
        result = volume_moving_averages(df)
        assert (result["ma_60"] >= result["ma_30"]).all()

    def test_empty_df(self) -> None:
        """Empty input returns empty output."""
        result = volume_moving_averages(pd.DataFrame())
        assert result.empty
        assert list(result.columns) == ["date", "ma_30", "ma_60", "ma_90"]

    def test_single_day(self) -> None:
        """Single-day input should produce one row with all MAs = 1."""
        df = pd.DataFrame({"publish_date": [datetime(2025, 6, 1)]})
        result = volume_moving_averages(df)
        assert len(result) == 1
        assert result.iloc[0]["ma_30"] == 1
        assert result.iloc[0]["ma_60"] == 1
        assert result.iloc[0]["ma_90"] == 1


class TestYoyComparison:
    """Tests for yoy_comparison()."""

    def test_output_columns(self) -> None:
        """Should have expected columns."""
        df = pd.DataFrame({
            "publish_date": pd.date_range("2024-01-01", periods=24, freq="ME"),
        })
        result = yoy_comparison(df)
        expected = ["month", "current_year_count", "previous_year_count", "change_pct"]
        assert list(result.columns) == expected

    def test_always_12_months(self) -> None:
        """Should always return 12 rows (one per month)."""
        df = pd.DataFrame({
            "publish_date": pd.date_range("2024-01-01", periods=24, freq="ME"),
        })
        result = yoy_comparison(df)
        assert len(result) == 12
        assert list(result["month"]) == list(range(1, 13))

    def test_known_change_pct(self) -> None:
        """Verify change_pct calculation with known values."""
        # 2024: 2 tenders in Jan; 2025: 4 tenders in Jan -> 100% increase
        df = pd.DataFrame({
            "publish_date": (
                [datetime(2024, 1, 10)] * 2
                + [datetime(2025, 1, 10)] * 4
            ),
        })
        result = yoy_comparison(df)
        jan_row = result[result["month"] == 1].iloc[0]
        assert jan_row["previous_year_count"] == 2
        assert jan_row["current_year_count"] == 4
        assert jan_row["change_pct"] == pytest.approx(100.0, abs=0.1)

    def test_zero_previous_year(self) -> None:
        """When previous year has 0 and current >0, change_pct should be NaN."""
        df = pd.DataFrame({
            "publish_date": [datetime(2025, 3, 15)],
        })
        result = yoy_comparison(df)
        mar_row = result[result["month"] == 3].iloc[0]
        assert mar_row["current_year_count"] == 1
        assert mar_row["previous_year_count"] == 0
        assert pd.isna(mar_row["change_pct"])

    def test_both_zero(self) -> None:
        """When both years have 0 for a month, change_pct should be 0."""
        df = pd.DataFrame({
            "publish_date": [datetime(2025, 1, 1), datetime(2024, 1, 1)],
        })
        result = yoy_comparison(df)
        # Month 6 should have 0/0 -> 0.0
        jun_row = result[result["month"] == 6].iloc[0]
        assert jun_row["current_year_count"] == 0
        assert jun_row["previous_year_count"] == 0
        assert jun_row["change_pct"] == 0.0

    def test_empty_df(self) -> None:
        """Empty input returns empty output."""
        result = yoy_comparison(pd.DataFrame())
        assert result.empty
        assert list(result.columns) == [
            "month", "current_year_count", "previous_year_count", "change_pct",
        ]

    def test_single_year_data(self) -> None:
        """Data from only one year should still return 12 rows."""
        df = pd.DataFrame({
            "publish_date": [datetime(2025, 6, 15)],
        })
        result = yoy_comparison(df)
        assert len(result) == 12


# ============================================================================
# 6. SCORING SYSTEM
# ============================================================================

class TestCalculateTenderScore:
    """Tests for calculate_tender_score()."""

    def test_known_urgency_score(self) -> None:
        """Tender closing in 5 days should get urgency=100."""
        row = pd.Series({
            "days_to_deadline": 5,
            "units": 50,
            "published_booklet": True,
            "docs_count": 3,
            "region": "מרכז",
            "publish_date": pd.Timestamp(datetime.now() - timedelta(days=3)),
        })
        result = calculate_tender_score(
            row,
            region_density={"מרכז": 0.9},
            units_percentile=0.7,
        )
        assert result["urgency_score"] == 100.0

    def test_urgency_tiers(self) -> None:
        """Test all urgency scoring tiers."""
        test_cases = [
            (3, 100.0),
            (10, 80.0),
            (20, 60.0),
            (45, 40.0),
            (90, 20.0),
        ]
        for days, expected in test_cases:
            row = pd.Series({
                "days_to_deadline": days,
                "units": 10,
                "published_booklet": False,
                "docs_count": 0,
                "region": None,
                "publish_date": None,
            })
            result = calculate_tender_score(row, units_percentile=0.5)
            assert result["urgency_score"] == expected, f"Failed for {days} days"

    def test_readiness_with_brochure_and_docs(self) -> None:
        """brochure(60) + 3 docs(30) = 90."""
        row = pd.Series({
            "days_to_deadline": 30,
            "units": 10,
            "published_booklet": True,
            "docs_count": 3,
            "region": None,
            "publish_date": None,
        })
        result = calculate_tender_score(row, units_percentile=0.5)
        assert result["readiness_score"] == 90.0

    def test_readiness_caps_at_100(self) -> None:
        """brochure(60) + 5 docs(50 capped to 40) = 100."""
        row = pd.Series({
            "days_to_deadline": 30,
            "units": 10,
            "published_booklet": True,
            "docs_count": 5,
            "region": None,
            "publish_date": None,
        })
        result = calculate_tender_score(row, units_percentile=0.5)
        assert result["readiness_score"] == 100.0

    def test_total_score_is_weighted_sum(self) -> None:
        """Total score should be the weighted sum of sub-scores."""
        row = pd.Series({
            "days_to_deadline": 5,
            "units": 100,
            "published_booklet": True,
            "docs_count": 4,
            "region": "מרכז",
            "publish_date": pd.Timestamp(datetime.now() - timedelta(days=2)),
        })
        result = calculate_tender_score(
            row,
            region_density={"מרכז": 0.8},
            units_percentile=0.9,
        )
        expected_total = (
            result["urgency_score"] * 0.20
            + result["size_score"] * 0.20
            + result["readiness_score"] * 0.25
            + result["location_score"] * 0.20
            + result["freshness_score"] * 0.15
        )
        assert result["total_score"] == pytest.approx(round(expected_total, 1), abs=0.2)

    def test_negative_deadline_gives_zero_urgency(self) -> None:
        """Expired tender (negative days) should get urgency=0."""
        row = pd.Series({
            "days_to_deadline": -5,
            "units": 10,
            "published_booklet": False,
            "docs_count": 0,
            "region": None,
            "publish_date": None,
        })
        result = calculate_tender_score(row, units_percentile=0.5)
        assert result["urgency_score"] == 0.0


class TestScoreAllTenders:
    """Tests for score_all_tenders()."""

    def test_adds_score_columns(self, sample_tenders: pd.DataFrame) -> None:
        """Should add 6 score columns to the DataFrame."""
        result = score_all_tenders(sample_tenders)
        for col in ["total_score", "urgency_score", "size_score",
                     "readiness_score", "location_score", "freshness_score"]:
            assert col in result.columns

    def test_same_row_count(self, sample_tenders: pd.DataFrame) -> None:
        """Output should have the same number of rows as input."""
        result = score_all_tenders(sample_tenders)
        assert len(result) == len(sample_tenders)

    def test_scores_in_range(self, sample_tenders: pd.DataFrame) -> None:
        """All total_score values should be between 0 and 100."""
        result = score_all_tenders(sample_tenders)
        assert (result["total_score"] >= 0).all()
        assert (result["total_score"] <= 100).all()

    def test_empty_df(self) -> None:
        """Empty input should return empty with score columns."""
        result = score_all_tenders(pd.DataFrame())
        assert "total_score" in result.columns


class TestGetTopTenders:
    """Tests for get_top_tenders()."""

    def test_returns_n_tenders(self, sample_tenders: pd.DataFrame) -> None:
        """Should return at most n tenders."""
        result = get_top_tenders(sample_tenders, n=5)
        assert len(result) == 5

    def test_sorted_descending(self, sample_tenders: pd.DataFrame) -> None:
        """Should be sorted by total_score descending."""
        result = get_top_tenders(sample_tenders, n=10)
        scores = result["total_score"].tolist()
        assert scores == sorted(scores, reverse=True)

    def test_empty_df(self) -> None:
        """Empty input returns empty."""
        result = get_top_tenders(pd.DataFrame(), n=5)
        assert result.empty


class TestGetScoreDistribution:
    """Tests for get_score_distribution()."""

    def test_histogram_structure(self, sample_tenders: pd.DataFrame) -> None:
        """Should return dict with bins, counts, mean, median, std."""
        result = get_score_distribution(sample_tenders)
        assert "bins" in result
        assert "counts" in result
        assert "mean" in result
        assert "median" in result
        assert "std" in result
        assert len(result["bins"]) == 11  # 10 bins -> 11 edges
        assert len(result["counts"]) == 10

    def test_counts_sum_to_total(self, sample_tenders: pd.DataFrame) -> None:
        """Sum of histogram counts should equal number of scored tenders."""
        result = get_score_distribution(sample_tenders)
        assert sum(result["counts"]) == len(sample_tenders)

    def test_empty_df(self) -> None:
        """Empty input returns zeroed structure."""
        result = get_score_distribution(pd.DataFrame())
        assert result["bins"] == []
        assert result["counts"] == []
        assert result["mean"] == 0.0


# ============================================================================
# EDGE CASES
# ============================================================================

class TestEdgeCases:
    """Cross-cutting edge case tests."""

    def test_single_row_tenders(self) -> None:
        """Single-row DataFrame should work for all functions."""
        df = pd.DataFrame({
            "tender_id": [1],
            "region": ["מרכז"],
            "publish_date": [datetime.now()],
            "deadline": [datetime.now() + timedelta(days=10)],
            "status_code": [1],
            "status": ["פעיל"],
            "tender_type": ["פומבי"],
            "units": [50],
            "published_booklet": [True],
            "docs_count": [2],
        })
        assert len(regional_tender_volume(df)) >= 1
        assert len(supply_pipeline(df)) >= 1
        assert len(monthly_publication_distribution(df)) >= 1
        assert len(score_all_tenders(df)) == 1

    def test_missing_optional_columns(self) -> None:
        """Functions should handle DataFrames with minimal columns."""
        df = pd.DataFrame({
            "tender_id": [1, 2],
            "region": ["מרכז", "צפון"],
            "publish_date": [datetime.now(), datetime.now() - timedelta(days=30)],
        })
        # Should not raise even without 'units', 'deadline', etc.
        result = regional_tender_volume(df)
        assert len(result) > 0

        result = score_all_tenders(df)
        assert len(result) == 2

    def test_all_nan_dates(self) -> None:
        """DataFrame with all NaT dates should return empty results."""
        df = pd.DataFrame({
            "tender_id": [1, 2],
            "region": ["מרכז", "צפון"],
            "publish_date": [pd.NaT, pd.NaT],
            "deadline": [pd.NaT, pd.NaT],
        })
        assert regional_tender_volume(df).empty
        assert supply_pipeline(df).empty

    def test_mixed_valid_invalid_dates(self) -> None:
        """Should process valid dates and skip invalid ones."""
        df = pd.DataFrame({
            "tender_id": [1, 2, 3],
            "region": ["מרכז", "צפון", "דרום"],
            "publish_date": [datetime.now(), pd.NaT, datetime.now() - timedelta(days=10)],
            "units": [10, 20, 30],
        })
        result = regional_tender_volume(df)
        # Only 2 valid rows expected
        assert result["count"].sum() == 2

    def test_tz_aware_dates(self) -> None:
        """TZ-aware dates (Supabase UTC) should be handled without error."""
        tz_dates = pd.to_datetime([
            "2025-06-01T00:00:00+00:00",
            "2025-07-15T00:00:00+00:00",
            "2025-08-20T00:00:00+00:00",
        ])
        df = pd.DataFrame({
            "tender_id": [1, 2, 3],
            "region": ["מרכז", "צפון", "דרום"],
            "publish_date": tz_dates,
            "deadline": tz_dates + pd.DateOffset(days=30),
            "units": [10, 20, 30],
            "status_code": [5, 5, 1],
            "tender_type": ["פומבי", "פומבי", "פומבי"],
            "published_booklet": [True, False, True],
            "docs_count": [2, 0, 1],
        })
        # All functions should work without TypeError
        vol = regional_tender_volume(df)
        assert len(vol) > 0
        assert vol["count"].sum() == 3

        pipe = supply_pipeline(df)
        assert len(pipe) > 0

        scored = score_all_tenders(df)
        assert len(scored) == 3
        assert (scored["total_score"] >= 0).all()

        ttc = avg_time_to_close(df)
        assert len(ttc) > 0  # 2 closed tenders

    def test_tz_aware_dates_in_scoring(self) -> None:
        """Scoring a single row with TZ-aware deadline and publish_date."""
        row = pd.Series({
            "deadline": pd.Timestamp("2025-06-15T00:00:00+00:00"),
            "units": 50,
            "published_booklet": True,
            "docs_count": 3,
            "region": "מרכז",
            "publish_date": pd.Timestamp("2025-06-01T00:00:00+00:00"),
        })
        # Should not raise TypeError
        result = calculate_tender_score(
            row,
            region_density={"מרכז": 0.8},
            units_percentile=0.7,
        )
        assert "total_score" in result
        assert result["total_score"] >= 0
