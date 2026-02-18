"""
Migrate existing JSON snapshots and cached detail files into the SQLite database.

Part A: Replay tenders_list_*.json snapshots chronologically into the
        tenders + tender_history tables.
Part B: Import documents from data/details_cache/*.json into the
        tender_documents table.

Usage:
    python scripts/migrate_json_to_db.py
"""

import json
import logging
import re
import sys
from pathlib import Path

import pandas as pd

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import DATA_DIR, PROJECT_ROOT
from data_client import normalize_api_columns
from db import TenderDB

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)


def find_json_snapshots() -> list[tuple[str, Path]]:
    """Find all tenders_list_*.json files in project root and data dir.

    Returns:
        List of (date_string, filepath) tuples sorted by date ascending.
    """
    pattern = re.compile(r"tenders_list_(\d{2})_(\d{2})_(\d{4})\.json")
    snapshots: list[tuple[str, Path]] = []

    search_dirs = [PROJECT_ROOT, DATA_DIR]
    seen_names: set[str] = set()

    for search_dir in search_dirs:
        if not search_dir.exists():
            continue
        for filepath in search_dir.glob("tenders_list_*.json"):
            if filepath.name in seen_names:
                continue
            seen_names.add(filepath.name)

            match = pattern.match(filepath.name)
            if match:
                day, month, year = match.groups()
                date_str = f"{year}-{month}-{day}"
                snapshots.append((date_str, filepath))

    snapshots.sort(key=lambda x: x[0])
    return snapshots


def migrate_snapshots(db: TenderDB) -> int:
    """Replay JSON snapshots into the database chronologically.

    Returns:
        Number of snapshots processed.
    """
    snapshots = find_json_snapshots()
    if not snapshots:
        logger.warning("No JSON snapshots found to migrate")
        return 0

    logger.info("Found %d JSON snapshots to migrate", len(snapshots))

    for i, (date_str, filepath) in enumerate(snapshots, 1):
        logger.info("[%d/%d] Processing %s (date: %s)", i, len(snapshots), filepath.name, date_str)

        try:
            df = pd.read_json(filepath, encoding="utf-8")

            # Normalize if raw API format (has MichrazID column)
            if "MichrazID" in df.columns:
                df = normalize_api_columns(df)

            db.upsert_tenders(df, snapshot_date=date_str)

        except Exception as exc:
            logger.error("Failed to process %s: %s", filepath.name, exc)
            continue

    return len(snapshots)


def migrate_documents(db: TenderDB) -> int:
    """Import documents from cached detail files into tender_documents.

    Returns:
        Total number of documents imported.
    """
    cache_dir = DATA_DIR / "details_cache"
    if not cache_dir.exists():
        logger.warning("No details_cache directory found at %s", cache_dir)
        return 0

    detail_files = list(cache_dir.glob("*.json"))
    if not detail_files:
        logger.warning("No cached detail files found")
        return 0

    logger.info("Found %d cached detail files to migrate", len(detail_files))

    total_docs = 0

    for i, filepath in enumerate(detail_files, 1):
        try:
            data = json.loads(filepath.read_text(encoding="utf-8"))
            tender_id = data.get("MichrazID")
            if not tender_id:
                continue

            doc_list = list(data.get("MichrazDocList", []))

            full_doc = data.get("MichrazFullDocument")
            if full_doc and full_doc.get("RowID") is not None:
                doc_list.append(full_doc)

            if doc_list:
                new_docs = db.upsert_documents(tender_id, doc_list)
                total_docs += len(new_docs)

        except Exception as exc:
            logger.error("Failed to process %s: %s", filepath.name, exc)
            continue

        if i % 50 == 0:
            logger.info("Progress: %d/%d detail files processed", i, len(detail_files))

    return total_docs


def main() -> None:
    """Run the full migration."""
    logger.info("Starting database migration...")

    db = TenderDB()

    # Part A: Tender snapshots
    snapshot_count = migrate_snapshots(db)
    logger.info("Part A complete: %d snapshots processed", snapshot_count)

    # Part B: Documents from details_cache
    doc_count = migrate_documents(db)
    logger.info("Part B complete: %d documents imported", doc_count)

    # Summary
    stats = db.get_stats()
    logger.info("Migration complete. DB stats:")
    for table, count in stats.items():
        logger.info("  %s: %d rows", table, count)


if __name__ == "__main__":
    main()
