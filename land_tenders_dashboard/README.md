# 🏗️ Israel Land Tenders Dashboard (מכרזי קרקע)

A Streamlit dashboard for tracking and analyzing land tenders from Israel Land Authority (רשות מקרקעי ישראל).

**Data Source:** [data.gov.il](https://data.gov.il) - Israel's Open Data Portal (CKAN API)

## 🚀 Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Step 1: Find the correct resource ID
python find_resources.py

# Step 2: Update src/data_client.py with the resource ID

# Step 3: Run the dashboard
streamlit run app.py
```

The dashboard will open at `http://localhost:8501`

## 📁 Project Structure

```
land_tenders_dashboard/
├── app.py                 # Main Streamlit dashboard
├── requirements.txt       # Python dependencies
├── find_resources.py      # 🆕 Helper to discover dataset IDs
├── scheduler.py           # Weekly data collection script
├── src/
│   └── data_client.py     # data.gov.il CKAN API client
├── data/                  # Stored snapshots (auto-created)
└── README.md
```

## 🔧 Configuration Guide

### Step 1: Find the Resource ID

The dashboard uses Israel's Open Data Portal API. You need to find the correct **resource_id** for the land tenders dataset.

**Option A: Run the finder script**
```bash
python find_resources.py
```

**Option B: Manual search**
1. Go to https://data.gov.il
2. Search for "מכרזי קרקע" or "רשות מקרקעי ישראל"
3. Click on the relevant dataset
4. Find the resource_id in the URL or API section:
   ```
   https://data.gov.il/dataset/DATASET_NAME/resource/RESOURCE_ID
   ```

### Step 2: Update Configuration

Edit `src/data_client.py` and update the `RESOURCE_IDS` dict:

```python
RESOURCE_IDS = {
    "tenders": "YOUR_RESOURCE_ID_HERE",  # Replace this!
    "development_costs": "04e375ef-08a6-4327-8044-7bd595c4d106",
}
```

### Step 3: Test the Connection

```bash
python -c "from src.data_client import LandTendersClient; c = LandTendersClient(); c.get_resource_fields('YOUR_RESOURCE_ID')"
```

## 📊 API Reference

The data.gov.il API follows the CKAN standard:

```python
# Search for datasets
GET https://data.gov.il/api/3/action/package_search?q=מכרזים

# Fetch data from a resource
GET https://data.gov.il/api/3/action/datastore_search?resource_id=RESOURCE_ID&limit=1000

# With filters
GET https://data.gov.il/api/3/action/datastore_search?resource_id=RESOURCE_ID&filters={"city":"תל אביב"}
```

## 📊 Features

### Current (v1.0)
- [x] KPI metrics (active tenders, units, area)
- [x] Tenders by city chart
- [x] Tenders by type (pie chart)
- [x] Timeline analysis
- [x] Price distribution
- [x] Upcoming deadlines with urgency indicators
- [x] Full data table with filters
- [x] CSV export

### Planned
- [ ] Weekly automated data collection
- [ ] Price trend analysis over time
- [ ] Email/Slack alerts for new tenders
- [ ] Map visualization
- [ ] Comparison with historical data

## ⏰ Weekly Data Collection (Optional)

To automatically fetch and store data weekly, you can set up a cron job:

```bash
# Edit crontab
crontab -e

# Add this line (runs every Sunday at 8 AM)
0 8 * * 0 cd /path/to/land_tenders_dashboard && python -c "from src.data_client import LandTendersClient; c=LandTendersClient(); df=c.fetch_tenders_list(); c.save_snapshot(df) if df is not None else None"
```

Or use the scheduler script (see `scheduler.py`).

## 🐛 Troubleshooting

### API returns 403/401
- The site may require cookies/session tokens
- Try copying cookies from browser DevTools

### Hebrew encoding issues
- Ensure files are saved with UTF-8 encoding
- Use `encoding='utf-8-sig'` when reading/writing CSVs

### Rate limiting
- Add delays between requests
- Don't fetch too frequently

## 📝 Notes

- This tool is for informational purposes
- Always verify tender details on the official site
- Data accuracy depends on the source API

## 📜 License

MIT - Feel free to use and modify
