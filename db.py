"""
Supabase database layer for the Land Tenders Dashboard.

Provides persistent storage for tenders, historical snapshots, and document
tracking via Supabase PostgreSQL. Replaces the original SQLite implementation
(Sprint 6 migration).

Tables managed by this module:
    tenders          — current state of each tender (upserted daily)
    tender_history   — daily snapshots for trend analysis
    tender_documents — per-tender document tracking (detect additions)

User-facing tables (watchlist, reviews, alert_history) are in user_db.py.

Usage:
    from db import TenderDB
    db = TenderDB()
    db.upsert_tenders(df, snapshot_date="2026-02-17")
    df = db.load_current_tenders()
"""

import logging
import math
from datetime import date, datetime
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)

# Column names expected in the tenders DataFrame (from normalize_api_columns).
TENDER_COLUMNS = [
    "tender_id", "tender_name", "city_code", "city", "region", "location",
    "tender_type_code", "tender_type", "purpose_code", "purpose",
    "status_code", "status", "units", "publish_date", "deadline",
    "committee_date", "published_booklet", "targeted",
    "area_sqm", "min_price", "gush", "helka",
]

# Batch size for Supabase upsert operations.
_BATCH_SIZE = 500

# Page size for paginated reads (Supabase default limit is 1000).
_PAGE_SIZE = 1000


def _clean_val(val: object) -> object:
    """Convert NaN/NaT/inf to None for JSON-safe Supabase payloads.

    Also converts booleans to int (0/1) because Supabase table columns
    ``published_booklet`` and ``targeted`` are typed as integer.

    Args:
        val: Any Python value (from a pandas row or dict).

    Returns:
        The value, or None if it's NaN/NaT/inf/empty-string.
    """
    if val is None:
        return None
    # bool check MUST come before numeric checks (bool is subclass of int)
    if isinstance(val, (bool,)):
        return int(val)
    try:
        import numpy as np
        if isinstance(val, np.bool_):
            return int(val)
    except ImportError:
        pass
    if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
        return None
    if isinstance(val, pd.Timestamp):
        if pd.isna(val):
            return None
        return val.isoformat()
    if hasattr(val, "isoformat"):
        return val.isoformat()
    return val


def _clean_dict(d: dict) -> dict:
    """Apply _clean_val to every value in a dict."""
    return {k: _clean_val(v) for k, v in d.items()}


class TenderDB:
    """Supabase-backed database for tender data persistence and history tracking.

    Maintains the same public API as the original SQLite implementation so
    callers (data_client, dashboard_utils, alerts, management page) don't
    need changes.
    """

    def __init__(self) -> None:
        """Connect to Supabase. Falls back to no-ops if not configured."""
        from user_db import _get_client

        self._client = _get_client()
        if self._client:
            logger.debug("TenderDB connected to Supabase")
        else:
            logger.warning("TenderDB: no Supabase connection — data operations will fail")

    # ------------------------------------------------------------------
    # Paginated read helper
    # ------------------------------------------------------------------

    def _paginated_select(
        self,
        table: str,
        select: str = "*",
        filters: Optional[dict] = None,
        order_col: Optional[str] = None,
        order_desc: bool = False,
    ) -> list[dict]:
        """Fetch all rows from a table using pagination.

        Supabase REST API returns at most 1000 rows per request.
        This method pages through until all rows are retrieved.

        Args:
            table: Table name.
            select: Column selection string.
            filters: Dict of {column: value} equality filters.
            order_col: Column to order by. Required for stable pagination.
            order_desc: If True, order descending.

        Returns:
            List of row dicts.
        """
        if not self._client:
            return []

        all_rows: list[dict] = []
        offset = 0

        while True:
            query = self._client.table(table).select(select)

            if filters:
                for col, val in filters.items():
                    query = query.eq(col, val)

            if order_col:
                query = query.order(order_col, desc=order_desc)

            query = query.range(offset, offset + _PAGE_SIZE - 1)

            try:
                result = query.execute()
            except Exception as exc:
                logger.error("Paginated select from %s failed: %s", table, exc)
                break

            rows = result.data or []
            all_rows.extend(rows)

            if len(rows) < _PAGE_SIZE:
                break  # Last page

            offset += _PAGE_SIZE

        return all_rows

    # ------------------------------------------------------------------
    # Tender upsert
    # ------------------------------------------------------------------

    def upsert_tenders(
        self,
        df: pd.DataFrame,
        snapshot_date: Optional[str] = None,
    ) -> None:
        """Insert or update tenders and write a history snapshot row.

        Args:
            df: DataFrame with normalized tender columns.
            snapshot_date: ISO date string for the history entry.
                Defaults to today.
        """
        if df is None or df.empty:
            logger.warning("upsert_tenders called with empty DataFrame")
            return
        if not self._client:
            logger.error("upsert_tenders: no Supabase connection")
            return

        snapshot_date = snapshot_date or date.today().isoformat()
        now = datetime.now().isoformat()

        # Build tender rows + history rows
        tender_rows: list[dict] = []
        history_rows: list[dict] = []

        for _, row in df.iterrows():
            tender_id = int(row.get("tender_id", 0))
            if not tender_id:
                continue

            tender_row = {
                "tender_id": tender_id,
                "tender_name": _clean_val(row.get("tender_name")),
                "city_code": _clean_val(row.get("city_code")),
                "city": _clean_val(row.get("city")),
                "region": _clean_val(row.get("region")),
                "location": _clean_val(row.get("location")),
                "tender_type_code": _clean_val(row.get("tender_type_code")),
                "tender_type": _clean_val(row.get("tender_type")),
                "purpose_code": _clean_val(row.get("purpose_code")),
                "purpose": _clean_val(row.get("purpose")),
                "status_code": _clean_val(row.get("status_code")),
                "status": _clean_val(row.get("status")),
                "units": _clean_val(row.get("units")),
                "publish_date": _clean_val(row.get("publish_date")),
                "deadline": _clean_val(row.get("deadline")),
                "committee_date": _clean_val(row.get("committee_date")),
                "published_booklet": _clean_val(row.get("published_booklet")),
                "targeted": _clean_val(row.get("targeted")),
                "area_sqm": _clean_val(row.get("area_sqm")),
                "min_price": _clean_val(row.get("min_price")),
                "gush": _clean_val(row.get("gush")),
                "helka": _clean_val(row.get("helka")),
                "last_updated": now,
            }
            tender_rows.append(tender_row)

            history_rows.append({
                "tender_id": tender_id,
                "snapshot_date": snapshot_date,
                "status_code": _clean_val(row.get("status_code")),
                "status": _clean_val(row.get("status")),
                "units": _clean_val(row.get("units")),
                "deadline": _clean_val(row.get("deadline")),
            })

        # Batch upsert tenders
        inserted = 0
        for i in range(0, len(tender_rows), _BATCH_SIZE):
            batch = tender_rows[i : i + _BATCH_SIZE]
            try:
                self._client.table("tenders").upsert(
                    batch,
                    on_conflict="tender_id",
                ).execute()
                inserted += len(batch)
            except Exception as exc:
                logger.error("upsert_tenders batch failed: %s", exc)

        # Batch upsert history (ignore duplicates for same tender+date)
        for i in range(0, len(history_rows), _BATCH_SIZE):
            batch = history_rows[i : i + _BATCH_SIZE]
            try:
                self._client.table("tender_history").upsert(
                    batch,
                    on_conflict="tender_id,snapshot_date",
                    ignore_duplicates=True,
                ).execute()
            except Exception as exc:
                logger.error("upsert_history batch failed: %s", exc)

        logger.info(
            "Upserted %d tenders (snapshot %s)", inserted, snapshot_date,
        )

    # ------------------------------------------------------------------
    # Document upsert
    # ------------------------------------------------------------------

    def upsert_documents(
        self,
        tender_id: int,
        doc_list: list[dict],
    ) -> list[dict]:
        """Insert new documents for a tender. Returns newly added docs.

        Args:
            tender_id: The tender's MichrazID.
            doc_list: List of document dicts from the API (MichrazDocList items).

        Returns:
            List of document dicts that were newly inserted.
        """
        if not doc_list or not self._client:
            return []

        today_str = date.today().isoformat()

        # Get existing row_ids for this tender to detect truly new docs
        try:
            existing_result = (
                self._client.table("tender_documents")
                .select("row_id")
                .eq("tender_id", tender_id)
                .execute()
            )
            existing_ids = {r["row_id"] for r in (existing_result.data or [])}
        except Exception as exc:
            logger.error("Failed to check existing docs for tender %d: %s", tender_id, exc)
            existing_ids = set()

        new_docs: list[dict] = []
        rows_to_insert: list[dict] = []

        for doc in doc_list:
            row_id = doc.get("RowID")
            if row_id is None or row_id in existing_ids:
                continue

            rows_to_insert.append({
                "tender_id": tender_id,
                "row_id": row_id,
                "doc_name": doc.get("DocName"),
                "description": doc.get("Teur"),
                "file_type": doc.get("FileType"),
                "size": doc.get("Size"),
                "pirsum_type": doc.get("PirsumType"),
                "update_date": _clean_val(doc.get("UpdateDate")),
                "first_seen": today_str,
            })
            new_docs.append(doc)

        if rows_to_insert:
            try:
                self._client.table("tender_documents").upsert(
                    rows_to_insert,
                    on_conflict="tender_id,row_id",
                    ignore_duplicates=True,
                ).execute()
                logger.info(
                    "Tender %d: %d new documents added", tender_id, len(new_docs),
                )
            except Exception as exc:
                logger.error("upsert_documents failed for tender %d: %s", tender_id, exc)
                return []

        return new_docs

    # ------------------------------------------------------------------
    # Query methods
    # ------------------------------------------------------------------

    def load_current_tenders(self) -> pd.DataFrame:
        """Load all tenders from Supabase as a DataFrame."""
        rows = self._paginated_select("tenders", order_col="tender_id")

        if not rows:
            logger.warning("No tenders loaded from Supabase")
            return pd.DataFrame()

        df = pd.DataFrame(rows)
        logger.info("Loaded %d tenders from Supabase", len(df))

        # Convert date columns to tz-naive datetime (Supabase returns UTC-aware
        # strings, but the dashboard uses datetime.now() which is tz-naive).
        for col in ("publish_date", "deadline", "committee_date"):
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce", utc=True)
                df[col] = df[col].dt.tz_localize(None)

        # Convert boolean-like columns
        if "published_booklet" in df.columns:
            df["published_booklet"] = df["published_booklet"].astype(bool)

        return df

    def load_tender_history(
        self,
        tender_id: Optional[int] = None,
    ) -> pd.DataFrame:
        """Load historical snapshots, optionally filtered by tender.

        Args:
            tender_id: If provided, filter to this tender only.

        Returns:
            DataFrame with history rows.
        """
        filters = {"tender_id": tender_id} if tender_id is not None else None
        rows = self._paginated_select(
            "tender_history",
            filters=filters,
            order_col="snapshot_date",
        )
        return pd.DataFrame(rows) if rows else pd.DataFrame()

    def load_tender_documents(self, tender_id: int) -> pd.DataFrame:
        """Load all documents for a specific tender.

        Args:
            tender_id: The tender's MichrazID.

        Returns:
            DataFrame with document rows.
        """
        rows = self._paginated_select(
            "tender_documents",
            filters={"tender_id": tender_id},
            order_col="update_date",
        )
        return pd.DataFrame(rows) if rows else pd.DataFrame()

    def get_new_documents(self, since_date: str) -> pd.DataFrame:
        """Get all documents first seen after a given date, with tender info.

        Note: Supabase REST API doesn't support JOINs natively, so we fetch
        documents and tenders separately, then merge in Python.

        Args:
            since_date: ISO date string (e.g. "2026-02-16").

        Returns:
            DataFrame with document rows plus tender_name, city, region.
        """
        if not self._client:
            return pd.DataFrame()

        try:
            # Fetch documents with first_seen > since_date (paginated)
            all_docs: list[dict] = []
            offset = 0
            while True:
                result = (
                    self._client.table("tender_documents")
                    .select("*")
                    .gt("first_seen", since_date)
                    .order("first_seen", desc=True)
                    .range(offset, offset + _PAGE_SIZE - 1)
                    .execute()
                )
                rows = result.data or []
                all_docs.extend(rows)
                if len(rows) < _PAGE_SIZE:
                    break
                offset += _PAGE_SIZE

            if not all_docs:
                return pd.DataFrame()

            docs_df = pd.DataFrame(all_docs)

            # Fetch tender info for the matching tender_ids
            tender_ids = docs_df["tender_id"].unique().tolist()
            tender_info: list[dict] = []
            for i in range(0, len(tender_ids), _BATCH_SIZE):
                batch_ids = tender_ids[i : i + _BATCH_SIZE]
                result = (
                    self._client.table("tenders")
                    .select("tender_id, tender_name, city, region")
                    .in_("tender_id", batch_ids)
                    .execute()
                )
                tender_info.extend(result.data or [])

            if tender_info:
                tenders_df = pd.DataFrame(tender_info)
                merged = docs_df.merge(tenders_df, on="tender_id", how="left")
                return merged

            return docs_df

        except Exception as exc:
            logger.error("get_new_documents failed: %s", exc)
            return pd.DataFrame()

    def get_tender_by_id(self, tender_id: int) -> Optional[dict]:
        """Look up a single tender by ID.

        Args:
            tender_id: The tender's MichrazID.

        Returns:
            Dict of tender fields, or None if not found.
        """
        if not self._client:
            return None

        try:
            result = (
                self._client.table("tenders")
                .select("*")
                .eq("tender_id", tender_id)
                .limit(1)
                .execute()
            )
            rows = result.data or []
            return rows[0] if rows else None
        except Exception as exc:
            logger.error("get_tender_by_id failed: %s", exc)
            return None

    def get_snapshot_dates(self) -> list[str]:
        """List all unique snapshot dates in the history table.

        Returns:
            Sorted list of ISO date strings.
        """
        if not self._client:
            return []

        try:
            # Fetch snapshot_date column (paginated), deduplicate in Python
            all_rows: list[dict] = []
            offset = 0
            while True:
                result = (
                    self._client.table("tender_history")
                    .select("snapshot_date")
                    .order("snapshot_date")
                    .range(offset, offset + _PAGE_SIZE - 1)
                    .execute()
                )
                rows = result.data or []
                all_rows.extend(rows)
                if len(rows) < _PAGE_SIZE:
                    break
                offset += _PAGE_SIZE

            dates = sorted({r["snapshot_date"] for r in all_rows if r.get("snapshot_date")})
            return dates
        except Exception as exc:
            logger.error("get_snapshot_dates failed: %s", exc)
            return []

    def get_new_docs_excluding(
        self,
        tender_id: int,
        since_date: str,
        exclude_row_ids: set[int],
    ) -> list[dict]:
        """Get new documents for a tender, excluding already-notified ones.

        Used by the alert engine (alert_history dedup is in Supabase).

        Args:
            tender_id: The tender's MichrazID.
            since_date: Only docs with first_seen > this date.
            exclude_row_ids: Set of row_ids already sent to this user.

        Returns:
            List of document dicts not yet notified.
        """
        if not self._client:
            return []

        try:
            result = (
                self._client.table("tender_documents")
                .select("row_id, doc_name, description, file_type, size, pirsum_type, update_date, first_seen")
                .eq("tender_id", tender_id)
                .gt("first_seen", since_date)
                .order("first_seen", desc=True)
                .execute()
            )
            rows = result.data or []
            return [r for r in rows if r["row_id"] not in exclude_row_ids]
        except Exception as exc:
            logger.error("get_new_docs_excluding failed: %s", exc)
            return []

    def get_stats(self) -> dict:
        """Get summary counts for logging/debugging.

        Returns:
            Dict with table row counts.
        """
        if not self._client:
            return {}

        stats = {}
        for table in ("tenders", "tender_history", "tender_documents"):
            try:
                result = (
                    self._client.table(table)
                    .select("*", count="exact")
                    .limit(0)
                    .execute()
                )
                stats[table] = result.count if result.count is not None else 0
            except Exception as exc:
                logger.error("get_stats failed for %s: %s", table, exc)
                stats[table] = -1

        return stats
