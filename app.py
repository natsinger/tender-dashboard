"""
MEGIDO Tender Intelligence Dashboard (מגידו | מכרזי קרקע)
==========================================================
Multipage Streamlit dashboard for tracking land tenders from רמ"י.
Two views: full dashboard for daily users, management overview for executives.
Branded for MEGIDO BY AURA (מגידו י.ק.).

Run with: streamlit run app.py
"""

import logging

import streamlit as st

# ── Logging setup ─────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
)

# ============================================================================
# PAGE CONFIG
# ============================================================================

st.set_page_config(
    page_title="MEGIDO | מגידו",
    page_icon="M",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Load fonts ──
st.markdown("""
<link href="https://fonts.googleapis.com/icon?family=Material+Icons" rel="stylesheet">
<link href="https://fonts.googleapis.com/icon?family=Material+Icons+Outlined" rel="stylesheet">
<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200" rel="stylesheet" />
<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200" rel="stylesheet" />
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<link href="https://fonts.googleapis.com/css2?family=Heebo:wght@400;500;600;700&display=swap" rel="stylesheet">
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
""", unsafe_allow_html=True)


# ============================================================================
# SHARED CSS — Card-based design with light sidebar
# ============================================================================

st.markdown("""
<style>
    /* ── Global RTL ── */
    html, body, [data-testid="stAppViewContainer"], .main .block-container {
        direction: rtl;
        text-align: right;
    }

    /* ── Hide keyboard shortcut hints ── */
    [data-testid="InputInstructions"],
    [data-testid="StyledThumbValue"] {
        display: none !important;
        visibility: hidden !important;
        height: 0 !important;
        overflow: hidden !important;
    }

    /* ── Bidi text fix ── */
    [data-testid="stExpander"] summary,
    [data-testid="stExpander"] summary span,
    .streamlit-expanderHeader,
    [data-testid="stMarkdownContainer"],
    [data-testid="stText"],
    [data-testid="stCaptionContainer"],
    p, span, label, li {
        unicode-bidi: plaintext;
    }
    code, pre, [data-testid="stMetricValue"] { direction: ltr; }

    /* ── Design Tokens ── */
    :root {
        --mg-bg-main: #F3F4F6;
        --mg-bg-card: #FFFFFF;
        --mg-bg-sidebar: #FFFFFF;
        --mg-primary: #1B6B3A;
        --mg-primary-light: #E8F5E9;
        --mg-primary-hover: #155D30;
        --mg-gold: #D4A017;
        --mg-text-heading: #111827;
        --mg-text-body: #374151;
        --mg-text-muted: #9CA3AF;
        --mg-text-section: #6B7280;
        --mg-border: #E5E7EB;
        --mg-border-light: #F0F0F0;
        --mg-shadow-sm: 0 1px 2px rgba(0,0,0,0.04);
        --mg-shadow-md: 0 2px 8px rgba(0,0,0,0.06);
        --mg-radius: 16px;
        --mg-radius-sm: 12px;
    }

    /* ── Typography ── */
    html, body, [class*="st-"], [data-testid="stAppViewContainer"] {
        font-family: 'Inter', 'Heebo', -apple-system, BlinkMacSystemFont, sans-serif !important;
        background-color: var(--mg-bg-main) !important;
        color: var(--mg-text-body);
    }
    h1, h2, h3, h4, h5, h6, .stTabs button {
        font-family: 'Inter', 'Heebo', -apple-system, sans-serif !important;
        color: var(--mg-text-heading) !important;
    }
    code, pre { font-family: 'JetBrains Mono', monospace !important; }

    .block-container { padding-top: 1rem; padding-bottom: 1rem; }

    /* ── Sort Icon Fix ── */
    [data-testid="stIconMaterial"] {
        font-family: 'Material Icons' !important;
        font-weight: normal; font-style: normal;
        font-size: 18px !important;
        visibility: visible !important;
        line-height: 1; direction: ltr;
        float: left !important;
    }

    /* ══════════════════════════════════════════════════════════════════
       METRIC CARDS — white cards, first one highlighted
       ══════════════════════════════════════════════════════════════════ */
    [data-testid="stMetric"] {
        background-color: var(--mg-bg-card) !important;
        border-radius: var(--mg-radius) !important;
        border: 1px solid var(--mg-border-light) !important;
        box-shadow: var(--mg-shadow-sm) !important;
        padding: 16px 20px !important;
        position: relative;
    }
    [data-testid="stMetric"]::before {
        content: none !important;
    }
    [data-testid="stMetricValue"] {
        color: var(--mg-text-heading) !important;
        font-weight: 700 !important;
        font-size: 28px !important;
    }
    [data-testid="stMetricLabel"] {
        color: var(--mg-text-muted) !important;
        font-weight: 500 !important;
        font-size: 12px !important;
        text-transform: uppercase;
        letter-spacing: 0.03em;
    }

    /* Highlighted primary KPI (first column) */
    .kpi-primary [data-testid="stMetric"] {
        background: linear-gradient(135deg, #1B6B3A 0%, #2D8B4E 100%) !important;
        border: none !important;
        box-shadow: 0 4px 12px rgba(27, 107, 58, 0.25) !important;
    }
    .kpi-primary [data-testid="stMetricValue"] {
        color: #FFFFFF !important;
    }
    .kpi-primary [data-testid="stMetricLabel"] {
        color: rgba(255,255,255,0.75) !important;
    }

    /* ══════════════════════════════════════════════════════════════════
       SIDEBAR — Light, clean
       ══════════════════════════════════════════════════════════════════ */
    section[data-testid="stSidebar"] > div {
        direction: rtl;
        text-align: right;
    }
    section[data-testid="stSidebar"] {
        background-color: var(--mg-bg-sidebar) !important;
        background-image: none !important;
        min-width: 270px !important;
        width: 270px !important;
        border-left: 1px solid var(--mg-border) !important;
        box-shadow: none !important;
    }

    /* Sidebar text */
    section[data-testid="stSidebar"] p,
    section[data-testid="stSidebar"] span,
    section[data-testid="stSidebar"] label {
        color: var(--mg-text-body) !important;
    }
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3,
    section[data-testid="stSidebar"] h4 {
        color: var(--mg-text-heading) !important;
    }

    /* Sidebar section labels (small caps) */
    .sidebar-section-label {
        font-size: 0.7rem;
        font-weight: 600;
        color: var(--mg-text-muted) !important;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin: 16px 0 8px 0;
    }

    /* Sidebar widgets — default light theme */
    section[data-testid="stSidebar"] [data-baseweb="select"],
    section[data-testid="stSidebar"] [data-baseweb="input"] {
        background-color: #F9FAFB !important;
        border-color: var(--mg-border) !important;
        border-radius: 10px !important;
    }
    section[data-testid="stSidebar"] [data-baseweb="select"] input,
    section[data-testid="stSidebar"] [data-baseweb="input"] input {
        color: var(--mg-text-heading) !important;
    }
    section[data-testid="stSidebar"] [data-baseweb="tag"] {
        background-color: var(--mg-primary) !important;
        color: #FFFFFF !important;
        border-radius: 6px !important;
    }
    section[data-testid="stSidebar"] input,
    section[data-testid="stSidebar"] textarea {
        color: var(--mg-text-heading) !important;
        background-color: #F9FAFB !important;
        border-color: var(--mg-border) !important;
    }
    section[data-testid="stSidebar"] input::placeholder,
    section[data-testid="stSidebar"] textarea::placeholder {
        color: var(--mg-text-muted) !important;
    }
    section[data-testid="stSidebar"] [data-testid="stTextInput"] > div,
    section[data-testid="stSidebar"] [data-testid="stPasswordInput"] > div {
        background-color: #F9FAFB !important;
        border-color: var(--mg-border) !important;
    }

    /* Sidebar dividers */
    section[data-testid="stSidebar"] hr {
        border-color: var(--mg-border) !important;
        margin: 12px 0 !important;
    }
    section[data-testid="stSidebar"] [data-testid="stCaptionContainer"] {
        color: var(--mg-text-muted) !important;
    }

    /* ══════════════════════════════════════════════════════════════════
       CARDS — dashboard-card class for section containers
       ══════════════════════════════════════════════════════════════════ */
    .dashboard-card {
        background: var(--mg-bg-card);
        border-radius: var(--mg-radius);
        padding: 20px;
        box-shadow: var(--mg-shadow-sm);
        border: 1px solid var(--mg-border-light);
        margin-bottom: 12px;
    }
    .dashboard-card-title {
        font-size: 0.85rem;
        font-weight: 600;
        color: var(--mg-text-heading);
        margin: 0 0 12px 0;
    }

    /* Style st.container(border=True) as cards */
    [data-testid="stVerticalBlock"] > div > [data-testid="stVerticalBlockBorderWrapper"] {
        background: var(--mg-bg-card) !important;
        border-radius: var(--mg-radius) !important;
        border: 1px solid var(--mg-border-light) !important;
        box-shadow: var(--mg-shadow-sm) !important;
        padding: 4px !important;
    }

    /* ── Tables ── */
    [data-testid="stDataFrame"], .stDataFrame {
        border: 1px solid var(--mg-border-light) !important;
        border-radius: var(--mg-radius-sm) !important;
        overflow: hidden;
    }

    /* ── Buttons ── */
    .stButton button {
        background-color: var(--mg-primary) !important;
        color: #FFFFFF !important;
        border-radius: 10px !important;
        border: none !important;
        padding: 8px 20px !important;
        font-weight: 600 !important;
        font-size: 0.85rem !important;
        box-shadow: var(--mg-shadow-sm) !important;
        transition: all 0.15s ease;
    }
    .stButton button:hover {
        background-color: var(--mg-primary-hover) !important;
        box-shadow: var(--mg-shadow-md) !important;
        transform: translateY(-1px);
    }

    /* ── Chart Titles ── */
    .pie-title {
        font-family: 'Inter', 'Heebo', sans-serif !important;
        color: var(--mg-text-heading) !important;
        font-weight: 600 !important;
        font-size: 13px !important;
        margin-bottom: 8px !important;
        text-align: center !important;
    }

    /* ── Pill Radio Buttons ── */
    div[role="radiogroup"] {
        background-color: #F3F4F6;
        padding: 2px;
        border-radius: 8px;
        display: inline-flex;
        border: 1px solid var(--mg-border);
        gap: 1px;
    }
    div[role="radiogroup"] label > div:first-child {
        display: none !important;
    }
    div[role="radiogroup"] label {
        padding: 2px 8px !important;
        border-radius: 6px !important;
        margin: 0 !important;
        font-size: 0.65rem !important;
        cursor: pointer;
        line-height: 1.4;
        transition: all 0.15s ease;
    }
    div[role="radiogroup"] label:hover {
        background-color: #E8F5E9;
    }
    div[role="radiogroup"] label[data-checked="true"],
    div[role="radiogroup"] label:has(input:checked) {
        background-color: var(--mg-primary) !important;
        color: #FFFFFF !important;
        font-weight: 600 !important;
    }
    [data-testid="stColumn"] .stRadio > div {
        justify-content: center;
    }
    [data-testid="stColumn"] .stRadio {
        margin-top: -8px;
        margin-bottom: 0;
    }

    /* ── Sidebar Toggle ── */
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
    [data-testid="collapsedControl"] button::after,
    button[kind="header"]::after {
        content: "\2630";
        font-size: 1.8rem;
        color: var(--mg-text-heading);
        display: block; line-height: 1; cursor: pointer;
    }
    [data-testid="stSidebarCollapseButton"] button::after {
        content: "\2715";
        font-size: 1.5rem;
        color: var(--mg-text-muted);
        display: block; line-height: 1; cursor: pointer;
    }

    /* ── Expander ── */
    .streamlit-expanderHeader svg,
    .streamlit-expanderHeader span[data-testid="stExpanderToggleIcon"] {
        display: none !important;
    }
    .streamlit-expanderHeader { padding-right: 0px !important; }

    [data-testid="stExpander"] details {
        background: var(--mg-bg-card) !important;
        border-radius: var(--mg-radius) !important;
        border: 1px solid var(--mg-border-light) !important;
        box-shadow: var(--mg-shadow-sm) !important;
    }
    .streamlit-expanderHeader {
        font-weight: 600;
        direction: rtl;
        text-align: right;
    }

    /* ── Section headers ── */
    .section-header {
        font-family: 'Inter', 'Heebo', sans-serif;
        font-size: 0.95rem;
        font-weight: 600;
        color: var(--mg-text-heading);
        padding: 0;
        border: none;
        margin: 0 0 8px 0;
        direction: rtl;
    }

    /* ── Headers RTL ── */
    h1, h2, h3, h4, h5, h6 {
        direction: rtl;
        text-align: right;
        unicode-bidi: plaintext;
    }
    h2, h3 { margin-top: 0.4rem; margin-bottom: 0.3rem; }
    h4, h5, h6 { margin-top: 0.3rem; margin-bottom: 0.2rem; }

    /* ── Text overflow ── */
    .detail-field {
        word-break: break-word;
        overflow-wrap: break-word;
        line-height: 1.6;
        font-size: 0.95rem;
        direction: rtl;
        unicode-bidi: plaintext;
    }
    .detail-field strong { color: var(--mg-text-heading); }

    /* ── Layout ── */
    [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
        min-width: 0; overflow: visible;
    }
    [data-testid="stHorizontalBlock"] { gap: 0.75rem; }

    .stPlotlyChart { overflow: visible !important; }
    .js-plotly-plot, .plot-container { overflow: visible !important; }

    /* ── Dividers ── */
    hr {
        border-color: var(--mg-border) !important;
        margin: 0.75rem 0 !important;
    }

    [data-testid="stSubheader"] {
        padding-bottom: 0.1rem;
        margin-bottom: 0.3rem;
    }

    /* ── Radio inline ── */
    .stRadio > div { gap: 0.3rem; }
    .stRadio label { font-size: 0.85rem !important; }

    /* ── Tabs ── */
    .stTabs [data-baseweb="tab"] {
        font-family: 'Inter', 'Heebo', sans-serif !important;
    }
    .stTabs [aria-selected="true"] {
        border-bottom-color: var(--mg-primary) !important;
        color: var(--mg-primary) !important;
    }

    /* ── Toggle compact ── */
    [data-testid="stToggle"] label {
        font-size: 0.8rem !important;
    }
</style>
""", unsafe_allow_html=True)



# ============================================================================
# MULTIPAGE NAVIGATION
# ============================================================================

dashboard = st.Page("pages/dashboard.py", title="לוח מכרזים", icon="📋", default=True)
management = st.Page("pages/management.py", title="סקירה ניהולית", icon="📊")

pg = st.navigation([dashboard, management])
pg.run()
