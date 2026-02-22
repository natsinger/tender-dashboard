"""Extracts lot-level data (מתחמים) from tender brochure PDFs.

Parses brochure Sections 1-3 to extract per-lot details including housing
unit counts (target-price vs free-market), pricing, zoning, and bid limits.
Uses pdfplumber for PDF parsing and handles reversed Hebrew RTL text.

Handles two document formats:
    1. Full brochure (חוברת) — multi-page with formal Section 1/2/3 headers.
    2. First publication (פרסום ראשון) — 1-2 page announcements with inline
       plan/designation data and no formal section headers.

Usage:
    extractor = BrochureLotExtractor()
    result = extractor.extract_all(pdf_bytes, tender_id=12345)
    print(result)

Tables populated:
    tender_lots — one row per lot per tender (via db.upsert_lots)
    tenders     — max_lots_per_bidder, lot_extraction_status (via db methods)
"""

import io
import logging
import re
from typing import Optional

import pdfplumber

from tender_pdf_extractor import (
    PLAN_NUMBER_PATTERN,
    _reverse_hebrew,
)

logger = logging.getLogger(__name__)

# Maximum pages to scan for lot data (sections 1-3 are typically within
# the first 20 pages of a brochure).
MAX_PAGES_TO_SCAN: int = 25

# ---------------------------------------------------------------------------
# Section 1 header keywords — both normal and reversed Hebrew forms.
# These identify the lot summary table in Section 1 of the brochure.
# ---------------------------------------------------------------------------
SECTION1_HEADERS = {
    "lot_number": ["מתחם", "םחתמ", "ם חתמ", "מס' מתחם"],
    "plot_numbers": [
        "מגרש", "שרגמ", "ש רגמ", "מס' מגרש",
        "םישרגמ",   # reversed plural: שרגמים -> םישרגמ
        "שרגמ",     # reversed: מגרש
    ],
    "helka": ["חלקה", "הקלח", "תוקלח"],
    "gush": ["גוש", "שוג"],
    "area_sqm": ["שטח", "חטש"],
    "units_target_price": [
        "מחיר מטרה", "הרטמ ריחמ",
        "יח\"ד.*מטרה", "ד\"חי.*הרטמ",
        "הרטמ",  # single-word fallback for reversed multi-line headers
        "הרכשהל",  # reversed: להשכרה (for rental) — used in type 6 brochures
    ],
    "units_free_market": [
        "שוק חופשי", "ישפוח קוש",
        "יח\"ד.*חופשי", "ד\"חי.*ישפוח",
        "ישפוח",  # single-word fallback for reversed multi-line headers
        "הריכמל",  # reversed: למכירה (for sale) — used in type 6 brochures
    ],
    "total_units": [
        "ד\"חי רפסמ",   # reversed: מספר יח"ד (number of units)
        "מספר יח\"ד",   # normal: מספר יח"ד
        "ד\"חי 'סמ",    # reversed: מס' יח"ד
        "ד\"חי",         # single-word: יח"ד (housing units)
    ],
    "min_price": [
        "מחיר מינימום", "םומינימ ריחמ",
        "םומינימ",  # single-word fallback for reversed multi-line headers
        "מינימום",
    ],
    "guarantee_amount": ["ערבות", "תוברע"],
    "sqm_value_appraisal": ["שווי.*שומה", "המוש.*יווש", "יווש.*המוש"],
    "sqm_value_current": ["שומה עדכנית", "תינכדע המוש", "תינכדע"],
    "discount_amount": ["הנחה", "החנה"],
}

# Section 2 keywords for zoning data.
SECTION2_KEYWORDS = {
    "zoning_plan": ["תב\"ע", "תכנית", "ע\"בת", "תינכת"],
    "zoning_designation": ["ייעוד", "דועיי"],
}

# Section 2 header patterns — both normal and reversed Hebrew.
SECTION2_HEADERS = [
    "היבט תכנוני ופיזי",
    "יזיפו ינונכת טביה",
    "תכנוני ופיזי",
    "ינונכת טביה",
    "פרק 2",
    "2 קרפ",
    "סעיף 2",
    "2 ףיעס",
]

# Section 3 header patterns used to bound Section 2 text extraction.
SECTION3_HEADERS = [
    "היבט כלכלי",
    "ילכלכ טביה",
    "פרק 3",
    "3 קרפ",
    "סעיף 3",
    "3 ףיעס",
    "תנאי סף",
    "ףס יאנת",
]

# Zoning designation keywords for land-use classification.
ZONING_DESIGNATION_KEYWORDS: list[str] = [
    "מגורים",
    "מסחר",
    "תעשיה",
    "מעורב",
    "ציבורי",
    "תיירות",
    "מלונאות",
    "משרדים",
    "תעסוקה",
    "חקלאי",
]

# Reversed forms of zoning designation keywords (pdfplumber RTL output).
ZONING_DESIGNATION_KEYWORDS_REVERSED: list[str] = [
    "םירוגמ",
    "רחסמ",
    "היישעת",
    "ברועמ",
    "ירוביצ",
    "תורייט",
    "תואנולמ",
    "םידרשמ",
    "הקוסעת",
    "יאלקח",
]

# Compiled pattern reusing PLAN_NUMBER_PATTERN from tender_pdf_extractor.
_PLAN_NUMBER_RE = re.compile(PLAN_NUMBER_PATTERN)

# Pattern to find lot/mitham numbers near plan references.
_LOT_NUMBER_RE = re.compile(r"(?:מתחם|םחתמ)\s*[:.]?\s*(\d+)")

# Date pattern to filter false-positive plan numbers.
_DATE_FILTER_RE = re.compile(
    r"^\d{1,2}/\d{1,2}/(?:19|20)\d{2}$"
    r"|^\d{1,2}\.\d{1,2}\.(?:19|20)\d{2}$"
)

# ---------------------------------------------------------------------------
# Inline zoning patterns — for first-publication (פרסום ראשון) documents
# that embed plan + designation in body text without section headers.
# ---------------------------------------------------------------------------

# Reversed Hebrew: "PLAN_NUMBER [qualifier] תינכות/תינכת הלח םישרגמה/םחתמה/ןיעקרקמה לע"
# (Normal: "על המקרקעין/השרגמים/המתחם חלה תכנית [qualifier] PLAN_NUMBER")
# The qualifier is optional — e.g. "מ"מת" (תמ"מ), "ת"מם" etc.
_INLINE_PLAN_RE = re.compile(
    r"([\dא-ת][\dא-ת/\-]{3,30})\s+"
    r"(?:ת\"מם|מ\"מת|ם\"מת)?\s*"        # optional qualifier like מ"מת / תמ"מ
    r"(?:תינכו?ת)\s+הלח\s+"
    r"(?:םישרגמה|םחתמה|ןיעקרקמה)\s+לע"
)

# Reversed Hebrew: "DESIGNATION וניה םישרגמה/םחתמה דועי/דועיי"
# (Normal: "ייעוד/יעוד השרגמים/המתחם הינו DESIGNATION")
_INLINE_DESIGNATION_RE = re.compile(
    r"([^\n,]{2,40})\s+וניה\s+(?:םישרגמה|םחתמה)\s+דועיי?"
)

# Reversed Hebrew: "םימחתמ N -ב" = "ב-N מתחמים" (in N lots)
_INLINE_LOT_COUNT_RE = re.compile(
    r"םימחתמ\s+(\d+)\s*-ב"
)

# Reversed Hebrew: "דחא םחתמב" = "במתחם אחד" (in one lot)
_INLINE_SINGLE_LOT_RE = re.compile(
    r"דחא\s+םחתמב"
)

# Reversed Hebrew for unit count: "ד"חי NNN" = "NNN יח"ד" (NNN housing units)
_INLINE_UNITS_RE = re.compile(
    r"""ד"חי\s+([\d,]+)""",
)

# Section 3 keywords for bid limits.
SECTION3_BID_LIMIT_KEYWORDS = [
    "מתחמים שניתן להגיש",
    "מגבלת מתחמים",
    "שירגהל ןתינש םימחתמ",
    "מספר מתחמים מרבי",
]

# Regex to extract a number from bid-limit text.
BID_LIMIT_NUMBER_PATTERN = re.compile(r"(\d+)")

# ---------------------------------------------------------------------------
# Section 3 header patterns — used to locate Section 3 ("מסלול מכרז").
# Also matches "היבט כלכלי" (economic aspect) and "תנאי סף" (threshold
# conditions) which appear in first-publication documents.
# ---------------------------------------------------------------------------
SECTION3_HEADER_RE: list[re.Pattern[str]] = [
    re.compile(r"מסלול\s+מכרז"),        # Normal Hebrew
    re.compile(r"זרכמ\s+לולסמ"),        # Reversed Hebrew
    re.compile(r"היבט\s+כלכלי"),        # Normal: היבט כלכלי
    re.compile(r"ילכלכ\s+טביה"),        # Reversed: ילכלכ טביה
    re.compile(r"תנאי\s+(?:ה)?סף"),     # Normal: תנאי סף / תנאי הסף
    re.compile(r"ף[סה]+\s+יאנת"),       # Reversed: ףסה יאנת / ףס יאנת
]

# Section 4 header patterns — used as an end boundary for Section 3 text.
SECTION4_HEADER_RE: list[re.Pattern[str]] = [
    re.compile(r"סעיף\s+4"),
    re.compile(r"פרק\s+4"),
    re.compile(r"4\s+ףיעס"),
    re.compile(r"4\s+קרפ"),
]

# ---------------------------------------------------------------------------
# Bid-limit regex patterns — checked in priority order (specific limits
# before unlimited).
# ---------------------------------------------------------------------------

# Hebrew number-word mapping (normal and reversed forms).
HEBREW_NUMBER_WORDS: dict[str, int] = {
    "אחד": 1,
    "דחא": 1,       # reversed
    "שני": 2,
    "ינש": 2,       # reversed
    "שניים": 2,
    "םיינש": 2,     # reversed
    "שלושה": 3,
    "השולש": 3,     # reversed
    "שלוש": 3,
    "שולש": 3,      # reversed
    "ארבעה": 4,
    "העברא": 4,     # reversed
    "ארבע": 4,
    "עברא": 4,      # reversed
    "חמישה": 5,
    "השימח": 5,     # reversed
    "חמש": 5,
    "שמח": 5,       # reversed
}

# Build a regex alternation of all Hebrew number words (longest first to
# avoid partial matches).
_HEBREW_NUM_WORDS_ALT = "|".join(
    sorted(HEBREW_NUMBER_WORDS.keys(), key=len, reverse=True)
)

# Specific-limit patterns (return an int extracted from the match group).
BID_LIMIT_SPECIFIC_PATTERNS: list[re.Pattern[str]] = [
    # Normal: "למתחם אחד בלבד"
    re.compile(
        rf"ל(?:מתחם|םחתמ)\s+({_HEBREW_NUM_WORDS_ALT})\s*(?:בלבד|דבלב)?",
    ),
    # Reversed word order: "דבלב דחא םחתמל" — word order is flipped and ל
    # is suffixed to םחתמ.  Number word precedes םחתמל in string position.
    re.compile(
        rf"(?:דבלב|בלבד)?\s*({_HEBREW_NUM_WORDS_ALT})\s+(?:םחתמ|מתחם)ל",
    ),
    # Normal: "לשני מתחמים" / "לשלושה מתחמים" — word-number before מתחמים
    re.compile(
        rf"ל({_HEBREW_NUM_WORDS_ALT})\s+(?:מתחמים|םימחתמ)",
    ),
    # Reversed: "םימחתמ ינשל" — word-number fused with ל suffix
    re.compile(
        rf"(?:מתחמים|םימחתמ)\s+({_HEBREW_NUM_WORDS_ALT})ל",
    ),
    # Normal: "ל-X מתחמים" — numeric with dash prefix
    re.compile(
        r"ל[\-–](\d+)\s+(?:מתחמים|םימחתמ)",
    ),
    # Reversed numeric: "םימחתמ X-ל"
    re.compile(
        r"(?:מתחמים|םימחתמ)\s+(\d+)[\-–]ל",
    ),
]

# Unlimited patterns (return None — no limit).
BID_LIMIT_UNLIMITED_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"ללא\s+הגבלה"),           # ללא הגבלה
    re.compile(r"הלבגה\s+אלל"),           # reversed: הלבגה אלל
    re.compile(r"לכל\s+ה?מתחמים"),        # לכל המתחמים / לכל מתחמים
    re.compile(r"ה?םימחתמ\s+לכל"),        # reversed: םימחתמה לכל / םימחתמ לכל
]


def _header_matches(cell_text: str, keyword_list: list[str]) -> bool:
    """Check if a table cell header matches any keyword variant.

    Supports both plain substring matching and regex patterns (keywords
    containing regex metacharacters like ``.*`` or ``\\d``).

    Args:
        cell_text: The text content of a table header cell.
        keyword_list: List of keyword variants to match against.

    Returns:
        True if any keyword is found in the cell text.
    """
    if not cell_text:
        return False
    cleaned = " ".join(cell_text.split())
    for kw in keyword_list:
        # If the keyword contains regex metacharacters, use re.search;
        # otherwise use fast substring match.
        if any(ch in kw for ch in r".*+?[](){}|\\^$"):
            if re.search(kw, cleaned):
                return True
        elif kw in cleaned:
            return True
    return False


# ---------------------------------------------------------------------------
# Minimum number of matched columns for a table to qualify as the lot table.
# ---------------------------------------------------------------------------
MIN_SECTION1_COLUMNS: int = 2

# Critical fields whose absence lowers row confidence.
CRITICAL_FIELDS: list[str] = [
    "lot_number",
    "units_target_price",
    "units_free_market",
]

# Fields that should be parsed as integers.
INT_FIELDS: set[str] = {
    "lot_number",
    "units_target_price",
    "units_free_market",
    "total_units",
}

# Fields that should be parsed as floats.
FLOAT_FIELDS: set[str] = {
    "area_sqm",
    "min_price",
    "guarantee_amount",
    "sqm_value_appraisal",
    "sqm_value_current",
    "discount_amount",
}

# Fields left as raw strings (only cleaned).
STRING_FIELDS: set[str] = {
    "plot_numbers",
    "helka",
    "gush",
}


def _find_section1_column_mapping(
    header_cells: list[Optional[str]],
) -> dict[str, int]:
    """Map SECTION1_HEADERS field names to column indices.

    Handles multi-line cell text by collapsing whitespace before matching.

    Args:
        header_cells: List of header cell strings (possibly multi-line).

    Returns:
        Dict mapping field name to column index.
    """
    mapping: dict[str, int] = {}
    for col_idx, cell in enumerate(header_cells):
        if cell is None:
            continue
        for field_name, keywords in SECTION1_HEADERS.items():
            if field_name not in mapping and _header_matches(cell, keywords):
                mapping[field_name] = col_idx
                break  # One field per column
    return mapping


def _detect_header_rows(
    table: list[list[Optional[str]]],
) -> tuple[list[Optional[str]], int]:
    """Detect and merge multi-line header rows into a single header.

    pdfplumber sometimes splits wrapped column headers across multiple rows.
    This function checks if merging the first two rows yields more column
    matches than using the first row alone.

    Args:
        table: Raw 2D table from pdfplumber (list of rows).

    Returns:
        Tuple of (merged_header_cells, num_header_rows_consumed).
    """
    if not table:
        return [], 0

    row0 = table[0]
    mapping_row0 = _find_section1_column_mapping(row0)

    if len(table) < 2:
        return row0, 1

    # Try merging row 0 + row 1
    row1 = table[1]
    merged: list[Optional[str]] = []
    max_cols = max(len(row0), len(row1))
    for i in range(max_cols):
        c0 = row0[i] if i < len(row0) else None
        c1 = row1[i] if i < len(row1) else None
        if c0 and c1:
            merged.append(f"{c0} {c1}")
        elif c0:
            merged.append(c0)
        elif c1:
            merged.append(c1)
        else:
            merged.append(None)

    mapping_merged = _find_section1_column_mapping(merged)

    # Use merged header if it matches strictly more columns.
    if len(mapping_merged) > len(mapping_row0):
        logger.debug(
            "Multi-line header detected: row0 matched %d, merged matched %d",
            len(mapping_row0),
            len(mapping_merged),
        )
        return merged, 2

    return row0, 1


def _clean_cell_value(value: Optional[str]) -> Optional[str]:
    """Strip whitespace, collapse newlines, and normalize a cell value.

    Args:
        value: Raw cell string from pdfplumber.

    Returns:
        Cleaned string, or None if empty / dash-only.
    """
    if value is None:
        return None
    cleaned = " ".join(str(value).split()).strip()
    if not cleaned or cleaned == "-" or cleaned == "--":
        return None
    return cleaned


def _parse_row(
    row: list[Optional[str]],
    col_mapping: dict[str, int],
) -> Optional[dict]:
    """Parse a single data row into a lot dict using the column mapping.

    Applies type-appropriate parsing for each field: int fields via
    ``_parse_int``, float fields via ``_parse_numeric``, and string fields
    via ``_clean_cell_value``.  Adds a ``confidence`` score (0.0-1.0)
    based on how many critical fields were successfully parsed.

    Args:
        row: List of cell values for one table row.
        col_mapping: Dict mapping field names to column indices.

    Returns:
        Parsed lot dict, or None if the row is entirely empty.
    """
    lot: dict[str, object] = {}
    any_data = False

    for field_name, col_idx in col_mapping.items():
        if col_idx >= len(row):
            lot[field_name] = None
            continue

        raw = _clean_cell_value(row[col_idx])

        if field_name in INT_FIELDS:
            parsed = _parse_int(raw)
            lot[field_name] = parsed
            if parsed is not None:
                any_data = True
        elif field_name in FLOAT_FIELDS:
            parsed_f = _parse_numeric(raw)
            lot[field_name] = parsed_f
            if parsed_f is not None:
                any_data = True
        else:
            # String field (e.g. plot_numbers)
            lot[field_name] = raw
            if raw is not None:
                any_data = True

    if not any_data:
        return None

    # Confidence: fraction of critical fields that were parsed.
    critical_present = sum(
        1 for f in CRITICAL_FIELDS
        if f in col_mapping and lot.get(f) is not None
    )
    critical_expected = sum(1 for f in CRITICAL_FIELDS if f in col_mapping)
    lot["confidence"] = (
        round(critical_present / critical_expected, 2)
        if critical_expected > 0
        else 0.0
    )

    return lot


def _score_section1_table(col_mapping: dict[str, int]) -> int:
    """Score a table by the number of Section 1 columns matched.

    Args:
        col_mapping: Column mapping produced by ``_find_section1_column_mapping``.

    Returns:
        Number of matched columns (higher is better).
    """
    return len(col_mapping)


def _parse_numeric(value: Optional[str]) -> Optional[float]:
    """Parse a Hebrew-formatted numeric string to float.

    Handles thousands separators (comma or period) and various whitespace.
    Returns None for empty or unparseable values.

    Args:
        value: Raw cell string (e.g. "1,234,567" or "1.234.567").

    Returns:
        Parsed float, or None.
    """
    if not value:
        return None
    # Strip whitespace and non-breaking spaces
    cleaned = re.sub(r"[\s\u00a0]", "", str(value))
    # Remove thousands separators (keep last period/comma as decimal)
    # Hebrew convention: comma for thousands, period for decimal
    cleaned = cleaned.replace(",", "")
    try:
        return float(cleaned)
    except ValueError:
        return None


def _parse_int(value: Optional[str]) -> Optional[int]:
    """Parse a string to integer, tolerating whitespace and commas.

    Args:
        value: Raw cell string.

    Returns:
        Parsed int, or None.
    """
    num = _parse_numeric(value)
    if num is not None:
        return int(num)
    return None


# ---------------------------------------------------------------------------
# Section 2 helper functions — zoning extraction from text and tables.
# ---------------------------------------------------------------------------


def _find_header_offset(text: str, headers: list[str]) -> int:
    """Find the character offset of the first matching section header.

    Args:
        text: Page text to search.
        headers: List of header keyword strings to look for.

    Returns:
        Character offset of the first match, or -1 if not found.
    """
    for header in headers:
        idx = text.find(header)
        if idx >= 0:
            return idx
    return -1


def _find_section2_text(
    pages: list[pdfplumber.page.Page],
) -> tuple[str, list[pdfplumber.page.Page]]:
    """Locate Section 2 and extract its text content.

    Scans page text for Section 2 header keywords, then collects all
    text until a Section 3 header is found (or end of scanned pages).

    Args:
        pages: List of pdfplumber Page objects.

    Returns:
        Tuple of (section2_text, list_of_pages_in_section2).
        Empty string and empty list if Section 2 is not found.
    """
    section2_start_page: int = -1
    section2_pages: list[pdfplumber.page.Page] = []
    text_chunks: list[str] = []

    for page_idx, page in enumerate(pages):
        page_text = page.extract_text() or ""

        if section2_start_page == -1:
            # Look for Section 2 header.
            offset = _find_header_offset(page_text, SECTION2_HEADERS)
            if offset >= 0:
                section2_start_page = page_idx
                # Check if Section 3 also starts on this same page.
                remaining = page_text[offset:]
                s3_offset = _find_header_offset(remaining, SECTION3_HEADERS)
                if s3_offset > 0:
                    text_chunks.append(remaining[:s3_offset])
                    section2_pages.append(page)
                    break
                text_chunks.append(remaining)
                section2_pages.append(page)
        else:
            # Already inside Section 2 — look for Section 3 boundary.
            s3_offset = _find_header_offset(page_text, SECTION3_HEADERS)
            if s3_offset >= 0:
                text_chunks.append(page_text[:s3_offset])
                section2_pages.append(page)
                break
            text_chunks.append(page_text)
            section2_pages.append(page)

    return "\n".join(text_chunks), section2_pages


def _find_zoning_column_mapping(
    header_cells: list[Optional[str]],
) -> dict[str, int]:
    """Map zoning-related field names to column indices in a table header.

    Looks for lot number, zoning plan, and zoning designation columns
    using SECTION1_HEADERS (for lot_number) and SECTION2_KEYWORDS.

    Args:
        header_cells: List of header cell strings.

    Returns:
        Dict mapping field name to column index.
    """
    mapping: dict[str, int] = {}
    lot_keywords = SECTION1_HEADERS["lot_number"]

    for col_idx, cell in enumerate(header_cells):
        if cell is None:
            continue
        if "lot_number" not in mapping and _header_matches(cell, lot_keywords):
            mapping["lot_number"] = col_idx
        elif "zoning_plan" not in mapping and _header_matches(
            cell, SECTION2_KEYWORDS["zoning_plan"]
        ):
            mapping["zoning_plan"] = col_idx
        elif "zoning_designation" not in mapping and _header_matches(
            cell, SECTION2_KEYWORDS["zoning_designation"]
        ):
            mapping["zoning_designation"] = col_idx

    return mapping


def _extract_zoning_from_tables(
    section2_pages: list[pdfplumber.page.Page],
) -> dict[int, dict]:
    """Try to extract zoning data from tables on Section 2 pages.

    Looks for tables with columns containing lot number and plan/zoning
    keywords. Returns structured mapping if a qualifying table is found.

    Args:
        section2_pages: Pages identified as belonging to Section 2.

    Returns:
        Dict mapping lot_number (int) to zoning info, or empty dict.
    """
    result: dict[int, dict] = {}

    for page in section2_pages:
        tables = page.extract_tables()
        if not tables:
            continue

        for table in tables:
            if not table or len(table) < 2:
                continue

            header_row = table[0]
            col_map = _find_zoning_column_mapping(header_row)

            if "lot_number" not in col_map:
                continue
            if "zoning_plan" not in col_map and "zoning_designation" not in col_map:
                continue

            # Parse data rows.
            for row in table[1:]:
                if not row or all(
                    c is None or str(c).strip() == "" for c in row
                ):
                    continue

                lot_idx = col_map["lot_number"]
                lot_raw = _clean_cell_value(
                    row[lot_idx] if lot_idx < len(row) else None
                )
                lot_num = _parse_int(lot_raw)
                if lot_num is None:
                    continue

                entry: dict[str, Optional[str]] = {}

                if "zoning_plan" in col_map:
                    plan_idx = col_map["zoning_plan"]
                    plan_raw = _clean_cell_value(
                        row[plan_idx] if plan_idx < len(row) else None
                    )
                    if plan_raw:
                        entry["zoning_plan"] = plan_raw

                if "zoning_designation" in col_map:
                    desig_idx = col_map["zoning_designation"]
                    desig_raw = _clean_cell_value(
                        row[desig_idx] if desig_idx < len(row) else None
                    )
                    if desig_raw:
                        entry["zoning_designation"] = desig_raw

                if entry:
                    result[lot_num] = entry

            if result:
                logger.info(
                    "Extracted zoning from table: %d lots", len(result),
                )
                return result

    return result


def _extract_all_plan_numbers(text: str) -> list[str]:
    """Extract all unique plan numbers from text, filtering out dates.

    Uses the PLAN_NUMBER_PATTERN from tender_pdf_extractor and filters
    out date-like matches.

    Args:
        text: Text to search for plan numbers.

    Returns:
        List of unique plan number strings found (order preserved).
    """
    matches = _PLAN_NUMBER_RE.findall(text)
    seen: set[str] = set()
    result: list[str] = []
    for m in matches:
        m = m.strip()
        if m not in seen and not _DATE_FILTER_RE.match(m):
            seen.add(m)
            result.append(m)
    return result


def _extract_first_plan_number(text: str) -> Optional[str]:
    """Extract the first plan number from text, filtering out dates.

    Args:
        text: Text to search.

    Returns:
        First valid plan number string, or None.
    """
    plans = _extract_all_plan_numbers(text)
    return plans[0] if plans else None


def _extract_designation(text: str) -> Optional[str]:
    """Extract a zoning designation keyword from text.

    Checks for both normal and reversed Hebrew designation keywords.
    Returns the first match found.

    Args:
        text: Text to search.

    Returns:
        Designation keyword string, or None if not found.
    """
    for kw in ZONING_DESIGNATION_KEYWORDS:
        if kw in text:
            return kw
    for idx, kw in enumerate(ZONING_DESIGNATION_KEYWORDS_REVERSED):
        if kw in text:
            return ZONING_DESIGNATION_KEYWORDS[idx]
    return None


def _extract_zoning_from_text(
    section2_text: str,
) -> dict[int, dict]:
    """Extract zoning data from Section 2 prose text.

    Handles several layouts:
        - Per-lot blocks: "מתחם 1: תכנית 606-0458471, ייעוד: מגורים"
        - Single plan for all lots (no lot-specific references)
        - Mixed normal and reversed Hebrew

    Args:
        section2_text: Extracted text of Section 2.

    Returns:
        Dict mapping lot_number (int) to zoning info, or empty dict.
        Key ``0`` is a sentinel for "applies to all lots".
    """
    result: dict[int, dict] = {}

    # Extract all plan numbers found in section text.
    all_plans = _extract_all_plan_numbers(section2_text)
    # Extract designation from text.
    designation = _extract_designation(section2_text)

    # Try per-lot association: find lot numbers and nearby plan numbers.
    lot_matches = list(_LOT_NUMBER_RE.finditer(section2_text))

    if lot_matches:
        for i, match in enumerate(lot_matches):
            lot_num = int(match.group(1))
            # Search forward from the lot mention to the next lot mention
            # (or end of text).  Do not look backwards to avoid bleeding
            # into the previous lot's plan/designation data.
            start = match.start()
            if i + 1 < len(lot_matches):
                end = lot_matches[i + 1].start()
            else:
                end = min(len(section2_text), match.end() + 300)
            context = section2_text[start:end]

            plan = _extract_first_plan_number(context)
            lot_designation = _extract_designation(context) or designation

            entry: dict[str, Optional[str]] = {}
            if plan:
                entry["zoning_plan"] = plan
            if lot_designation:
                entry["zoning_designation"] = lot_designation

            if entry:
                result[lot_num] = entry

    # If no per-lot data was found but we have a shared plan or designation,
    # return it keyed to lot 0 (sentinel for "all lots").
    if not result and (all_plans or designation):
        shared_entry: dict[str, Optional[str]] = {}
        if all_plans:
            shared_entry["zoning_plan"] = all_plans[0]
        if designation:
            shared_entry["zoning_designation"] = designation
        if shared_entry:
            result[0] = shared_entry

    return result


def _extract_zoning_inline(full_text: str) -> dict[int, dict]:
    """Extract zoning data from inline text in first-publication documents.

    First-publication (פרסום ראשון) documents embed plan and designation
    data in the body text rather than in a separate Section 2 with headers.

    Typical pattern (reversed Hebrew from pdfplumber):
        "זרכמה יטרפ רתי ,הקוסעת וניה םישרגמה דועי ,620-0876573 תינכות הלח םישרגמה לע"
        (Normal: "על השרגמים חלה תוכנית 620-0876573, ייעוד השרגמים הינו תעסוקה, יתר פרטי המכרז")

    Args:
        full_text: Combined text from all PDF pages.

    Returns:
        Dict mapping lot_number (int) to zoning info.
        Key ``0`` is a sentinel for "applies to all lots".
        Empty dict if no inline zoning data found.
    """
    result: dict[int, dict] = {}
    entry: dict[str, Optional[str]] = {}

    # Extract plan number from inline pattern.
    plan_match = _INLINE_PLAN_RE.search(full_text)
    if plan_match:
        plan = plan_match.group(1).strip()
        if not _DATE_FILTER_RE.match(plan):
            entry["zoning_plan"] = plan
            logger.info("Inline zoning: plan=%s", plan)

    # Extract designation from inline pattern.
    desig_match = _INLINE_DESIGNATION_RE.search(full_text)
    if desig_match:
        raw_desig = desig_match.group(1).strip()
        # The raw designation is reversed Hebrew; reverse it back.
        reversed_desig = _reverse_hebrew(raw_desig)
        # Try to match a known designation keyword in the reversed text.
        known_desig = _extract_designation(full_text)
        if known_desig:
            entry["zoning_designation"] = known_desig
        else:
            # Use the raw reversed text if no known keyword matches.
            entry["zoning_designation"] = reversed_desig
        logger.info("Inline zoning: designation=%s", entry.get("zoning_designation"))

    if entry:
        result[0] = entry  # Sentinel: applies to all lots.

    return result


def _extract_lots_from_text(
    full_text: str,
) -> list[dict]:
    """Extract lot data from body text when no table is found.

    Handles first-publication documents that list lot info inline,
    such as: "דחא םחתמב ד"חי 52 תיינבל" (for building 52 units in one lot).

    Also handles documents with lot count in text like:
    "םימחתמ 3 -ב ד"חי 302 תיינבל" (for building 302 units in 3 lots).

    Args:
        full_text: Combined text from all PDF pages.

    Returns:
        List of lot dicts extracted from text. Empty list if nothing found.
    """
    lots: list[dict] = []

    # Check for lot count in text.
    lot_count_match = _INLINE_LOT_COUNT_RE.search(full_text)
    single_lot_match = _INLINE_SINGLE_LOT_RE.search(full_text)

    # Determine how many lots are mentioned.
    if single_lot_match:
        num_lots = 1
    elif lot_count_match:
        num_lots = int(lot_count_match.group(1))
    else:
        # Try to detect from the document (default to 1 lot for simple
        # first-publication documents).
        num_lots = 1

    # Extract total unit count from text.
    units_match = _INLINE_UNITS_RE.search(full_text)
    total_units = None
    if units_match:
        units_raw = units_match.group(1).replace(",", "")
        try:
            total_units = int(units_raw)
        except ValueError:
            pass

    # Create lot entries. For simple documents with a single lot (or when
    # lot count matches but no per-lot table), create placeholder lots.
    if num_lots == 1:
        lot: dict[str, object] = {"lot_number": 1, "confidence": 0.5}
        if total_units is not None:
            lot["units_target_price"] = total_units
        lots.append(lot)
        logger.info(
            "Text-based lot extraction: 1 lot, units=%s", total_units,
        )
    elif num_lots > 1:
        # Multiple lots mentioned but no table — create numbered placeholders.
        for i in range(1, num_lots + 1):
            lot = {"lot_number": i, "confidence": 0.3}
            lots.append(lot)
        logger.info(
            "Text-based lot extraction: %d lots (placeholders), total_units=%s",
            num_lots, total_units,
        )

    return lots


class BrochureLotExtractor:
    """Extracts lot-level data from tender brochure PDFs.

    Parses three sections of the standard RMI brochure format:
        Section 1 -- Lot summary table (pricing, units, areas)
        Section 2 -- Zoning details per lot (taba, designation)
        Section 3 -- Bid limits (max lots per bidder)

    Attributes:
        max_pages: Maximum number of PDF pages to scan.
    """

    def __init__(self, max_pages: int = MAX_PAGES_TO_SCAN) -> None:
        """Initialize the lot extractor.

        Args:
            max_pages: Maximum pages to scan in each PDF.
        """
        self.max_pages = max_pages

    def extract_all(
        self,
        pdf_bytes: bytes,
        tender_id: int,
    ) -> dict:
        """Extract all lot-level data from a brochure PDF.

        Main entry point. Parses the PDF and returns structured lot data
        ready for database insertion via db.upsert_lots().

        Args:
            pdf_bytes: Raw PDF file contents as bytes.
            tender_id: The tender's MichrazID (for logging context).

        Returns:
            Dict with keys:
                lots: list[dict] — one dict per lot with all extracted fields
                max_lots_per_bidder: Optional[int] — bid limit from Section 3
                success: bool — whether any lots were extracted
                errors: list[str] — any extraction errors encountered
                pages_scanned: int — number of pages processed
        """
        result: dict = {
            "lots": [],
            "max_lots_per_bidder": None,
            "success": False,
            "errors": [],
            "pages_scanned": 0,
        }

        if not pdf_bytes:
            result["errors"].append("Empty PDF bytes provided")
            logger.error("extract_all called with empty PDF for tender %d", tender_id)
            return result

        logger.info(
            "Starting lot extraction for tender %d (%d bytes)",
            tender_id, len(pdf_bytes),
        )

        try:
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                pages_to_scan = min(len(pdf.pages), self.max_pages)
                result["pages_scanned"] = pages_to_scan

                # Collect page objects and text for all scanned pages
                pages: list[pdfplumber.page.Page] = [
                    pdf.pages[i] for i in range(pages_to_scan)
                ]
                page_texts: list[str] = [
                    page.extract_text() or "" for page in pages
                ]

                # Combined text for fallback extraction methods.
                full_text = "\n".join(page_texts)

                # Section 1: extract lot summary table
                lots = self._extract_section1_lots(pages)
                if lots:
                    result["lots"] = lots
                    logger.info(
                        "Tender %d: extracted %d lots from Section 1",
                        tender_id, len(lots),
                    )
                else:
                    # Fallback: extract lots from body text (first-publication
                    # documents without tables).
                    text_lots = _extract_lots_from_text(full_text)
                    if text_lots:
                        result["lots"] = text_lots
                        logger.info(
                            "Tender %d: extracted %d lots from text fallback",
                            tender_id, len(text_lots),
                        )
                    else:
                        result["errors"].append(
                            "No lot table found in Section 1"
                        )
                        logger.warning(
                            "Tender %d: no lot table found", tender_id,
                        )

                # Section 2: extract zoning info per lot
                zoning_map = self._extract_section2_zoning(pages)

                # Fallback: inline zoning extraction from full text
                # (for first-publication documents without section headers).
                if not zoning_map:
                    zoning_map = _extract_zoning_inline(full_text)

                if zoning_map:
                    # Apply zoning data to lots. Key 0 = applies to all lots.
                    shared_zoning = zoning_map.get(0)
                    for lot in result["lots"]:
                        lot_num = lot.get("lot_number")
                        if lot_num and lot_num in zoning_map:
                            lot.update(zoning_map[lot_num])
                        elif shared_zoning:
                            lot.update(shared_zoning)
                    logger.info(
                        "Tender %d: merged zoning data for %d lots",
                        tender_id, len(zoning_map),
                    )

                # Section 3: extract bid limits
                bid_limit = self._extract_section3_bid_limits(page_texts)
                if bid_limit is not None:
                    result["max_lots_per_bidder"] = bid_limit
                    logger.info(
                        "Tender %d: max_lots_per_bidder=%d",
                        tender_id, bid_limit,
                    )

        except Exception as exc:
            error_msg = f"PDF parsing failed: {exc}"
            result["errors"].append(error_msg)
            logger.exception(
                "Lot extraction failed for tender %d: %s", tender_id, exc,
            )

        result["success"] = len(result["lots"]) > 0

        logger.info(
            "Tender %d lot extraction complete: %d lots, success=%s, errors=%d",
            tender_id,
            len(result["lots"]),
            result["success"],
            len(result["errors"]),
        )

        return result

    def _extract_section1_lots(
        self,
        pages: list[pdfplumber.page.Page],
    ) -> list[dict]:
        """Extract the lot summary table from Section 1 of the brochure.

        Scans pages for a table containing lot-related headers (מתחם, מגרש,
        שטח, מחיר מטרה, שוק חופשי, etc.) and parses each data row.

        Handles:
            - Normal and reversed Hebrew column headers.
            - Multi-line (wrapped) headers that span two table rows.
            - Multi-page table continuation (rows on subsequent pages
              without repeated headers are appended).
            - Numeric parsing with thousands-separator handling.
            - Confidence scoring per row based on critical field coverage.

        Args:
            pages: List of pdfplumber Page objects to scan.

        Returns:
            List of lot dicts, each containing extracted fields.
            Empty list if no suitable table is found.
        """
        best_lots: list[dict] = []
        best_score: int = 0
        best_mapping: dict[str, int] = {}
        best_num_cols: int = 0
        found_on_page: int = -1

        for page_idx, page in enumerate(pages):
            tables = page.extract_tables()
            if not tables:
                # --- Multi-page continuation ---
                # If we already found the main table and this page has no
                # tables at all, stop looking for continuations.
                continue

            for table in tables:
                if not table or len(table) < 2:
                    continue

                # Detect (possibly multi-line) header and build mapping
                header_cells, header_rows_consumed = _detect_header_rows(table)
                col_mapping = _find_section1_column_mapping(header_cells)
                score = _score_section1_table(col_mapping)

                if score < MIN_SECTION1_COLUMNS:
                    # Not enough columns matched — might be a continuation
                    # table on a later page (same column count, no header).
                    if (
                        best_score >= MIN_SECTION1_COLUMNS
                        and page_idx == found_on_page + 1
                        and table
                        and len(table[0]) == best_num_cols
                    ):
                        logger.info(
                            "Page %d: appending %d continuation rows",
                            page_idx + 1,
                            len(table),
                        )
                        for row in table:
                            lot = _parse_row(row, best_mapping)
                            if lot is not None:
                                best_lots.append(lot)
                        found_on_page = page_idx
                    continue

                # This table qualifies. Parse data rows.
                if score > best_score:
                    data_rows = table[header_rows_consumed:]
                    lots: list[dict] = []
                    for row in data_rows:
                        if not row or all(
                            cell is None or str(cell).strip() == ""
                            for cell in row
                        ):
                            continue
                        lot = _parse_row(row, col_mapping)
                        if lot is not None:
                            lots.append(lot)

                    if lots:
                        best_lots = lots
                        best_score = score
                        best_mapping = col_mapping
                        best_num_cols = len(header_cells)
                        found_on_page = page_idx
                        logger.info(
                            "Page %d: found lot table (score=%d, %d rows). "
                            "Columns: %s",
                            page_idx + 1,
                            score,
                            len(lots),
                            col_mapping,
                        )

        if not best_lots:
            logger.debug("No qualifying lot table found across %d pages", len(pages))

        return best_lots

    def _extract_section2_zoning(
        self,
        pages: list[pdfplumber.page.Page],
    ) -> dict[int, dict]:
        """Extract zoning details (taba + designation) per lot from Section 2.

        Section 2 ("היבט תכנוני ופיזי") typically contains a table or text
        blocks mapping each lot number to its zoning plan and land-use
        designation.

        Strategy:
            1. Locate Section 2 by scanning page text for header keywords.
            2. Extract text between Section 2 header and Section 3 header.
            3. Try table-based extraction first (structured zoning table).
            4. Fall back to text-based extraction (plan numbers in prose).
            5. Associate plans with lot numbers; if a single plan is found
               with no lot-specific context, assign it to all lots via
               the sentinel key ``0``.

        Args:
            pages: List of pdfplumber Page objects to scan.

        Returns:
            Dict mapping lot_number (int) to a dict with keys:
                zoning_plan: str -- the plan number (e.g. "606-0458471")
                zoning_designation: str -- the land-use designation
            Key ``0`` is a sentinel meaning "applies to all lots".
            Empty dict if no zoning data found.
        """
        # Step 1: Collect page text and find Section 2 boundaries.
        section2_text, section2_pages = _find_section2_text(pages)

        if not section2_text:
            logger.debug("Section 2 header not found in %d pages", len(pages))
            return {}

        logger.debug(
            "Section 2 text extracted (%d chars) from %d pages",
            len(section2_text),
            len(section2_pages),
        )

        # Step 2: Try table-based extraction from the Section 2 pages.
        result = _extract_zoning_from_tables(section2_pages)

        # Step 3: Fall back to text-based extraction.
        if not result:
            result = _extract_zoning_from_text(section2_text)

        if result:
            logger.info(
                "Section 2 zoning extracted for %d lots: %s",
                len(result),
                list(result.keys()),
            )
        else:
            logger.debug("No zoning data could be extracted from Section 2")

        return result

    def _extract_section3_bid_limits(
        self,
        page_texts: list[str],
    ) -> Optional[int]:
        """Extract the maximum lots per bidder from Section 3.

        Locates Section 3 ("מסלול מכרז") in the page texts and searches for
        bid-limit phrases.  Handles both normal and reversed Hebrew text as
        produced by pdfplumber on RTL documents.

        Priority order:
            1. Specific numeric limits ("למתחם אחד בלבד", "לשני מתחמים",
               "ל-2 מתחמים").
            2. Unlimited markers ("ללא הגבלה", "לכל המתחמים") -> returns None.
            3. No pattern found -> returns None (assume unlimited).

        Args:
            page_texts: List of extracted text strings, one per page.

        Returns:
            Maximum lots per bidder as int, or None if unlimited / not found.
        """
        section3_text = self._find_section3_text(page_texts)
        if not section3_text:
            logger.debug("Section 3 header not found; searching all page text")
            section3_text = "\n".join(page_texts)

        if not section3_text.strip():
            logger.debug("No page text available for bid-limit extraction")
            return None

        # --- Priority 1: Specific numeric limits ---
        for pattern in BID_LIMIT_SPECIFIC_PATTERNS:
            match = pattern.search(section3_text)
            if match:
                raw_value = match.group(1)
                limit = self._parse_bid_limit_value(raw_value)
                if limit is not None and 1 <= limit <= 20:
                    logger.info(
                        "Bid limit found: %d (pattern=%s, raw=%r)",
                        limit, pattern.pattern, raw_value,
                    )
                    return limit

        # --- Priority 2: Unlimited markers ---
        for pattern in BID_LIMIT_UNLIMITED_PATTERNS:
            if pattern.search(section3_text):
                logger.info(
                    "Unlimited bid limit found (pattern=%s)",
                    pattern.pattern,
                )
                return None

        # --- Priority 3: Fall back to keyword-based search ---
        for keyword in SECTION3_BID_LIMIT_KEYWORDS:
            idx = section3_text.find(keyword)
            if idx != -1:
                window_start = max(0, idx - 100)
                window_end = min(
                    len(section3_text), idx + len(keyword) + 100,
                )
                window = section3_text[window_start:window_end]
                num_match = BID_LIMIT_NUMBER_PATTERN.search(window)
                if num_match:
                    limit = int(num_match.group(1))
                    if 1 <= limit <= 20:
                        logger.info(
                            "Bid limit found via keyword fallback: %d "
                            "(keyword=%r)",
                            limit, keyword,
                        )
                        return limit

        logger.debug("No bid-limit pattern matched; returning None (unlimited)")
        return None

    @staticmethod
    def _find_section3_text(page_texts: list[str]) -> str:
        """Locate Section 3 text between its header and Section 4 header.

        Scans page texts for a Section 3 header ("מסלול מכרז" or its reversed
        form) and extracts text from that header to the next section header
        or the end of available pages.

        Args:
            page_texts: List of extracted text strings, one per page.

        Returns:
            The concatenated text of Section 3, or empty string if not found.
        """
        full_text = "\n".join(page_texts)

        # Find Section 3 start.
        section3_start: Optional[int] = None
        for pattern in SECTION3_HEADER_RE:
            match = pattern.search(full_text)
            if match:
                section3_start = match.start()
                break

        if section3_start is None:
            return ""

        # Find Section 4 start (end boundary).
        section3_end: Optional[int] = None
        for pattern in SECTION4_HEADER_RE:
            match = pattern.search(full_text, pos=section3_start + 1)
            if match:
                if section3_end is None or match.start() < section3_end:
                    section3_end = match.start()

        if section3_end is None:
            section3_end = min(len(full_text), section3_start + 5000)

        return full_text[section3_start:section3_end]

    @staticmethod
    def _parse_bid_limit_value(raw: str) -> Optional[int]:
        """Convert a matched bid-limit capture group to an integer.

        Handles both digit strings ("2", "3") and Hebrew number words
        ("שני", "שלושה", "דחא").

        Args:
            raw: The raw matched string from a regex capture group.

        Returns:
            Integer value, or None if unparseable.
        """
        if raw.isdigit():
            return int(raw)
        return HEBREW_NUMBER_WORDS.get(raw)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
    )
    # Quick smoke test: instantiate the extractor
    extractor = BrochureLotExtractor()
    logger.info("BrochureLotExtractor instantiated OK (max_pages=%d)", extractor.max_pages)
