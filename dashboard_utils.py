"""
Shared utility functions for the Streamlit dashboard pages.

Contains data loading functions, chart constants, and snapshot comparison
helpers used by both the main dashboard and the management overview pages.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set

import pandas as pd
import streamlit as st

from config import CACHE_TTL, DATA_DIR, DEV_USER_EMAIL, PROJECT_ROOT
from data_client import LandTendersClient, generate_sample_data

logger = logging.getLogger(__name__)

# ── Shared chart styling constants ───────────────────────────────────────────
MEGIDO_CHART_COLORS: list[str] = [
    "#2563EB", "#60A5FA", "#1E3A5F", "#10B981", "#F59E0B", "#8B5CF6",
]
MEGIDO_GOLD_SCALE: list[list] = [[0, "#DBEAFE"], [1, "#2563EB"]]
PLOTLY_FONT: dict = dict(family="Inter, Heebo, sans-serif", size=11, color="#1E293B")
PLOTLY_BG: dict = dict(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")


def filter_active(df: pd.DataFrame) -> pd.DataFrame:
    """Return only tenders with a future deadline (open for bidding).

    The RMI website defines "active" as having a SgiraDate (deadline) that
    hasn't passed yet.  Status-code 3 ("פעיל") actually means the contract
    is awarded/running and all such tenders have past deadlines, so the old
    status-based filter was wrong.

    Args:
        df: DataFrame with a 'deadline' column.

    Returns:
        Filtered copy containing only future-deadline tenders.
    """
    if df.empty or "deadline" not in df.columns:
        return df.copy()
    deadlines = pd.to_datetime(df["deadline"], utc=True, errors="coerce")
    now = pd.Timestamp.now(tz="UTC")
    return df[deadlines > now].copy()


def _add_days_to_deadline(df: pd.DataFrame) -> pd.DataFrame:
    """Add computed days_to_deadline column to a tenders DataFrame.

    Calculates the number of calendar days from today to each tender's
    deadline. Negative values mean the deadline has passed.

    Args:
        df: DataFrame with a 'deadline' column (datetime or parseable).

    Returns:
        The same DataFrame with a new 'days_to_deadline' column added.
    """
    if df.empty or "deadline" not in df.columns:
        return df

    df = df.copy()
    now = pd.Timestamp(datetime.now())
    deadline_dt = pd.to_datetime(df["deadline"], errors="coerce")
    df["days_to_deadline"] = (deadline_dt - now).dt.days
    return df


@st.cache_data(ttl=CACHE_TTL)
def load_data(data_source: str = "latest_file") -> pd.DataFrame:
    """Load tender data from Supabase DB, JSON file, or API (with fallbacks).

    Args:
        data_source: One of "latest_file", "sample". Controls fallback chain.

    Returns:
        DataFrame of tenders with normalized columns.
    """
    if data_source == "sample":
        return _add_days_to_deadline(generate_sample_data())

    # Priority 1: Supabase database
    try:
        from db import TenderDB

        db = TenderDB()
        df = db.load_current_tenders()
        if len(df) > 0:
            return _add_days_to_deadline(df)
        logger.info("Database is empty, trying JSON fallback")
    except Exception as exc:
        logger.warning("Could not load from database: %s", exc)

    # Priority 2: JSON snapshot file
    client = LandTendersClient(data_dir=str(PROJECT_ROOT))
    if data_source == "latest_file":
        df = client.load_latest_json_snapshot()
        if df is not None:
            return _add_days_to_deadline(df)
        logger.warning("No JSON files found, fetching from API")
        st.warning("לא נמצאו קבצי JSON, טוען מהAPI...")

    # Priority 3: Live API call
    df = client.fetch_tenders_list()
    if df is None:
        logger.error("Could not fetch from API, falling back to sample data")
        st.error("לא ניתן לטעון מהAPI. מציג נתונים לדוגמה.")
        return _add_days_to_deadline(generate_sample_data())

    client.save_json_snapshot(df)
    return _add_days_to_deadline(df)


@st.cache_data(ttl=CACHE_TTL)
def load_tender_details(tender_id: int) -> Optional[Dict]:
    """Load tender details with caching.

    Args:
        tender_id: The tender's MichrazID.

    Returns:
        Dict of tender details from the API, or None if not found.
    """
    client = LandTendersClient(data_dir=str(DATA_DIR))
    return client.get_tender_details_cached(tender_id)


def render_email_input() -> None:
    """Render the sidebar email input widget (call ONCE per page).

    Must be called before any calls to get_user_email() so that
    the user has a way to identify themselves when Streamlit Cloud
    auth is not available.
    """
    if "user_email" not in st.session_state:
        st.session_state["user_email"] = DEV_USER_EMAIL or ""

    if not st.session_state["user_email"]:
        # Check Streamlit Cloud auth first — skip widget if authenticated
        for attr in ("user", "experimental_user"):
            try:
                user_info = getattr(st, attr, None)
                if user_info is not None:
                    email = getattr(user_info, "email", "") or ""
                    if not email:
                        email = user_info.get("email", "") if hasattr(user_info, "get") else ""
                    if email:
                        st.session_state["user_email"] = email
                        return
            except Exception:
                pass

        with st.sidebar:
            st.markdown("---")
            entered = st.text_input(
                "📧 הזן כתובת מייל לזיהוי",
                placeholder="your.name@company.co.il",
                key="_email_input",
            )
            if entered and "@" in entered:
                st.session_state["user_email"] = entered.strip()
                st.rerun()


@st.cache_data(ttl=300)
def load_building_rights_data(tender_id: int) -> dict:
    """Load building rights and brochure data for a tender.

    Checks the tender record for extraction_status, plan_number,
    brochure_summary, and lots_data. If building rights exist in the
    building_rights table, loads those too.

    Args:
        tender_id: The tender's MichrazID.

    Returns:
        Dict with keys: extraction_status, plan_number, brochure_summary,
        lots_data, building_rights, extraction_error.
    """
    from db import TenderDB

    result = {
        "extraction_status": "none",
        "plan_number": None,
        "brochure_summary": None,
        "lots_data": None,
        "building_rights": [],
        "extraction_error": None,
    }

    try:
        db = TenderDB()
        tender = db.get_tender_by_id(tender_id)
        if not tender:
            return result

        result["extraction_status"] = tender.get("extraction_status") or "none"
        result["plan_number"] = tender.get("plan_number")
        result["brochure_summary"] = tender.get("brochure_summary")
        result["lots_data"] = tender.get("lots_data")
        result["extraction_error"] = tender.get("extraction_error")

        # Load building rights if plan_number exists
        if result["plan_number"]:
            result["building_rights"] = db.load_building_rights(result["plan_number"])

    except Exception as exc:
        logger.error("load_building_rights_data failed for tender %d: %s", tender_id, exc)

    return result


def get_user_email() -> str:
    """Get the current user's email address (no widgets rendered).

    Returns the email from Streamlit Cloud auth or session state.
    Call render_email_input() once per page before using this.

    Returns:
        Email string, or empty string if not available.
    """
    # 1. Try Streamlit Cloud auth
    for attr in ("user", "experimental_user"):
        try:
            user_info = getattr(st, attr, None)
            if user_info is not None:
                email = getattr(user_info, "email", "") or ""
                if not email:
                    email = user_info.get("email", "") if hasattr(user_info, "get") else ""
                if email:
                    return email
        except Exception:
            pass

    # 2. Session state (populated by render_email_input)
    return st.session_state.get("user_email", "")


def find_new_tender_ids_from_snapshots() -> Set[int]:
    """Compare the two most recent JSON snapshots to find newly added tender IDs.

    Scans PROJECT_ROOT for tenders_list_*.json files, picks the two most recent
    by filename date, and returns tender IDs present in the newest but absent
    from the previous snapshot.

    Returns:
        Set of tender_id ints that are new in the latest snapshot.
    """
    pattern = "tenders_list_*.json"
    snapshots = sorted(PROJECT_ROOT.glob(pattern))
    if len(snapshots) < 2:
        logger.info("Not enough snapshots for comparison (%d found)", len(snapshots))
        return set()

    newest = snapshots[-1]
    previous = snapshots[-2]
    logger.info("Comparing snapshots: %s vs %s", previous.name, newest.name)

    try:
        with open(newest, encoding="utf-8") as f:
            new_data = json.load(f)
        with open(previous, encoding="utf-8") as f:
            old_data = json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Failed to read snapshots: %s", exc)
        return set()

    def _extract_ids(data: list | dict) -> Set[int]:
        """Extract tender IDs from a JSON snapshot (list of dicts or wrapped)."""
        records = data if isinstance(data, list) else data.get("data", data.get("results", []))
        ids: Set[int] = set()
        for rec in records:
            tid = rec.get("MichrazID") or rec.get("tender_id") or rec.get("michraz_id")
            if tid is not None:
                try:
                    ids.add(int(tid))
                except (ValueError, TypeError):
                    pass
        return ids

    new_ids = _extract_ids(new_data)
    old_ids = _extract_ids(old_data)
    diff = new_ids - old_ids
    logger.info("Snapshot diff: %d new, %d removed, %d total new",
                len(diff), len(old_ids - new_ids), len(new_ids))
    return diff
