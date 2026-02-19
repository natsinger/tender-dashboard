"""
Full dashboard page — daily user view.

Compact card-based layout: pre-filtered to 5 relevant tender types + active only.
Sections: header, KPIs, new tenders + pies, deadlines + explorer,
tender detail, watchlist, review status, analytics, debug.
Branded for MEGIDO BY AURA.
"""

from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict

import pandas as pd
import plotly.express as px
import streamlit as st

from config import (
    CLOSING_SOON_DAYS,
    DATA_DIR,
    DEFAULT_FETCH_DELAY,
    DEFAULT_FETCH_WORKERS,
    DOCUMENT_DOWNLOAD_API,
    LAND_AUTHORITY_API,
    NON_ACTIVE_STATUSES,
    RELEVANT_TENDER_TYPES,
    RMI_SITE_URL,
    TEAM_EMAIL,
    TENDER_DETAIL_API,
)
from dashboard_utils import get_user_email, load_data, load_tender_details, render_email_input
from data_client import LandTendersClient, build_document_url
from user_db import REVIEW_STAGES, UserDB

# ── Constants ────────────────────────────────────────────────────────────────
CHART_COLORS = ["#1B6B3A", "#3B82F6", "#D4A017", "#10B981", "#EF4444", "#8B5CF6"]
GOLD_SCALE = [[0, "#FEF3C7"], [1, "#D4A017"]]
PLOTLY_FONT = dict(family="Inter, Heebo, sans-serif", size=11, color="#111827")
PLOTLY_BG = dict(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")

today = datetime.now()

# ── Load & pre-filter data ───────────────────────────────────────────────────
render_email_input()

df_all = load_data(data_source="latest_file")
df = df_all[df_all["tender_type_code"].isin(RELEVANT_TENDER_TYPES)].copy()
active_df = df[~df["status"].isin(NON_ACTIVE_STATUSES)].copy()


# ============================================================================
# SIDEBAR — Light, clean
# ============================================================================

with st.sidebar:
    logo_path = Path(__file__).parent.parent / "assets" / "logo megido.jpg"
    if logo_path.exists():
        st.image(str(logo_path), width=160)

    st.markdown("---")

    # ── Team watchlist ────────────────────────────────────────────────────
    st.markdown('<p class="sidebar-section-label">צוות</p>', unsafe_allow_html=True)
    st.markdown("**📋 מכרזים נבחרים**")

    _sidebar_email = get_user_email()
    _team_db = UserDB()

    if not _sidebar_email:
        st.caption("יש להזדהות כדי לנהל מכרזים")
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

        if st.button("➕ הוסף למעקב", key="dash_team_btn_add", use_container_width=True):
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
                _tc1, _tc2 = st.columns([5, 1])
                with _tc1:
                    st.caption(_tdisplay)
                with _tc2:
                    if st.button("🗑️", key=f"dash_team_rm_{_tw['id']}"):
                        _team_db.remove_from_watchlist(TEAM_EMAIL, _ttid)
                        st.rerun()
        else:
            st.caption("אין מכרזים נבחרים")

    # ── Stats footer ─────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown('<p class="sidebar-section-label">מידע</p>', unsafe_allow_html=True)
    st.caption(f"עדכון: {today.strftime('%d/%m/%Y %H:%M')}")
    st.caption(f"רשומות: {len(df):,} (מתוך {len(df_all):,})")


# ============================================================================
# HEADER
# ============================================================================

st.markdown(
    '<div style="padding:8px 0 2px 0;">'
    '<span style="font-size:1.5rem;font-weight:700;color:#111827;">לוח מכרזים</span>'
    '<br>'
    '<span style="font-size:0.8rem;color:#9CA3AF;">'
    f'מעקב מכרזי קרקע  •  {today.strftime("%d/%m/%Y")}'
    "</span>"
    "</div>",
    unsafe_allow_html=True,
)

# ============================================================================
# ROW 1: 4 KPI CARDS (first one highlighted)
# ============================================================================

closing_soon_count = len(
    active_df[
        (active_df["deadline"].notna())
        & (active_df["deadline"] >= today)
        & (active_df["deadline"] <= today + timedelta(days=CLOSING_SOON_DAYS))
    ]
)

k1, k2, k3, k4 = st.columns(4)
with k1:
    st.markdown('<div class="kpi-primary">', unsafe_allow_html=True)
    st.metric("מכרזים פעילים", f"{len(active_df):,}")
    st.markdown("</div>", unsafe_allow_html=True)
with k2:
    st.metric("יח\"ד", f"{int(active_df['units'].sum()):,}")
with k3:
    st.metric("ערים", f"{active_df['city'].nunique()}")
with k4:
    st.metric(f"נסגרים ב-{CLOSING_SOON_DAYS} יום", closing_soon_count)


# ============================================================================
# ROW 2: NEW TENDERS (card) + PIE CHARTS (card)
# ============================================================================


def _last_sunday(ref_date: datetime) -> datetime:
    """Return the most recent Sunday (00:00) on or before ref_date."""
    days_since = ref_date.weekday() + 1
    if days_since == 7:
        days_since = 0
    return (ref_date - timedelta(days=days_since)).replace(hour=0, minute=0, second=0, microsecond=0)


sunday_cutoff = _last_sunday(today)

new_tenders_df = active_df[
    (active_df["published_booklet"] == True)
    & (active_df["deadline"].notna())
    & (active_df["deadline"] >= today)
].copy()

date_col = None
for candidate in ["created_date", "publish_date", "published_date"]:
    if candidate in new_tenders_df.columns:
        date_col = candidate
        break
if date_col:
    new_tenders_df = new_tenders_df[new_tenders_df[date_col] >= sunday_cutoff]

col_new, col_pies = st.columns([3, 2])

with col_new:
    with st.container(border=True):
        st.markdown(
            f'<div class="section-header">'
            f"🆕 מכרזים חדשים ({sunday_cutoff.strftime('%d/%m')})"
            f"</div>",
            unsafe_allow_html=True,
        )
        if len(new_tenders_df) > 0:
            new_display = new_tenders_df[["tender_name", "city", "units", "tender_type", "deadline"]].copy()
            new_display.columns = ["שם מכרז", "עיר", 'יח"ד', "סוג", "מועד אחרון"]
            new_display["מועד אחרון"] = pd.to_datetime(new_display["מועד אחרון"]).dt.strftime("%d/%m/%Y")
            new_display = new_display.sort_values('יח"ד', ascending=False)
            st.dataframe(
                new_display,
                use_container_width=True,
                hide_index=True,
                height=min(35 * len(new_display) + 38, 240),
            )
        else:
            st.info("אין מכרזים חדשים עם חוברת השבוע")

with col_pies:
    with st.container(border=True):
        st.markdown('<div class="section-header">📊 תמונת מצב</div>', unsafe_allow_html=True)
        p1, p2, p3 = st.columns(3)

        # ── Pie 1: Brochure availability ─────────────────────────────────
        with p1:
            st.markdown('<p class="pie-title">חוברת מכרז</p>', unsafe_allow_html=True)
            if "published_booklet" in active_df.columns and len(active_df) > 0:
                bc = active_df["published_booklet"].value_counts()
                avail, not_avail = int(bc.get(True, 0)), int(bc.get(False, 0))
                fig1 = px.pie(values=[avail, not_avail], names=["זמינה", "לא זמינה"],
                              color_discrete_sequence=["#1B6B3A", "#E5E7EB"], hole=0.55)
                fig1.update_traces(textinfo="value", textposition="inside", textfont_size=11)
                fig1.update_layout(height=160, margin=dict(t=2, b=2, l=2, r=2),
                                   showlegend=False, font=PLOTLY_FONT, **PLOTLY_BG)
                st.plotly_chart(fig1, use_container_width=True, key="pie_booklet")

        # ── Pie 2: Brochures by region ───────────────────────────────────
        with p2:
            st.markdown('<p class="pie-title">לפי מחוז</p>', unsafe_allow_html=True)
            pie2_opts = {"1W": 7, "2W": 14, "4W": 28}
            urg = st.session_state.get("urgency_pie2", "4W")
            pie2_days = pie2_opts.get(urg, 28)
            pie2_df = active_df[active_df["published_booklet"] == True].copy()
            pie2_cut = today + timedelta(days=pie2_days)
            pie2_df = pie2_df[(pie2_df["deadline"].notna()) & (pie2_df["deadline"] >= today) & (pie2_df["deadline"] <= pie2_cut)]

            if "region" in pie2_df.columns and len(pie2_df) > 0:
                br = pie2_df.groupby("region").size().reset_index(name="count").sort_values("count", ascending=False)
                if not br.empty:
                    fig2 = px.pie(br, values="count", names="region", hole=0.55, color_discrete_sequence=CHART_COLORS)
                    fig2.update_traces(textinfo="value", textposition="inside", textfont_size=11)
                    fig2.update_layout(height=160, margin=dict(t=2, b=2, l=2, r=2),
                                       showlegend=False, font=PLOTLY_FONT, **PLOTLY_BG)
                    st.plotly_chart(fig2, use_container_width=True, key="pie_brochure_region")
            st.radio("טווח", list(pie2_opts.keys()), index=2, horizontal=True, key="urgency_pie2", label_visibility="collapsed")

        # ── Pie 3: Active by region ──────────────────────────────────────
        with p3:
            st.markdown('<p class="pie-title">פעילים</p>', unsafe_allow_html=True)
            if "region" in active_df.columns and len(active_df) > 0:
                tr = active_df.groupby("region").size().reset_index(name="count").sort_values("count", ascending=False)
                if not tr.empty:
                    fig3 = px.pie(tr, values="count", names="region", hole=0.55, color_discrete_sequence=CHART_COLORS)
                    fig3.update_traces(textinfo="value", textposition="inside", textfont_size=11)
                    fig3.update_layout(height=160, margin=dict(t=2, b=2, l=2, r=2),
                                       showlegend=False, font=PLOTLY_FONT, **PLOTLY_BG)
                    st.plotly_chart(fig3, use_container_width=True, key="pie_region")


# ============================================================================
# ROW 3: CLOSING DEADLINES (card) + DATA EXPLORER (card)
# ============================================================================

col_dead, col_explore = st.columns([2, 3])

with col_dead:
    with st.container(border=True):
        st.markdown('<div class="section-header">⏰ מועדי סגירה</div>', unsafe_allow_html=True)
        show_all = st.toggle("הצג הכל", value=False, key="deadline_toggle")

        upcoming = active_df[
            (active_df["deadline"].notna()) & (active_df["deadline"] >= today)
        ].sort_values("deadline")
        if not show_all:
            upcoming = upcoming[upcoming["deadline"] <= today + timedelta(days=CLOSING_SOON_DAYS)]

        if len(upcoming) > 0:
            up_disp = upcoming[["tender_name", "city", "units", "deadline"]].copy()
            up_disp["days_left"] = (up_disp["deadline"] - today).dt.days

            def _urgency(d: int) -> str:
                if d <= 7:
                    return "🔴"
                if d <= 14:
                    return "🟡"
                return "🟢"

            up_disp.insert(0, "urg", up_disp["days_left"].apply(_urgency))
            up_disp["deadline"] = up_disp["deadline"].dt.strftime("%d/%m")
            st.dataframe(
                up_disp,
                column_config={
                    "urg": st.column_config.TextColumn("", width="small"),
                    "tender_name": st.column_config.TextColumn("שם", width="medium"),
                    "city": st.column_config.TextColumn("עיר", width="small"),
                    "units": st.column_config.NumberColumn('יח"ד', format="%d", width="small"),
                    "deadline": st.column_config.TextColumn("סגירה", width="small"),
                    "days_left": st.column_config.NumberColumn("ימים", format="%d", width="small"),
                },
                hide_index=True, use_container_width=True,
                height=min(35 * len(up_disp) + 38, 350),
            )
            st.caption(f"{len(up_disp)} מכרזים")
        else:
            st.info("אין מכרזים קרובים לסגירה")

with col_explore:
    with st.container(border=True):
        st.markdown('<div class="section-header">📋 סייר מכרזים</div>', unsafe_allow_html=True)

        explorer_df = active_df.copy()
        f1, f2, f3, f4 = st.columns(4)
        with f1:
            _cities = sorted(explorer_df["city"].dropna().unique().tolist())
            sel_cities = st.multiselect("עיר", _cities, default=[], key="exp_city", placeholder="הכל")
            if sel_cities:
                explorer_df = explorer_df[explorer_df["city"].isin(sel_cities)]
        with f2:
            _regions = sorted(explorer_df["region"].dropna().unique().tolist()) if "region" in explorer_df.columns else []
            sel_regions = st.multiselect("מחוז", _regions, default=[], key="exp_region", placeholder="הכל")
            if sel_regions:
                explorer_df = explorer_df[explorer_df["region"].isin(sel_regions)]
        with f3:
            _purposes = sorted(explorer_df["purpose"].dropna().unique().tolist()) if "purpose" in explorer_df.columns else []
            sel_purpose = st.multiselect("ייעוד", _purposes, default=[], key="exp_purpose", placeholder="הכל")
            if sel_purpose:
                explorer_df = explorer_df[explorer_df["purpose"].isin(sel_purpose)]
        with f4:
            _statuses = sorted(explorer_df["status"].dropna().unique().tolist())
            sel_status = st.multiselect("סטטוס", _statuses, default=[], key="exp_status", placeholder="הכל")
            if sel_status:
                explorer_df = explorer_df[explorer_df["status"].isin(sel_status)]

        EXP_COLS = ["tender_name", "city", "region", "tender_type", "purpose", "units", "deadline", "status", "published_booklet"]
        display_cols = [c for c in EXP_COLS if c in explorer_df.columns]

        if display_cols:
            exp_display = explorer_df[display_cols].copy()
            if "deadline" in exp_display.columns:
                exp_display = exp_display.sort_values("deadline", ascending=True, na_position="last")
            for col in ["publish_date", "deadline", "committee_date"]:
                if col in exp_display.columns:
                    exp_display[col] = pd.to_datetime(exp_display[col], errors="coerce")

            st.caption(f"{len(exp_display):,} רשומות")
            st.dataframe(
                exp_display, hide_index=True, use_container_width=True,
                column_config={
                    "tender_name": st.column_config.TextColumn("שם מכרז", width="large"),
                    "city": st.column_config.TextColumn("עיר", width="medium"),
                    "region": st.column_config.TextColumn("מחוז", width="small"),
                    "tender_type": st.column_config.TextColumn("סוג", width="medium"),
                    "purpose": st.column_config.TextColumn("ייעוד", width="medium"),
                    "units": st.column_config.NumberColumn('יח"ד', format="%d"),
                    "deadline": st.column_config.DateColumn("מועד סגירה", format="YYYY-MM-DD"),
                    "status": st.column_config.TextColumn("סטטוס", width="small"),
                    "published_booklet": st.column_config.CheckboxColumn("חוברת"),
                },
            )
            csv = explorer_df[display_cols].to_csv(index=False, encoding="utf-8-sig")
            st.download_button(
                label="📥 הורד CSV", data=csv,
                file_name=f"land_tenders_{today.strftime('%Y%m%d')}.csv", mime="text/csv",
            )


# ============================================================================
# TENDER DETAIL VIEWER (expander)
# ============================================================================

with st.expander("🔍 צפייה בפרטי מכרז", expanded=False):
    col_select, col_refresh = st.columns([4, 1])

    with col_select:
        detail_candidates = active_df.copy()
        if len(detail_candidates) == 0:
            detail_candidates = df.head(50)
        detail_candidates = detail_candidates.sort_values("deadline", ascending=False)

        def _fmt_label(row: pd.Series) -> str:
            name = row["tender_name"][:50] if pd.notna(row["tender_name"]) else "N/A"
            city = row["city"][:20] if pd.notna(row["city"]) else "N/A"
            return f"{row['tender_id']} - {name} ({city})"

        detail_candidates["_label"] = detail_candidates.apply(_fmt_label, axis=1)
        selected_tender_id = st.selectbox(
            "בחר מכרז", options=detail_candidates["tender_id"].tolist(),
            format_func=lambda tid: detail_candidates[detail_candidates["tender_id"] == tid]["_label"].values[0],
            key="detail_select",
        )

    with col_refresh:
        force_refresh = st.checkbox("רענן", value=False, help="עקוף מטמון")

    if selected_tender_id:
        with st.spinner(f"טוען פרטי מכרז {selected_tender_id}..."):
            details = load_tender_details(selected_tender_id)
            list_data = active_df[active_df["tender_id"] == selected_tender_id]
            list_data = list_data.iloc[0].to_dict() if len(list_data) > 0 else None

        if details:
            st.markdown("### סקירה כללית")
            ov1, ov2, ov3, ov4 = st.columns(4)
            with ov1:
                st.metric("מס' מכרז", details.get("MichrazID", selected_tender_id))
            with ov2:
                st.metric("סטטוס", list_data.get("status", "N/A") if list_data else "N/A")
            with ov3:
                units = details.get("YechidotDiur", list_data.get("units", 0) if list_data else 0)
                st.metric('יח"ד', f"{int(units):,}" if units else "N/A")
            with ov4:
                deadline_dt = pd.to_datetime(details.get("SgiraDate"), errors="coerce")
                if pd.notna(deadline_dt):
                    deadline_naive = deadline_dt.tz_localize(None) if deadline_dt.tzinfo else deadline_dt
                    st.metric("ימים לסגירה", (deadline_naive - today).days)
                else:
                    st.metric("מועד סגירה", "N/A")

            st.markdown("---")
            st.markdown("### פרטי מכרז")
            info_left, info_right = st.columns(2)
            with info_left:
                tender_name = details.get("MichrazName", "N/A")
                city_val = list_data.get("city", "N/A") if list_data else "N/A"
                location = details.get("Shchuna", list_data.get("location", "") if list_data else "")
                tender_type_val = list_data.get("tender_type", "N/A") if list_data else "N/A"
                purpose_val = list_data.get("purpose", "N/A") if list_data else "N/A"
                st.markdown(
                    f'<div class="detail-field">'
                    f"<strong>שם מכרז:</strong> {tender_name}<br>"
                    f"<strong>עיר:</strong> {city_val}<br>"
                    + (f"<strong>מיקום:</strong> {location}<br>" if location else "")
                    + f"<strong>סוג:</strong> {tender_type_val}<br>"
                    f"<strong>ייעוד:</strong> {purpose_val}</div>",
                    unsafe_allow_html=True,
                )
            with info_right:
                publish = pd.to_datetime(details.get("PtichaDate"), errors="coerce")
                publish_str = publish.strftime("%Y-%m-%d") if pd.notna(publish) else "N/A"
                deadline_dt2 = pd.to_datetime(details.get("SgiraDate"), errors="coerce")
                deadline_str = deadline_dt2.strftime("%Y-%m-%d %H:%M") if pd.notna(deadline_dt2) else "N/A"
                committee = pd.to_datetime(details.get("VaadaDate"), errors="coerce")
                committee_str = committee.strftime("%Y-%m-%d") if pd.notna(committee) else "N/A"
                st.markdown(
                    f'<div class="detail-field">'
                    f"<strong>תאריך פרסום:</strong> {publish_str}<br>"
                    f"<strong>מועד סגירה:</strong> {deadline_str}<br>"
                    f"<strong>תאריך ועדה:</strong> {committee_str}</div>",
                    unsafe_allow_html=True,
                )

            # Bids
            st.markdown("---")
            st.markdown("### 💰 הצעות ומציעים")
            plots = details.get("Tik", [])
            if plots:
                for plot_idx, plot in enumerate(plots, 1):
                    st.markdown(f"#### מגרש {plot_idx}: {plot.get('TikID', 'N/A')}")
                    winner_name = (plot.get("ShemZoche") or "").strip()
                    winner_amount = plot.get("SchumZchiya", 0)
                    if winner_name:
                        st.success(f"🏆 **זוכה:** {winner_name}")
                        st.markdown(
                            f'<div class="detail-field">'
                            f"<strong>סכום זכייה:</strong> ₪{winner_amount:,.2f} | "
                            f"<strong>שטח:</strong> {plot.get('Shetach', 0):,} מ\"ר | "
                            f"<strong>מחיר סף:</strong> ₪{plot.get('MechirSaf', 0):,.2f}</div>",
                            unsafe_allow_html=True,
                        )
                    bidders = plot.get("mpHatzaaotMitcham", [])
                    if bidders:
                        st.info(f"📊 **סה\"כ הצעות:** {len(bidders)}")
                        bidder_df = pd.DataFrame(bidders).sort_values("HatzaaSum", ascending=False)
                        disp_bid = bidder_df.copy()
                        disp_bid["HatzaaSum"] = disp_bid["HatzaaSum"].apply(lambda x: f"₪{x:,.2f}" if pd.notna(x) else "N/A")
                        disp_bid = disp_bid.rename(columns={"HatzaaID": "מס' הצעה", "HatzaaSum": "סכום", "HatzaaDescription": "תיאור"})
                        st.dataframe(disp_bid, use_container_width=True, hide_index=True)
                    else:
                        st.info("אין הצעות למגרש זה")
                    if plot_idx < len(plots):
                        st.markdown("---")
            else:
                st.info("אין מידע על הצעות")

            # Documents
            st.markdown("---")
            st.markdown("### 📄 מסמכים")
            full_doc = details.get("MichrazFullDocument")
            if full_doc and full_doc.get("RowID") is not None:
                doc_name = full_doc.get("DocName", "מסמך פרסום מלא.pdf")
                doc_url = build_document_url(full_doc)
                st.markdown(f"📕 [**הורד: {doc_name}**]({doc_url})")
            docs = details.get("MichrazDocList", [])
            if docs:
                st.markdown(f"#### 📁 מסמכים נוספים ({len(docs)})")
                for doc in docs[:15]:
                    d_name = doc.get("DocName", doc.get("Teur", "Unknown"))
                    d_desc = doc.get("Teur", "")
                    d_date = doc.get("UpdateDate", "")
                    if d_date:
                        dt = pd.to_datetime(d_date, errors="coerce")
                        if pd.notna(dt):
                            d_date = dt.strftime("%Y-%m-%d")
                    d_url = build_document_url(doc)
                    st.markdown(f"- [{d_name}]({d_url}) — {d_desc} ({d_date})")
                if len(docs) > 15:
                    st.caption(f"... ועוד {len(docs) - 15} מסמכים")
            elif not full_doc:
                st.info("אין מסמכים זמינים")
            st.markdown("---")
            st.markdown(f"🔗 [צפה באתר רמ\"י]({RMI_SITE_URL}/{selected_tender_id})")
        else:
            st.error(f"לא ניתן לטעון פרטים למכרז {selected_tender_id}")


# ============================================================================
# WATCHLIST (expander)
# ============================================================================

with st.expander("🔔 רשימת מעקב", expanded=False):
    user_email = get_user_email()
    if not user_email:
        st.warning("לא זוהה משתמש. הגדר DEV_USER_EMAIL בקובץ .env.")
    else:
        st.caption(f"משתמש: {user_email}")
        watch_db = UserDB()
        if not watch_db.available:
            st.warning("Supabase לא מוגדר — רשימת המעקב לא תישמר.")

        _watch_labels: dict[int, str] = {}
        for _, _r in df[["tender_id", "tender_name", "city"]].iterrows():
            _name = str(_r["tender_name"])[:50] if pd.notna(_r["tender_name"]) else ""
            _city = str(_r["city"])[:20] if pd.notna(_r["city"]) else ""
            _watch_labels[int(_r["tender_id"])] = f"{_name} — {_city}" if _city else _name

        add_col, btn_col = st.columns([3, 1])
        with add_col:
            watch_tender_id = st.selectbox(
                "בחר מכרז להוספה", options=list(_watch_labels.keys()), index=None,
                format_func=lambda tid: _watch_labels[tid],
                placeholder="הקלד שם מכרז או עיר...", key="watch_tender_input",
            )
        with btn_col:
            st.markdown("<br>", unsafe_allow_html=True)
            add_clicked = st.button("➕ הוסף למעקב", key="btn_add_watch")

        if add_clicked and watch_tender_id is not None:
            added = watch_db.add_to_watchlist(user_email, int(watch_tender_id))
            if added:
                st.success("מכרז נוסף! תקבל/י התראה במייל כשיתווספו מסמכים.")
                st.rerun()
            else:
                st.info("מכרז כבר ברשימת המעקב.")

        watchlist_rows = watch_db.get_watchlist_rows(user_email)
        if watchlist_rows:
            st.markdown(f"##### מכרזים במעקב ({len(watchlist_rows)})")
            _tender_lookup = df.set_index("tender_id").to_dict("index") if not df.empty else {}
            for row in watchlist_rows:
                tid = int(row["tender_id"])
                t = _tender_lookup.get(tid, {})
                w_cols = st.columns([2, 2, 2, 2, 1, 1])
                with w_cols[0]:
                    st.write(str(t.get("tender_name", tid))[:50])
                with w_cols[1]:
                    st.write(str(t.get("city", "")))
                with w_cols[2]:
                    st.write(str(t.get("region", "")))
                with w_cols[3]:
                    dl = t.get("deadline", "")
                    if dl and pd.notna(dl):
                        dt = pd.to_datetime(dl, errors="coerce")
                        st.write(dt.strftime("%d/%m/%Y") if pd.notna(dt) else "")
                    else:
                        st.write("")
                with w_cols[4]:
                    st.write(str(t.get("status", "")))
                with w_cols[5]:
                    if st.button("🗑️", key=f"rm_watch_{row['id']}"):
                        watch_db.remove_from_watchlist(user_email, tid)
                        st.rerun()
        else:
            st.info("רשימת המעקב ריקה.")


# ============================================================================
# TEAM REVIEW STATUS (expander)
# ============================================================================

with st.expander("📋 מכרזים נבחרים — סטטוס סקירה", expanded=False):
    _review_email = get_user_email()
    _review_db = UserDB()
    _team_ids = _review_db.get_watchlist_ids(TEAM_EMAIL)
    _team_df = df[df["tender_id"].astype(int).isin(_team_ids)].copy() if _team_ids else pd.DataFrame()

    _REVIEW_EMOJI: dict[str, str] = {
        "לא נסקר": "⬜", "סקירה ראשונית": "🔵",
        "בדיקה מעמיקה": "🟣", "הוצג בפורום": "🟠", "אושר בפורום": "🟢",
    }

    if len(_team_df) > 0:
        _rev_tbl = _team_df[["tender_name", "city", "tender_type", "units"]].copy()
        _rev_ids = _team_df["tender_id"].astype(int).tolist()
        _rev_map = _review_db.get_review_statuses_for_tenders(_rev_ids)
        _rev_tbl["review"] = [
            _REVIEW_EMOJI.get(_rev_map.get(int(tid), {}).get("status", "לא נסקר"), "⬜")
            + " " + _rev_map.get(int(tid), {}).get("status", "לא נסקר")
            for tid in _team_df["tender_id"]
        ]
        st.dataframe(
            _rev_tbl, hide_index=True, use_container_width=True,
            column_config={
                "tender_name": st.column_config.TextColumn("מכרז", width="medium"),
                "city": st.column_config.TextColumn("עיר", width="small"),
                "tender_type": st.column_config.TextColumn("סוג", width="small"),
                "units": st.column_config.NumberColumn('יח"ד', format="%d", width="small"),
                "review": st.column_config.TextColumn("סטטוס סקירה", width="medium"),
            },
        )
        if not _review_email:
            st.info("יש להזדהות כדי לעדכן סטטוס סקירה.")
        else:
            _rev_labels: dict[int, str] = {}
            for _, _r in _team_df.iterrows():
                _rev_labels[int(_r["tender_id"])] = f"{str(_r.get('tender_name', ''))[:30]} — {str(_r.get('city', ''))[:15]}"
            _rc1, _rc2 = st.columns([2, 2])
            with _rc1:
                _rev_tid = st.selectbox("מכרז", options=list(_rev_labels.keys()),
                                        format_func=lambda tid: _rev_labels[tid], key="dash_review_tender_select")
            with _rc2:
                _cur_status = _rev_map.get(_rev_tid, {}).get("status", REVIEW_STAGES[0])
                _cur_idx = REVIEW_STAGES.index(_cur_status) if _cur_status in REVIEW_STAGES else 0
                _new_status = st.selectbox("סטטוס חדש", options=REVIEW_STAGES, index=_cur_idx, key="dash_review_status_select")
            _rev_notes = st.text_input("הערות (אופציונלי)", key="dash_review_notes", placeholder="...")
            if st.button("💾 עדכן סטטוס", key="dash_btn_update_review"):
                _prev = _review_db.set_review_status(tender_id=_rev_tid, status=_new_status, updated_by=_review_email, notes=_rev_notes or None)
                st.success(f"מכרז {_rev_labels.get(_rev_tid, _rev_tid)}: {_prev or 'חדש'} → {_new_status}")
                st.rerun()
    else:
        st.info("אין מכרזים נבחרים. הוסף מכרזים דרך התפריט הצדדי ←")


# ============================================================================
# ANALYTICS (expander)
# ============================================================================

with st.expander("📊 ניתוח מפורט", expanded=False):
    chart_col1, chart_col2 = st.columns(2)
    with chart_col1:
        st.markdown("**📍 מכרזים לפי עיר**")
        city_counts = active_df["city"].value_counts().head(10)
        if len(city_counts) > 0:
            fig_city = px.bar(x=city_counts.values, y=city_counts.index, orientation="h",
                              labels={"x": "מספר מכרזים", "y": "עיר"},
                              color=city_counts.values, color_continuous_scale=GOLD_SCALE)
            fig_city.update_layout(showlegend=False, height=260, margin=dict(t=10, b=30, l=10, r=10), font=PLOTLY_FONT, **PLOTLY_BG)
            st.plotly_chart(fig_city, use_container_width=True)
    with chart_col2:
        st.markdown("**🏷️ מכרזים לפי סוג**")
        type_counts = active_df["tender_type"].value_counts()
        if len(type_counts) > 0:
            fig_type = px.pie(values=type_counts.values, names=type_counts.index, hole=0.4, color_discrete_sequence=CHART_COLORS)
            fig_type.update_layout(height=260, margin=dict(t=10, b=30, l=10, r=10), font=PLOTLY_FONT, **PLOTLY_BG)
            st.plotly_chart(fig_type, use_container_width=True)

    chart_col3, chart_col4 = st.columns(2)
    with chart_col3:
        st.markdown("**📈 מכרזים לאורך זמן**")
        timeline_df = active_df.copy()
        if len(timeline_df) > 0 and timeline_df["publish_date"].notna().any():
            timeline_df["month"] = timeline_df["publish_date"].dt.to_period("M").astype(str)
            monthly = timeline_df.groupby("month").size().reset_index(name="count")
            fig_tl = px.line(monthly, x="month", y="count", markers=True,
                             labels={"month": "חודש", "count": "מספר"}, color_discrete_sequence=["#1B6B3A"])
            fig_tl.update_layout(height=260, margin=dict(t=10, b=30, l=10, r=10), font=PLOTLY_FONT, **PLOTLY_BG)
            st.plotly_chart(fig_tl, use_container_width=True)
    with chart_col4:
        st.markdown('**🏠 יח"ד לפי סוג**')
        units_by_type = active_df.groupby("tender_type")["units"].sum().reset_index()
        units_by_type = units_by_type[units_by_type["units"] > 0]
        if not units_by_type.empty:
            fig_u = px.bar(units_by_type, x="tender_type", y="units",
                           labels={"units": 'סה"כ יח"ד', "tender_type": "סוג"}, color_discrete_sequence=["#D4A017"])
            fig_u.update_layout(height=260, margin=dict(t=10, b=30, l=10, r=10), font=PLOTLY_FONT, **PLOTLY_BG)
            st.plotly_chart(fig_u, use_container_width=True)


# ============================================================================
# DEBUG (expander)
# ============================================================================

with st.expander("🔧 ניהול ודיבוג", expanded=False):
    st.code(
        f"רשומות שנטענו: {len(df_all):,}\n"
        f"לאחר סינון סוג: {len(df):,}\n"
        f"פעילים: {len(active_df):,}\n"
        f"סוגי מכרז: {', '.join(df['tender_type'].unique().tolist())}",
    )
    st.code(
        f"List: {LAND_AUTHORITY_API} (POST)\n"
        f"Detail: {TENDER_DETAIL_API}?michrazID=\n"
        f"Docs: {DOCUMENT_DOWNLOAD_API}",
    )
