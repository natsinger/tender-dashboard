"""
Resource Finder - Discover datasets on data.gov.il
===================================================
Run this script to find the correct resource IDs for the dashboard.

Usage:
    python find_resources.py
"""

import requests
import json

BASE_URL = "https://data.gov.il/api/3/action"

def search_datasets(query: str):
    """Search for datasets matching a query."""
    print(f"\n🔍 Searching for: {query}")
    print("=" * 60)
    
    response = requests.get(f"{BASE_URL}/package_search", params={"q": query, "rows": 20})
    data = response.json()
    
    if not data.get("success"):
        print(f"❌ Search failed: {data.get('error')}")
        return
    
    results = data["result"]["results"]
    print(f"Found {len(results)} datasets\n")
    
    for i, dataset in enumerate(results, 1):
        print(f"{i}. {dataset.get('title', 'N/A')}")
        print(f"   Organization: {dataset.get('organization', {}).get('title', 'N/A')}")
        print(f"   Dataset name: {dataset.get('name')}")
        
        resources = dataset.get("resources", [])
        if resources:
            print(f"   Resources ({len(resources)}):")
            for res in resources:
                print(f"      📄 {res.get('name', 'Unnamed')}")
                print(f"         ID: {res.get('id')}")
                print(f"         Format: {res.get('format')}")
        print()


def get_resource_preview(resource_id: str, limit: int = 3):
    """Preview data from a specific resource."""
    print(f"\n📊 Preview of resource: {resource_id}")
    print("=" * 60)
    
    response = requests.get(f"{BASE_URL}/datastore_search", params={
        "resource_id": resource_id,
        "limit": limit
    })
    
    data = response.json()
    
    if not data.get("success"):
        print(f"❌ Fetch failed: {data.get('error')}")
        return
    
    result = data["result"]
    print(f"Total records: {result.get('total', 'N/A')}")
    
    # Show fields
    fields = result.get("fields", [])
    print(f"\nFields ({len(fields)}):")
    for f in fields:
        print(f"   - {f.get('id')}: {f.get('type')}")
    
    # Show sample records
    records = result.get("records", [])
    print(f"\nSample records ({len(records)}):")
    for i, record in enumerate(records, 1):
        print(f"\n   Record {i}:")
        for key, value in list(record.items())[:10]:  # Show first 10 fields
            print(f"      {key}: {value}")
        if len(record) > 10:
            print(f"      ... and {len(record) - 10} more fields")


def list_organization_datasets(org_id: str = "the_israel_lands_administration"):
    """List all datasets from a specific organization."""
    print(f"\n🏢 Datasets from organization: {org_id}")
    print("=" * 60)
    
    response = requests.get(f"{BASE_URL}/package_search", params={
        "fq": f"organization:{org_id}",
        "rows": 50
    })
    
    data = response.json()
    
    if not data.get("success"):
        # Try alternate org names
        for alt_org in ["3fa5ac56-7e9a-4f6f-9692-5f3e3a148fac", "israel_land_authority"]:
            response = requests.get(f"{BASE_URL}/package_search", params={
                "fq": f"organization:{alt_org}",
                "rows": 50
            })
            data = response.json()
            if data.get("success"):
                break
    
    if not data.get("success"):
        print("❌ Could not find organization. Trying search instead...")
        search_datasets("רשות מקרקעי ישראל")
        return
    
    results = data["result"]["results"]
    print(f"Found {len(results)} datasets\n")
    
    for dataset in results:
        print(f"📁 {dataset.get('title')}")
        for res in dataset.get("resources", []):
            print(f"   └─ {res.get('id')} ({res.get('format')})")
        print()


if __name__ == "__main__":
    print("=" * 60)
    print("  data.gov.il Resource Finder")
    print("  Find the correct resource IDs for land tenders data")
    print("=" * 60)
    
    # Search for relevant datasets
    search_terms = [
        "מכרזי קרקע",
        "מכרזים רמי",
        "רשות מקרקעי ישראל",
        "land tenders",
    ]
    
    print("\n" + "=" * 60)
    print("  Step 1: Searching for relevant datasets")
    print("=" * 60)
    
    for term in search_terms[:2]:  # Just first 2 to not overwhelm
        search_datasets(term)
    
    print("\n" + "=" * 60)
    print("  Step 2: Checking Israel Land Authority datasets")
    print("=" * 60)
    list_organization_datasets()
    
    print("\n" + "=" * 60)
    print("  Step 3: Preview a known dataset (development costs)")
    print("=" * 60)
    
    # Preview the development costs dataset (known to exist)
    get_resource_preview("04e375ef-08a6-4327-8044-7bd595c4d106", limit=2)
    
    print("\n" + "=" * 60)
    print("  NEXT STEPS")
    print("=" * 60)
    print("""
1. Look at the datasets found above
2. Find the one that contains land tender listings (מכרזי קרקע)
3. Copy the resource_id 
4. Update RESOURCE_IDS['tenders'] in src/data_client.py
5. Run the dashboard!

To preview a specific resource, add this at the end of this script:
    get_resource_preview("YOUR_RESOURCE_ID_HERE")
""")
