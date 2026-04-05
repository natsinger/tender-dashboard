"""Batch-enrich tenders from RMI API, newest first, in batches of 500.

Calls the Land Authority MichrazDetailsApi for each tender to fetch
documents, lot data, and other detail fields. Saves results to Supabase.

Usage:
    python scripts/batch_enrich.py --dry-run
    python scripts/batch_enrich.py --batch-size 500 --max-batches 1
    python scripts/batch_enrich.py --batch-size 500 --delay 2.0 --start-batch 2
"""

import argparse
import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from data_client import LandTendersClient
from db import TenderDB

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def get_all_tender_ids_desc(db: TenderDB) -> list[int]:
    """Fetch all tender IDs from Supabase, sorted descending (newest first)."""
    all_ids: list[int] = []
    offset = 0
    page = 1000

    while True:
        result = (
            db._client.table("tenders")
            .select("tender_id")
            .order("tender_id", desc=True)
            .range(offset, offset + page - 1)
            .execute()
        )
        rows = result.data or []
        all_ids.extend(r["tender_id"] for r in rows)
        if len(rows) < page:
            break
        offset += page

    return all_ids


def main() -> None:
    parser = argparse.ArgumentParser(description="Batch-enrich tenders from RMI API")
    parser.add_argument("--batch-size", type=int, default=500)
    parser.add_argument("--delay", type=float, default=1.5, help="Seconds between RMI API calls")
    parser.add_argument("--workers", type=int, default=2, help="Concurrent API workers")
    parser.add_argument("--start-batch", type=int, default=0, help="Skip first N batches (resume)")
    parser.add_argument("--max-batches", type=int, default=None, help="Stop after N batches")
    parser.add_argument("--dry-run", action="store_true", help="Show plan only")
    args = parser.parse_args()

    db = TenderDB()
    client = LandTendersClient()

    logger.info("Fetching tender ID list from Supabase...")
    all_ids = get_all_tender_ids_desc(db)
    logger.info("Total: %d tenders (newest first: %d .. %d)", len(all_ids), all_ids[0], all_ids[-1])

    batches = [all_ids[i : i + args.batch_size] for i in range(0, len(all_ids), args.batch_size)]
    total_batches = len(batches)
    logger.info("Split into %d batches of %d", total_batches, args.batch_size)

    if args.start_batch > 0:
        batches = batches[args.start_batch :]
        logger.info("Resuming from batch %d (%d remaining)", args.start_batch, len(batches))

    if args.max_batches:
        batches = batches[: args.max_batches]
        logger.info("Limiting to %d batch(es)", args.max_batches)

    if args.dry_run:
        for i, batch in enumerate(batches):
            bnum = i + args.start_batch
            logger.info("Batch %d: %d -> %d (%d tenders)", bnum, batch[0], batch[-1], len(batch))
        logger.info("Dry run — no API calls made.")
        return

    total_docs = 0
    for batch_idx, batch_ids in enumerate(batches):
        bnum = batch_idx + args.start_batch
        logger.info(
            "=== Batch %d/%d: %d -> %d (%d tenders) ===",
            bnum + 1, total_batches, batch_ids[0], batch_ids[-1], len(batch_ids),
        )

        t0 = time.time()
        try:
            # Clear the in-memory cache so we hit the RMI API fresh
            client._details_cache.clear()

            new_docs = client.sync_documents_to_db(batch_ids)
            elapsed = time.time() - t0
            total_docs += new_docs

            logger.info(
                "Batch %d done: %d new docs (%.0fs, %.1f tenders/sec)",
                bnum + 1, new_docs, elapsed,
                len(batch_ids) / elapsed if elapsed > 0 else 0,
            )

        except Exception as e:
            elapsed = time.time() - t0
            logger.error("Batch %d failed after %.0fs: %s", bnum + 1, elapsed, e)
            logger.info("Waiting 60s before next batch...")
            time.sleep(60)
            continue

        # Pause between batches
        if batch_idx < len(batches) - 1:
            logger.info("Pausing 15s between batches...")
            time.sleep(15)

    logger.info("All done! Total new documents: %d", total_docs)


if __name__ == "__main__":
    main()
