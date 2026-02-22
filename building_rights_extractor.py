"""Extract Section 5 building rights tables from Mavat zoning plan PDFs.

Parses the "טבלת זכויות והוראות בנייה" table which contains building rights
data: designations, plot sizes, building areas, coverage, floors, setbacks, etc.

Handles:
    - Multi-level merged headers (2-3 rows)
    - Reversed Hebrew text from pdfplumber RTL extraction
    - Tables spanning multiple pages
    - Column variations across different plan documents

Usage:
    from building_rights_extractor import extract_building_rights
    result = extract_building_rights(Path("plan.pdf"))
    print(result)
"""

import logging
import re
from pathlib import Path
from typing import Optional

import pdfplumber

logger = logging.getLogger(__name__)

# Maximum pages to scan when searching for Section 5.
MAX_PAGES_TO_SCAN = 30

# Keywords to locate Section 5 header (both normal and reversed Hebrew).
SECTION_KEYWORDS = [
    "טבלת זכויות",
    "תויוכז תלבט",
    "זכויות והוראות בנייה",
    "הינב תוארוהו תויוכז",
    "זכויות והוראות בניה",
    "הינב תוארוהו תויוכז",
]

# Status keywords extracted from the section header.
STATUS_KEYWORDS = {
    "מצב מוצע": "מצב מוצע",
    "עצומ בצמ": "מצב מוצע",
    "מצב מאושר": "מצב מאושר",
    "רשואמ בצמ": "מצב מאושר",
}

# Column mapping: canonical field name → list of Hebrew keyword patterns.
# Each pattern is matched against the REVERSED (original) header text.
# The algorithm reverses the header text first, then matches normal Hebrew.
COLUMN_KEYWORDS: dict[str, list[str]] = {
    "designation": ["יעוד"],
    "use": ["שימוש"],
    "area_condition": ["תאי שטח"],
    "plot_size_absolute": ["מוחלט"],
    "plot_size_minimum": ["מזערי"],
    "building_area_above_main": ["מעל.*עיקרי", "עיקרי.*מעל"],
    "building_area_above_service": ["מעל.*שי?רות", "שי?רות.*מעל"],
    "building_area_below_main": ["מתחת.*עיקרי", "עיקרי.*מתחת"],
    "building_area_below_service": ["מתחת.*שי?רות", "שי?רות.*מתחת"],
    "building_area_total": ["סה.*כ.*שטחי"],
    "coverage_pct": ["תכסית"],
    "housing_units": ["יח.*ד"],
    "building_height": ["גובה"],
    "floors_above": ["קומות.*מעל", "מעל.*קומות"],
    "floors_below": ["קומות.*מתחת", "מתחת.*קומות"],
    "setback_rear": ["אחורי"],
    "setback_front": ["קדמי"],
    "setback_side": ["צידי"],
    "balcony_area": ["מרפסות", "תוספרמ"],
}

# Fields that should be parsed as numeric values.
NUMERIC_FIELDS = {
    "plot_size_absolute", "plot_size_minimum",
    "building_area_above_main", "building_area_above_service",
    "building_area_below_main", "building_area_below_service",
    "building_area_total", "coverage_pct", "housing_units",
    "building_height", "floors_above", "floors_below",
    "setback_rear", "setback_front", "setback_side",
    "balcony_area",
}

# Text fields that should remain as strings.
TEXT_FIELDS = {"designation", "use", "area_condition"}


def _reverse_hebrew(text: str) -> str:
    """Reverse Hebrew text from pdfplumber visual order to logical order.

    Preserves number sequences in their original LTR direction.

    Args:
        text: Reversed Hebrew text from pdfplumber.

    Returns:
        Text in logical Hebrew reading order.
    """
    segments = re.split(r"(\d[\d,./\-]*\d|\d)", text)
    reversed_segments = []
    for seg in reversed(segments):
        if re.match(r"^\d[\d,./\-]*\d$|^\d$", seg):
            reversed_segments.append(seg)
        else:
            reversed_segments.append(seg[::-1])
    return "".join(reversed_segments)


def _clean_cell(value: Optional[str]) -> Optional[str]:
    """Clean a table cell value: strip whitespace, collapse newlines.

    Args:
        value: Raw cell value from pdfplumber.

    Returns:
        Cleaned string, or None if empty.
    """
    if value is None:
        return None
    cleaned = re.sub(r"\s*\n\s*", " ", str(value)).strip()
    return cleaned if cleaned else None


def _parse_numeric(raw: Optional[str]) -> Optional[float]:
    """Parse a numeric value from a cell, stripping footnote references.

    Handles patterns like:
        "2961"    → 2961.0
        "(1) 260" → 260.0
        "(4) 4"   → 4.0
        "(3)"     → None (footnote reference only, no actual value)
        ""        → None

    Args:
        raw: Raw cell string.

    Returns:
        Parsed float, or None if not parseable.
    """
    if not raw:
        return None

    # Strip footnote references: "(N)" at start or end
    cleaned = re.sub(r"\(\d+\)\s*", "", raw).strip()
    cleaned = re.sub(r"\s*\(\d+\)", "", cleaned).strip()

    if not cleaned:
        return None

    # Remove commas from numbers
    cleaned = cleaned.replace(",", "")

    try:
        return float(cleaned)
    except ValueError:
        return None


def _is_header_row(row: list[Optional[str]]) -> bool:
    """Detect if a table row is a header row (not data).

    Header rows have mostly None/text-only cells. Data rows have at least
    some numeric values.

    Args:
        row: Table row (list of cell values).

    Returns:
        True if this looks like a header row.
    """
    if not row:
        return True

    non_none_cells = [c for c in row if c is not None and str(c).strip()]
    if not non_none_cells:
        return True

    numeric_count = 0
    for cell in non_none_cells:
        cell_str = str(cell).strip()
        # Strip footnote references before checking
        stripped = re.sub(r"\(\d+\)\s*", "", cell_str).strip()
        stripped = re.sub(r"\s*\(\d+\)", "", stripped).strip()
        if stripped and re.match(r"^[\d,.\-\s]+$", stripped):
            numeric_count += 1

    # If less than 30% of non-None cells are numeric, it's likely a header
    return numeric_count < len(non_none_cells) * 0.3


def _forward_fill_row(row: list[Optional[str]]) -> list[Optional[str]]:
    """Forward-fill None values in a row (left to right).

    Used to expand merged header cells: a merged cell has a value in its
    first column and None in subsequent columns of the span.

    Args:
        row: Header row with None values from merged cells.

    Returns:
        Row with None values replaced by the previous non-None value.
    """
    filled = list(row)
    last_val = None
    for i, val in enumerate(filled):
        if val is not None and str(val).strip():
            last_val = val
        elif last_val is not None:
            filled[i] = last_val
    return filled


def _merge_header_rows(
    header_rows: list[list[Optional[str]]],
) -> list[str]:
    """Merge multi-level header rows into flat column names.

    Strategy:
    1. Forward-fill top header row unconditionally (expand merged cells)
    2. Forward-fill sub-header rows only within the same parent span
    3. For each column, concatenate non-None values from all header rows
    4. Reverse the Hebrew text to get normal reading order

    Args:
        header_rows: List of header rows (2-3 rows typically).

    Returns:
        List of flat column name strings (in normal Hebrew).
    """
    if not header_rows:
        return []

    num_cols = max(len(row) for row in header_rows)

    # Forward-fill the top row unconditionally
    filled_top = _forward_fill_row(header_rows[0])
    filled_top += [None] * (num_cols - len(filled_top))

    padded_rows = [filled_top]

    # For sub-header rows: only forward-fill within the same parent span.
    # This prevents "גודל מגרש מוחלט" from leaking into "תאי שטח" etc.
    for row_idx in range(1, len(header_rows)):
        row = list(header_rows[row_idx])
        row += [None] * (num_cols - len(row))
        filled = list(row)
        last_val = None
        last_parent = None

        for col in range(num_cols):
            parent = filled_top[col]
            cell = row[col]
            if cell is not None and str(cell).strip():
                last_val = cell
                last_parent = parent
            elif last_val is not None and parent is not None and parent == last_parent:
                # Same parent header → safe to forward-fill
                filled[col] = last_val
            else:
                # Different parent or no parent → reset
                last_val = None
                last_parent = parent

        padded_rows.append(filled)

    merged_headers = []
    for col_idx in range(num_cols):
        parts = []
        for row in padded_rows:
            val = _clean_cell(row[col_idx]) if col_idx < len(row) else None
            if val and val not in parts:
                parts.append(val)

        # Join parts and reverse Hebrew to get normal reading order
        raw_header = " | ".join(parts) if parts else ""
        reversed_header = _reverse_hebrew(raw_header) if raw_header else ""
        merged_headers.append(reversed_header)

    return merged_headers


def _map_columns(
    merged_headers: list[str],
) -> dict[int, str]:
    """Map column indices to canonical field names using keyword matching.

    Args:
        merged_headers: Flat column header strings (in normal Hebrew).

    Returns:
        Dict mapping column index → canonical field name.
    """
    column_map: dict[int, str] = {}
    used_fields: set[str] = set()

    for col_idx, header in enumerate(merged_headers):
        if not header:
            continue

        for field_name, keywords in COLUMN_KEYWORDS.items():
            if field_name in used_fields:
                continue

            for keyword in keywords:
                if re.search(keyword, header):
                    column_map[col_idx] = field_name
                    used_fields.add(field_name)
                    logger.debug(
                        "Mapped col %d → %s (header: %s, keyword: %s)",
                        col_idx, field_name, header, keyword,
                    )
                    break

            if field_name in used_fields:
                break

    return column_map


def _find_section5_pages(pdf: pdfplumber.PDF) -> list[dict]:
    """Find pages containing Section 5 and extract status.

    Args:
        pdf: Open pdfplumber PDF object.

    Returns:
        List of dicts with 'page_idx' and 'status' keys.
    """
    found = []
    pages_to_scan = min(len(pdf.pages), MAX_PAGES_TO_SCAN)

    for page_idx in range(pages_to_scan):
        text = pdf.pages[page_idx].extract_text() or ""

        has_section = any(kw in text for kw in SECTION_KEYWORDS)
        if not has_section:
            continue

        # Extract status
        status = None
        for kw, normalized in STATUS_KEYWORDS.items():
            if kw in text:
                status = normalized
                break

        found.append({"page_idx": page_idx, "status": status})
        logger.info(
            "Found Section 5 on page %d (status: %s)", page_idx + 1, status,
        )

    return found


def _select_rights_table(
    tables: list[list[list[Optional[str]]]],
) -> Optional[list[list[Optional[str]]]]:
    """Select the building rights table from all tables on a page.

    Picks the table with the most columns × rows, filtering out tiny tables
    (like the section header table which has 1 row × 2 cols).

    Args:
        tables: All tables extracted from a page.

    Returns:
        The selected table, or None if no suitable table found.
    """
    best_table = None
    best_score = 0

    for table in tables:
        if not table or len(table) < 3:
            continue

        num_cols = max(len(row) for row in table)
        if num_cols < 5:
            continue

        score = len(table) * num_cols
        if score > best_score:
            best_score = score
            best_table = table

    return best_table


def _extract_table_from_pages(
    pdf: pdfplumber.PDF,
    start_page_idx: int,
) -> Optional[list[list[Optional[str]]]]:
    """Extract the building rights table, handling multi-page continuation.

    Starts from the page where Section 5 was found, then checks subsequent
    pages for table continuation (same column count, has header rows).

    Args:
        pdf: Open pdfplumber PDF object.
        start_page_idx: Page index where Section 5 was found.

    Returns:
        Combined table rows, or None if no table found.
    """
    # Extract from the main page
    page = pdf.pages[start_page_idx]
    tables = page.extract_tables()
    main_table = _select_rights_table(tables)

    if not main_table:
        logger.warning("No suitable table found on page %d", start_page_idx + 1)
        return None

    num_cols = max(len(row) for row in main_table)
    logger.info(
        "Main table on page %d: %d rows × %d cols",
        start_page_idx + 1, len(main_table), num_cols,
    )

    # Check subsequent pages for continuation
    combined = list(main_table)
    for next_idx in range(start_page_idx + 1, min(len(pdf.pages), start_page_idx + 15)):
        next_text = pdf.pages[next_idx].extract_text() or ""

        # If next page has a new Section header, stop
        if any(kw in next_text for kw in SECTION_KEYWORDS):
            break

        next_tables = pdf.pages[next_idx].extract_tables()
        next_table = _select_rights_table(next_tables)

        if not next_table:
            break

        next_cols = max(len(row) for row in next_table)
        if next_cols != num_cols:
            break

        # Skip header rows on the continuation page
        data_start = 0
        for row_idx, row in enumerate(next_table):
            if not _is_header_row(row):
                data_start = row_idx
                break

        continuation_rows = next_table[data_start:]
        if continuation_rows:
            logger.info(
                "Continuation on page %d: %d data rows",
                next_idx + 1, len(continuation_rows),
            )
            combined.extend(continuation_rows)

    return combined


def _parse_table(
    raw_table: list[list[Optional[str]]],
) -> tuple[list[dict], list[str], dict[int, str]]:
    """Parse a raw table into structured row dicts.

    Detects header rows, merges them, maps columns, and parses data rows.

    Args:
        raw_table: Raw table from pdfplumber (list of rows).

    Returns:
        Tuple of (parsed_rows, merged_headers, column_map).
    """
    # Detect header rows
    header_rows = []
    data_start = 0
    for row_idx, row in enumerate(raw_table):
        if _is_header_row(row):
            header_rows.append(row)
            data_start = row_idx + 1
        else:
            break

    if not header_rows:
        logger.warning("No header rows detected in table")
        return [], [], {}

    logger.info("Detected %d header rows", len(header_rows))

    # Merge headers and map columns
    merged_headers = _merge_header_rows(header_rows)
    column_map = _map_columns(merged_headers)

    if not column_map:
        logger.warning(
            "No columns mapped. Headers: %s", merged_headers,
        )
        return [], merged_headers, {}

    logger.info("Column mapping: %s", column_map)

    # Parse data rows
    parsed_rows = []
    for row_idx in range(data_start, len(raw_table)):
        row = raw_table[row_idx]

        # Skip empty rows
        if not row or all(
            c is None or str(c).strip() == "" for c in row
        ):
            continue

        row_data: dict[str, object] = {}
        raw_data: dict[str, Optional[str]] = {}

        for col_idx, field_name in column_map.items():
            if col_idx >= len(row):
                continue

            raw_val = _clean_cell(row[col_idx])
            if raw_val:
                # Reverse Hebrew for text fields
                raw_val_reversed = _reverse_hebrew(raw_val)
            else:
                raw_val_reversed = raw_val

            raw_data[field_name] = raw_val

            if field_name in NUMERIC_FIELDS:
                row_data[field_name] = _parse_numeric(raw_val)
            elif field_name in TEXT_FIELDS:
                row_data[field_name] = raw_val_reversed
            else:
                row_data[field_name] = raw_val_reversed

        # Only include rows with at least some data
        if any(v is not None for v in row_data.values()):
            row_data["_raw"] = raw_data
            parsed_rows.append(row_data)

    return parsed_rows, merged_headers, column_map


def extract_building_rights(
    pdf_path: Path | str,
    plan_number: Optional[str] = None,
) -> dict:
    """Extract Section 5 building rights table from a Mavat plan PDF.

    Main entry point. Locates Section 5, extracts and parses the table,
    returns structured data.

    Args:
        pdf_path: Path to the PDF file.
        plan_number: Optional plan number for the result metadata.

    Returns:
        Dict with keys: plan_number, status, rows, source_page,
        raw_headers, column_map, extraction_method, success, errors.
    """
    pdf_path = Path(pdf_path)
    result: dict[str, object] = {
        "plan_number": plan_number or pdf_path.stem,
        "status": None,
        "rows": [],
        "source_page": None,
        "raw_headers": [],
        "column_map": {},
        "extraction_method": "pdfplumber_lattice",
        "success": False,
        "errors": [],
    }

    if not pdf_path.exists():
        result["errors"] = [f"File not found: {pdf_path}"]
        logger.error("File not found: %s", pdf_path)
        return result

    logger.info("Extracting building rights from: %s", pdf_path.name)

    try:
        with pdfplumber.open(pdf_path) as pdf:
            # Step 1: Find Section 5
            section_pages = _find_section5_pages(pdf)
            if not section_pages:
                result["errors"] = ["Section 5 not found in PDF"]
                logger.warning("Section 5 not found in %s", pdf_path.name)
                return result

            # Try each section page — early pages may mention
            # "טבלת זכויות" in text without the actual data table.
            for section in section_pages:
                result["status"] = section["status"]
                result["source_page"] = section["page_idx"] + 1

                # Step 2: Extract table (with multi-page continuation)
                raw_table = _extract_table_from_pages(
                    pdf, section["page_idx"],
                )
                if not raw_table:
                    logger.info(
                        "No usable table on page %d, trying next",
                        section["page_idx"] + 1,
                    )
                    continue

                # Step 3: Parse table
                rows, headers, col_map = _parse_table(raw_table)
                if rows:
                    result["rows"] = rows
                    result["raw_headers"] = headers
                    result["column_map"] = {
                        str(k): v for k, v in col_map.items()
                    }
                    result["success"] = True
                    logger.info(
                        "Extracted %d rows with %d columns from %s (page %d)",
                        len(rows), len(col_map), pdf_path.name,
                        section["page_idx"] + 1,
                    )
                    break

                logger.info(
                    "No columns mapped on page %d, trying next",
                    section["page_idx"] + 1,
                )

            if not result["success"]:
                result["errors"] = ["Table found but no data rows parsed"]
                logger.warning("No data rows parsed from %s", pdf_path.name)

    except Exception as e:
        error_msg = f"Extraction failed: {e}"
        result["errors"] = [error_msg]
        logger.exception(error_msg)

    return result


if __name__ == "__main__":
    import json
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
    )

    # Accept PDF path as argument, or use demo files
    if len(sys.argv) > 1:
        files = [Path(f) for f in sys.argv[1:]]
    else:
        files = [Path("demo tender_1.pdf"), Path("demo tender_2.pdf")]

    for pdf_file in files:
        if pdf_file.exists():
            print(f"\n{'=' * 60}")
            print(f"Processing: {pdf_file.name}")
            print(f"{'=' * 60}")
            extracted = extract_building_rights(pdf_file)
            # Remove _raw from display for cleaner output
            display = dict(extracted)
            display_rows = []
            for row in extracted.get("rows", []):
                clean_row = {k: v for k, v in row.items() if k != "_raw"}
                display_rows.append(clean_row)
            display["rows"] = display_rows
            print(json.dumps(display, ensure_ascii=False, indent=2))
        else:
            print(f"File not found: {pdf_file}")
