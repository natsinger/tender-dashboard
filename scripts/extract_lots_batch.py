"""Batch extraction of lot-level data from tender brochure PDFs.

Downloads the best available brochure PDF for each eligible tender (prioritizing
the full חוברת over פרסום ראשון), runs the BrochureLotExtractor to parse lot
tables, zoning info, and bid limits, then persists the results to Supabase.

Document selection priority (via find_best_brochure):
    1. Full brochure (חוברת המכרז) — multi-page formal document with Sections 1-3.
    2. MichrazFullDocument — combined publication PDF.
    3. Pirsum rishon (פרסום ראשון) — 1-2 page announcement (inline text fallback).

Eligibility criteria:
    - published_booklet = True
    - lot_extraction_status IS NULL OR IN ('pending', 'failed')

Pipeline per tender:
    1. Fetch tender details via data_client.get_tender_details_cached()
    2. Find best brochure via brochure_analyzer.find_best_brochure()
    3. Download PDF via data_client.download_document()
    4. Run BrochureLotExtractor().extract_all(pdf_bytes, tender_id)
    5. If lots found: db.upsert_lots(tender_id, lots)
    6. If max_lots_per_bidder found: db.update_max_lots_per_bidder(...)
    7. Update db.update_lot_extraction_status(tender_id, status)

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
from data_client import LandTendersClient
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


def process_tender(
    tender_id: int,
    db: TenderDB,
    client: LandTendersClient,
    extractor: BrochureLotExtractor,
) -> dict:
    """Run the lot extraction pipeline for a single tender.

    Uses find_best_brochure() to select the best available document:
    full brochure (חוברת) > MichrazFullDocument > pirsum rishon.

    Args:
        tender_id: The tender's MichrazID.
        db: TenderDB instance for persistence.
        client: API client for fetching details and downloading PDFs.
        extractor: BrochureLotExtractor instance.

    Returns:
        Result dict with keys: tender_id, status, lots_count,
        max_lots_per_bidder, doc_type, doc_size, error.
    """
    result: dict = {
        "tender_id": tender_id,
        "status": "pending",
        "lots_count": 0,
        "max_lots_per_bidder": None,
        "doc_type": "",
        "doc_size": 0,
        "error": None,
    }

    # Step 1: Fetch tender details
    logger.info("Tender %d: fetching details...", tender_id)
    details = client.get_tender_details_cached(tender_id)
    if not details:
        result["status"] = "failed"
        result["error"] = "Could not fetch tender details"
        db.update_lot_extraction_status(tender_id, "failed")
        return result

    time.sleep(API_DELAY)

    # Step 2: Find the best available brochure document
    doc, doc_type = find_best_brochure(details)
    result["doc_type"] = doc_type
    if not doc:
        result["status"] = "no_brochure"
        result["error"] = "No brochure document found"
        db.update_lot_extraction_status(tender_id, "no_brochure")
        return result

    logger.info(
        "Tender %d: selected %s document (Teur=%r, RowID=%s)",
        tender_id,
        doc_type,
        doc.get("Teur"),
        doc.get("RowID"),
    )

    # Step 3: Download the PDF
    logger.info("Tender %d: downloading brochure (RowID=%s)...", tender_id, doc.get("RowID"))
    pdf_bytes = client.download_document(doc)
    if not pdf_bytes:
        result["status"] = "failed"
        result["error"] = "Failed to download brochure PDF"
        db.update_lot_extraction_status(tender_id, "failed")
        return result

    result["doc_size"] = len(pdf_bytes)
    logger.info(
        "Tender %d: downloaded %d bytes (%s)",
        tender_id,
        len(pdf_bytes),
        doc_type,
    )
    time.sleep(API_DELAY)

    # Step 4: Run the lot extractor
    extraction = extractor.extract_all(pdf_bytes, tender_id)
    lots = extraction.get("lots", [])
    max_lots = extraction.get("max_lots_per_bidder")

    # Step 5: Persist lots if found
    if lots:
        upserted = db.upsert_lots(tender_id, lots)
        result["lots_count"] = upserted
        logger.info("Tender %d: upserted %d lots", tender_id, upserted)

    # Step 6: Persist max_lots_per_bidder — only if API didn't already
    # provide it (MaxToWin in the daily refresh is the source of truth).
    api_max = details.get("MaxToWin")
    if api_max is not None:
        result["max_lots_per_bidder"] = api_max
        logger.info("Tender %d: using API MaxToWin=%d", tender_id, api_max)
    elif max_lots is not None:
        db.update_max_lots_per_bidder(tender_id, max_lots)
        result["max_lots_per_bidder"] = max_lots

    # Step 7: Update extraction status
    if extraction.get("success"):
        result["status"] = "extracted"
        db.update_lot_extraction_status(tender_id, "extracted")
    else:
        errors = extraction.get("errors", [])
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
    args = parser.parse_args()

    db = TenderDB()
    client = LandTendersClient()
    extractor = BrochureLotExtractor()

    # Determine which tenders to process
    if args.tender_id:
        tender_ids = [args.tender_id]
        logger.info("Processing single tender: %d", args.tender_id)
    else:
        tenders = get_tenders_needing_extraction(db, limit=args.limit)
        tender_ids = [t["tender_id"] for t in tenders]

    if not tender_ids:
        logger.info("No tenders to process")
        return

    logger.info("Starting lot extraction for %d tenders...", len(tender_ids))

    # Process each tender
    results: list[dict] = []
    for tender_id in tender_ids:
        try:
            res = process_tender(tender_id, db, client, extractor)
            results.append(res)
            logger.info(
                "Tender %d: status=%s, lots=%d",
                tender_id,
                res["status"],
                res["lots_count"],
            )
        except Exception as exc:
            logger.error("Tender %d: unexpected error: %s", tender_id, exc, exc_info=True)
            results.append({
                "tender_id": tender_id,
                "status": "error",
                "lots_count": 0,
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
    failures = sum(1 for r in results if r["status"] in ("failed", "error"))
    successes = sum(1 for r in results if r["status"] == "extracted")
    no_brochure = sum(1 for r in results if r["status"] == "no_brochure")

    # Document type breakdown
    doc_type_counts: dict[str, int] = {}
    for r in results:
        dt = r.get("doc_type", "") or "none"
        doc_type_counts[dt] = doc_type_counts.get(dt, 0) + 1

    logger.info(
        "Batch complete: Processed %d tenders, extracted %d lots, %d failures",
        total,
        total_lots,
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
