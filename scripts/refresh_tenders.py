"""
Daily tender data refresh script.

Fetches all tenders from the Land Authority API, saves a JSON snapshot,
persists to SQLite, and syncs documents for active tenders.

Designed to be run by GitHub Actions cron job.

Usage:
    python scripts/refresh_tenders.py
"""

import logging
import sys
from pathlib import Path

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

    logger.info("Starting daily tender refresh...")

    # 1. Fetch from API
    df = client.fetch_tenders_list()
    if df is None:
        logger.error("Failed to fetch tenders from API")
        sys.exit(1)

    # 2. Save JSON snapshot (existing behavior)
    filepath = client.save_json_snapshot(df)
    logger.info("JSON snapshot saved: %s (%d tenders)", filepath, len(df))

    # 3. Save to SQLite database
    rows = client.save_to_db(df)
    logger.info("Saved %d tenders to database", rows)

    # 4. Sync documents for active tenders (status 1=draft, 2=committee, 3=active)
    if "status_code" in df.columns:
        active_ids = df[df["status_code"].isin([1, 2, 3])]["tender_id"].tolist()
    else:
        active_ids = df["tender_id"].tolist()

    logger.info("Syncing documents for %d active tenders...", len(active_ids))
    new_docs = client.sync_documents_to_db(active_ids)
    logger.info("Document sync complete: %d new documents found", new_docs)

    # 5. Log summary
    try:
        from db import TenderDB
        stats = TenderDB().get_stats()
        logger.info("DB stats: %s", stats)
    except Exception as exc:
        logger.warning("Could not read DB stats: %s", exc)

    logger.info("Daily refresh complete.")


if __name__ == "__main__":
    main()
