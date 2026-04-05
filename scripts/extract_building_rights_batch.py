"""Batch extraction of building rights from Taba plan PDFs.

Full pipeline for active tenders with a published brochure:
    1. Query Supabase for eligible tenders (published_booklet=1, active status,
       extraction not yet complete)
    2. For each tender (that doesn't already have building rights):
        a. Look up plan ID from the RMI tender details API
        b. Query TabaSearch API for the plan's takanon (תקנון) PDF path
        c. Download the takanon PDF directly (no Playwright needed)
        d. Extract Section 5 building rights table
        e. Store results in Supabase

Requires:
    - pdfplumber (text extraction)
    - requests (HTTP API calls — replaces Playwright browser automation)
    - Supabase credentials (env vars)

Usage:
    # Process all eligible tenders (default)
    python scripts/extract_building_rights_batch.py

    # Process only watchlisted tenders (legacy behavior)
    python scripts/extract_building_rights_batch.py --watchlist-only

    # Process specific tender IDs
    python scripts/extract_building_rights_batch.py --tender-ids 12345 67890

    # Process specific plan numbers directly (skip brochure step)
    python scripts/extract_building_rights_batch.py --plan-numbers 102-0909267 606-0458471

    # Dry run (no Supabase writes)
    python scripts/extract_building_rights_batch.py --dry-run
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

from building_rights_extractor import extract_building_rights
from data_client import LandTendersClient
from db import TenderDB
from taba_client import TabaClient
from tender_pdf_extractor import TenderPDFExtractor

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)

# Directory for cached downloads
BROCHURE_DIR = Path(__file__).resolve().parent.parent / "tmp" / "brochures"
MAVAT_DIR = Path(__file__).resolve().parent.parent / "tmp" / "mavat_plans"

# Rate limiting between Mavat requests (seconds)
MAVAT_DELAY = 5

# Maximum tenders to process per run (to avoid CI timeout)
MAX_PER_RUN = 20


def _download_brochure(
    client: LandTendersClient,
    tender_id: int,
) -> Optional[Path]:
    """Download the main brochure PDF for a tender.

    Args:
        client: API client instance.
        tender_id: The tender's MichrazID.

    Returns:
        Path to the downloaded PDF, or None if unavailable.
    """
    BROCHURE_DIR.mkdir(parents=True, exist_ok=True)
    cached = BROCHURE_DIR / f"{tender_id}.pdf"
    if cached.exists() and cached.stat().st_size > 0:
        logger.info("Using cached brochure: %s", cached.name)
        return cached

    details = client.get_tender_details_cached(tender_id)
    if not details:
        logger.warning("No details found for tender %d", tender_id)
        return None

    # Try the full brochure document first
    full_doc = details.get("MichrazFullDocument")
    if full_doc and full_doc.get("RowID") is not None:
        content = client.download_document(full_doc)
        if content:
            cached.write_bytes(content)
            logger.info("Downloaded brochure for tender %d (%d bytes)", tender_id, len(content))
            return cached

    # Fallback: look for a brochure in the document list
    for doc in details.get("MichrazDocList", []):
        doc_name = (doc.get("DocName") or "").lower()
        if "חוברת" in doc_name or "hoveret" in doc_name or "brochure" in doc_name:
            content = client.download_document(doc)
            if content:
                cached.write_bytes(content)
                logger.info("Downloaded brochure (from doc list) for tender %d", tender_id)
                return cached

    logger.warning("No brochure found for tender %d", tender_id)
    return None


def _extract_plan_number(pdf_path: Path) -> Optional[str]:
    """Extract the plan number from a tender brochure PDF.

    Args:
        pdf_path: Path to the brochure PDF.

    Returns:
        The plan number string, or None if not found.
    """
    extractor = TenderPDFExtractor()
    result = extractor.extract(pdf_path)
    return result.get("taba")


def _download_takanon(
    taba_client: TabaClient,
    plan_id: str,
    plan_number: Optional[str] = None,
) -> Optional[Path]:
    """Download the takanon (תקנון) PDF via the TabaSearch API.

    Args:
        taba_client: TabaClient instance.
        plan_id: The plan ID from the MichrazLinks URL.
        plan_number: Optional Taba plan number for naming the file.

    Returns:
        Path to the downloaded PDF, or None if failed.
    """
    result = taba_client.download_takanon_by_plan_id(
        plan_id, plan_number=plan_number,
    )
    if result["status"] == "success":
        return Path(result["file_path"])

    logger.warning(
        "Takanon download failed for plan %s (id=%s): %s",
        plan_number or "?", plan_id, result.get("error") or result["status"],
    )
    return None


def _download_mavat_plan(plan_number: str) -> Optional[Path]:
    """Legacy fallback: download via Playwright if TabaClient fails.

    Only used for --plan-numbers mode where we have a Taba plan number
    but no plan_id. Falls back to Playwright-based Mavat client.

    Args:
        plan_number: The תב"ע plan number.

    Returns:
        Path to the downloaded PDF, or None if failed.
    """
    MAVAT_DIR.mkdir(parents=True, exist_ok=True)

    safe_name = plan_number.replace("/", "_").replace("\\", "_")
    cached = MAVAT_DIR / f"{safe_name}.pdf"
    if cached.exists() and cached.stat().st_size > 0:
        logger.info("Using cached Mavat plan: %s", cached.name)
        return cached

    try:
        from mavat_client import MavatClient
        client = MavatClient(output_dir=MAVAT_DIR)
        result = client.download_horaot(plan_number)

        if result["status"] == "success":
            return Path(result["file_path"])

        logger.warning(
            "Mavat download failed for %s: %s",
            plan_number, result.get("error") or result["status"],
        )
        return None

    except Exception as exc:
        logger.error("Mavat download error for %s: %s", plan_number, exc)
        return None


def process_tender(
    tender_id: int,
    db: TenderDB,
    taba_client: TabaClient,
    client: Optional[LandTendersClient] = None,
    dry_run: bool = False,
) -> dict:
    """Run the full pipeline for a single tender.

    Uses the TabaClient (REST API) to look up the plan and download
    the takanon PDF directly — no Playwright browser automation needed.

    Falls back to the brochure→Mavat Playwright flow only if the
    TabaClient path fails (e.g., no MichrazLinks URL).

    Args:
        tender_id: The tender's MichrazID.
        db: Database instance.
        taba_client: TabaClient instance for API-based plan lookup.
        client: Optional LandTendersClient for brochure fallback.
        dry_run: If True, don't write to Supabase.

    Returns:
        Result dict with status and details.
    """
    result = {
        "tender_id": tender_id,
        "status": "pending",
        "plan_number": None,
        "building_rights_rows": 0,
        "error": None,
    }

    # Mark as extracting
    if not dry_run:
        db.set_extraction_status(tender_id, "extracting")

    # Step 1: Use TabaClient to get plan info from the RMI API
    plans = taba_client.get_tender_plan_ids(tender_id)

    plan_id = None
    plan_number = None
    if plans:
        plan_id = plans[0].get("plan_id")
        plan_number = plans[0].get("plan_number")

    # Fallback: check if tender already has a plan_number in DB
    if not plan_number:
        tender = db.get_tender_by_id(tender_id)
        if tender:
            plan_number = tender.get("plan_number")

    if not plan_id and not plan_number:
        # Last resort: try brochure extraction
        if client:
            logger.info("Tender %d: no plan from API, trying brochure...", tender_id)
            brochure_path = _download_brochure(client, tender_id)
            if brochure_path:
                plan_number = _extract_plan_number(brochure_path)

        if not plan_number:
            result["status"] = "no_plan"
            result["error"] = "No plan linked to tender (no API link, no brochure)"
            if not dry_run:
                db.set_extraction_status(tender_id, "failed", error=result["error"])
            return result

    result["plan_number"] = plan_number

    # Persist the plan number (use Taba plan number, not planId)
    if plan_number and not dry_run:
        db.update_plan_number(tender_id, plan_number)

    # Step 2: Check if building rights already exist
    if plan_number:
        existing = db.load_building_rights(plan_number)
        if existing:
            logger.info(
                "Tender %d: building rights already exist (%d rows) for plan %s",
                tender_id, len(existing), plan_number,
            )
            result["status"] = "already_extracted"
            result["building_rights_rows"] = len(existing)
            if not dry_run:
                db.set_extraction_status(tender_id, "complete")
            return result

    # Step 3: Download takanon PDF via TabaSearch API
    takanon_pdf = None
    if plan_id:
        logger.info(
            "Tender %d: downloading takanon via API (plan_id=%s)...",
            tender_id, plan_id,
        )
        takanon_pdf = _download_takanon(taba_client, plan_id, plan_number)

    # Fallback to Playwright-based Mavat if API download failed
    if not takanon_pdf and plan_number:
        logger.info(
            "Tender %d: API download failed, trying Mavat fallback for %s...",
            tender_id, plan_number,
        )
        takanon_pdf = _download_mavat_plan(plan_number)

    if not takanon_pdf:
        result["status"] = "download_failed"
        result["error"] = f"Could not download takanon for plan {plan_number or plan_id}"
        if not dry_run:
            db.set_extraction_status(tender_id, "failed", error=result["error"])
        return result

    # Step 4: Extract building rights
    logger.info(
        "Tender %d: extracting building rights from %s...",
        tender_id, takanon_pdf.name,
    )
    rights = extract_building_rights(takanon_pdf, plan_number=plan_number)

    if not rights["success"]:
        result["status"] = "extraction_failed"
        result["error"] = "; ".join(rights.get("errors", []))
        if not dry_run:
            db.set_extraction_status(tender_id, "failed", error=result["error"])
        return result

    # Step 5: Store in Supabase
    rows = rights["rows"]
    if not dry_run:
        clean_rows = [{k: v for k, v in r.items() if k != "_raw"} for r in rows]
        db.upsert_building_rights(plan_number, clean_rows, rights.get("status"))
        db.set_extraction_status(tender_id, "complete")

    result["status"] = "success"
    result["building_rights_rows"] = len(rows)
    logger.info(
        "Tender %d: extracted %d building rights rows for plan %s",
        tender_id, len(rows), plan_number,
    )
    return result


def process_plan_directly(
    plan_number: str,
    db: TenderDB,
    dry_run: bool = False,
) -> dict:
    """Process a plan number directly (skip brochure extraction).

    Args:
        plan_number: The תב"ע plan number.
        db: Database instance.
        dry_run: If True, don't write to Supabase.

    Returns:
        Result dict.
    """
    result = {
        "plan_number": plan_number,
        "status": "pending",
        "building_rights_rows": 0,
        "error": None,
    }

    # Check if already extracted
    existing = db.load_building_rights(plan_number)
    if existing:
        logger.info("Plan %s: already has %d rows", plan_number, len(existing))
        result["status"] = "already_extracted"
        result["building_rights_rows"] = len(existing)
        return result

    # Download from Mavat
    mavat_pdf = _download_mavat_plan(plan_number)
    if not mavat_pdf:
        result["status"] = "mavat_download_failed"
        return result

    # Extract
    rights = extract_building_rights(mavat_pdf, plan_number=plan_number)
    if not rights["success"]:
        result["status"] = "extraction_failed"
        result["error"] = "; ".join(rights.get("errors", []))
        return result

    rows = rights["rows"]
    if not dry_run:
        clean_rows = [{k: v for k, v in r.items() if k != "_raw"} for r in rows]
        db.upsert_building_rights(plan_number, clean_rows, rights.get("status"))

    result["status"] = "success"
    result["building_rights_rows"] = len(rows)
    return result


def get_tenders_needing_building_rights(
    db: TenderDB,
    limit: int = MAX_PER_RUN,
) -> list[dict]:
    """Query Supabase for tenders that need building rights extraction.

    Finds tenders where published_booklet is True and extraction_status
    is NULL, 'pending', 'failed', or 'none'. Filters to active statuses
    (status_code IN 1, 2, 3) in Python.

    Args:
        db: TenderDB instance.
        limit: Maximum number of tenders to return.

    Returns:
        List of tender dicts with tender_id and extraction_status.
    """
    if not db._client:
        logger.error("No Supabase connection — cannot query tenders")
        return []

    try:
        # Fetch tenders with published_booklet=1 and filter in Python.
        # Supabase REST API requires separate queries for NULL vs IN
        # conditions, so we over-fetch and filter locally.
        result = (
            db._client.table("tenders")
            .select("tender_id, extraction_status, published_booklet, status_code")
            .eq("published_booklet", 1)
            .order("tender_id", desc=True)
            .limit(limit * 3)  # Over-fetch to account for filtering
            .execute()
        )
        rows = result.data or []

        # Filter to active statuses (1=published, 2=extended, 3=approaching deadline)
        active_status_codes = {1, 2, 3}
        eligible = [
            r for r in rows
            if r.get("status_code") in active_status_codes
            and (
                r.get("extraction_status") is None
                or r.get("extraction_status") in ("pending", "failed", "none")
            )
        ]

        # Apply limit
        eligible = eligible[:limit]

        logger.info(
            "Found %d tenders needing building rights extraction "
            "(from %d with published_booklet, active status)",
            len(eligible),
            len(rows),
        )
        return eligible

    except Exception as exc:
        logger.error("Failed to query tenders for building rights extraction: %s", exc)
        return []


def get_watchlist_tender_ids(db: TenderDB) -> list[int]:
    """Get all unique tender IDs across all user watchlists.

    Args:
        db: Database instance (uses underlying Supabase client).

    Returns:
        List of unique tender IDs.
    """
    if not db._client:
        return []

    try:
        result = (
            db._client.table("user_watchlist")
            .select("tender_id")
            .eq("active", True)
            .execute()
        )
        ids = list({row["tender_id"] for row in (result.data or [])})
        logger.info("Found %d unique watchlisted tender IDs", len(ids))
        return ids
    except Exception as exc:
        logger.error("Failed to fetch watchlist IDs: %s", exc)
        return []


def main() -> None:
    """Main entry point for batch extraction."""
    parser = argparse.ArgumentParser(
        description="Extract building rights for active tenders with published brochures",
    )
    parser.add_argument(
        "--tender-ids", nargs="+", type=int,
        help="Specific tender IDs to process (overrides default query)",
    )
    parser.add_argument(
        "--plan-numbers", nargs="+",
        help="Specific plan numbers to process directly (skip brochure step)",
    )
    parser.add_argument(
        "--watchlist-only", action="store_true",
        help="Only process watchlisted tenders (legacy behavior)",
    )
    parser.add_argument(
        "--max-per-run", type=int, default=MAX_PER_RUN,
        help=f"Maximum tenders to process (default: {MAX_PER_RUN})",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Don't write to Supabase",
    )
    args = parser.parse_args()

    db = TenderDB()
    results = []

    if args.plan_numbers:
        # Direct plan number processing (no brochure, no tender lookup)
        logger.info("Processing %d plan numbers directly...", len(args.plan_numbers))
        for plan_num in args.plan_numbers:
            res = process_plan_directly(plan_num, db, dry_run=args.dry_run)
            results.append(res)
            logger.info("Plan %s: %s", plan_num, res["status"])
            if res["status"] not in ("already_extracted", "success"):
                time.sleep(MAVAT_DELAY)

    else:
        # Tender-based processing
        if args.tender_ids:
            tender_ids = args.tender_ids
        elif args.watchlist_only:
            tender_ids = get_watchlist_tender_ids(db)
        else:
            tenders = get_tenders_needing_building_rights(
                db, limit=args.max_per_run,
            )
            tender_ids = [t["tender_id"] for t in tenders]

        if not tender_ids:
            logger.info("No tenders to process")
            return

        # Limit to max_per_run (for --tender-ids and --watchlist-only paths)
        if len(tender_ids) > args.max_per_run:
            logger.info(
                "Processing %d/%d tenders (limited by --max-per-run)",
                args.max_per_run, len(tender_ids),
            )
            tender_ids = tender_ids[:args.max_per_run]

        taba_client = TabaClient(output_dir=MAVAT_DIR)
        client = LandTendersClient()

        for tender_id in tender_ids:
            res = process_tender(
                tender_id, db, taba_client,
                client=client, dry_run=args.dry_run,
            )
            results.append(res)
            logger.info("Tender %d: %s", tender_id, res["status"])

            # Rate limit between API requests (lighter than Playwright)
            if res["status"] not in ("already_extracted", "tender_not_found", "no_plan"):
                time.sleep(2)

    # Summary
    statuses = {}
    for r in results:
        statuses[r["status"]] = statuses.get(r["status"], 0) + 1

    logger.info("Batch complete: %d processed", len(results))
    for status, count in sorted(statuses.items()):
        logger.info("  %s: %d", status, count)

    total_rows = sum(r["building_rights_rows"] for r in results)
    logger.info("Total building rights rows: %d", total_rows)

    # Write results to file for debugging
    output_path = Path(__file__).resolve().parent.parent / "tmp" / "batch_building_rights_results.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    logger.info("Results written to %s", output_path)


if __name__ == "__main__":
    main()
