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

    /* ── MEGIDO Design Tokens ── */
    :root {
        --mg-bg-main: #F0F2F5;
        --mg-bg-card: #FFFFFF;
        --mg-bg-sidebar: #111827;
        --mg-sidebar-header: #0D1321;
        --mg-primary: #D4A017;
        --mg-primary-hover: #B8860B;
        --mg-navy: #1B2A4A;
        --mg-text-heading: #111827;
        --mg-text-body: #374151;
        --mg-text-muted: #9CA3AF;
        --mg-text-on-dark: #E5E7EB;
        --mg-text-on-dark-muted: #6B7280;
        --mg-border: #E5E7EB;
        --mg-border-dark: #1F2937;
        --mg-success: #10B981;
        --mg-warning: #F59E0B;
        --mg-danger: #EF4444;
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

    /* ── Metric Cards (MEGIDO Executive) ── */
    [data-testid="stMetric"] {
        background-color: var(--mg-bg-card) !important;
        border-radius: 12px !important;
        border: 1px solid var(--mg-border) !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.08), 0 1px 2px rgba(0,0,0,0.06) !important;
        padding: 20px !important;
        position: relative;
    }
    /* Gold accent stripe on right (RTL) */
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
        font-size: 26px !important;
    }
    [data-testid="stMetricLabel"] {
        color: var(--mg-text-muted) !important;
        font-weight: 500 !important;
        font-size: 14px !important;
    }

    /* ── Sidebar (Dark Executive) ── */
    section[data-testid="stSidebar"] > div {
        direction: rtl;
        text-align: right;
    }
    section[data-testid="stSidebar"] {
        background-color: var(--mg-bg-sidebar) !important;
        background-image: none !important;
        min-width: 285px !important;
        width: 285px !important;
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
        background-color: #1F2937 !important;
        border-color: #374151 !important;
    }
    section[data-testid="stSidebar"] [data-baseweb="select"] input,
    section[data-testid="stSidebar"] [data-baseweb="input"] input {
        color: var(--mg-text-on-dark) !important;
    }
    section[data-testid="stSidebar"] [data-baseweb="tag"] {
        background-color: var(--mg-primary) !important;
        color: #111827 !important;
    }
    section[data-testid="stSidebar"] [data-baseweb="select"] [data-baseweb="icon"] {
        color: var(--mg-text-on-dark-muted) !important;
    }

    /* Sidebar text inputs, password fields, auth forms — ensure ALL text visible */
    section[data-testid="stSidebar"] input,
    section[data-testid="stSidebar"] textarea {
        color: var(--mg-text-on-dark) !important;
        background-color: #1F2937 !important;
        border-color: #374151 !important;
        caret-color: var(--mg-primary) !important;
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
        background-color: #1F2937 !important;
        border-color: #374151 !important;
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

    /* ── Tables (Clean bordered) ── */
    [data-testid="stDataFrame"], .stDataFrame {
        border: 1px solid var(--mg-border) !important;
        border-radius: 8px !important;
        overflow: hidden;
    }

    /* ── Buttons (MEGIDO Gold) ── */
    .stButton button {
        background-color: var(--mg-primary) !important;
        color: #111827 !important;
        border-radius: 8px !important;
        border: none !important;
        padding: 10px 24px !important;
        font-weight: 600 !important;
        box-shadow: 0 1px 2px rgba(212, 160, 23, 0.2) !important;
        transition: all 0.15s ease;
    }
    .stButton button:hover {
        background-color: var(--mg-primary-hover) !important;
        box-shadow: 0 4px 12px rgba(212, 160, 23, 0.3) !important;
        transform: translateY(-1px);
    }

    /* ── Chart Titles ── */
    .pie-title {
        font-family: 'Inter', 'Heebo', sans-serif !important;
        color: var(--mg-text-heading) !important;
        font-weight: 700 !important;
        font-size: 16px !important;
        margin-bottom: 10px !important;
        text-align: center !important;
    }

    /* ── Pill-style Radio Buttons (Main Area) ── */
    div[role="radiogroup"] {
        background-color: var(--mg-bg-card);
        padding: 3px;
        border-radius: 10px;
        display: inline-flex;
        border: 1px solid var(--mg-border);
        box-shadow: 0 1px 2px rgba(0,0,0,0.05);
    }
    div[role="radiogroup"] label > div:first-child {
        display: none !important;
    }
    div[role="radiogroup"] label {
        padding: 4px 12px !important;
        border-radius: 7px !important;
        margin: 0 !important;
        transition: all 0.15s ease;
        font-size: 0.8rem !important;
        cursor: pointer;
    }
    div[role="radiogroup"] label:hover {
        background-color: #FFFBEB;
    }
    /* Active/selected radio pill */
    div[role="radiogroup"] label[data-checked="true"],
    div[role="radiogroup"] label:has(input:checked) {
        background-color: var(--mg-primary) !important;
        color: #111827 !important;
        font-weight: 600 !important;
        box-shadow: 0 1px 3px rgba(212, 160, 23, 0.3);
    }

    /* ── Center radio pills when inside chart columns ── */
    [data-testid="stColumn"] .stRadio > div {
        justify-content: center;
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
        color: var(--mg-text-heading);
        display: block;
        line-height: 1;
        cursor: pointer;
    }

    /* Expanded state (Close X) — light for dark sidebar */
    [data-testid="stSidebarCollapseButton"] button::after {
        content: "\2715";
        font-size: 1.5rem;
        color: var(--mg-text-on-dark-muted);
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

    /* ── Sidebar custom header (MEGIDO branding) ── */
    .sidebar-header {
        background-color: var(--mg-sidebar-header);
        border-radius: 12px;
        padding: 24px 16px 20px;
        text-align: center;
        margin-bottom: 16px;
        border: 1px solid var(--mg-border-dark);
    }
    .sidebar-header h2 {
        color: var(--mg-primary) !important;
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
        font-size: 1.2rem;
        font-weight: 700;
        color: var(--mg-text-heading);
        padding: 8px 12px 8px 0;
        border-right: 3px solid var(--mg-primary);
        margin: 1.5rem 0 1rem 0;
        direction: rtl;
    }

    /* ── New tenders highlight table ── */
    .new-tenders-card {
        background: #ECFDF5;
        border: 1px solid #6EE7B7;
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
    .detail-field strong { color: var(--mg-text-heading); }

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
    hr { border-color: var(--mg-border) !important; }

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

    /* ── Tabs styling ── */
    .stTabs [data-baseweb="tab"] {
        font-family: 'Inter', 'Heebo', sans-serif !important;
    }
    .stTabs [aria-selected="true"] {
        border-bottom-color: var(--mg-primary) !important;
        color: var(--mg-primary) !important;
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

dashboard = st.Page("pages/dashboard.py", title="לוח מכרזים", icon="📋", default=True)
management = st.Page("pages/management.py", title="סקירה ניהולית", icon="📊")

pg = st.navigation([dashboard, management])
pg.run()
