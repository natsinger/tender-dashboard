"""
Israel Land Tenders Dashboard (מכרזי קרקע)
==========================================
Executive-grade Streamlit dashboard for tracking land tenders from רמ"י.
Focused on three tender types: מכרז פומבי רגיל, מחיר מטרה, דיור במחיר מופחת.

Run with: streamlit run app.py
"""

import logging
import urllib.parse
from datetime import datetime, timedelta
from typing import Dict, Optional

import pandas as pd
import plotly.express as px
import streamlit as st

from config import (
    CACHE_TTL,
    CLOSING_SOON_DAYS,
    DATA_DIR,
    DEFAULT_FETCH_DELAY,
    DEFAULT_FETCH_WORKERS,
    DOCUMENT_DOWNLOAD_API,
    NON_ACTIVE_STATUSES,
    PROJECT_ROOT,
    RMI_SITE_URL,
)
from data_client import LandTendersClient, generate_sample_data

# ── Logging setup ─────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)


# ============================================================================
# PAGE CONFIG & STYLING
# ============================================================================

st.set_page_config(
    page_title="מכרזים",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── FIX: Load ALL Material fonts (Icons + Symbols) so dataframe sort arrows render as icons ──
st.markdown("""
<link href="https://fonts.googleapis.com/icon?family=Material+Icons" rel="stylesheet">
<link href="https://fonts.googleapis.com/icon?family=Material+Icons+Outlined" rel="stylesheet">
<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200" rel="stylesheet" />
<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200" rel="stylesheet" />
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700&display=swap" rel="stylesheet">
<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
""", unsafe_allow_html=True)


st.markdown("""
<style>
    /* ── Global RTL ── */
    html, body, [data-testid="stAppViewContainer"], .main .block-container {
        direction: rtl;
        text-align: right;
    }

    /* ── CRITICAL: Hide ALL Streamlit keyboard/input instruction overlays ── */
    [data-testid*="nstruction"],
    [class*="nstruction"],
    [class*="InputInstruction"],
    [data-testid="InputInstructions"],
    [data-testid="StyledThumbValue"],
    div[class*="InputInstruction"],
    div[class*="instruction"] {
        display: none !important;
        visibility: hidden !important;
        height: 0 !important;
        width: 0 !important;
        overflow: hidden !important;
        position: absolute !important;
        pointer-events: none !important;
        opacity: 0 !important;
    }

    /* ── Fix bidirectional text (Hebrew + numbers mix) ── */
    [data-testid="stExpander"] summary,
    [data-testid="stExpander"] summary span,
    .streamlit-expanderHeader,
    [data-testid="stMarkdownContainer"],
    [data-testid="stText"],
    [data-testid="stCaptionContainer"],
    p, span, label, li {
        unicode-bidi: plaintext;
    }

    /* Keep LTR for code / numbers where needed */
    code, pre, [data-testid="stMetricValue"] { direction: ltr; }

    /* ── Horizon Design Tokens ── */
    :root {
        --horizon-bg-main: #F4F7FE;
        --horizon-bg-card: #FFFFFF;
        --horizon-primary: #4318FF;
        --horizon-text-heading: #2B3674;
        --horizon-text-secondary: #A3AED0;
    }

    /* ── Typography & Foundation ── */
    html, body, [class*="st-"], [data-testid="stAppViewContainer"] {
        font-family: 'DM Sans', sans-serif !important;
        background-color: var(--horizon-bg-main) !important;
        color: var(--horizon-text-heading);
    }

    h1, h2, h3, h4, h5, h6, .stTabs button {
        font-family: 'DM Sans', sans-serif !important;
        color: var(--horizon-text-heading) !important;
    }

    .block-container { padding-top: 1.5rem; padding-bottom: 2rem; }

    /* ── Sort Icon Fix: Force Font & Align ── */
    [data-testid="stIconMaterial"] {
        font-family: 'Material Icons' !important;
        font-weight: normal;
        font-style: normal;
        font-size: 18px !important;
        visibility: visible !important;
        line-height: 1;
        direction: ltr;
        float: left !important;
    }

    /* ── Metric Cards (Horizon Style) ── */
    [data-testid="stMetric"] {
        background-color: var(--horizon-bg-card) !important;
        border-radius: 20px !important;
        border: none !important;
        box-shadow: 0px 18px 40px 0px rgba(112, 144, 176, 0.12) !important;
        padding: 20px !important;
    }
    [data-testid="stMetricValue"] {
        color: var(--horizon-text-heading) !important;
        font-weight: 700 !important;
        font-size: 26px !important;
    }
    [data-testid="stMetricLabel"] {
        color: var(--horizon-text-secondary) !important;
        font-weight: 500 !important;
        font-size: 14px !important;
    }

    /* ── Sidebar (Horizon Style) ── */
    section[data-testid="stSidebar"] > div {
        direction: rtl;
        text-align: right;
    }
    section[data-testid="stSidebar"] {
        background-color: var(--horizon-bg-card) !important;
        background-image: none !important;
        min-width: 285px !important;
        width: 285px !important;
        box-shadow: 1px 0px 20px rgba(0,0,0,0.02);
    }

    /* Default sidebar text */
    section[data-testid="stSidebar"] p,
    section[data-testid="stSidebar"] span,
    section[data-testid="stSidebar"] label {
        color: var(--horizon-text-secondary) !important;
    }

    /* Headers in sidebar */
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3 {
        color: var(--horizon-text-heading) !important;
    }

    /* Navigation/Inputs in sidebar */
    section[data-testid="stSidebar"] .stRadio label,
    section[data-testid="stSidebar"] .stMultiSelect label {
        color: var(--horizon-text-secondary) !important;
        font-weight: 500;
    }

    /* ── Tables (Horizon Borderless) ── */
    [data-testid="stDataFrame"], .stDataFrame {
        border: none !important;
    }

    /* ── Buttons (Horizon Pill) ── */
    .stButton button {
        background-color: var(--horizon-primary) !important;
        color: #FFFFFF !important;
        border-radius: 20px !important;
        border: none !important;
        padding: 10px 24px !important;
        font-weight: 500 !important;
        box-shadow: 0px 4px 10px rgba(67, 24, 255, 0.2) !important;
        transition: all 0.2s ease-in-out;
    }
    .stButton button:hover {
        box-shadow: 0px 8px 16px rgba(67, 24, 255, 0.3) !important;
        transform: translateY(-1px);
    }

    /* ── Chart Titles ── */
    .pie-title {
        font-family: 'DM Sans', sans-serif !important;
        color: var(--horizon-text-heading) !important;
        font-weight: 700 !important;
        font-size: 16px !important;
        margin-bottom: 10px !important;
        text-align: center !important;
    }

    /* ── Pill-style Radio Buttons (Main Area) ── */
    div[role="radiogroup"] {
        background-color: #FFFFFF;
        padding: 4px;
        border-radius: 12px;
        display: inline-flex;
        border: 1px solid #E0E5F2;
    }
    div[role="radiogroup"] label > div:first-child {
        display: none !important;
    }
    div[role="radiogroup"] label {
        padding: 6px 16px !important;
        border-radius: 8px !important;
        margin: 0 !important;
        transition: all 0.2s;
    }
    div[role="radiogroup"] label:hover {
        background-color: #F4F7FE;
    }

    /* ── Sidebar Toggle Fix (Force replace broken icons with Unicode) ── */
    [data-testid="stSidebarCollapseButton"] button,
    [data-testid="collapsedControl"] button,
    button[kind="header"] {
        border: none !important;
        background: transparent !important;
    }
    [data-testid="stSidebarCollapseButton"] button span,
    [data-testid="collapsedControl"] button span,
    button[kind="header"] span {
        display: none !important;
    }

    /* Collapsed state (Hamburger) */
    [data-testid="collapsedControl"] button::after,
    button[kind="header"]::after {
        content: "☰";
        font-size: 1.8rem;
        color: #1a1a2e;
        display: block;
        line-height: 1;
        cursor: pointer;
    }

    /* Expanded state (Close X) */
    [data-testid="stSidebarCollapseButton"] button::after {
        content: "✕";
        font-size: 1.5rem;
        color: #b8c4d4;
        display: block;
        line-height: 1;
        cursor: pointer;
    }

    /* ── Expander Arrow Fix (Hide arrow, keep clickable) ── */
    .streamlit-expanderHeader svg,
    .streamlit-expanderHeader span[data-testid="stExpanderToggleIcon"] {
        display: none !important;
    }
    .streamlit-expanderHeader {
        padding-right: 0px !important;
    }
    /* ── Sidebar custom header ── */
    .sidebar-header {
        background: linear-gradient(135deg, #0f3460 0%, #533483 100%);
        border-radius: 12px;
        padding: 20px 16px;
        text-align: center;
        margin-bottom: 12px;
    }
    .sidebar-header h2 {
        color: #ffffff !important;
        font-size: 1.4rem;
        margin: 0;
        text-align: center !important;
    }
    .sidebar-header p {
        color: #b8c4d4 !important;
        font-size: 0.85rem;
        margin: 6px 0 0 0;
        text-align: center !important;
    }

    /* ── New tenders highlight table ── */
    .new-tenders-card {
        background: linear-gradient(135deg, #e8f5e9 0%, #f1f8e9 100%);
        border: 1px solid #a5d6a7;
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 16px;
    }

    /* ── Expander styling ── */
    .streamlit-expanderHeader {
        font-weight: 600;
        direction: rtl;
        text-align: right;
    }
    [data-testid="stExpander"] details {
        direction: rtl;
    }

    /* ── Headers RTL with proper spacing ── */
    h1, h2, h3, h4, h5, h6 {
        direction: rtl;
        text-align: right;
        unicode-bidi: plaintext;
    }
    h2, h3 {
        margin-top: 0.8rem;
        margin-bottom: 0.6rem;
    }
    h4, h5, h6 {
        margin-top: 0.5rem;
        margin-bottom: 0.4rem;
    }

    /* ── Prevent text overflow globally ── */
    .detail-field {
        word-break: break-word;
        overflow-wrap: break-word;
        line-height: 1.6;
        font-size: 0.95rem;
        direction: rtl;
        unicode-bidi: plaintext;
    }
    .detail-field strong { color: #1a1a2e; }

    /* ── Column containers: prevent clipping ── */
    [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
        min-width: 0;
        overflow: visible;
    }
    [data-testid="stHorizontalBlock"] {
        gap: 1rem;
    }

    /* ── Plotly chart containers: no overflow ── */
    .stPlotlyChart {
        overflow: visible !important;
    }
    .js-plotly-plot, .plot-container {
        overflow: visible !important;
    }

    /* ── Divider colour ── */
    hr { border-color: #e0e3eb !important; }

    /* ── Subheader spacing fix ── */
    [data-testid="stSubheader"] {
        padding-bottom: 0.3rem;
        margin-bottom: 0.5rem;
    }

    /* ── Radio buttons inline fix ── */
    .stRadio > div {
        gap: 0.3rem;
    }
    .stRadio label {
        font-size: 0.85rem !important;
    }
</style>
""", unsafe_allow_html=True)

# ── JavaScript: Force-remove keyboard instruction overlays from DOM ──────
st.markdown("""
<script>
(function() {
    function removeInstructions() {
        document.querySelectorAll('[data-testid*="nstruction"]').forEach(el => el.remove());
        document.querySelectorAll('[data-testid="StyledThumbValue"]').forEach(el => el.remove());
        document.querySelectorAll('[class*="nstruction"]').forEach(el => el.remove());
        document.querySelectorAll('[class*="InputInstruction"]').forEach(el => el.remove());
        document.querySelectorAll('div, span, p, small').forEach(el => {
            const t = (el.textContent || '').trim().toLowerCase();
            if (t && (t.includes('keyboard') || t.includes('press ') ||
                t === 'double_arrow_left' || t === 'double_arrow_right' ||
                t.includes('\u2318') || t.includes('ctrl'))) {
                if (el.querySelectorAll('input, select, textarea, button, table, [data-testid="stDataFrame"]').length === 0) {
                    el.style.cssText = 'display:none!important;height:0!important;overflow:hidden!important;visibility:hidden!important;';
                }
            }
        });
    }
    removeInstructions();
    const observer = new MutationObserver(removeInstructions);
    observer.observe(document.body, { childList: true, subtree: true });
    [300, 800, 1500, 3000, 5000, 8000].forEach(ms => setTimeout(removeInstructions, ms));
})();
</script>
""", unsafe_allow_html=True)


# ============================================================================
# DATA LOADING
# ============================================================================

@st.cache_data(ttl=CACHE_TTL)
def load_data(data_source: str = "latest_file") -> pd.DataFrame:
    """Load tender data from API, JSON file, or sample data."""
    client = LandTendersClient(data_dir=str(PROJECT_ROOT))

    if data_source == "sample":
        return generate_sample_data()

    if data_source == "latest_file":
        df = client.load_latest_json_snapshot()
        if df is not None:
            return df
        logger.warning("No JSON files found, fetching from API")
        st.warning("לא נמצאו קבצי JSON, טוען מהAPI...")

    df = client.fetch_tenders_list()
    if df is None:
        logger.error("Could not fetch from API, falling back to sample data")
        st.error("לא ניתן לטעון מהAPI. מציג נתונים לדוגמה.")
        return generate_sample_data()

    client.save_json_snapshot(df)
    return df


@st.cache_data(ttl=CACHE_TTL)
def load_tender_details(tender_id: int) -> Optional[Dict]:
    """Load tender details with caching."""
    client = LandTendersClient(data_dir=str(DATA_DIR))
    return client.get_tender_details_cached(tender_id)


def build_document_url(doc: Dict) -> str:
    """Build a direct download URL for a tender document."""
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


# ============================================================================
# SIDEBAR
# ============================================================================

with st.sidebar:
    st.markdown("""
    <div class="sidebar-header">
        <h2>🏗️ מכרזי קרקע</h2>
        <p>רשות מקרקעי ישראל</p>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("---")

    data_source = "latest_file"
    df = load_data(data_source=data_source)
    today = datetime.now()

    st.markdown("---")

    # ── Filters ──────────────────────────────────────────────────────────
    st.markdown("### 🔍 סינון")

    # Region filter
    if 'region' in df.columns:
        regions = sorted(df['region'].dropna().unique().tolist())
        selected_regions = st.multiselect(
            "אזור / מחוז",
            regions,
            default=[],
            placeholder="בחר אזורים (ריק = הכל)"
        )
    else:
        selected_regions = []

    # City filter — cascades from region
    if selected_regions:
        cities_in_regions = df[df['region'].isin(selected_regions)]['city'].dropna().unique()
        cities = sorted(cities_in_regions.tolist())
        city_placeholder = f"ערים באזורים שנבחרו ({len(cities)})"
    else:
        cities = sorted(df['city'].dropna().unique().tolist())
        city_placeholder = "בחר ערים (ריק = הכל)"

    selected_cities = st.multiselect(
        "עיר / יישוב",
        cities,
        default=[],
        placeholder=city_placeholder
    )

    # Tender type filter
    types = sorted(df['tender_type'].dropna().unique().tolist())
    selected_types = st.multiselect(
        "סוג מכרז",
        types,
        default=[],
        placeholder="בחר סוגים (ריק = הכל)"
    )

    # Status filter
    statuses = sorted(df['status'].dropna().unique().tolist())
    selected_statuses = st.multiselect(
        "סטטוס",
        statuses,
        default=[],
        placeholder="בחר סטטוסים (ריק = הכל)"
    )

    st.markdown("---")
    st.caption(f"עדכון אחרון: {today.strftime('%Y-%m-%d %H:%M')}")
    st.caption(f"סה\"כ רשומות: {len(df):,}")


# ============================================================================
# APPLY FILTERS
# ============================================================================

filtered_df = df.copy()

if selected_regions:
    filtered_df = filtered_df[filtered_df['region'].isin(selected_regions)]

if selected_cities:
    filtered_df = filtered_df[filtered_df['city'].isin(selected_cities)]

if selected_types:
    filtered_df = filtered_df[filtered_df['tender_type'].isin(selected_types)]

if selected_statuses:
    filtered_df = filtered_df[filtered_df['status'].isin(selected_statuses)]

# Default active-only filter (unless user explicitly selected statuses)
if not selected_statuses:
    filtered_df = filtered_df[~filtered_df['status'].isin(NON_ACTIVE_STATUSES)]

# ============================================================================
# SECTION 0: NEW TENDERS THIS WEEK (since last Sunday)
# ============================================================================


def _last_sunday(ref_date: datetime) -> datetime:
    """Return the most recent Sunday (00:00) on or before ref_date."""
    days_since_sunday = ref_date.weekday() + 1
    if days_since_sunday == 7:
        days_since_sunday = 0
    return (ref_date - timedelta(days=days_since_sunday)).replace(
        hour=0, minute=0, second=0, microsecond=0,
    )


sunday_cutoff = _last_sunday(today)

# Filter: brochure available + still open
new_tenders_df = filtered_df[
    (filtered_df['published_booklet'] == True) &
    (filtered_df['deadline'].notna()) &
    (filtered_df['deadline'] >= today)
].copy()

# Use publish_date as the "new since" indicator
date_col = None
for candidate in ['created_date', 'publish_date', 'published_date']:
    if candidate in new_tenders_df.columns:
        date_col = candidate
        break

if date_col:
    new_tenders_df = new_tenders_df[new_tenders_df[date_col] >= sunday_cutoff]

st.title("🏗️ מכרזים")
st.caption(f"מעקב אחר מכרזי קרקע של רשות מקרקעי ישראל  •  מעודכן: {today.strftime('%d/%m/%Y')}")

if len(new_tenders_df) > 0:
    st.markdown('<div class="new-tenders-card">', unsafe_allow_html=True)
    st.markdown(f"### 🆕 מכרזים חדשים מיום ראשון ({sunday_cutoff.strftime('%d/%m')})")
    new_display = new_tenders_df[[
        'tender_name', 'city', 'units', 'tender_type', 'deadline'
    ]].copy()
    new_display.columns = ['שם מכרז', 'עיר', 'יח"ד', 'סוג', 'מועד אחרון']
    new_display['מועד אחרון'] = pd.to_datetime(new_display['מועד אחרון']).dt.strftime('%d/%m/%Y')
    new_display = new_display.sort_values('יח"ד', ascending=False)
    st.dataframe(
        new_display,
        use_container_width=True,
        hide_index=True,
        height=min(38 * len(new_display) + 40, 250),
    )
    st.markdown('</div>', unsafe_allow_html=True)
else:
    st.info(f"אין מכרזים חדשים עם חוברת מאז יום ראשון ({sunday_cutoff.strftime('%d/%m')})")

st.markdown("---")

# ============================================================================
# SECTION 1: EXECUTIVE KPIs
# ============================================================================

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("🟢 מכרזים פתוחים", f"{len(filtered_df):,}")

with col2:
    total_units = int(filtered_df['units'].sum())
    st.metric("🏠 יח\"ד", f"{total_units:,}")

with col3:
    unique_cities = filtered_df['city'].nunique()
    st.metric("🏙️ ערים", f"{unique_cities}")

with col4:
    closing_soon = len(filtered_df[
        (filtered_df['deadline'].notna()) &
        (filtered_df['deadline'] >= today) &
        (filtered_df['deadline'] <= today + timedelta(days=CLOSING_SOON_DAYS))
    ])
    st.metric(f"⏰ נסגרים ב-{CLOSING_SOON_DAYS} יום", closing_soon)

st.markdown("---")


# ============================================================================
# SECTION 2: THREE PIE CHARTS (side by side)
# ============================================================================

PLOTLY_FONT = dict(family="DM Sans, sans-serif", size=12, color="#2B3674")
PLOTLY_TRANSPARENT_BG = dict(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")

col_pie1, col_pie2, col_pie3 = st.columns(3)

# ── Pie Chart 1: Brochure Availability ────────────────────────────────────
with col_pie1:
    st.markdown('<p class="pie-title">📋 חוברת מכרז</p>', unsafe_allow_html=True)

    if 'published_booklet' in filtered_df.columns and len(filtered_df) > 0:
        booklet_counts = filtered_df['published_booklet'].value_counts()
        available = int(booklet_counts.get(True, 0))
        not_available = int(booklet_counts.get(False, 0))

        fig_booklet = px.pie(
            values=[available, not_available],
            names=["חוברת זמינה", "חוברת לא זמינה"],
            color_discrete_sequence=["#4318FF", "#E9EDF7"],
            hole=0.55,
        )
        fig_booklet.update_traces(
            textinfo='value',
            textposition='inside',
            textfont_size=14,
            hovertemplate='%{label}: %{value} (%{percent})<extra></extra>',
        )
        fig_booklet.update_layout(
            height=300,
            margin=dict(t=30, b=50, l=20, r=20),
            legend=dict(
                orientation="h", yanchor="top", y=-0.08,
                xanchor="center", x=0.5, font=dict(size=11),
            ),
            showlegend=True,
            font=PLOTLY_FONT,
            uniformtext_minsize=10, uniformtext_mode='hide',
            **PLOTLY_TRANSPARENT_BG,
        )
        st.plotly_chart(fig_booklet, use_container_width=True, key="pie_booklet")
    else:
        st.info("אין נתוני חוברת מכרז")

# ── Pie Chart 2: Brochure-only tenders by District + Urgency Toggle ──────
with col_pie2:
    st.markdown('<p class="pie-title">📋🗺️ חוברות לפי מחוז</p>', unsafe_allow_html=True)

    pie2_days_options = {"1W": 7, "2W": 14, "4W": 28}
    urgency_pie2 = st.session_state.get('urgency_pie2', '4W')
    pie2_days = pie2_days_options.get(urgency_pie2, 28)

    pie2_df = filtered_df[filtered_df['published_booklet'] == True].copy()
    pie2_cutoff = today + timedelta(days=pie2_days)
    pie2_df = pie2_df[
        (pie2_df['deadline'].notna()) &
        (pie2_df['deadline'] >= today) &
        (pie2_df['deadline'] <= pie2_cutoff)
    ]

    if 'region' in pie2_df.columns and len(pie2_df) > 0:
        brochure_by_region = (
            pie2_df.groupby('region')
            .size()
            .reset_index(name='count')
            .sort_values('count', ascending=False)
        )
        if not brochure_by_region.empty:
            fig_brochure_region = px.pie(
                brochure_by_region,
                values='count',
                names='region',
                hole=0.55,
                color_discrete_sequence=px.colors.sequential.Blues_r,
            )
            fig_brochure_region.update_traces(
                textinfo='value',
                textposition='inside',
                textfont_size=14,
                hovertemplate='%{label}: %{value} (%{percent})<extra></extra>',
            )
            fig_brochure_region.update_layout(
                height=300,
                margin=dict(t=30, b=20, l=10, r=10),
                showlegend=False,
                uniformtext_minsize=10, uniformtext_mode='hide',
                font=dict(family="DM Sans, sans-serif", size=11, color="#2B3674"),
                **PLOTLY_TRANSPARENT_BG,
            )
            st.plotly_chart(fig_brochure_region, use_container_width=True, key="pie_brochure_region")
        else:
            st.info("אין מכרזים עם חוברת בטווח שנבחר")
    else:
        st.info("אין נתונים")

    st.radio(
        "חלון סגירה:",
        list(pie2_days_options.keys()),
        index=2,
        horizontal=True,
        key="urgency_pie2",
    )

# ── Pie Chart 3: All tenders by District ──────────────────────────────────
with col_pie3:
    st.markdown('<p class="pie-title">מכרזים פעילים</p>', unsafe_allow_html=True)

    if 'region' in filtered_df.columns and len(filtered_df) > 0:
        tenders_by_region = (
            filtered_df.groupby('region')
            .size()
            .reset_index(name='count')
            .sort_values('count', ascending=False)
        )

        if not tenders_by_region.empty:
            fig_region = px.pie(
                tenders_by_region,
                values='count',
                names='region',
                hole=0.55,
                color_discrete_sequence=px.colors.sequential.Blues_r,
            )
            fig_region.update_traces(
                textinfo='value',
                textposition='inside',
                textfont_size=14,
                hovertemplate='%{label}: %{value} מכרזים (%{percent})<extra></extra>',
            )
            fig_region.update_layout(
                height=300,
                margin=dict(t=30, b=20, l=10, r=10),
                showlegend=False,
                uniformtext_minsize=10, uniformtext_mode='hide',
                font=dict(family="DM Sans, sans-serif", size=11, color="#2B3674"),
                **PLOTLY_TRANSPARENT_BG,
            )
            st.plotly_chart(fig_region, use_container_width=True, key="pie_region_units")

            with st.expander("📋 פירוט לפי מחוז"):
                for region_name in tenders_by_region['region'].tolist():
                    region_subset = filtered_df[filtered_df['region'] == region_name]
                    region_units = int(region_subset['units'].sum())
                    with st.expander(f"{region_name} — {region_units:,} יח\"ד ({len(region_subset)} מכרזים)"):
                        detail = region_subset.nlargest(8, 'units')[['tender_name', 'city', 'units', 'tender_type']].copy()
                        detail.columns = ['שם מכרז', 'עיר', 'יח"ד', 'סוג']
                        st.dataframe(detail, use_container_width=True, hide_index=True, height=min(38 * len(detail) + 40, 200))
        else:
            st.info("אין נתוני יח\"ד להצגה")
    else:
        st.info("אין נתוני אזור")

st.markdown("---")


# ============================================================================
# SECTION 3: UPCOMING DEADLINES TABLE (enhanced)
# ============================================================================

st.subheader("⏰ מכרזים קרובים לסגירה")

EXCLUDED_STATUSES = {"בוטל", "נסגר"}
upcoming = filtered_df[
    (filtered_df['deadline'].notna()) &
    (filtered_df['deadline'] >= today) &
    (~filtered_df['status'].isin(EXCLUDED_STATUSES))
].sort_values('deadline')

if len(upcoming) > 0:
    upcoming_display = upcoming[[
        'tender_id', 'tender_name', 'city', 'region', 'tender_type',
        'purpose', 'units', 'deadline', 'published_booklet'
    ]].copy()

    upcoming_display['days_left'] = (upcoming_display['deadline'] - today).dt.days

    def urgency_indicator(days: int) -> str:
        """Return urgency emoji based on days remaining."""
        if days <= 7:
            return '🔴'
        elif days <= 14:
            return '🟡'
        return '🟢'

    upcoming_display['urgency'] = upcoming_display['days_left'].apply(urgency_indicator)
    upcoming_display['booklet'] = upcoming_display['published_booklet'].apply(
        lambda x: '✅' if x else '❌'
    )

    display_upcoming = upcoming_display[[
        'urgency', 'tender_id', 'tender_name', 'city', 'region',
        'tender_type', 'purpose', 'units', 'deadline', 'days_left', 'booklet'
    ]].copy()
    display_upcoming['deadline'] = display_upcoming['deadline'].dt.strftime('%Y-%m-%d')

    st.info(f"מציג **{len(display_upcoming)}** מכרזים עם מועד סגירה עתידי")

    st.dataframe(
        display_upcoming,
        column_config={
            "urgency": st.column_config.TextColumn("", width="small"),
            "tender_id": st.column_config.NumberColumn("מס' מכרז", format="%d"),
            "tender_name": st.column_config.TextColumn("שם", width="medium"),
            "city": st.column_config.TextColumn("עיר", width="medium"),
            "region": st.column_config.TextColumn("מחוז", width="small"),
            "tender_type": st.column_config.TextColumn("סוג", width="medium"),
            "purpose": st.column_config.TextColumn("ייעוד", width="medium"),
            "units": st.column_config.NumberColumn("יח\"ד", format="%d"),
            "deadline": st.column_config.TextColumn("מועד סגירה"),
            "days_left": st.column_config.NumberColumn("ימים", format="%d"),
            "booklet": st.column_config.TextColumn("חוברת", width="small"),
        },
        hide_index=True,
        use_container_width=True,
    )
else:
    st.info("אין מכרזים קרובים לסגירה בטווח שנבחר.")

st.markdown("---")


# ============================================================================
# SECTION 4: FULL DATA EXPLORER
# ============================================================================

st.subheader("📋 כל המכרזים")

COLUMN_LABELS = {
    "tender_id": "מס' מכרז",
    "tender_name": "שם מכרז",
    "city": "עיר",
    "region": "מחוז",
    "tender_type": "סוג מכרז",
    "purpose": "ייעוד",
    "units": "יח\"ד",
    "deadline": "מועד סגירה",
    "publish_date": "תאריך פרסום",
    "committee_date": "תאריך ועדה",
    "status": "סטטוס",
    "published_booklet": "חוברת מכרז",
    "location": "מיקום",
    "targeted": "מכוון",
}

HIDDEN_COLUMNS = {
    'city_code', 'status_code', 'purpose_code', 'tender_type_code',
    'KodMerchav', 'KhalYaadRashi', 'PirsumDate', 'ChoveretUpdateDate',
    'area_sqm', 'min_price', 'gush', 'helka',
}

user_cols = [c for c in filtered_df.columns if c not in HIDDEN_COLUMNS]
default_cols = [
    'tender_id', 'tender_name', 'city', 'region', 'tender_type',
    'purpose', 'units', 'deadline', 'status', 'published_booklet'
]
display_cols = [c for c in default_cols if c in user_cols]

selected_cols = st.multiselect(
    "בחר עמודות להצגה",
    user_cols,
    default=display_cols,
    format_func=lambda c: COLUMN_LABELS.get(c, c),
)

# ── Per-column filters ──────────────────────────────────────────────────
st.markdown("##### סינון לפי עמודה")
filter_cols = st.columns(4)

table_df = filtered_df.copy()

with filter_cols[0]:
    if 'city' in table_df.columns:
        city_vals = sorted(table_df['city'].dropna().unique().tolist())
        tbl_city = st.multiselect(
            "עיר", city_vals, default=[], key="tbl_city",
            placeholder="הכל",
        )
        if tbl_city:
            table_df = table_df[table_df['city'].isin(tbl_city)]

with filter_cols[1]:
    if 'region' in table_df.columns:
        region_vals = sorted(table_df['region'].dropna().unique().tolist())
        tbl_region = st.multiselect(
            "מחוז", region_vals, default=[], key="tbl_region",
            placeholder="הכל",
        )
        if tbl_region:
            table_df = table_df[table_df['region'].isin(tbl_region)]

with filter_cols[2]:
    if 'purpose' in table_df.columns:
        purpose_vals = sorted(table_df['purpose'].dropna().unique().tolist())
        tbl_purpose = st.multiselect(
            "ייעוד", purpose_vals, default=[], key="tbl_purpose",
            placeholder="הכל",
        )
        if tbl_purpose:
            table_df = table_df[table_df['purpose'].isin(tbl_purpose)]

with filter_cols[3]:
    if 'status' in table_df.columns:
        status_vals = sorted(table_df['status'].dropna().unique().tolist())
        tbl_status = st.multiselect(
            "סטטוס", status_vals, default=[], key="tbl_status",
            placeholder="הכל",
        )
        if tbl_status:
            table_df = table_df[table_df['status'].isin(tbl_status)]

search_term = st.text_input(
    "🔍 חיפוש חופשי", placeholder="הקלד לחיפוש בכל העמודות..."
)

if selected_cols:
    display_df = table_df[selected_cols].copy()

    if search_term:
        mask = display_df.astype(str).apply(
            lambda row: row.str.contains(search_term, case=False, na=False).any(),
            axis=1
        )
        display_df = display_df[mask]

    st.caption(f"מציג {len(display_df):,} רשומות")

    if 'deadline' in display_df.columns:
        display_df = display_df.sort_values(
            'deadline', ascending=True, na_position='last'
        )

    display_df_formatted = display_df.copy()

    for col in ['publish_date', 'deadline', 'committee_date']:
        if col in display_df_formatted.columns:
            display_df_formatted[col] = pd.to_datetime(
                display_df_formatted[col], errors='coerce'
            )

    if 'tender_id' in display_df_formatted.columns:
        display_df_formatted['tender_id'] = (
            display_df_formatted['tender_id'].astype(str)
        )

    st.dataframe(
        display_df_formatted,
        hide_index=True,
        use_container_width=True,
        column_config={
            "tender_id": st.column_config.TextColumn("מס' מכרז", width="medium"),
            "tender_name": st.column_config.TextColumn("שם מכרז", width="large"),
            "city": st.column_config.TextColumn("עיר", width="medium"),
            "region": st.column_config.TextColumn("מחוז", width="small"),
            "tender_type": st.column_config.TextColumn("סוג", width="medium"),
            "purpose": st.column_config.TextColumn("ייעוד", width="medium"),
            "units": st.column_config.NumberColumn("יח\"ד", format="%d"),
            "deadline": st.column_config.DateColumn("מועד סגירה", format="YYYY-MM-DD"),
            "publish_date": st.column_config.DateColumn("תאריך פרסום", format="YYYY-MM-DD"),
            "committee_date": st.column_config.DateColumn("תאריך ועדה", format="YYYY-MM-DD"),
            "status": st.column_config.TextColumn("סטטוס", width="small"),
            "published_booklet": st.column_config.CheckboxColumn("חוברת"),
            "location": st.column_config.TextColumn("מיקום", width="medium"),
        },
    )

    csv = display_df.to_csv(index=False, encoding='utf-8-sig')
    st.download_button(
        label="📥 הורד CSV",
        data=csv,
        file_name=f"land_tenders_{today.strftime('%Y%m%d')}.csv",
        mime="text/csv"
    )

st.markdown("---")


# ============================================================================
# SECTION 5: TENDER DETAIL VIEWER
# ============================================================================

st.subheader("🔍 צפייה בפרטי מכרז")

col_select, col_refresh, col_fetch = st.columns([3, 1, 1])

with col_select:
    detail_candidates = filtered_df.copy()
    if len(detail_candidates) == 0:
        detail_candidates = df.head(50)

    detail_candidates = detail_candidates.sort_values('deadline', ascending=False)

    def format_tender_label(row: pd.Series) -> str:
        """Format tender row for selectbox display."""
        name = row['tender_name'][:50] if pd.notna(row['tender_name']) else 'N/A'
        city = row['city'][:20] if pd.notna(row['city']) else 'N/A'
        return f"{row['tender_id']} - {name} ({city})"

    detail_candidates['display_label'] = detail_candidates.apply(format_tender_label, axis=1)

    selected_tender_id = st.selectbox(
        "בחר מכרז לצפייה",
        options=detail_candidates['tender_id'].tolist(),
        format_func=lambda tid: detail_candidates[
            detail_candidates['tender_id'] == tid
        ]['display_label'].values[0]
    )

with col_refresh:
    force_refresh = st.checkbox(
        "רענן מהAPI",
        value=False,
        help="עקוף מטמון וטען נתונים חדשים"
    )

with col_fetch:
    if st.button(
        "📥 טען הכל",
        help=f"טען פרטים עבור {len(detail_candidates)} מכרזים"
    ):
        with st.spinner(f"טוען פרטים עבור {len(detail_candidates)} מכרזים..."):
            client = LandTendersClient(data_dir=str(DATA_DIR))
            tender_ids = detail_candidates['tender_id'].tolist()
            details_dict = client.fetch_multiple_details(
                tender_ids,
                max_workers=DEFAULT_FETCH_WORKERS,
                delay_seconds=DEFAULT_FETCH_DELAY,
            )
            st.success(f"נטענו פרטים עבור {len(details_dict)} מכרזים!")

# Display selected tender details
if selected_tender_id:
    st.markdown("---")

    with st.spinner(f"טוען פרטי מכרז {selected_tender_id}..."):
        details = load_tender_details(selected_tender_id)

        list_data = filtered_df[filtered_df['tender_id'] == selected_tender_id]
        if len(list_data) > 0:
            list_data = list_data.iloc[0].to_dict()
        else:
            list_data = None

    if details:
        with st.expander(f"📋 מכרז {selected_tender_id} — פרטים מלאים", expanded=True):

            st.markdown("### סקירה כללית")
            ov1, ov2, ov3, ov4 = st.columns(4)

            with ov1:
                st.metric("מס' מכרז", details.get('MichrazID', selected_tender_id))
            with ov2:
                st.metric("סטטוס", list_data.get('status', 'N/A') if list_data else 'N/A')
            with ov3:
                units = details.get(
                    'YechidotDiur',
                    list_data.get('units', 0) if list_data else 0
                )
                st.metric("יח\"ד", f"{int(units):,}" if units else "N/A")
            with ov4:
                deadline_dt = pd.to_datetime(details.get('SgiraDate'), errors='coerce')
                if pd.notna(deadline_dt):
                    deadline_naive = (
                        deadline_dt.tz_localize(None) if deadline_dt.tzinfo else deadline_dt
                    )
                    days_until = (deadline_naive - today).days
                    st.metric("ימים לסגירה", days_until)
                else:
                    st.metric("מועד סגירה", "N/A")

            st.markdown("---")
            st.markdown("### פרטי מכרז")

            info_left, info_right = st.columns(2)

            with info_left:
                tender_name = details.get('MichrazName', 'N/A')
                city_val = list_data.get('city', 'N/A') if list_data else 'N/A'
                location = details.get('Shchuna', list_data.get('location', '') if list_data else '')
                tender_type_val = list_data.get('tender_type', 'N/A') if list_data else 'N/A'
                purpose_val = list_data.get('purpose', 'N/A') if list_data else 'N/A'

                info_html = f'''
                <div class="detail-field">
                    <strong>שם מכרז:</strong> {tender_name}<br>
                    <strong>עיר:</strong> {city_val}<br>
                    {'<strong>מיקום:</strong> ' + str(location) + '<br>' if location else ''}
                    <strong>סוג:</strong> {tender_type_val}<br>
                    <strong>ייעוד:</strong> {purpose_val}
                </div>
                '''
                st.markdown(info_html, unsafe_allow_html=True)

            with info_right:
                publish = pd.to_datetime(details.get('PtichaDate'), errors='coerce')
                publish_str = publish.strftime('%Y-%m-%d') if pd.notna(publish) else 'N/A'
                deadline_dt = pd.to_datetime(details.get('SgiraDate'), errors='coerce')
                deadline_str = deadline_dt.strftime('%Y-%m-%d %H:%M') if pd.notna(deadline_dt) else 'N/A'
                committee = pd.to_datetime(details.get('VaadaDate'), errors='coerce')
                committee_str = committee.strftime('%Y-%m-%d') if pd.notna(committee) else 'N/A'

                dates_html = f'''
                <div class="detail-field">
                    <strong>תאריך פרסום:</strong> {publish_str}<br>
                    <strong>מועד סגירה:</strong> {deadline_str}<br>
                    <strong>תאריך ועדה:</strong> {committee_str}
                </div>
                '''
                st.markdown(dates_html, unsafe_allow_html=True)

            st.markdown("---")
            st.markdown("### 💰 הצעות ומציעים")

            plots = details.get('Tik', [])

            if plots:
                for plot_idx, plot in enumerate(plots, 1):
                    st.markdown(f"#### מגרש {plot_idx}: {plot.get('TikID', 'N/A')}")

                    winner_name = (plot.get('ShemZoche') or '').strip()
                    winner_amount = plot.get('SchumZchiya', 0)

                    if winner_name:
                        st.success(f"🏆 **זוכה:** {winner_name}")
                        winner_amount_str = f"₪{winner_amount:,.2f}" if winner_amount else 'N/A'
                        area_str = f"{plot.get('Shetach', 0):,} מ\"ר"
                        threshold_str = f"₪{plot.get('MechirSaf', 0):,.2f}"
                        bid_html = f'''
                        <div class="detail-field">
                            <strong>סכום זכייה:</strong> {winner_amount_str} &nbsp;|&nbsp;
                            <strong>שטח:</strong> {area_str} &nbsp;|&nbsp;
                            <strong>מחיר סף:</strong> {threshold_str}
                        </div>
                        '''
                        st.markdown(bid_html, unsafe_allow_html=True)

                    bidders = plot.get('mpHatzaaotMitcham', [])
                    if bidders:
                        st.info(f"📊 **סה\"כ הצעות:** {len(bidders)}")

                        bidder_df = pd.DataFrame(bidders)
                        bidder_df = bidder_df.sort_values('HatzaaSum', ascending=False)

                        display_bidder_df = bidder_df.copy()
                        display_bidder_df['HatzaaSum'] = display_bidder_df['HatzaaSum'].apply(
                            lambda x: f"₪{x:,.2f}" if pd.notna(x) else 'N/A'
                        )
                        display_bidder_df = display_bidder_df.rename(columns={
                            'HatzaaID': 'מס\' הצעה',
                            'HatzaaSum': 'סכום',
                            'HatzaaDescription': 'תיאור'
                        })

                        st.dataframe(
                            display_bidder_df,
                            use_container_width=True,
                            hide_index=True
                        )

                        csv_bid = bidder_df.to_csv(index=False, encoding='utf-8-sig')
                        st.download_button(
                            label=f"📥 הורד CSV מציעים (מגרש {plot_idx})",
                            data=csv_bid,
                            file_name=f"bidders_{selected_tender_id}_plot{plot_idx}.csv",
                            mime="text/csv"
                        )
                    else:
                        st.info("אין הצעות למגרש זה")

                    if plot_idx < len(plots):
                        st.markdown("---")
            else:
                st.info("אין מידע על הצעות למכרז זה")

            st.markdown("---")
            st.markdown("### 📄 מסמכים")

            full_doc = details.get('MichrazFullDocument')
            if full_doc and full_doc.get('RowID') is not None:
                doc_name = full_doc.get('DocName', 'מסמך פרסום מלא.pdf')
                doc_url = build_document_url(full_doc)
                st.markdown(
                    f"#### 📕 מסמך פרסום מלא\n\n"
                    f"[📥 **הורד: {doc_name}**]({doc_url})"
                )

            docs = details.get('MichrazDocList', [])
            if docs:
                st.markdown(f"#### 📁 מסמכים נוספים ({len(docs)})")
                for doc in docs[:15]:
                    doc_name = doc.get('DocName', doc.get('Teur', 'Unknown'))
                    doc_desc = doc.get('Teur', '')
                    doc_date = doc.get('UpdateDate', '')
                    if doc_date:
                        date_formatted = pd.to_datetime(doc_date, errors='coerce')
                        if pd.notna(date_formatted):
                            doc_date = date_formatted.strftime('%Y-%m-%d')

                    doc_url = build_document_url(doc)
                    st.markdown(
                        f"- [{doc_name}]({doc_url}) — {doc_desc} ({doc_date})"
                    )

                if len(docs) > 15:
                    st.caption(f"... ועוד {len(docs) - 15} מסמכים")

            elif not full_doc:
                st.info("אין מסמכים זמינים")

            st.markdown("---")
            official_url = f"{RMI_SITE_URL}/{selected_tender_id}"
            st.markdown(f"🔗 [צפה באתר רמ\"י הרשמי]({official_url})")

    else:
        st.error(f"לא ניתן לטעון פרטים למכרז {selected_tender_id}")
        st.info("יתכן שמזהה המכרז לא קיים, או שהAPI אינו זמין.")

st.markdown("---")


# ============================================================================
# SECTION 6: DETAILED ANALYTICS (collapsible)
# ============================================================================

with st.expander("📊 ניתוח מפורט", expanded=False):

    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        st.subheader("📍 מכרזים לפי עיר")
        city_counts = filtered_df['city'].value_counts().head(10)

        if len(city_counts) > 0:
            fig_city = px.bar(
                x=city_counts.values,
                y=city_counts.index,
                orientation='h',
                labels={'x': 'מספר מכרזים', 'y': 'עיר'},
                color=city_counts.values,
                color_continuous_scale='Blues'
            )
            fig_city.update_layout(showlegend=False, height=400)
            st.plotly_chart(fig_city, use_container_width=True)
        else:
            st.info("אין נתונים להצגה")

    with chart_col2:
        st.subheader("🏷️ מכרזים לפי סוג")
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
            st.info("אין נתונים להצגה")

    chart_col3, chart_col4 = st.columns(2)

    with chart_col3:
        st.subheader("📈 מכרזים לאורך זמן")
        timeline_df = filtered_df.copy()

        if len(timeline_df) > 0 and timeline_df['publish_date'].notna().any():
            timeline_df['month'] = timeline_df['publish_date'].dt.to_period('M').astype(str)
            monthly_counts = timeline_df.groupby('month').size().reset_index(name='count')

            fig_timeline = px.line(
                monthly_counts,
                x='month',
                y='count',
                markers=True,
                labels={'month': 'חודש', 'count': 'מספר מכרזים'}
            )
            fig_timeline.update_layout(height=400)
            st.plotly_chart(fig_timeline, use_container_width=True)
        else:
            st.info("אין נתוני תאריכים להצגה")

    with chart_col4:
        st.subheader("🏠 יח\"ד לפי סוג מכרז")
        units_by_type = filtered_df.groupby('tender_type')['units'].sum().reset_index()
        units_by_type = units_by_type[units_by_type['units'] > 0]

        if not units_by_type.empty:
            fig_units = px.bar(
                units_by_type,
                x='tender_type',
                y='units',
                labels={'units': 'סה\"כ יח\"ד', 'tender_type': 'סוג מכרז'},
                color_discrete_sequence=['#1f77b4']
            )
            fig_units.update_layout(height=400)
            st.plotly_chart(fig_units, use_container_width=True)
        else:
            st.info("אין נתוני יח\"ד להצגה")


# ============================================================================
# SECTION 7: ADMIN / DEBUG (collapsible)
# ============================================================================

with st.expander("🔧 ניהול ודיבוג", expanded=False):
    st.markdown("### סטטוס מערכת")
    st.code(f"""
    מקור נתונים: {data_source}
    רשומות שנטענו: {len(df):,}
    רשומות מסוננות: {len(filtered_df):,}
    סוגי מכרז: {', '.join(df['tender_type'].unique().tolist())}
    """)

    st.markdown("### API Endpoints")
    st.code(f"""
    List: {LAND_AUTHORITY_API} (POST)
    Detail: {TENDER_DETAIL_API}?michrazID=
    Docs: {DOCUMENT_DOWNLOAD_API}
    """)
