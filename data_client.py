"""
Israel Land Authority (רמ"י) Tenders Data Extraction Module.

Fetches tender data from the Israel Land Authority API, normalizes fields,
maps code tables to Hebrew labels, and provides two-tier caching (memory + file).

API base: https://apps.land.gov.il/MichrazimSite/api/
"""

import json
import logging
import time
import urllib.parse
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
import requests

from complete_city_codes import city_code_map as complete_city_code_map
from complete_city_regions import city_region_map
from config import (
    API_MAX_RETRIES,
    API_RETRY_BACKOFF,
    API_TIMEOUT,
    CACHE_TTL,
    DATA_DIR,
    DETAIL_TIMEOUT,
    DOCUMENT_DOWNLOAD_API,
    LAND_AUTHORITY_API,
    RELEVANT_TENDER_TYPES,
    REQUEST_HEADERS,
    TENDER_DETAIL_API,
)

logger = logging.getLogger(__name__)


# ============================================================================
# CODE-TO-LABEL MAPPINGS (from GeneralTablesApi)
# ============================================================================

# Table 215 — סוג מכרז (Tender mechanism type)
TENDER_TYPE_MAP: Dict[int, str] = {
    1: "מכרז פומבי רגיל",
    2: "הרשמה והגרלה",
    3: "מכרז למגרש בלתי מסוים",
    4: "קדימות על פי עדיפות",
    5: "מחיר מטרה",
    6: "דיור להשכרה",
    7: "מחיר למשתכן",
    8: "דיור במחיר מופחת",
    9: "מכרז ייזום",
    10: "מכרזי עמידר",
    11: "מכרזי החברה לפיתוח עכו",
}

# Table 318 — ייעוד מכרז (Land-use purpose)
PURPOSE_MAP: Dict[int, str] = {
    1: "בנייה רוויה",
    2: "בנייה נמוכה/צמודת קרקע",
    3: "דיור מוגן",
    4: "תעסוקה",
    5: "כריה וחציבה",
    6: "אנרגיה מתחדשת",
    7: "תחנת כוח",
    99: "אחר",
}

# Status codes (from API)
STATUS_MAP: Dict[int, str] = {
    1: "טיוטה",
    2: "נדון בוועדת מכרזים",
    3: "פעיל",
    4: "מושהה",
    5: "נסגר",
    7: "בוטל",
}


# ============================================================================
# RETRY HELPER
# ============================================================================

def _request_with_retry(
    session: requests.Session,
    method: str,
    url: str,
    max_retries: int = API_MAX_RETRIES,
    backoff: float = API_RETRY_BACKOFF,
    **kwargs: Any,
) -> requests.Response:
    """Execute an HTTP request with exponential backoff retry.

    Args:
        session: requests.Session instance.
        method: HTTP method ("get" or "post").
        url: Request URL.
        max_retries: Maximum number of attempts.
        backoff: Base delay multiplier (seconds). Each retry doubles.
        **kwargs: Passed to session.request().

    Returns:
        The successful Response object.

    Raises:
        requests.RequestException: If all retries are exhausted.
    """
    last_error: Optional[Exception] = None
    for attempt in range(1, max_retries + 1):
        try:
            response = session.request(method, url, **kwargs)
            response.raise_for_status()
            return response
        except requests.RequestException as exc:
            last_error = exc
            if attempt < max_retries:
                wait = backoff * (2 ** (attempt - 1))
                logger.warning(
                    "Request to %s failed (attempt %d/%d): %s — retrying in %.1fs",
                    url, attempt, max_retries, exc, wait,
                )
                time.sleep(wait)
            else:
                logger.error(
                    "Request to %s failed after %d attempts: %s",
                    url, max_retries, exc,
                )
    raise last_error  # type: ignore[misc]


# ============================================================================
# DATA EXTRACTION CLASS
# ============================================================================

class LandTendersClient:
    """Client for fetching land tender data from the Israel Land Authority API."""

    def __init__(self, data_dir: Optional[str] = None) -> None:
        self.session = requests.Session()
        self.session.headers.update(REQUEST_HEADERS)
        self.data_dir = Path(data_dir) if data_dir else DATA_DIR
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # In-memory cache for detail responses
        self._details_cache: Dict[int, tuple] = {}
        self._cache_ttl = CACHE_TTL

    def fetch_from_land_authority(self) -> Optional[List[Dict]]:
        """Fetch all tenders from the Land Authority search API.

        Returns:
            List of tender dicts, or None on failure.
        """
        try:
            response = _request_with_retry(
                self.session, "post", LAND_AUTHORITY_API,
                json={}, timeout=API_TIMEOUT,
            )
            data = response.json()

            if isinstance(data, list):
                logger.info("Fetched %d tenders from Land Authority API", len(data))
                return data

            logger.error("Unexpected data format: %s", type(data))
            return None

        except requests.RequestException as exc:
            logger.error("API request failed: %s", exc)
            return None
        except json.JSONDecodeError as exc:
            logger.error("Failed to parse JSON response: %s", exc)
            return None

    def fetch_tender_details(self, tender_id: int) -> Optional[Dict[str, Any]]:
        """Fetch detailed information for a single tender.

        Args:
            tender_id: The MichrazID to look up.

        Returns:
            Detail dict, or None on failure.
        """
        url = f"{TENDER_DETAIL_API}?michrazID={tender_id}"
        try:
            response = _request_with_retry(
                self.session, "get", url, timeout=DETAIL_TIMEOUT,
            )
            response.encoding = response.apparent_encoding or "utf-8"
            data = response.json()
            logger.info("Fetched details for tender %d", tender_id)
            return data

        except requests.RequestException as exc:
            logger.error("Failed to fetch details for tender %d: %s", tender_id, exc)
            return None
        except json.JSONDecodeError as exc:
            logger.error("Invalid JSON for tender %d: %s", tender_id, exc)
            return None

    def get_tender_details_cached(
        self, tender_id: int, force_refresh: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """Fetch tender details with two-tier caching (memory + file).

        Args:
            tender_id: Tender ID to fetch.
            force_refresh: Bypass cache if True.

        Returns:
            Detail dict, or None on failure.
        """
        # Check in-memory cache
        if not force_refresh and tender_id in self._details_cache:
            cached_data, cached_time = self._details_cache[tender_id]
            age = (datetime.now() - cached_time).total_seconds()
            if age < self._cache_ttl:
                logger.debug("Memory cache hit for tender %d", tender_id)
                return cached_data

        # Check file cache
        cache_file = self.data_dir / "details_cache" / f"{tender_id}.json"

        if not force_refresh and cache_file.exists():
            try:
                cached_data = json.loads(cache_file.read_text(encoding="utf-8"))
                file_mtime = datetime.fromtimestamp(cache_file.stat().st_mtime)
                age = (datetime.now() - file_mtime).total_seconds()

                if age < self._cache_ttl:
                    logger.debug("File cache hit for tender %d", tender_id)
                    self._details_cache[tender_id] = (cached_data, file_mtime)
                    return cached_data
            except Exception as exc:
                logger.warning("Failed to load cache file for %d: %s", tender_id, exc)

        # Fetch from API
        details = self.fetch_tender_details(tender_id)

        if details:
            self._details_cache[tender_id] = (details, datetime.now())
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            cache_file.write_text(
                json.dumps(details, ensure_ascii=False, indent=2, default=str),
                encoding="utf-8",
            )

        return details

    def fetch_multiple_details(
        self,
        tender_ids: List[int],
        max_workers: int = 3,
        delay_seconds: float = 1.0,
    ) -> Dict[int, Dict]:
        """Fetch details for multiple tenders with rate limiting.

        Args:
            tender_ids: List of tender IDs.
            max_workers: Concurrent workers.
            delay_seconds: Delay between requests.

        Returns:
            Dict mapping tender_id to detail dict.
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed

        results: Dict[int, Dict] = {}

        def fetch_with_delay(tid: int) -> tuple:
            time.sleep(delay_seconds)
            return tid, self.get_tender_details_cached(tid)

        logger.info("Fetching details for %d tenders...", len(tender_ids))

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(fetch_with_delay, tid): tid for tid in tender_ids
            }

            for i, future in enumerate(as_completed(futures), 1):
                tender_id, details = future.result()
                if details:
                    results[tender_id] = details
                if i % 10 == 0:
                    logger.info("Progress: %d/%d details fetched", i, len(tender_ids))

        logger.info(
            "Fetched details for %d/%d tenders", len(results), len(tender_ids),
        )
        return results

    def download_document(self, doc: Dict) -> Optional[bytes]:
        """Download a tender document (PDF, etc.) from the RMI API.

        Args:
            doc: Document metadata dict (must include MichrazID, RowID, PirsumType).

        Returns:
            Raw file bytes, or None on failure.
        """
        try:
            response = _request_with_retry(
                self.session, "post", DOCUMENT_DOWNLOAD_API,
                json=doc, timeout=DETAIL_TIMEOUT,
            )
            content_type = response.headers.get("Content-Type", "")
            if "text/html" in content_type:
                logger.warning(
                    "Document download returned HTML (RowID=%s)", doc.get("RowID"),
                )
                return None
            return response.content

        except requests.RequestException as exc:
            logger.error(
                "Document download failed (RowID=%s): %s", doc.get("RowID"), exc,
            )
            return None

    # ────────────────────────────────────────────────────────────────────────
    # Data loading / snapshots
    # ────────────────────────────────────────────────────────────────────────

    def fetch_tenders_list(self) -> Optional[pd.DataFrame]:
        """Fetch, normalize, and return all tenders as a DataFrame."""
        records = self.fetch_from_land_authority()
        if not records:
            return None

        df = pd.DataFrame(records)
        df = normalize_api_columns(df)

        date_columns = ["publish_date", "deadline", "committee_date"]
        for col in date_columns:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce", utc=True)
                if df[col].dtype == "datetime64[ns, UTC]":
                    df[col] = df[col].dt.tz_localize(None)

        logger.info("Processed %d tenders", len(df))
        return df

    def save_snapshot(self, df: pd.DataFrame, prefix: str = "tenders") -> str:
        """Save a timestamped CSV snapshot."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{prefix}_{timestamp}.csv"
        filepath = self.data_dir / filename
        df.to_csv(filepath, index=False, encoding="utf-8-sig")
        logger.info("Saved CSV snapshot: %s", filepath)
        return str(filepath)

    def save_json_snapshot(self, df: pd.DataFrame) -> str:
        """Save a JSON snapshot with date-based filename (DD_MM_YYYY)."""
        data = df.to_dict("records")
        filename = f"tenders_list_{datetime.now().strftime('%d_%m_%Y')}.json"
        filepath = self.data_dir / filename

        filepath.write_text(
            json.dumps(data, ensure_ascii=False, default=str),
            encoding="utf-8",
        )
        logger.info("Saved JSON snapshot: %s", filepath)
        return str(filepath)

    def load_latest_json_snapshot(self) -> Optional[pd.DataFrame]:
        """Load the most recent tenders_list_*.json snapshot.

        Applies field normalization and code-to-label mappings.
        """
        import re

        pattern = "tenders_list_*.json"
        files = list(self.data_dir.glob(pattern))

        if not files:
            return None

        def parse_date(filepath: Path) -> str:
            match = re.search(
                r"tenders_list_(\d{2})_(\d{2})_(\d{4})\.json", filepath.name,
            )
            if match:
                day, month, year = match.groups()
                return f"{year}{month}{day}"
            return "00000000"

        latest = max(files, key=parse_date)

        try:
            df = pd.read_json(latest, encoding="utf-8")
            logger.info(
                "Loaded %d tenders from %s", len(df), latest.name,
            )

            if "MichrazID" in df.columns:
                df = normalize_api_columns(df)
            else:
                df = apply_code_mappings(df)

            date_columns = ["publish_date", "deadline", "committee_date"]
            for col in date_columns:
                if col in df.columns:
                    df[col] = pd.to_datetime(df[col], errors="coerce", utc=True)
                    if df[col].dtype == "datetime64[ns, UTC]":
                        df[col] = df[col].dt.tz_localize(None)

            return df

        except Exception as exc:
            logger.error("Error loading %s: %s", latest, exc)
            return None

    def load_latest_snapshot(self, prefix: str = "tenders") -> Optional[pd.DataFrame]:
        """Load the most recent CSV snapshot."""
        files = sorted(self.data_dir.glob(f"{prefix}_*.csv"))
        if not files:
            return None
        return pd.read_csv(files[-1])

    def load_all_snapshots(self, prefix: str = "tenders") -> pd.DataFrame:
        """Load and combine all historical CSV snapshots."""
        files = sorted(self.data_dir.glob(f"{prefix}_*.csv"))
        if not files:
            return pd.DataFrame()

        dfs = []
        for f in files:
            df = pd.read_csv(f)
            df["_snapshot_date"] = f.stem.replace(f"{prefix}_", "")
            dfs.append(df)

        return pd.concat(dfs, ignore_index=True)

    # ────────────────────────────────────────────────────────────────────────
    # Database persistence
    # ────────────────────────────────────────────────────────────────────────

    def save_to_db(
        self, df: pd.DataFrame, snapshot_date: Optional[str] = None,
    ) -> int:
        """Save tenders DataFrame to SQLite.

        Args:
            df: Normalized tenders DataFrame.
            snapshot_date: ISO date string for the history entry.

        Returns:
            Number of tenders processed.
        """
        from db import TenderDB

        db = TenderDB()
        db.upsert_tenders(df, snapshot_date)
        return len(df)

    def sync_documents_to_db(self, tender_ids: List[int]) -> int:
        """Fetch details for given tenders and save their documents to DB.

        Args:
            tender_ids: List of tender IDs to sync documents for.

        Returns:
            Count of new documents found.
        """
        from db import TenderDB

        db = TenderDB()
        new_doc_count = 0

        for tid in tender_ids:
            details = self.get_tender_details_cached(tid)
            if not details:
                continue

            doc_list = list(details.get("MichrazDocList", []))
            full_doc = details.get("MichrazFullDocument")
            if full_doc and full_doc.get("RowID") is not None:
                doc_list.append(full_doc)

            new_docs = db.upsert_documents(tid, doc_list)
            new_doc_count += len(new_docs)

        return new_doc_count


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def apply_code_mappings(df: pd.DataFrame) -> pd.DataFrame:
    """Apply code-to-label mappings and filter to relevant tender types.

    Operates on DataFrames that already have normalized column names
    (e.g. loaded from a previously-saved JSON snapshot).
    """
    if "status_code" in df.columns:
        df["status"] = df["status_code"].map(STATUS_MAP).fillna("לא ידוע")

    if "tender_type_code" in df.columns:
        df["tender_type"] = df["tender_type_code"].map(TENDER_TYPE_MAP).fillna("אחר")

    if "purpose_code" in df.columns:
        df["purpose"] = df["purpose_code"].map(PURPOSE_MAP).fillna("אחר")

    if "tender_type_code" in df.columns:
        df = df[df["tender_type_code"].isin(RELEVANT_TENDER_TYPES)].reset_index(
            drop=True,
        )

    return df


def normalize_api_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Map raw Land Authority API fields to dashboard-friendly column names.

    Renames columns, maps city codes to names/regions, decodes code fields
    to Hebrew labels, and filters to relevant tender types.
    """
    column_mapping = {
        "MichrazID": "tender_id",
        "MichrazName": "tender_name",
        "KodYeshuv": "city_code",
        "Shchuna": "location",
        "KodSugMichraz": "tender_type_code",
        "YechidotDiur": "units",
        "StatusMichraz": "status_code",
        "PtichaDate": "publish_date",
        "SgiraDate": "deadline",
        "VaadaDate": "committee_date",
        "KodYeudMichraz": "purpose_code",
        "PublishedChoveret": "published_booklet",
        "Mekuvan": "targeted",
    }

    df = df.rename(columns=column_mapping)

    if "city_code" in df.columns:
        df["city"] = df["city_code"].map(complete_city_code_map).fillna("אחר")

    if "city_code" in df.columns:
        df["region"] = df["city_code"].map(city_region_map).fillna("לא ידוע")

    df = apply_code_mappings(df)

    if "location" in df.columns:
        df["location"] = df["location"].apply(
            lambda x: x.strip() if isinstance(x, str) else x,
        )

    for field in ("area_sqm", "min_price"):
        if field not in df.columns:
            df[field] = 0
    for field in ("gush", "helka"):
        if field not in df.columns:
            df[field] = None

    return df


def build_document_url(doc: Dict) -> str:
    """Build a direct download URL for a tender document.

    Args:
        doc: Document dict from the API (with MichrazID, RowID, etc.).

    Returns:
        Full URL string for downloading the document.
    """
    params = {
        "michrazId": doc.get("MichrazID", 0),
        "rowId": doc.get("RowID", 0),
        "size": doc.get("Size") or 0,
        "typePirsum": doc.get("PirsumType", 0),
        "fileName": doc.get("DocName", "document.pdf"),
        "teur": doc.get("Teur", ""),
        "fileType": doc.get("FileType", "application/pdf"),
    }
    return f"{DOCUMENT_DOWNLOAD_API}?{urllib.parse.urlencode(params)}"


def generate_sample_data() -> pd.DataFrame:
    """Generate synthetic sample data for testing the dashboard."""
    import random
    from datetime import timedelta

    cities = [
        "תל אביב", "ירושלים", "חיפה", "באר שבע", "נתניה", "ראשון לציון",
        "פתח תקווה", "אשדוד", "הרצליה", "רמת גן", "כפר סבא", "רעננה",
    ]
    tender_types = ["מגורים", "מסחר", "תעסוקה", "מעורב", "תיירות"]
    statuses = ["פעיל", "נסגר", "בוטל"]

    data = []
    base_date = datetime.now()

    for _ in range(50):
        publish_date = base_date - timedelta(days=random.randint(1, 90))
        deadline = publish_date + timedelta(days=random.randint(30, 90))

        data.append({
            "tender_id": f"מכ/{random.randint(100, 999)}/2024",
            "city": random.choice(cities),
            "tender_type": random.choice(tender_types),
            "units": random.randint(10, 500),
            "area_sqm": random.randint(1000, 50000),
            "min_price": random.randint(500000, 50000000),
            "publish_date": publish_date.strftime("%Y-%m-%d"),
            "deadline": deadline.strftime("%Y-%m-%d"),
            "status": random.choices(statuses, weights=[0.7, 0.25, 0.05])[0],
            "gush": random.randint(1000, 9999),
            "helka": random.randint(1, 200),
        })

    return pd.DataFrame(data)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
    )
    logger.info("Testing with sample data...")
    sample = generate_sample_data()
    logger.info("Sample data shape: %s", sample.shape)
