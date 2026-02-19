"""
SQLite database layer for the Land Tenders Dashboard.

Provides persistent storage for tenders, historical snapshots, document
tracking, user watchlists, and alert history. Replaces JSON snapshot
files as the primary data source while keeping JSON as a backup.

Schema:
    tenders          — current state of each tender (upserted daily)
    tender_history   — daily snapshots for trend analysis
    tender_documents — per-tender document tracking (detect additions)
    tender_scores    — scoring results (Sprint 4, created but unused)
    user_watchlist   — per-user tender watchlist for email alerts
    alert_history    — sent notification log for deduplication

Usage:
    from db import TenderDB
    db = TenderDB()
    db.upsert_tenders(df, snapshot_date="2026-02-17")
    df = db.load_current_tenders()
"""

import logging
import sqlite3
from datetime import date, datetime
from pathlib import Path
from typing import Optional

import pandas as pd

from config import DB_PATH

logger = logging.getLogger(__name__)

# Column names expected in the tenders DataFrame (from normalize_api_columns).
TENDER_COLUMNS = [
    "tender_id", "tender_name", "city_code", "city", "region", "location",
    "tender_type_code", "tender_type", "purpose_code", "purpose",
    "status_code", "status", "units", "publish_date", "deadline",
    "committee_date", "published_booklet", "targeted",
    "area_sqm", "min_price", "gush", "helka",
]

# SQL statements -----------------------------------------------------------

_CREATE_TENDERS = """
CREATE TABLE IF NOT EXISTS tenders (
    tender_id        INTEGER PRIMARY KEY,
    tender_name      TEXT,
    city_code        INTEGER,
    city             TEXT,
    region           TEXT,
    location         TEXT,
    tender_type_code INTEGER,
    tender_type      TEXT,
    purpose_code     INTEGER,
    purpose          TEXT,
    status_code      INTEGER,
    status           TEXT,
    units            INTEGER,
    publish_date     TEXT,
    deadline         TEXT,
    committee_date   TEXT,
    published_booklet INTEGER,
    targeted         INTEGER,
    area_sqm         REAL,
    min_price        REAL,
    gush             TEXT,
    helka            TEXT,
    first_seen       TEXT,
    last_updated     TEXT
)
"""

_CREATE_HISTORY = """
CREATE TABLE IF NOT EXISTS tender_history (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    tender_id     INTEGER NOT NULL,
    snapshot_date TEXT NOT NULL,
    status_code   INTEGER,
    status        TEXT,
    units         INTEGER,
    deadline      TEXT,
    UNIQUE(tender_id, snapshot_date)
)
"""

_CREATE_DOCUMENTS = """
CREATE TABLE IF NOT EXISTS tender_documents (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    tender_id   INTEGER NOT NULL,
    row_id      INTEGER NOT NULL,
    doc_name    TEXT,
    description TEXT,
    file_type   TEXT,
    size        INTEGER,
    pirsum_type INTEGER,
    update_date TEXT,
    first_seen  TEXT,
    UNIQUE(tender_id, row_id)
)
"""

_CREATE_SCORES = """
CREATE TABLE IF NOT EXISTS tender_scores (
    tender_id   INTEGER PRIMARY KEY,
    total_score REAL,
    breakdown   TEXT,
    scored_at   TEXT
)
"""

_CREATE_WATCHLIST = """
CREATE TABLE IF NOT EXISTS user_watchlist (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_email  TEXT NOT NULL,
    tender_id   INTEGER NOT NULL,
    created_at  TEXT NOT NULL,
    active      INTEGER NOT NULL DEFAULT 1,
    UNIQUE(user_email, tender_id)
)
"""

_CREATE_ALERT_HISTORY = """
CREATE TABLE IF NOT EXISTS alert_history (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_email  TEXT NOT NULL,
    tender_id   INTEGER NOT NULL,
    doc_row_id  INTEGER NOT NULL,
    sent_at     TEXT NOT NULL,
    UNIQUE(user_email, tender_id, doc_row_id)
)
"""

_CREATE_REVIEWS = """
CREATE TABLE IF NOT EXISTS tender_reviews (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    tender_id   INTEGER NOT NULL UNIQUE,
    status      TEXT NOT NULL DEFAULT 'לא נסקר',
    updated_by  TEXT NOT NULL,
    updated_at  TEXT NOT NULL,
    notes       TEXT
)
"""

# Valid review stages (ordered)
REVIEW_STAGES: list[str] = [
    "לא נסקר",
    "סקירה ראשונית",
    "בדיקה מעמיקה",
    "הוצג בפורום",
    "אושר בפורום",
]

_CREATE_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_tenders_city ON tenders(city)",
    "CREATE INDEX IF NOT EXISTS idx_tenders_region ON tenders(region)",
    "CREATE INDEX IF NOT EXISTS idx_tenders_status ON tenders(status_code)",
    "CREATE INDEX IF NOT EXISTS idx_tenders_deadline ON tenders(deadline)",
    "CREATE INDEX IF NOT EXISTS idx_history_tender ON tender_history(tender_id)",
    "CREATE INDEX IF NOT EXISTS idx_history_date ON tender_history(snapshot_date)",
    "CREATE INDEX IF NOT EXISTS idx_docs_tender ON tender_documents(tender_id)",
    "CREATE INDEX IF NOT EXISTS idx_docs_first_seen ON tender_documents(first_seen)",
    "CREATE INDEX IF NOT EXISTS idx_watchlist_user ON user_watchlist(user_email)",
    "CREATE INDEX IF NOT EXISTS idx_watchlist_tender ON user_watchlist(tender_id)",
    "CREATE INDEX IF NOT EXISTS idx_alert_hist_user ON alert_history(user_email)",
    "CREATE INDEX IF NOT EXISTS idx_reviews_tender ON tender_reviews(tender_id)",
]


class TenderDB:
    """SQLite database for tender data persistence and history tracking."""

    def __init__(self, db_path: Optional[Path] = None) -> None:
        """Open (or create) the database and ensure all tables exist.

        Args:
            db_path: Path to the SQLite file. Defaults to config.DB_PATH.
        """
        self.db_path = db_path or DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()
        logger.debug("TenderDB ready at %s", self.db_path)

    # ------------------------------------------------------------------
    # Connection helper
    # ------------------------------------------------------------------

    def _connect(self) -> sqlite3.Connection:
        """Create a new connection with WAL mode and row factory."""
        conn = sqlite3.connect(str(self.db_path), timeout=10)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        """Create tables and indexes if they don't exist."""
        conn = self._connect()
        try:
            conn.execute(_CREATE_TENDERS)
            conn.execute(_CREATE_HISTORY)
            conn.execute(_CREATE_DOCUMENTS)
            conn.execute(_CREATE_SCORES)

            # Migrate: drop old empty alert_rules table if it exists
            conn.execute("DROP TABLE IF EXISTS alert_rules")

            # Migrate: recreate alert_history with new schema if needed
            col_check = conn.execute("PRAGMA table_info(alert_history)").fetchall()
            col_names = {r["name"] for r in col_check} if col_check else set()
            if col_check and "user_email" not in col_names:
                conn.execute("DROP TABLE IF EXISTS alert_history")

            conn.execute(_CREATE_WATCHLIST)
            conn.execute(_CREATE_ALERT_HISTORY)
            conn.execute(_CREATE_REVIEWS)
            for idx_sql in _CREATE_INDEXES:
                conn.execute(idx_sql)
            conn.commit()
        finally:
            conn.close()

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

        snapshot_date = snapshot_date or date.today().isoformat()
        now = datetime.now().isoformat()

        conn = self._connect()
        try:
            cursor = conn.cursor()
            inserted = 0
            updated = 0

            for _, row in df.iterrows():
                tender_id = int(row.get("tender_id", 0))
                if not tender_id:
                    continue

                # Check if tender exists to preserve first_seen
                existing = cursor.execute(
                    "SELECT first_seen FROM tenders WHERE tender_id = ?",
                    (tender_id,),
                ).fetchone()

                first_seen = existing["first_seen"] if existing else snapshot_date

                # Prepare values for all columns
                values = {
                    "tender_id": tender_id,
                    "tender_name": _to_str(row.get("tender_name")),
                    "city_code": _to_int(row.get("city_code")),
                    "city": _to_str(row.get("city")),
                    "region": _to_str(row.get("region")),
                    "location": _to_str(row.get("location")),
                    "tender_type_code": _to_int(row.get("tender_type_code")),
                    "tender_type": _to_str(row.get("tender_type")),
                    "purpose_code": _to_int(row.get("purpose_code")),
                    "purpose": _to_str(row.get("purpose")),
                    "status_code": _to_int(row.get("status_code")),
                    "status": _to_str(row.get("status")),
                    "units": _to_int(row.get("units")),
                    "publish_date": _to_date_str(row.get("publish_date")),
                    "deadline": _to_date_str(row.get("deadline")),
                    "committee_date": _to_date_str(row.get("committee_date")),
                    "published_booklet": _to_int(row.get("published_booklet")),
                    "targeted": _to_int(row.get("targeted")),
                    "area_sqm": _to_float(row.get("area_sqm")),
                    "min_price": _to_float(row.get("min_price")),
                    "gush": _to_str(row.get("gush")),
                    "helka": _to_str(row.get("helka")),
                    "first_seen": first_seen,
                    "last_updated": now,
                }

                cursor.execute(
                    """INSERT OR REPLACE INTO tenders (
                        tender_id, tender_name, city_code, city, region,
                        location, tender_type_code, tender_type, purpose_code,
                        purpose, status_code, status, units, publish_date,
                        deadline, committee_date, published_booklet, targeted,
                        area_sqm, min_price, gush, helka, first_seen, last_updated
                    ) VALUES (
                        :tender_id, :tender_name, :city_code, :city, :region,
                        :location, :tender_type_code, :tender_type, :purpose_code,
                        :purpose, :status_code, :status, :units, :publish_date,
                        :deadline, :committee_date, :published_booklet, :targeted,
                        :area_sqm, :min_price, :gush, :helka, :first_seen,
                        :last_updated
                    )""",
                    values,
                )

                if existing:
                    updated += 1
                else:
                    inserted += 1

                # Write history row (ignore duplicates for same date)
                cursor.execute(
                    """INSERT OR IGNORE INTO tender_history
                       (tender_id, snapshot_date, status_code, status, units, deadline)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (
                        tender_id,
                        snapshot_date,
                        _to_int(row.get("status_code")),
                        _to_str(row.get("status")),
                        _to_int(row.get("units")),
                        _to_date_str(row.get("deadline")),
                    ),
                )

            conn.commit()
            logger.info(
                "Upserted tenders: %d inserted, %d updated (snapshot %s)",
                inserted, updated, snapshot_date,
            )
        finally:
            conn.close()

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
            List of document dicts that were newly inserted (first_seen == today).
        """
        if not doc_list:
            return []

        today = date.today().isoformat()
        conn = self._connect()
        new_docs: list[dict] = []

        try:
            cursor = conn.cursor()

            for doc in doc_list:
                row_id = doc.get("RowID")
                if row_id is None:
                    continue

                # Check if this doc already exists
                existing = cursor.execute(
                    "SELECT id FROM tender_documents WHERE tender_id = ? AND row_id = ?",
                    (tender_id, row_id),
                ).fetchone()

                if existing:
                    continue

                update_date = _to_date_str(doc.get("UpdateDate"))

                cursor.execute(
                    """INSERT INTO tender_documents
                       (tender_id, row_id, doc_name, description, file_type,
                        size, pirsum_type, update_date, first_seen)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        tender_id,
                        row_id,
                        doc.get("DocName"),
                        doc.get("Teur"),
                        doc.get("FileType"),
                        doc.get("Size"),
                        doc.get("PirsumType"),
                        update_date,
                        today,
                    ),
                )
                new_docs.append(doc)

            conn.commit()

            if new_docs:
                logger.info(
                    "Tender %d: %d new documents added", tender_id, len(new_docs),
                )
        finally:
            conn.close()

        return new_docs

    # ------------------------------------------------------------------
    # Query methods
    # ------------------------------------------------------------------

    def load_current_tenders(self) -> pd.DataFrame:
        """Load all tenders from the database as a DataFrame."""
        conn = self._connect()
        try:
            df = pd.read_sql_query("SELECT * FROM tenders", conn)
            logger.info("Loaded %d tenders from database", len(df))

            # Convert date columns to datetime
            for col in ("publish_date", "deadline", "committee_date"):
                if col in df.columns:
                    df[col] = pd.to_datetime(df[col], errors="coerce")

            # Convert boolean-like columns
            if "published_booklet" in df.columns:
                df["published_booklet"] = df["published_booklet"].astype(bool)

            return df
        finally:
            conn.close()

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
        conn = self._connect()
        try:
            if tender_id is not None:
                df = pd.read_sql_query(
                    "SELECT * FROM tender_history WHERE tender_id = ? ORDER BY snapshot_date",
                    conn,
                    params=(tender_id,),
                )
            else:
                df = pd.read_sql_query(
                    "SELECT * FROM tender_history ORDER BY snapshot_date",
                    conn,
                )
            return df
        finally:
            conn.close()

    def load_tender_documents(self, tender_id: int) -> pd.DataFrame:
        """Load all documents for a specific tender.

        Args:
            tender_id: The tender's MichrazID.

        Returns:
            DataFrame with document rows.
        """
        conn = self._connect()
        try:
            df = pd.read_sql_query(
                "SELECT * FROM tender_documents WHERE tender_id = ? ORDER BY update_date",
                conn,
                params=(tender_id,),
            )
            return df
        finally:
            conn.close()

    def get_new_documents(self, since_date: str) -> pd.DataFrame:
        """Get all documents first seen after a given date.

        Args:
            since_date: ISO date string (e.g. "2026-02-16").

        Returns:
            DataFrame with document rows, joined with tender name.
        """
        conn = self._connect()
        try:
            df = pd.read_sql_query(
                """SELECT d.*, t.tender_name, t.city, t.region
                   FROM tender_documents d
                   JOIN tenders t ON d.tender_id = t.tender_id
                   WHERE d.first_seen > ?
                   ORDER BY d.first_seen DESC""",
                conn,
                params=(since_date,),
            )
            return df
        finally:
            conn.close()

    def get_tender_by_id(self, tender_id: int) -> Optional[dict]:
        """Look up a single tender by ID.

        Args:
            tender_id: The tender's MichrazID.

        Returns:
            Dict of tender fields, or None if not found.
        """
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT * FROM tenders WHERE tender_id = ?",
                (tender_id,),
            ).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def get_snapshot_dates(self) -> list[str]:
        """List all unique snapshot dates in the history table.

        Returns:
            Sorted list of ISO date strings.
        """
        conn = self._connect()
        try:
            rows = conn.execute(
                "SELECT DISTINCT snapshot_date FROM tender_history ORDER BY snapshot_date",
            ).fetchall()
            return [r["snapshot_date"] for r in rows]
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Watchlist methods
    # ------------------------------------------------------------------

    def add_to_watchlist(self, user_email: str, tender_id: int) -> bool:
        """Add a tender to the user's watchlist.

        Args:
            user_email: The user's email address.
            tender_id: The tender's MichrazID (must exist in tenders table).

        Returns:
            True if added, False if already on the watchlist.
        """
        conn = self._connect()
        try:
            conn.execute(
                """INSERT OR IGNORE INTO user_watchlist
                   (user_email, tender_id, created_at, active)
                   VALUES (?, ?, ?, 1)""",
                (user_email, tender_id, date.today().isoformat()),
            )
            conn.commit()
            return conn.total_changes > 0
        finally:
            conn.close()

    def remove_from_watchlist(self, user_email: str, tender_id: int) -> None:
        """Remove a tender from the user's watchlist.

        Args:
            user_email: The user's email address.
            tender_id: The tender's MichrazID.
        """
        conn = self._connect()
        try:
            conn.execute(
                "DELETE FROM user_watchlist WHERE user_email = ? AND tender_id = ?",
                (user_email, tender_id),
            )
            conn.commit()
        finally:
            conn.close()

    def get_user_watchlist(self, user_email: str) -> pd.DataFrame:
        """Get all watched tenders for a user, joined with tender details.

        Args:
            user_email: The user's email address.

        Returns:
            DataFrame with watchlist entries joined to tender info.
        """
        conn = self._connect()
        try:
            df = pd.read_sql_query(
                """SELECT w.id AS watch_id, w.tender_id, w.created_at,
                          t.tender_name, t.city, t.region, t.status,
                          t.deadline, t.units, t.published_booklet,
                          t.tender_type
                   FROM user_watchlist w
                   JOIN tenders t ON w.tender_id = t.tender_id
                   WHERE w.user_email = ? AND w.active = 1
                   ORDER BY w.created_at DESC""",
                conn,
                params=(user_email,),
            )
            return df
        finally:
            conn.close()

    def get_all_active_watchlists(self) -> list[dict]:
        """Get all active watchlist entries grouped by user_email.

        Returns:
            List of dicts: [{user_email, tender_id, created_at}, ...].
        """
        conn = self._connect()
        try:
            rows = conn.execute(
                """SELECT user_email, tender_id, created_at
                   FROM user_watchlist
                   WHERE active = 1
                   ORDER BY user_email""",
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Alert history methods
    # ------------------------------------------------------------------

    def record_alert_sent(
        self, user_email: str, tender_id: int, doc_row_id: int,
    ) -> None:
        """Record that an alert email was sent for a document.

        Uses INSERT OR IGNORE for deduplication — safe to call multiple times.

        Args:
            user_email: Recipient email.
            tender_id: The tender's MichrazID.
            doc_row_id: The document's RowID from the API.
        """
        conn = self._connect()
        try:
            conn.execute(
                """INSERT OR IGNORE INTO alert_history
                   (user_email, tender_id, doc_row_id, sent_at)
                   VALUES (?, ?, ?, ?)""",
                (user_email, tender_id, doc_row_id, date.today().isoformat()),
            )
            conn.commit()
        finally:
            conn.close()

    def get_unsent_docs_for_watch(
        self,
        user_email: str,
        tender_id: int,
        since_date: str,
    ) -> list[dict]:
        """Find new documents for a watched tender not yet emailed to this user.

        Args:
            user_email: The user's email.
            tender_id: The watched tender ID.
            since_date: Only consider documents with first_seen > this date
                (typically the watchlist created_at date).

        Returns:
            List of document dicts with keys: row_id, doc_name, description,
            file_type, size, pirsum_type, update_date, first_seen.
        """
        conn = self._connect()
        try:
            rows = conn.execute(
                """SELECT d.row_id, d.doc_name, d.description, d.file_type,
                          d.size, d.pirsum_type, d.update_date, d.first_seen
                   FROM tender_documents d
                   WHERE d.tender_id = ?
                     AND d.first_seen > ?
                     AND NOT EXISTS (
                         SELECT 1 FROM alert_history ah
                         WHERE ah.user_email = ?
                           AND ah.tender_id = d.tender_id
                           AND ah.doc_row_id = d.row_id
                     )
                   ORDER BY d.first_seen DESC""",
                (tender_id, since_date, user_email),
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Review status methods
    # ------------------------------------------------------------------

    def get_review_status(self, tender_id: int) -> Optional[dict]:
        """Get the current review status for a tender.

        Args:
            tender_id: The tender's MichrazID.

        Returns:
            Dict with status, updated_by, updated_at, notes — or None.
        """
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT * FROM tender_reviews WHERE tender_id = ?",
                (tender_id,),
            ).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def set_review_status(
        self,
        tender_id: int,
        status: str,
        updated_by: str,
        notes: Optional[str] = None,
    ) -> str:
        """Set or update the review status for a tender.

        Args:
            tender_id: The tender's MichrazID.
            status: One of REVIEW_STAGES.
            updated_by: Email or name of the person updating.
            notes: Optional free-text notes.

        Returns:
            The previous status (for notification purposes), or empty string.
        """
        now = datetime.now().isoformat(timespec="seconds")
        conn = self._connect()
        try:
            # Get previous status
            prev_row = conn.execute(
                "SELECT status FROM tender_reviews WHERE tender_id = ?",
                (tender_id,),
            ).fetchone()
            prev_status = prev_row["status"] if prev_row else ""

            conn.execute(
                """INSERT INTO tender_reviews (tender_id, status, updated_by, updated_at, notes)
                   VALUES (?, ?, ?, ?, ?)
                   ON CONFLICT(tender_id)
                   DO UPDATE SET status = excluded.status,
                                 updated_by = excluded.updated_by,
                                 updated_at = excluded.updated_at,
                                 notes = excluded.notes""",
                (tender_id, status, updated_by, now, notes),
            )
            conn.commit()
            return prev_status
        finally:
            conn.close()

    def get_review_statuses_for_tenders(
        self, tender_ids: list[int],
    ) -> dict[int, dict]:
        """Bulk-fetch review statuses for a list of tender IDs.

        Args:
            tender_ids: List of tender MichrazIDs.

        Returns:
            Dict mapping tender_id → review dict (status, updated_by, etc.).
        """
        if not tender_ids:
            return {}
        conn = self._connect()
        try:
            placeholders = ",".join("?" * len(tender_ids))
            rows = conn.execute(
                f"SELECT * FROM tender_reviews WHERE tender_id IN ({placeholders})",  # noqa: S608
                tender_ids,
            ).fetchall()
            return {r["tender_id"]: dict(r) for r in rows}
        finally:
            conn.close()

    def get_new_docs_excluding(
        self,
        tender_id: int,
        since_date: str,
        exclude_row_ids: set[int],
    ) -> list[dict]:
        """Get new documents for a tender, excluding already-notified ones.

        Used by the alert engine when alert_history lives in Supabase.

        Args:
            tender_id: The tender's MichrazID.
            since_date: Only docs with first_seen > this date.
            exclude_row_ids: Set of row_ids already sent to this user.

        Returns:
            List of document dicts not yet notified.
        """
        conn = self._connect()
        try:
            rows = conn.execute(
                """SELECT row_id, doc_name, description, file_type,
                          size, pirsum_type, update_date, first_seen
                   FROM tender_documents
                   WHERE tender_id = ? AND first_seen > ?
                   ORDER BY first_seen DESC""",
                (tender_id, since_date),
            ).fetchall()
            return [
                dict(r) for r in rows
                if r["row_id"] not in exclude_row_ids
            ]
        finally:
            conn.close()

    def get_stats(self) -> dict:
        """Get summary counts for logging/debugging.

        Returns:
            Dict with table row counts.
        """
        conn = self._connect()
        try:
            stats = {}
            for table in (
                "tenders", "tender_history", "tender_documents",
                "user_watchlist", "alert_history", "tender_reviews",
            ):
                count = conn.execute(
                    f"SELECT COUNT(*) FROM {table}",  # noqa: S608
                ).fetchone()[0]
                stats[table] = count
            return stats
        finally:
            conn.close()


# ------------------------------------------------------------------
# Type conversion helpers
# ------------------------------------------------------------------

def _to_str(val: object) -> Optional[str]:
    """Convert a value to string, handling NaN/None."""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    return str(val).strip() if val else None


def _to_int(val: object) -> Optional[int]:
    """Convert a value to int, handling NaN/None/bool."""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    if isinstance(val, bool):
        return int(val)
    try:
        return int(val)
    except (ValueError, TypeError):
        return None


def _to_float(val: object) -> Optional[float]:
    """Convert a value to float, handling NaN/None."""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def _to_date_str(val: object) -> Optional[str]:
    """Convert a date/datetime/string to ISO date string."""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    if isinstance(val, (pd.Timestamp, datetime)):
        return val.isoformat()
    s = str(val).strip()
    return s if s else None
