# STATUS.md — Project State

**Last updated:** 2026-02-22 (session 5)

---

## Current State

Sprint 1 (Stabilize & Deploy MVP) — **complete**.
Sprint 3 (SQLite Data Persistence) — **complete** → superseded by Sprint 6.
Sprint 5 (Watchlist & Email Alerts) — **complete** (deployed to Streamlit Cloud, SMTP pending).
Sprint 6 (Full Supabase Migration) — **complete** (pending: run SQL schema + migration script + add GitHub secrets).
Management Page Redesign (Features #1-4) — **complete**.
MEGIDO Brand Redesign — **complete**.

**All data now lives in Supabase PostgreSQL.** SQLite (`data/tenders.db`) is no longer used by the app and has been added to `.gitignore`.

The app is now **multipage** with two views:
- **Dashboard** (`pages/dashboard.py`) — Full view for daily users: filters, KPIs, charts, tender details, watchlist management (with autocomplete), team watchlist controls (sidebar), review status editing, analytics, debug
- **Management** (`pages/management.py`) — Team operational dashboard (read-only):
  1. **Selected Tenders** — shared team watchlist with review status display
  2. **Closing Soon** — active tenders closing within 14 days, with popup detail dialog
  3. **Tender Type Tabs** — dedicated views for "מכרז ייזום" and "דיור להשכרה"
  4. **Compact KPIs** — single row with key metrics

Review tracking has 5 stages: לא נסקר → סקירה ראשונית → בדיקה מעמיקה → הוצג בפורום → אושר בפורום. Editing is in the Dashboard (requires login). Management is read-only.

Alert system (`alerts.py`) runs in the daily GitHub Actions cron after document sync. Sends Hebrew RTL HTML emails via SMTP2GO when new documents appear on watched tenders.

**To activate (one-time setup)**:
1. Run the SQL schema in Supabase SQL Editor (creates tables + indexes + GRANTs)
2. Run `scripts/sql/building_rights_schema.sql` in Supabase SQL Editor (adds `plan_number` column + `building_rights` table + brochure/extraction columns)
3. Run `python scripts/migrate_sqlite_to_supabase.py` to migrate existing data
4. Add `SUPABASE_URL` + `SUPABASE_KEY` to GitHub repo secrets
5. Add `SMTP_USER` + `SMTP_PASSWORD` to GitHub repo secrets
6. Add Supabase + SMTP secrets to Streamlit Cloud secrets
7. Create a GitHub PAT with `actions:write` scope and add as `GH_PAT` to Streamlit Cloud secrets

---

## Recent Changes

| Date | Change | Files |
|------|--------|-------|
| 2026-02-22 | **On-demand building rights UI** — dashboard button triggers brochure analysis (immediate) + GitHub Actions extraction (5-10 min). Shows brochure summary, lots table, building rights table with status tracking. | `brochure_analyzer.py` (NEW), `pages/dashboard.py`, `dashboard_utils.py`, `db.py`, `.github/workflows/extract_building_rights.yml` (NEW), `scripts/sql/building_rights_schema.sql`, `scripts/extract_building_rights_batch.py` |
| 2026-02-20 | **Building rights batch pipeline** — end-to-end: brochure → plan number → Mavat download → Section 5 extraction → Supabase. Runs in daily cron + CLI. SQL schema file included. | `scripts/extract_building_rights_batch.py` (NEW), `scripts/sql/building_rights_schema.sql` (NEW), `.github/workflows/daily_refresh.yml`, `db.py` |
| 2026-02-20 | **Building rights extractor** — extract Section 5 tables from Mavat plan PDFs. Multi-level header merging, Hebrew RTL handling, multi-page continuation, Supabase storage. 36 tests pass. | `building_rights_extractor.py` (NEW), `mavat_plan_extractor.py`, `db.py`, `test_building_rights.py` (NEW) |
| 2026-02-19 | **Sprint 6: Full Supabase migration** — rewrite db.py from SQLite to Supabase REST API, migration script, fix AlertEngine bug, update CI workflow | `db.py`, `scripts/migrate_sqlite_to_supabase.py` (NEW), `scripts/refresh_tenders.py`, `.github/workflows/daily_refresh.yml`, `user_db.py`, `dashboard_utils.py`, `.gitignore` |
| 2026-02-19 | Move team watchlist + review editing to Dashboard; Management now read-only | `pages/dashboard.py`, `pages/management.py` |
| 2026-02-19 | Supabase persistence — user_watchlist, tender_reviews, alert_history now in Supabase PostgreSQL | `user_db.py` (NEW), `config.py`, `requirements.txt`, `pages/dashboard.py`, `pages/management.py`, `alerts.py`, `db.py` |
| 2026-02-19 | Fix: complete PURPOSE_MAP (26 codes from API table -1), restore dataframe column filtering (narrow CSS/JS) | `data_client.py`, `app.py`, `data/tenders.db` |
| 2026-02-19 | Fix: st.experimental_user → st.user + sidebar email fallback for Streamlit Cloud auth | `dashboard_utils.py` |
| 2026-02-19 | MEGIDO rebrand — dark & modern executive UI, navy+gold palette, Inter/Heebo fonts, dark sidebar, gold accent cards, chart restyling | `app.py`, `.streamlit/config.toml`, `pages/dashboard.py`, `pages/management.py`, `assets/` (NEW) |
| 2026-02-18 | Feature #4: Tender type tabs — dedicated views for מכרז ייזום + דיור להשכרה | `pages/management.py`, `config.py` |
| 2026-02-18 | Feature #3: Close deadline popup — @st.dialog modal for tender details | `pages/management.py` |
| 2026-02-18 | Feature #2: Review status tracking — 5-stage workflow, any team member can update | `db.py`, `pages/management.py` |
| 2026-02-18 | Feature #1: Selected tenders — shared team watchlist at top of management page | `pages/management.py`, `config.py`, `db.py` |
| 2026-02-18 | Watchlist autocomplete — selectbox with tender_name + city search | `pages/dashboard.py` |
| 2026-02-18 | Config: added TEAM_EMAIL, expanded RELEVANT_TENDER_TYPES to include types 6+9 | `config.py` |
| 2026-02-17 | Sprint 5: Multipage app — restructured into navigation router + 2 pages | `app.py`, `pages/dashboard.py` (NEW), `pages/management.py` (NEW), `dashboard_utils.py` (NEW) |
| 2026-02-17 | Sprint 5: Watchlist UI — add/remove tenders, validated against DB, per-user | `pages/dashboard.py`, `db.py` |
| 2026-02-17 | Sprint 5: Alert engine — detect new docs, compose Hebrew HTML email, send via M365 SMTP | `alerts.py` (NEW) |
| 2026-02-17 | Sprint 5: DB schema — user_watchlist + alert_history tables with dedup indexes | `db.py` |
| 2026-02-17 | Sprint 5: SMTP config + build_document_url extraction | `config.py`, `data_client.py` |
| 2026-02-17 | Sprint 5: Cron integration — alert check after doc sync (non-fatal) | `scripts/refresh_tenders.py` |
| 2026-02-17 | Sprint 5: GitHub Actions — pass M365 secrets as env vars | `.github/workflows/daily_refresh.yml` |
| 2026-02-17 | Sprint 3: SQLite database layer — TenderDB class with schema, upsert, queries | `db.py` (NEW), `config.py` |
| 2026-02-17 | Sprint 3: Migration script — replay JSON snapshots + cached details into DB | `scripts/migrate_json_to_db.py` (NEW) |
| 2026-02-17 | Sprint 3: DB persistence in data_client — save_to_db(), sync_documents_to_db() | `data_client.py` |
| 2026-02-17 | Sprint 1: Config management — extract hardcoded values into `config.py` | `config.py` (NEW), `app.py`, `data_client.py` |
| 2026-02-17 | Sprint 1: GitHub Actions daily refresh cron job | `.github/workflows/daily_refresh.yml` (NEW), `scripts/refresh_tenders.py` (NEW) |

---

## Known Issues

1. **No tests** — No test suite exists. pytest tests should be added for data_client, db, and alerts modules.
2. **Date range filter removed** — The urgency toggle replaces the old date range picker. May want to add it back as an "advanced" option.
3. **Pie chart click-to-filter** — Plotly click events don't wire easily to Streamlit filters. Deferred.
4. **Streamlit Cloud auth** — Viewer auth not enforced. Using sidebar email input as fallback (works but self-reported).
5. **SMTP not configured** — Need working SMTP credentials (SMTP2GO) for alert emails.
6. **Supabase setup pending** — Need to run SQL schema creation + GRANT SQL + migrate data before app will load from Supabase.

---

## Next Steps

1. **Run building rights SQL schema** — Execute `scripts/sql/building_rights_schema.sql` in Supabase SQL Editor (adds `plan_number`, `building_rights` table, brochure columns).
2. **Create GitHub PAT** — Create a PAT with `actions:write` scope, add as `GH_PAT` to Streamlit Cloud secrets.
3. **Test building rights flow** — Click "נתח זכויות בנייה" in a tender detail view, verify brochure summary appears and GH Actions triggers.
4. **Sprint 4** — Analytical engine: scoring + market trends.
5. **WhatsApp API** — Integrate WhatsApp Business API for review status notifications.

---

## Database Schema (Supabase PostgreSQL)

```
-- Tender data (managed by db.py)
tenders            — ~10,447 rows — current state of each tender
tender_history     — ~30,997 rows — daily snapshots for trend analysis
tender_documents   —  ~3,471 rows — document metadata from 444 tenders
building_rights    — extracted Section 5 data from Mavat plan PDFs (NEW, needs SQL creation)

-- User data (managed by user_db.py)
user_watchlist     — per-user tender watchlist for email alerts
tender_reviews     — review status tracking (5-stage workflow)
alert_history      — sent alert log for deduplication
```

---

## Project Structure

```
Gov tender projects/
├── app.py                          # Multipage navigation router + shared CSS
├── config.py                       # Centralized configuration (API, SMTP, Supabase, paths)
├── db.py                           # Supabase database layer (tender data: tenders, history, documents)
├── user_db.py                      # Supabase client: watchlist, reviews, alert_history
├── data_client.py                  # API client, normalization, caching, DB persistence
├── dashboard_utils.py              # Shared data loading functions for pages
├── alerts.py                       # Email alert engine: watchlist → SMTP
├── tender_pdf_extractor.py         # PDF extraction: גוש, חלקה, תב"ע from brochure PDFs
├── brochure_analyzer.py             # On-demand brochure analysis + GitHub Actions trigger
├── building_rights_extractor.py    # PDF extraction: Section 5 building rights from Mavat plans
├── mavat_client.py                 # Playwright client: search plans on mavat.iplan.gov.il
├── mavat_plan_extractor.py         # Coordinator: download + extract from Mavat plan PDFs
├── test_pdf_extractor.py           # Test script for PDF extractor (2 sample PDFs)
├── test_pdf_extractor_batch.py     # Batch test: download + extract from N tender brochures
├── test_building_rights.py         # Tests for building rights extractor (36 tests)
├── requirements.txt                # Pinned Python dependencies
├── complete_city_codes.py          # CBS settlement code → city name mapping (1,281 entries)
├── complete_city_regions.py        # CBS settlement code → region mapping (1,488 entries)
├── CLAUDE.md                       # Project rules and guidelines
├── PRD.md                          # Product Requirements Document v3.0
├── STATUS.md                       # This file — living project state
├── DATA_FLOW_EXPLANATION.md        # Data pipeline documentation
├── .gitignore                      # Git ignore rules
├── assets/                         # Brand assets (logo, images)
│   └── logo megido.jpg             # MEGIDO BY AURA brand logo
├── pages/                          # Streamlit multipage app pages
│   ├── dashboard.py                # Full dashboard: filters, KPIs, charts, details, watchlist, review editing
│   └── management.py               # Team dashboard (read-only): watchlist, review display, type tabs, KPIs
├── .streamlit/
│   └── config.toml                 # Streamlit theme + server config
├── .github/
│   └── workflows/
│       ├── daily_refresh.yml       # GitHub Actions: daily refresh + alert emails
│       └── extract_building_rights.yml  # On-demand building rights extraction (workflow_dispatch)
├── scripts/
│   ├── refresh_tenders.py          # Data refresh script (used by cron)
│   ├── extract_building_rights_batch.py  # Batch pipeline: brochure → plan → Mavat → extract → Supabase
│   ├── migrate_json_to_db.py       # One-time migration: JSON → SQLite (historical)
│   ├── migrate_sqlite_to_supabase.py  # One-time migration: SQLite → Supabase (Sprint 6)
│   └── sql/
│       └── building_rights_schema.sql  # SQL: plan_number column + building_rights table
├── tenders_list_*.json             # Daily API snapshots (JSON backup)
├── data/
│   ├── tenders.db                  # SQLite database (gitignored, kept for migration reference)
│   └── details_cache/              # Cached tender detail JSON files
├── tmp/                            # Temporary files (gitignored)
└── venv/                           # Python virtual environment (gitignored)
```
