"""
Management overview page — לוח הנהלה.

Shows curated selected tenders (shared watchlist) with review status tracking,
closing-soon tenders (collapsible), tender-type cards with units, and compact KPIs.
Branded for MEGIDO BY AURA (מגידו י.ק.).
"""

from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import pandas as pd
import plotly.express as px
import streamlit as st

from config import CLOSING_SOON_DAYS, NON_ACTIVE_STATUSES, RELEVANT_TENDER_TYPES, TEAM_EMAIL
from dashboard_utils import (
    MEGIDO_CHART_COLORS,
    PLOTLY_BG,
    PLOTLY_FONT,
    load_data,
)
from db import TenderDB
from user_db import UserDB

# Purpose filter: same as dashboard
RELEVANT_PURPOSES = {"בנייה רוויה", "בנייה נמוכה/צמודת קרקע", "דיור מוגן (בית אבות)", "אחר"}

# The 3 tender types for the active card
CARD_TENDER_TYPES = {1, 5, 8}


# ============================================================================
# SIDEBAR (read-only stats)
# ============================================================================

today = datetime.now()
df_all = load_data(data_source="latest_file")
# Apply same filters as dashboard
df = df_all[df_all["tender_type_code"].isin(RELEVANT_TENDER_TYPES)].copy()
if "purpose" in df.columns:
    df = df[df["purpose"].isin(RELEVANT_PURPOSES)].copy()
watch_db = UserDB()

with st.sidebar:
    logo_path = Path(__file__).parent.parent / "assets" / "logo megido.jpg"
    if logo_path.exists():
        st.image(str(logo_path), width=140)
    st.markdown("""
    <div class="sidebar-header">
        <h2 style="color:#60A5FA !important;">MEGIDO</h2>
        <p>מגידו י.ק. | לוח הנהלה</p>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("---")

    _watched_count = len(watch_db.get_watchlist_ids(TEAM_EMAIL))
    st.caption(f"עדכון אחרון: {today.strftime('%Y-%m-%d %H:%M')}")
    st.caption(f"סה\"כ רשומות במאגר: {len(df):,}")
    st.caption(f"מכרזים מועדפים: {_watched_count}")


# ============================================================================
# FILTER TO ACTIVE TENDERS
# ============================================================================

active_df = df[~df['status'].isin(NON_ACTIVE_STATUSES)].copy()

if 'deadline' in active_df.columns:
    active_df['deadline'] = pd.to_datetime(active_df['deadline'], errors='coerce')


# ============================================================================
# HELPERS
# ============================================================================

def _urgency(days: Optional[int]) -> str:
    """Return urgency emoji based on days remaining."""
    if days is None or pd.isna(days):
        return "⚪"
    if days <= 7:
        return "🔴"
    if days <= 14:
        return "🟡"
    return "🟢"


_REVIEW_EMOJI: dict[str, str] = {
    "לא נסקר": "⬜",
    "סקירה ראשונית": "🔵",
    "בדיקה מעמיקה": "🟣",
    "הוצג בפורום": "🟠",
    "אושר בפורום": "🟢",
}


def _build_compact_table(
    source_df: pd.DataFrame,
    show_days_count: bool = False,
) -> pd.DataFrame:
    """Build a compact display DataFrame from tender data.

    Args:
        source_df: DataFrame with tender_name, city, tender_type, units,
                   deadline, published_booklet columns.
        show_days_count: If True, append days count to deadline format.

    Returns:
        Display-ready DataFrame with formatted columns.
    """
    tbl = source_df[[
        'tender_name', 'city', 'tender_type', 'units',
        'deadline', 'published_booklet',
    ]].copy()

    tbl['deadline'] = pd.to_datetime(tbl['deadline'], errors='coerce')
    tbl['days_left'] = tbl['deadline'].apply(
        lambda d: (d - today).days if pd.notna(d) else None
    )
    tbl['urgency'] = tbl['days_left'].apply(_urgency)

    if show_days_count:
        tbl['deadline_fmt'] = tbl.apply(
            lambda r: f"{r['urgency']} {r['deadline'].strftime('%d/%m')} ({int(r['days_left'])}ד׳)"
            if pd.notna(r['deadline']) and pd.notna(r['days_left']) else "—",
            axis=1,
        )
    else:
        tbl['deadline_fmt'] = tbl.apply(
            lambda r: f"{r['urgency']} {r['deadline'].strftime('%d/%m')}"
            if pd.notna(r['deadline']) else "—",
            axis=1,
        )

    tbl['booklet'] = tbl['published_booklet'].apply(
        lambda x: "✅" if x else "❌"
    )

    return tbl[['tender_name', 'city', 'tender_type', 'units',
                'deadline_fmt', 'booklet']].copy()


_COMPACT_COLUMNS = {
    "tender_name": st.column_config.TextColumn("מכרז", width="small"),
    "city": st.column_config.TextColumn("עיר", width="medium"),
    "tender_type": st.column_config.TextColumn("סוג", width="medium"),
    "units": st.column_config.NumberColumn("יח\"ד", format="%d", width="small"),
    "deadline_fmt": st.column_config.TextColumn("מועד", width="small"),
    "booklet": st.column_config.TextColumn("חוברת", width="small"),
}


# ============================================================================
# SECTION 1: SELECTED TENDERS + REVIEW STATUS (מכרזים מועדפים - חדר עסקאות)
# ============================================================================

st.markdown("#### מכרזים מועדפים - חדר עסקאות")

# Build watchlist_df by joining Supabase rows (id, tender_id, created_at, notes) with tender data
_watched_rows_main = watch_db.get_watchlist_rows(TEAM_EMAIL)
_watched_ids_main = [int(r["tender_id"]) for r in _watched_rows_main]
# notes lookup: tender_id -> note string
_notes_map: dict[int, str] = {
    int(r["tender_id"]): (r.get("notes") or "") for r in _watched_rows_main
}

if _watched_ids_main:
    watchlist_df = df[df['tender_id'].astype(int).isin(_watched_ids_main)].copy()
else:
    watchlist_df = pd.DataFrame()

if len(watchlist_df) > 0:
    display_sel = _build_compact_table(watchlist_df)

    watched_ids = watchlist_df['tender_id'].astype(int).tolist()
    review_map = watch_db.get_review_statuses_for_tenders(watched_ids)

    display_sel['review'] = [
        _REVIEW_EMOJI.get(
            review_map.get(int(tid), {}).get("status", "לא נסקר"), "⬜"
        ) + " " + review_map.get(int(tid), {}).get("status", "לא נסקר")
        for tid in watchlist_df['tender_id']
    ]

    # Attach personal notes (read-only) from the watchlist table
    display_sel['notes'] = [
        _notes_map.get(int(tid), "") for tid in watchlist_df['tender_id']
    ]

    st.dataframe(
        display_sel,
        column_config={
            **_COMPACT_COLUMNS,
            "review": st.column_config.TextColumn("סטטוס סקירה", width="medium"),
            "notes": st.column_config.TextColumn("הערות", width="large"),
        },
        hide_index=True,
        use_container_width=True,
    )

else:
    st.info("אין מכרזים מועדפים. הוסף מכרזים דרך דאשבורד חדר העסקאות.")

st.markdown("---")


# ============================================================================
# SECTION 2: CLOSING SOON — collapsed expander by default
# ============================================================================

closing_soon = active_df[
    (active_df['deadline'].notna()) &
    (active_df['deadline'] >= today) &
    (active_df['deadline'] <= today + timedelta(days=CLOSING_SOON_DAYS))
].sort_values('deadline').copy()


@st.dialog("פרטי מכרז", width="large")
def _show_tender_detail(tender_id: int) -> None:
    """Show tender detail in a modal dialog."""
    sqlite_db = TenderDB()
    tender = sqlite_db.get_tender_by_id(tender_id)
    if tender is None:
        st.error("מכרז לא נמצא")
        return

    st.markdown(f"### מכרז {tender.get('tender_name', tender_id)}")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"**עיר:** {tender.get('city', '—')}")
        st.markdown(f"**מחוז:** {tender.get('region', '—')}")
        st.markdown(f"**סוג:** {tender.get('tender_type', '—')}")
        st.markdown(f"**ייעוד:** {tender.get('purpose', '—')}")
    with c2:
        st.markdown(f"**יח\"ד:** {tender.get('units', '—')}")
        st.markdown(f"**סטטוס:** {tender.get('status', '—')}")
        dl = tender.get('deadline', '')
        if dl:
            dl_dt = pd.to_datetime(dl, errors='coerce')
            if pd.notna(dl_dt):
                days = (dl_dt - today).days
                st.markdown(
                    f"**מועד סגירה:** {dl_dt.strftime('%d/%m/%Y')} "
                    f"({_urgency(days)} {days} ימים)"
                )
        booklet = "✅" if tender.get('published_booklet') else "❌"
        st.markdown(f"**חוברת:** {booklet}")

    if tender.get('location'):
        st.markdown(f"**שכונה:** {tender['location']}")
    if tender.get('gush'):
        st.markdown(f"**גוש/חלקה:** {tender.get('gush', '')} / {tender.get('helka', '')}")


with st.expander(f"מכרזים שייסגרו בשבועיים הקרובים ({len(closing_soon)})", expanded=False):
    if len(closing_soon) > 0:
        display_cs = _build_compact_table(closing_soon, show_days_count=True)

        st.dataframe(
            display_cs,
            column_config=_COMPACT_COLUMNS,
            hide_index=True,
            use_container_width=True,
        )

        cs_ids = closing_soon['tender_id'].tolist()
        cs_labels = {
            int(r['tender_id']): f"{r.get('tender_name', '')} — {r.get('city', '')}"
            for _, r in closing_soon.iterrows()
        }

        pc1, pc2 = st.columns([3, 1])
        with pc1:
            popup_tender = st.selectbox(
                "בחר מכרז לצפייה בפרטים",
                options=cs_ids,
                format_func=lambda tid: cs_labels.get(int(tid), str(tid)),
                key="closing_popup_select",
                index=None,
                placeholder="בחר מכרז...",
            )
        with pc2:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("פרטים", key="btn_closing_detail"):
                if popup_tender is not None:
                    _show_tender_detail(int(popup_tender))

        st.caption(f"מציג {len(closing_soon)} מכרזים שנסגרים תוך {CLOSING_SOON_DAYS} יום")
    else:
        st.info(f"אין מכרזים שנסגרים תוך {CLOSING_SOON_DAYS} יום.")

st.markdown("---")


# ============================================================================
# SECTION 2B: PIE CHARTS + KPI CARDS
# ============================================================================

_pie_col, _kpi_col = st.columns([3, 2])

with _pie_col:
    _mp1, _mp2 = st.columns(2)

    # ── Pie: Brochure availability ────────────────────────────────────
    with _mp1:
        st.markdown('<p class="pie-title" style="font-size:13px;">חוברת מכרז</p>', unsafe_allow_html=True)
        if "published_booklet" in active_df.columns and len(active_df) > 0:
            _bc = active_df["published_booklet"].value_counts()
            _avail = int(_bc.get(True, 0))
            _not_avail = int(_bc.get(False, 0))
            _fig_b = px.pie(
                values=[_avail, _not_avail],
                names=["יש חוברת", "בלי חוברת"],
                color_discrete_sequence=["#2563EB", "#E2E8F0"],
                hole=0.55,
            )
            _fig_b.update_traces(textinfo="value", textposition="inside", textfont_size=12)
            _fig_b.update_layout(
                height=220, margin=dict(t=5, b=30, l=5, r=5),
                showlegend=True,
                legend=dict(
                    orientation="h", yanchor="top", y=-0.05,
                    xanchor="center", x=0.5, font=dict(size=11),
                ),
                font=PLOTLY_FONT, **PLOTLY_BG,
            )
            st.plotly_chart(_fig_b, use_container_width=True, key="mgmt_pie_booklet")
        else:
            st.info("אין נתונים")

    # ── Pie: Region distribution ──────────────────────────────────────
    with _mp2:
        st.markdown('<p class="pie-title" style="font-size:13px;">מכרזים לפי מחוז</p>', unsafe_allow_html=True)
        if "region" in active_df.columns and len(active_df) > 0:
            _reg = active_df.groupby("region").size().reset_index(name="count").sort_values("count", ascending=False)
            if not _reg.empty:
                _fig_r = px.pie(
                    _reg, values="count", names="region",
                    hole=0.55, color_discrete_sequence=MEGIDO_CHART_COLORS,
                )
                _fig_r.update_traces(textinfo="value", textposition="inside", textfont_size=12)
                _fig_r.update_layout(
                    height=220, margin=dict(t=5, b=30, l=5, r=5),
                    showlegend=True,
                    legend=dict(
                        orientation="h", yanchor="top", y=-0.05,
                        xanchor="center", x=0.5, font=dict(size=10),
                    ),
                    font=PLOTLY_FONT, **PLOTLY_BG,
                )
                st.plotly_chart(_fig_r, use_container_width=True, key="mgmt_pie_region")
            else:
                st.info("אין נתוני מחוזות")
        else:
            st.info("אין נתונים")

with _kpi_col:
    _card_active = active_df[active_df["tender_type_code"].isin(CARD_TENDER_TYPES)]
    _closing_count = len(closing_soon)
    _mk1, _mk2 = st.columns(2)
    with _mk1:
        st.metric("מכרזים פעילים", f"{len(_card_active):,}")
    with _mk2:
        st.metric("נסגרים ב-14 יום", f"{_closing_count}")

st.markdown("---")


# ============================================================================
# SECTION 3: BOTTOM CATEGORY CARDS — דיור להשכרה, דיור מוגן, מכרז ייזום
# ============================================================================

st.markdown("#### סוגים נוספים")

# Use unfiltered-by-purpose data for these categories
_all_typed = df_all[df_all["tender_type_code"].isin(RELEVANT_TENDER_TYPES)].copy()
_all_active = _all_typed[~_all_typed["status"].isin(NON_ACTIVE_STATUSES)].copy()

tab_diur_h, tab_diur_m, tab_yezum = st.tabs(["דיור להשכרה", "דיור מוגן", "מכרז ייזום"])

with tab_diur_h:
    diur_h_df = _all_active[_all_active['tender_type'] == "דיור להשכרה"].copy()
    if len(diur_h_df) > 0:
        _units_dh = int(diur_h_df["units"].sum())
        st.metric(f"סה\"כ יח\"ד", f"{_units_dh:,}")
        display_dh = _build_compact_table(diur_h_df, show_days_count=True)
        st.dataframe(
            display_dh,
            column_config=_COMPACT_COLUMNS,
            hide_index=True,
            use_container_width=True,
        )
        st.caption(f"{len(diur_h_df)} מכרזי דיור להשכרה פעילים")
    else:
        st.info("אין מכרזי דיור להשכרה פעילים כרגע.")

with tab_diur_m:
    diur_m_df = _all_active[_all_active["purpose"].str.contains("דיור מוגן", na=False)].copy() if "purpose" in _all_active.columns else pd.DataFrame()
    if len(diur_m_df) > 0:
        _units_dm = int(diur_m_df["units"].sum())
        st.metric(f"סה\"כ יח\"ד", f"{_units_dm:,}")
        display_dm = _build_compact_table(diur_m_df, show_days_count=True)
        st.dataframe(
            display_dm,
            column_config=_COMPACT_COLUMNS,
            hide_index=True,
            use_container_width=True,
        )
        st.caption(f"{len(diur_m_df)} מכרזי דיור מוגן פעילים")
    else:
        st.info("אין מכרזי דיור מוגן פעילים כרגע.")

with tab_yezum:
    yezum_df = _all_active[_all_active['tender_type'] == "מכרז ייזום"].copy()
    if len(yezum_df) > 0:
        _units_yz = int(yezum_df["units"].sum())
        st.metric(f"סה\"כ יח\"ד", f"{_units_yz:,}")
        display_y = _build_compact_table(yezum_df, show_days_count=True)
        st.dataframe(
            display_y,
            column_config=_COMPACT_COLUMNS,
            hide_index=True,
            use_container_width=True,
        )
        st.caption(f"{len(yezum_df)} מכרזי ייזום פעילים")
    else:
        st.info("אין מכרזי ייזום פעילים כרגע.")

st.markdown("---")
