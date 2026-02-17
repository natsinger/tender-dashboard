"""
Daily tender data refresh script.

Fetches all tenders from the Land Authority API and saves a JSON snapshot.
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
    """Fetch tenders and save a daily snapshot."""
    project_root = Path(__file__).resolve().parent.parent
    client = LandTendersClient(data_dir=str(project_root))

    logger.info("Starting daily tender refresh...")

    df = client.fetch_tenders_list()
    if df is None:
        logger.error("Failed to fetch tenders from API")
        sys.exit(1)

    filepath = client.save_json_snapshot(df)
    logger.info("Snapshot saved: %s (%d tenders)", filepath, len(df))


if __name__ == "__main__":
    main()
