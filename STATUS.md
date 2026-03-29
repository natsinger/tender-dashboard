# STATUS.md — Project State

**Last updated:** 2026-03-27 (building rights per תא שטח in מתחמים)

---

## Current State

All 6 sprints are **complete**. The project is an Israeli land tender intelligence platform (MEGIDO BY AURA) with a React/Next.js frontend deployed on Vercel and a Python data pipeline running via GitHub Actions.

- **Phase 3 (React/Next.js Migration)** — ~95% feature parity. Only missing: on-demand building rights extraction trigger button, debug section.
- **All 7 SQL migrations** have been applied to production Supabase.
- **Auth** — deployed and working (magic link + password login).
- **Lot extraction + building rights** — automated in daily cron.
- **Streamlit fully removed** — all legacy files deleted (app.py, pages/, .streamlit/, dashboard_utils.py, test scripts).
- **351 pytest tests passing**, zero regressions.

### Deployment

| Platform | Purpose | Branch | URL |
|----------|---------|--------|-----|
| **Vercel** | Next.js production frontend | `master` | https://tender-dashboard-six.vercel.app |
| **GitHub Actions** | Daily data refresh cron (06:00 UTC) + on-demand building rights extraction | `master` | N/A |

### Frontend (Next.js — `frontend/`)

Next.js 16 + React 19 + TypeScript + Tailwind v4 + shadcn/ui + Recharts + Supabase Auth + Zustand + TanStack Query.

Pages: Dashboard, Management, Explorer, Analytics, Watchlist, Login.

### Backend (Python)

Data pipeline scripts fetch from the Israeli Land Authority API, normalize and persist to Supabase PostgreSQL, extract lot data from brochure PDFs, extract building rights from Mavat plan PDFs, and send email alerts for new documents on watched tenders. The daily cron (`scripts/refresh_tenders.py`) runs data refresh, document sync, lot extraction, building rights extraction, and alert dispatch.

---

## Recent Changes

| Date | Change | Files |
|------|--------|-------|
| 2026-03-27 | **OCR support for scanned PDFs** — Added OCR extraction path to `building_rights_extractor.py` for scanned/image-only Mavat plan PDFs (~50% of PDFs). Uses pytesseract + pypdfium2 + OpenCV. Auto-detects scanned PDFs, OCRs pages to find Section 5, attempts table extraction. Text-based path untouched. Scanned Section 5 detection works (2/2 relevant PDFs), structured column extraction partial (needs Ghostscript+OCRmyPDF or Azure DI for full parsing). 351 tests pass, zero regressions. CI updated with tesseract-ocr apt install. | `building_rights_extractor.py`, `requirements.txt`, `.github/workflows/daily_refresh.yml` |
| 2026-03-27 | **Building rights per תא שטח in מתחמים** — Replaced 3 deferred aggregated columns (מסחר/תעסוקה/מוסדות ציבור) with a flat sub-table of building rights from Taba section 5. Each expanded tender in ניתוח שוק → מתחמים now shows all תאי שטח with ייעוד, שימוש, עיקרי, שירות, and יח"ד. New `useBuildingRightsForPlans` batch-fetch hook. `MultiLotTenderGroup` now carries raw `BuildingRight[]` array instead of aggregated totals. | `frontend/src/components/analytics/lot-comparison-section.tsx`, `frontend/src/hooks/use-lots.ts`, `frontend/src/hooks/use-analytics.ts`, `frontend/src/lib/utils/analytics-engine.ts` |
| 2026-03-10 | **GovMap TABA link integration** — Resolve RMI plan numbers to GovMap viewer URLs via TABA API. Backend: `govmap_client.py` (resolve/batch/build), `db.py` (`govmap_url` column + `update_govmap_urls`), daily cron Step 8 resolves pending plans. Frontend: `/api/govmap` proxy route, `use-govmap` hook (cache-first, API-fallback), `GovMapLink` component (MapPin icon), column added to team watchlist section. **Migration needed:** `ALTER TABLE tenders ADD COLUMN IF NOT EXISTS govmap_url TEXT;` 351 tests pass, build clean. | `govmap_client.py` (new), `tests/test_govmap_client.py` (new), `frontend/src/app/api/govmap/route.ts` (new), `frontend/src/hooks/use-govmap.ts` (new), `frontend/src/components/govmap-link.tsx` (new), `db.py`, `scripts/refresh_tenders.py`, `frontend/src/types/database.ts`, `frontend/src/components/management/team-watchlist-section.tsx` |
| 2026-03-08 | **Streamlit removal + status audit** — Removed all Streamlit files (app.py, pages/, .streamlit/, dashboard_utils.py, legacy test scripts). Cleaned config.py (removed st.secrets fallback), docstrings. Removed streamlit from requirements.txt. 331 tests pass, zero regressions. Full STATUS.md rewrite. | `app.py` (deleted), `pages/` (deleted), `.streamlit/` (deleted), `dashboard_utils.py` (deleted), `config.py`, `requirements.txt`, `STATUS.md` |
| 2026-03-06 | **Fix mitcham/gush data pipeline (Issue #12)** — API MitchamName preserved in `mitcham_name` TEXT field; non-numeric values use positional fallback for lot_number; gush_helka_raw JSONB stores structured array. Delete-then-insert upsert pattern for partial unique indexes. 4-level merge fallback. Frontend lots table shows "מזהה רמ״י" column. 28 new tests. 329 tests pass. | `data_client.py`, `db.py`, `scripts/extract_lots_batch.py`, `scripts/sql/fix_mitcham_gush_schema.sql`, `frontend/src/types/database.ts`, `frontend/src/components/explorer/detail-viewer.tsx`, `tests/test_mitcham_gush_fix.py` |
| 2026-03-05 | **Auth fix: dual login + SMTP template fix** — Fixed broken HTML in Supabase magic link template. Middleware getter pattern for response. Proxy lazy response access. Login page refactored to tabs (magic link + password). Dev-mode error debugging. | `frontend/src/lib/supabase/middleware.ts`, `frontend/src/proxy.ts`, `frontend/src/app/(auth)/login/page.tsx`, `frontend/src/stores/auth-store.ts` |
| 2026-03-05 | **Security audit & hardening** — 50 findings (4 critical, 12 high). RLS on all 9 tables, CSP header, GH Actions injection fix, SMTP_HOST secret, HTML email sanitization, CSV formula injection guard, auth hardening (getUser over getSession), console log gating. 0 npm vulnerabilities. | `alerts.py`, `frontend/next.config.ts`, `.github/workflows/`, `frontend/src/stores/auth-store.ts`, `frontend/src/app/auth/callback/page.tsx`, `frontend/src/components/explorer/csv-export.tsx`, `scripts/sql/enable_rls_all_tables.sql` |
| 2026-02-24 | **Automate extraction pipeline + fix merge bug** — Building rights batch runs on all active tenders with brochures (not just watchlisted). Daily refresh pipeline reordered. Critical merge fix: 4-level fallback for lot_number mismatch between API and PDF. 305 tests pass. | `scripts/extract_building_rights_batch.py`, `scripts/extract_lots_batch.py`, `.github/workflows/daily_refresh.yml` |
| 2026-02-24 | **Management page overhaul + Dashboard simplification** — 12 user-reported changes. Management: RTL column reorder, brochure toggle, lot data columns, pie alignment, KPI unit-breakdown, top 10 cities chart, date-only deadlines. Dashboard: removed pies, moved watchlist management to sidebar. | Multiple Streamlit files (now deleted) |
| 2026-02-23 | **Full app audit & fix** — Fixed week pills overlap, alert failure visibility, Supabase enrichment overwrite bug, old brochure format extraction. Consolidated UserDB instances, added pagination, HTML escaping. 305 tests pass. | `db.py`, `data_client.py`, `user_db.py`, `alerts.py`, `config.py`, `lot_extractor.py`, `tests/test_lot_extractor.py` |
| 2026-02-23 | **API-first lot data integration** — New `extract_lots_from_api()` maps Tik[] fields to lot schema. Pipeline: API lots first, PDF overlay for PDF-only fields. 7 new columns on tender_lots. 294 tests pass. | `data_client.py`, `db.py`, `scripts/extract_lots_batch.py`, `scripts/sql/tender_lots_schema.sql` |
| 2026-02-22 | **Lot extraction pipeline (complete)** — Full BrochureLotExtractor: Section 1 lot tables, Section 2 zoning, Section 3 bid limits. SQL schema for tender_lots (14 columns). Batch CLI script. 153 tests. | `lot_extractor.py`, `scripts/extract_lots_batch.py`, `tests/test_lot_extractor.py`, `scripts/sql/tender_lots_schema.sql`, `db.py` |
| 2026-02-22 | **Analytics page + enrichment engine** — Market intelligence: trends, competitive analysis, price analytics, scoring. Price extraction from Tik[], taba plan analytics. New tables: tender_prices, taba_analytics. | `analytics_engine.py`, `analytics_enrichment.py`, `tests/test_analytics_enrichment.py`, `scripts/sql/analytics_enrichment_schema.sql`, `db.py`, `data_client.py` |
| 2026-02-22 | **Full brochure document selection** — `find_best_brochure()` with 3-tier priority (חוברת המכרז > MichrazFullDocument > פרסום ראשון). Full brochure yields 100% zoning extraction vs 40% for pirsum rishon. | `brochure_analyzer.py`, `scripts/extract_lots_batch.py` |
| 2026-02-20 | **Building rights pipeline** — End-to-end: brochure → plan number → Mavat download → Section 5 extraction → Supabase. Daily cron + CLI. 36 tests. | `building_rights_extractor.py`, `mavat_plan_extractor.py`, `scripts/extract_building_rights_batch.py`, `scripts/sql/building_rights_schema.sql`, `db.py` |
| 2026-02-19 | **Sprint 6: Full Supabase migration** — Rewrote db.py from SQLite to Supabase REST API. Migration script. AlertEngine fix. CI workflow update. | `db.py`, `scripts/migrate_sqlite_to_supabase.py`, `scripts/refresh_tenders.py`, `.github/workflows/daily_refresh.yml`, `user_db.py` |

---

## Known Issues

1. **On-demand building rights extraction trigger** — Not yet exposed in React frontend (was a Streamlit-only button that dispatched a GitHub Actions workflow). Minor — daily cron handles extraction automatically.
2. **Feature parity ~95%** — Missing: on-demand building rights trigger button, debug section. All core functionality (dashboard, explorer, analytics, management, watchlist, auth) is live.

---

## Next Steps

1. **Add on-demand building rights extraction to React frontend** — Button in Explorer detail view to trigger `extract_building_rights.yml` workflow via GitHub API.
2. **Expand test coverage** — Add tests for `data_client.py`, `db.py`, `alerts.py` modules (currently untested or lightly tested).
3. **WhatsApp API integration** — WhatsApp Business API for review status notifications.
4. **Performance monitoring** — Add error tracking / performance monitoring to Vercel frontend.

---

## Database Schema (Supabase PostgreSQL)

All tables exist in production. All 7 SQL migrations have been applied.

```
-- Tender data (managed by db.py)
tenders            — ~10,447 rows — current state of each tender (+ enrichment columns)
tender_history     — ~30,997 rows — daily snapshots for trend analysis
tender_documents   —  ~3,471 rows — document metadata from 444 tenders
building_rights    — extracted Section 5 data from Mavat plan PDFs
tender_prices      — winning bids, floor prices, appraisals per plot
taba_analytics     — aggregated plan-level analytics
tender_lots        — lot-level data from API + brochure PDFs (21 columns incl. mitcham_name, gush_helka_raw)

-- User data (managed by user_db.py)
user_watchlist     — per-user tender watchlist for email alerts (includes notes column)
tender_reviews     — review status tracking (5-stage workflow)
alert_history      — sent alert log for deduplication

-- Security: RLS enabled on all tables, anon writes revoked, team-wide policies on watchlist/reviews/alerts
```

---

## Project Structure

```
Gov tender projects/
├── config.py                       # Centralized configuration (API, SMTP, Supabase, paths)
├── db.py                           # Supabase database layer (tenders, history, documents, lots, building_rights)
├── user_db.py                      # Supabase client: watchlist, reviews, alert_history
├── data_client.py                  # API client, normalization, caching, DB persistence, lot extraction from API
├── alerts.py                       # Email alert engine: watchlist → SMTP (HTML sanitized)
├── lot_extractor.py                # PDF extraction: lot-level data (מתחמים) from brochure PDFs
├── building_rights_extractor.py    # PDF extraction: Section 5 building rights from Mavat plans
├── brochure_analyzer.py            # Brochure document selection + on-demand analysis
├── analytics_engine.py             # Market analytics: regional, seasonal, price, competitive, scoring
├── analytics_enrichment.py         # Price extraction, taba analytics, detail field enrichment
├── govmap_client.py                # GovMap TABA plan resolver (plan_number → viewer URL)
├── mavat_client.py                 # Playwright client: search plans on mavat.iplan.gov.il
├── mavat_plan_extractor.py         # Coordinator: download + extract from Mavat plan PDFs
├── tender_pdf_extractor.py         # PDF extraction: גוש, חלקה, תב"ע from brochure PDFs
├── complete_city_codes.py          # CBS settlement code → city name mapping (1,281 entries)
├── complete_city_regions.py        # CBS settlement code → region mapping (1,488 entries)
├── requirements.txt                # Pinned Python dependencies
├── CLAUDE.md                       # Project rules and guidelines
├── PRD.md                          # Product Requirements Document
├── STATUS.md                       # This file — living project state
├── DATA_FLOW_EXPLANATION.md        # Data pipeline documentation
├── TECH_SPEC.md                    # Technical specification
├── .gitignore                      # Git ignore rules
├── assets/
│   └── logo megido.jpg             # MEGIDO BY AURA brand logo
├── frontend/                       # Next.js production frontend (deployed on Vercel)
│   ├── src/
│   │   ├── app/
│   │   │   ├── (dashboard)/        # Protected routes
│   │   │   │   ├── dashboard/      # Main dashboard: KPIs, charts, closing deadlines
│   │   │   │   ├── management/     # Team operational dashboard (read-only)
│   │   │   │   ├── explorer/       # Tender explorer: filterable table, detail viewer, lots
│   │   │   │   ├── analytics/      # Market intelligence: trends, prices, scoring
│   │   │   │   ├── watchlist/      # Watchlist management
│   │   │   │   └── layout.tsx      # Dashboard layout wrapper
│   │   │   ├── (auth)/
│   │   │   │   └── login/          # Login page (magic link + password tabs)
│   │   │   ├── auth/
│   │   │   │   └── callback/       # Supabase auth callback handler
│   │   │   ├── api/
│   │   │   │   ├── auth/           # Auth API routes (role check)
│   │   │   │   ├── govmap/        # GovMap TABA URL proxy (on-demand)
│   │   │   │   └── tender-details/ # Tender details API proxy
│   │   │   ├── layout.tsx          # Root layout
│   │   │   ├── page.tsx            # Landing / redirect
│   │   │   └── globals.css         # Global styles
│   │   ├── components/
│   │   │   ├── ui/                 # shadcn/ui primitives
│   │   │   ├── layout/             # Sidebar, header, navigation
│   │   │   ├── dashboard/          # Dashboard-specific components
│   │   │   ├── management/         # Management page components
│   │   │   ├── explorer/           # Explorer components (detail-viewer, csv-export)
│   │   │   ├── analytics/          # Analytics page components
│   │   │   ├── charts/             # Shared chart components (Recharts)
│   │   │   ├── auth-guard.tsx      # Route protection
│   │   │   ├── filter-bar.tsx      # Shared filter bar
│   │   │   ├── data-table.tsx      # Shared data table
│   │   │   ├── metric-card.tsx     # KPI metric card
│   │   │   ├── govmap-link.tsx     # GovMap TABA link (MapPin icon)
│   │   │   ├── watchlist-manager.tsx
│   │   │   ├── review-status-editor.tsx
│   │   │   ├── tender-detail-modal.tsx
│   │   │   ├── error-boundary.tsx
│   │   │   └── ...
│   │   ├── hooks/                  # Data hooks
│   │   │   ├── use-tenders.ts      # Tender list queries
│   │   │   ├── use-lots.ts         # Lot data queries
│   │   │   ├── use-bulk-lots.ts    # Bulk lot loading
│   │   │   ├── use-watchlist.ts    # Watchlist CRUD
│   │   │   ├── use-reviews.ts      # Review status mutations
│   │   │   ├── use-govmap.ts       # GovMap URL resolution (cache-first, API-fallback)
│   │   │   ├── use-documents.ts    # Document queries
│   │   │   ├── use-analytics.ts    # Analytics data
│   │   │   ├── use-prices.ts       # Price data
│   │   │   ├── use-tender-details.ts
│   │   │   └── index.ts
│   │   ├── stores/
│   │   │   ├── auth-store.ts       # Zustand auth state (magic link + password)
│   │   │   └── filter-store.ts     # Zustand filter state
│   │   ├── lib/
│   │   │   ├── supabase/           # Supabase client (browser + server + middleware)
│   │   │   ├── utils/              # Utility functions
│   │   │   ├── constants.ts        # Shared constants
│   │   │   ├── cn.ts               # Class name utility
│   │   │   └── utils.ts
│   │   ├── types/
│   │   │   └── database.ts         # TypeScript interfaces (Tender, TenderLot, etc.)
│   │   ├── design-system/
│   │   │   ├── tokens/             # Design tokens (colors, typography, spacing)
│   │   │   ├── variants.ts         # Component variants
│   │   │   └── system.md           # Design system docs
│   │   └── providers/
│   │       └── query-provider.tsx   # TanStack Query provider
│   ├── proxy.ts                    # Auth proxy / middleware helper
│   ├── next.config.ts              # Next.js config (CSP headers)
│   ├── vercel.json                 # Vercel deployment config
│   ├── package.json                # Dependencies
│   └── tsconfig.json               # TypeScript config
├── scripts/
│   ├── refresh_tenders.py          # Data refresh script (used by daily cron)
│   ├── extract_lots_batch.py       # Batch lot extraction: brochure PDF → tender_lots → Supabase
│   ├── extract_building_rights_batch.py  # Batch: brochure → plan → Mavat → building_rights → Supabase
│   ├── migrate_json_to_db.py       # One-time migration: JSON → SQLite (historical)
│   ├── migrate_sqlite_to_supabase.py  # One-time migration: SQLite → Supabase (Sprint 6)
│   └── sql/
│       ├── building_rights_schema.sql       # plan_number column + building_rights table
│       ├── analytics_enrichment_schema.sql  # tender_prices + taba_analytics tables
│       ├── tender_lots_schema.sql           # tender_lots table (21 columns)
│       ├── watchlist_notes_schema.sql       # notes column on user_watchlist
│       ├── lot_count_schema.sql             # lot_count + max_lots_per_bidder columns
│       ├── enable_rls_all_tables.sql        # RLS policies on all tables
│       └── fix_mitcham_gush_schema.sql      # mitcham_name + gush_helka_raw columns
├── tests/                          # pytest test suite (351 tests)
│   ├── test_analytics_engine.py    # Analytics engine tests (102 tests)
│   ├── test_analytics_enrichment.py  # Analytics enrichment tests (23 tests)
│   ├── test_lot_extractor.py       # Lot extractor tests (153 tests)
│   ├── test_govmap_client.py       # GovMap TABA resolver tests
│   └── test_mitcham_gush_fix.py    # Mitcham/gush fix tests (28 tests)
├── .github/
│   └── workflows/
│       ├── daily_refresh.yml       # Daily cron: data refresh + doc sync + lots + building rights + alerts
│       └── extract_building_rights.yml  # On-demand building rights extraction (workflow_dispatch)
├── data/
│   └── details_cache/              # Cached tender detail JSON files
├── tenders_list_*.json             # Daily API snapshots (JSON backup)
├── tmp/                            # Temporary files (gitignored)
└── venv/                           # Python virtual environment (gitignored)
```
