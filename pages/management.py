"""
Management overview page — simplified executive view.

Shows KPIs, brochure/region pie charts, and a closing-soon table.
No detail viewer, watchlist, data explorer, or debug section.
"""

from datetime import datetime, timedelta

import pandas as pd
import plotly.express as px
import streamlit as st

from config import CLOSING_SOON_DAYS, NON_ACTIVE_STATUSES
from dashboard_utils import load_data


# ============================================================================
# SIDEBAR (minimal)
# ============================================================================

with st.sidebar:
    st.markdown("""
    <div class="sidebar-header">
        <h2>📊 סקירה ניהולית</h2>
        <p>רשות מקרקעי ישראל</p>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("---")

    today = datetime.now()
    df = load_data(data_source="latest_file")

    st.caption(f"עדכון אחרון: {today.strftime('%Y-%m-%d %H:%M')}")
    st.caption(f"סה\"כ רשומות במאגר: {len(df):,}")


# ============================================================================
# FILTER TO ACTIVE TENDERS ONLY
# ============================================================================

active_df = df[~df['status'].isin(NON_ACTIVE_STATUSES)].copy()


# ============================================================================
# HEADER
# ============================================================================

st.title("📊 סקירה ניהולית")
st.caption(f"תמונת מצב מכרזי קרקע  •  {today.strftime('%d/%m/%Y')}")

st.markdown("---")


# ============================================================================
# KPIs WITH DELTAS
# ============================================================================

# Calculate "new this week" delta
week_ago = today - timedelta(days=7)
two_weeks_ago = today - timedelta(days=14)

date_col = None
for candidate in ['created_date', 'publish_date', 'published_date']:
    if candidate in active_df.columns:
        date_col = candidate
        break

new_this_week = 0
new_last_week = 0
if date_col:
    new_this_week = len(active_df[active_df[date_col] >= week_ago])
    new_last_week = len(
        active_df[
            (active_df[date_col] >= two_weeks_ago) &
            (active_df[date_col] < week_ago)
        ]
    )

col1, col2, col3, col4 = st.columns(4)

with col1:
    delta = new_this_week - new_last_week if date_col else None
    delta_str = f"{delta:+d} מהשבוע שעבר" if delta is not None else None
    st.metric("🟢 מכרזים פעילים", f"{len(active_df):,}", delta=delta_str)

with col2:
    total_units = int(active_df['units'].sum())
    st.metric("🏠 סה\"כ יח\"ד", f"{total_units:,}")

with col3:
    unique_cities = active_df['city'].nunique()
    st.metric("🏙️ ערים", f"{unique_cities}")

with col4:
    closing_14 = len(active_df[
        (active_df['deadline'].notna()) &
        (active_df['deadline'] >= today) &
        (active_df['deadline'] <= today + timedelta(days=CLOSING_SOON_DAYS))
    ])
    st.metric(f"⏰ נסגרים ב-{CLOSING_SOON_DAYS} יום", closing_14)

st.markdown("---")


# ============================================================================
# TWO PIE CHARTS
# ============================================================================

PLOTLY_FONT = dict(family="DM Sans, sans-serif", size=12, color="#2B3674")
PLOTLY_TRANSPARENT_BG = dict(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")

col_pie1, col_pie2 = st.columns(2)

# ── Brochure availability ────────────────────────────────────────────────
with col_pie1:
    st.markdown('<p class="pie-title">📋 חוברת מכרז</p>', unsafe_allow_html=True)

    if 'published_booklet' in active_df.columns and len(active_df) > 0:
        booklet_counts = active_df['published_booklet'].value_counts()
        available = int(booklet_counts.get(True, 0))
        not_available = int(booklet_counts.get(False, 0))

        pct = (available / len(active_df) * 100) if len(active_df) > 0 else 0

        fig_booklet = px.pie(
            values=[available, not_available],
            names=["חוברת זמינה", "חוברת לא זמינה"],
            color_discrete_sequence=["#4318FF", "#E9EDF7"],
            hole=0.55,
        )
        fig_booklet.update_traces(
            textinfo='value',
            textposition='inside',
            textfont_size=14,
            hovertemplate='%{label}: %{value} (%{percent})<extra></extra>',
        )
        fig_booklet.update_layout(
            height=350,
            margin=dict(t=30, b=50, l=20, r=20),
            legend=dict(
                orientation="h", yanchor="top", y=-0.08,
                xanchor="center", x=0.5, font=dict(size=11),
            ),
            showlegend=True,
            font=PLOTLY_FONT,
            uniformtext_minsize=10, uniformtext_mode='hide',
            **PLOTLY_TRANSPARENT_BG,
        )
        st.plotly_chart(fig_booklet, use_container_width=True, key="mgmt_pie_booklet")
        st.caption(f"כיסוי חוברות: {pct:.0f}% מהמכרזים הפעילים")
    else:
        st.info("אין נתוני חוברת מכרז")

# ── Tenders by region ────────────────────────────────────────────────────
with col_pie2:
    st.markdown('<p class="pie-title">🗺️ מכרזים לפי מחוז</p>', unsafe_allow_html=True)

    if 'region' in active_df.columns and len(active_df) > 0:
        tenders_by_region = (
            active_df.groupby('region')
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
                color_discrete_sequence=px.colors.sequential.Blues_r,
            )
            fig_region.update_traces(
                textinfo='value',
                textposition='inside',
                textfont_size=14,
                hovertemplate='%{label}: %{value} מכרזים (%{percent})<extra></extra>',
            )
            fig_region.update_layout(
                height=350,
                margin=dict(t=30, b=50, l=10, r=10),
                legend=dict(
                    orientation="h", yanchor="top", y=-0.08,
                    xanchor="center", x=0.5, font=dict(size=11),
                ),
                showlegend=True,
                uniformtext_minsize=10, uniformtext_mode='hide',
                font=PLOTLY_FONT,
                **PLOTLY_TRANSPARENT_BG,
            )
            st.plotly_chart(fig_region, use_container_width=True, key="mgmt_pie_region")
        else:
            st.info("אין נתוני אזור")
    else:
        st.info("אין נתוני אזור")

st.markdown("---")


# ============================================================================
# CLOSING SOON TABLE (top 20)
# ============================================================================

st.subheader("⏰ מכרזים קרובים לסגירה — Top 20")

EXCLUDED_STATUSES = {"בוטל", "נסגר"}
upcoming = active_df[
    (active_df['deadline'].notna()) &
    (active_df['deadline'] >= today) &
    (~active_df['status'].isin(EXCLUDED_STATUSES))
].sort_values('deadline').head(20)

if len(upcoming) > 0:
    upcoming_display = upcoming[[
        'tender_id', 'tender_name', 'city', 'region',
        'units', 'deadline', 'published_booklet'
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

    display_table = upcoming_display[[
        'urgency', 'tender_id', 'tender_name', 'city', 'region',
        'units', 'deadline', 'days_left', 'booklet'
    ]].copy()
    display_table['deadline'] = display_table['deadline'].dt.strftime('%d/%m/%Y')

    st.dataframe(
        display_table,
        column_config={
            "urgency": st.column_config.TextColumn("", width="small"),
            "tender_id": st.column_config.NumberColumn("מס' מכרז", format="%d"),
            "tender_name": st.column_config.TextColumn("שם", width="medium"),
            "city": st.column_config.TextColumn("עיר", width="medium"),
            "region": st.column_config.TextColumn("מחוז", width="small"),
            "units": st.column_config.NumberColumn("יח\"ד", format="%d"),
            "deadline": st.column_config.TextColumn("מועד סגירה"),
            "days_left": st.column_config.NumberColumn("ימים", format="%d"),
            "booklet": st.column_config.TextColumn("חוברת", width="small"),
        },
        hide_index=True,
        use_container_width=True,
    )
else:
    st.info("אין מכרזים קרובים לסגירה.")
