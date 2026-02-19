"""
Supabase-backed persistent storage for user data.

Handles the three tables that must survive app redeploys:
  - user_watchlist    (per-user tender watchlist)
  - tender_reviews    (shared team review status)
  - alert_history     (deduplication for email alerts)

Tender data itself stays in local SQLite (db.py).

Usage:
    from user_db import UserDB
    udb = UserDB()
    udb.add_to_watchlist("user@example.com", 20240339)
"""

import logging
from datetime import date, datetime
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)

# Valid review stages (ordered) — kept in sync with db.py
REVIEW_STAGES: list[str] = [
    "לא נסקר",
    "סקירה ראשונית",
    "בדיקה מעמיקה",
    "הוצג בפורום",
    "אושר בפורום",
]


def _get_client():
    """Return a Supabase client or None if credentials are not configured."""
    try:
        from supabase import create_client

        from config import SUPABASE_KEY, SUPABASE_URL

        if not SUPABASE_URL or not SUPABASE_KEY:
            logger.warning("Supabase credentials not set — user data won't persist")
            return None
        return create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as exc:
        logger.warning("Supabase unavailable: %s", exc)
        return None


class UserDB:
    """Persistent user data storage backed by Supabase PostgreSQL.

    Falls back to no-ops if Supabase is not configured (app still runs,
    watchlist/reviews just don't persist across sessions).
    """

    def __init__(self) -> None:
        self._client = _get_client()
        if self._client:
            logger.info("UserDB connected to Supabase")
        else:
            logger.warning("UserDB: no Supabase connection — watchlist/reviews are session-only")

    @property
    def available(self) -> bool:
        """True if Supabase is connected and writes will persist."""
        return self._client is not None

    # ------------------------------------------------------------------
    # Watchlist
    # ------------------------------------------------------------------

    def add_to_watchlist(self, user_email: str, tender_id: int) -> bool:
        """Add a tender to the user's watchlist.

        Args:
            user_email: The user's email (lowercased for consistency).
            tender_id: The tender's MichrazID.

        Returns:
            True if added, False if already on the watchlist.
        """
        if not self._client:
            return False
        email = user_email.lower().strip()
        try:
            result = (
                self._client.table("user_watchlist")
                .upsert(
                    {
                        "user_email": email,
                        "tender_id": tender_id,
                        "created_at": date.today().isoformat(),
                        "active": 1,
                    },
                    on_conflict="user_email,tender_id",
                    ignore_duplicates=True,
                )
                .execute()
            )
            return bool(result.data)
        except Exception as exc:
            logger.error("add_to_watchlist failed: %s", exc)
            return False

    def remove_from_watchlist(self, user_email: str, tender_id: int) -> None:
        """Remove a tender from the user's watchlist.

        Args:
            user_email: The user's email.
            tender_id: The tender's MichrazID.
        """
        if not self._client:
            return
        email = user_email.lower().strip()
        try:
            (
                self._client.table("user_watchlist")
                .delete()
                .eq("user_email", email)
                .eq("tender_id", tender_id)
                .execute()
            )
        except Exception as exc:
            logger.error("remove_from_watchlist failed: %s", exc)

    def get_watchlist_ids(self, user_email: str) -> list[int]:
        """Return list of watched tender IDs for this user.

        Args:
            user_email: The user's email.

        Returns:
            List of tender IDs, or empty list on error.
        """
        if not self._client:
            return []
        email = user_email.lower().strip()
        try:
            result = (
                self._client.table("user_watchlist")
                .select("tender_id, id, created_at")
                .eq("user_email", email)
                .eq("active", 1)
                .execute()
            )
            return [row["tender_id"] for row in (result.data or [])]
        except Exception as exc:
            logger.error("get_watchlist_ids failed: %s", exc)
            return []

    def get_watchlist_rows(self, user_email: str) -> list[dict]:
        """Return watchlist rows (id, tender_id, created_at) for this user.

        Args:
            user_email: The user's email.

        Returns:
            List of dicts with watchlist metadata.
        """
        if not self._client:
            return []
        email = user_email.lower().strip()
        try:
            result = (
                self._client.table("user_watchlist")
                .select("id, tender_id, created_at")
                .eq("user_email", email)
                .eq("active", 1)
                .order("created_at", desc=True)
                .execute()
            )
            return result.data or []
        except Exception as exc:
            logger.error("get_watchlist_rows failed: %s", exc)
            return []

    def get_all_active_watchlists(self) -> list[dict]:
        """Return all active watchlist entries (for the alert cron).

        Returns:
            List of dicts: {user_email, tender_id, created_at}.
        """
        if not self._client:
            return []
        try:
            result = (
                self._client.table("user_watchlist")
                .select("user_email, tender_id, created_at")
                .eq("active", 1)
                .execute()
            )
            return result.data or []
        except Exception as exc:
            logger.error("get_all_active_watchlists failed: %s", exc)
            return []

    # ------------------------------------------------------------------
    # Alert history
    # ------------------------------------------------------------------

    def record_alert_sent(
        self, user_email: str, tender_id: int, doc_row_id: int,
    ) -> None:
        """Record that an alert email was sent for a document.

        Args:
            user_email: Recipient email.
            tender_id: The tender's MichrazID.
            doc_row_id: The document's RowID from the API.
        """
        if not self._client:
            return
        email = user_email.lower().strip()
        try:
            (
                self._client.table("alert_history")
                .upsert(
                    {
                        "user_email": email,
                        "tender_id": tender_id,
                        "doc_row_id": doc_row_id,
                        "sent_at": date.today().isoformat(),
                    },
                    on_conflict="user_email,tender_id,doc_row_id",
                    ignore_duplicates=True,
                )
                .execute()
            )
        except Exception as exc:
            logger.error("record_alert_sent failed: %s", exc)

    def get_sent_doc_ids(self, user_email: str, tender_id: int) -> set[int]:
        """Get all doc_row_ids already sent to this user for this tender.

        Args:
            user_email: The user's email.
            tender_id: The tender's MichrazID.

        Returns:
            Set of doc_row_ids already notified.
        """
        if not self._client:
            return set()
        email = user_email.lower().strip()
        try:
            result = (
                self._client.table("alert_history")
                .select("doc_row_id")
                .eq("user_email", email)
                .eq("tender_id", tender_id)
                .execute()
            )
            return {row["doc_row_id"] for row in (result.data or [])}
        except Exception as exc:
            logger.error("get_sent_doc_ids failed: %s", exc)
            return set()

    # ------------------------------------------------------------------
    # Review status
    # ------------------------------------------------------------------

    def get_review_status(self, tender_id: int) -> Optional[dict]:
        """Get the current review status for a tender.

        Args:
            tender_id: The tender's MichrazID.

        Returns:
            Dict with status, updated_by, updated_at, notes — or None.
        """
        if not self._client:
            return None
        try:
            result = (
                self._client.table("tender_reviews")
                .select("*")
                .eq("tender_id", tender_id)
                .execute()
            )
            rows = result.data or []
            return rows[0] if rows else None
        except Exception as exc:
            logger.error("get_review_status failed: %s", exc)
            return None

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
            Previous status string, or empty string if new.
        """
        if not self._client:
            return ""
        now = datetime.now().isoformat(timespec="seconds")
        try:
            # Get previous status
            prev = self.get_review_status(tender_id)
            prev_status = prev.get("status", "") if prev else ""

            (
                self._client.table("tender_reviews")
                .upsert(
                    {
                        "tender_id": tender_id,
                        "status": status,
                        "updated_by": updated_by,
                        "updated_at": now,
                        "notes": notes or "",
                    },
                    on_conflict="tender_id",
                )
                .execute()
            )
            return prev_status
        except Exception as exc:
            logger.error("set_review_status failed: %s", exc)
            return ""

    def get_review_statuses_for_tenders(
        self, tender_ids: list[int],
    ) -> dict[int, dict]:
        """Bulk-fetch review statuses for a list of tender IDs.

        Args:
            tender_ids: List of tender MichrazIDs.

        Returns:
            Dict mapping tender_id → review dict.
        """
        if not self._client or not tender_ids:
            return {}
        try:
            result = (
                self._client.table("tender_reviews")
                .select("*")
                .in_("tender_id", tender_ids)
                .execute()
            )
            return {row["tender_id"]: row for row in (result.data or [])}
        except Exception as exc:
            logger.error("get_review_statuses_for_tenders failed: %s", exc)
            return {}
