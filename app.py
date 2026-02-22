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
    initial_sidebar_state="collapsed",
)

# ── Load fonts: Inter + Heebo (typography), Material (dataframe sort arrows) ──
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
# SHARED CSS (MEGIDO Executive Design System)
# ============================================================================

st.markdown("""
<style>
    /* ================================================================
       MEGIDO Design System — Deep Blue Professional Palette
       Mobile-first responsive layout
       ================================================================ */

    /* ── Global RTL ── */
    html, body, [data-testid="stAppViewContainer"], .main .block-container {
        direction: rtl;
        text-align: right;
    }

    /* ── Hide Streamlit keyboard shortcut hints (narrow selectors to avoid
         breaking dataframe column filter/search popups) ── */
    [data-testid="InputInstructions"],
    [data-testid="StyledThumbValue"] {
        display: none !important;
        visibility: hidden !important;
        height: 0 !important;
        overflow: hidden !important;
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

    /* ── MEGIDO Design Tokens (Deep Blue) ── */
    :root {
        --mg-bg-main: #F8FAFC;
        --mg-bg-card: #FFFFFF;
        --mg-bg-sidebar: #0F172A;
        --mg-sidebar-header: #0F172A;
        --mg-primary: #2563EB;
        --mg-primary-hover: #1D4ED8;
        --mg-primary-light: #DBEAFE;
        --mg-secondary: #1E3A5F;
        --mg-accent: #60A5FA;
        --mg-text-heading: #1E293B;
        --mg-text-body: #334155;
        --mg-text-muted: #64748B;
        --mg-text-on-dark: #E2E8F0;
        --mg-text-on-dark-muted: #94A3B8;
        --mg-border: #E2E8F0;
        --mg-border-dark: #1E293B;
        --mg-success: #10B981;
        --mg-warning: #F59E0B;
        --mg-danger: #EF4444;

        /* Spacing scale */
        --mg-space-xs: 4px;
        --mg-space-sm: 8px;
        --mg-space-md: 16px;
        --mg-space-lg: 24px;
        --mg-space-xl: 32px;
    }

    /* ── Typography & Foundation ── */
    html, body, [class*="st-"], [data-testid="stAppViewContainer"] {
        font-family: 'Inter', 'Heebo', -apple-system, BlinkMacSystemFont, sans-serif !important;
        background-color: var(--mg-bg-main) !important;
        color: var(--mg-text-body);
    }

    h1, h2, h3, h4, h5, h6, .stTabs button {
        font-family: 'Inter', 'Heebo', -apple-system, sans-serif !important;
        color: var(--mg-text-heading) !important;
    }

    code, pre {
        font-family: 'JetBrains Mono', monospace !important;
    }

    .block-container {
        padding-top: 0.75rem;
        padding-bottom: 1rem;
        max-width: 100%;
    }

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

    /* ── Metric Cards ── */
    [data-testid="stMetric"] {
        background-color: var(--mg-bg-card) !important;
        border-radius: 12px !important;
        border: 1px solid var(--mg-border) !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04) !important;
        padding: 14px 16px !important;
        position: relative;
        transition: box-shadow 0.15s ease;
    }
    [data-testid="stMetric"]:hover {
        box-shadow: 0 4px 12px rgba(37,99,235,0.1), 0 2px 4px rgba(0,0,0,0.06) !important;
    }
    /* Blue accent stripe on right (RTL) */
    [data-testid="stMetric"]::before {
        content: '';
        position: absolute;
        right: 0;
        top: 12px;
        bottom: 12px;
        width: 3px;
        background: var(--mg-primary);
        border-radius: 3px;
    }
    [data-testid="stMetricValue"] {
        color: var(--mg-text-heading) !important;
        font-weight: 700 !important;
        font-size: 22px !important;
    }
    [data-testid="stMetricLabel"] {
        color: var(--mg-text-muted) !important;
        font-weight: 500 !important;
        font-size: 12px !important;
    }

    /* ── Sidebar (Dark Slate) ── */
    section[data-testid="stSidebar"] > div {
        direction: rtl;
        text-align: right;
    }
    section[data-testid="stSidebar"] {
        background-color: var(--mg-bg-sidebar) !important;
        background-image: none !important;
        box-shadow: 1px 0 0 var(--mg-border-dark);
    }

    /* Default sidebar text (light on dark) */
    section[data-testid="stSidebar"] p,
    section[data-testid="stSidebar"] span,
    section[data-testid="stSidebar"] label {
        color: var(--mg-text-on-dark-muted) !important;
    }

    /* Headers in sidebar */
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3 {
        color: var(--mg-text-on-dark) !important;
    }

    /* Navigation/Inputs in sidebar */
    section[data-testid="stSidebar"] .stRadio label,
    section[data-testid="stSidebar"] .stMultiSelect label {
        color: var(--mg-text-on-dark-muted) !important;
        font-weight: 500;
    }

    /* Dark sidebar widget overrides */
    section[data-testid="stSidebar"] [data-baseweb="select"],
    section[data-testid="stSidebar"] [data-baseweb="input"] {
        background-color: #1E293B !important;
        border-color: #334155 !important;
    }
    section[data-testid="stSidebar"] [data-baseweb="select"] input,
    section[data-testid="stSidebar"] [data-baseweb="input"] input {
        color: var(--mg-text-on-dark) !important;
    }
    section[data-testid="stSidebar"] [data-baseweb="tag"] {
        background-color: var(--mg-primary) !important;
        color: #FFFFFF !important;
    }
    section[data-testid="stSidebar"] [data-baseweb="select"] [data-baseweb="icon"] {
        color: var(--mg-text-on-dark-muted) !important;
    }

    /* Sidebar text inputs, password fields, auth forms */
    section[data-testid="stSidebar"] input,
    section[data-testid="stSidebar"] textarea {
        color: var(--mg-text-on-dark) !important;
        background-color: #1E293B !important;
        border-color: #334155 !important;
        caret-color: var(--mg-accent) !important;
    }
    section[data-testid="stSidebar"] input::placeholder,
    section[data-testid="stSidebar"] textarea::placeholder {
        color: var(--mg-text-on-dark-muted) !important;
        opacity: 0.7 !important;
    }
    /* Sidebar form containers and auth elements */
    section[data-testid="stSidebar"] [data-testid="stTextInput"] > div,
    section[data-testid="stSidebar"] [data-testid="stPasswordInput"] > div,
    section[data-testid="stSidebar"] [data-testid="stForm"] input {
        background-color: #1E293B !important;
        border-color: #334155 !important;
    }
    section[data-testid="stSidebar"] [data-testid="stTextInput"] label,
    section[data-testid="stSidebar"] [data-testid="stPasswordInput"] label {
        color: var(--mg-text-on-dark) !important;
    }

    /* Sidebar dividers */
    section[data-testid="stSidebar"] hr {
        border-color: var(--mg-border-dark) !important;
    }

    /* Sidebar captions */
    section[data-testid="stSidebar"] [data-testid="stCaptionContainer"] {
        color: var(--mg-text-on-dark-muted) !important;
    }

    /* ── Tables (Clean bordered + mobile scroll) ── */
    [data-testid="stDataFrame"], .stDataFrame {
        border: 1px solid var(--mg-border) !important;
        border-radius: 10px !important;
        overflow: hidden;
    }

    /* ── Buttons (Deep Blue) ── */
    .stButton button {
        background-color: var(--mg-primary) !important;
        color: #FFFFFF !important;
        border-radius: 8px !important;
        border: none !important;
        padding: 10px 24px !important;
        font-weight: 600 !important;
        box-shadow: 0 1px 2px rgba(37, 99, 235, 0.2) !important;
        transition: all 0.15s ease;
    }
    .stButton button:hover {
        background-color: var(--mg-primary-hover) !important;
        box-shadow: 0 4px 12px rgba(37, 99, 235, 0.25) !important;
        transform: translateY(-1px);
    }

    /* ── Chart Titles ── */
    .pie-title {
        font-family: 'Inter', 'Heebo', sans-serif !important;
        color: var(--mg-text-heading) !important;
        font-weight: 700 !important;
        font-size: 15px !important;
        margin-bottom: 8px !important;
        text-align: center !important;
    }

    /* ── Pill-style Radio Buttons (Main Area) ── */
    div[role="radiogroup"] {
        background-color: var(--mg-bg-card);
        padding: 2px;
        border-radius: 8px;
        display: inline-flex;
        border: 1px solid var(--mg-border);
        box-shadow: none;
        gap: 2px;
    }
    div[role="radiogroup"] label > div:first-child {
        display: none !important;
    }
    div[role="radiogroup"] label {
        padding: 2px 8px !important;
        border-radius: 6px !important;
        margin: 0 !important;
        transition: all 0.15s ease;
        font-size: 0.65rem !important;
        cursor: pointer;
        line-height: 1.4;
    }
    div[role="radiogroup"] label:hover {
        background-color: var(--mg-primary-light);
    }
    /* Active/selected radio pill */
    div[role="radiogroup"] label[data-checked="true"],
    div[role="radiogroup"] label:has(input:checked) {
        background-color: var(--mg-primary) !important;
        color: #FFFFFF !important;
        font-weight: 600 !important;
        box-shadow: none;
    }

    /* ── Center radio pills when inside chart columns ── */
    [data-testid="stColumn"] .stRadio > div {
        justify-content: center;
    }
    /* Shrink the radio container inside columns */
    [data-testid="stColumn"] .stRadio {
        margin-top: -8px;
        margin-bottom: 0;
    }

    /* ── Sidebar Toggle Buttons ── */
    [data-testid="stSidebarCollapseButton"] button,
    [data-testid="stExpandSidebarButton"] button,
    button[kind="headerNoPadding"] {
        border: none !important;
        background: transparent !important;
    }

    /* ── Expander Arrow Fix (Hide arrow, keep clickable) ── */
    .streamlit-expanderHeader svg,
    .streamlit-expanderHeader span[data-testid="stExpanderToggleIcon"] {
        display: none !important;
    }
    .streamlit-expanderHeader {
        padding-right: 0px !important;
    }

    /* ── Sidebar custom header (MEGIDO branding) ── */
    .sidebar-header {
        background: linear-gradient(135deg, #1E293B 0%, #0F172A 100%);
        border-radius: 12px;
        padding: 24px 16px 20px;
        text-align: center;
        margin-bottom: 16px;
        border: 1px solid #334155;
    }
    .sidebar-header h2 {
        color: #60A5FA !important;
        font-size: 1.5rem;
        font-weight: 700;
        margin: 0;
        letter-spacing: 0.05em;
        text-align: center !important;
    }
    .sidebar-header p {
        color: var(--mg-text-on-dark-muted) !important;
        font-size: 0.82rem;
        margin: 6px 0 0 0;
        text-align: center !important;
    }

    /* ── Section headers with accent border ── */
    .section-header {
        font-family: 'Inter', 'Heebo', sans-serif;
        font-size: 1rem;
        font-weight: 700;
        color: var(--mg-text-heading);
        padding: 4px 10px 4px 0;
        border-right: 3px solid var(--mg-primary);
        margin: 0.5rem 0 0.5rem 0;
        direction: rtl;
    }

    /* ── New tenders highlight table ── */
    .new-tenders-card {
        background: #EFF6FF;
        border: 1px solid #93C5FD;
        border-radius: 10px;
        padding: 10px;
        margin-bottom: 8px;
    }

    /* ── Compact toggle for deadlines ── */
    [data-testid="stToggle"] label {
        font-size: 0.8rem !important;
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
        margin-top: 0.4rem;
        margin-bottom: 0.3rem;
    }
    h4, h5, h6 {
        margin-top: 0.3rem;
        margin-bottom: 0.2rem;
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
    .detail-field strong { color: var(--mg-text-heading); }

    /* ── Column containers: prevent clipping ── */
    [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
        min-width: 0;
        overflow: visible;
    }
    [data-testid="stHorizontalBlock"] {
        gap: 0.75rem;
    }

    /* ── Plotly chart containers: no overflow ── */
    .stPlotlyChart {
        overflow: visible !important;
    }
    .js-plotly-plot, .plot-container {
        overflow: visible !important;
    }

    /* ── Divider colour + compact ── */
    hr {
        border-color: var(--mg-border) !important;
        margin: 0.5rem 0 !important;
    }

    /* ── Subheader spacing fix ── */
    [data-testid="stSubheader"] {
        padding-bottom: 0.1rem;
        margin-bottom: 0.3rem;
    }

    /* ── Radio buttons inline fix ── */
    .stRadio > div {
        gap: 0.3rem;
    }
    .stRadio label {
        font-size: 0.85rem !important;
    }

    /* ── Tabs styling ── */
    .stTabs [data-baseweb="tab"] {
        font-family: 'Inter', 'Heebo', sans-serif !important;
    }
    .stTabs [aria-selected="true"] {
        border-bottom-color: var(--mg-primary) !important;
        color: var(--mg-primary) !important;
    }

    /* ================================================================
       TABLES — LTR by default (numbers/data read naturally left→right)
       Narrow columns minimized.
       ================================================================ */

    [data-testid="stDataFrame"],
    [data-testid="stDataFrame"] table,
    [data-testid="stDataFrame"] th,
    [data-testid="stDataFrame"] td,
    .stDataFrame,
    .stDataFrame table {
        direction: ltr !important;
        text-align: left !important;
    }
    /* Compact table cells */
    [data-testid="stDataFrame"] th,
    [data-testid="stDataFrame"] td {
        white-space: nowrap;
        padding: 4px 8px !important;
        font-size: 0.85rem;
    }

    /* ================================================================
       MOBILE-FIRST RESPONSIVE BREAKPOINTS
       ================================================================ */

    /* ── Mobile: <768px — compact, single-column friendly ── */
    @media (max-width: 767px) {

        /* ── Sidebar: force left:0 so translateX(-100%) hides it fully ── */
        section[data-testid="stSidebar"] {
            left: 0 !important;
            width: 85vw !important;
            max-width: 320px !important;
            min-width: 0 !important;
            z-index: 1000 !important;
            transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1),
                        visibility 0.3s ease,
                        box-shadow 0.3s ease !important;
        }
        /* Collapsed: fully off-screen + invisible (opacity prevents child overrides) */
        section[data-testid="stSidebar"][aria-expanded="false"] {
            transform: translateX(-100%) !important;
            opacity: 0 !important;
            pointer-events: none !important;
            overflow: hidden !important;
            box-shadow: none !important;
        }
        /* Expanded: slide in as overlay */
        section[data-testid="stSidebar"][aria-expanded="true"] {
            transform: translateX(0) !important;
            opacity: 1 !important;
            pointer-events: auto !important;
            overflow-y: auto !important;
            box-shadow: 4px 0 24px rgba(0,0,0,0.3) !important;
        }

        /* ── Main content: full width, no sidebar offset ── */
        [data-testid="stAppViewContainer"] > section.main,
        [data-testid="stAppViewContainer"] {
            margin-left: 0 !important;
            width: 100% !important;
        }

        /* ── Content: clear the Streamlit header ── */
        .block-container {
            padding-left: 0.5rem !important;
            padding-right: 0.5rem !important;
            padding-top: 2.5rem !important;
        }
        /* Streamlit header: compact, full-width */
        [data-testid="stHeader"] {
            left: 0 !important;
            width: 100% !important;
            height: 2.5rem !important;
            min-height: 2.5rem !important;
            background: var(--mg-bg-main) !important;
            z-index: 900;
        }
        /* Sidebar expand button: style as clear icon */
        [data-testid="stExpandSidebarButton"] {
            z-index: 901 !important;
        }

        /* Stack columns vertically on mobile */
        [data-testid="stHorizontalBlock"] {
            flex-direction: column !important;
            gap: 0.5rem;
        }
        [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
            width: 100% !important;
            flex: 1 1 100% !important;
        }

        /* Smaller metric values on mobile */
        [data-testid="stMetricValue"] {
            font-size: 18px !important;
        }
        [data-testid="stMetric"] {
            padding: 10px 12px !important;
        }

        /* Reduce heading sizes */
        h1 { font-size: 1.3rem !important; }
        h2 { font-size: 1.1rem !important; }
        h3 { font-size: 1rem !important; }
        h4 { font-size: 0.9rem !important; }

        /* Full-width tables with horizontal scroll */
        [data-testid="stDataFrame"] {
            overflow-x: auto !important;
            -webkit-overflow-scrolling: touch;
            max-width: 100vw !important;
        }

        /* Compact section headers */
        .section-header {
            font-size: 0.9rem;
            margin: 0.3rem 0;
        }

        /* Tabs: smaller text, horizontal scroll */
        .stTabs [data-baseweb="tab-list"] {
            overflow-x: auto !important;
            -webkit-overflow-scrolling: touch;
            flex-wrap: nowrap !important;
        }
        .stTabs [data-baseweb="tab"] {
            font-size: 0.8rem !important;
            padding: 8px 12px !important;
            white-space: nowrap;
        }

        /* Radio pills: smaller on mobile */
        div[role="radiogroup"] label {
            font-size: 0.6rem !important;
            padding: 2px 6px !important;
        }

        /* Pie title smaller */
        .pie-title {
            font-size: 13px !important;
        }

        /* Button full-width on mobile */
        .stButton button {
            width: 100%;
            padding: 10px 16px !important;
        }

        /* Expanders: tighter on mobile */
        [data-testid="stExpander"] {
            margin-top: 0.25rem !important;
            margin-bottom: 0.25rem !important;
        }

        /* Plotly charts: constrain height on mobile */
        .stPlotlyChart {
            max-height: 280px !important;
        }
    }

    /* ── Tablet: 768px–1024px ── */
    @media (min-width: 768px) and (max-width: 1024px) {
        .block-container {
            padding-left: 1rem !important;
            padding-right: 1rem !important;
            padding-top: 2rem !important;
        }

        [data-testid="stMetricValue"] {
            font-size: 20px !important;
        }
    }

    /* ── Desktop: >1024px ── */
    @media (min-width: 1025px) {
        .block-container {
            padding-left: 1.5rem !important;
            padding-right: 1.5rem !important;
        }
    }
</style>
""", unsafe_allow_html=True)



# ============================================================================
# MULTIPAGE NAVIGATION
# ============================================================================

dashboard = st.Page("pages/dashboard.py", title="דאשבורד חדר עסקאות", icon="📋", default=True)
explorer = st.Page("pages/explorer.py", title="סייר מכרזים", icon="🔍")
analytics = st.Page("pages/analytics.py", title="ניתוח שוק", icon="📈")
management = st.Page("pages/management.py", title="לוח הנהלה", icon="📊")

pg = st.navigation([dashboard, explorer, analytics, management])
pg.run()
