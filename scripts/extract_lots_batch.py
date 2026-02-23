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
import sys
import time
from pathlib import Path
from typing import Optional

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


def merge_api_and_pdf_lots(
    api_lots: list[dict],
    pdf_lots: list[dict],
) -> list[dict]:
    """Merge API-extracted lots with PDF-extracted lots.

    For each lot, the API data is the base. PDF-only fields
    (units_target_price, units_free_market, zoning_designation, etc.)
    are overlaid on top. Matching is by lot_number.

    Args:
        api_lots: Lots from extract_lots_from_api() (data_source='api').
        pdf_lots: Lots from BrochureLotExtractor.extract_all().

    Returns:
        List of merged lot dicts with data_source='merged'.
    """
    if not api_lots:
        # No API data — use PDF lots as-is with data_source='pdf'
        for lot in pdf_lots:
            lot["data_source"] = "pdf"
        return pdf_lots

    if not pdf_lots:
        # No PDF data — API lots already have data_source='api'
        return api_lots

    # Index PDF lots by lot_number for O(1) lookup
    pdf_by_lot_num: dict[Optional[int], dict] = {}
    for pdf_lot in pdf_lots:
        lot_num = pdf_lot.get("lot_number")
        if lot_num is not None:
            pdf_by_lot_num[lot_num] = pdf_lot

    merged: list[dict] = []
    for api_lot in api_lots:
        lot_num = api_lot.get("lot_number")
        merged_lot = dict(api_lot)  # Start with API base

        # Find matching PDF lot
        pdf_lot = pdf_by_lot_num.get(lot_num)
        if pdf_lot:
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

            merged_lot["data_source"] = "merged"
        # else: keep data_source='api'

        merged.append(merged_lot)

    # Check for PDF lots not in API (e.g. lot numbers that don't match)
    api_lot_nums = {lot.get("lot_number") for lot in api_lots}
    for pdf_lot in pdf_lots:
        lot_num = pdf_lot.get("lot_number")
        if lot_num is not None and lot_num not in api_lot_nums:
            pdf_lot["data_source"] = "pdf"
            merged.append(pdf_lot)
            logger.info(
                "PDF lot %d has no API match — added as pdf-only",
                lot_num,
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

    # ── Step 7: Persist max_lots_per_bidder ───────────────────────────
    # API MaxToWin is the source of truth; PDF extraction is fallback.
    api_max = details.get("MaxToWin")
    pdf_max = pdf_extraction.get("max_lots_per_bidder") if pdf_extraction else None

    if api_max is not None:
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
