"""
Weekly Data Collection Scheduler
================================
Run this script to continuously collect data on a schedule.

Usage:
    python scheduler.py

Or run once manually:
    python -c "from scheduler import collect_now; collect_now()"
"""

import schedule
import time
from datetime import datetime
import sys
sys.path.append('src')

from data_client import LandTendersClient


def collect_now():
    """Run a single data collection."""
    print(f"\n{'='*50}")
    print(f"🕐 Starting data collection at {datetime.now()}")
    print(f"{'='*50}")
    
    client = LandTendersClient(data_dir="data")
    
    try:
        df = client.fetch_tenders_list()
        
        if df is not None and len(df) > 0:
            filepath = client.save_snapshot(df)
            print(f"✅ Successfully collected {len(df)} tenders")
            print(f"📁 Saved to: {filepath}")
        else:
            print("⚠️ No data retrieved from API")
            print("   Check if API endpoints are configured correctly")
            
    except Exception as e:
        print(f"❌ Error during collection: {e}")
    
    print(f"{'='*50}\n")


def run_scheduler():
    """Run the scheduler loop."""
    print("🚀 Starting Land Tenders Data Collector")
    print("   Schedule: Every Sunday at 08:00")
    print("   Press Ctrl+C to stop\n")
    
    # Schedule weekly collection
    schedule.every().sunday.at("08:00").do(collect_now)
    
    # Also run immediately on start (optional)
    # collect_now()
    
    # Keep running
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Land Tenders Data Collector")
    parser.add_argument("--now", action="store_true", help="Run collection immediately")
    parser.add_argument("--daemon", action="store_true", help="Run as continuous scheduler")
    
    args = parser.parse_args()
    
    if args.now:
        collect_now()
    elif args.daemon:
        run_scheduler()
    else:
        print("Usage:")
        print("  python scheduler.py --now     # Run once immediately")
        print("  python scheduler.py --daemon  # Run continuous scheduler")
