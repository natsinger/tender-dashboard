"""Batch extraction of lot-level data — API-first with PDF overlay.

Uses the API Tik[] array as the primary source of truth for structured lot data
(area, pricing, guarantee, appraisal, development costs, gush/helka, zoning plan,
winner info). Then overlays PDF-only fields (units_target_price, units_free_market,
zoning_designation) from brochure extraction on top.

This eliminates ~80% of PDF dependency: even if brochure download or OCR fails,
the API baseline data is already persisted.

Document selection priority (via find_best_brochure):
    1. Full brochure (חוברת המכרז) — multi-page formal document with Sections 1-3.
    2. MichrazFullDocument — combined publication PDF.
    3. Pirsum rishon (פרסום ראשון) — 1-2 page announcement (inline text fallback).

Eligibility criteria:
    - published_booklet = True
    - lot_extraction_status IS NULL OR IN ('pending', 'failed')

Pipeline per tender (API-first):
    1. Fetch tender details via data_client.get_tender_details_cached()
    2. Extract lots from API Tik[] → upsert immediately (data_source='api')
    3. Find best brochure via brochure_analyzer.find_best_brochure()
    4. Download PDF via data_client.download_document()
    5. Run BrochureLotExtractor().extract_all(pdf_bytes, tender_id)
    6. Merge: overlay PDF-only fields onto API base rows
    7. Upsert merged result (data_source='merged')
    8. Update extraction status + max_lots_per_bidder

Designed to be run by GitHub Actions cron job (after document sync step).

Usage:
    # Process up to 50 tenders (default batch)
    python scripts/extract_lots_batch.py

    # Process a single tender
    python scripts/extract_lots_batch.py --tender-id 20100316

    # Custom batch size
    python scripts/extract_lots_batch.py --limit 20
"""

import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Optional

# Ensure UTF-8 output on Windows (Hebrew RTL display)
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from brochure_analyzer import find_best_brochure
from data_client import LandTendersClient, extract_lots_from_api
from db import TenderDB
from lot_extractor import BrochureLotExtractor

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)

# Default batch size per run
DEFAULT_LIMIT: int = 50

# Rate limiting between API calls (seconds)
API_DELAY: float = 1.0

# Fields that only come from PDF extraction (never in the API).
PDF_ONLY_FIELDS: set[str] = {
    "units_target_price",
    "units_free_market",
    "zoning_designation",
    "discount_amount",
    "sqm_value_current",
}


def get_tenders_needing_extraction(
    db: TenderDB,
    limit: int = DEFAULT_LIMIT,
) -> list[dict]:
    """Query Supabase for tenders that need lot extraction.

    Finds tenders where published_booklet is True and lot_extraction_status
    is NULL, 'pending', or 'failed'.

    Args:
        db: TenderDB instance.
        limit: Maximum number of tenders to return.

    Returns:
        List of tender dicts with tender_id and lot_extraction_status.
    """
    if not db._client:
        logger.error("No Supabase connection — cannot query tenders")
        return []

    try:
        # Fetch tenders with published_booklet=True and no successful extraction.
        # Supabase REST API requires separate queries for NULL vs IN conditions,
        # so we fetch candidates with published_booklet=1 and filter in Python.
        result = (
            db._client.table("tenders")
            .select("tender_id, lot_extraction_status, published_booklet")
            .eq("published_booklet", 1)
            .order("tender_id")
            .limit(limit * 3)  # Over-fetch to account for filtering
            .execute()
        )
        rows = result.data or []

        # Filter to NULL, 'pending', or 'failed' statuses
        eligible = [
            r for r in rows
            if r.get("lot_extraction_status") is None
            or r.get("lot_extraction_status") in ("pending", "failed")
        ]

        # Apply limit
        eligible = eligible[:limit]

        logger.info(
            "Found %d tenders needing lot extraction (from %d with published_booklet)",
            len(eligible),
            len(rows),
        )
        return eligible

    except Exception as exc:
        logger.error("Failed to query tenders for lot extraction: %s", exc)
        return []


def _overlay_pdf_onto_api(
    api_lot: dict,
    pdf_lot: dict,
) -> dict:
    """Overlay PDF-only fields onto an API lot base.

    Creates a new merged lot dict starting from the API lot. PDF-only
    fields are copied unconditionally; shared fields use the API value
    when non-null, falling back to PDF.

    Args:
        api_lot: Lot dict from extract_lots_from_api().
        pdf_lot: Lot dict from BrochureLotExtractor.

    Returns:
        New merged lot dict with data_source='merged'.
    """
    merged_lot = dict(api_lot)

    # PDF lot_number (sequential from brochure) becomes the canonical lot_number.
    # API's mitcham_name and gush_helka_raw are always preserved.
    pdf_lot_number = pdf_lot.get("lot_number")
    if pdf_lot_number is not None:
        merged_lot["lot_number"] = pdf_lot_number

    # Overlay PDF-only fields
    for field in PDF_ONLY_FIELDS:
        pdf_val = pdf_lot.get(field)
        if pdf_val is not None:
            merged_lot[field] = pdf_val

    # For shared fields, prefer API if non-null; otherwise use PDF
    for field in ("zoning_plan", "plot_numbers", "area_sqm"):
        if merged_lot.get(field) is None:
            pdf_val = pdf_lot.get(field)
            if pdf_val is not None:
                merged_lot[field] = pdf_val

    # Always preserve API's mitcham_name and gush_helka_raw on the merged record
    # (they come from the api_lot base via dict(api_lot) above, but ensure they
    # are not overwritten by PDF values which wouldn't have them).

    merged_lot["data_source"] = "merged"
    return merged_lot


def _enrich_pdf_with_api_aggregate(
    pdf_lot: dict,
    api_lot: dict,
) -> dict:
    """Enrich a PDF lot with aggregate fields from the API lot.

    Used when a single API lot represents an aggregate of multiple PDF
    lots (e.g., 1 API lot with total_units=2868 vs 23 PDF lots with
    detailed breakdowns). Copies API-only fields that are missing from
    the PDF lot without overwriting PDF-specific detail.

    Args:
        pdf_lot: Detailed PDF lot dict (the base).
        api_lot: Aggregate API lot dict (source of supplementary data).

    Returns:
        New enriched lot dict with data_source='merged'.
    """
    enriched = dict(pdf_lot)

    # Copy API fields that PDF doesn't have (except PDF_ONLY_FIELDS which
    # should stay as extracted from PDF, and lot_number which stays from PDF).
    api_only_candidates = (
        "gush", "helka", "zoning_plan", "plot_numbers",
        "winner_name", "winning_amount",
    )
    for field in api_only_candidates:
        if enriched.get(field) is None:
            api_val = api_lot.get(field)
            if api_val is not None:
                enriched[field] = api_val

    # Preserve API's gush_helka_raw on the merged record.
    # NOTE: mitcham_name is intentionally NOT copied here because in a
    # 1-to-many aggregate scenario (1 API lot → N PDF lots), broadcasting
    # the same mitcham_name to all rows violates the unique constraint
    # uq_tender_lots_api(tender_id, COALESCE(mitcham_name, '')).
    api_gush_raw = api_lot.get("gush_helka_raw")
    if api_gush_raw is not None:
        enriched["gush_helka_raw"] = api_gush_raw

    enriched["data_source"] = "merged"
    return enriched


def merge_api_and_pdf_lots(
    api_lots: list[dict],
    pdf_lots: list[dict],
) -> list[dict]:
    """Merge API-extracted lots with PDF-extracted lots.

    Uses a multi-level fallback strategy because API and PDF lot numbers
    often use different numbering schemes:
      - API lot_number comes from MitchamName (internal compound IDs like
        1121, 1124, or None).
      - PDF lot_number comes from brochure tables (sequential 1, 2, 3 or
        parcel numbers like 78343+).

    Merge strategies (tried in order):
      1. Exact lot_number match -- works when numbering is consistent.
      2. Positional match -- when both sides have the same count but
         different numbering, align by position (1st<->1st, 2nd<->2nd).
      3. Count mismatch with API fewer (e.g., 1 API lot, 23 PDF lots):
         PDF lots are the granular view; keep them as base and enrich
         with API aggregate fields.
      4. Count mismatch with API more (e.g., 8 API, 7 PDF): positional
         match for the first N lots, keep remaining API lots as-is.

    Args:
        api_lots: Lots from extract_lots_from_api() (data_source='api').
        pdf_lots: Lots from BrochureLotExtractor.extract_all().

    Returns:
        List of merged lot dicts with data_source='merged' where
        matching succeeded, 'api' or 'pdf' otherwise.
    """
    if not api_lots:
        # No API data — use PDF lots as-is with data_source='pdf'
        for lot in pdf_lots:
            lot["data_source"] = "pdf"
        logger.info("Merge strategy: pdf-only (no API lots)")
        return pdf_lots

    if not pdf_lots:
        # No PDF data — API lots already have data_source='api'
        logger.info("Merge strategy: api-only (no PDF lots)")
        return api_lots

    # ── Strategy 1: Exact lot_number match ─────────────────────────────
    pdf_by_lot_num: dict[Optional[int], dict] = {}
    for pdf_lot in pdf_lots:
        lot_num = pdf_lot.get("lot_number")
        if lot_num is not None:
            pdf_by_lot_num[lot_num] = pdf_lot

    exact_match_count = sum(
        1 for api_lot in api_lots
        if api_lot.get("lot_number") is not None
        and api_lot.get("lot_number") in pdf_by_lot_num
    )

    if exact_match_count > 0:
        # At least some exact matches -- use existing logic
        merged: list[dict] = []
        for api_lot in api_lots:
            lot_num = api_lot.get("lot_number")
            pdf_lot = pdf_by_lot_num.get(lot_num)
            if pdf_lot:
                merged.append(_overlay_pdf_onto_api(api_lot, pdf_lot))
            else:
                merged.append(dict(api_lot))

        # Add PDF lots with no API match
        api_lot_nums = {lot.get("lot_number") for lot in api_lots}
        for pdf_lot in pdf_lots:
            lot_num = pdf_lot.get("lot_number")
            if lot_num is not None and lot_num not in api_lot_nums:
                pdf_copy = dict(pdf_lot)
                pdf_copy["data_source"] = "pdf"
                merged.append(pdf_copy)

        logger.info(
            "Merge strategy: exact lot_number match "
            "(%d/%d API lots matched)",
            exact_match_count, len(api_lots),
        )
        return merged

    # ── No exact matches — fall through to positional strategies ───────
    n_api = len(api_lots)
    n_pdf = len(pdf_lots)

    # ── Strategy 2: Positional match (same count) ─────────────────────
    if n_api == n_pdf:
        merged = []
        for api_lot, pdf_lot in zip(api_lots, pdf_lots):
            merged.append(_overlay_pdf_onto_api(api_lot, pdf_lot))
        logger.info(
            "Merge strategy: positional match (both sides have %d lots, "
            "lot_number schemes differ)",
            n_api,
        )
        return merged

    # ── Strategy 3: API has fewer lots than PDF ───────────────────────
    # PDF lots are the detailed/granular view. Use PDF as base, enrich
    # with API aggregate fields.
    if n_api < n_pdf:
        merged = []
        for pdf_lot in pdf_lots:
            # Enrich each PDF lot with the first (or only) API lot's
            # aggregate data. When there's 1 API lot this broadcasts it;
            # when there are K API lots we round-robin or just use the
            # first one (aggregate fields like winner_name / gush are
            # typically the same across API lots in this scenario).
            api_lot = api_lots[0]
            merged.append(_enrich_pdf_with_api_aggregate(pdf_lot, api_lot))

        logger.info(
            "Merge strategy: pdf-granular enriched with api-aggregate "
            "(%d API lots → %d PDF lots)",
            n_api, n_pdf,
        )
        return merged

    # ── Strategy 4: API has more lots than PDF ────────────────────────
    # Positional match for the first N PDF lots, keep remaining API lots
    # as-is.
    merged = []
    for i, api_lot in enumerate(api_lots):
        if i < n_pdf:
            merged.append(_overlay_pdf_onto_api(api_lot, pdf_lots[i]))
        else:
            merged.append(dict(api_lot))
    logger.info(
        "Merge strategy: partial positional match "
        "(%d API lots, %d PDF lots — first %d matched by position)",
        n_api, n_pdf, n_pdf,
    )
    return merged


def get_backfill_tender_ids(cache_dir: Path) -> list[int]:
    """Get tender IDs from all cached detail JSON files.

    Used by --backfill to process all tenders with cached API details
    without querying Supabase.

    Args:
        cache_dir: Path to the details_cache directory.

    Returns:
        Sorted list of tender IDs.
    """
    ids: list[int] = []
    for fpath in cache_dir.glob("*.json"):
        try:
            ids.append(int(fpath.stem))
        except ValueError:
            continue
    ids.sort()
    logger.info("Found %d cached tender detail files for backfill", len(ids))
    return ids


def process_tender(
    tender_id: int,
    db: TenderDB,
    client: LandTendersClient,
    extractor: BrochureLotExtractor,
    api_only: bool = False,
) -> dict:
    """Run the API-first lot extraction pipeline for a single tender.

    Flow:
        1. Fetch tender details
        2. Extract lots from API Tik[] → upsert immediately
        3. (skip if api_only) Find best brochure → download PDF
        4. (skip if api_only) Extract PDF lots (for PDF-only fields)
        5. Merge API + PDF lots → upsert merged result
        6. Update extraction status + max_lots_per_bidder

    Args:
        tender_id: The tender's MichrazID.
        db: TenderDB instance for persistence.
        client: API client for fetching details and downloading PDFs.
        extractor: BrochureLotExtractor instance.
        api_only: If True, skip PDF download/extraction (fast backfill mode).

    Returns:
        Result dict with keys: tender_id, status, lots_count,
        api_lots_count, pdf_lots_count, max_lots_per_bidder,
        doc_type, doc_size, error.
    """
    result: dict = {
        "tender_id": tender_id,
        "status": "pending",
        "lots_count": 0,
        "api_lots_count": 0,
        "pdf_lots_count": 0,
        "max_lots_per_bidder": None,
        "doc_type": "",
        "doc_size": 0,
        "error": None,
    }

    # ── Step 1: Fetch tender details ──────────────────────────────────
    logger.info("Tender %d: fetching details...", tender_id)
    details = client.get_tender_details_cached(tender_id)
    if not details:
        result["status"] = "failed"
        result["error"] = "Could not fetch tender details"
        db.update_lot_extraction_status(tender_id, "failed")
        return result

    time.sleep(API_DELAY)

    # ── Step 2: Extract lots from API Tik[] ───────────────────────────
    api_lots = extract_lots_from_api(details)
    result["api_lots_count"] = len(api_lots)

    if api_lots:
        upserted = db.upsert_lots(tender_id, api_lots)
        logger.info(
            "Tender %d: upserted %d API lots", tender_id, upserted,
        )

    # ── Step 3: Find the best available brochure document ─────────────
    pdf_lots: list[dict] = []
    pdf_extraction: Optional[dict] = None

    if api_only:
        doc = None
        doc_type = ""
        logger.debug("Tender %d: api_only mode — skipping PDF", tender_id)
    else:
        doc, doc_type = find_best_brochure(details)

    result["doc_type"] = doc_type

    if doc:
        logger.info(
            "Tender %d: selected %s document (Teur=%r, RowID=%s)",
            tender_id,
            doc_type,
            doc.get("Teur"),
            doc.get("RowID"),
        )

        # ── Step 4: Download the PDF ─────────────────────────────────
        logger.info(
            "Tender %d: downloading brochure (RowID=%s)...",
            tender_id,
            doc.get("RowID"),
        )
        pdf_bytes = client.download_document(doc)

        if pdf_bytes:
            result["doc_size"] = len(pdf_bytes)
            logger.info(
                "Tender %d: downloaded %d bytes (%s)",
                tender_id,
                len(pdf_bytes),
                doc_type,
            )
            time.sleep(API_DELAY)

            # ── Step 5: Run the PDF lot extractor ─────────────────────
            pdf_extraction = extractor.extract_all(pdf_bytes, tender_id)
            pdf_lots = pdf_extraction.get("lots", [])
            result["pdf_lots_count"] = len(pdf_lots)
        else:
            logger.warning(
                "Tender %d: failed to download brochure PDF", tender_id,
            )
    else:
        logger.info("Tender %d: no brochure document found", tender_id)

    # ── Step 6: Merge API + PDF lots and upsert ───────────────────────
    merged_lots = merge_api_and_pdf_lots(api_lots, pdf_lots)

    if merged_lots:
        upserted = db.upsert_lots(tender_id, merged_lots)
        result["lots_count"] = upserted
        logger.info("Tender %d: upserted %d merged lots", tender_id, upserted)
        # Persist lot_count on the tenders table for dashboard display
        db.update_tender_fields(tender_id, {"lot_count": len(merged_lots)})

    # ── Step 7: Persist max_lots_per_bidder ───────────────────────────
    # API MaxToWin is the source of truth; PDF extraction is fallback.
    api_max = details.get("MaxToWin")
    pdf_max = pdf_extraction.get("max_lots_per_bidder") if pdf_extraction else None

    if api_max is not None:
        db.update_max_lots_per_bidder(tender_id, int(api_max))
        result["max_lots_per_bidder"] = api_max
        logger.info("Tender %d: using API MaxToWin=%d", tender_id, api_max)
    elif pdf_max is not None:
        db.update_max_lots_per_bidder(tender_id, pdf_max)
        result["max_lots_per_bidder"] = pdf_max

    # ── Step 8: Update extraction status ──────────────────────────────
    has_lots = len(merged_lots) > 0
    pdf_success = pdf_extraction.get("success", False) if pdf_extraction else False

    if has_lots:
        result["status"] = "extracted"
        db.update_lot_extraction_status(tender_id, "extracted")
    elif not doc:
        result["status"] = "no_brochure"
        if api_lots:
            # We have API data but no brochure — still mark extracted
            result["status"] = "extracted"
            db.update_lot_extraction_status(tender_id, "extracted")
        else:
            result["error"] = "No brochure document found and no API lot data"
            db.update_lot_extraction_status(tender_id, "no_brochure")
    else:
        errors = pdf_extraction.get("errors", []) if pdf_extraction else []
        result["status"] = "failed"
        result["error"] = "; ".join(errors) if errors else "No lots found"
        db.update_lot_extraction_status(tender_id, "failed")

    return result


def main() -> None:
    """Main entry point for batch lot extraction."""
    parser = argparse.ArgumentParser(
        description="Extract lot data from tender brochure PDFs",
    )
    parser.add_argument(
        "--tender-id",
        type=int,
        help="Process a single tender by ID",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_LIMIT,
        help=f"Maximum tenders to process per run (default: {DEFAULT_LIMIT})",
    )
    parser.add_argument(
        "--backfill",
        action="store_true",
        help="Process ALL cached tender details (API-only, no PDF downloads)",
    )
    parser.add_argument(
        "--api-only",
        action="store_true",
        help="Skip PDF download/extraction — only extract from API Tik[]",
    )
    args = parser.parse_args()

    db = TenderDB()
    client = LandTendersClient()
    extractor = BrochureLotExtractor()

    # --backfill implies --api-only
    api_only = args.api_only or args.backfill

    # Determine which tenders to process
    if args.tender_id:
        tender_ids = [args.tender_id]
        logger.info("Processing single tender: %d", args.tender_id)
    elif args.backfill:
        cache_dir = Path(__file__).resolve().parent.parent / "data" / "details_cache"
        tender_ids = get_backfill_tender_ids(cache_dir)
    else:
        tenders = get_tenders_needing_extraction(db, limit=args.limit)
        tender_ids = [t["tender_id"] for t in tenders]

    if not tender_ids:
        logger.info("No tenders to process")
        return

    logger.info(
        "Starting lot extraction for %d tenders (api_only=%s)...",
        len(tender_ids),
        api_only,
    )

    # Process each tender
    results: list[dict] = []
    for tender_id in tender_ids:
        try:
            res = process_tender(
                tender_id, db, client, extractor, api_only=api_only,
            )
            results.append(res)
            logger.info(
                "Tender %d: status=%s, lots=%d (api=%d, pdf=%d)",
                tender_id,
                res["status"],
                res["lots_count"],
                res["api_lots_count"],
                res["pdf_lots_count"],
            )
        except Exception as exc:
            logger.error("Tender %d: unexpected error: %s", tender_id, exc, exc_info=True)
            results.append({
                "tender_id": tender_id,
                "status": "error",
                "lots_count": 0,
                "api_lots_count": 0,
                "pdf_lots_count": 0,
                "max_lots_per_bidder": None,
                "error": str(exc),
            })
            # Update status even on unexpected errors
            try:
                db.update_lot_extraction_status(tender_id, "failed")
            except Exception:
                pass

    # Summary
    total = len(results)
    total_lots = sum(r["lots_count"] for r in results)
    total_api = sum(r.get("api_lots_count", 0) for r in results)
    total_pdf = sum(r.get("pdf_lots_count", 0) for r in results)
    failures = sum(1 for r in results if r["status"] in ("failed", "error"))
    successes = sum(1 for r in results if r["status"] == "extracted")
    no_brochure = sum(1 for r in results if r["status"] == "no_brochure")

    # Document type breakdown
    doc_type_counts: dict[str, int] = {}
    for r in results:
        dt = r.get("doc_type", "") or "none"
        doc_type_counts[dt] = doc_type_counts.get(dt, 0) + 1

    logger.info(
        "Batch complete: Processed %d tenders, extracted %d lots "
        "(api=%d, pdf=%d), %d failures",
        total,
        total_lots,
        total_api,
        total_pdf,
        failures,
    )
    logger.info(
        "  Breakdown — extracted: %d, no_brochure: %d, failed/error: %d",
        successes,
        no_brochure,
        failures,
    )
    logger.info(
        "  Doc types — %s",
        ", ".join(f"{k}: {v}" for k, v in sorted(doc_type_counts.items())),
    )

    # Write results to tmp/ for debugging
    output_path = Path(__file__).resolve().parent.parent / "tmp" / "batch_lot_extraction_results.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    logger.info("Results written to %s", output_path)


if __name__ == "__main__":
    main()
