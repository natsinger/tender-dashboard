"""
Analytics enrichment module for the Land Tenders Dashboard.

Extracts structured pricing data, plan numbers, and supplementary fields
from the tender detail API responses (cached JSON files). Builds aggregated
plan-level (taba) analytics and persists everything to Supabase via TenderDB.

Functions:
    extract_winning_prices      -- parse Tik[] price fields from a single detail
    extract_winning_prices_from_cache -- batch-process all cached detail files
    capture_detail_api_fields   -- pull acquisition_form, participation_fee, land_area
    extract_taba_plan_numbers_from_cache -- extract plan numbers from TochnitMigrash
    build_taba_analytics        -- aggregate plan-level stats from DB data
    derive_land_area            -- populate land_area_sqm from detail/building_rights
    run_full_enrichment         -- orchestrate the complete enrichment pipeline

Usage:
    from analytics_enrichment import run_full_enrichment
    stats = run_full_enrichment()
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from db import TenderDB

from config import DATA_DIR

logger = logging.getLogger(__name__)


# ============================================================================
# PRICE EXTRACTION
# ============================================================================

def extract_winning_prices(detail: dict) -> list[dict]:
    """Parse pricing data from a tender detail response's Tik[] array.

    Extracts floor price, appraisal, winning bid, winner name, and
    individual bid amounts from each tik (plot/lot) in the tender.

    Args:
        detail: A single tender detail dict from the RMI API.

    Returns:
        List of price row dicts ready for tender_prices table.
        Empty list if no Tik data exists.
    """
    if not detail or not isinstance(detail, dict):
        return []

    tender_id = detail.get("MichrazID")
    if not tender_id:
        return []

    tik_list = detail.get("Tik")
    if not tik_list or not isinstance(tik_list, list):
        return []

    price_rows: list[dict] = []

    for tik in tik_list:
        if not isinstance(tik, dict):
            continue

        tik_id = tik.get("TikID")
        if not tik_id:
            continue

        # Collect individual bids from mpHatzaaotMitcham
        bids: list[float] = []
        mp_bids = tik.get("mpHatzaaotMitcham")
        if isinstance(mp_bids, list):
            for bid in mp_bids:
                if isinstance(bid, dict):
                    bid_sum = bid.get("HatzaaSum")
                    if bid_sum is not None and isinstance(bid_sum, (int, float)):
                        bids.append(float(bid_sum))

        winning_bid = tik.get("SchumZchiya")
        # Treat 0 or None as no winning bid
        if winning_bid is not None and (not isinstance(winning_bid, (int, float)) or winning_bid == 0):
            winning_bid = None

        floor_price = tik.get("MechirSaf")
        if floor_price is not None and (not isinstance(floor_price, (int, float)) or floor_price == 0):
            floor_price = None

        appraisal = tik.get("mechirShuma")
        if appraisal is not None and (not isinstance(appraisal, (int, float)) or appraisal == 0):
            appraisal = None

        winner_name = tik.get("ShemZoche")
        if isinstance(winner_name, str):
            winner_name = winner_name.strip()
            # Some entries have placeholder text for "no bids"
            if not winner_name or "אין הצעות" in winner_name:
                winner_name = None

        capacity = tik.get("Kibolet")
        if capacity is not None and (not isinstance(capacity, (int, float)) or capacity == 0):
            capacity = None

        row: dict[str, Any] = {
            "tender_id": int(tender_id),
            "tik_id": str(tik_id),
            "mitcham_name": tik.get("MitchamName"),
            "land_area": tik.get("Shetach") if isinstance(tik.get("Shetach"), (int, float)) and tik.get("Shetach", 0) > 0 else None,
            "floor_price": float(floor_price) if floor_price is not None else None,
            "appraisal_price": float(appraisal) if appraisal is not None else None,
            "winning_bid": float(winning_bid) if winning_bid is not None else None,
            "winner_name": winner_name,
            "num_bids": len(bids) if bids else 0,
            "highest_bid": max(bids) if bids else None,
            "lowest_bid": min(bids) if bids else None,
            "dev_costs": tik.get("HotzaotPituach") if isinstance(tik.get("HotzaotPituach"), (int, float)) and tik.get("HotzaotPituach", 0) > 0 else None,
            "capacity_units": int(capacity) if capacity is not None else None,
        }
        price_rows.append(row)

    return price_rows


def extract_winning_prices_from_cache(
    cache_dir: Path,
) -> list[dict]:
    """Batch-process all detail cache files to extract price data.

    Args:
        cache_dir: Path to the directory containing detail JSON cache files.

    Returns:
        Flat list of all price rows across all cached tenders.
    """
    if not cache_dir.is_dir():
        logger.warning("Cache directory does not exist: %s", cache_dir)
        return []

    all_prices: list[dict] = []
    cache_files = sorted(cache_dir.glob("*.json"))
    logger.info("Processing %d cache files for price extraction", len(cache_files))

    for filepath in cache_files:
        try:
            detail = json.loads(filepath.read_text(encoding="utf-8"))
            prices = extract_winning_prices(detail)
            all_prices.extend(prices)
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Failed to process %s: %s", filepath.name, exc)

    logger.info("Extracted %d price rows from cache", len(all_prices))
    return all_prices


# ============================================================================
# DETAIL API FIELD CAPTURE
# ============================================================================

def capture_detail_api_fields(detail: dict) -> dict:
    """Extract supplementary fields from a tender detail response.

    Pulls fields not available in the list API: acquisition form code,
    participation fee, and total land area (summed across all tiks).

    Args:
        detail: A single tender detail dict from the RMI API.

    Returns:
        Dict with keys: tender_id, acquisition_form, participation_fee,
        land_area_sqm. Values may be None if not present.
    """
    if not detail or not isinstance(detail, dict):
        return {}

    tender_id = detail.get("MichrazID")
    if not tender_id:
        return {}

    # Acquisition form (KodTzuratHaknaya) -- integer code
    acquisition_form = detail.get("KodTzuratHaknaya")
    if acquisition_form is not None and not isinstance(acquisition_form, (int, float)):
        acquisition_form = None

    # Participation fee (SchumHishtatfut)
    participation_fee = detail.get("SchumHishtatfut")
    if participation_fee is not None and not isinstance(participation_fee, (int, float)):
        participation_fee = None

    # Sum land area across all tiks
    total_land_area: float = 0.0
    tik_list = detail.get("Tik")
    if isinstance(tik_list, list):
        for tik in tik_list:
            if isinstance(tik, dict):
                shetach = tik.get("Shetach")
                if isinstance(shetach, (int, float)) and shetach > 0:
                    total_land_area += float(shetach)

    return {
        "tender_id": int(tender_id),
        "acquisition_form": int(acquisition_form) if acquisition_form is not None else None,
        "participation_fee": float(participation_fee) if participation_fee is not None else None,
        "land_area_sqm": total_land_area if total_land_area > 0 else None,
    }


# ============================================================================
# TABA PLAN NUMBER EXTRACTION
# ============================================================================

# Regex to extract plan numbers from TabaSearch URLs
_TABA_URL_PATTERN = re.compile(r"planNumber=([^&]+)", re.IGNORECASE)


def extract_taba_plan_numbers_from_cache(
    cache_dir: Path,
) -> dict[int, list[str]]:
    """Extract plan numbers from TochnitMigrash and MichrazLinks in cached details.

    Collects plan numbers from two sources per tender:
    1. TochnitMigrash[].Tochnit field in each Tik
    2. MichrazLinks[].url containing TabaSearch plan numbers

    Args:
        cache_dir: Path to the directory containing detail JSON cache files.

    Returns:
        Dict mapping tender_id to deduplicated list of plan numbers.
    """
    if not cache_dir.is_dir():
        logger.warning("Cache directory does not exist: %s", cache_dir)
        return {}

    result: dict[int, list[str]] = {}
    cache_files = sorted(cache_dir.glob("*.json"))
    logger.info("Processing %d cache files for plan number extraction", len(cache_files))

    for filepath in cache_files:
        try:
            detail = json.loads(filepath.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Failed to process %s: %s", filepath.name, exc)
            continue

        if not isinstance(detail, dict):
            continue

        tender_id = detail.get("MichrazID")
        if not tender_id:
            continue

        plan_numbers: set[str] = set()

        # Source 1: TochnitMigrash in each Tik
        tik_list = detail.get("Tik")
        if isinstance(tik_list, list):
            for tik in tik_list:
                if not isinstance(tik, dict):
                    continue
                tochniots = tik.get("TochnitMigrash")
                if isinstance(tochniots, list):
                    for tm in tochniots:
                        if isinstance(tm, dict):
                            tochnit = tm.get("Tochnit")
                            if isinstance(tochnit, str) and tochnit.strip():
                                plan_numbers.add(tochnit.strip())

        # Source 2: MichrazLinks URLs with TabaSearch plan numbers
        links = detail.get("MichrazLinks")
        if isinstance(links, list):
            for link in links:
                if not isinstance(link, dict):
                    continue
                url = link.get("url", "")
                if not isinstance(url, str):
                    continue
                match = _TABA_URL_PATTERN.search(url)
                if match:
                    # May be comma-separated (e.g. "3050356,3052151")
                    raw_numbers = match.group(1)
                    for num in raw_numbers.split(","):
                        num = num.strip()
                        if num:
                            plan_numbers.add(num)

        if plan_numbers:
            result[int(tender_id)] = sorted(plan_numbers)

    logger.info(
        "Extracted plan numbers for %d tenders from cache", len(result),
    )
    return result


# ============================================================================
# TABA ANALYTICS BUILDER
# ============================================================================

def build_taba_analytics(db: TenderDB) -> list[dict]:
    """Build aggregated plan-level analytics from DB data.

    Combines tender metadata, plan numbers, and price data to produce
    one analytics row per unique plan number.

    Args:
        db: A TenderDB instance (from db.py).

    Returns:
        List of taba_analytics row dicts ready for upsert.
    """
    # Load all tenders
    tenders_df = db.load_current_tenders()
    if tenders_df.empty:
        logger.warning("No tenders loaded for taba analytics")
        return []

    # Load all prices
    prices_df = db.load_tender_prices()

    # Build a plan_number -> tender_ids mapping from tenders table
    plan_tenders: dict[str, list[dict]] = {}

    for _, row in tenders_df.iterrows():
        plan_number = row.get("plan_number")
        if not plan_number or not isinstance(plan_number, str):
            continue

        tender_info = {
            "tender_id": row.get("tender_id"),
            "units": row.get("units", 0) or 0,
            "city_code": row.get("city_code"),
            "purpose_code": row.get("purpose_code"),
            "rmi_region_code": row.get("rmi_region_code"),
            "publish_date": row.get("publish_date"),
            "land_area_sqm": row.get("land_area_sqm", 0) or 0,
        }
        plan_tenders.setdefault(plan_number, []).append(tender_info)

    if not plan_tenders:
        logger.info("No plan numbers found in tenders table")
        return []

    # Build price lookup by tender_id
    price_by_tender: dict[int, list[dict]] = {}
    if not prices_df.empty:
        for _, prow in prices_df.iterrows():
            tid = prow.get("tender_id")
            if tid is not None:
                price_by_tender.setdefault(int(tid), []).append(prow.to_dict())

    analytics_rows: list[dict] = []
    now_iso = datetime.now().isoformat()

    for plan_number, tender_list in plan_tenders.items():
        tender_ids = [t["tender_id"] for t in tender_list]
        total_units = sum(int(t["units"]) for t in tender_list if t["units"])
        total_land = sum(float(t["land_area_sqm"]) for t in tender_list if t["land_area_sqm"])

        region_codes = sorted({
            int(t["rmi_region_code"])
            for t in tender_list
            if t.get("rmi_region_code") is not None
        })
        city_codes = sorted({
            int(t["city_code"])
            for t in tender_list
            if t.get("city_code") is not None
        })
        purpose_codes = sorted({
            int(t["purpose_code"])
            for t in tender_list
            if t.get("purpose_code") is not None
        })

        # Parse publish dates for first_seen/last_seen
        pub_dates: list[str] = []
        for t in tender_list:
            pd_val = t.get("publish_date")
            if pd_val is not None:
                if hasattr(pd_val, "isoformat"):
                    pub_dates.append(pd_val.isoformat()[:10])
                elif isinstance(pd_val, str) and len(pd_val) >= 10:
                    pub_dates.append(pd_val[:10])

        first_seen = min(pub_dates) if pub_dates else None
        last_seen = max(pub_dates) if pub_dates else None

        # Aggregate price metrics
        all_appraisal: list[float] = []
        all_floor: list[float] = []
        all_winning: list[float] = []

        for tid in tender_ids:
            for price_row in price_by_tender.get(int(tid), []):
                ap = price_row.get("appraisal_price")
                if ap is not None and isinstance(ap, (int, float)) and ap > 0:
                    all_appraisal.append(float(ap))
                fp = price_row.get("floor_price")
                if fp is not None and isinstance(fp, (int, float)) and fp > 0:
                    all_floor.append(float(fp))
                wb = price_row.get("winning_bid")
                if wb is not None and isinstance(wb, (int, float)) and wb > 0:
                    all_winning.append(float(wb))

        avg_appraisal = sum(all_appraisal) / len(all_appraisal) if all_appraisal else None
        avg_floor = sum(all_floor) / len(all_floor) if all_floor else None
        avg_winning = sum(all_winning) / len(all_winning) if all_winning else None

        # Primary premium: vs appraisal (שומה רמ"י)
        premium_vs_appraisal: Optional[float] = None
        if avg_appraisal and avg_winning and avg_appraisal > 0:
            premium_vs_appraisal = round(
                (avg_winning - avg_appraisal) / avg_appraisal * 100, 2,
            )

        # Secondary: vs floor (מחיר סף)
        premium_vs_floor: Optional[float] = None
        if avg_floor and avg_winning and avg_floor > 0:
            premium_vs_floor = round(
                (avg_winning - avg_floor) / avg_floor * 100, 2,
            )

        analytics_rows.append({
            "plan_number": plan_number,
            "tender_count": len(tender_list),
            "total_units": total_units,
            "total_land_area": total_land if total_land > 0 else None,
            "avg_appraisal_price": round(avg_appraisal, 2) if avg_appraisal else None,
            "avg_floor_price": round(avg_floor, 2) if avg_floor else None,
            "avg_winning_bid": round(avg_winning, 2) if avg_winning else None,
            "premium_vs_appraisal_pct": premium_vs_appraisal,
            "premium_vs_floor_pct": premium_vs_floor,
            "region_codes": region_codes,
            "city_codes": city_codes,
            "purpose_codes": purpose_codes,
            "first_seen": first_seen,
            "last_seen": last_seen,
            "updated_at": now_iso,
        })

    logger.info("Built analytics for %d plans", len(analytics_rows))
    return analytics_rows


# ============================================================================
# LAND AREA DERIVATION
# ============================================================================

def derive_land_area(db: TenderDB) -> int:
    """Populate land_area_sqm on tenders from detail cache and building rights.

    For each tender missing land_area_sqm, tries to derive it from:
    1. Sum of Shetach values in cached detail Tik[] entries
    2. Sum of plot_size_absolute from building_rights table

    Args:
        db: A TenderDB instance (from db.py).

    Returns:
        Number of tenders updated.
    """
    cache_dir = DATA_DIR / "details_cache"
    if not cache_dir.is_dir():
        logger.warning("No details_cache directory found at %s", cache_dir)
        return 0

    updated = 0

    # Load tenders missing land_area_sqm
    tenders_df = db.load_current_tenders()
    if tenders_df.empty:
        return 0

    missing = tenders_df[
        tenders_df["land_area_sqm"].isna() | (tenders_df["land_area_sqm"] == 0)
    ] if "land_area_sqm" in tenders_df.columns else tenders_df

    logger.info("Found %d tenders missing land_area_sqm", len(missing))

    for _, row in missing.iterrows():
        tender_id = int(row["tender_id"])
        cache_file = cache_dir / f"{tender_id}.json"

        land_area: Optional[float] = None

        # Try from cache file (sum of Shetach across Tik[])
        if cache_file.exists():
            try:
                detail = json.loads(cache_file.read_text(encoding="utf-8"))
                fields = capture_detail_api_fields(detail)
                if fields.get("land_area_sqm"):
                    land_area = fields["land_area_sqm"]
            except (json.JSONDecodeError, OSError):
                pass

        # Fallback: sum from building_rights if plan_number exists
        if land_area is None and row.get("plan_number"):
            rights = db.load_building_rights(row["plan_number"])
            if rights:
                total = sum(
                    float(r.get("plot_size_absolute", 0) or 0)
                    for r in rights
                    if r.get("plot_size_absolute")
                )
                if total > 0:
                    land_area = total

        if land_area is not None:
            success = db.update_tender_fields(
                tender_id, {"land_area_sqm": land_area},
            )
            if success:
                updated += 1

    logger.info("Updated land_area_sqm for %d tenders", updated)
    return updated


# ============================================================================
# FULL ENRICHMENT ORCHESTRATOR
# ============================================================================

def run_full_enrichment(
    cache_dir: Optional[Path] = None,
) -> dict[str, int]:
    """Orchestrate the complete analytics enrichment pipeline.

    Steps:
    1. Extract prices from all cached detail files -> upsert to tender_prices
    2. Extract detail API fields (acquisition_form, fees, land area) -> update tenders
    3. Extract taba plan numbers -> update plan_number on tenders
    4. Derive land_area_sqm for tenders missing it
    5. Build taba analytics -> upsert to taba_analytics

    Args:
        cache_dir: Path to the detail cache directory. Defaults to
            DATA_DIR / "details_cache".

    Returns:
        Dict of operation counts: prices_extracted, detail_fields_updated,
        plan_numbers_set, land_areas_derived, taba_plans_built.
    """
    from db import TenderDB

    db = TenderDB()
    if cache_dir is None:
        cache_dir = DATA_DIR / "details_cache"

    stats: dict[str, int] = {
        "prices_extracted": 0,
        "detail_fields_updated": 0,
        "plan_numbers_set": 0,
        "land_areas_derived": 0,
        "taba_plans_built": 0,
    }

    logger.info("Starting full analytics enrichment from %s", cache_dir)

    # Step 1: Extract and upsert prices
    price_rows = extract_winning_prices_from_cache(cache_dir)
    if price_rows:
        stats["prices_extracted"] = db.upsert_tender_prices(price_rows)

    # Step 2: Extract detail API fields and update tenders
    if cache_dir.is_dir():
        detail_updates = 0
        for filepath in sorted(cache_dir.glob("*.json")):
            try:
                detail = json.loads(filepath.read_text(encoding="utf-8"))
                fields = capture_detail_api_fields(detail)
                if not fields or not fields.get("tender_id"):
                    continue

                tender_id = fields.pop("tender_id")
                # Only update non-None values
                update_data = {k: v for k, v in fields.items() if v is not None}
                if update_data:
                    success = db.update_tender_fields(tender_id, update_data)
                    if success:
                        detail_updates += 1
            except (json.JSONDecodeError, OSError) as exc:
                logger.warning("Failed to process %s: %s", filepath.name, exc)
            except Exception as exc:
                logger.error("Failed to update tender from %s: %s", filepath.name, exc)

        stats["detail_fields_updated"] = detail_updates

    # Step 3: Extract and set plan numbers
    plan_map = extract_taba_plan_numbers_from_cache(cache_dir)
    plan_count = 0
    for tender_id, plans in plan_map.items():
        if plans:
            # Store the first plan number (primary plan)
            success = db.update_plan_number(tender_id, plans[0])
            if success:
                plan_count += 1
    stats["plan_numbers_set"] = plan_count

    # Step 4: Derive land_area_sqm
    stats["land_areas_derived"] = derive_land_area(db)

    # Step 5: Build and upsert taba analytics
    taba_rows = build_taba_analytics(db)
    if taba_rows:
        stats["taba_plans_built"] = db.upsert_taba_analytics(taba_rows)

    logger.info("Enrichment complete: %s", stats)
    return stats


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
    )
    result = run_full_enrichment()
    logger.info("Enrichment results: %s", result)
