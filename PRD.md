# PRD — Israel Land Tender Intelligence Dashboard

**Version**: 2.0  
**Author**: Nathanael (Product Owner)  
**Last Updated**: February 11, 2026  
**Status**: Draft — Pending Review

---

## 1. Background & Context

Israel's Land Authority (רשות מקרקעי ישראל / רמ"י) publishes land tenders for residential and commercial development through its public portal at `apps.land.gov.il/MichrazimSite`. These tenders represent significant investment opportunities — each one includes metadata such as location, closing date, number of housing units (יח"ד), tender type, and whether a tender brochure (חוברת מכרז) has been published.

**A working dashboard already exists.** Built in Streamlit, it fetches live data from the רמ"י API, displays KPIs, charts, a filterable data table, and a tender detail viewer with document listings. The data pipeline is functional with ~10,448 records and 632 active tenders.

This PRD defines the next evolution: reshaping the existing dashboard into an **executive-grade decision tool** for a real estate CEO, adding missing analytical views, and later integrating planning documents from mavat.iplan.gov.il.

---

## 2. Problem Statement

The current dashboard is a capable data explorer, but it was built as a development/analysis tool, not an executive decision-making interface. Specifically:

1. **No brochure readiness signal** — There's no way to see at a glance which tenders have a published חוברת מכרז (actionable) vs. those that don't (not yet evaluable). The `PublishedChoveret` field exists in the data but isn't visualized.
2. **No regional unit distribution** — The dashboard shows tenders by city and units by type, but not **how many housing units are distributed across regions (מחוז)** — a key strategic metric for deciding where to focus.
3. **No urgency quick-toggle** — The date range picker works, but a CEO needs one-click access to "what's closing this week / this month" without configuring date ranges.
4. **Information hierarchy is flat** — KPIs, charts, tables, and detail views are stacked vertically with equal visual weight. An executive needs the most critical signals at the top, with progressive detail below.
5. **No path from tender to planning documents** — Connecting to mavat.iplan.gov.il for brochure PDFs is manual.

---

## 3. Product Vision

Reshape the existing Streamlit dashboard into a focused executive view where a CEO can assess the tender landscape in 30 seconds, drill into specifics in 2 minutes, and — in a later phase — access extracted data from planning documents without leaving the dashboard.

---

## 4. Target User

**Primary user**: CEO of a real estate development company.

This person needs high-level signals, not raw data. They make decisions based on region, timing, and scale (number of units). They may share the dashboard with CFO or investment committee. Usage is daily to weekly, spiking around tender deadlines.

---

## 5. What Already Exists

The following features are **already built and working** in the current Streamlit app:

| Feature | Status | Notes |
|---------|--------|-------|
| Live API data fetch from רמ"י | ✅ Working | 3 data source modes: JSON file, Live API, Sample Data |
| KPI cards (Active Tenders, Total Units, Cities, Closing Soon 14d) | ✅ Working | |
| Sidebar filters (Region, City, Type, Status, Date Range) | ✅ Working | |
| Tenders by City — horizontal bar chart | ✅ Working | Color-coded by count |
| Tenders by Type — donut chart | ✅ Working | מגורים, אחר, מסחרי, תעשוקה |
| Tenders Over Time — line chart | ✅ Working | Monthly trend since 2000 |
| Housing Units by Type — bar chart | ✅ Working | |
| Upcoming Deadlines section | ⚠️ Bug | Shows "No upcoming deadlines found" — likely a date filter or field mapping issue |
| All Tenders Data table | ✅ Working | Column selector, search, CSV export |
| Tender Detail Viewer | ✅ Working | Dropdown select, full metadata, documents list |
| Documents listing per tender | ✅ Working | Shows PDFs including חוברת המכרז with timestamps |
| Link to official רמ"י page | ✅ Working | |
| Raw API Response (debug) | ✅ Working | Expandable JSON viewer |
| Configuration & API Status | ✅ Working | |

**Total records**: ~10,448 | **Last updated**: 2026-02-11 09:56

---

## 6. User Stories — Enhancements

### Phase 1 — Executive Redesign (Streamlit)

| ID | Story | Priority |
|----|-------|----------|
| US-1 | As a CEO, I want a **brochure availability pie chart** showing how many open tenders have a published חוברת מכרז vs. those that don't, so I know at a glance which are actionable. | Must Have |
| US-2 | As a CEO, I want a **units by region pie chart** showing how יח"ד are distributed across מחוז regions, so I can see where the supply is. | Must Have |
| US-3 | As a CEO, I want **1-week / 2-week / 4-week quick toggles** in the sidebar that instantly filter to tenders closing within that window, so I can prioritize by urgency. | Must Have |
| US-4 | As a CEO, I want the **main view redesigned with clear information hierarchy**: executive summary at top (KPIs + the two new pie charts), then the urgency-filtered table, then detailed explorer below. | Must Have |
| US-5 | As a CEO, I want clicking a **pie chart segment to filter the table** (e.g., click a region → table shows only that region's tenders). | Should Have |
| US-6 | As a CEO, I want the **table to default-sort by closing date** (soonest first) and **visually highlight** tenders closing within 7 days. | Must Have |
| US-7 | As a CEO, I want the **Upcoming Deadlines section to actually work** — it currently shows "No upcoming deadlines found" which seems like a bug. | Must Have |
| US-8 | As a CEO, I want the **dashboard to feel polished** — consistent styling, readable at presentation distance, no debug/dev elements in the main view. | Should Have |

### Phase 2 — mavat.iplan.gov.il Integration

| ID | Story | Priority |
|----|-------|----------|
| US-9 | As a CEO, I want the system to **automatically look up a tender's plan number** on mavat.iplan.gov.il. | Must Have |
| US-10 | As a CEO, I want the system to **find and download the חוברת מכרז PDF** from the planning portal. | Must Have |
| US-11 | As a CEO, I want **key data extracted from the PDF** and displayed in the tender detail view (development conditions, timelines, special requirements). | Should Have |

### Phase 3 — React Migration (Future)

| ID | Story | Priority |
|----|-------|----------|
| US-12 | As a product owner, I want the dashboard **rebuilt in React** for better performance, custom UI, and easier deployment with access controls. | Future |
| US-13 | As a user, I want the dashboard accessible via a **shared URL with authentication**. | Future |

---

## 7. Feature Specification — Phase 1

### 7.1 Redesigned Main View Layout

The current vertical stack needs to be reorganized into a clear information hierarchy:

```
┌─────────────────────────────────────────────────────────┐
│  HEADER: מכרזי קרקע · Last Updated · Data Source        │
├──────────┬──────────────────────────────────────────────┤
│          │                                              │
│  SIDEBAR │  SECTION 1: Executive KPIs                   │
│          │  [Active Tenders] [Total Units] [Cities]     │
│  Urgency │  [Closing Soon — dynamic per toggle]         │
│  Toggle  │                                              │
│  ○ 1 wk  │──────────────────────────────────────────────│
│  ○ 2 wks │                                              │
│  ○ 4 wks │  SECTION 2: Two Pie Charts (side by side)   │
│  ───────  │  ┌──────────────┐  ┌──────────────┐        │
│  Filters │  │  Brochure    │  │  Units by    │        │
│  Region  │  │  Availability│  │  Region      │        │
│  City    │  └──────────────┘  └──────────────┘        │
│  Type    │                                              │
│  Status  │──────────────────────────────────────────────│
│          │                                              │
│          │  SECTION 3: Upcoming Deadlines Table         │
│          │  (filtered by urgency toggle)                │
│          │  Sorted by closing date, highlighted rows    │
│          │                                              │
│          │──────────────────────────────────────────────│
│          │                                              │
│          │  SECTION 4: Full Data Explorer               │
│          │  (existing table + column selector + search) │
│          │                                              │
│          │──────────────────────────────────────────────│
│          │                                              │
│          │  SECTION 5: Tender Detail Viewer             │
│          │  (existing detail view + documents)          │
│          │                                              │
│          │──────────────────────────────────────────────│
│          │                                              │
│          │  SECTION 6 (collapsed): Detailed Analytics   │
│          │  Tenders by City | Over Time | Units by Type │
│          │                                              │
│          │──────────────────────────────────────────────│
│          │                                              │
│          │  SECTION 7 (collapsed): Admin/Debug          │
│          │  Raw API Response | Config & API Status      │
│          │                                              │
└──────────┴──────────────────────────────────────────────┘
```

**Key changes from current layout:**
- **Elevate** the two new pie charts to the top section alongside KPIs.
- **Merge** the "Upcoming Deadlines" and the data table into a clearer flow: urgency-filtered view first, full explorer below.
- **Move** analytical charts (Tenders by City, Over Time, Units by Type) to a collapsible "📊 Detailed Analytics" section.
- **Move** debug elements (Raw API Response, Configuration & API Status) to a collapsible "🔧 Admin/Debug" section at the bottom.
- **Consider** making Live API the default data source for production use.

### 7.2 Sidebar — Urgency Quick Toggle

Add a new section at the top of the sidebar, above the existing filters:

- **Label**: "⏰ Closing Window"
- **Widget**: `st.radio` with options: "1 שבוע", "2 שבועות", "4 שבועות", "הכל"
- **Default**: "4 שבועות"
- **Behavior**: Filters the entire dashboard (KPIs, pie charts, tables) to show only tenders with deadline within the selected window from today
- **Show count** next to each option: "1 שבוע (3)"
- This filter works **in addition to** the existing Region/City/Type/Status filters (AND logic)

### 7.3 Pie Chart 1 — Brochure Availability (חוברת מכרז)

- **Data source**: `PublishedChoveret` field (boolean or equivalent — agent must verify actual field name and type in codebase)
- **Two segments**: "חוברת זמינה" (available) / "חוברת לא זמינה" (not available)
- **Display**: Count + percentage label on each segment
- **Interaction**: Click segment → filter the table below to show only matching tenders
- **Colors**: Green for available, gray for not available
- **Responds to**: Urgency toggle and sidebar filters

### 7.4 Pie Chart 2 — Housing Units by Region (יח"ד לפי מחוז)

- **Data source**: Sum of units (יח"ד) field, grouped by region (מחוז) — agent must verify actual field names
- **Segments**: One per region, sized by total units
- **Display**: Region name + total units in label/tooltip
- **Interaction**: Click segment → filter the table to that region
- **Colors**: Distinct, accessible palette per region (consistent across the dashboard)
- **Responds to**: Urgency toggle and sidebar filters

### 7.5 Upcoming Deadlines Table (Enhanced)

This replaces the current broken "Upcoming Deadlines" section.

- **Source**: Same data, filtered by the urgency toggle (1/2/4 weeks)
- **Default sort**: Closing date ascending (soonest first)
- **Columns**: Tender ID, Tender Name, City, Region, Type, Units, Closing Date, Days Remaining, Brochure Status
- **Conditional formatting**:
  - Closing within 7 days → red highlight
  - Closing within 14 days → amber highlight
  - Has brochure → green checkmark
- **Row count badge**: "Showing X tenders closing within Y"
- **Click row**: Scroll to or populate the Tender Detail Viewer below

### 7.6 Existing Features — Keep but Reorganize

| Feature | Action |
|---------|--------|
| Tenders by City (bar chart) | Move to collapsible "📊 Detailed Analytics" section |
| Tenders by Type (donut chart) | Move to collapsible "📊 Detailed Analytics" section |
| Tenders Over Time (line chart) | Move to collapsible "📊 Detailed Analytics" section |
| Housing Units by Type (bar chart) | Move to collapsible "📊 Detailed Analytics" section |
| All Tenders Data table | Keep in Section 4, below the urgency table |
| Tender Detail Viewer | Keep in Section 5 |
| Raw API Response | Move to "🔧 Admin/Debug" expander |
| Configuration & API Status | Move to "🔧 Admin/Debug" expander |
| Data Source radio buttons | Keep in sidebar, consider Live API as default |

---

## 8. Technical Requirements

### 8.1 Stack (Current — Phase 1)

| Layer | Technology | Status |
|-------|-----------|--------|
| Frontend | Streamlit | Existing |
| Data Fetching | Python (requests/httpx) | Existing |
| Charts | Plotly (via Streamlit) | Existing |
| Data Processing | Pandas | Existing |
| Deployment | Local | Current |

### 8.2 Stack (Future — Phase 3: React Migration)

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| Frontend | React + Recharts/Plotly.js | Custom UI, better performance, shareable URL |
| Backend API | FastAPI (Python) | Serve data to React frontend |
| Auth | TBD (basic auth → OAuth) | Restrict dashboard access |
| Deployment | TBD (cloud hosting) | Shareable URL |

### 8.3 Non-Functional Requirements

| Requirement | Target |
|-------------|--------|
| Page load (Streamlit) | < 5 seconds with cached data |
| Data freshness | Updated at least once every 24 hours |
| Language | Hebrew UI, RTL layout throughout |
| Visual quality | Readable at presentation/projector distance |
| Deployment (now) | Local |
| Deployment (later) | Shareable URL with access restrictions |

---

## 9. Phase 2 — mavat.iplan.gov.il Integration

### 9.1 Workflow

For each tender in the dashboard:

1. Extract the plan/tender number from the רמ"י data
2. Search on `mavat.iplan.gov.il/SV3?text=<tender_number>`
3. Navigate results to find the correct plan
4. Locate the חוברת מכרז PDF in the plan's document list
5. Download the PDF
6. Extract structured data from the PDF
7. Store extracted data and display it in the Tender Detail Viewer

### 9.2 PDF Data Extraction

**Target document**: חוברת מכרז (Tender Brochure)

Data to extract (to be refined with sample documents from Nathanael):
- Development conditions and restrictions
- Timeline requirements
- Special obligations (affordable housing quotas, public spaces, etc.)
- Financial terms
- Zoning specifics

**Technical approach**: Python-based (pdfplumber / PyMuPDF). Government PDF formats vary — extraction rules will be built incrementally, starting with the most common format. Low-confidence extractions flagged for manual review.

### 9.3 Dashboard Additions (Phase 2)

- New indicator in the Tender Detail Viewer: "Planning Documents" status
- Extracted data summary shown in the detail view
- Direct download link to the original PDF

> **Note**: The current dashboard already lists documents per tender (including חוברת המכרז.pdf, תשריטים.pdf, פרסום ראשון.pdf, etc.). Phase 2 extends this by cross-referencing with mavat.iplan.gov.il and extracting content from the PDFs.

---

## 10. Roadmap

### Phase 1 — Executive Redesign (Streamlit)
**Estimated duration**: 1–2 weeks

| Step | Task | Priority |
|------|------|----------|
| 1.1 | **Inspect existing codebase** — Read all files, understand data schema, field names, current architecture | First |
| 1.2 | **Fix Upcoming Deadlines** — Debug why it shows "No upcoming deadlines found" | Must Have |
| 1.3 | **Add urgency quick toggle** — 1/2/4 week radio in sidebar | Must Have |
| 1.4 | **Add brochure availability pie chart** — PublishedChoveret field | Must Have |
| 1.5 | **Add units by region pie chart** — Units grouped by מחוז | Must Have |
| 1.6 | **Redesign layout** — Reorder sections per the hierarchy in 7.1 | Must Have |
| 1.7 | **Enhance table** — Default sort by deadline, conditional row highlighting | Must Have |
| 1.8 | **Relocate analytical charts** — Move to collapsible section | Should Have |
| 1.9 | **Relocate debug elements** — Move to admin expander | Should Have |
| 1.10 | **Visual polish** — Consistent colors, executive-friendly styling | Should Have |
| 1.11 | **Pie chart click-to-filter** — Interactive filtering from chart segments | Nice to Have |

### Phase 2 — Planning Document Integration
**Estimated duration**: 3–4 weeks

| Step | Task |
|------|------|
| 2.1 | Map mavat.iplan.gov.il search/navigation flow |
| 2.2 | Build automated search by tender number |
| 2.3 | PDF download pipeline |
| 2.4 | PDF content extraction |
| 2.5 | Integrate extracted data into Tender Detail Viewer |
| 2.6 | Validate across diverse brochure formats |

### Phase 3 — React Migration (Future)
**Estimated duration**: 4–6 weeks

| Step | Task |
|------|------|
| 3.1 | Design React component architecture based on finalized Streamlit layout |
| 3.2 | Build FastAPI backend to serve tender data |
| 3.3 | Implement React frontend with all Phase 1+2 features |
| 3.4 | Add authentication layer |
| 3.5 | Deploy to cloud with shareable URL |

---

## 11. Success Metrics

| Metric | Target | How to Measure |
|--------|--------|---------------|
| Time-to-insight | CEO answers "what's closing this week" in < 30 seconds | Qualitative test |
| Data accuracy | 100% match with רמ"י website | Spot-check 10 random tenders weekly |
| Data freshness | < 24 hours old | Timestamp comparison |
| Brochure chart accuracy | Matches actual PublishedChoveret values | Compare chart totals with raw data |
| Region chart accuracy | Sum of units per region = total units KPI | Automated check |
| Upcoming Deadlines | Shows actual upcoming tenders (bug fixed) | Manual verification |
| PDF extraction accuracy (Phase 2) | > 90% of key fields correctly extracted | Validation against source PDFs |

---

## 12. Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|-----------|------------|
| **API changes without notice** | High | Medium | Monitoring script that alerts on schema changes. Defensive parsing. |
| **Agent ignores existing code** | High | Medium | CLAUDE.md and PRD explicitly instruct to inspect codebase first. STATUS.md documents what exists. |
| **Streamlit performance at scale** | Medium | Medium | Cache aggressively with `st.cache_data`. Limit default data window. |
| **Pie chart interactivity limits** | Medium | High | Plotly supports click events but wiring to Streamlit filters requires `st.session_state` workarounds. Accept as Streamlit limitation, resolve in React. |
| **PDF format inconsistency (Phase 2)** | High | High | Build incrementally. Flag low-confidence extractions. |
| **Deployment security (Phase 3)** | Medium | Medium | Plan auth before deploying. Basic auth minimum. |

---

## 13. Open Questions

1. ~~What is the exact API structure?~~ → ✅ Resolved — pipeline exists and works
2. ~~What specific fields are available?~~ → ✅ Resolved — field names mapped in codebase
3. **Why does "Upcoming Deadlines" show no results?** → Debug in Step 1.2
4. **What is the exact field name/type for brochure availability?** → Agent must inspect actual data
5. **How are tender numbers formatted for mavat.iplan.gov.il lookup?** → Investigate in Phase 2
6. **What does the חוברת מכרז PDF typically look like?** → Nathanael to provide samples before Phase 2
7. **Should "Closing Soon" KPI dynamically respond to the urgency toggle?** → Recommended yes

---

## 14. Glossary

| Term | Hebrew | Meaning |
|------|--------|---------|
| רמ"י | רשות מקרקעי ישראל | Israel Land Authority |
| מכרז | — | Tender |
| חוברת מכרז | — | Tender brochure / information document |
| יח"ד | יחידות דיור | Housing units |
| מחוז | — | Region / district |
| יישוב | — | City / settlement |
| תב"ע | תוכנית בניין עיר | Statutory urban building plan |
| mavat / מבא"ת | מידע בנושא אישורים ותכניות | Planning information portal |

---

_End of PRD v2.0_
