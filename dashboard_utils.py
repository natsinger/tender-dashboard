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
    """Load tender data from SQLite DB, JSON file, or API (with fallbacks).

    Args:
        data_source: One of "latest_file", "sample". Controls fallback chain.

    Returns:
        DataFrame of tenders with normalized columns.
    """
    if data_source == "sample":
        return generate_sample_data()

    # Priority 1: SQLite database
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


def get_user_email() -> str:
    """Get the current user's email address.

    On Streamlit Cloud: uses st.user.email (requires viewer auth enabled).
    Local development: uses DEV_USER_EMAIL from config/env.

    Returns:
        Email string, or empty string if not available.
    """
    try:
        user_info = st.user
        email = getattr(user_info, "email", "") or ""
        if email:
            return email
    except Exception:
        pass

    return DEV_USER_EMAIL
