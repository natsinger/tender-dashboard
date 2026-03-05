# STATUS.md — Project State

**Last updated:** 2026-03-05 (session 22 — Auth fix: dual login + SMTP template fix)

---

## Current State

Sprint 1 (Stabilize & Deploy MVP) — **complete**.
Sprint 3 (SQLite Data Persistence) — **complete** → superseded by Sprint 6.
Sprint 5 (Watchlist & Email Alerts) — **complete** (deployed to Streamlit Cloud, SMTP pending).
Sprint 6 (Full Supabase Migration) — **complete** (pending: run SQL schema + migration script + add GitHub secrets).
Sprint 4 (Analytical Engine) — **complete** (analytics_engine + analytics_enrichment + pages/analytics.py, 125 tests).
Management Page Redesign (Features #1-4) — **complete**.
MEGIDO Brand Redesign — **complete**.
Mobile-First Responsive Redesign (Deep Blue) — **complete**.
Lot Extraction Pipeline — **complete** (lot_extractor + extract_lots_batch + 169 tests, real-PDF fixes applied, pending SQL schema deployment).
API-First Lot Integration — **complete** (API Tik[] as source of truth, PDF overlay for PDF-only fields, 7 new columns).
Phase 3 (React/Next.js Migration) — **in progress** (frontend deployed on Vercel, feature parity ongoing).

**All data lives in Supabase PostgreSQL.** SQLite (`data/tenders.db`) is no longer used and has been added to `.gitignore`.

### Deployment

| Platform | Purpose | Branch | URL |
|----------|---------|--------|-----|
| **Vercel** | Next.js production frontend | `master` | (configured in Vercel dashboard) |
| Streamlit Cloud | Legacy Streamlit dashboard | `master` | (still functional) |
| GitHub Actions | Daily data refresh cron (06:00 UTC) | `master` | N/A |

### Frontend (Next.js — `frontend/`)

Next.js 16 + React 19 + TypeScript + Tailwind v4 + shadcn/ui + Recharts + Supabase Auth + Zustand + TanStack.

Pages: Dashboard, Management, Explorer, Analytics, Watchlist, Login.

### Backend (Streamlit — root)

The Streamlit app still runs and has four views:
- **Dashboard** (`pages/dashboard.py`) — Full view for daily users: filters, KPIs, charts (no pies), tender details, closing deadlines, watchlist management in sidebar (personal + team + review editing), analytics, debug
- **Explorer** (`pages/explorer.py`) — Tender explorer: filterable data table, detail viewer with lot/land/pricing data, building rights section
- **Analytics** (`pages/analytics.py`) — Market intelligence: trends, competitive analysis, price analytics, scoring with radar charts
- **Management** (`pages/management.py`) — Team operational dashboard (read-only):
  1. **Selected Tenders** — shared team watchlist with lot data columns (שוק חופשי, מחיר מטרה, סה"כ, % מחיר מטרה), brochure toggle, RTL column order
  2. **Closing Soon** — "נסגרים ב14 ימים הקרובים" with popup detail dialog
  3. **Pies + KPIs** — dual pie charts (aligned), 3 unit-breakdown KPIs, top 10 cities bar chart
  4. **Tender Type Tabs** — dedicated views for "מכרז ייזום", "דיור להשכרה", "סוגים נוספים" (date-only deadlines)

Review tracking has 5 stages: לא נסקר → סקירה ראשונית → בדיקה מעמיקה → הוצג בפורום → אושר בפורום. Editing is in the Dashboard (requires login). Management is read-only.

Alert system (`alerts.py`) runs in the daily GitHub Actions cron after document sync. Sends Hebrew RTL HTML emails via SMTP2GO when new documents appear on watched tenders.

**To activate (one-time setup)**:
1. Run the SQL schema in Supabase SQL Editor (creates tables + indexes + GRANTs)
2. Run `scripts/sql/building_rights_schema.sql` in Supabase SQL Editor (adds `plan_number` column + `building_rights` table + brochure/extraction columns)
3. Run `scripts/sql/analytics_enrichment_schema.sql` in Supabase SQL Editor (adds enrichment columns + `tender_prices` + `taba_analytics` tables)
3b. Run `scripts/sql/tender_lots_schema.sql` in Supabase SQL Editor (adds `tender_lots` table + lot extraction columns)
3c. Run `scripts/sql/watchlist_notes_schema.sql` in Supabase SQL Editor (adds `notes` column to `user_watchlist`)
3d. Run `scripts/sql/lot_count_schema.sql` in Supabase SQL Editor (adds `lot_count` + `max_lots_per_bidder` columns to `tenders`)
3e. Run `scripts/sql/enable_rls_all_tables.sql` in Supabase SQL Editor (enables RLS on all tables, revokes anon writes, adds team-wide policies for watchlist/reviews/alerts)
4. Run `python scripts/migrate_sqlite_to_supabase.py` to migrate existing data
5. Add `SUPABASE_URL` + `SUPABASE_KEY` to GitHub repo secrets
6. Add `SMTP_USER` + `SMTP_PASSWORD` to GitHub repo secrets
7. Add Supabase + SMTP secrets to Streamlit Cloud secrets
8. Create a GitHub PAT with `actions:write` scope and add as `GH_PAT` to Streamlit Cloud secrets

---

## Recent Changes

| Date | Change | Files |
|------|--------|-------|
| 2026-03-05 | **Auth fix: dual login + SMTP template fix** — Root cause: broken HTML tag in Supabase magic link email template (`<h2כניסה` missing `>`) caused Go template engine to crash with 500 on every OTP request. Code fixes: (1) **middleware.ts** — getter pattern for response (fixes stale closure after token refresh). (2) **proxy.ts** — lazy response access after `getUser()`, removed signOut from redirect branch, narrower auth code interception (requires both `?code=` AND `?type=`), cookie copying to redirect responses. (3) **login/page.tsx** — refactored to tabs UI with two auth methods: magic link ("קישור קסם") + password login ("סיסמה") with signup flow (8-char min + confirm), dev-mode error debugging shows actual Supabase error, all OTP errors now block success flow. (4) **auth-store.ts** — separate `initialized` flag (prevents one-shot failure), `res.ok` guard on `/api/auth/role` response. Build passes, all verification checks pass, magic links confirmed working after template fix. | `frontend/src/lib/supabase/middleware.ts`, `frontend/src/proxy.ts`, `frontend/src/app/(auth)/login/page.tsx`, `frontend/src/stores/auth-store.ts` |
| 2026-03-05 | **Security audit & hardening** — Comprehensive security audit (50 findings: 4 critical, 12 high, 22 medium, 12 low). Fixes applied on `security_fixes` branch: (1) **RLS migration SQL** — enables Row Level Security on all 9 unprotected Supabase tables, revokes anon writes, adds team-wide policies for watchlist/reviews/alerts, read-only on data tables (MUST run manually in SQL Editor). (2) **CSP header** — Content-Security-Policy added to next.config.ts (script/style/img/connect/frame-ancestors). (3) **GH Actions command injection** — `${{ github.event.inputs.tender_id }}` moved to env var intermediary in extract_building_rights.yml. (4) **SMTP_HOST secret** — hardcoded value moved to `${{ secrets.SMTP_HOST }}` in daily_refresh.yml (MUST add GitHub secret). (5) **HTML email sanitization** — all dynamic values in alerts.py wrapped with `html.escape()`. (6) **CSV formula injection** — cells starting with `=+\-@\t` prefixed with `'` in csv-export.tsx. (7) **Auth hardening** — `getSession()` → `getUser()` in auth-store.ts, OTP type validation against allowlist, generic Hebrew error messages in callback. (8) **Console log gating** — all console.log/warn/error wrapped in `NODE_ENV === "development"` across 10 files. (9) **npm audit fix** — 0 vulnerabilities (hono + @hono/node-server patched). TypeScript compiles cleanly. | `alerts.py`, `frontend/next.config.ts`, `.github/workflows/extract_building_rights.yml`, `.github/workflows/daily_refresh.yml`, `frontend/src/stores/auth-store.ts`, `frontend/src/app/auth/callback/page.tsx`, `frontend/src/components/explorer/csv-export.tsx`, `frontend/src/proxy.ts`, `frontend/src/lib/supabase/client.ts`, `frontend/src/lib/supabase/server.ts`, `frontend/src/components/error-boundary.tsx`, `frontend/src/app/(auth)/login/page.tsx`, `frontend/src/hooks/use-bulk-lots.ts`, `frontend/src/hooks/use-reviews.ts`, `frontend/src/hooks/use-documents.ts`, `scripts/sql/enable_rls_all_tables.sql` (NEW) |
| 2026-03-04 | **Explorer: show land & pricing data from API** — Added "נתוני קרקע ומחירים" section to Explorer detail viewer, displaying per-lot data directly from the API Tik[] array: area (שטח), reserve price (מחיר סף), appraisal (שומה), development costs (עלויות פיתוח), guarantee (ערבות), units per lot (יח"ד), gush/helka, and taba/plan number. Data was already fetched but never displayed. Works for single and multi-lot tenders. | `pages/explorer.py` |
| 2026-02-24 | **Automate extraction pipeline + fix merge bug** — (1) Building rights batch (`extract_building_rights_batch.py`): new `get_tenders_needing_building_rights()` queries ALL active tenders with brochure (not just watchlisted); default behavior changed; `MAX_PER_RUN` 10→20; `--watchlist-only` flag for legacy mode. (2) Daily refresh workflow: building rights moved after lot extraction (faster pipeline), limit 5→20, step renamed. (3) **Critical merge fix** in `merge_api_and_pdf_lots()`: lot_number mismatch between API (MitchamName-based) and PDF (sequential/parcel-based) caused zero merges — added 4-level fallback (exact match → positional → PDF-as-base → partial positional). Verified on tenders 405/2024 (8 lots, 7 merged with target/free data) and 311/2025 (23 lots, all merged, sum=2868). 305 tests pass. | `scripts/extract_building_rights_batch.py`, `scripts/extract_lots_batch.py`, `.github/workflows/daily_refresh.yml` |
| 2026-02-24 | **Management page overhaul + Dashboard simplification** — 12 user-reported changes across 2 pages. **Management** (10 items + 4 refinements): (1) Watchlist table RTL column reorder via reversed DataFrame columns, (2) brochure toggle filter (st.pills הכל/עם חוברת), (3) lot data columns (שוק חופשי, מחיר מטרה, סה"כ, % מחיר מטרה) via new `_aggregate_lot_data()` helper calling `TenderDB.get_lots()`, (4) closing-soon title → "נסגרים ב14 ימים הקרובים", (5) updated caption, (6) divider + "מכרזי מקרקעין לדיור למכירה" header before pies, (7) aligned pie chart params (textfont_size=14, height=220), (8) 3 KPI unit-breakdown metrics (סה"כ/שוק חופשי/מחיר מטרה), (9) top 10 cities bar chart, (10) date-only deadlines in bottom tabs. Refinements: reversed column order for RTL, renamed מכרז→מספר מכרז, fixed בה"כ→סה"כ, fixed % מ.מ.→% מחיר מטרה. **Dashboard** (2 items): (1) removed pie charts + week toggle from main area (kept KPI cards), (2) moved all watchlist management (personal + team add/remove, review editing form) to sidebar with 3 sections. 305 tests pass, both pages import cleanly, app returns HTTP 200. | `pages/management.py`, `pages/dashboard.py` |
| 2026-02-24 | **Dashboard UI polish** — 6 user-reported fixes: (1) Unified all table columns to RTL direction with consistent order (שם מכרז → יח"ד → עיר) across 7 tables in 4 pages. (2) Dashboard layout reorganized — closing deadlines moved up, bar chart full-width below. (3) Notes/הערות column added to team review table. (4) Building rights in Explorer auto-loads from Supabase (no button press required). (5) Page order changed: לוח הנהלה → דאשבורד → סייר מכרזים → ניתוח שוק. (6) Pie charts fixed: identical size, label+value on slices, st.pills for week toggle + deadline/brochure filters. City bar chart left margin increased for Hebrew names. | `app.py`, `pages/dashboard.py`, `pages/explorer.py`, `pages/management.py` |
| 2026-02-24 | **Explorer UX: auto-show lot data, optional building rights button** — Reordered tender detail viewer sections: lot data (from API/tender_lots) now renders BEFORE building rights section so existing data is always visible without clicking. When br_status=="none", existing brochure data (plan_number, lots_data, brochure_summary) is now displayed automatically. Extraction button relabeled from "נתח זכויות בנייה" to "ניתוח מעמיק מחוברת המכרז" and presented as optional with contextual caption ("נתוני מתחמים בסיסיים זמינים למעלה") when API lot data exists. No functionality removed — button still triggers full brochure extraction workflow. | `pages/explorer.py` |
| 2026-02-23 | **Full app audit & fix** — Comprehensive static+runtime audit of all 4 pages + 5 core modules, addressing 4 user-reported issues + all high/medium code findings. **(1) Dashboard UI** — fixed week pills overlap (removed negative margin in CSS), merged orphaned caption into metric label, replaced meaningless color gradient with single-color bars on city chart. **(2) Alert system** — made failures visible (logger.error + structured summary), added SMTP connectivity check, prioritized watchlisted tenders in DOC_SYNC_LIMIT. **(3) Supabase schema** — CRITICAL: fixed enrichment overwrite bug where daily upsert_tenders() was resetting acquisition_form/participation_fee/land_area_sqm to None. Fixed tz_localize→tz_convert for UTC-aware datetimes (3 locations). **(4) Old brochure format** — added max_licensable_area and development_costs keyword groups to lot_extractor SECTION1_HEADERS, adjusted confidence scoring so total_units counts as alternative to target/free-market split. 11 new tests. **Code quality** — removed unused imports across 3 pages, consolidated 3 UserDB instances to 1 in dashboard.py, moved stale `today = datetime.now()` to rendering blocks (4 pages), added HTML escaping for unsafe_allow_html (explorer+analytics), wired up dead force_refresh checkbox (explorer), added pagination to user_db.get_all_active_watchlists() and get_sent_doc_ids(). 305 tests pass (294 original + 11 new), 0 regressions. | `app.py`, `pages/dashboard.py`, `pages/explorer.py`, `pages/analytics.py`, `pages/management.py`, `db.py`, `data_client.py`, `user_db.py`, `alerts.py`, `scripts/refresh_tenders.py`, `config.py`, `lot_extractor.py`, `tests/test_lot_extractor.py` |
| 2026-02-23 | **UI bug-fix batch + watchlist notes + Explorer enhancements** — (1) Fixed city chart title "מכרזים לפי עיר" → "מכרזים פעילים לפי עיר" (2 locations). (2) Fixed brochure toggle label "בלי חוברת" → "הצג גם ללא חוברת" with help tooltip. (3) Changed new-announcement detection from last-Sunday cutoff to rolling 7-day window. (4) Added KPI caption "ללא מכרזי ייזום" to clarify active tender count (248 excludes type 9). (5) Added per-tender notes to watchlist: `notes` column on `user_watchlist`, `set_watchlist_note()` + `get_watchlist_note()` in user_db.py, editable text_area in Dashboard. (6) Fixed review-notes pre-population in Dashboard (added `value=` parameter). (7) Added lot_count and max_lots_per_bidder columns to Dashboard deadlines table and Explorer table. (8) Row selection in Explorer table auto-opens detail viewer. (9) Management page team watchlist now shows notes read-only. (10) Improved save_to_db() error handling: `_KNOWN_DB_COLUMNS` safelist blocks unknown columns, explicit error logging with full traceback. | `pages/dashboard.py`, `pages/explorer.py`, `pages/management.py`, `user_db.py`, `db.py`, `data_client.py`, `scripts/refresh_tenders.py`, `scripts/sql/watchlist_notes_schema.sql` (NEW), `scripts/sql/lot_count_schema.sql` (NEW) |
| 2026-02-23 | **API-first lot data integration** — New `extract_lots_from_api()` function in data_client.py maps Tik[] array fields (MitchamName, Shetach, Kibolet, MechirSaf, SchumArvut, mechirShuma, HotzaotPituach, TochnitMigrash, GushHelka, ShemZoche, SchumZchiya) to lot schema. Pipeline rewritten: API lots upserted first (data_source='api'), then PDF-only fields (units_target_price, units_free_market, zoning_designation) overlaid via merge (data_source='merged'). 7 new columns on tender_lots: total_units, development_costs, gush, helka, winner_name, winning_amount, data_source. Explorer page updated with new columns + 4-column summary metrics. 294 tests pass (no regressions). | `data_client.py`, `db.py`, `scripts/extract_lots_batch.py`, `pages/explorer.py`, `scripts/sql/tender_lots_schema.sql`, `STATUS.md` |
| 2026-02-22 | **Full brochure document selection** — Investigated 450 cached tender details and found 142 tenders have חוברת המכרז (full brochure, 1-40MB) in MichrazDocList vs פרסום ראשון (1-2 page announcement). New `find_best_brochure()` function in brochure_analyzer.py with 3-tier priority: (1) חוברת from MichrazDocList, (2) MichrazFullDocument, (3) פרסום ראשון fallback. Updated extract_lots_batch.py to use find_best_brochure() with doc_type tracking. Tested on 8 real brochures: full brochure yields 100% zoning extraction (5/5) vs 40% for pirsum rishon (2/5). Multi-lot tenders (14, 7, 7 lots) correctly extract Section 1 tables, Section 2 zoning tables, and Section 3 bid limits from full brochures. 169 tests pass (no regressions). | `brochure_analyzer.py`, `scripts/extract_lots_batch.py`, `STATUS.md` |
| 2026-02-22 | **Lot extraction real-PDF fixes** — Downloaded 8 diverse brochures (types 1/5/6/9) and discovered pirsum rishon docs use inline text, not Section headers. Added: `_extract_zoning_inline()` for inline plan+designation from reversed Hebrew text (pattern: "PLAN תינכות הלח םישרגמה לע"), `_extract_lots_from_text()` fallback for no-table documents, new Section 1 column keywords (helka, gush, total_units, rental/sale columns). Results on 8 real PDFs: S1 75%->100%, S2 0%->88%, S3 0% (correctly: pirsum rishon docs don't contain bid limits). 169 tests pass (+16 new). | `lot_extractor.py`, `tests/test_lot_extractor.py`, `STATUS.md` |
| 2026-02-22 | **Lot extraction pipeline (complete)** — Full BrochureLotExtractor: Section 1 lot table parsing (multi-page, reversed Hebrew, multi-line headers), Section 2 zoning (table + text extraction), Section 3 bid limits (Hebrew number words + regex). SQL schema for `tender_lots` table (14 columns) + 3 tenders columns. 4 DB methods (upsert_lots, get_lots, update_lot_extraction_status, update_max_lots_per_bidder). Batch CLI script with --tender-id and --limit args. Explorer page lot display section with bid-limit badge, formatted table, summary metrics, and extraction status indicator. 153 pytest tests pass. QA-verified against 5+ real brochure PDFs. | `lot_extractor.py` (NEW), `scripts/extract_lots_batch.py` (NEW), `tests/test_lot_extractor.py` (NEW), `scripts/sql/tender_lots_schema.sql` (NEW), `db.py`, `pages/explorer.py`, `STATUS.md` |
| 2026-02-22 | **Dashboard UI improvements** — Added city distribution pie (top 10) under existing pies. Taller closing deadlines table (550px) with reordered columns (days_left, urg, deadline first for mobile LTR). Brochure-only toggle on deadlines table. Inline HTML cards for "סוגים נוספים" (units + count on same line). JSON snapshot comparison for new tender detection. Shared chart constants extracted to dashboard_utils.py. Management page: added brochure + region pies and 2 KPI cards after closing-soon section, removed redundant bottom KPI row. CSS: smaller radio pills, bigger mobile sidebar arrows (24px SVG, 2.5rem touch target). | `dashboard_utils.py`, `pages/dashboard.py`, `pages/management.py`, `app.py`, `STATUS.md` |
| 2026-02-22 | **Mobile sidebar fix (round 2)** — replaced `visibility:hidden` with `opacity:0` for collapsed sidebar (prevents Streamlit child elements from overriding). Updated selectors from old `collapsedControl` to `stExpandSidebarButton`. Force `left:0` + `translateX(-100%)` for full off-screen collapse. Verified with Playwright at 375x812 mobile viewport. | `app.py` |
| 2026-02-22 | **Mobile-first responsive redesign** — replaced gold/navy palette with Deep Blue professional palette (primary #2563EB, sidebar #0F172A, accent #60A5FA). Added mobile-first CSS with @media breakpoints at 768px and 1024px: single-column stacking on mobile, responsive metric cards, horizontal-scrolling tables, compact typography. Updated all 5 files: CSS tokens in app.py, chart colors in dashboard.py and analytics.py, inline HTML colors in explorer.py and management.py, Streamlit theme in config.toml. | `app.py`, `pages/dashboard.py`, `pages/analytics.py`, `pages/explorer.py`, `pages/management.py`, `.streamlit/config.toml` |
| 2026-02-22 | **Analytics page** — new "ניתוח שוק" page with 5 sections: Market Overview (KPIs + supply pipeline), Trends (regional volume, momentum, monthly distribution, moving averages), Competitive Intelligence (lifecycle, deadline overlap, saturation, document intelligence), Price Analytics (price trends, taba summary, price premium), Scoring (top 20 table with badges, histogram, radar deep-dive). Sidebar date range + region filters. | `pages/analytics.py` (NEW), `app.py` |
| 2026-02-22 | **Analytics enrichment engine** -- price extraction from Tik[], detail API field capture (acquisition_form, participation_fee, land_area), taba plan number extraction, aggregated plan-level analytics, days_to_deadline computed column. New tables: tender_prices, taba_analytics. 23 tests pass. | `analytics_enrichment.py` (NEW), `tests/test_analytics_enrichment.py` (NEW), `scripts/sql/analytics_enrichment_schema.sql` (NEW), `db.py`, `data_client.py`, `dashboard_utils.py` |
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

1. **Partial test coverage** — 305 pytest tests: `analytics_engine` (102), `analytics_enrichment` (23), `lot_extractor` (180). Tests for `data_client`, `db`, and `alerts` modules are still needed.
2. **Date range filter removed** — The urgency toggle replaces the old date range picker. May want to add it back as an "advanced" option.
3. **Pie chart click-to-filter** — Plotly click events don't wire easily to Streamlit filters. Deferred.
4. **Streamlit Cloud auth** — Viewer auth not enforced. Using sidebar email input as fallback (works but self-reported).
5. ~~**SMTP not configured**~~ — **RESOLVED** (session 22). SMTP2GO credentials are correct; root cause was broken HTML tag in Supabase magic link email template. Fixed in Supabase Dashboard.
6. **Supabase setup pending** — Need to run SQL schema creation + GRANT SQL + migrate data before app will load from Supabase.
7. **Streamlit use_container_width deprecation** — Still supported in Streamlit 1.54.0 but may be deprecated in future versions. Migrate to `width` parameter when needed.
8. **Old brochure format DB columns** — `max_licensable_area` and `development_costs` fields are now extracted but need corresponding columns added to the `tender_lots` table in Supabase (run ALTER TABLE).
9. **SMTP_HOST GitHub secret needed** — After merging `security_fixes`, add `SMTP_HOST` secret with value `mail.smtp2go.com` to GitHub repo secrets (was previously hardcoded in workflow YAML).
10. **RLS migration pending** — Run `scripts/sql/enable_rls_all_tables.sql` in Supabase SQL Editor to enable Row Level Security on all tables. Without this, the anon key (visible in browser) allows unrestricted read/write. Policies use team-wide access (all authenticated users see all rows) — role-based restrictions (team vs management) are enforced in frontend via `TEAM_EMAILS` / `MANAGEMENT_EMAILS` env vars.
11. **Production auth env vars needed** — Must set in Vercel env vars: `NEXT_PUBLIC_SITE_URL` (production URL), `TEAM_EMAILS`, `MANAGEMENT_EMAILS`, `NEXT_PUBLIC_TEAM_EMAIL`, `SUPABASE_SERVICE_ROLE_KEY`. Must also set Supabase Dashboard Site URL + Redirect URLs to production URL.

---

## Next Steps

1. **Deploy auth to production** — Set Vercel env vars (`NEXT_PUBLIC_SITE_URL`, `TEAM_EMAILS`, `MANAGEMENT_EMAILS`, `NEXT_PUBLIC_TEAM_EMAIL`, `SUPABASE_SERVICE_ROLE_KEY`). Update Supabase Dashboard: Site URL → production URL, add production `/auth/callback` to Redirect URLs.
2. **Run lot extraction SQL schema** — Execute `scripts/sql/tender_lots_schema.sql` in Supabase SQL Editor (adds `tender_lots` table with 21 columns including API-sourced fields: total_units, development_costs, gush, helka, winner_name, winning_amount, data_source).
3. **Run lot extraction batch** — Execute `python scripts/extract_lots_batch.py --limit 20` to process first batch of tenders with brochures.
4. **Add lot extraction to daily cron** — Add `extract_lots_batch.py` step to `.github/workflows/daily_refresh.yml` after document sync.
5. **Run building rights SQL schema** — Execute `scripts/sql/building_rights_schema.sql` in Supabase SQL Editor (adds `plan_number`, `building_rights` table, brochure columns).
6. **Create GitHub PAT** — Create a PAT with `actions:write` scope, add as `GH_PAT` to Streamlit Cloud secrets.
7. **Test building rights flow** — Click "נתח זכויות בנייה" in a tender detail view, verify brochure summary appears and GH Actions triggers.
8. **WhatsApp API** — Integrate WhatsApp Business API for review status notifications.
9. **Expand test coverage** — Add tests for data_client, db, alerts, and dashboard_utils modules.

---

## Database Schema (Supabase PostgreSQL)

```
-- Tender data (managed by db.py)
tenders            — ~10,447 rows — current state of each tender (+ enrichment columns)
tender_history     — ~30,997 rows — daily snapshots for trend analysis
tender_documents   —  ~3,471 rows — document metadata from 444 tenders
building_rights    — extracted Section 5 data from Mavat plan PDFs
tender_prices      — winning bids, floor prices, appraisals per plot (NEW, needs SQL creation)
taba_analytics     — aggregated plan-level analytics (NEW, needs SQL creation)
tender_lots        — lot-level data from API + brochure PDFs (21 columns: lot_number, units, pricing, zoning, gush/helka, winner, data_source; needs SQL creation)

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
├── db.py                           # Supabase database layer (tender data: tenders, history, documents, lots)
├── user_db.py                      # Supabase client: watchlist, reviews, alert_history
├── data_client.py                  # API client, normalization, caching, DB persistence
├── dashboard_utils.py              # Shared data loading functions for pages
├── alerts.py                       # Email alert engine: watchlist → SMTP
├── tender_pdf_extractor.py         # PDF extraction: גוש, חלקה, תב"ע from brochure PDFs
├── brochure_analyzer.py             # On-demand brochure analysis + GitHub Actions trigger
├── analytics_engine.py             # Market analytics: regional, seasonal, price, competitive, scoring
├── analytics_enrichment.py         # Price extraction, taba analytics, detail field enrichment
├── lot_extractor.py                # PDF extraction: lot-level data (מתחמים) from brochure PDFs
├── building_rights_extractor.py    # PDF extraction: Section 5 building rights from Mavat plans
├── mavat_client.py                 # Playwright client: search plans on mavat.iplan.gov.il
├── mavat_plan_extractor.py         # Coordinator: download + extract from Mavat plan PDFs
├── test_pdf_extractor.py           # Test script for PDF extractor (2 sample PDFs)
├── test_pdf_extractor_batch.py     # Batch test: download + extract from N tender brochures
├── test_building_rights.py         # Tests for building rights extractor (36 tests)
├── tests/                          # pytest test suite (278 tests)
│   ├── test_analytics_engine.py    # Tests for analytics engine (102 tests)
│   ├── test_analytics_enrichment.py  # Tests for analytics enrichment (23 tests)
│   └── test_lot_extractor.py       # Tests for lot extractor (153 tests)
├── requirements.txt                # Pinned Python dependencies
├── complete_city_codes.py          # CBS settlement code → city name mapping (1,281 entries)
├── complete_city_regions.py        # CBS settlement code → region mapping (1,488 entries)
├── CLAUDE.md                       # Project rules and guidelines
├── PRD.md                          # Product Requirements Document v4.0
├── STATUS.md                       # This file — living project state
├── DATA_FLOW_EXPLANATION.md        # Data pipeline documentation
├── .gitignore                      # Git ignore rules
├── assets/                         # Brand assets (logo, images)
│   └── logo megido.jpg             # MEGIDO BY AURA brand logo
├── pages/                          # Streamlit multipage app pages
│   ├── dashboard.py                # Full dashboard: filters, KPIs, charts, details, watchlist, review editing
│   ├── explorer.py                 # Tender explorer: filterable table, detail viewer, lot data display
│   ├── analytics.py                # Market analytics: trends, competitive intel, prices, scoring
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
│   ├── extract_lots_batch.py       # Batch lot extraction: brochure PDF → lot table → Supabase
│   ├── migrate_json_to_db.py       # One-time migration: JSON → SQLite (historical)
│   ├── migrate_sqlite_to_supabase.py  # One-time migration: SQLite → Supabase (Sprint 6)
│   └── sql/
│       ├── building_rights_schema.sql  # SQL: plan_number column + building_rights table
│       ├── analytics_enrichment_schema.sql  # SQL: tender_prices + taba_analytics tables + enrichment columns
│       ├── tender_lots_schema.sql     # SQL: tender_lots table + lot extraction columns on tenders
│       ├── watchlist_notes_schema.sql # SQL: notes column on user_watchlist
│       ├── lot_count_schema.sql       # SQL: lot_count + max_lots_per_bidder columns on tenders
│       └── enable_rls_all_tables.sql  # SQL: RLS policies + anon write revocation on all tables
├── tenders_list_*.json             # Daily API snapshots (JSON backup)
├── frontend/                       # Next.js production frontend (deployed on Vercel)
│   ├── src/
│   │   ├── app/                   # Next.js App Router pages (dashboard, management, explorer, analytics, watchlist, login)
│   │   ├── components/            # React components (shadcn/ui + custom)
│   │   ├── design-system/         # Design tokens (colors, typography, spacing, shadows, borders)
│   │   ├── hooks/                 # Data hooks (use-tenders, use-lots, use-watchlist, use-analytics, etc.)
│   │   ├── stores/                # Zustand stores (filter-store, auth-store)
│   │   ├── lib/                   # Utilities, Supabase client, constants, analytics engine
│   │   ├── types/                 # TypeScript types (database.ts)
│   │   └── providers/             # React Query provider
│   ├── vercel.json                # Vercel deployment config
│   ├── package.json               # Next.js 16 + React 19 + Tailwind v4 + Recharts + Supabase
│   └── tsconfig.json              # TypeScript config
├── data/
│   ├── tenders.db                  # SQLite database (gitignored, kept for migration reference)
│   └── details_cache/              # Cached tender detail JSON files
├── tmp/                            # Temporary files (gitignored)
└── venv/                           # Python virtual environment (gitignored)
```
