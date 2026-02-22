"""Tests for building_rights_extractor against demo Mavat plan PDFs.

Validates that Section 5 tables are correctly extracted with proper
column mapping, numeric parsing, and Hebrew text reversal.

Usage:
    pytest test_building_rights.py -v
"""

from pathlib import Path

import pytest

from building_rights_extractor import (
    extract_building_rights,
    _reverse_hebrew,
    _parse_numeric,
    _is_header_row,
    _forward_fill_row,
)

# ---------------------------------------------------------------------------
# Demo PDF paths — skip tests if files not present
# ---------------------------------------------------------------------------

DEMO_1 = Path("demo tender_1.pdf")
DEMO_2 = Path("demo tender_2.pdf")


# ---------------------------------------------------------------------------
# Unit tests for helper functions
# ---------------------------------------------------------------------------


class TestReverseHebrew:
    """Tests for _reverse_hebrew()."""

    def test_simple_hebrew(self) -> None:
        assert _reverse_hebrew("םירוגמ") == "מגורים"

    def test_preserves_numbers(self) -> None:
        assert _reverse_hebrew("390 שרגמ") == "מגרש 390"

    def test_number_with_footnote(self) -> None:
        result = _reverse_hebrew("260 (1) שרגמ")
        assert "מגרש" in result
        assert "260" in result


class TestParseNumeric:
    """Tests for _parse_numeric()."""

    def test_plain_integer(self) -> None:
        assert _parse_numeric("2961") == 2961.0

    def test_footnote_prefix(self) -> None:
        assert _parse_numeric("(1) 260") == 260.0

    def test_footnote_suffix(self) -> None:
        assert _parse_numeric("4 (4)") == 4.0

    def test_footnote_only(self) -> None:
        assert _parse_numeric("(4)") is None

    def test_empty(self) -> None:
        assert _parse_numeric("") is None

    def test_none(self) -> None:
        assert _parse_numeric(None) is None

    def test_commas(self) -> None:
        assert _parse_numeric("19,183") == 19183.0

    def test_double_footnote(self) -> None:
        assert _parse_numeric("(3) 10") == 10.0


class TestIsHeaderRow:
    """Tests for _is_header_row()."""

    def test_all_none(self) -> None:
        assert _is_header_row([None, None, None]) is True

    def test_all_text(self) -> None:
        assert _is_header_row(["דועי", "שומיש", None]) is True

    def test_mostly_numeric(self) -> None:
        assert _is_header_row(["390", "260", "80", "340", "50"]) is False

    def test_mixed_with_footnotes(self) -> None:
        # Data row: footnotes + numbers
        row = ["(3)", "(3)", "(2)", "1", "2", "9", "1", "50", "340"]
        assert _is_header_row(row) is False


class TestForwardFillRow:
    """Tests for _forward_fill_row()."""

    def test_basic_fill(self) -> None:
        row = ["A", None, None, "B", None]
        assert _forward_fill_row(row) == ["A", "A", "A", "B", "B"]

    def test_no_fill_needed(self) -> None:
        row = ["A", "B", "C"]
        assert _forward_fill_row(row) == ["A", "B", "C"]

    def test_leading_none(self) -> None:
        row = [None, None, "A", None]
        assert _forward_fill_row(row) == [None, None, "A", "A"]


# ---------------------------------------------------------------------------
# Integration tests against demo PDFs
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not DEMO_1.exists(), reason="demo tender_1.pdf not found")
class TestDemoTender1:
    """Integration tests against demo tender_1.pdf."""

    @pytest.fixture(scope="class")
    def result(self) -> dict:
        return extract_building_rights(DEMO_1)

    def test_success(self, result: dict) -> None:
        assert result["success"] is True

    def test_status(self, result: dict) -> None:
        assert result["status"] == "מצב מוצע"

    def test_row_count(self, result: dict) -> None:
        assert len(result["rows"]) == 5

    def test_all_columns_mapped(self, result: dict) -> None:
        assert len(result["column_map"]) == 16

    def test_designation_values(self, result: dict) -> None:
        designations = [r["designation"] for r in result["rows"]]
        assert "מגורים" in designations
        assert "דיור מיוחד" in designations

    def test_plot_size(self, result: dict) -> None:
        row_0 = result["rows"][0]
        assert row_0["plot_size_absolute"] == 6767.0

    def test_housing_units(self, result: dict) -> None:
        row_0 = result["rows"][0]
        assert row_0["housing_units"] == 200.0

    def test_building_areas_mapped(self, result: dict) -> None:
        """Verify service + main area columns are both mapped."""
        col_map_vals = set(result["column_map"].values())
        assert "building_area_above_main" in col_map_vals
        assert "building_area_below_service" in col_map_vals

    def test_floors(self, result: dict) -> None:
        row_0 = result["rows"][0]
        assert row_0["floors_above"] == 10.0
        assert row_0["floors_below"] == 4.0

    def test_balcony_column_present(self, result: dict) -> None:
        col_map_vals = set(result["column_map"].values())
        assert "balcony_area" in col_map_vals


@pytest.mark.skipif(not DEMO_2.exists(), reason="demo tender_2.pdf not found")
class TestDemoTender2:
    """Integration tests against demo tender_2.pdf."""

    @pytest.fixture(scope="class")
    def result(self) -> dict:
        return extract_building_rights(DEMO_2)

    def test_success(self, result: dict) -> None:
        assert result["success"] is True

    def test_status(self, result: dict) -> None:
        assert result["status"] == "מצב מוצע"

    def test_row_count_at_least(self, result: dict) -> None:
        # Large multi-page table
        assert len(result["rows"]) >= 30

    def test_all_columns_mapped(self, result: dict) -> None:
        assert len(result["column_map"]) == 16

    def test_first_row_values(self, result: dict) -> None:
        """Verify first row matches known values from PDF screenshot."""
        row = result["rows"][0]
        assert row["designation"] == "מגורים א'"
        assert row["area_condition"] == "1 - 212"
        assert row["plot_size_minimum"] == 390.0
        assert row["building_area_above_main"] == 260.0
        assert row["building_area_below_main"] == 80.0
        assert row["building_area_total"] == 340.0
        assert row["coverage_pct"] == 50.0
        assert row["housing_units"] == 1.0
        assert row["building_height"] == 9.0
        assert row["floors_above"] == 2.0
        assert row["floors_below"] == 1.0

    def test_building_height_mapped(self, result: dict) -> None:
        col_map_vals = set(result["column_map"].values())
        assert "building_height" in col_map_vals

    def test_plot_size_both_columns(self, result: dict) -> None:
        col_map_vals = set(result["column_map"].values())
        assert "plot_size_absolute" in col_map_vals
        assert "plot_size_minimum" in col_map_vals

    def test_megurim_bet_row(self, result: dict) -> None:
        """Verify a מגורים ב' row from the screenshot."""
        bet_rows = [r for r in result["rows"] if r.get("designation") == "מגורים ב'"]
        assert len(bet_rows) > 0

        # Find the row with area_condition=1200
        target = [r for r in bet_rows if r.get("area_condition") == "1200"]
        assert len(target) > 0
        row = target[0]
        assert row["plot_size_absolute"] == 2596.0
        assert row["building_area_above_main"] == 2016.0
        assert row["building_area_below_main"] == 945.0
        assert row["building_area_total"] == 2961.0
