"""
Supabase database layer for the Land Tenders Dashboard.

Provides persistent storage for tenders, historical snapshots, and document
tracking via Supabase PostgreSQL. Replaces the original SQLite implementation
(Sprint 6 migration).

Tables managed by this module:
    tenders          — current state of each tender (upserted daily)
    tender_history   — daily snapshots for trend analysis
    tender_documents — per-tender document tracking (detect additions)
    building_rights  — extracted building rights from Mavat plan PDFs

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

    def update_plan_number(self, tender_id: int, plan_number: str) -> bool:
        """Store an extracted plan number (תב"ע) on a tender.

        Args:
            tender_id: The tender's MichrazID.
            plan_number: The תב"ע plan number string.

        Returns:
            True if the update succeeded.
        """
        if not self._client or not plan_number:
            return False

        try:
            self._client.table("tenders").update(
                {"plan_number": plan_number}
            ).eq("tender_id", tender_id).execute()
            logger.info("Stored plan_number=%s for tender %d", plan_number, tender_id)
            return True
        except Exception as exc:
            logger.error("update_plan_number failed for tender %d: %s", tender_id, exc)
            return False

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
        for table in ("tenders", "tender_history", "tender_documents", "building_rights"):
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

    # ------------------------------------------------------------------
    # Building rights (Section 5 from Mavat plan PDFs)
    # ------------------------------------------------------------------

    # Columns stored in typed fields. Anything else goes into extra_data JSONB.
    _BUILDING_RIGHTS_TYPED_COLS = {
        "designation", "use_type", "area_condition",
        "plot_size_absolute", "plot_size_minimum",
        "building_area_above", "building_area_above_service",
        "building_area_below", "building_area_below_service",
        "building_area_total",
        "coverage_pct", "housing_units", "building_height",
        "floors_above", "floors_below",
        "setback_rear", "setback_front", "setback_side",
        "balcony_area",
    }

    # Columns typed as INT in the schema — must cast float → int.
    _BUILDING_RIGHTS_INT_COLS = {"housing_units", "floors_above", "floors_below"}

    # Maps extractor field names → Supabase column names.
    _RIGHTS_FIELD_MAP = {
        "designation": "designation",
        "use": "use_type",
        "area_condition": "area_condition",
        "plot_size_absolute": "plot_size_absolute",
        "plot_size_minimum": "plot_size_minimum",
        "building_area_above_main": "building_area_above",
        "building_area_above_service": "building_area_above_service",
        "building_area_below_main": "building_area_below",
        "building_area_below_service": "building_area_below_service",
        "building_area_total": "building_area_total",
        "coverage_pct": "coverage_pct",
        "housing_units": "housing_units",
        "building_height": "building_height",
        "floors_above": "floors_above",
        "floors_below": "floors_below",
        "setback_rear": "setback_rear",
        "setback_front": "setback_front",
        "setback_side": "setback_side",
        "balcony_area": "balcony_area",
    }

    def upsert_building_rights(
        self,
        plan_number: str,
        rows: list[dict],
        plan_status: Optional[str] = None,
    ) -> int:
        """Insert or update building rights rows for a plan.

        Maps extractor field names to Supabase column names. Fields not
        in the schema are stored in the extra_data JSONB column.

        Args:
            plan_number: The plan number (e.g. "606-0458471").
            rows: List of row dicts from building_rights_extractor.
            plan_status: "מצב מוצע" or "מצב מאושר".

        Returns:
            Number of rows upserted.
        """
        if not rows or not self._client:
            return 0

        db_rows: list[dict] = []
        for idx, row in enumerate(rows):
            db_row: dict = {
                "plan_number": plan_number,
                "plan_status": plan_status,
                "row_index": idx,
            }

            extra: dict = {}
            for src_field, value in row.items():
                if src_field.startswith("_"):
                    continue
                db_col = self._RIGHTS_FIELD_MAP.get(src_field)
                if db_col:
                    cleaned = _clean_val(value)
                    # Cast float → int for INT columns (e.g. 3.0 → 3)
                    if (
                        db_col in self._BUILDING_RIGHTS_INT_COLS
                        and isinstance(cleaned, float)
                    ):
                        cleaned = int(cleaned)
                    db_row[db_col] = cleaned
                else:
                    extra[src_field] = _clean_val(value)

            if extra:
                db_row["extra_data"] = extra

            db_rows.append(db_row)

        # Batch upsert
        inserted = 0
        for i in range(0, len(db_rows), _BATCH_SIZE):
            batch = db_rows[i : i + _BATCH_SIZE]
            try:
                self._client.table("building_rights").upsert(
                    batch,
                    on_conflict="plan_number,plan_status,row_index",
                ).execute()
                inserted += len(batch)
            except Exception as exc:
                logger.error(
                    "upsert_building_rights failed for %s: %s",
                    plan_number, exc,
                )

        if inserted:
            logger.info(
                "Upserted %d building rights rows for plan %s (%s)",
                inserted, plan_number, plan_status,
            )
        return inserted

    def load_building_rights(
        self,
        plan_number: str,
        plan_status: Optional[str] = None,
    ) -> list[dict]:
        """Load building rights rows for a plan.

        Args:
            plan_number: The plan number.
            plan_status: Optional filter by status.

        Returns:
            List of row dicts ordered by row_index.
        """
        filters: dict = {"plan_number": plan_number}
        if plan_status:
            filters["plan_status"] = plan_status

        return self._paginated_select(
            "building_rights",
            filters=filters,
            order_col="row_index",
        )

    # ------------------------------------------------------------------
    # Brochure analysis & extraction pipeline status
    # ------------------------------------------------------------------

    def update_brochure_data(
        self,
        tender_id: int,
        plan_number: Optional[str],
        lots_data: dict,
        brochure_summary: str,
        extraction_status: str = "brochure_extracted",
    ) -> bool:
        """Store brochure extraction results on the tender record.

        Args:
            tender_id: The tender's MichrazID.
            plan_number: The תב"ע plan number (may be None).
            lots_data: Structured plot data from TenderPDFExtractor.
            brochure_summary: Text summary of the brochure.
            extraction_status: Pipeline status to set.

        Returns:
            True if the update succeeded.
        """
        if not self._client:
            return False

        import json as _json

        update_data: dict = {
            "brochure_summary": brochure_summary or None,
            "lots_data": _json.loads(_json.dumps(lots_data, default=str)) if lots_data else {},
            "extraction_status": extraction_status,
            "extraction_error": None,
        }
        if plan_number:
            update_data["plan_number"] = plan_number

        try:
            self._client.table("tenders").update(
                update_data,
            ).eq("tender_id", tender_id).execute()
            logger.info(
                "Stored brochure data for tender %d (status=%s, plan=%s)",
                tender_id, extraction_status, plan_number,
            )
            return True
        except Exception as exc:
            logger.error("update_brochure_data failed for tender %d: %s", tender_id, exc)
            return False

    def set_extraction_status(
        self,
        tender_id: int,
        status: str,
        error: Optional[str] = None,
    ) -> bool:
        """Update the building rights extraction pipeline status.

        Args:
            tender_id: The tender's MichrazID.
            status: One of 'none', 'brochure_extracted', 'queued',
                'complete', 'failed'.
            error: Error message (for 'failed' status).

        Returns:
            True if the update succeeded.
        """
        if not self._client:
            return False

        update_data: dict = {"extraction_status": status}
        if error is not None:
            update_data["extraction_error"] = error
        elif status != "failed":
            update_data["extraction_error"] = None

        try:
            self._client.table("tenders").update(
                update_data,
            ).eq("tender_id", tender_id).execute()
            logger.info("Set extraction_status=%s for tender %d", status, tender_id)
            return True
        except Exception as exc:
            logger.error("set_extraction_status failed for tender %d: %s", tender_id, exc)
            return False

    def get_pending_extractions(self) -> list[dict]:
        """Get tenders queued for building rights extraction.

        Returns tenders where extraction_status == 'queued' and
        plan_number is set.

        Returns:
            List of tender dicts with tender_id and plan_number.
        """
        if not self._client:
            return []

        try:
            result = (
                self._client.table("tenders")
                .select("tender_id, plan_number, extraction_status")
                .eq("extraction_status", "queued")
                .not_.is_("plan_number", "null")
                .execute()
            )
            rows = result.data or []
            logger.info("Found %d tenders queued for extraction", len(rows))
            return rows
        except Exception as exc:
            logger.error("get_pending_extractions failed: %s", exc)
            return []
