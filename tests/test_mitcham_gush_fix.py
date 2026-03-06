"""Tests for the mitcham/gush data fix.

Covers:
    - extract_lots_from_api() preserving mitcham_name from raw MitchamName
    - Non-numeric MitchamName → positional fallback for lot_number
    - Numeric MitchamName → direct int conversion for lot_number
    - Null MitchamName → positional fallback
    - GushHelka[] → gush_helka_raw stored as list
    - merge_api_and_pdf_lots() preserving mitcham_name from API
    - merge_api_and_pdf_lots() using PDF lot_number as canonical
    - Strategy 3 merge (1 API lot vs N PDF lots) not blindly broadcasting gush
"""

import sys
from pathlib import Path

import pytest

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from data_client import extract_lots_from_api
from scripts.extract_lots_batch import (
    _enrich_pdf_with_api_aggregate,
    _overlay_pdf_onto_api,
    merge_api_and_pdf_lots,
)


# ============================================================================
# extract_lots_from_api tests
# ============================================================================


class TestExtractLotsPreservesMitchamName:
    """Verify mitcham_name field is set from raw MitchamName."""

    def test_simple_numeric_mitcham_name(self) -> None:
        details = {
            "MichrazID": 99999,
            "Tik": [
                {"MitchamName": "1121", "Shetach": 500},
            ],
        }
        lots = extract_lots_from_api(details)
        assert len(lots) == 1
        assert lots[0]["mitcham_name"] == "1121"

    def test_string_mitcham_name_preserved(self) -> None:
        details = {
            "MichrazID": 99999,
            "Tik": [
                {"MitchamName": "Lot A", "Shetach": 300},
            ],
        }
        lots = extract_lots_from_api(details)
        assert lots[0]["mitcham_name"] == "Lot A"


class TestExtractLotsNonNumericMitcham:
    """Mock API response with non-numeric MitchamName like '2 א'."""

    def test_non_numeric_mitcham_name_and_positional_fallback(self) -> None:
        details = {
            "MichrazID": 99999,
            "Tik": [
                {"MitchamName": "2 א", "Shetach": 100},
                {"MitchamName": "3 ב", "Shetach": 200},
            ],
        }
        lots = extract_lots_from_api(details)

        # mitcham_name should be the raw string
        assert lots[0]["mitcham_name"] == "2 א"
        assert lots[1]["mitcham_name"] == "3 ב"

        # lot_number should use 1-based positional fallback
        assert lots[0]["lot_number"] == 1
        assert lots[1]["lot_number"] == 2


class TestExtractLotsNumericMitcham:
    """Mock API response with numeric '1121' MitchamName."""

    def test_numeric_mitcham_parsed_as_lot_number(self) -> None:
        details = {
            "MichrazID": 99999,
            "Tik": [
                {"MitchamName": "1121"},
                {"MitchamName": "1124"},
            ],
        }
        lots = extract_lots_from_api(details)

        assert lots[0]["mitcham_name"] == "1121"
        assert lots[0]["lot_number"] == 1121

        assert lots[1]["mitcham_name"] == "1124"
        assert lots[1]["lot_number"] == 1124


class TestExtractLotsNullMitcham:
    """Mock API response with null MitchamName."""

    def test_null_mitcham_uses_positional_fallback(self) -> None:
        details = {
            "MichrazID": 99999,
            "Tik": [
                {"MitchamName": None, "Shetach": 400},
                {"Shetach": 500},  # MitchamName key missing entirely
            ],
        }
        lots = extract_lots_from_api(details)

        # No mitcham_name field when MitchamName is None or missing
        assert "mitcham_name" not in lots[0]
        assert "mitcham_name" not in lots[1]

        # lot_number uses 1-based positional fallback
        assert lots[0]["lot_number"] == 1
        assert lots[1]["lot_number"] == 2


class TestExtractLotsGushHelkaRaw:
    """Mock API response with GushHelka[], verify gush_helka_raw stored as list."""

    def test_gush_helka_raw_preserved(self) -> None:
        gush_helka_data = [
            {"Gush": "6001", "Helka": "10"},
            {"Gush": "6001", "Helka": "11"},
        ]
        details = {
            "MichrazID": 99999,
            "Tik": [
                {
                    "MitchamName": "1",
                    "GushHelka": gush_helka_data,
                },
            ],
        }
        lots = extract_lots_from_api(details)
        assert lots[0]["gush_helka_raw"] == gush_helka_data
        # Also check backward-compat comma-joined fields
        assert lots[0]["gush"] == "6001"
        assert lots[0]["helka"] == "10, 11"

    def test_empty_gush_helka_no_raw(self) -> None:
        details = {
            "MichrazID": 99999,
            "Tik": [
                {"MitchamName": "1", "GushHelka": []},
            ],
        }
        lots = extract_lots_from_api(details)
        assert "gush_helka_raw" not in lots[0]

    def test_multiple_gush_values(self) -> None:
        gush_helka_data = [
            {"Gush": "6001", "Helka": "10"},
            {"Gush": "6002", "Helka": "20"},
        ]
        details = {
            "MichrazID": 99999,
            "Tik": [
                {"MitchamName": "1", "GushHelka": gush_helka_data},
            ],
        }
        lots = extract_lots_from_api(details)
        assert lots[0]["gush"] == "6001, 6002"
        assert lots[0]["helka"] == "10, 20"
        assert lots[0]["gush_helka_raw"] == gush_helka_data


# ============================================================================
# merge_api_and_pdf_lots tests
# ============================================================================


class TestMergePreservesMitchamName:
    """Verify merged record has mitcham_name from API."""

    def test_exact_match_preserves_mitcham_name(self) -> None:
        api_lots = [
            {
                "lot_number": 1,
                "mitcham_name": "1121",
                "area_sqm": 500,
                "data_source": "api",
            },
        ]
        pdf_lots = [
            {
                "lot_number": 1,
                "units_target_price": 100,
                "data_source": "pdf",
            },
        ]
        merged = merge_api_and_pdf_lots(api_lots, pdf_lots)
        assert len(merged) == 1
        assert merged[0]["mitcham_name"] == "1121"
        assert merged[0]["data_source"] == "merged"

    def test_positional_match_preserves_mitcham_name(self) -> None:
        api_lots = [
            {
                "lot_number": 1121,
                "mitcham_name": "1121",
                "area_sqm": 500,
                "data_source": "api",
            },
        ]
        pdf_lots = [
            {
                "lot_number": 78343,
                "units_target_price": 100,
                "data_source": "pdf",
            },
        ]
        # Same count, no exact match → positional strategy
        merged = merge_api_and_pdf_lots(api_lots, pdf_lots)
        assert len(merged) == 1
        assert merged[0]["mitcham_name"] == "1121"


class TestMergePdfLotNumberCanonical:
    """Verify merged record uses PDF lot_number."""

    def test_overlay_uses_pdf_lot_number(self) -> None:
        api_lot = {
            "lot_number": 1121,
            "mitcham_name": "1121",
            "area_sqm": 500,
            "data_source": "api",
        }
        pdf_lot = {
            "lot_number": 1,
            "units_target_price": 100,
        }
        merged = _overlay_pdf_onto_api(api_lot, pdf_lot)
        # PDF lot_number is canonical
        assert merged["lot_number"] == 1
        # API mitcham_name preserved
        assert merged["mitcham_name"] == "1121"

    def test_positional_merge_uses_pdf_lot_number(self) -> None:
        api_lots = [
            {"lot_number": 1121, "mitcham_name": "1121", "data_source": "api"},
            {"lot_number": 1124, "mitcham_name": "1124", "data_source": "api"},
        ]
        pdf_lots = [
            {"lot_number": 1, "units_target_price": 50},
            {"lot_number": 2, "units_target_price": 75},
        ]
        merged = merge_api_and_pdf_lots(api_lots, pdf_lots)
        assert merged[0]["lot_number"] == 1
        assert merged[1]["lot_number"] == 2
        assert merged[0]["mitcham_name"] == "1121"
        assert merged[1]["mitcham_name"] == "1124"


class TestMergeStrategy3NoBlindGushBroadcast:
    """1 API lot vs N PDF lots — Strategy 3 (pdf-granular enriched with api-aggregate).

    To trigger Strategy 3, API and PDF lot numbers must NOT have exact matches
    (otherwise Strategy 1 takes precedence). We use API lot_number=1121
    (from MitchamName) vs PDF lot_numbers 1,2,3.
    """

    def test_pdf_lot_with_gush_keeps_own(self) -> None:
        api_lots = [
            {
                "lot_number": 1121,
                "gush": "6001",
                "helka": "10",
                "mitcham_name": "1121",
                "gush_helka_raw": [{"Gush": "6001", "Helka": "10"}],
                "data_source": "api",
            },
        ]
        pdf_lots = [
            {"lot_number": 1, "gush": "7001", "helka": "20"},
            {"lot_number": 2, "gush": "7002", "helka": "30"},
            {"lot_number": 3},  # No gush — should get API's gush
        ]

        merged = merge_api_and_pdf_lots(api_lots, pdf_lots)
        assert len(merged) == 3

        # PDF lots that already have gush keep their own
        assert merged[0]["gush"] == "7001"
        assert merged[0]["helka"] == "20"

        assert merged[1]["gush"] == "7002"
        assert merged[1]["helka"] == "30"

        # PDF lot without gush gets API aggregate gush
        assert merged[2]["gush"] == "6001"
        assert merged[2]["helka"] == "10"

    def test_mitcham_name_not_broadcast_in_aggregate(self) -> None:
        """mitcham_name must NOT be broadcast in 1-to-many aggregate merge
        (Strategy 3) because it would create duplicate key violations.
        gush_helka_raw IS broadcast since it's supplementary data."""
        api_lots = [
            {
                "lot_number": 1121,
                "mitcham_name": "1121",
                "gush_helka_raw": [{"Gush": "6001", "Helka": "10"}],
                "data_source": "api",
            },
        ]
        pdf_lots = [
            {"lot_number": 1, "units_target_price": 50},
            {"lot_number": 2, "units_target_price": 75},
        ]
        merged = merge_api_and_pdf_lots(api_lots, pdf_lots)

        # mitcham_name should NOT be copied (would violate unique constraint)
        for lot in merged:
            assert "mitcham_name" not in lot or lot.get("mitcham_name") is None
            # gush_helka_raw IS copied (supplementary, not unique-constrained)
            assert lot["gush_helka_raw"] == [{"Gush": "6001", "Helka": "10"}]
            assert lot["data_source"] == "merged"


# ============================================================================
# Edge cases
# ============================================================================


class TestExtractLotsEdgeCases:
    """Edge cases for extract_lots_from_api."""

    def test_empty_tik_list(self) -> None:
        assert extract_lots_from_api({"MichrazID": 1, "Tik": []}) == []

    def test_missing_tik_key(self) -> None:
        assert extract_lots_from_api({"MichrazID": 1}) == []

    def test_whitespace_mitcham_name(self) -> None:
        details = {
            "MichrazID": 1,
            "Tik": [{"MitchamName": "  42  "}],
        }
        lots = extract_lots_from_api(details)
        assert lots[0]["mitcham_name"] == "42"
        assert lots[0]["lot_number"] == 42

    def test_mixed_numeric_and_non_numeric(self) -> None:
        details = {
            "MichrazID": 1,
            "Tik": [
                {"MitchamName": "100"},
                {"MitchamName": "2 א"},
                {"MitchamName": "300"},
            ],
        }
        lots = extract_lots_from_api(details)
        assert lots[0]["lot_number"] == 100
        assert lots[0]["mitcham_name"] == "100"

        assert lots[1]["lot_number"] == 2  # positional fallback (idx=1 → 2)
        assert lots[1]["mitcham_name"] == "2 א"

        assert lots[2]["lot_number"] == 300
        assert lots[2]["mitcham_name"] == "300"

    def test_numeric_fields_extracted(self) -> None:
        details = {
            "MichrazID": 1,
            "Tik": [
                {
                    "MitchamName": "1",
                    "Shetach": 1000.5,
                    "Kibolet": 200,
                    "MechirSaf": 5000000,
                    "SchumArvut": 100000,
                    "mechirShuma": 2500,
                    "HotzaotPituach": 300000,
                },
            ],
        }
        lots = extract_lots_from_api(details)
        lot = lots[0]
        assert lot["area_sqm"] == 1000.5
        assert lot["total_units"] == 200
        assert lot["min_price"] == 5000000
        assert lot["guarantee_amount"] == 100000
        assert lot["sqm_value_appraisal"] == 2500
        assert lot["development_costs"] == 300000

    def test_winner_fields_extracted(self) -> None:
        details = {
            "MichrazID": 1,
            "Tik": [
                {
                    "MitchamName": "1",
                    "ShemZoche": "  חברת בנייה בע\"מ  ",
                    "SchumZchiya": 7500000,
                },
            ],
        }
        lots = extract_lots_from_api(details)
        assert lots[0]["winner_name"] == "חברת בנייה בע\"מ"
        assert lots[0]["winning_amount"] == 7500000

    def test_zoning_plan_and_plots_extracted(self) -> None:
        details = {
            "MichrazID": 1,
            "Tik": [
                {
                    "MitchamName": "1",
                    "TochnitMigrash": [
                        {"Tochnit": "תב/2000", "MigrashName": "מ-1"},
                        {"Tochnit": "תב/2000", "MigrashName": "מ-2"},
                        {"Tochnit": "תב/3000", "MigrashName": "מ-3"},
                    ],
                },
            ],
        }
        lots = extract_lots_from_api(details)
        # Plans de-duplicated
        assert lots[0]["zoning_plan"] == "תב/2000, תב/3000"
        assert lots[0]["plot_numbers"] == "מ-1, מ-2, מ-3"


class TestMergeEdgeCases:
    """Edge cases for merge logic."""

    def test_no_api_lots_returns_pdf_lots(self) -> None:
        pdf_lots = [
            {"lot_number": 1, "area_sqm": 500},
        ]
        merged = merge_api_and_pdf_lots([], pdf_lots)
        assert len(merged) == 1
        assert merged[0]["data_source"] == "pdf"

    def test_no_pdf_lots_returns_api_lots(self) -> None:
        api_lots = [
            {"lot_number": 1, "area_sqm": 500, "data_source": "api"},
        ]
        merged = merge_api_and_pdf_lots(api_lots, [])
        assert len(merged) == 1
        assert merged[0]["data_source"] == "api"

    def test_api_more_than_pdf_keeps_extra_api(self) -> None:
        api_lots = [
            {"lot_number": 1121, "mitcham_name": "1121", "data_source": "api"},
            {"lot_number": 1124, "mitcham_name": "1124", "data_source": "api"},
            {"lot_number": 1127, "mitcham_name": "1127", "data_source": "api"},
        ]
        pdf_lots = [
            {"lot_number": 1, "units_target_price": 50},
        ]
        merged = merge_api_and_pdf_lots(api_lots, pdf_lots)
        assert len(merged) == 3
        # First lot merged with PDF
        assert merged[0]["lot_number"] == 1
        assert merged[0]["mitcham_name"] == "1121"
        # Extra API lots kept as-is
        assert merged[1]["lot_number"] == 1124
        assert merged[2]["lot_number"] == 1127
