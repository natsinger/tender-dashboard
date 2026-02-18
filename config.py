"""
Centralized configuration for the Land Tenders Dashboard.

Loads settings from (in priority order):
1. Streamlit secrets (st.secrets) — for Streamlit Cloud deployment
2. Environment variables / .env file — for local development
3. Hardcoded defaults — safe fallbacks

Usage:
    from config import cfg
    print(cfg.LAND_AUTHORITY_API)
"""

import os
from pathlib import Path
from typing import Set

# Try to load .env file for local development
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def _get(key: str, default: str = "") -> str:
    """Get a config value from st.secrets, then env vars, then default."""
    # Priority 1: Streamlit secrets (available on Streamlit Cloud)
    try:
        import streamlit as st
        if hasattr(st, "secrets") and key in st.secrets:
            return str(st.secrets[key])
    except Exception:
        pass

    # Priority 2: Environment variable
    val = os.environ.get(key)
    if val is not None:
        return val

    # Priority 3: Default
    return default


def _get_int(key: str, default: int) -> int:
    """Get an integer config value."""
    raw = _get(key, str(default))
    try:
        return int(raw)
    except (ValueError, TypeError):
        return default


# ============================================================================
# API ENDPOINTS
# ============================================================================

LAND_AUTHORITY_API: str = _get(
    "LAND_AUTHORITY_API",
    "https://apps.land.gov.il/MichrazimSite/api/SearchApi/Search",
)

TENDER_DETAIL_API: str = _get(
    "TENDER_DETAIL_API",
    "https://apps.land.gov.il/MichrazimSite/api/MichrazDetailsApi/Get",
)

DOCUMENT_DOWNLOAD_API: str = _get(
    "DOCUMENT_DOWNLOAD_API",
    "https://apps.land.gov.il/MichrazimSite/api/MichrazDetailsApi/GetFileContent",
)

RMI_SITE_URL: str = _get(
    "RMI_SITE_URL",
    "https://apps.land.gov.il/MichrazimSite/#/michraz",
)

# ============================================================================
# HTTP
# ============================================================================

REQUEST_HEADERS: dict = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
    "Content-Type": "application/json",
}

API_TIMEOUT: int = _get_int("API_TIMEOUT", 60)
DETAIL_TIMEOUT: int = _get_int("DETAIL_TIMEOUT", 30)
API_MAX_RETRIES: int = _get_int("API_MAX_RETRIES", 3)
API_RETRY_BACKOFF: float = float(_get("API_RETRY_BACKOFF", "2.0"))

# ============================================================================
# CACHING
# ============================================================================

CACHE_TTL: int = _get_int("CACHE_TTL", 3600)  # seconds

# ============================================================================
# PATHS
# ============================================================================

PROJECT_ROOT: Path = Path(__file__).resolve().parent
DATA_DIR: Path = PROJECT_ROOT / _get("DATA_DIR", "data")
DB_PATH: Path = PROJECT_ROOT / _get("DB_PATH", "data/tenders.db")
LOGS_DIR: Path = PROJECT_ROOT / "logs"

# ============================================================================
# DASHBOARD DEFAULTS
# ============================================================================

CLOSING_SOON_DAYS: int = _get_int("CLOSING_SOON_DAYS", 14)
DEFAULT_FETCH_WORKERS: int = _get_int("DEFAULT_FETCH_WORKERS", 3)
DEFAULT_FETCH_DELAY: float = float(_get("DEFAULT_FETCH_DELAY", "1.0"))

# Tender types shown in the dashboard (codes from GeneralTablesApi Table 215)
RELEVANT_TENDER_TYPES: Set[int] = {1, 5, 8}

# Statuses excluded from the default "active" view
NON_ACTIVE_STATUSES: list = [
    "נסגר", "בוטל", "לא אקטואלי", "תהליך מסתיים", "עוכב", "מכרז סגור",
]
