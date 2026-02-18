# STATUS.md — Project State

**Last updated:** 2026-02-17

---

## Current State

Sprint 1 (Stabilize & Deploy MVP) — **complete**.
Sprint 3 (SQLite Data Persistence) — **complete**.

The dashboard now loads data from SQLite instead of JSON files, with JSON kept as fallback:
- `db.py` — TenderDB class with 6 tables, WAL mode, upsert with change detection
- 10,447 tenders, 30,997 history rows, 3,471 documents migrated from JSON + details_cache
- Daily refresh saves to both SQLite and JSON, syncs documents for active tenders
- `app.py` tries DB first → JSON fallback → API fallback → sample data

**Next**: Deploy to Streamlit Cloud, or start Sprint 4 (Analytical Engine).

---

## Recent Changes

| Date | Change | Files |
|------|--------|-------|
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

1. **No tests** — No test suite exists. pytest tests should be added for data_client and db functions.
2. **Date range filter removed** — The urgency toggle replaces the old date range picker. May want to add it back as an "advanced" option.
3. **Pie chart click-to-filter** — Plotly click events don't wire easily to Streamlit filters. Deferred.
4. **Streamlit Cloud auth** — Not yet configured. Need org email domain.
5. **DB file in git** — tenders.db (7.5 MB) is committed to git. May need git-lfs if it grows significantly.

---

## Next Steps

1. **Deploy to Streamlit Cloud** — Connect repo, configure email allowlist auth.
2. **Verify deployment** — All sections render, data loads from DB correctly.
3. **Sprint 2** — User to define missing features.
4. **Sprint 4** — Analytical engine: scoring + market trends.
5. **Sprint 5** — Alerts: Telegram + email notifications for new tenders/documents.

---

## Database Schema

```
tenders            — 10,447 rows — current state of each tender
tender_history     — 30,997 rows — daily snapshots (4 dates)
tender_documents   —  3,471 rows — document metadata from 444 tenders
tender_scores      — (empty)     — Sprint 4: scoring results
alert_rules        — (empty)     — Sprint 5: alert configuration
alert_history      — (empty)     — Sprint 5: sent notifications
```

---

## Project Structure

```
Gov tender projects/
├── app.py                          # Main Streamlit dashboard
├── config.py                       # Centralized configuration
├── db.py                           # SQLite database layer (NEW - Sprint 3)
├── data_client.py                  # API client, data normalization, caching, DB persistence
├── tender_pdf_extractor.py         # PDF extraction: גוש, חלקה, תב"ע from brochure PDFs
├── mavat_client.py                 # Playwright client: search plans on mavat.iplan.gov.il
├── test_pdf_extractor.py           # Test script for PDF extractor (2 sample PDFs)
├── test_pdf_extractor_batch.py     # Batch test: download + extract from N tender brochures
├── requirements.txt                # Pinned Python dependencies
├── complete_city_codes.py          # CBS settlement code → city name mapping (1,281 entries)
├── complete_city_regions.py        # CBS settlement code → region mapping (1,488 entries)
├── CLAUDE.md                       # Project rules and guidelines
├── PRD.md                          # Product Requirements Document v2.0
├── STATUS.md                       # This file — living project state
├── DATA_FLOW_EXPLANATION.md        # Data pipeline documentation
├── .gitignore                      # Git ignore rules
├── .streamlit/
│   └── config.toml                 # Streamlit theme + server config
├── .github/
│   └── workflows/
│       └── daily_refresh.yml       # GitHub Actions: daily tender snapshot + DB update
├── scripts/
│   ├── refresh_tenders.py          # Data refresh script (used by cron)
│   └── migrate_json_to_db.py       # One-time migration: JSON → SQLite (NEW - Sprint 3)
├── tenders_list_*.json             # Daily API snapshots (JSON backup)
├── data/
│   ├── tenders.db                  # SQLite database (NEW - Sprint 3)
│   └── details_cache/              # Cached tender detail JSON files
├── tmp/                            # Temporary files (gitignored)
└── venv/                           # Python virtual environment (gitignored)
```
