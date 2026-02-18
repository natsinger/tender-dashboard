"""
Israel Land Tenders Dashboard (מכרזי קרקע)
==========================================
Multipage Streamlit dashboard for tracking land tenders from רמ"י.
Two views: full dashboard for daily users, management overview for executives.

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
    page_title="מכרזים",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Load ALL Material fonts (Icons + Symbols) so dataframe sort arrows render ──
st.markdown("""
<link href="https://fonts.googleapis.com/icon?family=Material+Icons" rel="stylesheet">
<link href="https://fonts.googleapis.com/icon?family=Material+Icons+Outlined" rel="stylesheet">
<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200" rel="stylesheet" />
<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200" rel="stylesheet" />
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700&display=swap" rel="stylesheet">
<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
""", unsafe_allow_html=True)


# ============================================================================
# SHARED CSS (Horizon Design System)
# ============================================================================

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
        content: "\2630";
        font-size: 1.8rem;
        color: #1a1a2e;
        display: block;
        line-height: 1;
        cursor: pointer;
    }

    /* Expanded state (Close X) */
    [data-testid="stSidebarCollapseButton"] button::after {
        content: "\2715";
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
# MULTIPAGE NAVIGATION
# ============================================================================

dashboard = st.Page("pages/dashboard.py", title="לוח מכרזים", icon="🏗️", default=True)
management = st.Page("pages/management.py", title="סקירה ניהולית", icon="📊")

pg = st.navigation([dashboard, management])
pg.run()
