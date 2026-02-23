"""
Market analytics page — ניתוח שוק.

Comprehensive market intelligence dashboard with trends, competitive analysis,
price analytics, and a composite scoring system. All analytics are computed
via analytics_engine.py functions, and data is loaded via dashboard_utils and
db.py.

Sections:
    1. Header + Sidebar Filters (date range, region)
    2. Market Overview (KPIs + supply pipeline)
    3. Trends (regional volume, momentum, monthly distribution, moving averages)
    4. Competitive Intelligence (lifecycle, deadline overlap, saturation, docs)
    5. Price Analytics (price trends, taba summary, price premium)
    6. Scoring (top tenders, distribution, radar deep-dive)

Branded for MEGIDO BY AURA (מגידו י.ק.).
"""

import html
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from analytics_engine import (
    deadline_overlap_analysis,
    document_intelligence,
    get_score_distribution,
    get_top_tenders,
    monthly_publication_distribution,
    price_premium_analysis,
    price_trends_by_region,
    region_saturation_index,
    regional_momentum,
    regional_tender_volume,
    score_all_tenders,
    supply_pipeline,
    taba_analysis_summary,
    tender_lifecycle_analysis,
    volume_moving_averages,
)
from config import CACHE_TTL, NON_ACTIVE_STATUSES, RELEVANT_TENDER_TYPES
from dashboard_utils import load_data

# ── Chart constants (matching dashboard.py MEGIDO design system) ─────────────
MEGIDO_CHART_COLORS = ["#2563EB", "#60A5FA", "#1E3A5F", "#10B981", "#F59E0B", "#8B5CF6"]
MEGIDO_GOLD_SCALE = [[0, "#DBEAFE"], [1, "#2563EB"]]
PLOTLY_FONT = dict(family="Inter, Heebo, sans-serif", size=11, color="#1E293B")
PLOTLY_BG = dict(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
PLOTLY_GRID = dict(gridcolor="rgba(226,232,240,0.5)", zerolinecolor="rgba(226,232,240,0.7)")


# ============================================================================
# DATA LOADING (cached)
# ============================================================================

@st.cache_data(ttl=CACHE_TTL)
def _load_prices() -> pd.DataFrame:
    """Load tender prices from Supabase (cached)."""
    try:
        from db import TenderDB
        return TenderDB().load_tender_prices()
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=CACHE_TTL)
def _load_taba() -> pd.DataFrame:
    """Load taba analytics from Supabase (cached)."""
    try:
        from db import TenderDB
        return TenderDB().load_taba_analytics()
    except Exception:
        return pd.DataFrame()


# ── Load all data ────────────────────────────────────────────────────────────
# Compute `today` fresh on each render (not at module-import time).
today = datetime.now()

df_all = load_data(data_source="latest_file")
df = df_all[df_all["tender_type_code"].isin(RELEVANT_TENDER_TYPES)].copy()
prices_df = _load_prices()
taba_df = _load_taba()


# ============================================================================
# SIDEBAR — brand + filters
# ============================================================================

with st.sidebar:
    logo_path = Path(__file__).parent.parent / "assets" / "logo megido.jpg"
    if logo_path.exists():
        st.image(str(logo_path), width=140)

    st.markdown("""
    <div class="sidebar-header">
        <h2>MEGIDO</h2>
        <p>מגידו י.ק. | ניתוח שוק</p>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("---")

    # ── Date range filter ─────────────────────────────────────────────────
    st.markdown("#### סינון תאריך")
    min_date = pd.to_datetime(df["publish_date"], errors="coerce").min()
    if pd.isna(min_date):
        min_date = today - timedelta(days=365)
    else:
        min_date = min_date.to_pydatetime()

    date_range = st.date_input(
        "טווח תאריכים",
        value=(min_date.date(), today.date()),
        min_value=min_date.date(),
        max_value=today.date(),
        key="analytics_date_range",
    )

    # ── Region multi-select ───────────────────────────────────────────────
    st.markdown("#### סינון מחוז")
    all_regions = sorted(df["region"].dropna().unique().tolist()) if "region" in df.columns else []
    selected_regions = st.multiselect(
        "מחוזות",
        options=all_regions,
        default=[],
        key="analytics_regions",
        placeholder="כל המחוזות",
    )

    st.markdown("---")
    st.caption(f"עדכון: {today.strftime('%d/%m/%Y %H:%M')}")
    st.caption(f"רשומות: {len(df):,} (מ-{len(df_all):,})")


# ── Apply filters to working DataFrame ────────────────────────────────────
filtered_df = df.copy()

if isinstance(date_range, tuple) and len(date_range) == 2:
    start_date, end_date = date_range
    pub_dt = pd.to_datetime(filtered_df["publish_date"], errors="coerce")
    filtered_df = filtered_df[
        (pub_dt >= pd.Timestamp(start_date)) & (pub_dt <= pd.Timestamp(end_date))
    ]

if selected_regions:
    filtered_df = filtered_df[filtered_df["region"].isin(selected_regions)]


# ============================================================================
# HEADER
# ============================================================================

st.markdown(
    '<div style="display:flex;align-items:center;gap:12px;padding:8px 0 4px 0;">'
    '<span style="font-size:1.4rem;font-weight:700;color:#1E293B;">'
    "MEGIDO | ניתוח שוק"
    "</span>"
    '<span style="font-size:0.85rem;color:#64748B;margin-right:auto;">'
    "מגמות, ניקוד ומודיעין תחרותי"
    "</span>"
    "</div>",
    unsafe_allow_html=True,
)
st.markdown("---")


# ============================================================================
# SECTION 1: MARKET OVERVIEW (KPIs + Supply Pipeline)
# ============================================================================

st.markdown(
    '<div class="section-header">סקירת שוק</div>',
    unsafe_allow_html=True,
)

# ── KPI row ───────────────────────────────────────────────────────────────
scored_df = score_all_tenders(filtered_df)
avg_score = scored_df["total_score"].mean() if not scored_df.empty else 0

k1, k2, k3, k4 = st.columns(4)
with k1:
    st.metric("סה\"כ מכרזים", f"{len(filtered_df):,}")
with k2:
    st.metric("ציון ממוצע", f"{avg_score:.1f}")
with k3:
    region_count = filtered_df["region"].nunique() if "region" in filtered_df.columns else 0
    st.metric("מחוזות פעילים", f"{region_count}")
with k4:
    total_units = int(filtered_df["units"].sum()) if "units" in filtered_df.columns else 0
    st.metric("סה\"כ יח\"ד", f"{total_units:,}")

# ── Supply pipeline chart ─────────────────────────────────────────────────
pipeline_data = supply_pipeline(filtered_df)
if not pipeline_data.empty:
    fig_pipeline = go.Figure()
    fig_pipeline.add_trace(go.Scatter(
        x=pipeline_data["date"],
        y=pipeline_data["new_published"],
        name="מכרזים חדשים",
        fill="tozeroy",
        line=dict(color="#2563EB", width=2),
        fillcolor="rgba(37,99,235,0.3)",
    ))
    fig_pipeline.add_trace(go.Scatter(
        x=pipeline_data["date"],
        y=pipeline_data["closing"],
        name="נסגרים",
        fill="tozeroy",
        line=dict(color="#3B82F6", width=2),
        fillcolor="rgba(59,130,246,0.2)",
    ))
    fig_pipeline.add_trace(go.Scatter(
        x=pipeline_data["date"],
        y=pipeline_data["active_net"],
        name="שינוי נטו",
        line=dict(color="#EF4444", width=2, dash="dot"),
    ))
    fig_pipeline.update_layout(
        title="צינור היצע מכרזים",
        height=320,
        margin=dict(t=40, b=30, l=10, r=10),
        font=PLOTLY_FONT,
        **PLOTLY_BG,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        xaxis=dict(**PLOTLY_GRID),
        yaxis=dict(**PLOTLY_GRID),
    )
    st.plotly_chart(fig_pipeline, use_container_width=True, key="supply_pipeline")
else:
    st.info("אין מספיק נתונים לתצוגת צינור היצע")

st.markdown("---")


# ============================================================================
# SECTION 2: TRENDS
# ============================================================================

st.markdown(
    '<div class="section-header">מגמות</div>',
    unsafe_allow_html=True,
)

trend_tab1, trend_tab2, trend_tab3, trend_tab4 = st.tabs([
    "נפח אזורי", "מומנטום אזורי", "התפלגות חודשית", "ממוצעים נעים",
])

# ── Tab 1: Regional tender volume ─────────────────────────────────────────
with trend_tab1:
    vol_data = regional_tender_volume(filtered_df)
    if not vol_data.empty:
        fig_vol = px.line(
            vol_data,
            x="date",
            y="count",
            color="region",
            markers=True,
            labels={"date": "תאריך", "count": "מספר מכרזים", "region": "מחוז"},
            color_discrete_sequence=MEGIDO_CHART_COLORS,
        )
        fig_vol.update_layout(
            title="נפח מכרזים לפי מחוז לאורך זמן",
            height=350,
            margin=dict(t=40, b=30, l=10, r=10),
            font=PLOTLY_FONT,
            **PLOTLY_BG,
            xaxis=dict(**PLOTLY_GRID),
            yaxis=dict(**PLOTLY_GRID),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )
        st.plotly_chart(fig_vol, use_container_width=True, key="regional_volume")
    else:
        st.info("אין נתונים זמינים לנפח אזורי")

# ── Tab 2: Regional momentum ─────────────────────────────────────────────
with trend_tab2:
    momentum_data = regional_momentum(filtered_df)
    if not momentum_data.empty:
        # Add direction arrows
        direction_map = {"up": "↑ עולה", "down": "↓ יורד", "stable": "→ יציב"}
        color_map = {"up": "#10B981", "down": "#EF4444", "stable": "#64748B"}

        display_mom = momentum_data.copy()
        display_mom["כיוון"] = display_mom["direction"].map(direction_map)
        display_mom["צבע"] = display_mom["direction"].map(color_map)

        # Build HTML table for colored display
        rows_html = ""
        for _, row in display_mom.iterrows():
            color = row["צבע"]
            region_safe = html.escape(str(row["region"]))
            rows_html += (
                f"<tr>"
                f"<td style='padding:6px 12px;border-bottom:1px solid #E2E8F0;'>{region_safe}</td>"
                f"<td style='padding:6px 12px;border-bottom:1px solid #E2E8F0;text-align:center;'>{row['recent_count']}</td>"
                f"<td style='padding:6px 12px;border-bottom:1px solid #E2E8F0;text-align:center;'>{row['previous_count']}</td>"
                f"<td style='padding:6px 12px;border-bottom:1px solid #E2E8F0;text-align:center;'>{row['change_pct']:.1f}%</td>"
                f"<td style='padding:6px 12px;border-bottom:1px solid #E2E8F0;text-align:center;color:{color};font-weight:600;'>{row['כיוון']}</td>"
                f"</tr>"
            )

        st.markdown(
            f"""<table style="width:100%;border-collapse:collapse;background:#FFFFFF;border-radius:8px;overflow:hidden;border:1px solid #E2E8F0;">
            <thead><tr style="background:#F8FAFC;">
                <th style="padding:8px 12px;text-align:right;font-weight:600;border-bottom:2px solid #E2E8F0;">מחוז</th>
                <th style="padding:8px 12px;text-align:center;font-weight:600;border-bottom:2px solid #E2E8F0;">תקופה אחרונה</th>
                <th style="padding:8px 12px;text-align:center;font-weight:600;border-bottom:2px solid #E2E8F0;">תקופה קודמת</th>
                <th style="padding:8px 12px;text-align:center;font-weight:600;border-bottom:2px solid #E2E8F0;">שינוי %</th>
                <th style="padding:8px 12px;text-align:center;font-weight:600;border-bottom:2px solid #E2E8F0;">כיוון</th>
            </tr></thead>
            <tbody>{rows_html}</tbody>
            </table>""",
            unsafe_allow_html=True,
        )
    else:
        st.info("אין מספיק נתונים לניתוח מומנטום")

# ── Tab 3: Monthly publication distribution ───────────────────────────────
with trend_tab3:
    monthly_data = monthly_publication_distribution(filtered_df)
    if not monthly_data.empty:
        fig_monthly = px.bar(
            monthly_data,
            x="month_name_he",
            y="avg_count",
            labels={"month_name_he": "חודש", "avg_count": "ממוצע מכרזים"},
            color="avg_count",
            color_continuous_scale=MEGIDO_GOLD_SCALE,
        )
        fig_monthly.update_layout(
            title="התפלגות פרסום חודשית (ממוצע שנתי)",
            height=320,
            margin=dict(t=40, b=30, l=10, r=10),
            font=PLOTLY_FONT,
            **PLOTLY_BG,
            showlegend=False,
            xaxis=dict(**PLOTLY_GRID),
            yaxis=dict(**PLOTLY_GRID),
        )
        st.plotly_chart(fig_monthly, use_container_width=True, key="monthly_dist")
    else:
        st.info("אין נתונים להתפלגות חודשית")

# ── Tab 4: Volume moving averages ─────────────────────────────────────────
with trend_tab4:
    ma_data = volume_moving_averages(filtered_df)
    if not ma_data.empty:
        fig_ma = go.Figure()
        ma_colors = {"ma_30": "#2563EB", "ma_60": "#3B82F6", "ma_90": "#1E3A5F"}
        ma_names = {"ma_30": "30 יום", "ma_60": "60 יום", "ma_90": "90 יום"}
        for col in ["ma_30", "ma_60", "ma_90"]:
            if col in ma_data.columns:
                fig_ma.add_trace(go.Scatter(
                    x=ma_data["date"],
                    y=ma_data[col],
                    name=ma_names[col],
                    line=dict(color=ma_colors[col], width=2),
                ))
        fig_ma.update_layout(
            title="ממוצעים נעים — נפח פרסום מכרזים",
            height=320,
            margin=dict(t=40, b=30, l=10, r=10),
            font=PLOTLY_FONT,
            **PLOTLY_BG,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            xaxis=dict(**PLOTLY_GRID),
            yaxis=dict(**PLOTLY_GRID),
        )
        st.plotly_chart(fig_ma, use_container_width=True, key="volume_ma")
    else:
        st.info("אין נתונים לממוצעים נעים")

st.markdown("---")


# ============================================================================
# SECTION 3: COMPETITIVE INTELLIGENCE
# ============================================================================

st.markdown(
    '<div class="section-header">מודיעין תחרותי</div>',
    unsafe_allow_html=True,
)

ci_tab1, ci_tab2, ci_tab3, ci_tab4 = st.tabs([
    "מחזור חיים", "חפיפת מועדים", "רוויה אזורית", "מודיעין מסמכים",
])

# ── Tab 1: Tender lifecycle analysis ──────────────────────────────────────
with ci_tab1:
    lifecycle_data = tender_lifecycle_analysis(filtered_df)
    if not lifecycle_data.empty:
        st.dataframe(
            lifecycle_data.rename(columns={
                "region": "מחוז",
                "tender_type": "סוג מכרז",
                "avg_lifecycle_days": "ממוצע ימים",
                "median_lifecycle_days": "חציון ימים",
                "count": "מספר מכרזים",
            }),
            hide_index=True,
            use_container_width=True,
        )
        st.caption("ניתוח זמני מחזור חיים למכרזים שנסגרו — מפרסום ועד סגירה")
    else:
        st.info("אין מכרזים סגורים בטווח הנבחר לניתוח מחזור חיים")

# ── Tab 2: Deadline overlap analysis ──────────────────────────────────────
with ci_tab2:
    overlap_data = deadline_overlap_analysis(filtered_df)
    if not overlap_data.empty:
        # Color by competition level
        comp_colors = {"low": "#10B981", "medium": "#F59E0B", "high": "#EF4444"}
        comp_hebrew = {"low": "נמוכה", "medium": "בינונית", "high": "גבוהה"}

        display_overlap = overlap_data.copy()
        display_overlap["week_start"] = pd.to_datetime(display_overlap["week_start"]).dt.strftime("%d/%m/%Y")
        display_overlap["רמת תחרות"] = display_overlap["competition_level"].map(comp_hebrew)

        st.dataframe(
            display_overlap.rename(columns={
                "week_start": "תחילת שבוע",
                "tender_count": "מכרזים",
                "regions_involved": "מחוזות",
                "רמת תחרות": "רמת תחרות",
            })[["תחילת שבוע", "מכרזים", "מחוזות", "רמת תחרות"]],
            hide_index=True,
            use_container_width=True,
        )
        st.caption("שבועות עם חפיפת מועדי סגירה — רמת תחרות נמוכה (1-2), בינונית (3-5), גבוהה (6+)")
    else:
        st.info("אין נתוני מועדי סגירה לניתוח חפיפה")

# ── Tab 3: Region saturation index ────────────────────────────────────────
with ci_tab3:
    saturation_data = region_saturation_index(filtered_df)
    if not saturation_data.empty:
        trend_hebrew = {"saturating": "מתרווה", "opening": "נפתח", "stable": "יציב"}
        trend_colors = {"saturating": "#EF4444", "opening": "#10B981", "stable": "#64748B"}

        rows_html = ""
        for _, row in saturation_data.iterrows():
            score = row["saturation_score"]
            # Color the score badge
            if score >= 70:
                badge_color = "#EF4444"
            elif score >= 40:
                badge_color = "#F59E0B"
            else:
                badge_color = "#10B981"

            trend_label = trend_hebrew.get(row["trend"], row["trend"])
            trend_color = trend_colors.get(row["trend"], "#64748B")
            region_safe = html.escape(str(row["region"]))

            rows_html += (
                f"<tr>"
                f"<td style='padding:6px 12px;border-bottom:1px solid #E2E8F0;'>{region_safe}</td>"
                f"<td style='padding:6px 12px;border-bottom:1px solid #E2E8F0;text-align:center;'>{row['active_count']}</td>"
                f"<td style='padding:6px 12px;border-bottom:1px solid #E2E8F0;text-align:center;'>{row['closed_count']}</td>"
                f"<td style='padding:6px 12px;border-bottom:1px solid #E2E8F0;text-align:center;'>{row['total_units']:,}</td>"
                f"<td style='padding:6px 12px;border-bottom:1px solid #E2E8F0;text-align:center;'>"
                f"<span style='background:{badge_color};color:#fff;padding:2px 8px;border-radius:12px;font-size:0.85rem;font-weight:600;'>{score:.0f}</span></td>"
                f"<td style='padding:6px 12px;border-bottom:1px solid #E2E8F0;text-align:center;color:{trend_color};font-weight:600;'>{trend_label}</td>"
                f"</tr>"
            )

        st.markdown(
            f"""<table style="width:100%;border-collapse:collapse;background:#FFFFFF;border-radius:8px;overflow:hidden;border:1px solid #E2E8F0;">
            <thead><tr style="background:#F8FAFC;">
                <th style="padding:8px 12px;text-align:right;font-weight:600;border-bottom:2px solid #E2E8F0;">מחוז</th>
                <th style="padding:8px 12px;text-align:center;font-weight:600;border-bottom:2px solid #E2E8F0;">פעילים</th>
                <th style="padding:8px 12px;text-align:center;font-weight:600;border-bottom:2px solid #E2E8F0;">סגורים</th>
                <th style="padding:8px 12px;text-align:center;font-weight:600;border-bottom:2px solid #E2E8F0;">יח"ד</th>
                <th style="padding:8px 12px;text-align:center;font-weight:600;border-bottom:2px solid #E2E8F0;">ציון רוויה</th>
                <th style="padding:8px 12px;text-align:center;font-weight:600;border-bottom:2px solid #E2E8F0;">מגמה</th>
            </tr></thead>
            <tbody>{rows_html}</tbody>
            </table>""",
            unsafe_allow_html=True,
        )
        st.caption("ציון רוויה 0-100 (ביחס למחוז הפעיל ביותר). 6 חודשים אחרונים.")
    else:
        st.info("אין מספיק נתונים לניתוח רוויה אזורית")

# ── Tab 4: Document intelligence ──────────────────────────────────────────
with ci_tab4:
    doc_data = document_intelligence(filtered_df)
    if not doc_data.empty:
        st.dataframe(
            doc_data.rename(columns={
                "region": "מחוז",
                "avg_docs": "מסמכים ממוצע",
                "brochure_rate_pct": "שיעור חוברות %",
                "total_tenders": "סה\"כ מכרזים",
            }),
            hide_index=True,
            use_container_width=True,
        )
        st.caption("מודיעין זמינות מסמכים וחוברות לפי מחוז")
    else:
        st.info("אין נתוני מסמכים זמינים")

st.markdown("---")


# ============================================================================
# SECTION 4: PRICE ANALYTICS
# ============================================================================

st.markdown(
    '<div class="section-header">ניתוח מחירים</div>',
    unsafe_allow_html=True,
)

price_tab1, price_tab2, price_tab3 = st.tabs([
    "מגמות מחירים", "ניתוח תב\"ע", "פרמיית מחיר",
])

# ── Tab 1: Price trends by region ─────────────────────────────────────────
with price_tab1:
    if not prices_df.empty and not filtered_df.empty:
        price_trend_data = price_trends_by_region(prices_df, filtered_df)
        if not price_trend_data.empty:
            fig_price = px.line(
                price_trend_data,
                x="date",
                y="avg_price_per_sqm",
                color="region",
                markers=True,
                labels={
                    "date": "תאריך",
                    "avg_price_per_sqm": "מחיר ממוצע למ\"ר (₪)",
                    "region": "מחוז",
                },
                color_discrete_sequence=MEGIDO_CHART_COLORS,
            )
            fig_price.update_layout(
                title="מגמות מחיר זכייה ממוצע למ\"ר לפי מחוז",
                height=350,
                margin=dict(t=40, b=30, l=10, r=10),
                font=PLOTLY_FONT,
                **PLOTLY_BG,
                xaxis=dict(**PLOTLY_GRID),
                yaxis=dict(**PLOTLY_GRID),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            )
            st.plotly_chart(fig_price, use_container_width=True, key="price_trends")
        else:
            st.info("אין נתוני מחירים עם שטח קרקע תקין לחישוב מחיר למ\"ר")
    else:
        st.info("אין נתוני מחירי מכרזים. יש להריץ את סקריפט ההעשרה (analytics_enrichment.py) תחילה.")

# ── Tab 2: Taba analysis summary ──────────────────────────────────────────
with price_tab2:
    if not taba_df.empty:
        taba_summary = taba_analysis_summary(taba_df)
        if not taba_summary.empty:
            display_taba = taba_summary.copy()
            # Format numeric columns
            for col in ["avg_appraisal_price", "avg_floor_price", "avg_winning_bid"]:
                if col in display_taba.columns:
                    display_taba[col] = pd.to_numeric(display_taba[col], errors="coerce").apply(
                        lambda x: f"₪{x:,.0f}" if pd.notna(x) and x > 0 else "—"
                    )
            for col in ["premium_vs_appraisal_pct", "premium_vs_floor_pct"]:
                if col in display_taba.columns:
                    display_taba[col] = pd.to_numeric(display_taba[col], errors="coerce").apply(
                        lambda x: f"{x:.1f}%" if pd.notna(x) else "—"
                    )
            if "tender_rate_per_year" in display_taba.columns:
                display_taba["tender_rate_per_year"] = pd.to_numeric(
                    display_taba["tender_rate_per_year"], errors="coerce"
                ).apply(lambda x: f"{x:.1f}" if pd.notna(x) else "—")

            st.dataframe(
                display_taba.rename(columns={
                    "plan_number": "מספר תב\"ע",
                    "tender_count": "מכרזים",
                    "total_units": "יח\"ד",
                    "total_land_area": "שטח קרקע",
                    "avg_appraisal_price": "שומה ממוצעת",
                    "avg_floor_price": "מחיר סף ממוצע",
                    "avg_winning_bid": "זכייה ממוצעת",
                    "premium_vs_appraisal_pct": "פרמיה מול שומה",
                    "premium_vs_floor_pct": "פרמיה מול סף",
                    "first_seen": "ראשון",
                    "last_seen": "אחרון",
                    "tender_rate_per_year": "קצב/שנה",
                }),
                hide_index=True,
                use_container_width=True,
            )
            st.caption("ניתוח מצטבר לפי תב\"ע — מחירים, פרמיות וקצב מכרזים")
        else:
            st.info("אין נתוני תב\"ע מעובדים")
    else:
        st.info("אין נתוני תב\"ע. יש להריץ את סקריפט ההעשרה תחילה.")

# ── Tab 3: Price premium analysis ─────────────────────────────────────────
with price_tab3:
    if not prices_df.empty:
        premium_data = price_premium_analysis(prices_df)
        if not premium_data.empty:
            display_premium = premium_data.copy()
            # Format prices
            for col in ["appraisal_price", "floor_price", "winning_price"]:
                if col in display_premium.columns:
                    display_premium[col] = pd.to_numeric(display_premium[col], errors="coerce").apply(
                        lambda x: f"₪{x:,.0f}" if pd.notna(x) and x > 0 else "—"
                    )
            # Format premiums
            for col in ["premium_vs_appraisal_pct", "premium_vs_floor_pct"]:
                if col in display_premium.columns:
                    display_premium[col] = pd.to_numeric(display_premium[col], errors="coerce").apply(
                        lambda x: f"{x:+.1f}%" if pd.notna(x) else "—"
                    )

            st.dataframe(
                display_premium.rename(columns={
                    "tender_id": "מכרז",
                    "appraisal_price": "שומה",
                    "floor_price": "מחיר סף",
                    "winning_price": "זכייה",
                    "premium_vs_appraisal_pct": "פרמיה מול שומה",
                    "premium_vs_floor_pct": "פרמיה מול סף",
                    "region": "מחוז",
                }),
                hide_index=True,
                use_container_width=True,
            )
            st.caption("פרמיית/הנחת מחיר זכייה ביחס לשומת רמ\"י ומחיר סף")
        else:
            st.info("אין מכרזים עם נתוני הצעות זוכות")
    else:
        st.info("אין נתוני מחירים זמינים. יש להריץ את סקריפט ההעשרה תחילה.")

st.markdown("---")


# ============================================================================
# SECTION 5: SCORING
# ============================================================================

st.markdown(
    '<div class="section-header">ניקוד מכרזים</div>',
    unsafe_allow_html=True,
)

score_tab1, score_tab2, score_tab3 = st.tabs([
    "טופ 20", "התפלגות ציונים", "ניתוח מכרז",
])

# ── Tab 1: Top 20 scored tenders ──────────────────────────────────────────
with score_tab1:
    top_tenders = get_top_tenders(filtered_df, n=20)
    if not top_tenders.empty:
        display_top = top_tenders[[
            "tender_name", "city", "region", "units", "total_score",
            "urgency_score", "size_score", "readiness_score",
            "location_score", "freshness_score",
        ]].copy()

        # Build color-coded score badges via HTML
        def _score_badge(score: float) -> str:
            """Return an HTML badge string for a score value."""
            if score >= 70:
                bg = "#10B981"
            elif score >= 40:
                bg = "#F59E0B"
            else:
                bg = "#EF4444"
            return f'<span style="background:{bg};color:#fff;padding:2px 8px;border-radius:12px;font-weight:600;font-size:0.85rem;">{score:.0f}</span>'

        rows_html = ""
        for _, row in display_top.iterrows():
            name = html.escape(str(row.get("tender_name", ""))[:40])
            city = html.escape(str(row.get("city", "")) if pd.notna(row.get("city")) else "")
            region = html.escape(str(row.get("region", "")) if pd.notna(row.get("region")) else "")
            units = int(row.get("units", 0)) if pd.notna(row.get("units")) else 0
            badge = _score_badge(row["total_score"])

            rows_html += (
                f"<tr>"
                f"<td style='padding:5px 10px;border-bottom:1px solid #E2E8F0;'>{name}</td>"
                f"<td style='padding:5px 10px;border-bottom:1px solid #E2E8F0;'>{city}</td>"
                f"<td style='padding:5px 10px;border-bottom:1px solid #E2E8F0;'>{region}</td>"
                f"<td style='padding:5px 10px;border-bottom:1px solid #E2E8F0;text-align:center;'>{units}</td>"
                f"<td style='padding:5px 10px;border-bottom:1px solid #E2E8F0;text-align:center;'>{badge}</td>"
                f"</tr>"
            )

        st.markdown(
            f"""<table style="width:100%;border-collapse:collapse;background:#FFFFFF;border-radius:8px;overflow:hidden;border:1px solid #E2E8F0;">
            <thead><tr style="background:#F8FAFC;">
                <th style="padding:8px 10px;text-align:right;font-weight:600;border-bottom:2px solid #E2E8F0;">שם מכרז</th>
                <th style="padding:8px 10px;text-align:right;font-weight:600;border-bottom:2px solid #E2E8F0;">עיר</th>
                <th style="padding:8px 10px;text-align:right;font-weight:600;border-bottom:2px solid #E2E8F0;">מחוז</th>
                <th style="padding:8px 10px;text-align:center;font-weight:600;border-bottom:2px solid #E2E8F0;">יח"ד</th>
                <th style="padding:8px 10px;text-align:center;font-weight:600;border-bottom:2px solid #E2E8F0;">ציון</th>
            </tr></thead>
            <tbody>{rows_html}</tbody>
            </table>""",
            unsafe_allow_html=True,
        )
        st.caption("20 המכרזים עם הציון הגבוה ביותר (דחיפות 20%, גודל 20%, מוכנות 25%, מיקום 20%, טריות 15%)")
    else:
        st.info("אין מכרזים לניקוד")

# ── Tab 2: Score distribution histogram ───────────────────────────────────
with score_tab2:
    dist_data = get_score_distribution(filtered_df)
    if dist_data["bins"]:
        bins = dist_data["bins"]
        counts = dist_data["counts"]

        # Build bar labels from bin edges
        bin_labels = [f"{bins[i]:.0f}-{bins[i+1]:.0f}" for i in range(len(counts))]

        fig_dist = px.bar(
            x=bin_labels,
            y=counts,
            labels={"x": "טווח ציון", "y": "מספר מכרזים"},
            color=counts,
            color_continuous_scale=MEGIDO_GOLD_SCALE,
        )
        fig_dist.update_layout(
            title="התפלגות ציוני מכרזים",
            height=320,
            margin=dict(t=40, b=30, l=10, r=10),
            font=PLOTLY_FONT,
            **PLOTLY_BG,
            showlegend=False,
            xaxis=dict(**PLOTLY_GRID),
            yaxis=dict(**PLOTLY_GRID),
        )
        st.plotly_chart(fig_dist, use_container_width=True, key="score_distribution")

        # Stats
        s1, s2, s3 = st.columns(3)
        with s1:
            st.metric("ממוצע", f"{dist_data['mean']:.1f}")
        with s2:
            st.metric("חציון", f"{dist_data['median']:.1f}")
        with s3:
            st.metric("סטיית תקן", f"{dist_data['std']:.1f}")
    else:
        st.info("אין ציונים זמינים להתפלגות")

# ── Tab 3: Tender deep-dive with radar chart ──────────────────────────────
with score_tab3:
    if not scored_df.empty:
        # Build labels for selectbox
        deep_labels: dict[int, str] = {}
        for _, r in scored_df[["tender_id", "tender_name", "city", "total_score"]].iterrows():
            name = str(r["tender_name"])[:35] if pd.notna(r["tender_name"]) else ""
            city = str(r["city"])[:15] if pd.notna(r["city"]) else ""
            score_val = r["total_score"] if pd.notna(r["total_score"]) else 0
            deep_labels[int(r["tender_id"])] = f"{name} — {city} (ציון: {score_val:.0f})"

        sorted_ids = scored_df.sort_values("total_score", ascending=False)["tender_id"].astype(int).tolist()

        selected_deep = st.selectbox(
            "בחר מכרז לניתוח מעמיק",
            options=sorted_ids,
            format_func=lambda tid: deep_labels.get(tid, str(tid)),
            key="deep_dive_select",
            index=0,
        )

        if selected_deep is not None:
            tender_row = scored_df[scored_df["tender_id"] == selected_deep]
            if not tender_row.empty:
                row = tender_row.iloc[0]

                # Radar chart of 5 components
                categories = ["דחיפות", "גודל", "מוכנות", "מיקום", "טריות"]
                values = [
                    row.get("urgency_score", 0),
                    row.get("size_score", 0),
                    row.get("readiness_score", 0),
                    row.get("location_score", 0),
                    row.get("freshness_score", 0),
                ]
                # Close the polygon
                categories_closed = categories + [categories[0]]
                values_closed = values + [values[0]]

                fig_radar = go.Figure()
                fig_radar.add_trace(go.Scatterpolar(
                    r=values_closed,
                    theta=categories_closed,
                    fill="toself",
                    fillcolor="rgba(37,99,235,0.2)",
                    line=dict(color="#2563EB", width=2),
                    name="ציון",
                ))
                fig_radar.update_layout(
                    polar=dict(
                        radialaxis=dict(
                            visible=True,
                            range=[0, 100],
                            tickfont=dict(size=9, color="#64748B"),
                        ),
                        angularaxis=dict(
                            tickfont=dict(family="Inter, Heebo, sans-serif", size=12, color="#1E293B"),
                        ),
                        bgcolor="rgba(0,0,0,0)",
                    ),
                    height=380,
                    margin=dict(t=30, b=30, l=50, r=50),
                    font=PLOTLY_FONT,
                    **PLOTLY_BG,
                    showlegend=False,
                )
                st.plotly_chart(fig_radar, use_container_width=True, key="radar_deep")

                # Metrics row
                m1, m2, m3, m4, m5 = st.columns(5)
                with m1:
                    st.metric("דחיפות", f"{values[0]:.0f}")
                with m2:
                    st.metric("גודל", f"{values[1]:.0f}")
                with m3:
                    st.metric("מוכנות", f"{values[2]:.0f}")
                with m4:
                    st.metric("מיקום", f"{values[3]:.0f}")
                with m5:
                    st.metric("טריות", f"{values[4]:.0f}")

                st.markdown(
                    f"**ציון כולל: {row.get('total_score', 0):.1f}** / 100",
                )
    else:
        st.info("אין מכרזים לניתוח מעמיק")
