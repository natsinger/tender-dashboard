"""Extract lots for status=2 tenders (2020+) that have pending lot data.

Runs the existing extract_lots_batch.process_tender() on tenders that have
API lot data (lot_count > 0) but lot_extraction_status='pending'.

Usage:
    python scripts/extract_lots_active.py --dry-run
    python scripts/extract_lots_active.py
"""

import argparse
import logging
import os
import sys
import time
from pathlib import Path

os.environ.setdefault("PYTHONIOENCODING", "utf-8")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from data_client import LandTendersClient
from db import TenderDB
from lot_extractor import BrochureLotExtractor
from scripts.extract_lots_batch import process_tender

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract lots for status=2 tenders (2020+)",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--max-tenders", type=int, default=None)
    args = parser.parse_args()

    db = TenderDB()
    client = LandTendersClient()
    extractor = BrochureLotExtractor()

    # Get all status=2 tenders from 2020+ with pending lot extraction
    result = (
        db._client.table("tenders")
        .select("tender_id, tender_name, lot_count, lot_extraction_status")
        .eq("status_code", 2)
        .gte("tender_id", 20200000)
        .in_("lot_extraction_status", ["pending", "failed"])
        .order("tender_id", desc=True)
        .limit(500)
        .execute()
    )
    tenders = result.data or []
    logger.info("Found %d tenders needing lot extraction", len(tenders))

    if args.max_tenders:
        tenders = tenders[: args.max_tenders]

    if args.dry_run:
        for t in tenders:
            logger.info(
                "  %d %-15s lot_count=%s status=%s",
                t["tender_id"], t.get("tender_name", "?"),
                t.get("lot_count", 0), t.get("lot_extraction_status", "NULL"),
            )
        logger.info("Dry run — no API calls made.")
        return

    success = 0
    failed = 0
    total_lots = 0

    for i, t in enumerate(tenders, 1):
        tid = t["tender_id"]
        logger.info(
            "--- [%d/%d] Tender %d (%s) ---",
            i, len(tenders), tid, t.get("tender_name", "?"),
        )

        r = process_tender(tid, db, client, extractor, api_only=False)

        if r["status"] == "extracted":
            success += 1
            total_lots += r["lots_count"]
        else:
            failed += 1
            if r.get("error"):
                logger.warning("  Error: %s", r["error"])

        time.sleep(1)

    logger.info(
        "=== Done! success=%d failed=%d total_lots=%d ===",
        success, failed, total_lots,
    )


if __name__ == "__main__":
    main()
