"""
Tests for the analytics_enrichment module.

Covers price extraction, detail field capture, plan number extraction,
and edge cases (empty data, null values, Hebrew text).
"""

import json
import sys
from pathlib import Path

import pytest

# Ensure the project root is on sys.path so we can import project modules
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from analytics_enrichment import (
    capture_detail_api_fields,
    extract_taba_plan_numbers_from_cache,
    extract_winning_prices,
)


# ============================================================================
# FIXTURES — realistic mock detail data
# ============================================================================

@pytest.fixture
def detail_with_prices() -> dict:
    """Detail response with winning bids, floor prices, and bids."""
    return {
        "MichrazID": 20250275,
        "MichrazName": "275/2025",
        "KodMerchav": 3,
        "KodTzuratHaknaya": 2,
        "SchumHishtatfut": 5000.0,
        "KhalYaadRashi": 2,
        "Tik": [
            {
                "MichrazID": 20250275,
                "TikID": "0000800031679",
                "MitchamName": "74547",
                "Shetach": 8780,
                "Kibolet": 148,
                "HotzaotPituach": 36132250,
                "MechirSaf": 2814190.0,
                "mechirShuma": 20616777,
                "SchumArvut": 3613000,
                "ShemZoche": "אבני דרך י.י. בע\"מ ",
                "SchumZchiya": 24180180.0,
                "TochnitMigrash": [
                    {
                        "MichrazID": 20250275,
                        "TikID": "0000800031679",
                        "Tochnit": "307-0692160",
                        "MigrashName": "101",
                    },
                ],
                "mpHatzaaotMitcham": [
                    {"HatzaaSum": 24180180.0, "HatzaaDescription": 1},
                    {"HatzaaSum": 10814190.0, "HatzaaDescription": None},
                    {"HatzaaSum": 4185185.0, "HatzaaDescription": None},
                ],
                "GushHelka": [],
            },
            {
                "MichrazID": 20250275,
                "TikID": "0000800027071",
                "MitchamName": "74693",
                "Shetach": 10297,
                "Kibolet": 115,
                "HotzaotPituach": 46944435,
                "MechirSaf": 2365405.0,
                "mechirShuma": 17328975,
                "SchumArvut": 4694000,
                "ShemZoche": " אין הצעות למתחם זה",
                "SchumZchiya": 0.0,
                "TochnitMigrash": [
                    {"Tochnit": "307-0692160", "MigrashName": "300"},
                    {"Tochnit": "307-1119718", "MigrashName": "304"},
                ],
                "mpHatzaaotMitcham": [],
                "GushHelka": [],
            },
        ],
        "MichrazLinks": [
            {
                "url": "https://apps.land.gov.il/TabaSearch/#/Plans?planNumber=3050356,3052151",
                "DisplayText": "מאגר תוכניות בניין עיר",
                "CssClass": "icon-taba",
            },
        ],
    }


@pytest.fixture
def detail_no_prices() -> dict:
    """Detail response with empty Tik[] and no price data."""
    return {
        "MichrazID": 20260027,
        "MichrazName": "27/2026",
        "KodMerchav": 7,
        "KodTzuratHaknaya": 2,
        "SchumHishtatfut": None,
        "KhalYaadRashi": None,
        "Tik": [
            {
                "MichrazID": 20260027,
                "TikID": "0000800033444",
                "MitchamName": "91",
                "Shetach": 5016,
                "Kibolet": 0,
                "HotzaotPituach": 0,
                "MechirSaf": None,
                "mechirShuma": 0,
                "SchumZchiya": None,
                "ShemZoche": None,
                "TochnitMigrash": [
                    {"Tochnit": "5/10/ת/130", "MigrashName": "91"},
                ],
                "mpHatzaaotMitcham": [],
                "GushHelka": [],
            },
        ],
        "MichrazLinks": [
            {
                "url": "https://apps.land.gov.il/TabaSearch/#/Plans?planNumber=7001915",
                "DisplayText": "מאגר תוכניות בניין עיר",
                "CssClass": "icon-taba",
            },
        ],
    }


# ============================================================================
# extract_winning_prices
# ============================================================================

class TestExtractWinningPrices:
    """Tests for extract_winning_prices()."""

    def test_with_winning_bids(self, detail_with_prices: dict) -> None:
        """Should extract price rows including winning bid data."""
        rows = extract_winning_prices(detail_with_prices)

        assert len(rows) == 2

        # First tik has a real winner
        tik1 = rows[0]
        assert tik1["tender_id"] == 20250275
        assert tik1["tik_id"] == "0000800031679"
        assert tik1["mitcham_name"] == "74547"
        assert tik1["land_area"] == 8780
        assert tik1["floor_price"] == 2814190.0
        assert tik1["appraisal_price"] == 20616777
        assert tik1["winning_bid"] == 24180180.0
        assert tik1["winner_name"] == 'אבני דרך י.י. בע"מ'
        assert tik1["num_bids"] == 3
        assert tik1["highest_bid"] == 24180180.0
        assert tik1["lowest_bid"] == 4185185.0
        assert tik1["dev_costs"] == 36132250
        assert tik1["capacity_units"] == 148

    def test_tik_with_no_bids(self, detail_with_prices: dict) -> None:
        """Second tik has 'no bids' placeholder — winner_name should be None."""
        rows = extract_winning_prices(detail_with_prices)
        tik2 = rows[1]

        assert tik2["tik_id"] == "0000800027071"
        assert tik2["winning_bid"] is None  # SchumZchiya was 0
        assert tik2["winner_name"] is None  # contains "אין הצעות"
        assert tik2["num_bids"] == 0
        assert tik2["highest_bid"] is None
        assert tik2["lowest_bid"] is None

    def test_detail_without_prices(self, detail_no_prices: dict) -> None:
        """Tender with null/zero prices should still return rows with None values."""
        rows = extract_winning_prices(detail_no_prices)

        assert len(rows) == 1
        row = rows[0]
        assert row["tender_id"] == 20260027
        assert row["floor_price"] is None
        assert row["appraisal_price"] is None
        assert row["winning_bid"] is None
        assert row["winner_name"] is None
        assert row["num_bids"] == 0
        assert row["land_area"] == 5016  # Shetach is present

    def test_empty_detail(self) -> None:
        """Empty or None input should return empty list."""
        assert extract_winning_prices({}) == []
        assert extract_winning_prices(None) == []  # type: ignore[arg-type]

    def test_no_tik_key(self) -> None:
        """Detail without Tik key should return empty list."""
        assert extract_winning_prices({"MichrazID": 123}) == []

    def test_empty_tik_list(self) -> None:
        """Detail with empty Tik[] should return empty list."""
        assert extract_winning_prices({"MichrazID": 123, "Tik": []}) == []

    def test_tik_with_null_values(self) -> None:
        """Tik entries with all-null price fields should yield rows with None."""
        detail = {
            "MichrazID": 99999,
            "Tik": [
                {
                    "TikID": "T001",
                    "MitchamName": "test",
                    "Shetach": None,
                    "Kibolet": None,
                    "HotzaotPituach": None,
                    "MechirSaf": None,
                    "mechirShuma": None,
                    "SchumZchiya": None,
                    "ShemZoche": None,
                    "mpHatzaaotMitcham": None,
                },
            ],
        }
        rows = extract_winning_prices(detail)
        assert len(rows) == 1
        assert rows[0]["floor_price"] is None
        assert rows[0]["winning_bid"] is None
        assert rows[0]["land_area"] is None

    def test_hebrew_winner_name_preserved(self) -> None:
        """Hebrew characters in winner name should be preserved correctly."""
        detail = {
            "MichrazID": 11111,
            "Tik": [
                {
                    "TikID": "T002",
                    "MitchamName": "מתחם א",
                    "Shetach": 1000,
                    "MechirSaf": 500000.0,
                    "mechirShuma": 400000,
                    "SchumZchiya": 600000.0,
                    "ShemZoche": "  חברת בנייה ישראלית בע\"מ  ",
                    "Kibolet": 50,
                    "HotzaotPituach": 100000,
                    "mpHatzaaotMitcham": [
                        {"HatzaaSum": 600000.0},
                    ],
                },
            ],
        }
        rows = extract_winning_prices(detail)
        assert len(rows) == 1
        assert rows[0]["winner_name"] == 'חברת בנייה ישראלית בע"מ'


# ============================================================================
# capture_detail_api_fields
# ============================================================================

class TestCaptureDetailApiFields:
    """Tests for capture_detail_api_fields()."""

    def test_all_fields_present(self, detail_with_prices: dict) -> None:
        """Should extract acquisition_form, participation_fee, and land_area."""
        fields = capture_detail_api_fields(detail_with_prices)

        assert fields["tender_id"] == 20250275
        assert fields["acquisition_form"] == 2
        assert fields["participation_fee"] == 5000.0
        # land_area_sqm = 8780 + 10297 = 19077
        assert fields["land_area_sqm"] == 19077.0

    def test_null_participation_fee(self, detail_no_prices: dict) -> None:
        """Should return None for missing participation fee."""
        fields = capture_detail_api_fields(detail_no_prices)

        assert fields["tender_id"] == 20260027
        assert fields["acquisition_form"] == 2
        assert fields["participation_fee"] is None
        assert fields["land_area_sqm"] == 5016.0

    def test_empty_input(self) -> None:
        """Empty or None input should return empty dict."""
        assert capture_detail_api_fields({}) == {}
        assert capture_detail_api_fields(None) == {}  # type: ignore[arg-type]

    def test_no_tik_for_land_area(self) -> None:
        """Missing Tik[] should yield None for land_area_sqm."""
        detail = {
            "MichrazID": 12345,
            "KodTzuratHaknaya": 3,
            "SchumHishtatfut": 1000,
        }
        fields = capture_detail_api_fields(detail)
        assert fields["land_area_sqm"] is None
        assert fields["acquisition_form"] == 3
        assert fields["participation_fee"] == 1000.0


# ============================================================================
# extract_taba_plan_numbers_from_cache
# ============================================================================

class TestExtractTabaPlanNumbers:
    """Tests for extract_taba_plan_numbers_from_cache()."""

    def test_from_tochnitmigrash_and_links(
        self, detail_with_prices: dict, tmp_path: Path,
    ) -> None:
        """Should extract plan numbers from both TochnitMigrash and MichrazLinks."""
        cache_dir = tmp_path / "details_cache"
        cache_dir.mkdir()

        filepath = cache_dir / "20250275.json"
        filepath.write_text(
            json.dumps(detail_with_prices, ensure_ascii=False),
            encoding="utf-8",
        )

        result = extract_taba_plan_numbers_from_cache(cache_dir)

        assert 20250275 in result
        plans = result[20250275]
        # From TochnitMigrash: 307-0692160, 307-1119718
        # From MichrazLinks: 3050356, 3052151
        assert "307-0692160" in plans
        assert "307-1119718" in plans
        assert "3050356" in plans
        assert "3052151" in plans

    def test_single_plan_from_links(
        self, detail_no_prices: dict, tmp_path: Path,
    ) -> None:
        """Should extract plan number from a single TabaSearch link."""
        cache_dir = tmp_path / "details_cache"
        cache_dir.mkdir()

        filepath = cache_dir / "20260027.json"
        filepath.write_text(
            json.dumps(detail_no_prices, ensure_ascii=False),
            encoding="utf-8",
        )

        result = extract_taba_plan_numbers_from_cache(cache_dir)
        assert 20260027 in result
        plans = result[20260027]
        assert "7001915" in plans
        # Also has "5/10/ת/130" from TochnitMigrash (Hebrew plan number)
        assert "5/10/ת/130" in plans

    def test_empty_cache_dir(self, tmp_path: Path) -> None:
        """Empty cache directory should return empty dict."""
        cache_dir = tmp_path / "empty_cache"
        cache_dir.mkdir()
        result = extract_taba_plan_numbers_from_cache(cache_dir)
        assert result == {}

    def test_nonexistent_cache_dir(self, tmp_path: Path) -> None:
        """Non-existent directory should return empty dict."""
        result = extract_taba_plan_numbers_from_cache(tmp_path / "does_not_exist")
        assert result == {}

    def test_malformed_json_skipped(self, tmp_path: Path) -> None:
        """Malformed JSON files should be skipped without error."""
        cache_dir = tmp_path / "bad_cache"
        cache_dir.mkdir()

        bad_file = cache_dir / "99999.json"
        bad_file.write_text("{ invalid json", encoding="utf-8")

        good_detail = {
            "MichrazID": 11111,
            "Tik": [{"TikID": "T1", "TochnitMigrash": [{"Tochnit": "PLAN-001"}]}],
            "MichrazLinks": [],
        }
        good_file = cache_dir / "11111.json"
        good_file.write_text(
            json.dumps(good_detail, ensure_ascii=False),
            encoding="utf-8",
        )

        result = extract_taba_plan_numbers_from_cache(cache_dir)
        # Bad file skipped, good file processed
        assert 11111 in result
        assert "PLAN-001" in result[11111]
        assert 99999 not in result

    def test_detail_with_no_plan_data(self, tmp_path: Path) -> None:
        """Detail with empty TochnitMigrash and no MichrazLinks should be skipped."""
        cache_dir = tmp_path / "no_plans"
        cache_dir.mkdir()

        detail = {
            "MichrazID": 22222,
            "Tik": [
                {
                    "TikID": "T1",
                    "TochnitMigrash": [],
                    "mpHatzaaotMitcham": [],
                },
            ],
            "MichrazLinks": [],
        }
        filepath = cache_dir / "22222.json"
        filepath.write_text(
            json.dumps(detail, ensure_ascii=False),
            encoding="utf-8",
        )

        result = extract_taba_plan_numbers_from_cache(cache_dir)
        assert 22222 not in result  # No plans found = excluded


# ============================================================================
# Edge cases
# ============================================================================

class TestEdgeCases:
    """Additional edge case tests."""

    def test_tik_missing_tikid(self) -> None:
        """Tik entry without TikID should be skipped."""
        detail = {
            "MichrazID": 33333,
            "Tik": [
                {
                    "MitchamName": "missing-id",
                    "Shetach": 100,
                    "MechirSaf": 1000,
                    "mechirShuma": 900,
                    "SchumZchiya": 1200,
                    "ShemZoche": "test",
                    "mpHatzaaotMitcham": [],
                },
            ],
        }
        rows = extract_winning_prices(detail)
        assert len(rows) == 0

    def test_non_dict_tik_entries(self) -> None:
        """Non-dict entries in Tik[] should be skipped."""
        detail = {
            "MichrazID": 44444,
            "Tik": [None, "string", 42, {"TikID": "T1", "Shetach": 500, "mpHatzaaotMitcham": []}],
        }
        rows = extract_winning_prices(detail)
        assert len(rows) == 1
        assert rows[0]["tik_id"] == "T1"

    def test_non_numeric_bid_amounts_skipped(self) -> None:
        """Non-numeric HatzaaSum values should be skipped in bid collection."""
        detail = {
            "MichrazID": 55555,
            "Tik": [
                {
                    "TikID": "T1",
                    "Shetach": 200,
                    "MechirSaf": 1000,
                    "mechirShuma": 800,
                    "SchumZchiya": 1500.0,
                    "ShemZoche": "winner",
                    "mpHatzaaotMitcham": [
                        {"HatzaaSum": 1500.0},
                        {"HatzaaSum": "not-a-number"},
                        {"HatzaaSum": None},
                        {"HatzaaSum": 1200.0},
                    ],
                },
            ],
        }
        rows = extract_winning_prices(detail)
        assert len(rows) == 1
        assert rows[0]["num_bids"] == 2  # Only 1500 and 1200
        assert rows[0]["highest_bid"] == 1500.0
        assert rows[0]["lowest_bid"] == 1200.0

    def test_capture_fields_non_numeric_acquisition(self) -> None:
        """Non-numeric KodTzuratHaknaya should yield None."""
        detail = {
            "MichrazID": 66666,
            "KodTzuratHaknaya": "invalid",
            "SchumHishtatfut": "also-invalid",
            "Tik": [],
        }
        fields = capture_detail_api_fields(detail)
        assert fields["acquisition_form"] is None
        assert fields["participation_fee"] is None
        assert fields["land_area_sqm"] is None

    def test_multiple_cache_files_prices(self, tmp_path: Path) -> None:
        """extract_winning_prices_from_cache should aggregate across files."""
        from analytics_enrichment import extract_winning_prices_from_cache

        cache_dir = tmp_path / "multi_cache"
        cache_dir.mkdir()

        for i, tid in enumerate([11111, 22222]):
            detail = {
                "MichrazID": tid,
                "Tik": [
                    {
                        "TikID": f"T{i}",
                        "Shetach": 1000 + i * 500,
                        "MechirSaf": 50000.0,
                        "mechirShuma": 40000,
                        "SchumZchiya": 60000.0,
                        "ShemZoche": f"Winner {i}",
                        "Kibolet": 10,
                        "HotzaotPituach": 5000,
                        "mpHatzaaotMitcham": [{"HatzaaSum": 60000.0}],
                    },
                ],
            }
            filepath = cache_dir / f"{tid}.json"
            filepath.write_text(
                json.dumps(detail, ensure_ascii=False),
                encoding="utf-8",
            )

        rows = extract_winning_prices_from_cache(cache_dir)
        assert len(rows) == 2
        tender_ids = {r["tender_id"] for r in rows}
        assert tender_ids == {11111, 22222}
