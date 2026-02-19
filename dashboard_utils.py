"""
Shared utility functions for the Streamlit dashboard pages.

Contains data loading functions used by both the main dashboard
and the management overview pages.
"""

import logging
from typing import Dict, Optional

import pandas as pd
import streamlit as st

from config import CACHE_TTL, DATA_DIR, DEV_USER_EMAIL, PROJECT_ROOT
from data_client import LandTendersClient, generate_sample_data

logger = logging.getLogger(__name__)


@st.cache_data(ttl=CACHE_TTL)
def load_data(data_source: str = "latest_file") -> pd.DataFrame:
    """Load tender data from Supabase DB, JSON file, or API (with fallbacks).

    Args:
        data_source: One of "latest_file", "sample". Controls fallback chain.

    Returns:
        DataFrame of tenders with normalized columns.
    """
    if data_source == "sample":
        return generate_sample_data()

    # Priority 1: Supabase database
    try:
        from db import TenderDB

        db = TenderDB()
        df = db.load_current_tenders()
        if len(df) > 0:
            return df
        logger.info("Database is empty, trying JSON fallback")
    except Exception as exc:
        logger.warning("Could not load from database: %s", exc)

    # Priority 2: JSON snapshot file
    client = LandTendersClient(data_dir=str(PROJECT_ROOT))
    if data_source == "latest_file":
        df = client.load_latest_json_snapshot()
        if df is not None:
            return df
        logger.warning("No JSON files found, fetching from API")
        st.warning("לא נמצאו קבצי JSON, טוען מהAPI...")

    # Priority 3: Live API call
    df = client.fetch_tenders_list()
    if df is None:
        logger.error("Could not fetch from API, falling back to sample data")
        st.error("לא ניתן לטעון מהAPI. מציג נתונים לדוגמה.")
        return generate_sample_data()

    client.save_json_snapshot(df)
    return df


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
