"""
Tender Explorer page — filterable data table with export and detail viewer.

Extracted from the main dashboard into its own page for cleaner navigation.
Allows filtering by city, region, purpose, and status with CSV export.
"""

from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st

from config import (
    CLOSING_SOON_DAYS,
    DATA_DIR,
    DOCUMENT_DOWNLOAD_API,
    NON_ACTIVE_STATUSES,
    RELEVANT_TENDER_TYPES,
    RMI_SITE_URL,
    TENDER_DETAIL_API,
)
from dashboard_utils import (
    get_user_email,
    load_building_rights_data,
    load_data,
    load_tender_details,
    render_email_input,
)
from data_client import LandTendersClient, build_document_url
from analytics_engine import score_all_tenders

# ── Constants ────────────────────────────────────────────────────────────────
RELEVANT_PURPOSES = {"בנייה רוויה", "בנייה נמוכה/צמודת קרקע", "דיור מוגן (בית אבות)", "אחר"}

today = datetime.now()

# ── Load & pre-filter data ───────────────────────────────────────────────────
render_email_input()

df_all = load_data(data_source="latest_file")
df = df_all[df_all["tender_type_code"].isin(RELEVANT_TENDER_TYPES)].copy()
if "purpose" in df.columns:
    df = df[df["purpose"].isin(RELEVANT_PURPOSES)].copy()
df = score_all_tenders(df)
active_df = df[~df["status"].isin(NON_ACTIVE_STATUSES)].copy()


# ============================================================================
# HEADER
# ============================================================================

st.markdown(
    '<div style="display:flex;align-items:center;gap:12px;padding:8px 0 4px 0;">'
    '<span style="font-size:1.3rem;font-weight:700;color:#1E293B;">'
    "סייר מכרזים"
    "</span>"
    f'<span style="font-size:0.8rem;color:#64748B;margin-right:auto;">{today.strftime("%d/%m/%Y")}</span>'
    "</div>",
    unsafe_allow_html=True,
)


# ============================================================================
# DATA EXPLORER — 4 inline filters
# ============================================================================

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

# Fixed display columns
EXP_COLS = ["total_score", "tender_name", "city", "region", "tender_type", "purpose", "units", "deadline", "status", "published_booklet"]
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
        exp_display,
        hide_index=True,
        use_container_width=True,
        column_config={
            "total_score": st.column_config.ProgressColumn("ציון", min_value=0, max_value=100, format="%.0f"),
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
        label="הורד CSV",
        data=csv,
        file_name=f"land_tenders_{today.strftime('%Y%m%d')}.csv",
        mime="text/csv",
    )


# ============================================================================
# TENDER DETAIL VIEWER (expander)
# ============================================================================

with st.expander("צפייה בפרטי מכרז", expanded=False):
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
            "בחר מכרז",
            options=detail_candidates["tender_id"].tolist(),
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
                    f"<strong>ייעוד:</strong> {purpose_val}"
                    f"</div>",
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
                    f"<strong>תאריך ועדה:</strong> {committee_str}"
                    f"</div>",
                    unsafe_allow_html=True,
                )

            # ── Bids ─────────────────────────────────────────────────────
            st.markdown("---")
            st.markdown("### הצעות ומציעים")
            plots = details.get("Tik", [])
            if plots:
                for plot_idx, plot in enumerate(plots, 1):
                    st.markdown(f"#### מגרש {plot_idx}: {plot.get('TikID', 'N/A')}")
                    winner_name = (plot.get("ShemZoche") or "").strip()
                    winner_amount = plot.get("SchumZchiya", 0)
                    if winner_name:
                        st.success(f"**זוכה:** {winner_name}")
                        st.markdown(
                            f'<div class="detail-field">'
                            f"<strong>סכום זכייה:</strong> ₪{winner_amount:,.2f} | "
                            f"<strong>שטח:</strong> {plot.get('Shetach', 0):,} מ\"ר | "
                            f"<strong>מחיר סף:</strong> ₪{plot.get('MechirSaf', 0):,.2f}"
                            f"</div>",
                            unsafe_allow_html=True,
                        )
                    bidders = plot.get("mpHatzaaotMitcham", [])
                    if bidders:
                        st.info(f"**סה\"כ הצעות:** {len(bidders)}")
                        bidder_df = pd.DataFrame(bidders).sort_values("HatzaaSum", ascending=False)
                        disp_bid = bidder_df.copy()
                        disp_bid["HatzaaSum"] = disp_bid["HatzaaSum"].apply(
                            lambda x: f"₪{x:,.2f}" if pd.notna(x) else "N/A"
                        )
                        disp_bid = disp_bid.rename(columns={
                            "HatzaaID": "מס' הצעה", "HatzaaSum": "סכום", "HatzaaDescription": "תיאור"
                        })
                        st.dataframe(disp_bid, use_container_width=True, hide_index=True)
                    else:
                        st.info("אין הצעות למגרש זה")
                    if plot_idx < len(plots):
                        st.markdown("---")
            else:
                st.info("אין מידע על הצעות למכרז זה")

            # ── Documents ────────────────────────────────────────────────
            st.markdown("---")
            st.markdown("### מסמכים")
            full_doc = details.get("MichrazFullDocument")
            if full_doc and full_doc.get("RowID") is not None:
                doc_name = full_doc.get("DocName", "מסמך פרסום מלא.pdf")
                doc_url = build_document_url(full_doc)
                st.markdown(f"[**הורד: {doc_name}**]({doc_url})")

            docs = details.get("MichrazDocList", [])
            if docs:
                st.markdown(f"#### מסמכים נוספים ({len(docs)})")
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

            # ── Building Rights ────────────────────────────────────────
            st.markdown("---")
            st.markdown("### זכויות בנייה")

            br_data = load_building_rights_data(selected_tender_id)
            br_status = br_data["extraction_status"]

            if br_status == "none":
                if st.button("נתח זכויות בנייה", key=f"br_btn_{selected_tender_id}"):
                    with st.spinner("מוריד ומנתח חוברת מכרז..."):
                        from brochure_analyzer import (
                            download_and_analyze_brochure,
                            trigger_extraction_workflow,
                        )
                        from db import TenderDB

                        br_client = LandTendersClient(data_dir=str(DATA_DIR))
                        br_result = download_and_analyze_brochure(
                            selected_tender_id, br_client, details,
                        )

                        if br_result["success"]:
                            db = TenderDB()
                            lots_data = {
                                "plots": br_result["lots"],
                                "purpose": br_result["purpose"],
                            }

                            new_status = "queued"
                            if br_result["plan_number"]:
                                existing = db.load_building_rights(br_result["plan_number"])
                                if existing:
                                    new_status = "complete"

                            db.update_brochure_data(
                                selected_tender_id,
                                br_result["plan_number"],
                                lots_data,
                                br_result["summary"],
                                extraction_status=new_status,
                            )

                            if new_status == "queued" and br_result["plan_number"]:
                                triggered = trigger_extraction_workflow(selected_tender_id)
                                if triggered:
                                    st.success("ניתוח חוברת הושלם. זכויות בנייה יעובדו תוך 5-10 דקות.")
                                else:
                                    st.warning("ניתוח חוברת הושלם, אך לא הצלחנו להפעיל את עיבוד זכויות הבנייה.")
                            elif new_status == "complete":
                                st.success("ניתוח הושלם — זכויות בנייה כבר קיימות!")
                            else:
                                st.info("ניתוח חוברת הושלם.")

                            load_building_rights_data.clear()
                            st.rerun()
                        else:
                            st.error(f"ניתוח נכשל: {'; '.join(br_result['errors'])}")
                else:
                    st.caption("לחץ לניתוח חוברת המכרז וחילוץ זכויות בנייה")

            elif br_status in ("brochure_extracted", "queued"):
                st.info("ממתין לעיבוד זכויות בנייה (יושלם תוך דקות)")

                if br_data["plan_number"]:
                    st.markdown(f"**תב\"ע:** {br_data['plan_number']}")

                if br_data["lots_data"] and isinstance(br_data["lots_data"], dict):
                    lots_plots = br_data["lots_data"].get("plots", [])
                    if lots_plots:
                        st.markdown("**מגרשים:**")
                        lots_rows = []
                        for p in lots_plots:
                            lots_rows.append({
                                "גוש": p.get("gush", "-"),
                                "חלקה": p.get("helka", "-"),
                                "מגרש": p.get("migrash", "-"),
                                "שטח": p.get("area", "-"),
                            })
                        st.dataframe(pd.DataFrame(lots_rows), use_container_width=True, hide_index=True)

                if br_data["brochure_summary"]:
                    with st.expander("סיכום חוברת מכרז", expanded=False):
                        st.text(br_data["brochure_summary"])

                if st.button("בדוק שוב", key=f"br_check_{selected_tender_id}"):
                    load_building_rights_data.clear()
                    st.rerun()

            elif br_status == "complete":
                if br_data["plan_number"]:
                    st.markdown(f"**תב\"ע:** {br_data['plan_number']}")

                rights = br_data["building_rights"]
                if rights:
                    display_rows = []
                    for row in rights:
                        display_rows.append({
                            "יעוד": row.get("designation", "-"),
                            "שימוש": row.get("use_type", "-"),
                            "תאי שטח": row.get("area_condition", "-"),
                            'שטח מגרש (מ"ר)': row.get("plot_size_absolute", "-"),
                            "שטח בנייה עיקרי": row.get("building_area_above", "-"),
                            "שטח בנייה סה\"כ": row.get("building_area_total", "-"),
                            "תכסית %": row.get("coverage_pct", "-"),
                            'יח"ד': row.get("housing_units", "-"),
                            "קומות": row.get("floors_above", "-"),
                            'גובה (מ\')': row.get("building_height", "-"),
                            "קו בניין קדמי": row.get("setback_front", "-"),
                            "קו בניין אחורי": row.get("setback_rear", "-"),
                            "קו בניין צידי": row.get("setback_side", "-"),
                        })

                    rights_df = pd.DataFrame(display_rows)
                    st.dataframe(rights_df, use_container_width=True, hide_index=True)
                    st.caption(f"סה\"כ {len(rights)} שורות מתוך טבלת זכויות בנייה")
                else:
                    st.info("לא נמצאו זכויות בנייה עבור התב\"ע")

                if br_data["lots_data"] and isinstance(br_data["lots_data"], dict):
                    lots_plots = br_data["lots_data"].get("plots", [])
                    if lots_plots:
                        with st.expander("מגרשים מחוברת המכרז", expanded=False):
                            lots_rows = []
                            for p in lots_plots:
                                lots_rows.append({
                                    "גוש": p.get("gush", "-"),
                                    "חלקה": p.get("helka", "-"),
                                    "מגרש": p.get("migrash", "-"),
                                    "שטח": p.get("area", "-"),
                                })
                            st.dataframe(pd.DataFrame(lots_rows), use_container_width=True, hide_index=True)

                if br_data["brochure_summary"]:
                    with st.expander("סיכום חוברת מכרז", expanded=False):
                        st.text(br_data["brochure_summary"])

            elif br_status == "failed":
                error_msg = br_data.get("extraction_error") or "שגיאה לא ידועה"
                st.error(f"חילוץ זכויות בנייה נכשל: {error_msg}")

                if br_data["brochure_summary"]:
                    with st.expander("סיכום חוברת מכרז", expanded=False):
                        st.text(br_data["brochure_summary"])

                if st.button("נסה שוב", key=f"br_retry_{selected_tender_id}"):
                    from db import TenderDB
                    TenderDB().set_extraction_status(selected_tender_id, "none")
                    load_building_rights_data.clear()
                    st.rerun()

            # ── Lot Data (from tender_lots table) ─────────────────────
            st.markdown("---")
            st.markdown("### נתוני מתחמים")

            try:
                from db import TenderDB as _LotDB

                _lot_db = _LotDB()
                _tender_record = _lot_db.get_tender_by_id(selected_tender_id)
                _lots = _lot_db.get_lots(selected_tender_id)

                # ── Bid limit badge ───────────────────────────────────
                _max_lots = (
                    _tender_record.get("max_lots_per_bidder")
                    if _tender_record
                    else None
                )
                if _max_lots is not None and _max_lots > 0:
                    st.markdown(
                        '<div style="display:inline-block;padding:4px 14px;'
                        "border-radius:16px;font-size:0.85rem;font-weight:600;"
                        'background:#FFF7ED;color:#C2410C;border:1px solid #FDBA74;">'
                        f"\U0001f3af הגבלת הגשה: עד {_max_lots} מתחמים"
                        "</div>",
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(
                        '<div style="display:inline-block;padding:4px 14px;'
                        "border-radius:16px;font-size:0.85rem;font-weight:600;"
                        'background:#F0FDF4;color:#166534;border:1px solid #86EFAC;">'
                        "\U0001f3af ללא הגבלה"
                        "</div>",
                        unsafe_allow_html=True,
                    )

                # ── Lots table ────────────────────────────────────────
                if _lots:
                    _lots_df = pd.DataFrame(_lots)

                    _COL_MAP = {
                        "lot_number": "מתחם",
                        "plot_numbers": "מגרש",
                        "area_sqm": 'שטח מ"ר',
                        "units_target_price": 'יח"ד מטרה',
                        "units_free_market": 'יח"ד שוק חופשי',
                        "min_price": "מחיר מינימום \u20aa",
                        "guarantee_amount": "ערבות \u20aa",
                        "zoning_plan": 'תב"ע',
                    }
                    _display_cols = [
                        c for c in _COL_MAP if c in _lots_df.columns
                    ]
                    _lots_display = _lots_df[_display_cols].rename(
                        columns=_COL_MAP,
                    )

                    # Numeric formatting config
                    _col_config = {}
                    _num_cols_fmt_d = ['שטח מ"ר', 'יח"ד מטרה', 'יח"ד שוק חופשי']
                    _num_cols_fmt_money = ["מחיר מינימום \u20aa", "ערבות \u20aa"]
                    for _nc in _num_cols_fmt_d:
                        if _nc in _lots_display.columns:
                            _col_config[_nc] = st.column_config.NumberColumn(
                                _nc, format="%d",
                            )
                    for _mc in _num_cols_fmt_money:
                        if _mc in _lots_display.columns:
                            _col_config[_mc] = st.column_config.NumberColumn(
                                _mc, format="%,.0f",
                            )
                    for _tc in ["מתחם", "מגרש", 'תב"ע']:
                        if _tc in _lots_display.columns:
                            _col_config[_tc] = st.column_config.TextColumn(_tc)

                    st.dataframe(
                        _lots_display,
                        column_config=_col_config,
                        use_container_width=True,
                        hide_index=True,
                        height=min(35 * len(_lots_display) + 38, 400),
                    )

                    # ── Summary metrics ───────────────────────────────
                    _total_lots = len(_lots_display)
                    _total_target = (
                        pd.to_numeric(
                            _lots_df.get("units_target_price"), errors="coerce",
                        ).sum()
                        if "units_target_price" in _lots_df.columns
                        else 0
                    )
                    _total_free = (
                        pd.to_numeric(
                            _lots_df.get("units_free_market"), errors="coerce",
                        ).sum()
                        if "units_free_market" in _lots_df.columns
                        else 0
                    )

                    _sm1, _sm2, _sm3 = st.columns(3)
                    with _sm1:
                        st.metric("סה\"כ מתחמים", f"{_total_lots:,}")
                    with _sm2:
                        st.metric('יח"ד מטרה', f"{_total_target:,.0f}")
                    with _sm3:
                        st.metric('יח"ד שוק חופשי', f"{_total_free:,.0f}")
                else:
                    st.info("אין נתוני מתחמים למכרז זה")

                # ── Extraction status indicator ───────────────────────
                _lot_status = (
                    _tender_record.get("lot_extraction_status")
                    if _tender_record
                    else None
                )
                _lot_date = (
                    _tender_record.get("lot_extraction_date")
                    if _tender_record
                    else None
                )

                if _lot_status == "extracted":
                    _date_str = ""
                    if _lot_date:
                        _dt = pd.to_datetime(_lot_date, errors="coerce")
                        if pd.notna(_dt):
                            _date_str = f" ({_dt.strftime('%d/%m/%Y %H:%M')})"
                    st.markdown(
                        f'<span style="color:#166534;font-size:0.8rem;">'
                        f"\u2705 מתחמים חולצו בהצלחה{_date_str}"
                        f"</span>",
                        unsafe_allow_html=True,
                    )
                elif _lot_status == "pending":
                    st.markdown(
                        '<span style="color:#92400E;font-size:0.8rem;">'
                        "\u23f3 חילוץ מתחמים בהמתנה"
                        "</span>",
                        unsafe_allow_html=True,
                    )
                elif _lot_status == "failed":
                    st.markdown(
                        '<span style="color:#991B1B;font-size:0.8rem;">'
                        "\u274c חילוץ מתחמים נכשל"
                        "</span>",
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(
                        '<span style="color:#94A3B8;font-size:0.8rem;">'
                        "\u2796 נתוני מתחמים לא זמינים"
                        "</span>",
                        unsafe_allow_html=True,
                    )

            except Exception as _lot_exc:
                import logging as _lot_logging

                _lot_logging.getLogger(__name__).error(
                    "Failed to load lot data for tender %d: %s",
                    selected_tender_id,
                    _lot_exc,
                )
                st.caption("לא ניתן לטעון נתוני מתחמים")

            st.markdown("---")
            st.markdown(f"[צפה באתר רמ\"י]({RMI_SITE_URL}/{selected_tender_id})")
        else:
            st.error(f"לא ניתן לטעון פרטים למכרז {selected_tender_id}")
