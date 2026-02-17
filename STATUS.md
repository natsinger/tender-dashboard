# STATUS.md — Project State

**Last updated:** 2026-02-17

---

## Current State

Sprint 1 (Stabilize & Deploy MVP) — **in progress**.

The codebase has been refactored for production deployment:
- Centralized configuration via `config.py` (loads from st.secrets / .env / defaults)
- All `print()` statements replaced with `logging` module
- Retry logic with exponential backoff on all API calls (3 attempts, 2s base delay)
- Pinned dependencies in `requirements.txt` with exact versions
- Removed outdated `land_tenders_dashboard/` directory
- GitHub Actions daily refresh workflow added
- Streamlit Cloud theme configured in `.streamlit/config.toml`

**Next**: Push to GitHub, connect Streamlit Cloud, configure email allowlist auth.

---

## Recent Changes

| Date | Change | Files |
|------|--------|-------|
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

1. **No tests** — No test suite exists. pytest tests should be added for data_client functions.
2. **Date range filter removed** — The urgency toggle replaces the old date range picker. May want to add it back as an "advanced" option.
3. **Pie chart click-to-filter** — Plotly click events don't wire easily to Streamlit filters. Deferred.
4. **Streamlit Cloud auth** — Not yet configured. Need org email domain.

---

## Next Steps

1. **Push to GitHub** — Commit Sprint 1 changes on a feature branch.
2. **Deploy to Streamlit Cloud** — Connect repo, configure email allowlist auth.
3. **Verify deployment** — All sections render, data loads correctly.
4. **Sprint 2** — User to define missing features.

---

## Project Structure

```
Gov tender projects/
├── app.py                          # Main Streamlit dashboard
├── config.py                       # Centralized configuration (NEW)
├── data_client.py                  # API client, data normalization, caching
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
│       └── daily_refresh.yml       # GitHub Actions: daily tender snapshot
├── scripts/
│   └── refresh_tenders.py          # Data refresh script (used by cron)
├── tenders_list_*.json             # Daily API snapshots
├── data/
│   └── details_cache/              # Cached tender detail JSON files
├── tmp/                            # Temporary files (gitignored)
└── venv/                           # Python virtual environment (gitignored)
```
