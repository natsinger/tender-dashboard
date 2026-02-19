# STATUS.md — Project State

**Last updated:** 2026-02-19 (session 2)

---

## Current State

Sprint 1 (Stabilize & Deploy MVP) — **complete**.
Sprint 3 (SQLite Data Persistence) — **complete**.
Sprint 5 (Watchlist & Email Alerts) — **complete** (deployed to Streamlit Cloud, SMTP pending).
Management Page Redesign (Features #1-4) — **complete**.
MEGIDO Brand Redesign — **complete**.
Supabase Integration (user data persistence) — **complete** (watchlist, reviews, alert_history).

The app is now **multipage** with two views:
- **Dashboard** (`pages/dashboard.py`) — Full view for daily users: filters, KPIs, charts, tender details, watchlist management (with autocomplete), analytics, debug
- **Management** (`pages/management.py`) — Team operational dashboard:
  1. **Selected Tenders** — shared team watchlist with review status tracking (5 stages)
  2. **Closing Soon** — active tenders closing within 14 days, with popup detail dialog
  3. **Tender Type Tabs** — dedicated views for "מכרז ייזום" and "דיור להשכרה"
  4. **Compact KPIs** — single row with key metrics

Review tracking has 5 stages: לא נסקר → סקירה ראשונית → בדיקה מעמיקה → הוצג בפורום → אושר בפורום. Any team member can update. WhatsApp notification is stubbed (TODO: integrate WhatsApp Business API).

Alert system (`alerts.py`) runs in the daily GitHub Actions cron after document sync. Sends Hebrew RTL HTML emails via M365 SMTP when new documents appear on watched tenders.

**To activate alerts**: Add `M365_EMAIL` and `M365_PASSWORD` to GitHub repo secrets. Optionally set `DASHBOARD_URL` secret.

**Next**: Verify multipage app works locally, test review status tracking, configure WhatsApp API.

---

## Recent Changes

| Date | Change | Files |
|------|--------|-------|
| 2026-02-19 | Sprint 6 roadmap: full Supabase migration (move ALL tables off SQLite) | `STATUS.md` |
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
| 2026-02-17 | Sprint 5: PRD v3.0 — added user personas + watchlist/alert feature spec | `PRD.md` |
| 2026-02-17 | Sprint 3: SQLite database layer — TenderDB class with schema, upsert, queries | `db.py` (NEW), `config.py` |
| 2026-02-17 | Sprint 3: Migration script — replay JSON snapshots + cached details into DB | `scripts/migrate_json_to_db.py` (NEW) |
| 2026-02-17 | Sprint 3: DB persistence in data_client — save_to_db(), sync_documents_to_db() | `data_client.py` |
| 2026-02-17 | Sprint 3: Refresh script — save to DB + sync documents for active tenders | `scripts/refresh_tenders.py` |
| 2026-02-17 | Sprint 3: Dashboard loads from DB first with JSON fallback | `app.py` |
| 2026-02-17 | Sprint 3: GitHub Actions commits tenders.db alongside JSON snapshots | `.github/workflows/daily_refresh.yml` |
| 2026-02-17 | Sprint 1: Config management — extract hardcoded values into `config.py` | `config.py` (NEW), `app.py`, `data_client.py` |
| 2026-02-17 | Sprint 1: Logging — replace all print() with logging module | `app.py`, `data_client.py` |
| 2026-02-17 | Sprint 1: Retry logic — exponential backoff on API calls | `data_client.py` |
| 2026-02-17 | Sprint 1: Code cleanup — delete `land_tenders_dashboard/`, pin deps, update .gitignore | `requirements.txt`, `.gitignore` |
| 2026-02-17 | Sprint 1: GitHub Actions daily refresh cron job | `.github/workflows/daily_refresh.yml` (NEW), `scripts/refresh_tenders.py` (NEW) |
| 2026-02-17 | Sprint 1: Streamlit Cloud theme config | `.streamlit/config.toml` |
| 2026-02-17 | Mavat client: Playwright-based module to search plans and download הוראות PDFs from mavat.iplan.gov.il | `mavat_client.py` |
| 2026-02-16 | Executive UI Polish: Fixed sidebar icons (Unicode), table sort icons (Material fonts), CSS overlays | `app.py`, `.streamlit/config.toml` |
| 2026-02-12 | PDF extractor: 50-tender batch test, fix combined column spaces, Q&A doc filtering, text-based gush fallback | `tender_pdf_extractor.py`, `test_pdf_extractor_batch.py` |
| 2026-02-11 | Build PDF extraction module for גוש/חלקה/תב"ע from tender brochures | `tender_pdf_extractor.py`, `test_pdf_extractor.py`, `requirements.txt` |
| 2026-02-11 | Add clickable document download links (GET URL with all params) | `app.py`, `data_client.py` |
| 2026-02-11 | Phase 1 executive redesign — full app.py rewrite | `app.py` |
| 2026-02-11 | Fix tender type codes, add purpose mapping, filter to types 1/5/8 | `data_client.py` |

---

## Known Issues

1. **No tests** — No test suite exists. pytest tests should be added for data_client, db, and alerts modules.
2. **Date range filter removed** — The urgency toggle replaces the old date range picker. May want to add it back as an "advanced" option.
3. **Pie chart click-to-filter** — Plotly click events don't wire easily to Streamlit filters. Deferred.
4. **Streamlit Cloud auth** — Viewer auth not enforced. Using sidebar email input as fallback (works but self-reported).
5. **DB file in git** — tenders.db (8 MB) is committed to git. Sprint 6 will move to Supabase and remove from git.
6. **SMTP not configured** — Need working SMTP credentials (M365 or SMTP2GO) for alert emails.
7. **Supabase anon key permissions** — Need to run GRANT SQL for the anon role to write to tables.

---

## Next Steps

1. **Verify Supabase integration** — Add tenders to watchlist on deployed app, close and reopen, confirm data persists.
2. **Run Supabase GRANT SQL** — `GRANT ALL ON user_watchlist, alert_history, tender_reviews TO anon;` + sequences.
3. **Configure SMTP** — Add `SMTP_USER` + `SMTP_PASSWORD` to Streamlit Cloud secrets.
4. **Sprint 4** — Analytical engine: scoring + market trends.
5. **Sprint 6** — Full Supabase migration: move ALL data (tenders, history, documents) from SQLite to Supabase PostgreSQL. Remove `data/tenders.db` from git. Rewrite `db.py` to use Supabase REST client. Update daily cron to write directly to Supabase.


---

## Database Schema

```
tenders            — 10,447 rows — current state of each tender
tender_history     — 30,997 rows — daily snapshots (4 dates)
tender_documents   —  3,471 rows — document metadata from 444 tenders
tender_scores      — (empty)     — Sprint 4: scoring results
user_watchlist     — (empty)     — per-user tender watchlist for email alerts
alert_history      — (empty)     — sent alert log for deduplication
tender_reviews     — (empty)     — review status tracking (5-stage workflow)
```

---

## Project Structure

```
Gov tender projects/
├── app.py                          # Multipage navigation router + shared CSS
├── config.py                       # Centralized configuration (API, SMTP, paths)
├── db.py                           # SQLite database layer (tender data only since Supabase migration)
├── user_db.py                      # Supabase client: watchlist, reviews, alert_history (NEW)
├── data_client.py                  # API client, normalization, caching, DB persistence
├── dashboard_utils.py              # Shared data loading functions for pages
├── alerts.py                       # Email alert engine: watchlist → SMTP
├── tender_pdf_extractor.py         # PDF extraction: גוש, חלקה, תב"ע from brochure PDFs
├── mavat_client.py                 # Playwright client: search plans on mavat.iplan.gov.il
├── test_pdf_extractor.py           # Test script for PDF extractor (2 sample PDFs)
├── test_pdf_extractor_batch.py     # Batch test: download + extract from N tender brochures
├── requirements.txt                # Pinned Python dependencies
├── complete_city_codes.py          # CBS settlement code → city name mapping (1,281 entries)
├── complete_city_regions.py        # CBS settlement code → region mapping (1,488 entries)
├── CLAUDE.md                       # Project rules and guidelines
├── PRD.md                          # Product Requirements Document v3.0
├── STATUS.md                       # This file — living project state
├── DATA_FLOW_EXPLANATION.md        # Data pipeline documentation
├── .gitignore                      # Git ignore rules
├── assets/                         # Brand assets (logo, images)
│   └── logo.jpg                    # MEGIDO BY AURA brand logo
├── pages/                          # Streamlit multipage app pages (NEW - Sprint 5)
│   ├── dashboard.py                # Full dashboard: filters, KPIs, charts, details, watchlist
│   └── management.py               # Team dashboard: watchlist, review tracking, type tabs, KPIs
├── .streamlit/
│   └── config.toml                 # Streamlit theme + server config
├── .github/
│   └── workflows/
│       └── daily_refresh.yml       # GitHub Actions: daily refresh + alert emails
├── scripts/
│   ├── refresh_tenders.py          # Data refresh script (used by cron)
│   └── migrate_json_to_db.py       # One-time migration: JSON → SQLite
├── tenders_list_*.json             # Daily API snapshots (JSON backup)
├── data/
│   ├── tenders.db                  # SQLite database
│   └── details_cache/              # Cached tender detail JSON files
├── tmp/                            # Temporary files (gitignored)
└── venv/                           # Python virtual environment (gitignored)
```
