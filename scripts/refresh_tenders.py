"""
Daily tender data refresh script.

Fetches all tenders from the Land Authority API, saves a JSON snapshot,
persists to SQLite, syncs documents for active tenders, and sends
watchlist alert emails for any new documents found.

Designed to be run by GitHub Actions cron job.

Usage:
    python scripts/refresh_tenders.py
"""

import logging
import os
import sys
import traceback
from pathlib import Path

# Ensure UTF-8 output on Windows (Hebrew RTL display)
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from data_client import LandTendersClient

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)


def main() -> None:
    """Fetch tenders, save snapshot, persist to DB, sync documents."""
    project_root = Path(__file__).resolve().parent.parent
    client = LandTendersClient(data_dir=str(project_root))

    # Diagnostic: check if Supabase env vars are reaching the script
    sb_url = os.environ.get("SUPABASE_URL", "")
    sb_key = os.environ.get("SUPABASE_KEY", "")
    logger.info(
        "Env check: SUPABASE_URL=%s (len=%d), SUPABASE_KEY=%s (len=%d)",
        "SET" if sb_url else "EMPTY", len(sb_url),
        "SET" if sb_key else "EMPTY", len(sb_key),
    )

    logger.info("Starting daily tender refresh...")

    # 1. Fetch from API
    df = client.fetch_tenders_list()
    if df is None:
        logger.error("Failed to fetch tenders from API")
        sys.exit(1)

    # 2. Save JSON snapshot (existing behavior)
    filepath = client.save_json_snapshot(df)
    logger.info("JSON snapshot saved: %s (%d tenders)", filepath, len(df))

    # 3. Detect new tender IDs (before upsert) for new-tender alerts
    new_tender_rows: list[dict] = []
    try:
        from db import TenderDB as _TenderDB_pre
        existing_ids = _TenderDB_pre().get_all_tender_ids()
        fetched_ids = set(df["tender_id"].tolist())
        new_ids = fetched_ids - existing_ids
        if new_ids:
            new_tender_rows = df[df["tender_id"].isin(new_ids)].to_dict("records")
            logger.info(
                "Detected %d new tender(s) not yet in DB: %s",
                len(new_ids), sorted(new_ids),
            )
    except Exception as exc:
        logger.warning("New-tender detection failed (non-fatal): %s", exc)

    # 4. Save to database
    try:
        rows = client.save_to_db(df)
        logger.info("Saved %d tenders to database", rows)
    except Exception as exc:
        logger.error(
            "Failed to save to database: %s\n%s",
            exc,
            traceback.format_exc(),
        )

    # 5. Sync documents for active tenders (non-fatal — skipped if API is slow)
    try:
        if "status_code" in df.columns:
            active_ids = df[df["status_code"].isin([1, 2, 3])]["tender_id"].tolist()
        else:
            active_ids = df["tender_id"].tolist()

        # Prioritize watchlisted tenders so they are synced first
        try:
            from user_db import UserDB as _UserDB_sync
            watched_entries = _UserDB_sync().get_all_active_watchlists()
            watched_ids = {entry["tender_id"] for entry in watched_entries}
            watched_first = [tid for tid in active_ids if tid in watched_ids]
            rest = [tid for tid in active_ids if tid not in watched_ids]
            active_ids = watched_first + rest
            if watched_first:
                logger.info(
                    "Prioritized %d watchlisted tenders for doc sync",
                    len(watched_first),
                )
        except Exception as exc:
            logger.warning("Could not prioritize watchlisted tenders: %s", exc)

        # Limit batch size to avoid API rate limits in CI (no cache on fresh checkout)
        max_doc_sync = int(os.environ.get("DOC_SYNC_LIMIT", "50"))
        if len(active_ids) > max_doc_sync:
            logger.info(
                "Limiting doc sync to %d/%d tenders (set DOC_SYNC_LIMIT to change)",
                max_doc_sync, len(active_ids),
            )
            active_ids = active_ids[:max_doc_sync]

        logger.info("Syncing documents for %d active tenders...", len(active_ids))
        new_docs = client.sync_documents_to_db(active_ids)
        logger.info("Document sync complete: %d new documents found", new_docs)
    except Exception as exc:
        logger.warning("Document sync failed (non-fatal): %s", exc)

    # 6. Log summary
    try:
        from db import TenderDB
        stats = TenderDB().get_stats()
        logger.info("DB stats: %s", stats)
    except Exception as exc:
        logger.warning("Could not read DB stats: %s", exc)

    # 7. Check watchlist alerts and send emails (non-fatal)
    watchlist_emails = 0
    new_tender_email = 0
    try:
        from alerts import AlertEngine
        from db import TenderDB as _TenderDB
        from user_db import UserDB as _UserDB

        engine = AlertEngine(_TenderDB(), _UserDB())

        # Watchlist document alerts (team-wide)
        watchlist_emails = engine.check_and_send()
        logger.info("Watchlist alerts: %d email(s) sent", watchlist_emails)

        # New tender alerts (if any new tenders were detected in step 3)
        if new_tender_rows:
            sent = engine.send_new_tender_alert(new_tender_rows)
            new_tender_email = 1 if sent else 0
            logger.info("New-tender alert: %s", "sent" if sent else "not sent")
    except Exception as exc:
        logger.error(
            "Alert check failed (non-fatal): %s\n%s",
            exc,
            traceback.format_exc(),
        )

    # 8. Resolve GovMap TABA URLs for tenders with plan numbers
    try:
        logger.info("Step 8: Resolving GovMap TABA URLs...")
        from db import TenderDB as _TenderDB_gm
        from govmap_client import batch_resolve_govmap_urls

        gm_db = _TenderDB_gm()
        result = (
            gm_db._client.table("tenders")
            .select("tender_id, plan_number")
            .not_.is_("plan_number", "null")
            .is_("govmap_url", "null")
            .execute()
        )
        pending = result.data if result.data else []

        if pending:
            plan_numbers = [row["plan_number"] for row in pending]
            plan_to_tid = {
                row["plan_number"]: row["tender_id"] for row in pending
            }
            logger.info(
                "Found %d tenders with plan_number but no govmap_url",
                len(pending),
            )

            resolved = batch_resolve_govmap_urls(plan_numbers)
            updates: list[tuple[str, int]] = [
                (url, plan_to_tid[pn])
                for pn, url in resolved.items()
                if url is not None
            ]
            failed = len(resolved) - len(updates)

            if updates:
                gm_db.update_govmap_urls(updates)

            logger.info(
                "GovMap resolve complete: %d resolved, %d failed",
                len(updates), failed,
            )
        else:
            logger.info("No tenders pending GovMap resolution")
    except Exception as exc:
        logger.warning(
            "GovMap URL resolution failed (non-fatal): %s\n%s",
            exc, traceback.format_exc(),
        )

    # 9. Final summary
    logger.info(
        "=== Daily refresh complete | watchlist_emails=%d new_tender_email=%d ===",
        watchlist_emails,
        new_tender_email,
    )


if __name__ == "__main__":
    main()
