"""
Israel Land Tenders Dashboard (מכרזי קרקע)
==========================================
A Streamlit dashboard for tracking and analyzing land tenders from רמ"י.

Run with: streamlit run app.py
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from typing import Optional, Dict
import sys
sys.path.append('src')

from data_client import LandTendersClient, generate_sample_data, normalize_hebrew_columns

# ============================================================================
# PAGE CONFIG
# ============================================================================

st.set_page_config(
    page_title="מכרזי קרקע - Dashboard",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for RTL support
st.markdown("""
<style>
    .rtl-text {
        direction: rtl;
        text-align: right;
    }
    .metric-card {
        background-color: #f0f2f6;
        border-radius: 10px;
        padding: 20px;
        text-align: center;
    }
    .stMetric > div {
        direction: rtl;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# DATA LOADING
# ============================================================================

@st.cache_data(ttl=3600)  # Cache for 1 hour
def load_data(data_source: str = "latest_file") -> pd.DataFrame:
    """Load tender data from API, JSON file, or sample data."""
    # Use parent directory (project root) for JSON files
    import os
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    client = LandTendersClient(data_dir=root_dir)

    if data_source == "sample":
        return generate_sample_data()

    if data_source == "latest_file":
        df = client.load_latest_json_snapshot()
        if df is not None:
            return df
        st.warning("⚠️ No JSON files found, fetching from API...")

    # Fetch fresh from API
    df = client.fetch_tenders_list()
    if df is None:
        st.error("❌ Could not fetch from API. Using sample data.")
        return generate_sample_data()

    # Save for future use
    client.save_json_snapshot(df)
    return df

@st.cache_data(ttl=3600)
def load_tender_details(tender_id: int) -> Optional[Dict]:
    """Load tender details with caching."""
    client = LandTendersClient(data_dir="data")
    return client.get_tender_details_cached(tender_id)

# ============================================================================
# SIDEBAR
# ============================================================================

with st.sidebar:
    st.image("https://www.gov.il/BlobFolder/generalpage/land-tenders/he/Michrazim_land-tenders_banner.jpg", 
             use_container_width=True)
    st.title("🏗️ מכרזי קרקע")
    st.markdown("---")

    # Data source selector
    data_source = st.radio(
        "Data Source",
        ["latest_file", "live_api", "sample"],
        format_func=lambda x: {
            "latest_file": "📂 Latest JSON File",
            "live_api": "🌐 Live API",
            "sample": "🧪 Sample Data"
        }[x],
        index=0,  # Default to latest file
        help="Choose data source: Latest JSON file (default), Live API, or Sample data for testing"
    )

    # Load data
    df = load_data(data_source=data_source)
    
    st.markdown("### 🔍 Filters")

    # Region filter - multiselect
    if 'region' in df.columns:
        regions = sorted(df['region'].dropna().unique().tolist())
        selected_regions = st.multiselect(
            "Regions / אזורים",
            regions,
            default=[],
            placeholder="Select regions (leave empty for all)"
        )
    else:
        selected_regions = []

    # City filter - CASCADE from region selection
    if selected_regions:
        # Filter cities to only those in selected regions
        cities_in_selected_regions = df[df['region'].isin(selected_regions)]['city'].dropna().unique()
        cities = sorted(cities_in_selected_regions.tolist())
        placeholder_text = f"Select cities in selected region(s) ({len(cities)} available)"
    else:
        # No region selected - show all cities
        cities = sorted(df['city'].dropna().unique().tolist())
        placeholder_text = "Select cities (leave empty for all)"

    selected_cities = st.multiselect(
        "Cities / ערים",
        cities,
        default=[],
        placeholder=placeholder_text
    )

    # Tender type filter - multiselect
    types = sorted(df['tender_type'].dropna().unique().tolist())
    selected_types = st.multiselect(
        "Types / סוגי מכרז",
        types,
        default=[],
        placeholder="Select types (leave empty for all)"
    )

    # Status filter - multiselect
    statuses = sorted(df['status'].dropna().unique().tolist())
    selected_statuses = st.multiselect(
        "Status / סטטוס",
        statuses,
        default=[],
        placeholder="Select statuses (leave empty for all)"
    )
    
    # Date range filter
    st.markdown("#### 📅 Date Range")

    # Use deadline instead of publish_date (more reliable in the data)
    valid_dates = df['deadline'].dropna()

    if len(valid_dates) > 0:
        min_date = valid_dates.min()
        max_date = valid_dates.max()

        date_range = st.date_input(
            "Deadline Range",
            value=(min_date.date(), max_date.date()),
            min_value=min_date.date(),
            max_value=max_date.date()
        )
    else:
        date_range = None
        st.info("No valid dates available for filtering")
    
    st.markdown("---")
    st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    st.caption(f"Total records: {len(df)}")

# ============================================================================
# APPLY FILTERS
# ============================================================================

filtered_df = df.copy()

# Apply region filter (only if regions are selected)
if selected_regions:
    filtered_df = filtered_df[filtered_df['region'].isin(selected_regions)]

# Apply city filter (only if cities are selected)
if selected_cities:
    filtered_df = filtered_df[filtered_df['city'].isin(selected_cities)]

# Apply tender type filter (only if types are selected)
if selected_types:
    filtered_df = filtered_df[filtered_df['tender_type'].isin(selected_types)]

# Apply status filter (only if statuses are selected)
if selected_statuses:
    filtered_df = filtered_df[filtered_df['status'].isin(selected_statuses)]

# Apply date range filter
if date_range and len(date_range) == 2:
    start_date, end_date = date_range
    filtered_df = filtered_df[
        (filtered_df['deadline'].notna()) &
        (filtered_df['deadline'].dt.date >= start_date) &
        (filtered_df['deadline'].dt.date <= end_date)
    ]

# ============================================================================
# MAIN DASHBOARD
# ============================================================================

st.title("📊 Israel Land Tenders Dashboard")
st.markdown("Track and analyze land tenders from רשות מקרקעי ישראל")

# KPI Metrics Row
col1, col2, col3, col4 = st.columns(4)

with col1:
    active_tenders = len(filtered_df[filtered_df['status'] == 'פעיל'])
    st.metric("🟢 Active Tenders", active_tenders)

with col2:
    total_units = filtered_df['units'].sum()
    st.metric("🏠 Total Units", f"{int(total_units):,}")

with col3:
    unique_cities = filtered_df['city'].nunique()
    st.metric("🏙️ Cities", f"{unique_cities}")

with col4:
    # Tenders closing soon (next 14 days)
    today = datetime.now()
    closing_soon = len(filtered_df[
        (filtered_df['deadline'] >= today) & 
        (filtered_df['deadline'] <= today + timedelta(days=14))
    ])
    st.metric("⏰ Closing Soon (14d)", closing_soon)

st.markdown("---")

# ============================================================================
# CHARTS ROW 1: Distribution by City & Type
# ============================================================================

col1, col2 = st.columns(2)

with col1:
    st.subheader("📍 Tenders by City")
    city_counts = filtered_df['city'].value_counts().head(10)

    if len(city_counts) > 0:
        fig_city = px.bar(
            x=city_counts.values,
            y=city_counts.index,
            orientation='h',
            labels={'x': 'Number of Tenders', 'y': 'City'},
            color=city_counts.values,
            color_continuous_scale='Blues'
        )
        fig_city.update_layout(showlegend=False, height=400)
        st.plotly_chart(fig_city, use_container_width=True)
    else:
        st.info("No data available for the selected filters")

with col2:
    st.subheader("🏷️ Tenders by Type")
    type_counts = filtered_df['tender_type'].value_counts()

    if len(type_counts) > 0:
        fig_type = px.pie(
            values=type_counts.values,
            names=type_counts.index,
            hole=0.4,
            color_discrete_sequence=px.colors.qualitative.Set2
        )
        fig_type.update_layout(height=400)
        st.plotly_chart(fig_type, use_container_width=True)
    else:
        st.info("No data available for the selected filters")

# ============================================================================
# CHARTS ROW 2: Timeline & Price Analysis
# ============================================================================

col1, col2 = st.columns(2)

with col1:
    st.subheader("📈 Tenders Over Time")
    # Group by publish month
    timeline_df = filtered_df.copy()

    if len(timeline_df) > 0 and timeline_df['publish_date'].notna().any():
        timeline_df['month'] = timeline_df['publish_date'].dt.to_period('M').astype(str)
        monthly_counts = timeline_df.groupby('month').size().reset_index(name='count')

        fig_timeline = px.line(
            monthly_counts,
            x='month',
            y='count',
            markers=True,
            labels={'month': 'Month', 'count': 'Number of Tenders'}
        )
        fig_timeline.update_layout(height=400)
        st.plotly_chart(fig_timeline, use_container_width=True)
    else:
        st.info("No data available for the selected filters")

with col2:
    st.subheader("🏠 Housing Units by Type")
    # Group by tender type
    units_by_type = filtered_df.groupby('tender_type')['units'].sum().reset_index()
    units_by_type = units_by_type[units_by_type['units'] > 0]  # Filter out zero units

    if not units_by_type.empty:
        fig_units = px.bar(
            units_by_type,
            x='tender_type',
            y='units',
            labels={'units': 'Total Units', 'tender_type': 'Tender Type'},
            color_discrete_sequence=['#1f77b4']
        )
        fig_units.update_layout(height=400)
        st.plotly_chart(fig_units, use_container_width=True)
    else:
        st.info("No units data available for the selected filters")

# ============================================================================
# UPCOMING DEADLINES
# ============================================================================

st.markdown("---")
st.subheader("⏰ Upcoming Deadlines")

today = datetime.now()
upcoming = filtered_df[
    (filtered_df['deadline'] >= today) & 
    (filtered_df['status'] == 'פעיל')
].sort_values('deadline').head(10)

if len(upcoming) > 0:
    upcoming_display = upcoming[['tender_id', 'city', 'tender_type', 'units', 'deadline']].copy()
    upcoming_display['days_left'] = (upcoming_display['deadline'] - today).dt.days
    upcoming_display['deadline'] = upcoming_display['deadline'].dt.strftime('%Y-%m-%d')
    
    # Color code by urgency
    def urgency_color(days):
        if days <= 7:
            return '🔴'
        elif days <= 14:
            return '🟡'
        else:
            return '🟢'
    
    upcoming_display['urgency'] = upcoming_display['days_left'].apply(urgency_color)
    upcoming_display = upcoming_display[['urgency', 'tender_id', 'city', 'tender_type', 'units', 'deadline', 'days_left']]
    
    st.dataframe(
        upcoming_display,
        column_config={
            "urgency": st.column_config.TextColumn("", width=30),
            "tender_id": "Tender ID",
            "city": "City",
            "tender_type": "Type",
            "units": "Units",
            "deadline": "Deadline",
            "days_left": st.column_config.NumberColumn("Days Left", format="%d")
        },
        hide_index=True,
        use_container_width=True
    )
else:
    st.info("No upcoming deadlines found.")

# ============================================================================
# FULL DATA TABLE
# ============================================================================

st.markdown("---")
st.subheader("📋 All Tenders Data")

# Column selection
all_cols = filtered_df.columns.tolist()
default_cols = ['tender_id', 'tender_name', 'city', 'tender_type', 'units', 'deadline', 'status']
display_cols = [c for c in default_cols if c in all_cols]

selected_cols = st.multiselect("Select columns to display", all_cols, default=display_cols)

# Add search functionality
col1, col2 = st.columns([3, 1])
with col1:
    search_term = st.text_input("🔍 Search in all columns", placeholder="Type to search...")
with col2:
    st.write("")  # Spacing
    show_all = st.checkbox("Show all columns", value=False)

if show_all:
    selected_cols = all_cols

if selected_cols:
    display_df = filtered_df[selected_cols].copy()

    # Apply search filter if search term provided
    if search_term:
        # Search across all string columns
        mask = display_df.astype(str).apply(
            lambda row: row.str.contains(search_term, case=False, na=False).any(),
            axis=1
        )
        display_df = display_df[mask]
        st.caption(f"Found {len(display_df)} records matching '{search_term}'")

    # Format columns for display
    display_df_formatted = display_df.copy()

    # Convert date columns to datetime
    for col in ['publish_date', 'deadline', 'committee_date']:
        if col in display_df_formatted.columns:
            display_df_formatted[col] = pd.to_datetime(display_df_formatted[col], errors='coerce')

    # Convert tender_id to string for better display
    if 'tender_id' in display_df_formatted.columns:
        display_df_formatted['tender_id'] = display_df_formatted['tender_id'].astype(str)

    # Convert tender_name to string
    if 'tender_name' in display_df_formatted.columns:
        display_df_formatted['tender_name'] = display_df_formatted['tender_name'].astype(str)

    # Display with data_editor for better interactivity
    st.data_editor(
        display_df_formatted,
        hide_index=True,
        use_container_width=True,
        disabled=True,  # Read-only
        column_config={
            "tender_id": st.column_config.TextColumn("Tender ID", width="medium"),
            "tender_name": st.column_config.TextColumn("Tender Name", width="large"),
            "city": st.column_config.TextColumn("City", width="medium"),
            "tender_type": st.column_config.TextColumn("Type", width="medium"),
            "units": st.column_config.NumberColumn("Units", format="%d"),
            "deadline": st.column_config.DateColumn("Deadline", format="YYYY-MM-DD"),
            "publish_date": st.column_config.DateColumn("Published", format="YYYY-MM-DD"),
            "committee_date": st.column_config.DateColumn("Committee Date", format="YYYY-MM-DD"),
            "status": st.column_config.TextColumn("Status", width="small"),
        }
    )

    # Download button
    csv = display_df.to_csv(index=False, encoding='utf-8-sig')
    st.download_button(
        label="📥 Download CSV",
        data=csv,
        file_name=f"land_tenders_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv"
    )

# ============================================================================
# TENDER DETAIL VIEWER
# ============================================================================

st.markdown("---")
st.subheader("🔍 Tender Detail Viewer")

# Create columns for controls
col1, col2, col3 = st.columns([3, 1, 1])

with col1:
    # Filter for tenders in committee review
    committee_tenders = filtered_df[filtered_df['status'] == 'נדון בוועדת מכרזים'].copy()

    if len(committee_tenders) == 0:
        st.info("No tenders with status 'נדון בוועדת מכרזים' found. Adjust filters or select different status.")
        committee_tenders = filtered_df.head(50)  # Fallback to first 50

    # Sort by deadline descending (most recent first)
    committee_tenders = committee_tenders.sort_values('deadline', ascending=False)

    # Create display labels
    def format_tender_label(row):
        return f"{row['tender_id']} - {row['tender_name'][:50] if pd.notna(row['tender_name']) else 'N/A'} ({row['city'][:20] if pd.notna(row['city']) else 'N/A'})"

    committee_tenders['display_label'] = committee_tenders.apply(format_tender_label, axis=1)

    selected_tender_id = st.selectbox(
        "Select a tender to view details",
        options=committee_tenders['tender_id'].tolist(),
        format_func=lambda tid: committee_tenders[committee_tenders['tender_id']==tid]['display_label'].values[0]
    )

with col2:
    force_refresh = st.checkbox("Force refresh", value=False,
                                help="Bypass cache and fetch latest data from API")

with col3:
    # Bulk fetch button
    if st.button("📥 Fetch All", help=f"Fetch details for all {len(committee_tenders)} committee review tenders"):
        with st.spinner(f"Fetching details for {len(committee_tenders)} tenders..."):
            client = LandTendersClient(data_dir="data")
            tender_ids = committee_tenders['tender_id'].tolist()
            details_dict = client.fetch_multiple_details(tender_ids, max_workers=3, delay_seconds=1.0)

            st.success(f"✅ Fetched details for {len(details_dict)} tenders! They are now cached for instant viewing.")
            st.info(f"Cache saved to: data/details_cache/")

# Display selected tender details
if selected_tender_id:
    st.markdown("---")

    with st.spinner(f"Loading details for tender {selected_tender_id}..."):
        details = load_tender_details(selected_tender_id)

        # Also get list data for context
        list_data = filtered_df[filtered_df['tender_id'] == selected_tender_id]
        if len(list_data) > 0:
            list_data = list_data.iloc[0].to_dict()
        else:
            list_data = None

    if details:
        # Create expandable detail view
        with st.expander(f"📋 Tender {selected_tender_id} - Full Details", expanded=True):

            # Overview section
            st.markdown("### Overview")

            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric("Tender ID", details.get('MichrazID', selected_tender_id))
            with col2:
                st.metric("Status", list_data.get('status', 'N/A') if list_data else 'N/A')
            with col3:
                units = details.get('YechidotDiur', list_data.get('units', 0) if list_data else 0)
                st.metric("Units", f"{int(units):,}" if units else "N/A")
            with col4:
                deadline = pd.to_datetime(details.get('SgiraDate'), errors='coerce')
                if pd.notna(deadline):
                    # Convert to timezone-naive for comparison
                    deadline_naive = deadline.tz_localize(None) if deadline.tzinfo else deadline
                    days_until = (deadline_naive - datetime.now()).days
                    st.metric("Days Until Deadline", days_until)
                else:
                    st.metric("Deadline", "N/A")

            # Tender information
            st.markdown("---")
            st.markdown("### Tender Information")

            info_cols = st.columns(2)

            with info_cols[0]:
                st.write("**Tender Name:**", details.get('MichrazName', 'N/A'))
                st.write("**City:**", list_data.get('city', 'N/A') if list_data else 'N/A')
                # Show location (neighborhood/street) if available
                location = details.get('Shchuna', list_data.get('location', '') if list_data else '')
                if location:
                    st.write("**Location:**", location)
                st.write("**Type:**", list_data.get('tender_type', 'N/A') if list_data else 'N/A')

            with info_cols[1]:
                publish = pd.to_datetime(details.get('PtichaDate'), errors='coerce')
                st.write("**Publish Date:**", publish.strftime('%Y-%m-%d') if pd.notna(publish) else 'N/A')

                deadline = pd.to_datetime(details.get('SgiraDate'), errors='coerce')
                st.write("**Deadline:**", deadline.strftime('%Y-%m-%d %H:%M') if pd.notna(deadline) else 'N/A')

                committee = pd.to_datetime(details.get('VaadaDate'), errors='coerce')
                st.write("**Committee Date:**", committee.strftime('%Y-%m-%d') if pd.notna(committee) else 'N/A')

            # Bidder information section
            st.markdown("---")
            st.markdown("### 💰 Bidder Information")

            # Get plots (Tik)
            plots = details.get('Tik', [])

            if plots and len(plots) > 0:
                for plot_idx, plot in enumerate(plots, 1):
                    st.markdown(f"#### Plot {plot_idx}: {plot.get('TikID', 'N/A')}")

                    # Winner information
                    winner_name = (plot.get('ShemZoche') or '').strip()
                    winner_amount = plot.get('SchumZchiya', 0)

                    if winner_name:
                        st.success(f"🏆 **Winner:** {winner_name}")
                        winner_cols = st.columns(3)
                        with winner_cols[0]:
                            st.write("**Winning Bid:**", f"₪{winner_amount:,.2f}" if winner_amount else 'N/A')
                        with winner_cols[1]:
                            st.write("**Plot Area:**", f"{plot.get('Shetach', 0):,} sqm")
                        with winner_cols[2]:
                            st.write("**Min Price:**", f"₪{plot.get('MechirSaf', 0):,.2f}")

                    # Bidders list
                    bidders = plot.get('mpHatzaaotMitcham', [])

                    if bidders and len(bidders) > 0:
                        st.info(f"📊 **Total Bids:** {len(bidders)}")

                        # Convert to DataFrame for display
                        bidder_df = pd.DataFrame(bidders)
                        bidder_df = bidder_df.sort_values('HatzaaSum', ascending=False)  # Sort by amount

                        # Format the display
                        display_bidder_df = bidder_df.copy()
                        display_bidder_df['HatzaaSum'] = display_bidder_df['HatzaaSum'].apply(lambda x: f"₪{x:,.2f}" if pd.notna(x) else 'N/A')
                        display_bidder_df = display_bidder_df.rename(columns={
                            'HatzaaID': 'Bid ID',
                            'HatzaaSum': 'Bid Amount',
                            'HatzaaDescription': 'Description'
                        })

                        # Display as table
                        st.dataframe(
                            display_bidder_df,
                            use_container_width=True,
                            hide_index=True
                        )

                        # Offer CSV download of bidders
                        csv = bidder_df.to_csv(index=False, encoding='utf-8-sig')
                        st.download_button(
                            label=f"📥 Download Bidders CSV (Plot {plot_idx})",
                            data=csv,
                            file_name=f"bidders_{selected_tender_id}_plot{plot_idx}.csv",
                            mime="text/csv"
                        )
                    else:
                        st.info("No bids available for this plot")

                    if plot_idx < len(plots):
                        st.markdown("---")
            else:
                st.info("No bidder information available for this tender")

            # Documents section
            st.markdown("---")
            st.markdown("### 📄 Documents")

            docs = details.get('MichrazDocList', [])

            if docs and len(docs) > 0:
                st.info(f"📁 **Total Documents:** {len(docs)}")

                for doc in docs[:10]:  # Show first 10 documents
                    doc_name = doc.get('DocName', doc.get('Teur', 'Unknown'))
                    doc_desc = doc.get('Teur', 'No description')
                    doc_date = doc.get('UpdateDate', '')

                    st.markdown(f"- **{doc_name}** - {doc_desc} ({doc_date})")

                if len(docs) > 10:
                    st.caption(f"... and {len(docs) - 10} more documents")
            else:
                st.info("No documents available")

            # Link to official site
            st.markdown("---")
            official_url = f"https://apps.land.gov.il/MichrazimSite/#/michraz/{selected_tender_id}"
            st.markdown(f"🔗 [View on Official Land Authority Site]({official_url})")

            # Raw data for debugging (collapsed by default)
            with st.expander("🔧 Raw API Response (for debugging)"):
                st.json(details)

    else:
        st.error(f"❌ Failed to load details for tender {selected_tender_id}")
        st.info("This could mean:")
        st.write("- The tender ID does not exist in the detail API")
        st.write("- The API is currently unavailable")
        st.write("- Network connection issue")

# ============================================================================
# FOOTER / API STATUS
# ============================================================================

st.markdown("---")
with st.expander("🔧 Configuration & API Status"):
    st.markdown("""
    ### API Configuration Instructions
    
    To connect to the real data source:
    
    1. **Discover API endpoints:**
       - Open https://apps.land.gov.il/MichrazimSite/#/homePage in Chrome
       - Press F12 → Network tab → Filter by "XHR"
       - Browse the tenders list and look for API calls
    
    2. **Update `src/data_client.py`:**
       - Modify the `ENDPOINTS` dict with real URLs
       - Adjust the `fetch_tenders_list()` method based on API structure
       - Update `normalize_hebrew_columns()` mapping
    
    3. **Toggle off "Use Sample Data"** in the sidebar
    
    ### Current Status
    """)
    
    st.code(f"""
    Data source: {data_source}
    Records loaded: {len(df)}
    Filtered records: {len(filtered_df)}
    """)
