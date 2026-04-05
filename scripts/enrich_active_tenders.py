"""One-time enrichment for status=2 tenders (נדון בוועדת מכרזים) from 2020+.

Fetches fresh details from the RMI API, syncs documents, and extracts
building rights for tenders that are missing data.

Usage:
    python scripts/enrich_active_tenders.py --dry-run
    python scripts/enrich_active_tenders.py --max-tenders 5
    python scripts/enrich_active_tenders.py
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

from building_rights_extractor import extract_building_rights
from data_client import LandTendersClient
from db import TenderDB
from taba_client import TabaClient

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# Target: status_code=2 from 2020 onwards
TARGET_STATUS = 2
MIN_TENDER_ID = 20200000


def get_target_tenders(db: TenderDB) -> list[dict]:
    """Fetch status=2 tenders from 2020+ sorted newest first."""
    all_tenders: list[dict] = []
    offset = 0
    page = 1000

    while True:
        result = (
            db._client.table("tenders")
            .select("tender_id, tender_name, city, plan_number, extraction_status")
            .eq("status_code", TARGET_STATUS)
            .gte("tender_id", MIN_TENDER_ID)
            .order("tender_id", desc=True)
            .range(offset, offset + page - 1)
            .execute()
        )
        rows = result.data or []
        all_tenders.extend(rows)
        if len(rows) < page:
            break
        offset += page

    return all_tenders


def enrich_tender(
    tender: dict,
    client: LandTendersClient,
    db: TenderDB,
    taba: TabaClient,
    dry_run: bool = False,
) -> dict:
    """Enrich a single tender: details + docs + building rights.

    Returns:
        Summary dict with what was done.
    """
    tid = tender["tender_id"]
    name = tender.get("tender_name", "?")
    plan = tender.get("plan_number")
    summary = {
        "tender_id": tid,
        "name": name,
        "docs_synced": 0,
        "building_rights": False,
        "plan_found": plan is not None,
        "errors": [],
    }

    if dry_run:
        return summary

    # Step 1: Fetch details from RMI API + sync documents.
    # Clear cache for this tender to force a fresh API call.
    client._details_cache.pop(tid, None)
    cache_file = Path("details_cache") / f"{tid}.json"
    if cache_file.exists():
        cache_file.unlink()

    try:
        new_docs = client.sync_documents_to_db([tid])
        summary["docs_synced"] = new_docs
    except Exception as exc:
        summary["errors"].append(f"doc_sync: {exc}")
        logger.warning("Tender %d doc sync failed: %s", tid, exc)

    # Re-read tender to pick up any plan_number backfilled by sync.
    if not plan:
        try:
            refreshed = db._client.table("tenders").select(
                "plan_number",
            ).eq("tender_id", tid).execute()
            if refreshed.data and refreshed.data[0].get("plan_number"):
                plan = refreshed.data[0]["plan_number"]
                summary["plan_found"] = True
        except Exception:
            pass

    # Step 2: Building rights extraction (if we have a plan number).
    if plan and tender.get("extraction_status") not in ("complete", "success"):
        try:
            plan_ids = taba.get_tender_plan_ids(tid)
            if not plan_ids:
                # Use existing plan_number directly
                plan_ids = [plan]

            for plan_id in plan_ids[:3]:
                dl = taba.download_takanon_by_plan_id(str(plan_id))
                if dl.get("status") != "success":
                    continue

                pdf_path = Path(dl["file_path"])
                plan_number = dl.get("plan_number", str(plan_id))
                rights = extract_building_rights(pdf_path, plan_number)

                if rights.get("success") and rights.get("rows"):
                    clean_rows = [
                        {k: v for k, v in r.items() if k != "_raw"}
                        for r in rights["rows"]
                    ]
                    db.upsert_building_rights(
                        plan_number, clean_rows, rights.get("status"),
                    )
                    db.update_plan_number(tid, plan_number)
                    summary["building_rights"] = True
                    logger.info(
                        "Tender %d: extracted %d building rights rows (plan %s)",
                        tid, len(clean_rows), plan_number,
                    )
                    break

                time.sleep(2)

        except Exception as exc:
            summary["errors"].append(f"building_rights: {exc}")
            logger.warning("Tender %d building rights failed: %s", tid, exc)

    return summary


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Enrich status=2 tenders (2020+) from RMI API",
    )
    parser.add_argument("--max-tenders", type=int, default=None)
    parser.add_argument("--delay", type=float, default=2.0,
                        help="Seconds between API calls (default 2.0)")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    db = TenderDB()
    client = LandTendersClient()
    taba = TabaClient()

    tenders = get_target_tenders(db)
    logger.info(
        "Found %d status=%d tenders from 2020+", len(tenders), TARGET_STATUS,
    )

    if args.max_tenders:
        tenders = tenders[: args.max_tenders]
        logger.info("Limiting to %d tenders", len(tenders))

    if args.dry_run:
        for t in tenders:
            plan = t.get("plan_number", "—")
            ext = t.get("extraction_status", "NULL")
            logger.info(
                "  %d %-15s plan=%-20s extraction=%s",
                t["tender_id"], t.get("tender_name", "?"), plan, ext,
            )
        logger.info("Dry run — no API calls made.")
        return

    total_docs = 0
    total_br = 0
    total_errors = 0

    for i, tender in enumerate(tenders, 1):
        tid = tender["tender_id"]
        logger.info(
            "--- [%d/%d] Tender %d (%s) ---",
            i, len(tenders), tid, tender.get("tender_name", "?"),
        )

        result = enrich_tender(tender, client, db, taba, dry_run=False)

        total_docs += result["docs_synced"]
        if result["building_rights"]:
            total_br += 1
        if result["errors"]:
            total_errors += 1
            for err in result["errors"]:
                logger.warning("  Error: %s", err)

        if i % 10 == 0:
            logger.info(
                "Progress: %d/%d | docs=%d br=%d errors=%d",
                i, len(tenders), total_docs, total_br, total_errors,
            )

        time.sleep(args.delay)

    logger.info(
        "=== Done! Processed %d tenders | new_docs=%d building_rights=%d errors=%d ===",
        len(tenders), total_docs, total_br, total_errors,
    )


if __name__ == "__main__":
    main()
