"""
Israel Land Authority (רמ"י) Tenders Data Extraction Module

This module fetches tender data from data.gov.il - Israel's Open Data Portal.
The API uses CKAN standard: https://data.gov.il/api/action/datastore_search

SETUP INSTRUCTIONS:
1. Go to https://data.gov.il
2. Search for "מכרזי קרקע" or "רשות מקרקעי ישראל"
3. Find the relevant dataset and click on it
4. Look for the "resource_id" in the URL or API examples
5. Update RESOURCE_IDS below with the correct IDs

Example resource URL:
https://data.gov.il/dataset/DATASET_NAME/resource/RESOURCE_ID
"""

import requests
import pandas as pd
from datetime import datetime
from typing import Optional, Dict, List, Any
import json
import os

# ============================================================================
# CONFIGURATION - UPDATE WITH CORRECT RESOURCE IDs
# ============================================================================

# data.gov.il CKAN API base URL
BASE_URL = "https://data.gov.il/api/3/action"

# Resource IDs - UPDATE THESE after finding the correct datasets on data.gov.il
# Go to: https://data.gov.il/organization/the_israel_lands_administration
# Or search for "מכרזי קרקע" / "מכרזים" / "רמי"
RESOURCE_IDS = {
    # Main tenders list - FIND AND UPDATE THIS
    "tenders": "04e375ef-08a6-4327-8044-7bd595c4d106",
    
    # Development costs (עלויות פיתוח) - from Ministry of Housing
    # This one is confirmed to exist:
    "development_costs": "04e375ef-08a6-4327-8044-7bd595c4d106",
}

# Standard headers
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
}

# ============================================================================
# DATA EXTRACTION CLASS
# ============================================================================

class LandTendersClient:
    """Client for fetching data from data.gov.il (Israel's Open Data Portal)."""
    
    def __init__(self, data_dir: str = "data"):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
    
    def _datastore_search(self, resource_id: str, limit: int = 10000, 
                          offset: int = 0, filters: Optional[Dict] = None,
                          fields: Optional[List[str]] = None) -> Optional[Dict]:
        """
        Query the CKAN datastore_search API.
        
        API Documentation: https://data.gov.il/api/3/action/datastore_search
        
        Args:
            resource_id: The resource ID from data.gov.il
            limit: Max records to return (default 10000)
            offset: Pagination offset
            filters: Dict of field:value filters
            fields: List of fields to return (None = all)
        """
        url = f"{BASE_URL}/datastore_search"
        
        params = {
            "resource_id": resource_id,
            "limit": limit,
            "offset": offset,
        }
        
        if filters:
            params["filters"] = json.dumps(filters)
        
        if fields:
            params["fields"] = ",".join(fields)
        
        try:
            response = self.session.get(url, params=params, timeout=60)
            response.raise_for_status()
            data = response.json()
            
            if data.get("success"):
                return data["result"]
            else:
                print(f"❌ API Error: {data.get('error', 'Unknown error')}")
                return None
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Request failed: {e}")
            return None
    
    def list_datasets(self, query: str = "מכרזים") -> Optional[List[Dict]]:
        """Search for datasets on data.gov.il."""
        url = f"{BASE_URL}/package_search"
        
        try:
            response = self.session.get(url, params={"q": query}, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            if data.get("success"):
                results = data["result"]["results"]
                print(f"Found {len(results)} datasets:")
                for r in results:
                    print(f"  - {r.get('title')}")
                    print(f"    Name: {r.get('name')}")
                    for res in r.get('resources', []):
                        print(f"    Resource: {res.get('id')} ({res.get('format')})")
                return results
            return None
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Search failed: {e}")
            return None
    
    def get_resource_fields(self, resource_id: str) -> Optional[List[Dict]]:
        """Get field definitions for a resource."""
        result = self._datastore_search(resource_id, limit=1)
        if result:
            fields = result.get("fields", [])
            print(f"Fields in resource {resource_id}:")
            for f in fields:
                print(f"  - {f.get('id')}: {f.get('type')}")
            return fields
        return None
    
    def fetch_tenders_list(self, filters: Optional[Dict] = None) -> Optional[pd.DataFrame]:
        """
        Fetch list of all tenders from data.gov.il.
        
        Make sure to update RESOURCE_IDS['tenders'] with the correct resource ID first!
        """
        resource_id = RESOURCE_IDS.get("tenders")
        
        if resource_id == "REPLACE_WITH_RESOURCE_ID":
            print("⚠️  Resource ID not configured!")
            print("   1. Go to https://data.gov.il")
            print("   2. Search for 'מכרזי קרקע' or browse רשות מקרקעי ישראל")
            print("   3. Find the resource_id and update RESOURCE_IDS in data_client.py")
            print("\n   Running dataset discovery...")
            self.list_datasets("מכרזים קרקע")
            return None
        
        # Fetch all records (pagination if needed)
        all_records = []
        offset = 0
        limit = 10000
        
        while True:
            result = self._datastore_search(resource_id, limit=limit, offset=offset, filters=filters)
            
            if not result:
                break
            
            records = result.get("records", [])
            all_records.extend(records)
            
            total = result.get("total", 0)
            print(f"Fetched {len(all_records)} / {total} records...")
            
            if len(all_records) >= total:
                break
            
            offset += limit
        
        if all_records:
            df = pd.DataFrame(all_records)
            print(f"✅ Successfully fetched {len(df)} tenders")
            return df
        
        return None
    
    def fetch_development_costs(self) -> Optional[pd.DataFrame]:
        """Fetch development costs data (confirmed dataset)."""
        resource_id = RESOURCE_IDS.get("development_costs")
        result = self._datastore_search(resource_id)
        
        if result and result.get("records"):
            return pd.DataFrame(result["records"])
        return None
    
    def save_snapshot(self, df: pd.DataFrame, prefix: str = "tenders") -> str:
        """Save a timestamped snapshot of the data."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{prefix}_{timestamp}.csv"
        filepath = os.path.join(self.data_dir, filename)
        df.to_csv(filepath, index=False, encoding="utf-8-sig")
        print(f"✅ Saved: {filepath}")
        return filepath
    
    def load_latest_snapshot(self, prefix: str = "tenders") -> Optional[pd.DataFrame]:
        """Load the most recent snapshot."""
        files = [f for f in os.listdir(self.data_dir) if f.startswith(prefix) and f.endswith('.csv')]
        if not files:
            return None
        latest = sorted(files)[-1]
        return pd.read_csv(os.path.join(self.data_dir, latest))
    
    def load_all_snapshots(self, prefix: str = "tenders") -> pd.DataFrame:
        """Load and combine all historical snapshots for trend analysis."""
        files = [f for f in os.listdir(self.data_dir) if f.startswith(prefix) and f.endswith('.csv')]
        if not files:
            return pd.DataFrame()
        
        dfs = []
        for f in sorted(files):
            df = pd.read_csv(os.path.join(self.data_dir, f))
            # Extract snapshot date from filename
            df['_snapshot_date'] = f.replace(prefix + "_", "").replace(".csv", "")
            dfs.append(df)
        
        return pd.concat(dfs, ignore_index=True)


# ============================================================================
# SAMPLE DATA FOR TESTING (remove once real API works)
# ============================================================================

def generate_sample_data() -> pd.DataFrame:
    """Generate sample data to test the dashboard before API is configured."""
    import random
    from datetime import timedelta
    
    cities = ["תל אביב", "ירושלים", "חיפה", "באר שבע", "נתניה", "ראשון לציון", 
              "פתח תקווה", "אשדוד", "הרצליה", "רמת גן", "כפר סבא", "רעננה"]
    
    tender_types = ["מגורים", "מסחר", "תעסוקה", "מעורב", "תיירות"]
    statuses = ["פעיל", "נסגר", "בוטל"]
    
    data = []
    base_date = datetime.now()
    
    for i in range(50):
        publish_date = base_date - timedelta(days=random.randint(1, 90))
        deadline = publish_date + timedelta(days=random.randint(30, 90))
        
        data.append({
            "tender_id": f"מכ/{random.randint(100,999)}/2024",
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


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def normalize_hebrew_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Map Hebrew column names to English for easier processing.
    Update this mapping based on actual API response.
    """
    column_mapping = {
        "מספר מכרז": "tender_id",
        "עיר": "city",
        "יישוב": "city",
        "סוג מכרז": "tender_type",
        "סוג": "tender_type",
        "יחידות דיור": "units",
        "שטח": "area_sqm",
        "מחיר מינימום": "min_price",
        "תאריך פרסום": "publish_date",
        "מועד אחרון": "deadline",
        "סטטוס": "status",
        "גוש": "gush",
        "חלקה": "helka",
    }
    
    return df.rename(columns=column_mapping)


if __name__ == "__main__":
    # Quick test
    print("🧪 Testing with sample data...")
    sample = generate_sample_data()
    print(sample.head())
    print(f"\n📊 Sample data shape: {sample.shape}")
