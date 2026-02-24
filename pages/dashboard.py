"""
Full dashboard page — daily user view (דאשבורד חדר עסקאות).

Compact executive layout: pre-filtered to relevant tender types + purposes.
Sections: header, new documents tables, KPIs + deadlines,
review status table, bottom category cards, analytics, debug.
Branded for MEGIDO BY AURA.
"""

from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from config import (
    CLOSING_SOON_DAYS,
    DOCUMENT_DOWNLOAD_API,
    LAND_AUTHORITY_API,
    RELEVANT_TENDER_TYPES,
    RMI_SITE_URL,
    TEAM_EMAIL,
    TENDER_DETAIL_API,
)
from dashboard_utils import (
    MEGIDO_CHART_COLORS,
    PLOTLY_BG,
    PLOTLY_FONT,
    filter_active,
    find_new_tender_ids_from_snapshots,
    get_user_email,
    load_data,
    render_email_input,
)
from analytics_engine import score_all_tenders
from user_db import REVIEW_STAGES, UserDB

# Purpose filter: only include these ייעוד values across the entire dashboard
RELEVANT_PURPOSES = {"בנייה רוויה", "בנייה נמוכה/צמודת קרקע", "מגורים/מסחר/מלונאות/נופש", "דיור מוגן (בית אבות)", "אחר"}

# The 3 tender types for KPI cards (פומבי=1, מחיר מטרה=5, דיור במחיר מופחת=8)
CARD_TENDER_TYPES = {1, 5, 8}


@st.cache_resource
def _get_user_db() -> UserDB:
    """Return a single shared UserDB instance (cached across reruns)."""
    return UserDB()


user_db = _get_user_db()

# Compute `today` fresh on each render (not at module-import time).
today = datetime.now()

# ── Load & pre-filter data ───────────────────────────────────────────────────
render_email_input()

df_all = load_data(data_source="latest_file")
# Pre-filter: only relevant types
df = df_all[df_all["tender_type_code"].isin(RELEVANT_TENDER_TYPES)].copy()
# Purpose filter (point 8)
if "purpose" in df.columns:
    df = df[df["purpose"].isin(RELEVANT_PURPOSES)].copy()
# Score all tenders
df = score_all_tenders(df)
# Active-only base
active_df = filter_active(df)


# ============================================================================
# SIDEBAR — brand + watchlist management + review status editing
# ============================================================================

_REVIEW_EMOJI: dict[str, str] = {
    "לא נסקר": "⬜",
    "סקירה ראשונית": "🔵",
    "בדיקה מעמיקה": "🟣",
    "הוצג בפורום": "🟠",
    "אושר בפורום": "🟢",
}

with st.sidebar:
    logo_path = Path(__file__).parent.parent / "assets" / "logo megido.jpg"
    if logo_path.exists():
        st.image(str(logo_path), width=140)

    # ── Personal watchlist management (moved from ROW 3) ──────────────
    st.markdown("---")
    st.markdown(
        '<h4 style="color:#E2E8F0 !important;">ניהול מועדפים</h4>',
        unsafe_allow_html=True,
    )

    _sidebar_email = get_user_email()

    if not _sidebar_email:
        st.caption("יש להזדהות כדי לנהל מכרזים מועדפים")
    else:
        st.caption(f"משתמש: {_sidebar_email}")
        _personal_db = user_db

        if not _personal_db.available:
            st.warning("Supabase לא מוגדר — רשימת המעקב לא תישמר.")

        # ── Personal watchlist: add tender ──────────────────────────
        _watch_labels: dict[int, str] = {}
        for _, _r in df[["tender_id", "tender_name", "city"]].iterrows():
            _name = str(_r["tender_name"])[:40] if pd.notna(_r["tender_name"]) else ""
            _city = str(_r["city"])[:15] if pd.notna(_r["city"]) else ""
            _watch_labels[int(_r["tender_id"])] = f"{_name} — {_city}" if _city else _name

        watch_tender_id = st.selectbox(
            "הוספה למעקב אישי",
            options=list(_watch_labels.keys()),
            index=None,
            format_func=lambda tid: _watch_labels[tid],
            placeholder="הקלד שם מכרז או עיר...",
            key="watch_tender_input",
        )

        if st.button("הוסף למעקב", key="btn_add_watch", use_container_width=True):
            if watch_tender_id is not None:
                added = _personal_db.add_to_watchlist(_sidebar_email, int(watch_tender_id))
                if added:
                    st.success("נוסף!")
                    st.rerun()
                else:
                    st.info("כבר ברשימה.")

        # ── Personal watchlist: current items ──────────────────────
        watchlist_rows = _personal_db.get_watchlist_rows(_sidebar_email)
        if watchlist_rows:
            _tender_lookup = df.set_index("tender_id").to_dict("index") if not df.empty else {}
            for row in watchlist_rows:
                tid = int(row["tender_id"])
                t = _tender_lookup.get(tid, {})
                _tdisplay = str(t.get("tender_name", tid))[:25]
                _tcity = str(t.get("city", ""))[:12]
                _tunits = t.get("units", "")
                _tunits_str = f' | {int(_tunits)} יח"ד' if _tunits and pd.notna(_tunits) and int(_tunits) > 0 else ""
                _wc1, _wc2 = st.columns([5, 1])
                with _wc1:
                    st.markdown(
                        f'<span style="color:#E2E8F0;font-size:0.82rem;">'
                        f"{_tdisplay}"
                        f'</span><br>'
                        f'<span style="color:#60A5FA;font-size:0.75rem;">'
                        f"{_tcity}{_tunits_str}"
                        f'</span>',
                        unsafe_allow_html=True,
                    )
                with _wc2:
                    if st.button("🗑️", key=f"rm_watch_{row['id']}"):
                        _personal_db.remove_from_watchlist(_sidebar_email, tid)
                        st.rerun()
        else:
            st.caption("אין מכרזים במעקב אישי")

    # ── Team watchlist management ────────────────────────────────────────
    st.markdown("---")
    st.markdown(
        '<h4 style="color:#E2E8F0 !important;">מועדפים - חדר עסקאות</h4>',
        unsafe_allow_html=True,
    )

    _team_db = user_db

    if not _sidebar_email:
        st.caption("יש להזדהות כדי לנהל מכרזים מועדפים")
    else:
        _team_labels: dict[int, str] = {}
        for _, _r in df[["tender_id", "tender_name", "city"]].iterrows():
            _name = str(_r["tender_name"])[:40] if pd.notna(_r["tender_name"]) else ""
            _city = str(_r["city"])[:15] if pd.notna(_r["city"]) else ""
            _team_labels[int(_r["tender_id"])] = f"{_name} — {_city}" if _city else _name

        _team_tid = st.selectbox(
            "חיפוש מכרז",
            options=list(_team_labels.keys()),
            index=None,
            format_func=lambda tid: _team_labels[tid],
            placeholder="שם מכרז או עיר...",
            key="dash_team_watch_select",
        )

        if st.button("הוסף למעקב צוות", key="dash_team_btn_add", use_container_width=True):
            if _team_tid is not None:
                _added = _team_db.add_to_watchlist(TEAM_EMAIL, int(_team_tid))
                if _added:
                    st.success("נוסף!")
                    st.rerun()
                else:
                    st.info("כבר ברשימה.")

        _team_wl = _team_db.get_watchlist_rows(TEAM_EMAIL)
        if _team_wl:
            _tlookup = df.set_index("tender_id").to_dict("index") if not df.empty else {}
            for _tw in _team_wl:
                _ttid = int(_tw["tender_id"])
                _tt = _tlookup.get(_ttid, {})
                _tdisplay = str(_tt.get("tender_name", _ttid))[:25]
                _tcity = str(_tt.get("city", ""))[:12]
                _tunits = _tt.get("units", "")
                _tunits_str = f' | {int(_tunits)} יח"ד' if _tunits and pd.notna(_tunits) and int(_tunits) > 0 else ""
                _tc1, _tc2 = st.columns([5, 1])
                with _tc1:
                    st.markdown(
                        f'<span style="color:#E2E8F0;font-size:0.82rem;">'
                        f"{_tdisplay}"
                        f'</span><br>'
                        f'<span style="color:#60A5FA;font-size:0.75rem;">'
                        f"{_tcity}{_tunits_str}"
                        f'</span>',
                        unsafe_allow_html=True,
                    )
                with _tc2:
                    if st.button("🗑️", key=f"dash_team_rm_{_tw['id']}"):
                        _team_db.remove_from_watchlist(TEAM_EMAIL, _ttid)
                        st.rerun()
        else:
            st.caption("אין מכרזים מועדפים")

    # ── Review status editing (moved from ROW 4 form) ─────────────────
    st.markdown("---")
    st.markdown(
        '<h4 style="color:#E2E8F0 !important;">עדכון סטטוס סקירה</h4>',
        unsafe_allow_html=True,
    )

    _review_email = get_user_email()
    _review_db = user_db

    _team_ids = _review_db.get_watchlist_ids(TEAM_EMAIL)
    _team_df = df[df["tender_id"].astype(int).isin(_team_ids)].copy() if _team_ids else pd.DataFrame()

    if not _review_email:
        st.caption("יש להזדהות כדי לעדכן סטטוס סקירה.")
    elif len(_team_df) > 0:
        _rev_ids = _team_df["tender_id"].astype(int).tolist()
        _rev_map = _review_db.get_review_statuses_for_tenders(_rev_ids)

        _rev_labels: dict[int, str] = {}
        for _, _r in _team_df.iterrows():
            _rname = str(_r.get("tender_name", ""))[:30]
            _rcity = str(_r.get("city", ""))[:15]
            _rev_labels[int(_r["tender_id"])] = f"{_rname} — {_rcity}"

        _rev_tid = st.selectbox(
            "מכרז",
            options=list(_rev_labels.keys()),
            format_func=lambda tid: _rev_labels[tid],
            key="dash_review_tender_select",
        )

        _cur_status = _rev_map.get(_rev_tid, {}).get("status", REVIEW_STAGES[0])
        _cur_idx = REVIEW_STAGES.index(_cur_status) if _cur_status in REVIEW_STAGES else 0
        _new_status = st.selectbox(
            "סטטוס חדש",
            options=REVIEW_STAGES,
            index=_cur_idx,
            key="dash_review_status_select",
        )

        # Pre-populate notes only when the selected tender changes
        _cur_notes = _rev_map.get(_rev_tid, {}).get("notes", "") or ""
        if st.session_state.get("_prev_rev_tid") != _rev_tid:
            st.session_state["dash_review_notes"] = _cur_notes
            st.session_state["_prev_rev_tid"] = _rev_tid

        _rev_notes = st.text_input(
            "הערות",
            key="dash_review_notes",
            placeholder="...",
        )

        if st.button("עדכן סטטוס", key="dash_btn_update_review", use_container_width=True):
            _prev = _review_db.set_review_status(
                tender_id=_rev_tid,
                status=_new_status,
                updated_by=_review_email,
                notes=_rev_notes or None,
            )
            st.success(f"{_prev or 'חדש'} → {_new_status}")
            st.session_state["_prev_rev_tid"] = None
            st.rerun()
    else:
        st.caption("אין מכרזים מועדפים לעדכון")

    # ── Stats footer ─────────────────────────────────────────────────────
    st.markdown("---")
    st.caption(f"עדכון: {today.strftime('%d/%m/%Y %H:%M')}")
    st.caption(f"רשומות: {len(df):,} (מ-{len(df_all):,})")


# ============================================================================
# ROW 0: COMPACT HEADER
# ============================================================================

st.markdown(
    '<div style="display:flex;align-items:center;gap:12px;padding:8px 0 4px 0;margin:0;">'
    '<span style="font-size:1.25rem;font-weight:700;color:#1E293B;">'
    'מכרזי מקרקעין פעילים רמ"י (פומבי, מחיר מטרה, דיור במחיר מופחת)'
    "</span>"
    f'<span style="font-size:0.8rem;color:#64748B;margin-right:auto;">{today.strftime("%d/%m/%Y")}</span>'
    "</div>",
    unsafe_allow_html=True,
)


# ============================================================================
# ROW 1: NEW DOCUMENT TABLES + KPI CARDS + CLOSING DEADLINES
# ============================================================================


cutoff_date = (today - timedelta(days=7)).replace(hour=0, minute=0, second=0, microsecond=0)
since_date_str = cutoff_date.strftime("%Y-%m-%d")

# ── Detect new tenders via JSON snapshot comparison ──────────────────────────
snapshot_new_ids = find_new_tender_ids_from_snapshots()

# ── Fetch new documents from the DB ──────────────────────────────────────────
from db import TenderDB

_doc_db = TenderDB()
new_docs_df = _doc_db.get_new_documents(since_date_str)

# Build set of tender_ids that have any new doc this week
new_doc_tender_ids = set()
# Build set of tender_ids that have a new brochure doc this week
new_brochure_tender_ids = set()

if not new_docs_df.empty and "tender_id" in new_docs_df.columns:
    new_doc_tender_ids = set(new_docs_df["tender_id"].unique())
    # Detect brochure docs: doc_name or description contains "חוברת"
    brochure_mask = (
        new_docs_df["doc_name"].fillna("").str.contains("חוברת", na=False)
        | new_docs_df["description"].fillna("").str.contains("חוברת", na=False)
    )
    brochure_docs = new_docs_df[brochure_mask]
    if not brochure_docs.empty:
        new_brochure_tender_ids = set(brochure_docs["tender_id"].unique())

# Merge: union of DB-based new docs + snapshot-based new tenders
new_doc_tender_ids = new_doc_tender_ids | snapshot_new_ids

# Filter to only active tenders within our dataset
table1_df = active_df[active_df["tender_id"].isin(new_doc_tender_ids)].copy()
table2_df = active_df[active_df["tender_id"].isin(new_brochure_tender_ids)].copy()

# ── Table display helper ─────────────────────────────────────────────────────


def _render_new_table(source_df: pd.DataFrame, title: str, key_prefix: str) -> None:
    """Render a condensed table with RMI links."""
    st.markdown(
        f'<div class="section-header" style="font-size:0.95rem;margin:0 0 6px 0;">'
        f"{title}"
        f"</div>",
        unsafe_allow_html=True,
    )
    if len(source_df) > 0:
        tbl = source_df[["tender_id", "tender_name", "units", "city", "tender_type"]].copy()
        tbl["קישור"] = tbl["tender_id"].apply(lambda tid: f"{RMI_SITE_URL}/{tid}")
        tbl = tbl.drop(columns=["tender_id"])
        tbl.columns = ["שם מכרז", 'יח"ד', "עיר", "סוג", "קישור רמ\"י"]
        tbl = tbl.sort_values('יח"ד', ascending=False)
        st.dataframe(
            tbl,
            use_container_width=True,
            hide_index=True,
            height=min(35 * len(tbl) + 38, 250),
            column_config={
                "שם מכרז": st.column_config.TextColumn("שם מכרז", width="medium"),
                'יח"ד': st.column_config.NumberColumn('יח"ד', format="%d", width="small"),
                "עיר": st.column_config.TextColumn("עיר", width="small"),
                "סוג": st.column_config.TextColumn("סוג", width="small"),
                "קישור רמ\"י": st.column_config.LinkColumn("קישור רמ\"י", width="small", display_text="צפה באתר"),
            },
        )
    else:
        st.info("אין פריטים חדשים השבוע")


# ── Layout: two tables left, KPI cards + deadlines right ─────────────────────
col_tables, col_kpi = st.columns([3, 2])

with col_tables:
    _render_new_table(
        table1_df,
        f"מודעות חדשות במכרזים (7 הימים האחרונים)",
        "new_docs",
    )
    st.markdown("")
    _render_new_table(
        table2_df,
        "מכרזים שפורסמה בהם חוברת מכרז חדשה",
        "new_brochures",
    )

with col_kpi:
    # Only count 3 types for the active card: פומבי(1), מחיר מטרה(5), דיור במחיר מופחת(8)
    card_active_df = active_df[active_df["tender_type_code"].isin(CARD_TENDER_TYPES)]
    closing_soon_count = len(
        active_df[
            (active_df["deadline"].notna())
            & (active_df["deadline"] >= today)
            & (active_df["deadline"] <= today + timedelta(days=CLOSING_SOON_DAYS))
        ]
    )
    k1, k2 = st.columns(2)
    with k1:
        st.metric("מכרזים פעילים (ללא ייזום)", f"{len(card_active_df):,}")
    with k2:
        st.metric("מכרזים שייסגרו בשבועיים הקרובים", closing_soon_count)

    # ── Closing deadlines — directly after KPI cards (pies removed) ──
    st.markdown(
        '<div class="section-header" style="font-size:0.95rem;margin:0 0 6px 0;">מועדי סגירה</div>',
        unsafe_allow_html=True,
    )

    # Controls row: deadline range + brochure filter as pills
    _ctrl1, _ctrl2 = st.columns(2)
    with _ctrl1:
        _deadline_sel = st.pills(
            "טווח", ["14 ימים", "הכל"], default="14 ימים",
            key="deadline_pills", label_visibility="collapsed",
        )
    with _ctrl2:
        _brochure_sel = st.pills(
            "חוברת", ["עם חוברת", "הכל"], default="עם חוברת",
            key="brochure_pills", label_visibility="collapsed",
        )
    show_all_deadlines = _deadline_sel == "הכל"
    _show_all_brochure = _brochure_sel == "הכל"

    upcoming = active_df[
        (active_df["deadline"].notna())
        & (active_df["deadline"] >= today)
    ].sort_values("deadline")

    if not show_all_deadlines:
        upcoming = upcoming[upcoming["deadline"] <= today + timedelta(days=CLOSING_SOON_DAYS)]

    # Default (עם חוברת): show only tenders WITH brochure.
    # "הכל": show all including without brochure.
    if not _show_all_brochure and "published_booklet" in upcoming.columns:
        upcoming = upcoming[upcoming["published_booklet"] == True]

    if len(upcoming) > 0:
        # Include lot_count and max_lots_per_bidder only if present in the DataFrame
        _base_cols = ["tender_name", "city", "units", "deadline"]
        _extra_cols = [c for c in ["lot_count", "max_lots_per_bidder"] if c in upcoming.columns]
        up_disp = upcoming[_base_cols + _extra_cols].copy()
        up_disp["days_left"] = (up_disp["deadline"] - today).dt.days

        def _urgency(d: int) -> str:
            if d <= 7:
                return "🔴"
            if d <= 14:
                return "🟡"
            return "🟢"

        up_disp["urg"] = up_disp["days_left"].apply(_urgency)
        up_disp["deadline"] = up_disp["deadline"].dt.strftime("%d/%m")

        # Reorder: tender_name first (rightmost in RTL), then units, city, days/deadline/urg
        _ordered = ["tender_name", "units", "city", "days_left", "deadline", "urg"] + _extra_cols
        up_disp = up_disp[_ordered]

        _deadline_col_config = {
            "tender_name": st.column_config.TextColumn("שם", width="medium"),
            "units": st.column_config.NumberColumn('יח"ד', format="%d", width="small"),
            "city": st.column_config.TextColumn("עיר", width="small"),
            "days_left": st.column_config.NumberColumn("ימים", format="%d", width="small"),
            "deadline": st.column_config.TextColumn("סגירה", width="small"),
            "urg": st.column_config.TextColumn("", width="small"),
        }
        if "lot_count" in up_disp.columns:
            _deadline_col_config["lot_count"] = st.column_config.NumberColumn(
                "מתחמים", format="%d", width="small",
            )
        if "max_lots_per_bidder" in up_disp.columns:
            _deadline_col_config["max_lots_per_bidder"] = st.column_config.NumberColumn(
                "מקס' לזוכה", format="%d", width="small",
            )

        st.dataframe(
            up_disp,
            column_config=_deadline_col_config,
            hide_index=True,
            use_container_width=True,
            height=min(35 * len(up_disp) + 38, 550),
        )
        st.caption(f"{len(up_disp)} מכרזים")
    else:
        st.info("אין מכרזים קרובים לסגירה")


# ============================================================================
# ROW 2: CITY BAR CHART (full width)
# ============================================================================

st.markdown(
    '<p class="pie-title" style="font-size:13px;">מכרזים פעילים לפי עיר (טופ 10)</p>',
    unsafe_allow_html=True,
)
if "city" in active_df.columns and len(active_df) > 0:
    city_counts = active_df["city"].value_counts().head(10)
    if len(city_counts) > 0:
        fig_city_bar = px.bar(
            x=city_counts.values, y=city_counts.index, orientation="h",
            color_discrete_sequence=["#2563EB"],
        )
        fig_city_bar.update_layout(
            showlegend=False, height=260,
            margin=dict(t=5, b=20, l=100, r=5),
            xaxis_title=None, yaxis_title=None,
            coloraxis_showscale=False,
            font=PLOTLY_FONT, **PLOTLY_BG,
        )
        st.plotly_chart(fig_city_bar, use_container_width=True, key="bar_city")
    else:
        st.info("אין נתוני ערים")
else:
    st.info("אין נתונים")

st.markdown("---")


# ============================================================================
# ROW 3: TEAM REVIEW STATUS — read-only table (editing moved to sidebar)
# ============================================================================

st.markdown(
    '<div class="section-header" style="font-size:1rem;margin:0 0 6px 0;">'
    "מכרזים מועדפים - סטטוס סקירה"
    "</div>",
    unsafe_allow_html=True,
)

# Reuse _team_df and _rev_map from sidebar (already computed above for review form)
if len(_team_df) > 0:
    _rev_tbl = _team_df[["tender_name", "units", "city", "tender_type"]].copy()
    _rev_ids_main = _team_df["tender_id"].astype(int).tolist()
    _rev_map_main = _review_db.get_review_statuses_for_tenders(_rev_ids_main)

    _rev_tbl["review"] = [
        _REVIEW_EMOJI.get(
            _rev_map_main.get(int(tid), {}).get("status", "לא נסקר"), "⬜"
        )
        + " "
        + _rev_map_main.get(int(tid), {}).get("status", "לא נסקר")
        for tid in _team_df["tender_id"]
    ]

    _rev_tbl["notes"] = [
        _rev_map_main.get(int(tid), {}).get("notes", "") or ""
        for tid in _team_df["tender_id"]
    ]

    st.dataframe(
        _rev_tbl,
        column_config={
            "tender_name": st.column_config.TextColumn("מכרז", width="medium"),
            "units": st.column_config.NumberColumn('יח"ד', format="%d", width="small"),
            "city": st.column_config.TextColumn("עיר", width="small"),
            "tender_type": st.column_config.TextColumn("סוג", width="small"),
            "review": st.column_config.TextColumn("סטטוס סקירה", width="medium"),
            "notes": st.column_config.TextColumn("הערות", width="large"),
        },
        hide_index=True,
        use_container_width=True,
    )
else:
    st.info("אין מכרזים מועדפים. הוסף מכרזים דרך התפריט הצדדי ←")


# ============================================================================
# ROW 4: BOTTOM CATEGORY CARDS — דיור להשכרה, דיור מוגן, מכרז ייזום
# ============================================================================

st.markdown("---")
st.markdown(
    '<div class="section-header" style="font-size:1rem;margin:0 0 6px 0;">סוגים נוספים</div>',
    unsafe_allow_html=True,
)

# Use the unfiltered-by-purpose data for these categories (from df_all filtered by type only)
_all_typed = df_all[df_all["tender_type_code"].isin(RELEVANT_TENDER_TYPES)].copy()
_all_active = filter_active(_all_typed)

bc1, bc2, bc3 = st.columns(3)

_CARD_HTML = """<div style="
    background:#FFFFFF;border:1px solid #E2E8F0;border-radius:12px;
    padding:14px 16px;position:relative;box-shadow:0 1px 3px rgba(0,0,0,0.06);
"><div style="
    position:absolute;right:0;top:12px;bottom:12px;width:3px;
    background:#2563EB;border-radius:3px;
"></div>
<div style="color:#64748B;font-weight:500;font-size:12px;margin-bottom:4px;">{label}</div>
<div style="display:flex;align-items:baseline;gap:8px;">
    <span style="color:#1E293B;font-weight:700;font-size:22px;">{units} יח&quot;ד</span>
    <span style="color:#64748B;font-size:12px;">{count} מכרזים</span>
</div></div>"""

with bc1:
    _diur_hashkara = _all_active[_all_active["tender_type"] == "דיור להשכרה"]
    _units_dh = int(_diur_hashkara["units"].sum()) if len(_diur_hashkara) > 0 else 0
    st.markdown(
        _CARD_HTML.format(label="דיור להשכרה", units=f"{_units_dh:,}", count=len(_diur_hashkara)),
        unsafe_allow_html=True,
    )

with bc2:
    _diur_mugan = _all_active[_all_active["purpose"].str.contains("דיור מוגן", na=False)] if "purpose" in _all_active.columns else pd.DataFrame()
    _units_dm = int(_diur_mugan["units"].sum()) if len(_diur_mugan) > 0 else 0
    st.markdown(
        _CARD_HTML.format(label="דיור מוגן", units=f"{_units_dm:,}", count=len(_diur_mugan)),
        unsafe_allow_html=True,
    )

with bc3:
    _yezum = _all_active[_all_active["tender_type"] == "מכרז ייזום"]
    _units_yz = int(_yezum["units"].sum()) if len(_yezum) > 0 else 0
    st.markdown(
        _CARD_HTML.format(label="מכרז ייזום", units=f"{_units_yz:,}", count=len(_yezum)),
        unsafe_allow_html=True,
    )


# ============================================================================
# ROW 5: DETAILED ANALYTICS (compact expander)
# ============================================================================

with st.expander("ניתוח מפורט", expanded=False):
    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        st.markdown("**מכרזים פעילים לפי עיר**")
        city_counts = active_df["city"].value_counts().head(10)
        if len(city_counts) > 0:
            fig_city = px.bar(
                x=city_counts.values, y=city_counts.index, orientation="h",
                labels={"x": "מספר מכרזים", "y": "עיר"},
                color_discrete_sequence=["#2563EB"],
            )
            fig_city.update_layout(
                showlegend=False, height=260,
                margin=dict(t=10, b=30, l=10, r=10),
                coloraxis_showscale=False,
                font=PLOTLY_FONT, **PLOTLY_BG,
            )
            st.plotly_chart(fig_city, use_container_width=True)
        else:
            st.info("אין נתונים")

    with chart_col2:
        st.markdown("**מכרזים לפי סוג**")
        type_counts = active_df["tender_type"].value_counts()
        if len(type_counts) > 0:
            fig_type = px.pie(
                values=type_counts.values, names=type_counts.index,
                hole=0.4, color_discrete_sequence=MEGIDO_CHART_COLORS,
            )
            fig_type.update_layout(
                height=260, margin=dict(t=10, b=30, l=10, r=10),
                font=PLOTLY_FONT, **PLOTLY_BG,
            )
            st.plotly_chart(fig_type, use_container_width=True)
        else:
            st.info("אין נתונים")

    chart_col3, chart_col4 = st.columns(2)

    with chart_col3:
        st.markdown("**מכרזים לאורך זמן**")
        timeline_df = active_df.copy()
        if len(timeline_df) > 0 and timeline_df["publish_date"].notna().any():
            timeline_df["month"] = timeline_df["publish_date"].dt.to_period("M").astype(str)
            monthly = timeline_df.groupby("month").size().reset_index(name="count")
            fig_tl = px.line(
                monthly, x="month", y="count", markers=True,
                labels={"month": "חודש", "count": "מספר"},
                color_discrete_sequence=["#1E3A5F"],
            )
            fig_tl.update_layout(
                height=260, margin=dict(t=10, b=30, l=10, r=10),
                font=PLOTLY_FONT, **PLOTLY_BG,
            )
            st.plotly_chart(fig_tl, use_container_width=True)
        else:
            st.info("אין נתוני תאריכים")

    with chart_col4:
        st.markdown('**יח"ד לפי סוג**')
        units_by_type = active_df.groupby("tender_type")["units"].sum().reset_index()
        units_by_type = units_by_type[units_by_type["units"] > 0]
        if not units_by_type.empty:
            fig_u = px.bar(
                units_by_type, x="tender_type", y="units",
                labels={"units": 'סה"כ יח"ד', "tender_type": "סוג"},
                color_discrete_sequence=["#2563EB"],
            )
            fig_u.update_layout(
                height=260, margin=dict(t=10, b=30, l=10, r=10),
                font=PLOTLY_FONT, **PLOTLY_BG,
            )
            st.plotly_chart(fig_u, use_container_width=True)
        else:
            st.info("אין נתוני יח\"ד")


# ============================================================================
# ROW 6: DEBUG (compact expander)
# ============================================================================

with st.expander("ניהול ודיבוג", expanded=False):
    st.markdown("### סטטוס מערכת")
    st.code(
        f"רשומות שנטענו: {len(df_all):,}\n"
        f"לאחר סינון סוג: {len(df):,}\n"
        f"פעילים: {len(active_df):,}\n"
        f"סוגי מכרז: {', '.join(df['tender_type'].unique().tolist())}",
    )
    st.markdown("### API Endpoints")
    st.code(
        f"List: {LAND_AUTHORITY_API} (POST)\n"
        f"Detail: {TENDER_DETAIL_API}?michrazID=\n"
        f"Docs: {DOCUMENT_DOWNLOAD_API}",
    )
