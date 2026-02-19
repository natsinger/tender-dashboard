"""
Full dashboard page — daily user view.

Includes: new tenders, KPIs, pie charts, deadlines table, data explorer,
tender detail viewer, watchlist management, detailed analytics, and admin/debug.
Branded for MEGIDO BY AURA (מגידו י.ק.).
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
    RMI_SITE_URL,
    TENDER_DETAIL_API,
)
from dashboard_utils import get_user_email, load_data, load_tender_details
from data_client import LandTendersClient, build_document_url

# ── MEGIDO brand constants ─────────────────────────────────────────────────
MEGIDO_CHART_COLORS = ["#D4A017", "#3B82F6", "#1B2A4A", "#10B981", "#EF4444", "#8B5CF6"]
MEGIDO_GOLD_SCALE = [[0, "#FEF3C7"], [1, "#D4A017"]]


# ============================================================================
# SIDEBAR
# ============================================================================

with st.sidebar:
    logo_path = Path(__file__).parent.parent / "assets" / "logo.jpg"
    if logo_path.exists():
        st.image(str(logo_path), width=140)
    st.markdown("""
    <div class="sidebar-header">
        <h2>MEGIDO</h2>
        <p>מגידו י.ק. | מכרזי קרקע</p>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("---")

    data_source = "latest_file"
    df = load_data(data_source=data_source)
    today = datetime.now()

    st.markdown("---")

    # ── Filters ──────────────────────────────────────────────────────────
    st.markdown("### 🔍 סינון")

    # Region filter
    if 'region' in df.columns:
        regions = sorted(df['region'].dropna().unique().tolist())
        selected_regions = st.multiselect(
            "אזור / מחוז",
            regions,
            default=[],
            placeholder="בחר אזורים (ריק = הכל)"
        )
    else:
        selected_regions = []

    # City filter — cascades from region
    if selected_regions:
        cities_in_regions = df[df['region'].isin(selected_regions)]['city'].dropna().unique()
        cities = sorted(cities_in_regions.tolist())
        city_placeholder = f"ערים באזורים שנבחרו ({len(cities)})"
    else:
        cities = sorted(df['city'].dropna().unique().tolist())
        city_placeholder = "בחר ערים (ריק = הכל)"

    selected_cities = st.multiselect(
        "עיר / יישוב",
        cities,
        default=[],
        placeholder=city_placeholder
    )

    # Tender type filter
    types = sorted(df['tender_type'].dropna().unique().tolist())
    selected_types = st.multiselect(
        "סוג מכרז",
        types,
        default=[],
        placeholder="בחר סוגים (ריק = הכל)"
    )

    # Status filter
    statuses = sorted(df['status'].dropna().unique().tolist())
    selected_statuses = st.multiselect(
        "סטטוס",
        statuses,
        default=[],
        placeholder="בחר סטטוסים (ריק = הכל)"
    )

    st.markdown("---")
    st.caption(f"עדכון אחרון: {today.strftime('%Y-%m-%d %H:%M')}")
    st.caption(f"סה\"כ רשומות: {len(df):,}")


# ============================================================================
# APPLY FILTERS
# ============================================================================

filtered_df = df.copy()

if selected_regions:
    filtered_df = filtered_df[filtered_df['region'].isin(selected_regions)]

if selected_cities:
    filtered_df = filtered_df[filtered_df['city'].isin(selected_cities)]

if selected_types:
    filtered_df = filtered_df[filtered_df['tender_type'].isin(selected_types)]

if selected_statuses:
    filtered_df = filtered_df[filtered_df['status'].isin(selected_statuses)]

# Default active-only filter (unless user explicitly selected statuses)
if not selected_statuses:
    filtered_df = filtered_df[~filtered_df['status'].isin(NON_ACTIVE_STATUSES)]

# ============================================================================
# SECTION 0: NEW TENDERS THIS WEEK (since last Sunday)
# ============================================================================


def _last_sunday(ref_date: datetime) -> datetime:
    """Return the most recent Sunday (00:00) on or before ref_date."""
    days_since_sunday = ref_date.weekday() + 1
    if days_since_sunday == 7:
        days_since_sunday = 0
    return (ref_date - timedelta(days=days_since_sunday)).replace(
        hour=0, minute=0, second=0, microsecond=0,
    )


sunday_cutoff = _last_sunday(today)

# Filter: brochure available + still open
new_tenders_df = filtered_df[
    (filtered_df['published_booklet'] == True) &
    (filtered_df['deadline'].notna()) &
    (filtered_df['deadline'] >= today)
].copy()

# Use publish_date as the "new since" indicator
date_col = None
for candidate in ['created_date', 'publish_date', 'published_date']:
    if candidate in new_tenders_df.columns:
        date_col = candidate
        break

if date_col:
    new_tenders_df = new_tenders_df[new_tenders_df[date_col] >= sunday_cutoff]

st.markdown('<div class="section-header" style="font-size:1.6rem; margin-top:0;">מכרזי קרקע</div>', unsafe_allow_html=True)
st.caption(f"MEGIDO | מעקב מכרזי קרקע  •  מעודכן: {today.strftime('%d/%m/%Y')}")

if len(new_tenders_df) > 0:
    st.markdown('<div class="new-tenders-card">', unsafe_allow_html=True)
    st.markdown(f"### 🆕 מכרזים חדשים מיום ראשון ({sunday_cutoff.strftime('%d/%m')})")
    new_display = new_tenders_df[[
        'tender_name', 'city', 'units', 'tender_type', 'deadline'
    ]].copy()
    new_display.columns = ['שם מכרז', 'עיר', 'יח"ד', 'סוג', 'מועד אחרון']
    new_display['מועד אחרון'] = pd.to_datetime(new_display['מועד אחרון']).dt.strftime('%d/%m/%Y')
    new_display = new_display.sort_values('יח"ד', ascending=False)
    st.dataframe(
        new_display,
        use_container_width=True,
        hide_index=True,
        height=min(38 * len(new_display) + 40, 250),
    )
    st.markdown('</div>', unsafe_allow_html=True)
else:
    st.info(f"אין מכרזים חדשים עם חוברת מאז יום ראשון ({sunday_cutoff.strftime('%d/%m')})")

st.markdown("---")

# ============================================================================
# SECTION 1: EXECUTIVE KPIs
# ============================================================================

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("🟢 מכרזים פתוחים", f"{len(filtered_df):,}")

with col2:
    total_units = int(filtered_df['units'].sum())
    st.metric("🏠 יח\"ד", f"{total_units:,}")

with col3:
    unique_cities = filtered_df['city'].nunique()
    st.metric("🏙️ ערים", f"{unique_cities}")

with col4:
    closing_soon = len(filtered_df[
        (filtered_df['deadline'].notna()) &
        (filtered_df['deadline'] >= today) &
        (filtered_df['deadline'] <= today + timedelta(days=CLOSING_SOON_DAYS))
    ])
    st.metric(f"⏰ נסגרים ב-{CLOSING_SOON_DAYS} יום", closing_soon)

st.markdown("---")


# ============================================================================
# SECTION 2: THREE PIE CHARTS (side by side)
# ============================================================================

PLOTLY_FONT = dict(family="Inter, Heebo, sans-serif", size=12, color="#111827")
PLOTLY_TRANSPARENT_BG = dict(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")

col_pie1, col_pie2, col_pie3 = st.columns(3)

# ── Pie Chart 1: Brochure Availability ────────────────────────────────────
with col_pie1:
    st.markdown('<p class="pie-title">📋 חוברת מכרז</p>', unsafe_allow_html=True)

    if 'published_booklet' in filtered_df.columns and len(filtered_df) > 0:
        booklet_counts = filtered_df['published_booklet'].value_counts()
        available = int(booklet_counts.get(True, 0))
        not_available = int(booklet_counts.get(False, 0))

        fig_booklet = px.pie(
            values=[available, not_available],
            names=["חוברת זמינה", "חוברת לא זמינה"],
            color_discrete_sequence=["#D4A017", "#E5E7EB"],
            hole=0.55,
        )
        fig_booklet.update_traces(
            textinfo='value',
            textposition='inside',
            textfont_size=14,
            hovertemplate='%{label}: %{value} (%{percent})<extra></extra>',
        )
        fig_booklet.update_layout(
            height=220,
            margin=dict(t=10, b=30, l=5, r=5),
            legend=dict(
                orientation="h", yanchor="top", y=-0.08,
                xanchor="center", x=0.5, font=dict(size=11),
            ),
            showlegend=True,
            font=PLOTLY_FONT,
            uniformtext_minsize=10, uniformtext_mode='hide',
            **PLOTLY_TRANSPARENT_BG,
        )
        st.plotly_chart(fig_booklet, use_container_width=True, key="pie_booklet")
    else:
        st.info("אין נתוני חוברת מכרז")

# ── Pie Chart 2: Brochure-only tenders by District + Urgency Toggle ──────
with col_pie2:
    # Title + week toggle in one row
    _pie2_title_col, _pie2_radio_col = st.columns([2, 1])
    with _pie2_title_col:
        st.markdown('<p class="pie-title" style="margin-bottom:0;">חוברות לפי מחוז</p>', unsafe_allow_html=True)
    with _pie2_radio_col:
        st.radio(
            "טווח",
            list({"1W": 7, "2W": 14, "4W": 28}.keys()),
            index=2,
            horizontal=True,
            key="urgency_pie2",
            label_visibility="collapsed",
        )

    pie2_days_options = {"1W": 7, "2W": 14, "4W": 28}
    urgency_pie2 = st.session_state.get('urgency_pie2', '4W')
    pie2_days = pie2_days_options.get(urgency_pie2, 28)

    pie2_df = filtered_df[filtered_df['published_booklet'] == True].copy()
    pie2_cutoff = today + timedelta(days=pie2_days)
    pie2_df = pie2_df[
        (pie2_df['deadline'].notna()) &
        (pie2_df['deadline'] >= today) &
        (pie2_df['deadline'] <= pie2_cutoff)
    ]

    if 'region' in pie2_df.columns and len(pie2_df) > 0:
        brochure_by_region = (
            pie2_df.groupby('region')
            .size()
            .reset_index(name='count')
            .sort_values('count', ascending=False)
        )
        if not brochure_by_region.empty:
            fig_brochure_region = px.pie(
                brochure_by_region,
                values='count',
                names='region',
                hole=0.55,
                color_discrete_sequence=MEGIDO_CHART_COLORS,
            )
            fig_brochure_region.update_traces(
                textinfo='value',
                textposition='inside',
                textfont_size=14,
                hovertemplate='%{label}: %{value} (%{percent})<extra></extra>',
            )
            fig_brochure_region.update_layout(
                height=220,
                margin=dict(t=10, b=10, l=5, r=5),
                showlegend=False,
                uniformtext_minsize=10, uniformtext_mode='hide',
                font=dict(family="Inter, Heebo, sans-serif", size=11, color="#111827"),
                **PLOTLY_TRANSPARENT_BG,
            )
            st.plotly_chart(fig_brochure_region, use_container_width=True, key="pie_brochure_region")
        else:
            st.info("אין מכרזים עם חוברת בטווח שנבחר")
    else:
        st.info("אין נתונים")

# ── Pie Chart 3: All tenders by District ──────────────────────────────────
with col_pie3:
    st.markdown('<p class="pie-title">מכרזים פעילים</p>', unsafe_allow_html=True)

    if 'region' in filtered_df.columns and len(filtered_df) > 0:
        tenders_by_region = (
            filtered_df.groupby('region')
            .size()
            .reset_index(name='count')
            .sort_values('count', ascending=False)
        )

        if not tenders_by_region.empty:
            fig_region = px.pie(
                tenders_by_region,
                values='count',
                names='region',
                hole=0.55,
                color_discrete_sequence=MEGIDO_CHART_COLORS,
            )
            fig_region.update_traces(
                textinfo='value',
                textposition='inside',
                textfont_size=14,
                hovertemplate='%{label}: %{value} מכרזים (%{percent})<extra></extra>',
            )
            fig_region.update_layout(
                height=220,
                margin=dict(t=10, b=10, l=5, r=5),
                showlegend=False,
                uniformtext_minsize=10, uniformtext_mode='hide',
                font=dict(family="Inter, Heebo, sans-serif", size=11, color="#111827"),
                **PLOTLY_TRANSPARENT_BG,
            )
            st.plotly_chart(fig_region, use_container_width=True, key="pie_region_units")

            with st.expander("📋 פירוט לפי מחוז"):
                for region_name in tenders_by_region['region'].tolist():
                    region_subset = filtered_df[filtered_df['region'] == region_name]
                    region_units = int(region_subset['units'].sum())
                    with st.expander(f"{region_name} — {region_units:,} יח\"ד ({len(region_subset)} מכרזים)"):
                        detail = region_subset.nlargest(8, 'units')[['tender_name', 'city', 'units', 'tender_type']].copy()
                        detail.columns = ['שם מכרז', 'עיר', 'יח"ד', 'סוג']
                        st.dataframe(detail, use_container_width=True, hide_index=True, height=min(38 * len(detail) + 40, 200))
        else:
            st.info("אין נתוני יח\"ד להצגה")
    else:
        st.info("אין נתוני אזור")

st.markdown("---")


# ============================================================================
# SECTION 3: UPCOMING DEADLINES TABLE (enhanced)
# ============================================================================

st.subheader("⏰ מכרזים קרובים לסגירה")

EXCLUDED_STATUSES = {"בוטל", "נסגר"}
upcoming = filtered_df[
    (filtered_df['deadline'].notna()) &
    (filtered_df['deadline'] >= today) &
    (~filtered_df['status'].isin(EXCLUDED_STATUSES))
].sort_values('deadline')

if len(upcoming) > 0:
    upcoming_display = upcoming[[
        'tender_name', 'city', 'units', 'deadline', 'published_booklet'
    ]].copy()

    upcoming_display['days_left'] = (upcoming_display['deadline'] - today).dt.days

    def urgency_indicator(days: int) -> str:
        """Return urgency emoji based on days remaining."""
        if days <= 7:
            return '🔴'
        elif days <= 14:
            return '🟡'
        return '🟢'

    upcoming_display['urgency'] = upcoming_display['days_left'].apply(urgency_indicator)
    upcoming_display['booklet'] = upcoming_display['published_booklet'].apply(
        lambda x: '✅' if x else '❌'
    )
    upcoming_display['deadline'] = upcoming_display['deadline'].dt.strftime('%d/%m')

    display_upcoming = upcoming_display[[
        'urgency', 'tender_name', 'city', 'units', 'deadline', 'days_left', 'booklet'
    ]].copy()

    st.caption(f"מציג {len(display_upcoming)} מכרזים עם מועד סגירה עתידי")

    st.dataframe(
        display_upcoming,
        column_config={
            "urgency": st.column_config.TextColumn("", width="small"),
            "tender_name": st.column_config.TextColumn("שם", width="medium"),
            "city": st.column_config.TextColumn("עיר", width="small"),
            "units": st.column_config.NumberColumn("יח\"ד", format="%d", width="small"),
            "deadline": st.column_config.TextColumn("סגירה", width="small"),
            "days_left": st.column_config.NumberColumn("ימים", format="%d", width="small"),
            "booklet": st.column_config.TextColumn("📋", width="small"),
        },
        hide_index=True,
        use_container_width=True,
    )
else:
    st.info("אין מכרזים קרובים לסגירה בטווח שנבחר.")

st.markdown("---")


# ============================================================================
# SECTION 4: FULL DATA EXPLORER
# ============================================================================

st.subheader("📋 כל המכרזים")

COLUMN_LABELS = {
    "tender_id": "מס' מכרז",
    "tender_name": "שם מכרז",
    "city": "עיר",
    "region": "מחוז",
    "tender_type": "סוג מכרז",
    "purpose": "ייעוד",
    "units": "יח\"ד",
    "deadline": "מועד סגירה",
    "publish_date": "תאריך פרסום",
    "committee_date": "תאריך ועדה",
    "status": "סטטוס",
    "published_booklet": "חוברת מכרז",
    "location": "מיקום",
    "targeted": "מכוון",
}

HIDDEN_COLUMNS = {
    'city_code', 'status_code', 'purpose_code', 'tender_type_code',
    'KodMerchav', 'KhalYaadRashi', 'PirsumDate', 'ChoveretUpdateDate',
    'area_sqm', 'min_price', 'gush', 'helka',
}

user_cols = [c for c in filtered_df.columns if c not in HIDDEN_COLUMNS]
default_cols = [
    'tender_name', 'city', 'tender_type',
    'units', 'deadline', 'status', 'published_booklet'
]
display_cols = [c for c in default_cols if c in user_cols]

selected_cols = st.multiselect(
    "בחר עמודות להצגה",
    user_cols,
    default=display_cols,
    format_func=lambda c: COLUMN_LABELS.get(c, c),
)

# ── Per-column filters ──────────────────────────────────────────────────
st.markdown("##### סינון לפי עמודה")
filter_cols = st.columns(4)

table_df = filtered_df.copy()

with filter_cols[0]:
    if 'city' in table_df.columns:
        city_vals = sorted(table_df['city'].dropna().unique().tolist())
        tbl_city = st.multiselect(
            "עיר", city_vals, default=[], key="tbl_city",
            placeholder="הכל",
        )
        if tbl_city:
            table_df = table_df[table_df['city'].isin(tbl_city)]

with filter_cols[1]:
    if 'region' in table_df.columns:
        region_vals = sorted(table_df['region'].dropna().unique().tolist())
        tbl_region = st.multiselect(
            "מחוז", region_vals, default=[], key="tbl_region",
            placeholder="הכל",
        )
        if tbl_region:
            table_df = table_df[table_df['region'].isin(tbl_region)]

with filter_cols[2]:
    if 'purpose' in table_df.columns:
        purpose_vals = sorted(table_df['purpose'].dropna().unique().tolist())
        tbl_purpose = st.multiselect(
            "ייעוד", purpose_vals, default=[], key="tbl_purpose",
            placeholder="הכל",
        )
        if tbl_purpose:
            table_df = table_df[table_df['purpose'].isin(tbl_purpose)]

with filter_cols[3]:
    if 'status' in table_df.columns:
        status_vals = sorted(table_df['status'].dropna().unique().tolist())
        tbl_status = st.multiselect(
            "סטטוס", status_vals, default=[], key="tbl_status",
            placeholder="הכל",
        )
        if tbl_status:
            table_df = table_df[table_df['status'].isin(tbl_status)]

search_term = st.text_input(
    "🔍 חיפוש חופשי", placeholder="הקלד לחיפוש בכל העמודות..."
)

if selected_cols:
    display_df = table_df[selected_cols].copy()

    if search_term:
        mask = display_df.astype(str).apply(
            lambda row: row.str.contains(search_term, case=False, na=False).any(),
            axis=1
        )
        display_df = display_df[mask]

    st.caption(f"מציג {len(display_df):,} רשומות")

    if 'deadline' in display_df.columns:
        display_df = display_df.sort_values(
            'deadline', ascending=True, na_position='last'
        )

    display_df_formatted = display_df.copy()

    for col in ['publish_date', 'deadline', 'committee_date']:
        if col in display_df_formatted.columns:
            display_df_formatted[col] = pd.to_datetime(
                display_df_formatted[col], errors='coerce'
            )

    if 'tender_id' in display_df_formatted.columns:
        display_df_formatted['tender_id'] = (
            display_df_formatted['tender_id'].astype(str)
        )

    st.dataframe(
        display_df_formatted,
        hide_index=True,
        use_container_width=True,
        column_config={
            "tender_id": st.column_config.TextColumn("מס' מכרז", width="medium"),
            "tender_name": st.column_config.TextColumn("שם מכרז", width="large"),
            "city": st.column_config.TextColumn("עיר", width="medium"),
            "region": st.column_config.TextColumn("מחוז", width="small"),
            "tender_type": st.column_config.TextColumn("סוג", width="medium"),
            "purpose": st.column_config.TextColumn("ייעוד", width="medium"),
            "units": st.column_config.NumberColumn("יח\"ד", format="%d"),
            "deadline": st.column_config.DateColumn("מועד סגירה", format="YYYY-MM-DD"),
            "publish_date": st.column_config.DateColumn("תאריך פרסום", format="YYYY-MM-DD"),
            "committee_date": st.column_config.DateColumn("תאריך ועדה", format="YYYY-MM-DD"),
            "status": st.column_config.TextColumn("סטטוס", width="small"),
            "published_booklet": st.column_config.CheckboxColumn("חוברת"),
            "location": st.column_config.TextColumn("מיקום", width="medium"),
        },
    )

    csv = display_df.to_csv(index=False, encoding='utf-8-sig')
    st.download_button(
        label="📥 הורד CSV",
        data=csv,
        file_name=f"land_tenders_{today.strftime('%Y%m%d')}.csv",
        mime="text/csv"
    )

st.markdown("---")


# ============================================================================
# SECTION 5: TENDER DETAIL VIEWER
# ============================================================================

st.subheader("🔍 צפייה בפרטי מכרז")

col_select, col_refresh, col_fetch = st.columns([3, 1, 1])

with col_select:
    detail_candidates = filtered_df.copy()
    if len(detail_candidates) == 0:
        detail_candidates = df.head(50)

    detail_candidates = detail_candidates.sort_values('deadline', ascending=False)

    def format_tender_label(row: pd.Series) -> str:
        """Format tender row for selectbox display."""
        name = row['tender_name'][:50] if pd.notna(row['tender_name']) else 'N/A'
        city = row['city'][:20] if pd.notna(row['city']) else 'N/A'
        return f"{row['tender_id']} - {name} ({city})"

    detail_candidates['display_label'] = detail_candidates.apply(format_tender_label, axis=1)

    selected_tender_id = st.selectbox(
        "בחר מכרז לצפייה",
        options=detail_candidates['tender_id'].tolist(),
        format_func=lambda tid: detail_candidates[
            detail_candidates['tender_id'] == tid
        ]['display_label'].values[0]
    )

with col_refresh:
    force_refresh = st.checkbox(
        "רענן מהAPI",
        value=False,
        help="עקוף מטמון וטען נתונים חדשים"
    )

with col_fetch:
    if st.button(
        "📥 טען הכל",
        help=f"טען פרטים עבור {len(detail_candidates)} מכרזים"
    ):
        with st.spinner(f"טוען פרטים עבור {len(detail_candidates)} מכרזים..."):
            client = LandTendersClient(data_dir=str(DATA_DIR))
            tender_ids = detail_candidates['tender_id'].tolist()
            details_dict = client.fetch_multiple_details(
                tender_ids,
                max_workers=DEFAULT_FETCH_WORKERS,
                delay_seconds=DEFAULT_FETCH_DELAY,
            )
            st.success(f"נטענו פרטים עבור {len(details_dict)} מכרזים!")

# Display selected tender details
if selected_tender_id:
    st.markdown("---")

    with st.spinner(f"טוען פרטי מכרז {selected_tender_id}..."):
        details = load_tender_details(selected_tender_id)

        list_data = filtered_df[filtered_df['tender_id'] == selected_tender_id]
        if len(list_data) > 0:
            list_data = list_data.iloc[0].to_dict()
        else:
            list_data = None

    if details:
        with st.expander(f"📋 מכרז {selected_tender_id} — פרטים מלאים", expanded=True):

            st.markdown("### סקירה כללית")
            ov1, ov2, ov3, ov4 = st.columns(4)

            with ov1:
                st.metric("מס' מכרז", details.get('MichrazID', selected_tender_id))
            with ov2:
                st.metric("סטטוס", list_data.get('status', 'N/A') if list_data else 'N/A')
            with ov3:
                units = details.get(
                    'YechidotDiur',
                    list_data.get('units', 0) if list_data else 0
                )
                st.metric("יח\"ד", f"{int(units):,}" if units else "N/A")
            with ov4:
                deadline_dt = pd.to_datetime(details.get('SgiraDate'), errors='coerce')
                if pd.notna(deadline_dt):
                    deadline_naive = (
                        deadline_dt.tz_localize(None) if deadline_dt.tzinfo else deadline_dt
                    )
                    days_until = (deadline_naive - today).days
                    st.metric("ימים לסגירה", days_until)
                else:
                    st.metric("מועד סגירה", "N/A")

            st.markdown("---")
            st.markdown("### פרטי מכרז")

            info_left, info_right = st.columns(2)

            with info_left:
                tender_name = details.get('MichrazName', 'N/A')
                city_val = list_data.get('city', 'N/A') if list_data else 'N/A'
                location = details.get('Shchuna', list_data.get('location', '') if list_data else '')
                tender_type_val = list_data.get('tender_type', 'N/A') if list_data else 'N/A'
                purpose_val = list_data.get('purpose', 'N/A') if list_data else 'N/A'

                info_html = f'''
                <div class="detail-field">
                    <strong>שם מכרז:</strong> {tender_name}<br>
                    <strong>עיר:</strong> {city_val}<br>
                    {'<strong>מיקום:</strong> ' + str(location) + '<br>' if location else ''}
                    <strong>סוג:</strong> {tender_type_val}<br>
                    <strong>ייעוד:</strong> {purpose_val}
                </div>
                '''
                st.markdown(info_html, unsafe_allow_html=True)

            with info_right:
                publish = pd.to_datetime(details.get('PtichaDate'), errors='coerce')
                publish_str = publish.strftime('%Y-%m-%d') if pd.notna(publish) else 'N/A'
                deadline_dt = pd.to_datetime(details.get('SgiraDate'), errors='coerce')
                deadline_str = deadline_dt.strftime('%Y-%m-%d %H:%M') if pd.notna(deadline_dt) else 'N/A'
                committee = pd.to_datetime(details.get('VaadaDate'), errors='coerce')
                committee_str = committee.strftime('%Y-%m-%d') if pd.notna(committee) else 'N/A'

                dates_html = f'''
                <div class="detail-field">
                    <strong>תאריך פרסום:</strong> {publish_str}<br>
                    <strong>מועד סגירה:</strong> {deadline_str}<br>
                    <strong>תאריך ועדה:</strong> {committee_str}
                </div>
                '''
                st.markdown(dates_html, unsafe_allow_html=True)

            st.markdown("---")
            st.markdown("### 💰 הצעות ומציעים")

            plots = details.get('Tik', [])

            if plots:
                for plot_idx, plot in enumerate(plots, 1):
                    st.markdown(f"#### מגרש {plot_idx}: {plot.get('TikID', 'N/A')}")

                    winner_name = (plot.get('ShemZoche') or '').strip()
                    winner_amount = plot.get('SchumZchiya', 0)

                    if winner_name:
                        st.success(f"🏆 **זוכה:** {winner_name}")
                        winner_amount_str = f"₪{winner_amount:,.2f}" if winner_amount else 'N/A'
                        area_str = f"{plot.get('Shetach', 0):,} מ\"ר"
                        threshold_str = f"₪{plot.get('MechirSaf', 0):,.2f}"
                        bid_html = f'''
                        <div class="detail-field">
                            <strong>סכום זכייה:</strong> {winner_amount_str} &nbsp;|&nbsp;
                            <strong>שטח:</strong> {area_str} &nbsp;|&nbsp;
                            <strong>מחיר סף:</strong> {threshold_str}
                        </div>
                        '''
                        st.markdown(bid_html, unsafe_allow_html=True)

                    bidders = plot.get('mpHatzaaotMitcham', [])
                    if bidders:
                        st.info(f"📊 **סה\"כ הצעות:** {len(bidders)}")

                        bidder_df = pd.DataFrame(bidders)
                        bidder_df = bidder_df.sort_values('HatzaaSum', ascending=False)

                        display_bidder_df = bidder_df.copy()
                        display_bidder_df['HatzaaSum'] = display_bidder_df['HatzaaSum'].apply(
                            lambda x: f"₪{x:,.2f}" if pd.notna(x) else 'N/A'
                        )
                        display_bidder_df = display_bidder_df.rename(columns={
                            'HatzaaID': 'מס\' הצעה',
                            'HatzaaSum': 'סכום',
                            'HatzaaDescription': 'תיאור'
                        })

                        st.dataframe(
                            display_bidder_df,
                            use_container_width=True,
                            hide_index=True
                        )

                        csv_bid = bidder_df.to_csv(index=False, encoding='utf-8-sig')
                        st.download_button(
                            label=f"📥 הורד CSV מציעים (מגרש {plot_idx})",
                            data=csv_bid,
                            file_name=f"bidders_{selected_tender_id}_plot{plot_idx}.csv",
                            mime="text/csv"
                        )
                    else:
                        st.info("אין הצעות למגרש זה")

                    if plot_idx < len(plots):
                        st.markdown("---")
            else:
                st.info("אין מידע על הצעות למכרז זה")

            st.markdown("---")
            st.markdown("### 📄 מסמכים")

            full_doc = details.get('MichrazFullDocument')
            if full_doc and full_doc.get('RowID') is not None:
                doc_name = full_doc.get('DocName', 'מסמך פרסום מלא.pdf')
                doc_url = build_document_url(full_doc)
                st.markdown(
                    f"#### 📕 מסמך פרסום מלא\n\n"
                    f"[📥 **הורד: {doc_name}**]({doc_url})"
                )

            docs = details.get('MichrazDocList', [])
            if docs:
                st.markdown(f"#### 📁 מסמכים נוספים ({len(docs)})")
                for doc in docs[:15]:
                    doc_name = doc.get('DocName', doc.get('Teur', 'Unknown'))
                    doc_desc = doc.get('Teur', '')
                    doc_date = doc.get('UpdateDate', '')
                    if doc_date:
                        date_formatted = pd.to_datetime(doc_date, errors='coerce')
                        if pd.notna(date_formatted):
                            doc_date = date_formatted.strftime('%Y-%m-%d')

                    doc_url = build_document_url(doc)
                    st.markdown(
                        f"- [{doc_name}]({doc_url}) — {doc_desc} ({doc_date})"
                    )

                if len(docs) > 15:
                    st.caption(f"... ועוד {len(docs) - 15} מסמכים")

            elif not full_doc:
                st.info("אין מסמכים זמינים")

            st.markdown("---")
            official_url = f"{RMI_SITE_URL}/{selected_tender_id}"
            st.markdown(f"🔗 [צפה באתר רמ\"י הרשמי]({official_url})")

    else:
        st.error(f"לא ניתן לטעון פרטים למכרז {selected_tender_id}")
        st.info("יתכן שמזהה המכרז לא קיים, או שהAPI אינו זמין.")

st.markdown("---")


# ============================================================================
# SECTION 5.5: WATCHLIST MANAGEMENT
# ============================================================================

st.subheader("🔔 רשימת מעקב")

user_email = get_user_email()

if not user_email:
    st.warning(
        "לא זוהה משתמש. "
        "בסביבת פיתוח, הגדר DEV_USER_EMAIL בקובץ .env."
    )
else:
    st.caption(f"משתמש: {user_email}")

    from db import TenderDB
    watch_db = TenderDB()

    # ── Add to watchlist ──────────────────────────────────────────────
    # Build label map from ALL tenders (not just filtered) so user can watch any tender
    _watch_labels: dict[int, str] = {}
    for _, _r in df[['tender_id', 'tender_name', 'city']].iterrows():
        _name = str(_r['tender_name'])[:50] if pd.notna(_r['tender_name']) else ''
        _city = str(_r['city'])[:20] if pd.notna(_r['city']) else ''
        _watch_labels[int(_r['tender_id'])] = f"{_name} — {_city}" if _city else _name

    add_col, btn_col = st.columns([3, 1])

    with add_col:
        watch_tender_id = st.selectbox(
            "בחר מכרז להוספה לרשימת מעקב",
            options=list(_watch_labels.keys()),
            index=None,
            format_func=lambda tid: _watch_labels[tid],
            placeholder="הקלד מספר מכרז או שם עיר...",
            key="watch_tender_input",
        )

    with btn_col:
        st.markdown("<br>", unsafe_allow_html=True)
        add_clicked = st.button("➕ הוסף למעקב", key="btn_add_watch")

    if add_clicked and watch_tender_id is not None:
        _label = _watch_labels[watch_tender_id]
        added = watch_db.add_to_watchlist(user_email, int(watch_tender_id))
        if added:
            st.success(
                f"מכרז {_label} נוסף לרשימת המעקב! "
                f"תקבל/י התראה במייל כשיתווספו מסמכים חדשים."
            )
        else:
            st.info(f"מכרז {_label} כבר נמצא ברשימת המעקב.")

    # ── Display watchlist ─────────────────────────────────────────────
    watchlist_df = watch_db.get_user_watchlist(user_email)

    if len(watchlist_df) > 0:
        st.markdown(f"##### מכרזים במעקב ({len(watchlist_df)})")

        for _, row in watchlist_df.iterrows():
            w_cols = st.columns([2, 2, 2, 2, 1, 1])
            with w_cols[0]:
                st.write(str(row.get('tender_name', row['tender_id'])))
            with w_cols[1]:
                st.write(row.get('city', ''))
            with w_cols[2]:
                st.write(row.get('region', ''))
            with w_cols[3]:
                deadline_val = row.get('deadline', '')
                if pd.notna(deadline_val):
                    dl = pd.to_datetime(deadline_val, errors='coerce')
                    st.write(dl.strftime('%d/%m/%Y') if pd.notna(dl) else '')
                else:
                    st.write('')
            with w_cols[4]:
                st.write(row.get('status', ''))
            with w_cols[5]:
                if st.button("🗑️", key=f"rm_watch_{row['watch_id']}"):
                    watch_db.remove_from_watchlist(user_email, int(row['tender_id']))
                    st.rerun()

        st.info("תקבל/י התראה במייל כשיתווספו מסמכים חדשים למכרזים שברשימה.")
    else:
        st.info("רשימת המעקב ריקה. הוסף/י מכרזים לפי מספר כדי לקבל התראות.")

st.markdown("---")


# ============================================================================
# SECTION 6: DETAILED ANALYTICS (collapsible)
# ============================================================================

with st.expander("📊 ניתוח מפורט", expanded=False):

    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        st.subheader("📍 מכרזים לפי עיר")
        city_counts = filtered_df['city'].value_counts().head(10)

        if len(city_counts) > 0:
            fig_city = px.bar(
                x=city_counts.values,
                y=city_counts.index,
                orientation='h',
                labels={'x': 'מספר מכרזים', 'y': 'עיר'},
                color=city_counts.values,
                color_continuous_scale=MEGIDO_GOLD_SCALE,
            )
            fig_city.update_layout(
                showlegend=False, height=280,
                margin=dict(t=10, b=30, l=10, r=10),
                font=PLOTLY_FONT, **PLOTLY_TRANSPARENT_BG,
            )
            st.plotly_chart(fig_city, use_container_width=True)
        else:
            st.info("אין נתונים להצגה")

    with chart_col2:
        st.subheader("🏷️ מכרזים לפי סוג")
        type_counts = filtered_df['tender_type'].value_counts()

        if len(type_counts) > 0:
            fig_type = px.pie(
                values=type_counts.values,
                names=type_counts.index,
                hole=0.4,
                color_discrete_sequence=MEGIDO_CHART_COLORS,
            )
            fig_type.update_layout(
                height=280,
                margin=dict(t=10, b=30, l=10, r=10),
                font=PLOTLY_FONT, **PLOTLY_TRANSPARENT_BG,
            )
            st.plotly_chart(fig_type, use_container_width=True)
        else:
            st.info("אין נתונים להצגה")

    chart_col3, chart_col4 = st.columns(2)

    with chart_col3:
        st.subheader("📈 מכרזים לאורך זמן")
        timeline_df = filtered_df.copy()

        if len(timeline_df) > 0 and timeline_df['publish_date'].notna().any():
            timeline_df['month'] = timeline_df['publish_date'].dt.to_period('M').astype(str)
            monthly_counts = timeline_df.groupby('month').size().reset_index(name='count')

            fig_timeline = px.line(
                monthly_counts,
                x='month',
                y='count',
                markers=True,
                labels={'month': 'חודש', 'count': 'מספר מכרזים'},
                color_discrete_sequence=['#1B2A4A'],
            )
            fig_timeline.update_layout(
                height=280,
                margin=dict(t=10, b=30, l=10, r=10),
                font=PLOTLY_FONT, **PLOTLY_TRANSPARENT_BG,
            )
            st.plotly_chart(fig_timeline, use_container_width=True)
        else:
            st.info("אין נתוני תאריכים להצגה")

    with chart_col4:
        st.subheader("🏠 יח\"ד לפי סוג מכרז")
        units_by_type = filtered_df.groupby('tender_type')['units'].sum().reset_index()
        units_by_type = units_by_type[units_by_type['units'] > 0]

        if not units_by_type.empty:
            fig_units = px.bar(
                units_by_type,
                x='tender_type',
                y='units',
                labels={'units': 'סה\"כ יח\"ד', 'tender_type': 'סוג מכרז'},
                color_discrete_sequence=['#D4A017'],
            )
            fig_units.update_layout(
                height=280,
                margin=dict(t=10, b=30, l=10, r=10),
                font=PLOTLY_FONT, **PLOTLY_TRANSPARENT_BG,
            )
            st.plotly_chart(fig_units, use_container_width=True)
        else:
            st.info("אין נתוני יח\"ד להצגה")


# ============================================================================
# SECTION 7: ADMIN / DEBUG (collapsible)
# ============================================================================

with st.expander("🔧 ניהול ודיבוג", expanded=False):
    st.markdown("### סטטוס מערכת")
    st.code(f"""
    מקור נתונים: {data_source}
    רשומות שנטענו: {len(df):,}
    רשומות מסוננות: {len(filtered_df):,}
    סוגי מכרז: {', '.join(df['tender_type'].unique().tolist())}
    """)

    st.markdown("### API Endpoints")
    st.code(f"""
    List: {LAND_AUTHORITY_API} (POST)
    Detail: {TENDER_DETAIL_API}?michrazID=
    Docs: {DOCUMENT_DOWNLOAD_API}
    """)
