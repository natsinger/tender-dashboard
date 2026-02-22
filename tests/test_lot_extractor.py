"""Tests for the lot_extractor module — Sections 1-3 extraction.

Covers:
    - _parse_numeric / _parse_int helper functions
    - _header_matches with plain and regex keywords
    - _clean_cell_value edge cases
    - _find_section1_column_mapping with normal, reversed, and mixed Hebrew
    - _detect_header_rows with single-row and multi-line headers
    - _parse_row field typing, confidence scoring, and edge cases
    - _score_section1_table scoring logic
    - BrochureLotExtractor._extract_section1_lots via mocked pdfplumber pages:
        * Single-lot tender
        * Multi-lot tender
        * Reversed Hebrew headers
        * Multi-line headers
        * Missing columns
        * Dash / empty values
        * Multi-page table continuation
    - Section 2 zoning extraction (_extract_section2_zoning):
        * Single plan for all lots
        * Multiple plans for different lots
        * Plan in table format
        * Reversed Hebrew section header
        * No Section 2 found
        * Empty section
    - Section 3 bid limit extraction
    - Inline zoning extraction (_extract_zoning_inline):
        * Standard inline plan + designation
        * Plan with מ"מת qualifier
        * Mixed-use designation
        * No inline data found
    - Text-based lot extraction (_extract_lots_from_text):
        * Single lot with units
        * Multiple lots
        * No lot data
    - New Section 1 column keywords (helka, gush, total_units, etc.)
"""

import sys
from pathlib import Path
from typing import Optional
from unittest.mock import MagicMock

import pytest

# Ensure project root is importable
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from lot_extractor import (
    CRITICAL_FIELDS,
    FLOAT_FIELDS,
    INT_FIELDS,
    MIN_SECTION1_COLUMNS,
    SECTION1_HEADERS,
    SECTION2_HEADERS,
    SECTION3_HEADERS,
    BrochureLotExtractor,
    _clean_cell_value,
    _detect_header_rows,
    _extract_all_plan_numbers,
    _extract_designation,
    _extract_lots_from_text,
    _extract_zoning_from_tables,
    _extract_zoning_from_text,
    _extract_zoning_inline,
    _find_header_offset,
    _find_section1_column_mapping,
    _find_section2_text,
    _find_zoning_column_mapping,
    _header_matches,
    _parse_int,
    _parse_numeric,
    _parse_row,
    _score_section1_table,
)


# ============================================================================
# _parse_numeric
# ============================================================================

class TestParseNumeric:
    """Tests for _parse_numeric() — float parsing with Hebrew formatting."""

    def test_plain_integer(self) -> None:
        assert _parse_numeric("42") == 42.0

    def test_with_commas(self) -> None:
        assert _parse_numeric("1,482,000") == 1482000.0

    def test_with_spaces(self) -> None:
        assert _parse_numeric("1 482 000") == 1482000.0

    def test_with_non_breaking_space(self) -> None:
        assert _parse_numeric("1\u00a0482\u00a0000") == 1482000.0

    def test_decimal(self) -> None:
        assert _parse_numeric("9218.5") == 9218.5

    def test_none_input(self) -> None:
        assert _parse_numeric(None) is None

    def test_empty_string(self) -> None:
        assert _parse_numeric("") is None

    def test_dash(self) -> None:
        assert _parse_numeric("-") is None

    def test_non_numeric(self) -> None:
        assert _parse_numeric("abc") is None

    def test_whitespace_only(self) -> None:
        assert _parse_numeric("   ") is None

    def test_negative_number(self) -> None:
        assert _parse_numeric("-500") == -500.0

    def test_large_value(self) -> None:
        assert _parse_numeric("24,180,180") == 24180180.0


# ============================================================================
# _parse_int
# ============================================================================

class TestParseInt:
    """Tests for _parse_int() — integer parsing."""

    def test_plain(self) -> None:
        assert _parse_int("27") == 27

    def test_with_commas(self) -> None:
        assert _parse_int("1,449,894") == 1449894

    def test_float_truncated(self) -> None:
        # 54.0 -> 54
        assert _parse_int("54.0") == 54

    def test_none(self) -> None:
        assert _parse_int(None) is None

    def test_dash(self) -> None:
        assert _parse_int("-") is None

    def test_empty(self) -> None:
        assert _parse_int("") is None

    def test_non_numeric(self) -> None:
        assert _parse_int("N/A") is None


# ============================================================================
# _header_matches
# ============================================================================

class TestHeaderMatches:
    """Tests for _header_matches() — keyword matching in cell headers."""

    def test_plain_match(self) -> None:
        assert _header_matches("מספר מתחם", ["מתחם", "םחתמ"]) is True

    def test_reversed_match(self) -> None:
        assert _header_matches("םחתמ רפסמ", ["מתחם", "םחתמ"]) is True

    def test_no_match(self) -> None:
        assert _header_matches("unrelated header", ["מתחם", "םחתמ"]) is False

    def test_none_cell(self) -> None:
        assert _header_matches(None, ["מתחם"]) is False  # type: ignore[arg-type]

    def test_empty_cell(self) -> None:
        assert _header_matches("", ["מתחם"]) is False

    def test_multiline_cell(self) -> None:
        """Multi-line text should be collapsed before matching."""
        assert _header_matches("מספר\nמתחם", ["מתחם"]) is True

    def test_regex_pattern_match(self) -> None:
        """Keywords with regex metacharacters should use re.search."""
        assert _header_matches(
            'יח"ד מתב"ע במחיר מטרה',
            ['יח"ד.*מטרה'],
        ) is True

    def test_regex_pattern_no_match(self) -> None:
        assert _header_matches(
            'יח"ד מתב"ע בשוק חופשי',
            ['יח"ד.*מטרה'],
        ) is False

    def test_regex_free_market(self) -> None:
        assert _header_matches(
            'יח"ד מתב"ע בשוק חופשי',
            ['יח"ד.*חופשי'],
        ) is True

    def test_regex_value_appraisal(self) -> None:
        assert _header_matches(
            "שווי מ\"ר בנוי לפי שומה",
            ['שווי.*שומה'],
        ) is True


# ============================================================================
# _clean_cell_value
# ============================================================================

class TestCleanCellValue:
    """Tests for _clean_cell_value()."""

    def test_normal_string(self) -> None:
        assert _clean_cell_value("70998") == "70998"

    def test_whitespace(self) -> None:
        assert _clean_cell_value("  70998  ") == "70998"

    def test_newlines(self) -> None:
        assert _clean_cell_value("28\n43") == "28 43"

    def test_none(self) -> None:
        assert _clean_cell_value(None) is None

    def test_empty_string(self) -> None:
        assert _clean_cell_value("") is None

    def test_single_dash(self) -> None:
        assert _clean_cell_value("-") is None

    def test_double_dash(self) -> None:
        assert _clean_cell_value("--") is None

    def test_only_whitespace(self) -> None:
        assert _clean_cell_value("   ") is None


# ============================================================================
# _find_section1_column_mapping — normal Hebrew
# ============================================================================

class TestFindColumnMappingNormalHebrew:
    """Test column mapping with standard (non-reversed) Hebrew headers."""

    def test_full_header_row(self) -> None:
        """All 10 columns present in normal Hebrew."""
        header = [
            "מספר מתחם",
            "מספר מגרש",
            'שטח במ"ר',
            'מספר יח"ד מתב"ע במחיר מטרה',
            'מספר יח"ד מתב"ע בשוק חופשי',
            'מחיר מינימום בש"ח',
            "גובה ערבות",
            'שווי מ"ר בנוי עיקרי בש"ח לפי שומה',
            'שווי מ"ר בנוי לפי שומה עדכנית',
            "גובה ההנחה",
        ]
        mapping = _find_section1_column_mapping(header)

        assert mapping["lot_number"] == 0
        assert mapping["plot_numbers"] == 1
        assert mapping["area_sqm"] == 2
        assert mapping["units_target_price"] == 3
        assert mapping["units_free_market"] == 4
        assert mapping["min_price"] == 5
        assert mapping["guarantee_amount"] == 6
        assert mapping["sqm_value_appraisal"] == 7
        assert mapping["sqm_value_current"] == 8
        assert mapping["discount_amount"] == 9

    def test_partial_header(self) -> None:
        """Only lot_number and area columns present."""
        header = ["מספר מתחם", None, 'שטח במ"ר']
        mapping = _find_section1_column_mapping(header)

        assert "lot_number" in mapping
        assert "area_sqm" in mapping
        assert len(mapping) == 2

    def test_empty_header(self) -> None:
        """All-None header yields empty mapping."""
        mapping = _find_section1_column_mapping([None, None, None])
        assert mapping == {}


# ============================================================================
# _find_section1_column_mapping — reversed Hebrew
# ============================================================================

class TestFindColumnMappingReversedHebrew:
    """Test column mapping with reversed (RTL-extracted) Hebrew headers."""

    def test_reversed_lot_and_plot(self) -> None:
        header = ["םחתמ רפסמ", "שרגמ רפסמ", "חטש"]
        mapping = _find_section1_column_mapping(header)

        assert mapping["lot_number"] == 0
        assert mapping["plot_numbers"] == 1
        assert mapping["area_sqm"] == 2

    def test_reversed_pricing_columns(self) -> None:
        header = [
            "םחתמ רפסמ",
            "םומינימ ריחמ",
            "תוברע הבוג",
            "החנה הבוג",
        ]
        mapping = _find_section1_column_mapping(header)

        assert mapping["lot_number"] == 0
        assert mapping["min_price"] == 1
        assert mapping["guarantee_amount"] == 2
        assert mapping["discount_amount"] == 3

    def test_reversed_unit_columns(self) -> None:
        """Reversed free-market header."""
        header = ["םחתמ", "ישפוח קוש", "הרטמ ריחמ"]
        mapping = _find_section1_column_mapping(header)

        assert mapping["lot_number"] == 0
        assert mapping["units_free_market"] == 1
        assert mapping["units_target_price"] == 2

    def test_reversed_appraisal_columns(self) -> None:
        header = ["המוש יפל יווש", "תינכדע המוש"]
        mapping = _find_section1_column_mapping(header)

        assert mapping["sqm_value_appraisal"] == 0
        assert mapping["sqm_value_current"] == 1


# ============================================================================
# _find_section1_column_mapping — multi-line reversed headers from real PDFs
# ============================================================================

class TestFindColumnMappingMultiLineReversed:
    """Test column mapping with multi-line reversed headers seen in real PDFs.

    pdfplumber splits long reversed headers across lines, which changes
    word order when collapsed.  These tests reproduce actual header text
    from production brochures.
    """

    def test_real_pdf_20230081_header(self) -> None:
        """Tender 20230081 header — 11 cols, reversed multi-line."""
        header = [
            'הבוג תוברע םויקל העצהה ח"שב',          # col 0: guarantee
            'םולשת תואצוה יללכ חותיפ',                # col 1: unrecognized
            "יווש ר''מ יונב ירקיע ח''שב אלל) (מ''עמ", # col 2: sqm value
            'ריחמ םומינימ ח"שב ללוכ אל) (מ"עמ',       # col 3: min_price
            'רפסמ ד"חי ע"בתמ קושב ישפוח',             # col 4: free market
            'רפסמ ד"חי בתמ ע" ריחמב הרטמ',            # col 5: target price
            "חטש ר''מב ךרעב",                         # col 6: area
            'הקלח (תומלשב)',                           # col 7: unrecognized
            'שוג',                                     # col 8: unrecognized
            'שרגמ',                                    # col 9: plot
            'םחתמ',                                    # col 10: lot
        ]
        mapping = _find_section1_column_mapping(header)

        assert mapping["guarantee_amount"] == 0
        assert mapping["min_price"] == 3
        assert mapping["units_free_market"] == 4
        assert mapping["units_target_price"] == 5
        assert mapping["area_sqm"] == 6
        assert mapping["plot_numbers"] == 9
        assert mapping["lot_number"] == 10

    def test_real_pdf_20250422_header(self) -> None:
        """Tender 20250422 header — 7 cols, reversed multi-line."""
        header = [
            'ד"חי רפסמ קושב ע"בתמ ישפוח',  # col 0: free market
            'ד"חי רפסמ ריחמב ע "בתמ הרטמ',  # col 1: target price
            "ר''מב חטש",                     # col 2: area
            'הקלח',                          # col 3: unrecognized
            'שוג',                           # col 4: unrecognized
            'שרגמ',                          # col 5: plot
            'םחתמ',                          # col 6: lot
        ]
        mapping = _find_section1_column_mapping(header)

        assert mapping["units_free_market"] == 0
        assert mapping["units_target_price"] == 1
        assert mapping["area_sqm"] == 2
        assert mapping["plot_numbers"] == 5
        assert mapping["lot_number"] == 6

    def test_reversed_single_word_minimum(self) -> None:
        """Single-word reversed 'םומינימ' should match min_price."""
        header = ["םחתמ", "םומינימ ריחמ"]
        mapping = _find_section1_column_mapping(header)
        assert mapping["min_price"] == 1

    def test_reversed_single_word_minimum_scrambled_order(self) -> None:
        """When multi-line collapsing reverses word order."""
        header = ["םחתמ", "ריחמ םומינימ"]
        mapping = _find_section1_column_mapping(header)
        assert mapping["min_price"] == 1


# ============================================================================
# _find_section1_column_mapping — mixed/edge cases
# ============================================================================

class TestFindColumnMappingEdgeCases:
    """Test column mapping edge cases: different orderings, extra columns."""

    def test_shuffled_columns(self) -> None:
        """Columns in non-standard order."""
        header = [
            "גובה ערבות",
            'שטח במ"ר',
            "מספר מתחם",
        ]
        mapping = _find_section1_column_mapping(header)

        assert mapping["guarantee_amount"] == 0
        assert mapping["area_sqm"] == 1
        assert mapping["lot_number"] == 2

    def test_extra_unrecognized_columns(self) -> None:
        """Extra columns that don't match any keyword should be ignored."""
        header = ["מספר מתחם", "הערות", "שטח", "סטטוס"]
        mapping = _find_section1_column_mapping(header)

        assert mapping["lot_number"] == 0
        assert mapping["area_sqm"] == 2
        assert len(mapping) == 2

    def test_duplicate_keyword_takes_first(self) -> None:
        """If two columns match the same keyword, the first should win."""
        header = ["מתחם ראשי", "מתחם משני"]
        mapping = _find_section1_column_mapping(header)

        assert mapping["lot_number"] == 0
        assert len(mapping) == 1


# ============================================================================
# _detect_header_rows
# ============================================================================

class TestDetectHeaderRows:
    """Tests for multi-line header detection and merging."""

    def test_single_row_header(self) -> None:
        """Header fully in first row, no merging needed."""
        table = [
            ["מספר מתחם", "מספר מגרש", "שטח"],
            ["70998", "28,43", "5,328"],
        ]
        header, consumed = _detect_header_rows(table)

        assert consumed == 1
        assert header == table[0]

    def test_multi_line_header(self) -> None:
        """Header split across two rows; merged should match more columns."""
        table = [
            # Row 0: partial header words
            ["מספר", "מספר", 'יח"ד', 'יח"ד'],
            # Row 1: completing words
            ["מתחם", "מגרש", "במחיר מטרה", "בשוק חופשי"],
            # Row 2: data
            ["70998", "28,43", "27", "27"],
        ]
        header, consumed = _detect_header_rows(table)

        assert consumed == 2
        # Merged header should contain the combined text
        mapping = _find_section1_column_mapping(header)
        assert "lot_number" in mapping
        assert "plot_numbers" in mapping

    def test_empty_table(self) -> None:
        header, consumed = _detect_header_rows([])
        assert header == []
        assert consumed == 0

    def test_single_row_table(self) -> None:
        """Table with only one row should use it as header."""
        table = [["מתחם", "שטח"]]
        header, consumed = _detect_header_rows(table)
        assert consumed == 1

    def test_merge_with_nones(self) -> None:
        """When one row has None and the other has text, use the text."""
        table = [
            ["מתחם", None, "שטח"],
            [None, "מגרש", None],
            ["70998", "28", "5000"],
        ]
        header, consumed = _detect_header_rows(table)

        # Merging should pick up "מגרש" from row 1
        mapping = _find_section1_column_mapping(header)
        # Row 0 alone has lot_number and area_sqm (2 matches).
        # Merged would add plot_numbers (3 matches) — so merged wins.
        assert consumed == 2
        assert "plot_numbers" in mapping


# ============================================================================
# _parse_row
# ============================================================================

class TestParseRow:
    """Tests for _parse_row() — per-row data extraction."""

    @pytest.fixture
    def full_mapping(self) -> dict[str, int]:
        """Column mapping for a full 10-column table."""
        return {
            "lot_number": 0,
            "plot_numbers": 1,
            "area_sqm": 2,
            "units_target_price": 3,
            "units_free_market": 4,
            "min_price": 5,
            "guarantee_amount": 6,
            "sqm_value_appraisal": 7,
            "sqm_value_current": 8,
            "discount_amount": 9,
        }

    def test_full_row(self, full_mapping: dict[str, int]) -> None:
        """Parse a complete data row with all fields."""
        row = [
            "70998",        # lot_number
            "28,43",        # plot_numbers
            "5,328",        # area_sqm
            "27",           # units_target_price
            "27",           # units_free_market
            "1,449,894",    # min_price
            "1,482,000",    # guarantee_amount
            "9,218",        # sqm_value_appraisal
            "11,995",       # sqm_value_current
            "600,000",      # discount_amount
        ]
        lot = _parse_row(row, full_mapping)

        assert lot is not None
        assert lot["lot_number"] == 70998
        assert lot["plot_numbers"] == "28,43"
        assert lot["area_sqm"] == 5328.0
        assert lot["units_target_price"] == 27
        assert lot["units_free_market"] == 27
        assert lot["min_price"] == 1449894.0
        assert lot["guarantee_amount"] == 1482000.0
        assert lot["sqm_value_appraisal"] == 9218.0
        assert lot["sqm_value_current"] == 11995.0
        assert lot["discount_amount"] == 600000.0
        assert lot["confidence"] == 1.0

    def test_row_with_dashes(self, full_mapping: dict[str, int]) -> None:
        """Row where min_price is '-' should yield None for that field."""
        row = [
            "70999",
            "25-27",
            "10,369",
            "54",
            "36",
            "-",             # min_price is dash
            "2,500,000",
            "8,000",
            "10,000",
            "-",             # discount_amount is dash
        ]
        lot = _parse_row(row, full_mapping)

        assert lot is not None
        assert lot["lot_number"] == 70999
        assert lot["min_price"] is None
        assert lot["discount_amount"] is None
        assert lot["confidence"] == 1.0  # critical fields all present

    def test_missing_critical_field_lowers_confidence(self) -> None:
        """When a critical field (units_target_price) fails to parse,
        confidence should drop."""
        mapping = {
            "lot_number": 0,
            "units_target_price": 1,
            "units_free_market": 2,
        }
        row = ["70998", "N/A", "27"]
        lot = _parse_row(row, mapping)

        assert lot is not None
        assert lot["lot_number"] == 70998
        assert lot["units_target_price"] is None  # couldn't parse
        assert lot["units_free_market"] == 27
        # 2 of 3 critical fields present -> 0.67
        assert lot["confidence"] == pytest.approx(0.67, abs=0.01)

    def test_all_empty_row_returns_none(self) -> None:
        """A row with all empty/None cells should return None."""
        mapping = {"lot_number": 0, "area_sqm": 1}
        row = [None, ""]
        lot = _parse_row(row, mapping)

        assert lot is None

    def test_short_row_handles_missing_cols(self, full_mapping: dict[str, int]) -> None:
        """Row shorter than mapping should fill missing fields with None."""
        row = ["70998", "28"]  # Only 2 cells but mapping expects 10
        lot = _parse_row(row, full_mapping)

        assert lot is not None
        assert lot["lot_number"] == 70998
        assert lot["area_sqm"] is None
        assert lot["units_target_price"] is None

    def test_confidence_with_no_critical_fields_in_mapping(self) -> None:
        """Mapping with no critical fields should give confidence 0.0."""
        mapping = {"area_sqm": 0, "guarantee_amount": 1}
        row = ["5000", "1,000,000"]
        lot = _parse_row(row, mapping)

        assert lot is not None
        assert lot["confidence"] == 0.0


# ============================================================================
# _score_section1_table
# ============================================================================

class TestScoreSection1Table:
    """Tests for _score_section1_table()."""

    def test_full_mapping_score(self) -> None:
        mapping = {
            "lot_number": 0,
            "plot_numbers": 1,
            "area_sqm": 2,
            "units_target_price": 3,
            "units_free_market": 4,
        }
        assert _score_section1_table(mapping) == 5

    def test_empty_mapping(self) -> None:
        assert _score_section1_table({}) == 0

    def test_single_field(self) -> None:
        assert _score_section1_table({"lot_number": 0}) == 1


# ============================================================================
# BrochureLotExtractor._extract_section1_lots — integration tests with mocks
# ============================================================================

def _make_mock_page(
    tables: Optional[list[list[list[Optional[str]]]]] = None,
    text: str = "",
) -> MagicMock:
    """Create a mock pdfplumber Page with the given tables and text.

    Args:
        tables: List of tables; each table is a list of rows; each row
                is a list of cell strings. If None, page.extract_tables()
                returns [].
        text: Page text returned by extract_text().
    """
    page = MagicMock()
    page.extract_tables.return_value = tables if tables is not None else []
    page.extract_text.return_value = text
    return page


class TestExtractSection1LotsSingleLot:
    """Single-lot tender table extraction."""

    def test_single_lot_normal_hebrew(self) -> None:
        """Single lot with normal Hebrew headers."""
        table = [
            # Header row
            [
                "מספר מתחם",
                "מספר מגרש",
                'שטח במ"ר',
                'מספר יח"ד מתב"ע במחיר מטרה',
                'מספר יח"ד מתב"ע בשוק חופשי',
                'מחיר מינימום בש"ח',
                "גובה ערבות",
            ],
            # Data row
            [
                "70998",
                "28,43",
                "5,328",
                "27",
                "27",
                "1,449,894",
                "1,482,000",
            ],
        ]
        page = _make_mock_page([table])
        extractor = BrochureLotExtractor()
        lots = extractor._extract_section1_lots([page])

        assert len(lots) == 1
        lot = lots[0]
        assert lot["lot_number"] == 70998
        assert lot["plot_numbers"] == "28,43"
        assert lot["area_sqm"] == 5328.0
        assert lot["units_target_price"] == 27
        assert lot["units_free_market"] == 27
        assert lot["min_price"] == 1449894.0
        assert lot["guarantee_amount"] == 1482000.0
        assert lot["confidence"] == 1.0


class TestExtractSection1LotsMultiLot:
    """Multi-lot tender extraction."""

    def test_three_lots(self) -> None:
        """Three lots in one table."""
        table = [
            ["מתחם", "מגרש", "שטח", "מחיר מינימום", "ערבות"],
            ["70998", "28,43", "5,328", "1,449,894", "1,482,000"],
            ["70999", "25-27", "10,369", "2,800,000", "2,900,000"],
            ["71000", "50", "3,200", "-", "500,000"],
        ]
        page = _make_mock_page([table])
        extractor = BrochureLotExtractor()
        lots = extractor._extract_section1_lots([page])

        assert len(lots) == 3
        assert lots[0]["lot_number"] == 70998
        assert lots[1]["lot_number"] == 70999
        assert lots[2]["lot_number"] == 71000
        assert lots[2]["min_price"] is None  # was "-"

    def test_skips_empty_rows(self) -> None:
        """Empty rows between data should be skipped."""
        table = [
            ["מתחם", "שטח", "ערבות"],
            ["70998", "5,328", "1,482,000"],
            [None, None, None],  # empty row
            ["", "", ""],        # whitespace row
            ["70999", "10,369", "2,900,000"],
        ]
        page = _make_mock_page([table])
        extractor = BrochureLotExtractor()
        lots = extractor._extract_section1_lots([page])

        assert len(lots) == 2


class TestExtractSection1LotsReversedHebrew:
    """Extraction with reversed Hebrew headers."""

    def test_fully_reversed_headers(self) -> None:
        """All headers in reversed Hebrew form."""
        table = [
            ["םחתמ רפסמ", "שרגמ רפסמ", "חטש", "תוברע", "םומינימ ריחמ"],
            ["70998", "28", "5,328", "1,482,000", "1,449,894"],
        ]
        page = _make_mock_page([table])
        extractor = BrochureLotExtractor()
        lots = extractor._extract_section1_lots([page])

        assert len(lots) == 1
        assert lots[0]["lot_number"] == 70998
        assert lots[0]["guarantee_amount"] == 1482000.0
        assert lots[0]["min_price"] == 1449894.0


class TestExtractSection1LotsMultiLineHeaders:
    """Extraction with multi-line (wrapped) column headers."""

    def test_header_split_across_two_rows(self) -> None:
        """Headers that span two rows should be merged and matched."""
        table = [
            # Row 0: first line of header
            ["מספר", "מספר", "שטח", 'יח"ד מתב"ע', 'יח"ד מתב"ע'],
            # Row 1: second line of header
            ["מתחם", "מגרש", 'במ"ר', "במחיר מטרה", "בשוק חופשי"],
            # Row 2: data
            ["70998", "28,43", "5,328", "27", "27"],
        ]
        page = _make_mock_page([table])
        extractor = BrochureLotExtractor()
        lots = extractor._extract_section1_lots([page])

        assert len(lots) == 1
        lot = lots[0]
        assert lot["lot_number"] == 70998
        assert lot["units_target_price"] == 27
        assert lot["units_free_market"] == 27


class TestExtractSection1LotsMissingColumns:
    """Extraction when some expected columns are absent."""

    def test_no_unit_columns(self) -> None:
        """Table without unit columns should still extract other fields."""
        table = [
            ["מתחם", "מגרש", "שטח", "ערבות"],
            ["70998", "28", "5,328", "1,482,000"],
        ]
        page = _make_mock_page([table])
        extractor = BrochureLotExtractor()
        lots = extractor._extract_section1_lots([page])

        assert len(lots) == 1
        lot = lots[0]
        assert lot["lot_number"] == 70998
        assert "units_target_price" not in lot
        assert "units_free_market" not in lot
        # confidence should reflect missing critical fields (only lot_number
        # present out of 1 critical field in mapping)
        assert lot["confidence"] == 1.0  # only lot_number is in mapping & present

    def test_only_lot_number_below_threshold(self) -> None:
        """A table matching only 1 column (below MIN_SECTION1_COLUMNS)
        should be rejected."""
        table = [
            ["מתחם"],
            ["70998"],
        ]
        page = _make_mock_page([table])
        extractor = BrochureLotExtractor()
        lots = extractor._extract_section1_lots([page])

        assert lots == []


class TestExtractSection1LotsDashValues:
    """Handling of dash values and missing data in cells."""

    def test_all_dash_data_row(self) -> None:
        """Row where all data cells are '-' should be treated as empty
        (lot_number can't parse '-')."""
        table = [
            ["מתחם", "שטח", "ערבות"],
            ["-", "-", "-"],
        ]
        page = _make_mock_page([table])
        extractor = BrochureLotExtractor()
        lots = extractor._extract_section1_lots([page])

        # All cleaned values are None -> _parse_row returns None
        assert lots == []


class TestExtractSection1LotsMultiPage:
    """Multi-page table continuation."""

    def test_continuation_on_next_page(self) -> None:
        """Rows on the next page without headers should be appended."""
        # Page 1: table with header + first lot
        table_page1 = [
            ["מתחם", "מגרש", "שטח", "ערבות"],
            ["70998", "28", "5,328", "1,482,000"],
        ]
        page1 = _make_mock_page([table_page1])

        # Page 2: continuation — same column count, no recognized headers
        table_page2 = [
            ["70999", "30", "10,369", "2,900,000"],
            ["71000", "50", "3,200", "500,000"],
        ]
        page2 = _make_mock_page([table_page2])

        extractor = BrochureLotExtractor()
        lots = extractor._extract_section1_lots([page1, page2])

        assert len(lots) == 3
        assert lots[0]["lot_number"] == 70998
        assert lots[1]["lot_number"] == 70999
        assert lots[2]["lot_number"] == 71000

    def test_non_adjacent_page_not_continued(self) -> None:
        """A table on page 3 (non-adjacent to page 1) should NOT be
        treated as a continuation."""
        table_page1 = [
            ["מתחם", "מגרש", "שטח", "ערבות"],
            ["70998", "28", "5,328", "1,482,000"],
        ]
        page1 = _make_mock_page([table_page1])

        # Page 2: no tables
        page2 = _make_mock_page()

        # Page 3: would-be continuation
        table_page3 = [
            ["70999", "30", "10,369", "2,900,000"],
        ]
        page3 = _make_mock_page([table_page3])

        extractor = BrochureLotExtractor()
        lots = extractor._extract_section1_lots([page1, page2, page3])

        # Only page 1's lot should be extracted
        assert len(lots) == 1
        assert lots[0]["lot_number"] == 70998


class TestExtractSection1LotsNoTable:
    """Edge case: no tables found in any page."""

    def test_no_tables(self) -> None:
        page = _make_mock_page()
        extractor = BrochureLotExtractor()
        lots = extractor._extract_section1_lots([page])
        assert lots == []

    def test_empty_page_list(self) -> None:
        extractor = BrochureLotExtractor()
        lots = extractor._extract_section1_lots([])
        assert lots == []


class TestExtractSection1LotsBestTableSelection:
    """When multiple tables exist, the highest-scoring one should win."""

    def test_picks_higher_scoring_table(self) -> None:
        """Two tables on same page; the one with more columns wins."""
        # Weak table: only 2 columns
        weak_table = [
            ["מתחם", "שטח"],
            ["11111", "1,000"],
        ]
        # Strong table: 5 columns
        strong_table = [
            ["מתחם", "מגרש", "שטח", "ערבות", "הנחה"],
            ["70998", "28", "5,328", "1,482,000", "600,000"],
        ]
        page = _make_mock_page([weak_table, strong_table])
        extractor = BrochureLotExtractor()
        lots = extractor._extract_section1_lots([page])

        assert len(lots) == 1
        assert lots[0]["lot_number"] == 70998
        assert lots[0]["discount_amount"] == 600000.0


class TestExtractSection1LotsConfidenceScoring:
    """Confidence scoring integration tests."""

    def test_full_confidence(self) -> None:
        table = [
            ["מתחם", "מגרש", 'יח"ד במחיר מטרה', 'יח"ד בשוק חופשי'],
            ["70998", "28", "27", "27"],
        ]
        page = _make_mock_page([table])
        extractor = BrochureLotExtractor()
        lots = extractor._extract_section1_lots([page])

        assert len(lots) == 1
        assert lots[0]["confidence"] == 1.0

    def test_partial_confidence(self) -> None:
        """Unit field that can't be parsed should lower confidence."""
        table = [
            ["מתחם", "מגרש", 'יח"ד במחיר מטרה', 'יח"ד בשוק חופשי'],
            ["70998", "28", "N/A", "27"],
        ]
        page = _make_mock_page([table])
        extractor = BrochureLotExtractor()
        lots = extractor._extract_section1_lots([page])

        assert len(lots) == 1
        # lot_number OK, units_target_price failed, units_free_market OK
        # -> 2/3 = 0.67
        assert lots[0]["confidence"] == pytest.approx(0.67, abs=0.01)


# ============================================================================
# Section 3 — _extract_section3_bid_limits
# ============================================================================


class TestExtractSection3BidLimitsNormalHebrew:
    """Tests for bid-limit extraction with normal Hebrew text."""

    def test_one_lot_bilvad(self) -> None:
        """'למתחם אחד בלבד' -> 1."""
        text = "מסלול מכרז\nניתן להגיש הצעה למתחם אחד בלבד"
        extractor = BrochureLotExtractor()
        assert extractor._extract_section3_bid_limits([text]) == 1

    def test_two_lots(self) -> None:
        """'לשני מתחמים' -> 2."""
        text = "מסלול מכרז\nניתן להגיש הצעה לשני מתחמים"
        extractor = BrochureLotExtractor()
        assert extractor._extract_section3_bid_limits([text]) == 2

    def test_three_lots(self) -> None:
        """'לשלושה מתחמים' -> 3."""
        text = "מסלול מכרז\nניתן להגיש הצעה לשלושה מתחמים"
        extractor = BrochureLotExtractor()
        assert extractor._extract_section3_bid_limits([text]) == 3

    def test_four_lots(self) -> None:
        """'לארבעה מתחמים' -> 4."""
        text = "מסלול מכרז\nניתן להגיש הצעה לארבעה מתחמים"
        extractor = BrochureLotExtractor()
        assert extractor._extract_section3_bid_limits([text]) == 4

    def test_five_lots(self) -> None:
        """'לחמישה מתחמים' -> 5."""
        text = "מסלול מכרז\nניתן להגיש הצעה לחמישה מתחמים"
        extractor = BrochureLotExtractor()
        assert extractor._extract_section3_bid_limits([text]) == 5

    def test_numeric_dash_two(self) -> None:
        """'ל-2 מתחמים' -> 2."""
        text = "מסלול מכרז\nניתן להגיש הצעה ל-2 מתחמים"
        extractor = BrochureLotExtractor()
        assert extractor._extract_section3_bid_limits([text]) == 2

    def test_numeric_dash_three(self) -> None:
        """'ל-3 מתחמים' -> 3."""
        text = "מסלול מכרז\nניתן להגיש הצעה ל-3 מתחמים"
        extractor = BrochureLotExtractor()
        assert extractor._extract_section3_bid_limits([text]) == 3

    def test_unlimited_lelo_hagbala(self) -> None:
        """'ללא הגבלה' -> None (unlimited)."""
        text = "מסלול מכרז\nניתן להגיש הצעה ללא הגבלה על מספר המתחמים"
        extractor = BrochureLotExtractor()
        assert extractor._extract_section3_bid_limits([text]) is None

    def test_unlimited_lekol_hamithamim(self) -> None:
        """'לכל המתחמים' -> None (unlimited)."""
        text = "מסלול מכרז\nניתן להגיש הצעה לכל המתחמים"
        extractor = BrochureLotExtractor()
        assert extractor._extract_section3_bid_limits([text]) is None

    def test_one_lot_without_bilvad(self) -> None:
        """'למתחם אחד' without בלבד -> 1."""
        text = "מסלול מכרז\nניתן להגיש הצעה למתחם אחד"
        extractor = BrochureLotExtractor()
        assert extractor._extract_section3_bid_limits([text]) == 1


class TestExtractSection3BidLimitsReversedHebrew:
    """Tests for bid-limit extraction with reversed (RTL) Hebrew text."""

    def test_reversed_one_lot_bilvad(self) -> None:
        """'דבלב דחא םחתמל' -> 1."""
        text = "זרכמ לולסמ\nדבלב דחא םחתמל העצה שיגהל ןתינ"
        extractor = BrochureLotExtractor()
        assert extractor._extract_section3_bid_limits([text]) == 1

    def test_reversed_two_lots(self) -> None:
        """'םימחתמ ינשל' -> 2."""
        text = "זרכמ לולסמ\nםימחתמ ינשל העצה שיגהל ןתינ"
        extractor = BrochureLotExtractor()
        assert extractor._extract_section3_bid_limits([text]) == 2

    def test_reversed_three_lots(self) -> None:
        """'םימחתמ השולשל' -> 3."""
        text = "זרכמ לולסמ\nםימחתמ השולשל העצה שיגהל ןתינ"
        extractor = BrochureLotExtractor()
        assert extractor._extract_section3_bid_limits([text]) == 3

    def test_reversed_numeric_dash(self) -> None:
        """'םימחתמ 2-ל' -> 2."""
        text = "זרכמ לולסמ\nםימחתמ 2-ל העצה שיגהל ןתינ"
        extractor = BrochureLotExtractor()
        assert extractor._extract_section3_bid_limits([text]) == 2

    def test_reversed_unlimited(self) -> None:
        """'הלבגה אלל' -> None (unlimited)."""
        text = "זרכמ לולסמ\nםימחתמה רפסמ לע הלבגה אלל העצה שיגהל ןתינ"
        extractor = BrochureLotExtractor()
        assert extractor._extract_section3_bid_limits([text]) is None

    def test_reversed_all_lots(self) -> None:
        """'םימחתמה לכל' -> None (unlimited)."""
        text = "זרכמ לולסמ\nםימחתמה לכל העצה שיגהל ןתינ"
        extractor = BrochureLotExtractor()
        assert extractor._extract_section3_bid_limits([text]) is None


class TestExtractSection3BidLimitsEdgeCases:
    """Edge cases for bid-limit extraction."""

    def test_no_section3_header(self) -> None:
        """No Section 3 header — falls back to scanning all text."""
        text = "some unrelated text with no bid limit info"
        extractor = BrochureLotExtractor()
        assert extractor._extract_section3_bid_limits([text]) is None

    def test_empty_page_texts(self) -> None:
        """Empty page list -> None."""
        extractor = BrochureLotExtractor()
        assert extractor._extract_section3_bid_limits([]) is None

    def test_section3_with_no_limit_mentioned(self) -> None:
        """Section 3 exists but contains no bid-limit language."""
        text = "מסלול מכרז\nהמכרז כולל 5 מתחמים באזור הדרום. פרטים נוספים."
        extractor = BrochureLotExtractor()
        assert extractor._extract_section3_bid_limits([text]) is None

    def test_section3_bounded_by_section4(self) -> None:
        """Section 3 text should stop at Section 4 header."""
        # The bid limit is in Section 3, unrelated text is in Section 4.
        text = (
            "מסלול מכרז\nניתן להגיש הצעה למתחם אחד בלבד\n"
            "סעיף 4\nכאן טקסט של סעיף 4"
        )
        extractor = BrochureLotExtractor()
        assert extractor._extract_section3_bid_limits([text]) == 1

    def test_multi_page_section3(self) -> None:
        """Section 3 text split across two pages."""
        page1 = "כללי\nמסלול מכרז"
        page2 = "ניתן להגיש הצעה לשני מתחמים\nסעיף 4\nפרטים"
        extractor = BrochureLotExtractor()
        assert extractor._extract_section3_bid_limits([page1, page2]) == 2

    def test_specific_limit_takes_priority_over_unlimited(self) -> None:
        """If both a specific limit and unlimited marker appear, specific wins."""
        text = (
            "מסלול מכרז\n"
            "ניתן להגיש הצעה לשני מתחמים בלבד, ללא הגבלה על סכום"
        )
        extractor = BrochureLotExtractor()
        assert extractor._extract_section3_bid_limits([text]) == 2

    def test_keyword_fallback_with_number(self) -> None:
        """Keyword-based fallback extracts a number near the keyword."""
        text = "מסלול מכרז\nמספר מתחמים מרבי: 4 מתחמים"
        extractor = BrochureLotExtractor()
        assert extractor._extract_section3_bid_limits([text]) == 4


class TestParseBidLimitValue:
    """Tests for BrochureLotExtractor._parse_bid_limit_value."""

    def test_digit_string(self) -> None:
        assert BrochureLotExtractor._parse_bid_limit_value("3") == 3

    def test_hebrew_word_normal(self) -> None:
        assert BrochureLotExtractor._parse_bid_limit_value("שני") == 2

    def test_hebrew_word_reversed(self) -> None:
        assert BrochureLotExtractor._parse_bid_limit_value("דחא") == 1

    def test_unknown_word(self) -> None:
        assert BrochureLotExtractor._parse_bid_limit_value("unknown") is None


class TestFindSection3Text:
    """Tests for BrochureLotExtractor._find_section3_text."""

    def test_normal_header(self) -> None:
        pages = ["intro\nמסלול מכרז\ncontent here\nסעיף 4\nafter"]
        result = BrochureLotExtractor._find_section3_text(pages)
        assert "מסלול מכרז" in result
        assert "content here" in result
        assert "after" not in result

    def test_reversed_header(self) -> None:
        pages = ["intro\nזרכמ לולסמ\ncontent here"]
        result = BrochureLotExtractor._find_section3_text(pages)
        assert "זרכמ לולסמ" in result
        assert "content here" in result

    def test_no_header(self) -> None:
        pages = ["no relevant headers here"]
        result = BrochureLotExtractor._find_section3_text(pages)
        assert result == ""

    def test_empty_pages(self) -> None:
        result = BrochureLotExtractor._find_section3_text([])
        assert result == ""


# ============================================================================
# Section 2 — helper function unit tests
# ============================================================================


class TestFindHeaderOffset:
    """Tests for _find_header_offset()."""

    def test_finds_normal_header(self) -> None:
        text = "some preamble\nהיבט תכנוני ופיזי\ncontent"
        assert _find_header_offset(text, SECTION2_HEADERS) >= 0

    def test_finds_reversed_header(self) -> None:
        text = "some preamble\nיזיפו ינונכת טביה\ncontent"
        assert _find_header_offset(text, SECTION2_HEADERS) >= 0

    def test_finds_partial_header(self) -> None:
        text = "some preamble\nתכנוני ופיזי\ncontent"
        assert _find_header_offset(text, SECTION2_HEADERS) >= 0

    def test_not_found(self) -> None:
        text = "no matching header here at all"
        assert _find_header_offset(text, SECTION2_HEADERS) == -1


class TestFindZoningColumnMapping:
    """Tests for _find_zoning_column_mapping()."""

    def test_full_zoning_table_header(self) -> None:
        header = ["מתחם", "תכנית", "ייעוד"]
        mapping = _find_zoning_column_mapping(header)
        assert mapping["lot_number"] == 0
        assert mapping["zoning_plan"] == 1
        assert mapping["zoning_designation"] == 2

    def test_reversed_zoning_header(self) -> None:
        header = ["םחתמ", "תינכת", "דועיי"]
        mapping = _find_zoning_column_mapping(header)
        assert mapping["lot_number"] == 0
        assert mapping["zoning_plan"] == 1
        assert mapping["zoning_designation"] == 2

    def test_plan_only_no_designation(self) -> None:
        header = ["מתחם", 'תב"ע']
        mapping = _find_zoning_column_mapping(header)
        assert mapping["lot_number"] == 0
        assert mapping["zoning_plan"] == 1
        assert "zoning_designation" not in mapping

    def test_no_lot_number(self) -> None:
        """Without lot_number column, mapping should not include it."""
        header = ["תכנית", "ייעוד"]
        mapping = _find_zoning_column_mapping(header)
        assert "lot_number" not in mapping
        assert "zoning_plan" in mapping


class TestExtractAllPlanNumbers:
    """Tests for _extract_all_plan_numbers()."""

    def test_single_plan(self) -> None:
        text = "תכנית 606-0458471 חלה על המתחם"
        plans = _extract_all_plan_numbers(text)
        assert "606-0458471" in plans

    def test_multiple_plans(self) -> None:
        text = "תכנית 606-0458471 ותכנית 401-0123456"
        plans = _extract_all_plan_numbers(text)
        assert len(plans) == 2
        assert "606-0458471" in plans
        assert "401-0123456" in plans

    def test_filters_dates(self) -> None:
        text = "תאריך 15/02/2026 ותכנית 606-0458471"
        plans = _extract_all_plan_numbers(text)
        # The date should be filtered out
        assert all("15/02/2026" not in p for p in plans)

    def test_no_plans(self) -> None:
        text = "no plan numbers in this text at all"
        assert _extract_all_plan_numbers(text) == []

    def test_deduplicates(self) -> None:
        text = "תכנית 606-0458471 ותכנית 606-0458471"
        plans = _extract_all_plan_numbers(text)
        assert len(plans) == 1


class TestExtractDesignation:
    """Tests for _extract_designation()."""

    def test_normal_megurim(self) -> None:
        assert _extract_designation("ייעוד: מגורים") == "מגורים"

    def test_normal_mischar(self) -> None:
        assert _extract_designation("ייעוד: מסחר") == "מסחר"

    def test_reversed_megurim(self) -> None:
        assert _extract_designation("דועיי: םירוגמ") == "מגורים"

    def test_reversed_taasiya(self) -> None:
        assert _extract_designation("דועיי: היישעת") == "תעשיה"

    def test_mixed_use(self) -> None:
        assert _extract_designation("ייעוד: מעורב") == "מעורב"

    def test_no_designation(self) -> None:
        assert _extract_designation("no designation here") is None


# ============================================================================
# Section 2 — _find_section2_text
# ============================================================================


class TestFindSection2Text:
    """Tests for _find_section2_text()."""

    def test_normal_header_single_page(self) -> None:
        """Section 2 on single page with both headers."""
        text = (
            "פרק 1 כללי\n"
            "היבט תכנוני ופיזי\n"
            "תכנית 606-0458471 חלה על המתחם\n"
            "היבט כלכלי\n"
            "מחיר מינימום 1000000"
        )
        page = _make_mock_page(text=text)
        section_text, section_pages = _find_section2_text([page])

        assert "606-0458471" in section_text
        assert "מחיר מינימום" not in section_text
        assert len(section_pages) == 1

    def test_reversed_header(self) -> None:
        """Section 2 with reversed Hebrew header."""
        text = (
            "1 קרפ\n"
            "יזיפו ינונכת טביה\n"
            "תכנית 606-0458471\n"
            "ילכלכ טביה\n"
            "other content"
        )
        page = _make_mock_page(text=text)
        section_text, section_pages = _find_section2_text([page])

        assert "606-0458471" in section_text
        assert "other content" not in section_text

    def test_multi_page_section(self) -> None:
        """Section 2 spans two pages."""
        page1_text = "intro\nהיבט תכנוני ופיזי\nplan info start"
        page2_text = "plan info continues\nהיבט כלכלי\nfinancial stuff"
        page1 = _make_mock_page(text=page1_text)
        page2 = _make_mock_page(text=page2_text)

        section_text, section_pages = _find_section2_text([page1, page2])

        assert "plan info start" in section_text
        assert "plan info continues" in section_text
        assert "financial stuff" not in section_text
        assert len(section_pages) == 2

    def test_no_section2_header(self) -> None:
        """No Section 2 header found at all."""
        page = _make_mock_page(text="completely unrelated content")
        section_text, section_pages = _find_section2_text([page])

        assert section_text == ""
        assert section_pages == []

    def test_empty_section(self) -> None:
        """Section 2 header immediately followed by Section 3 header."""
        text = "היבט תכנוני ופיזי\nהיבט כלכלי\ncontent"
        page = _make_mock_page(text=text)
        section_text, _ = _find_section2_text([page])

        # There is a newline between the headers, so text will be very short
        # but not necessarily empty (contains the header itself).
        # The key assertion: Section 3 content should not be included.
        assert "content" not in section_text


# ============================================================================
# Section 2 — _extract_zoning_from_tables
# ============================================================================


class TestExtractZoningFromTables:
    """Tests for _extract_zoning_from_tables()."""

    def test_table_with_plan_and_designation(self) -> None:
        """Table with lot, plan, and designation columns."""
        table = [
            ["מתחם", "תכנית", "ייעוד"],
            ["1", "606-0458471", "מגורים"],
            ["2", "606-0458472", "מסחר"],
        ]
        page = _make_mock_page(tables=[table], text="")
        result = _extract_zoning_from_tables([page])

        assert len(result) == 2
        assert result[1]["zoning_plan"] == "606-0458471"
        assert result[1]["zoning_designation"] == "מגורים"
        assert result[2]["zoning_plan"] == "606-0458472"
        assert result[2]["zoning_designation"] == "מסחר"

    def test_table_plan_only(self) -> None:
        """Table with lot and plan but no designation."""
        table = [
            ["מתחם", 'תב"ע'],
            ["1", "606-0458471"],
            ["2", "606-0458472"],
        ]
        page = _make_mock_page(tables=[table], text="")
        result = _extract_zoning_from_tables([page])

        assert len(result) == 2
        assert result[1]["zoning_plan"] == "606-0458471"
        assert "zoning_designation" not in result[1]

    def test_reversed_table_headers(self) -> None:
        """Table with reversed Hebrew column headers."""
        table = [
            ["םחתמ", "תינכת", "דועיי"],
            ["1", "606-0458471", "מגורים"],
        ]
        page = _make_mock_page(tables=[table], text="")
        result = _extract_zoning_from_tables([page])

        assert len(result) == 1
        assert result[1]["zoning_plan"] == "606-0458471"

    def test_no_qualifying_table(self) -> None:
        """No table with both lot_number and zoning columns."""
        table = [
            ["שם", "כתובת"],
            ["test", "test address"],
        ]
        page = _make_mock_page(tables=[table], text="")
        result = _extract_zoning_from_tables([page])

        assert result == {}

    def test_empty_pages(self) -> None:
        result = _extract_zoning_from_tables([])
        assert result == {}


# ============================================================================
# Section 2 — _extract_zoning_from_text
# ============================================================================


class TestExtractZoningFromText:
    """Tests for _extract_zoning_from_text()."""

    def test_single_plan_for_all_lots(self) -> None:
        """Single plan in text, no lot-specific references."""
        text = "תכנית 606-0458471 חלה על כל המתחמים. ייעוד: מגורים"
        result = _extract_zoning_from_text(text)

        # Should use sentinel key 0 for "all lots".
        assert 0 in result
        assert result[0]["zoning_plan"] == "606-0458471"
        assert result[0]["zoning_designation"] == "מגורים"

    def test_per_lot_plans(self) -> None:
        """Different plans for different lots."""
        text = (
            "מתחם 1 - תכנית 606-0458471 ייעוד מגורים\n"
            "מתחם 2 - תכנית 401-0123456 ייעוד מסחר"
        )
        result = _extract_zoning_from_text(text)

        assert 1 in result
        assert result[1]["zoning_plan"] == "606-0458471"
        assert result[1]["zoning_designation"] == "מגורים"
        assert 2 in result
        assert result[2]["zoning_plan"] == "401-0123456"
        assert result[2]["zoning_designation"] == "מסחר"

    def test_reversed_lot_reference(self) -> None:
        """Reversed Hebrew lot reference with plan."""
        text = "םחתמ 1 - תכנית 606-0458471 מגורים"
        result = _extract_zoning_from_text(text)

        assert 1 in result
        assert result[1]["zoning_plan"] == "606-0458471"

    def test_designation_only_no_plan(self) -> None:
        """Section with designation but no plan number."""
        text = "ייעוד הקרקע: מגורים"
        result = _extract_zoning_from_text(text)

        assert 0 in result
        assert result[0]["zoning_designation"] == "מגורים"
        assert "zoning_plan" not in result[0]

    def test_no_zoning_data(self) -> None:
        """Text with no plan numbers or designation keywords."""
        text = "this text has nothing relevant"
        result = _extract_zoning_from_text(text)

        assert result == {}


# ============================================================================
# Section 2 — integration tests via BrochureLotExtractor._extract_section2_zoning
# ============================================================================


class TestExtractSection2ZoningSinglePlan:
    """Single plan shared across all lots."""

    def test_single_plan_text_based(self) -> None:
        """Single plan in prose text, no table."""
        text = (
            "פרק 1 כללי\n"
            "היבט תכנוני ופיזי\n"
            "על המתחמים חלה תכנית 606-0458471\n"
            "ייעוד: מגורים\n"
            "היבט כלכלי\n"
            "financial details"
        )
        page = _make_mock_page(text=text)
        extractor = BrochureLotExtractor()
        result = extractor._extract_section2_zoning([page])

        assert 0 in result
        assert result[0]["zoning_plan"] == "606-0458471"
        assert result[0]["zoning_designation"] == "מגורים"


class TestExtractSection2ZoningMultiplePlans:
    """Different plans for different lots."""

    def test_per_lot_text_based(self) -> None:
        """Each lot has its own plan in text."""
        text = (
            "היבט תכנוני ופיזי\n"
            "מתחם 1 - תכנית 606-0458471 ייעוד מגורים\n"
            "מתחם 2 - תכנית 401-0123456 ייעוד מסחר\n"
            "היבט כלכלי"
        )
        page = _make_mock_page(text=text)
        extractor = BrochureLotExtractor()
        result = extractor._extract_section2_zoning([page])

        assert 1 in result
        assert result[1]["zoning_plan"] == "606-0458471"
        assert result[1]["zoning_designation"] == "מגורים"
        assert 2 in result
        assert result[2]["zoning_plan"] == "401-0123456"
        assert result[2]["zoning_designation"] == "מסחר"


class TestExtractSection2ZoningTableFormat:
    """Plan data in a table."""

    def test_zoning_table(self) -> None:
        """Section 2 contains a zoning table with lot, plan, designation."""
        table = [
            ["מתחם", "תכנית", "ייעוד"],
            ["1", "606-0458471", "מגורים"],
            ["2", "606-0458472", "מסחר"],
            ["3", "606-0458473", "תעשיה"],
        ]
        text = (
            "היבט תכנוני ופיזי\n"
            "הפירוט מופיע בטבלה\n"
            "היבט כלכלי"
        )
        page = _make_mock_page(tables=[table], text=text)
        extractor = BrochureLotExtractor()
        result = extractor._extract_section2_zoning([page])

        assert len(result) == 3
        assert result[1]["zoning_plan"] == "606-0458471"
        assert result[1]["zoning_designation"] == "מגורים"
        assert result[2]["zoning_plan"] == "606-0458472"
        assert result[2]["zoning_designation"] == "מסחר"
        assert result[3]["zoning_plan"] == "606-0458473"
        assert result[3]["zoning_designation"] == "תעשיה"


class TestExtractSection2ZoningReversedHeader:
    """Section 2 with reversed Hebrew header."""

    def test_reversed_section_header(self) -> None:
        """The reversed Hebrew form 'יזיפו ינונכת טביה' is detected."""
        text = (
            "1 קרפ\n"
            "יזיפו ינונכת טביה\n"
            "תכנית 606-0458471 חלה על המתחמים\n"
            "מגורים\n"
            "ילכלכ טביה"
        )
        page = _make_mock_page(text=text)
        extractor = BrochureLotExtractor()
        result = extractor._extract_section2_zoning([page])

        assert 0 in result
        assert result[0]["zoning_plan"] == "606-0458471"
        assert result[0]["zoning_designation"] == "מגורים"


class TestExtractSection2ZoningNotFound:
    """No Section 2 header found."""

    def test_no_section2(self) -> None:
        """Pages without Section 2 header return empty dict."""
        page = _make_mock_page(text="completely unrelated document content")
        extractor = BrochureLotExtractor()
        result = extractor._extract_section2_zoning([page])

        assert result == {}

    def test_empty_pages(self) -> None:
        """Empty page list returns empty dict."""
        extractor = BrochureLotExtractor()
        result = extractor._extract_section2_zoning([])

        assert result == {}


class TestExtractSection2ZoningEmptySection:
    """Section 2 header found but no zoning data inside."""

    def test_empty_section_content(self) -> None:
        """Section 2 exists but has no plan or designation info."""
        text = (
            "היבט תכנוני ופיזי\n"
            "מידע כללי ללא פרטי תכנון\n"
            "היבט כלכלי"
        )
        page = _make_mock_page(text=text)
        extractor = BrochureLotExtractor()
        result = extractor._extract_section2_zoning([page])

        assert result == {}

    def test_section_with_only_designation(self) -> None:
        """Section has designation but no plan number."""
        text = (
            "היבט תכנוני ופיזי\n"
            "ייעוד הקרקע: תעשיה\n"
            "היבט כלכלי"
        )
        page = _make_mock_page(text=text)
        extractor = BrochureLotExtractor()
        result = extractor._extract_section2_zoning([page])

        # Should still extract the designation under sentinel key 0
        assert 0 in result
        assert result[0]["zoning_designation"] == "תעשיה"


# ============================================================================
# _extract_zoning_inline — inline plan + designation from full text
# ============================================================================


class TestExtractZoningInline:
    """Tests for _extract_zoning_inline() — inline plan extraction from
    first-publication documents."""

    def test_standard_inline_plan_and_designation(self) -> None:
        """Standard reversed inline pattern with plan + designation."""
        text = (
            "זרכמה יטרפ רתי ,הקוסעת וניה םישרגמה דועי "
            ",620-0876573 תינכות הלח םישרגמה לע"
        )
        result = _extract_zoning_inline(text)
        assert 0 in result
        assert result[0]["zoning_plan"] == "620-0876573"
        assert result[0]["zoning_designation"] == "תעסוקה"

    def test_inline_plan_with_tmm_qualifier(self) -> None:
        """Plan with מ"מת (תמ"מ) qualifier."""
        text = '.605-0543108 מ"מת תינכת הלח ןיעקרקמה לע'
        result = _extract_zoning_inline(text)
        assert 0 in result
        assert result[0]["zoning_plan"] == "605-0543108"

    def test_inline_plan_megurim_designation(self) -> None:
        """Residential designation with plan number."""
        text = (
            "זרכמה יטרפ רתי ,םירוגמ וניה םישרגמה דועי "
            ",302-1169606 תינכות הלח םישרגמה לע"
        )
        result = _extract_zoning_inline(text)
        assert 0 in result
        assert result[0]["zoning_plan"] == "302-1169606"
        assert result[0]["zoning_designation"] == "מגורים"

    def test_inline_designation_with_mixed_use(self) -> None:
        """Mixed-use designation (e.g. מגורים and תעסוקה)."""
        text = (
            "הקוסעתו רחסמ ,םירוגמ וניה םישרגמה דועי "
            ",302-1169606 תינכות הלח םישרגמה לע"
        )
        result = _extract_zoning_inline(text)
        assert 0 in result
        # Should match the first known keyword
        assert result[0]["zoning_designation"] == "מגורים"

    def test_inline_plan_on_mitcham(self) -> None:
        """Pattern with 'םחתמה לע' (על המתחם) instead of םישרגמה."""
        text = (
            "זרכמה יטרפ רתי ,היינחו םיעצומו םימייק םישיבכ וניה םחתמה דועי "
            ",159/03/4 תינכות הלח םחתמה לע"
        )
        result = _extract_zoning_inline(text)
        assert 0 in result
        assert result[0]["zoning_plan"] == "159/03/4"

    def test_no_inline_zoning(self) -> None:
        """Document with no inline zoning pattern returns empty dict."""
        text = "This document has no Hebrew zoning information at all."
        result = _extract_zoning_inline(text)
        assert result == {}

    def test_inline_plan_only_no_designation(self) -> None:
        """Plan found but no designation pattern."""
        text = ",620-0876573 תינכות הלח םישרגמה לע"
        result = _extract_zoning_inline(text)
        assert 0 in result
        assert result[0]["zoning_plan"] == "620-0876573"
        assert "zoning_designation" not in result[0]


# ============================================================================
# _extract_lots_from_text — text-based lot extraction fallback
# ============================================================================


class TestExtractLotsFromText:
    """Tests for _extract_lots_from_text() — lot extraction from body text
    when no table is found."""

    def test_single_lot_with_units(self) -> None:
        """Single lot document with unit count."""
        text = (
            "הרדחב\n"
            'הקוסעתו רחסמ ,ד"חי 554 תיינבל\n'
            "דחא םחתמב\n"
        )
        lots = _extract_lots_from_text(text)
        assert len(lots) == 1
        assert lots[0]["lot_number"] == 1
        assert lots[0]["units_target_price"] == 554

    def test_multiple_lots_from_text(self) -> None:
        """Multiple lots mentioned in text."""
        text = (
            "לאימרכ ,ןובנ תמרב היוור הינבב\n"
            'םימחתמ 3 -ב ד"חי 302 תיינבל\n'
        )
        lots = _extract_lots_from_text(text)
        assert len(lots) == 3
        assert all(lot["lot_number"] == i + 1 for i, lot in enumerate(lots))

    def test_no_lots_in_text(self) -> None:
        """Document with no lot/unit indicators returns single placeholder."""
        text = "completely unrelated content without any lot data"
        lots = _extract_lots_from_text(text)
        # Still returns 1 placeholder lot (default for documents)
        assert len(lots) == 1
        assert lots[0]["lot_number"] == 1
        assert lots[0]["confidence"] == 0.5

    def test_single_lot_without_units(self) -> None:
        """Single lot document without unit count."""
        text = "דחא םחתמב תיתוריית הייצקרטאל"
        lots = _extract_lots_from_text(text)
        assert len(lots) == 1
        assert lots[0]["lot_number"] == 1
        assert lots[0].get("units_target_price") is None


# ============================================================================
# Section 1 — new column recognition tests
# ============================================================================


class TestSection1NewColumns:
    """Tests for new column keywords added to SECTION1_HEADERS."""

    def test_helka_column_recognized(self) -> None:
        """חלקה/הקלח column is recognized."""
        header = ["חטש\nר''מב\nךרעב", "הקלח", "שוג", "שרגמ", "םחתמ"]
        mapping = _find_section1_column_mapping(header)
        assert "helka" in mapping
        assert "gush" in mapping
        assert "plot_numbers" in mapping
        assert "lot_number" in mapping
        assert "area_sqm" in mapping

    def test_total_units_column_recognized(self) -> None:
        """ד"חי רפסמ (מספר יח"ד) is recognized as total_units."""
        header = ['ד"חי רפסמ', "םישרגמ", "םחתמ"]
        mapping = _find_section1_column_mapping(header)
        assert "total_units" in mapping

    def test_rental_sale_columns_recognized(self) -> None:
        """הרכשהל (להשכרה) and הריכמל (למכירה) are recognized."""
        header = ["הריכמל", "הרכשהל", "חטש", "םחתמ"]
        mapping = _find_section1_column_mapping(header)
        assert "units_free_market" in mapping  # הריכמל = למכירה
        assert "units_target_price" in mapping  # הרכשהל = להשכרה

    def test_tokhnit_column_in_section2(self) -> None:
        """תוקלח (חלקות) column variant is recognized."""
        header = ["חטש\nר''מב\nךרעב", "תוקלח\n(קלחב)", "שוג\n(המוש)", "םחתמ"]
        mapping = _find_section1_column_mapping(header)
        assert "helka" in mapping
        assert "gush" in mapping


# ============================================================================
# Integration: extract_all with inline zoning fallback
# ============================================================================


class TestExtractAllInlineZoning:
    """Integration tests for extract_all using inline zoning fallback."""

    def test_extract_all_with_no_section_headers(self) -> None:
        """extract_all should use inline zoning when no section headers exist.

        Simulates a first-publication document with inline text.
        """
        # Create a mock PDF with one page that has no Section 2 headers
        # but has inline zoning text.
        import io

        # Use a minimal mock to test the pipeline.
        page_text = (
            "הריכח תויוכז תשיכרל\n"
            'הקוסעתו רחסמ ,ד"חי 100 תיינבל\n'
            "דחא םחתמב\n"
            "זרכמה יטרפ רתי ,םירוגמ וניה םישרגמה דועי "
            ",620-0876573 תינכות הלח םישרגמה לע\n"
        )
        page = _make_mock_page(text=page_text)

        extractor = BrochureLotExtractor()
        # Test _extract_section2_zoning returns empty (no section headers)
        result = extractor._extract_section2_zoning([page])
        assert result == {}

        # Test inline fallback works on this text
        inline_result = _extract_zoning_inline(page_text)
        assert 0 in inline_result
        assert inline_result[0]["zoning_plan"] == "620-0876573"
        assert inline_result[0]["zoning_designation"] == "מגורים"
