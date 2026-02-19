"""
Management overview page — team operational dashboard.

Shows curated selected tenders (shared watchlist) with review status tracking,
closing-soon tenders with popup detail, tender-type tabs, and compact KPIs.
Branded for MEGIDO BY AURA (מגידו י.ק.).
"""

from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import pandas as pd
import streamlit as st

from config import CLOSING_SOON_DAYS, NON_ACTIVE_STATUSES, TEAM_EMAIL
from dashboard_utils import get_user_email, load_data
from db import REVIEW_STAGES, TenderDB


# ============================================================================
# SIDEBAR (minimal)
# ============================================================================

with st.sidebar:
    logo_path = Path(__file__).parent.parent / "assets" / "logo.jpg"
    if logo_path.exists():
        st.image(str(logo_path), width=140)
    st.markdown("""
    <div class="sidebar-header">
        <h2>MEGIDO</h2>
        <p>מגידו י.ק. | סקירה ניהולית</p>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("---")

    today = datetime.now()
    df = load_data(data_source="latest_file")

    st.caption(f"עדכון אחרון: {today.strftime('%Y-%m-%d %H:%M')}")
    st.caption(f"סה\"כ רשומות במאגר: {len(df):,}")

    watch_db = TenderDB()
    watchlist_df = watch_db.get_user_watchlist(TEAM_EMAIL)
    st.caption(f"מכרזים במעקב: {len(watchlist_df)}")


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
# SECTION 1: SELECTED TENDERS + REVIEW STATUS
# ============================================================================

st.markdown("#### 📋 מכרזים נבחרים")

if len(watchlist_df) > 0:
    # Build compact table
    display_sel = _build_compact_table(watchlist_df)

    # Fetch review statuses for all watched tenders
    watched_ids = watchlist_df['tender_id'].astype(int).tolist()
    review_map = watch_db.get_review_statuses_for_tenders(watched_ids)

    # Add review status column
    display_sel['review'] = [
        _REVIEW_EMOJI.get(
            review_map.get(int(tid), {}).get("status", "לא נסקר"), "⬜"
        ) + " " + review_map.get(int(tid), {}).get("status", "לא נסקר")
        for tid in watchlist_df['tender_id']
    ]

    st.dataframe(
        display_sel,
        column_config={
            **_COMPACT_COLUMNS,
            "review": st.column_config.TextColumn("סטטוס סקירה", width="medium"),
        },
        hide_index=True,
        use_container_width=True,
    )

    # ── Review status update controls ──────────────────────────────────
    with st.expander("🔄 עדכון סטטוס סקירה", expanded=False):
        user_email = get_user_email() or "unknown"

        # Build tender selectbox options
        _sel_labels: dict[int, str] = {}
        for _, _r in watchlist_df.iterrows():
            _name = str(_r.get('tender_name', ''))[:30]
            _city = str(_r.get('city', ''))[:15]
            _sel_labels[int(_r['tender_id'])] = f"{_name} — {_city}"

        rc1, rc2 = st.columns([2, 2])
        with rc1:
            review_tender_id = st.selectbox(
                "מכרז",
                options=list(_sel_labels.keys()),
                format_func=lambda tid: _sel_labels[tid],
                key="review_tender_select",
            )
        with rc2:
            # Pre-select current status
            current_status = review_map.get(
                review_tender_id, {},
            ).get("status", REVIEW_STAGES[0])
            current_idx = (
                REVIEW_STAGES.index(current_status)
                if current_status in REVIEW_STAGES else 0
            )
            new_status = st.selectbox(
                "סטטוס חדש",
                options=REVIEW_STAGES,
                index=current_idx,
                key="review_status_select",
            )

        notes = st.text_input(
            "הערות (אופציונלי)", key="review_notes", placeholder="..."
        )

        if st.button("💾 עדכן סטטוס", key="btn_update_review"):
            prev = watch_db.set_review_status(
                tender_id=review_tender_id,
                status=new_status,
                updated_by=user_email,
                notes=notes or None,
            )
            tender_label = _sel_labels.get(review_tender_id, str(review_tender_id))
            st.success(f"מכרז {tender_label}: {prev or 'חדש'} → {new_status}")

            # TODO: WhatsApp notification integration
            # When WhatsApp Business API is configured, send message here:
            # f"🔔 מכרז {tender_label} — סטטוס עודכן: {new_status} (ע\"י {user_email})"

            st.rerun()

else:
    st.info(
        "אין מכרזים ברשימת המעקב. "
        "הוסף מכרזים מלוח המכרזים הראשי (📋 לוח מכרזים)."
    )

st.markdown("---")


# ============================================================================
# SECTION 2: CLOSING SOON + POPUP DETAIL
# ============================================================================

st.markdown("#### ⏰ נסגרים בקרוב")

closing_soon = active_df[
    (active_df['deadline'].notna()) &
    (active_df['deadline'] >= today) &
    (active_df['deadline'] <= today + timedelta(days=CLOSING_SOON_DAYS))
].sort_values('deadline').copy()


@st.dialog("📋 פרטי מכרז", width="large")
def _show_tender_detail(tender_id: int) -> None:
    """Show tender detail in a modal dialog."""
    tender = watch_db.get_tender_by_id(tender_id)
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


if len(closing_soon) > 0:
    display_cs = _build_compact_table(closing_soon, show_days_count=True)

    st.dataframe(
        display_cs,
        column_config=_COMPACT_COLUMNS,
        hide_index=True,
        use_container_width=True,
    )

    # Button to show all closing-soon tenders in popup
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
        if st.button("🔍 פרטים", key="btn_closing_detail"):
            if popup_tender is not None:
                _show_tender_detail(int(popup_tender))

    st.caption(f"מציג {len(closing_soon)} מכרזים שנסגרים תוך {CLOSING_SOON_DAYS} יום")
else:
    st.info(f"אין מכרזים שנסגרים תוך {CLOSING_SOON_DAYS} יום.")

st.markdown("---")


# ============================================================================
# SECTION 3: TENDER TYPE TABS
# ============================================================================

st.markdown("#### 🏷️ מכרזים לפי סוג")

tab_yezum, tab_diur, tab_all = st.tabs(["מכרז ייזום", "דיור להשכרה", "כל המכרזים"])

with tab_yezum:
    yezum_df = active_df[active_df['tender_type'] == "מכרז ייזום"].copy()
    if len(yezum_df) > 0:
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

with tab_diur:
    diur_df = active_df[active_df['tender_type'] == "דיור להשכרה"].copy()
    if len(diur_df) > 0:
        display_d = _build_compact_table(diur_df, show_days_count=True)
        st.dataframe(
            display_d,
            column_config=_COMPACT_COLUMNS,
            hide_index=True,
            use_container_width=True,
        )
        st.caption(f"{len(diur_df)} מכרזי דיור להשכרה פעילים")
    else:
        st.info("אין מכרזי דיור להשכרה פעילים כרגע.")

with tab_all:
    if len(active_df) > 0:
        display_all = _build_compact_table(active_df, show_days_count=True)
        st.dataframe(
            display_all,
            column_config=_COMPACT_COLUMNS,
            hide_index=True,
            use_container_width=True,
        )
        st.caption(f"{len(active_df)} מכרזים פעילים")
    else:
        st.info("אין מכרזים פעילים.")

st.markdown("---")


# ============================================================================
# SECTION 4: COMPACT KPIs
# ============================================================================

total_units = int(active_df['units'].sum()) if 'units' in active_df.columns else 0
unique_cities = active_df['city'].nunique() if 'city' in active_df.columns else 0
closing_count = len(closing_soon)
yezum_count = len(active_df[active_df['tender_type'] == "מכרז ייזום"])
diur_count = len(active_df[active_df['tender_type'] == "דיור להשכרה"])

k1, k2, k3, k4, k5, k6 = st.columns(6)
k1.metric("🟢 פעילים", f"{len(active_df):,}")
k2.metric("🏠 יח\"ד", f"{total_units:,}")
k3.metric(f"⏰ ≤{CLOSING_SOON_DAYS}ד׳", f"{closing_count}")
k4.metric("📋 במעקב", f"{len(watchlist_df)}")
k5.metric("🔨 ייזום", f"{yezum_count}")
k6.metric("🏘️ דיור", f"{diur_count}")
