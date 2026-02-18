# TECH_SPEC.md — Technical Specification

**Version**: 1.0  
**Last Updated**: 2026-02-15

---

## 1. Architecture Overview

### 1.1 High-Level Design (Phase 1 & 2)

The system is a local-first Python application with a Streamlit frontend. It follows a modular design where data acquisition, processing, and presentation are decoupled.

```mermaid
graph TD
    User[User (CEO)] -->|Interacts| Streamlit[Streamlit Dashboard (app.py)]
    
    subgraph "Data Layer"
        Streamlit -->|Requests Data| DataClient[Data Client (data_client.py)]
        DataClient -->|Fetches| RamiAPI[Israel Land Authority API]
        DataClient -->|Caches| LocalCache[JSON Cache (data/)]
    end
    
    subgraph "Integration Layer (Phase 2)"
        Streamlit -->|Triggers| MavatClient[Mavat Client (mavat_client.py)]
        MavatClient -->|Automates| MavatWeb[mavat.iplan.gov.il]
        MavatClient -->|Downloads| PDFDocs[Plan Documents (PDFs)]
        PDFDocs -->|Parsed by| PDFExtractor[PDF Extractor]
        PDFExtractor -->|Structured Data| Streamlit
    end
```

### 1.2 core Components

| Component | Responsibility | Key Libraries |
|-----------|----------------|---------------|
| `app.py` | Main entry point. Handles UI rendering, state management, and user interaction. | `streamlit`, `pandas`, `plotly` |
| `data_client.py` | Interface for fetching tender data, normalizing it, and managing the local cache. Handles retry logic and API quirks. | `requests`, `pandas` |
| `mavat_client.py` | Headless browser automation to search for plans and download "horot" (instructions) documents. | `playwright` |
| `tender_pdf_extractor.py` | Extracts structured data (text, tables) from PDF brochures and plan documents. | `pdfplumber`, `pymupdf` (fitz) |

---

## 2. Data Models

### 2.1 Tender (Main Entity)
*Primary source: RAMI API*

| Field Name | Type | Description | Source Field (API) |
|------------|------|-------------|--------------------|
| `id` | str | Unique tender ID | `MasMichraz` |
| `name` | str | Tender description | `ShemMichraz` |
| `status` | str | Current status (Active/Closed) | `StatusMichraz` |
| `city` | str | City name | `ShemYishuv` |
| `region` | str | Region name (North, Center, etc.) | `Merhav` |
| `type_id` | int | Tender type code | `SugMichraz` |
| `type_desc` | str | Tender type description | From `general_tables.json` |
| `units` | int | Total housing units | `YichiydotDiour` |
| `closing_date` | date | Deadline for submission | `TaarichSium` |
| `brochure_exists`| bool | Is the brochure published? | `PublishedChoveret` |
| `plan_num` | str | Statutory plan number (Taba) | `MisparTochnit` |

### 2.2 Plan Document (Phase 2)
*Primary source: Mavat Website*

| Field Name | Type | Description |
|------------|------|-------------|
| `plan_num` | str | matching `MisparTochnit` |
| `mp_id` | int | Internal Mavat ID |
| `instruction_pdf`| path | Path to local PDF file |
| `zoning_data` | dict | Extracted zoning info (height, density, usage) |
| `timelines` | list | Extracted milestones/dates |

---

## 3. External Interfaces

### 3.1 Israel Land Authority (RAMI) API
*   **Endpoint**: `https://apps.land.gov.il/MichrazimSite/api/Tender/GetTenders`
*   **Method**: `GET`
*   **Auth**: None required (public)
*   **Response**: JSON array of tender objects.

### 3.2 Mavat Planning Portal
*   **URL**: `https://mavat.iplan.gov.il`
*   **Interaction**: via Playwright (no public API).
*   **Flow**:
    1.  `GET /SV1` (Search Page)
    2.  `POST /rest/api/sv3/Search` (Internal API via browser)
    3.  `GET /SV4/1/{mp_id}/310` (Plan Page)

---

## 4. Folder Structure & Hygiene

*   `data/`: Persistent data (processed).
*   `tmp/`: Temporary downloads, logs, and raw debug files (gitignored).
*   `logs/`: Execution logs (gitignored).
*   `assets/`: Static assets (images, CSS).
*   `tests/`: Unit and integration tests.

---

## 5. Development Workflow

1.  **Environment**: Python 3.10+ virtual environment (`venv`).
2.  **Dependencies**: Managed in `requirements.txt`.
3.  **Linting**: `ruff` for linting and formatting.
4.  **Testing**: `pytest` for unit tests.

---

## 6. Future Considerations (Phase 3)

*   **Migration to React**: Shift `app.py` logic to a FastAPI backend.
*   **Database**: Replace local JSON caching with SQLite or PostgreSQL.
*   **Authentication**: Add user auth for executive dashboard access.
