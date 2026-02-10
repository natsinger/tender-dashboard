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
def load_data(use_sample: bool = True) -> pd.DataFrame:
    """Load tender data - uses sample data until API is configured."""
    client = LandTendersClient(data_dir="data")
    
    if use_sample:
        df = generate_sample_data()
    else:
        # Try to fetch from API
        df = client.fetch_tenders_list()
        if df is None:
            st.warning("⚠️ Could not fetch from API. Using cached data if available...")
            df = client.load_latest_snapshot()
        if df is None:
            st.error("❌ No data available. Using sample data.")
            df = generate_sample_data()
    
    # Ensure date columns are datetime
    for col in ['publish_date', 'deadline']:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')
    
    return df

# ============================================================================
# SIDEBAR
# ============================================================================

with st.sidebar:
    st.image("https://www.gov.il/BlobFolder/generalpage/land-tenders/he/Michrazim_land-tenders_banner.jpg", 
             use_container_width=True)
    st.title("🏗️ מכרזי קרקע")
    st.markdown("---")
    
    # Data source toggle
    use_sample = st.toggle("Use Sample Data", value=True, 
                           help="Toggle off once API endpoints are configured")
    
    # Load data
    df = load_data(use_sample=use_sample)
    
    st.markdown("### 🔍 Filters")
    
    # City filter
    cities = ["All"] + sorted(df['city'].dropna().unique().tolist())
    selected_city = st.selectbox("City / עיר", cities)
    
    # Tender type filter
    types = ["All"] + sorted(df['tender_type'].dropna().unique().tolist())
    selected_type = st.selectbox("Type / סוג מכרז", types)
    
    # Status filter
    statuses = ["All"] + sorted(df['status'].dropna().unique().tolist())
    selected_status = st.selectbox("Status / סטטוס", statuses)
    
    # Date range filter
    st.markdown("#### 📅 Date Range")
    min_date = df['publish_date'].min()
    max_date = df['publish_date'].max()
    
    if pd.notna(min_date) and pd.notna(max_date):
        date_range = st.date_input(
            "Publish Date Range",
            value=(min_date.date(), max_date.date()),
            min_value=min_date.date(),
            max_value=max_date.date()
        )
    else:
        date_range = None
    
    st.markdown("---")
    st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    st.caption(f"Total records: {len(df)}")

# ============================================================================
# APPLY FILTERS
# ============================================================================

filtered_df = df.copy()

if selected_city != "All":
    filtered_df = filtered_df[filtered_df['city'] == selected_city]

if selected_type != "All":
    filtered_df = filtered_df[filtered_df['tender_type'] == selected_type]

if selected_status != "All":
    filtered_df = filtered_df[filtered_df['status'] == selected_status]

if date_range and len(date_range) == 2:
    start_date, end_date = date_range
    filtered_df = filtered_df[
        (filtered_df['publish_date'].dt.date >= start_date) & 
        (filtered_df['publish_date'].dt.date <= end_date)
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
    st.metric("🏠 Total Units", f"{total_units:,.0f}")

with col3:
    total_area = filtered_df['area_sqm'].sum()
    st.metric("📐 Total Area (sqm)", f"{total_area:,.0f}")

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

with col2:
    st.subheader("🏷️ Tenders by Type")
    type_counts = filtered_df['tender_type'].value_counts()
    fig_type = px.pie(
        values=type_counts.values,
        names=type_counts.index,
        hole=0.4,
        color_discrete_sequence=px.colors.qualitative.Set2
    )
    fig_type.update_layout(height=400)
    st.plotly_chart(fig_type, use_container_width=True)

# ============================================================================
# CHARTS ROW 2: Timeline & Price Analysis
# ============================================================================

col1, col2 = st.columns(2)

with col1:
    st.subheader("📈 Tenders Over Time")
    # Group by publish month
    timeline_df = filtered_df.copy()
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

with col2:
    st.subheader("💰 Minimum Price Distribution")
    # Filter out nulls and zeros
    price_df = filtered_df[filtered_df['min_price'] > 0]
    
    fig_price = px.histogram(
        price_df,
        x='min_price',
        nbins=20,
        labels={'min_price': 'Minimum Price (₪)'},
        color_discrete_sequence=['#1f77b4']
    )
    fig_price.update_layout(height=400)
    st.plotly_chart(fig_price, use_container_width=True)

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
default_cols = ['tender_id', 'city', 'tender_type', 'units', 'area_sqm', 'min_price', 'publish_date', 'deadline', 'status']
display_cols = [c for c in default_cols if c in all_cols]

selected_cols = st.multiselect("Select columns to display", all_cols, default=display_cols)

if selected_cols:
    display_df = filtered_df[selected_cols].copy()
    
    # Format date columns
    for col in ['publish_date', 'deadline']:
        if col in display_df.columns:
            display_df[col] = display_df[col].dt.strftime('%Y-%m-%d')
    
    st.dataframe(display_df, hide_index=True, use_container_width=True)
    
    # Download button
    csv = display_df.to_csv(index=False, encoding='utf-8-sig')
    st.download_button(
        label="📥 Download CSV",
        data=csv,
        file_name=f"land_tenders_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv"
    )

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
    Data source: {'Sample Data' if use_sample else 'API'}
    Records loaded: {len(df)}
    Filtered records: {len(filtered_df)}
    """)
