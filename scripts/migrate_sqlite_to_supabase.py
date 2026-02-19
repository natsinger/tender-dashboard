"""
One-time migration script: SQLite → Supabase.

Reads all rows from the local SQLite database (tenders, tender_history,
tender_documents) and upserts them into Supabase PostgreSQL in batches.

Idempotent — safe to run multiple times (uses upsert with on_conflict).

Usage:
    python scripts/migrate_sqlite_to_supabase.py
"""

import logging
import math
import sqlite3
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import DB_PATH

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

BATCH_SIZE = 500


def _get_supabase_client():
    """Create and return a Supabase client."""
    from supabase import create_client

    from config import SUPABASE_KEY, SUPABASE_URL

    if not SUPABASE_URL or not SUPABASE_KEY:
        logger.error("SUPABASE_URL and SUPABASE_KEY must be set in .env or environment")
        sys.exit(1)

    return create_client(SUPABASE_URL, SUPABASE_KEY)


def _read_sqlite_table(db_path: Path, table: str) -> list[dict]:
    """Read all rows from a SQLite table as a list of dicts."""
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(f"SELECT * FROM {table}").fetchall()  # noqa: S608
        return [dict(r) for r in rows]
    finally:
        conn.close()


def _clean_row(row: dict) -> dict:
    """Convert NaN-like values to None for JSON compatibility."""
    cleaned = {}
    for key, val in row.items():
        if val is None:
            cleaned[key] = None
        elif isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
            cleaned[key] = None
        elif isinstance(val, str) and val.strip() == "":
            cleaned[key] = None
        else:
            cleaned[key] = val
    return cleaned


def _batch_upsert(
    client,
    table: str,
    rows: list[dict],
    on_conflict: str,
) -> int:
    """Upsert rows to Supabase in batches. Returns total rows processed."""
    total = len(rows)
    if total == 0:
        logger.info("  %s: no rows to migrate", table)
        return 0

    processed = 0
    for i in range(0, total, BATCH_SIZE):
        batch = rows[i : i + BATCH_SIZE]
        cleaned = [_clean_row(r) for r in batch]

        # Remove the 'id' column for tables with BIGSERIAL PKs
        # (let Supabase auto-generate IDs)
        if table in ("tender_history", "tender_documents"):
            cleaned = [{k: v for k, v in row.items() if k != "id"} for row in cleaned]

        client.table(table).upsert(
            cleaned,
            on_conflict=on_conflict,
        ).execute()

        processed += len(batch)
        logger.info(
            "  %s: %d / %d rows upserted (%.0f%%)",
            table, processed, total, processed / total * 100,
        )

    return processed


def main() -> None:
    """Run the migration."""
    logger.info("Starting SQLite → Supabase migration")
    logger.info("SQLite source: %s", DB_PATH)

    if not DB_PATH.exists():
        logger.error("SQLite database not found at %s", DB_PATH)
        sys.exit(1)

    client = _get_supabase_client()

    # 1. Migrate tenders
    logger.info("Reading tenders from SQLite...")
    tenders = _read_sqlite_table(DB_PATH, "tenders")
    logger.info("  Found %d tenders", len(tenders))
    _batch_upsert(client, "tenders", tenders, on_conflict="tender_id")

    # 2. Migrate tender_history
    logger.info("Reading tender_history from SQLite...")
    history = _read_sqlite_table(DB_PATH, "tender_history")
    logger.info("  Found %d history rows", len(history))
    _batch_upsert(client, "tender_history", history, on_conflict="tender_id,snapshot_date")

    # 3. Migrate tender_documents
    logger.info("Reading tender_documents from SQLite...")
    docs = _read_sqlite_table(DB_PATH, "tender_documents")
    logger.info("  Found %d document rows", len(docs))
    _batch_upsert(client, "tender_documents", docs, on_conflict="tender_id,row_id")

    logger.info("Migration complete!")

    # Verify counts
    for table in ("tenders", "tender_history", "tender_documents"):
        result = client.table(table).select("*", count="exact").limit(0).execute()
        count = result.count if result.count is not None else "unknown"
        logger.info("  Supabase %s: %s rows", table, count)


if __name__ == "__main__":
    main()
