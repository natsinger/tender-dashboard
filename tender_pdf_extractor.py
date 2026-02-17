"""Extracts structured plot data (גוש, חלקה, תב"ע) from tender brochure PDFs.

This module uses pdfplumber for text-based PDF extraction. It handles the
reversed Hebrew text that pdfplumber produces from RTL documents by searching
for keywords in both normal and reversed forms.

Usage:
    extractor = TenderPDFExtractor()
    result = extractor.extract(Path("hoveret_1.pdf"))
    print(result)
"""

import logging
import re
from pathlib import Path
from typing import Optional

import pdfplumber

logger = logging.getLogger(__name__)

# Maximum number of pages to scan (the relevant section is always near the start)
MAX_PAGES_TO_SCAN = 15

# Table header keywords in both normal and reversed Hebrew forms.
# pdfplumber often reverses RTL text, so we search for both directions.
HEADER_KEYWORDS = {
    "gush": ["גוש", "שוג", "ש וג"],
    "helka": ["חלקה", "הקלח"],
    "migrash": ["מגרש", "שרגמ", "ש רגמ"],
    "mitham": ["מתחם", "םחתמ", "ם חתמ"],
    "area": ["שטח", "חטש"],
    "min_price": ["מחיר", "ריחמ"],
    "guarantee": ["ערבות", "תוברע", "ת וברע"],
}

# Combined column header: "גוש/חלקה" appears as "הקלח/שוג" when reversed
COMBINED_GUSH_HELKA_KEYWORDS = ["גוש/חלקה", "הקלח/שוג"]

# Regex patterns for extracting plan number (תב"ע / תכנית) from text.
PLAN_KEYWORDS_NORMAL = [r"תכנית", r'תב"ע', r"תב״ע", r"תוכנית"]
PLAN_KEYWORDS_REVERSED = [r"תינכת", r'ע"בת', r"ע״בת", r"תינכות"]

# Plan number format: digits separated by dashes or slashes, optionally with Hebrew letters
PLAN_NUMBER_PATTERN = r"[\dא-ת]{1,10}[-/][\dא-ת/\-]{3,30}"

# Date pattern to filter out false positive plan numbers (DD/MM/YYYY, D/M/YYYY, etc.)
DATE_PATTERN = re.compile(
    r"^\d{1,2}/\d{1,2}/(?:19|20)\d{2}$"
    r"|^\d{1,2}\.\d{1,2}\.(?:19|20)\d{2}$"
    r"|^(?:19|20)\d{2}/\d{1,2}/\d{1,2}$"
)

# Purpose (ייעוד) keywords — both normal and reversed.
PURPOSE_KEYWORDS_NORMAL = [r"ייעוד\s+(?:המגרש|הקרקע|המקרקעין)"]
PURPOSE_KEYWORDS_REVERSED = [r"(?:שרגמה|עקרקה|ןיעקרקמה)\s+דועיי?"]

# Minimum number of key columns to accept a table as the plot table.
# "key columns" = gush, helka, migrash, gush_helka (not mitham or area alone).
MIN_KEY_COLUMNS = 1

# Keywords indicating the PDF is NOT a land tender brochure (quarrying only).
# Note: "הרשמה והגרלה" removed — too broad, many valid tenders use lottery process.
NON_LAND_KEYWORDS = [
    "יפדוע הריפח",   # reversed: חפירה עודפי (excavation surplus)
    "עודפי חפירה",    # normal: excavation surplus
    "הייירכ",         # reversed: כרייה (quarrying)
    "כרייה",          # normal: quarrying
]

# Keywords indicating announcement/date-change PDF (not actual brochure)
ANNOUNCEMENT_KEYWORDS = [
    "םידעומ תייחד",   # reversed: דחיית מועדים (date postponement)
    "דחיית מועדים",   # normal
    "ןוכדע תעדומ",    # reversed: מודעת עדכון (update notice)
    "מודעת עדכון",    # normal
]

# Strong fields — a table must have at least one of these to be accepted.
# This prevents matching financial/guarantee tables that only have "mitham".
STRONG_FIELDS = {"gush", "helka", "migrash", "gush_helka"}


def _reverse_hebrew(text: str) -> str:
    """Reverse a Hebrew string, preserving number sequences.

    pdfplumber extracts RTL text in visual order (reversed). This function
    reverses it back to logical reading order while keeping LTR number
    sequences intact.

    Args:
        text: The reversed Hebrew text from pdfplumber.

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
    # Replace newlines with commas for multi-value cells, then clean
    cleaned = re.sub(r"\s*\n\s*", ", ", str(value)).strip()
    # Remove leading/trailing commas
    cleaned = cleaned.strip(",").strip()
    return cleaned if cleaned else None


def _header_matches(cell_text: str, keyword_list: list[str]) -> bool:
    """Check if a table cell header matches any of the keyword variants.

    Args:
        cell_text: The text content of a table header cell.
        keyword_list: List of keyword variants to match against.

    Returns:
        True if any keyword is found in the cell text.
    """
    if not cell_text:
        return False
    cleaned = " ".join(cell_text.split())
    return any(kw in cleaned for kw in keyword_list)


def _find_column_indices(
    header_row: list[Optional[str]],
) -> dict[str, int]:
    """Map field names to column indices based on header keywords.

    Handles combined "גוש/חלקה" columns by mapping them to a special
    "gush_helka" field that gets split during row parsing.

    Args:
        header_row: List of header cell strings from a table.

    Returns:
        Dict mapping field names to column indices.
    """
    indices: dict[str, int] = {}

    for col_idx, cell in enumerate(header_row):
        if cell is None:
            continue
        cell_flat = " ".join(cell.split())
        # Normalize spaces around '/' so "הקלח / שוג" matches "הקלח/שוג"
        cell_normalized = re.sub(r"\s*/\s*", "/", cell_flat)

        # Check combined gush/helka column first
        if any(kw in cell_normalized for kw in COMBINED_GUSH_HELKA_KEYWORDS):
            indices["gush_helka"] = col_idx
            continue

        for field_name, keywords in HEADER_KEYWORDS.items():
            if field_name not in indices and _header_matches(cell, keywords):
                indices[field_name] = col_idx

    return indices


def _is_date(value: str) -> bool:
    """Check if a string looks like a date rather than a plan number.

    Args:
        value: String to check.

    Returns:
        True if it matches common date formats.
    """
    return bool(DATE_PATTERN.match(value.strip()))


def _extract_plan_number(text: str) -> Optional[str]:
    """Extract the תב"ע/תכנית plan number from page text.

    Searches for plan-related keywords and extracts the nearby number pattern.
    Filters out date-like patterns to avoid false positives.

    Args:
        text: Full page text from pdfplumber.

    Returns:
        The extracted plan number string, or None if not found.
    """
    all_keywords = PLAN_KEYWORDS_NORMAL + PLAN_KEYWORDS_REVERSED

    for keyword in all_keywords:
        pattern = keyword + r"[^:\n]{0,30}[:：]\s*(" + PLAN_NUMBER_PATTERN + r")"
        match = re.search(pattern, text)
        if match:
            plan_num = match.group(1).strip()
            if not _is_date(plan_num):
                logger.info("Found plan number '%s' near keyword '%s'", plan_num, keyword)
                return plan_num

    # Fallback: NUMBER :הניה pattern (reversed "הינה: NUMBER")
    reversed_plan_pattern = r"(" + PLAN_NUMBER_PATTERN + r")\s*:הניה"
    match = re.search(reversed_plan_pattern, text)
    if match:
        plan_num = match.group(1).strip()
        if not _is_date(plan_num):
            logger.info("Found plan number '%s' from reversed plan pattern", plan_num)
            return plan_num

    # Plan number BEFORE reversed keyword (e.g., "א33/102/02/5 תינכות")
    for kw_pattern in [r"תינכו[תם]", r"תינכת"]:
        pat = r"(" + PLAN_NUMBER_PATTERN + r")\s+" + kw_pattern
        match = re.search(pat, text)
        if match:
            plan_num = match.group(1).strip()
            if not _is_date(plan_num):
                logger.info("Found plan number '%s' from reversed keyword pattern", plan_num)
                return plan_num

    # "הלח ... תינכת/תינכות" with plan number
    reversed_plan_pattern4 = (
        r"(" + PLAN_NUMBER_PATTERN + r")\s+(?:תינכו[תם]|תינכת)\s+הלח"
    )
    match = re.search(reversed_plan_pattern4, text)
    if match:
        plan_num = match.group(1).strip()
        if not _is_date(plan_num):
            logger.info("Found plan number '%s' from 'חלה תכנית' pattern", plan_num)
            return plan_num

    # Context-based fallback: search near any plan keyword
    for keyword in all_keywords:
        kw_match = re.search(keyword, text)
        if kw_match:
            start = max(0, kw_match.start() - 80)
            end = min(len(text), kw_match.end() + 80)
            context = text[start:end]
            num_match = re.search(PLAN_NUMBER_PATTERN, context)
            if num_match:
                plan_num = num_match.group(0).strip()
                if not _is_date(plan_num):
                    logger.info(
                        "Found plan number '%s' in context around '%s'",
                        plan_num,
                        keyword,
                    )
                    return plan_num

    return None


def _extract_gush_helka_from_text(text: str) -> Optional[dict[str, str]]:
    """Extract גוש and חלקה from body text when no table column exists.

    Searches for patterns like "בגוש 2199 חלקה 39" or their reversed forms.

    Args:
        text: Full page text from pdfplumber.

    Returns:
        Dict with 'gush' and optionally 'helka', or None if not found.
    """
    def _clean_num(val: str) -> str:
        """Strip leading/trailing commas and whitespace from numeric values."""
        return val.strip().strip(",").strip()

    # Normal Hebrew: "בגוש 2199 חלקה 39"
    normal = re.search(
        r"(?:בגוש|גוש)\s+([\d,]+)\s+(?:חלקה|חלקות)\s+([\d,\s]+)",
        text,
    )
    if normal:
        return {
            "gush": _clean_num(normal.group(1)),
            "helka": _clean_num(normal.group(2)),
        }

    # Reversed Hebrew: "39 הקלח 2199 שוגב"
    reversed_pat = re.search(
        r"([\d,\s]+)\s+(?:הקלח|תוקלח)\s+([\d,]+)\s+(?:שוגב|שוג)",
        text,
    )
    if reversed_pat:
        return {
            "gush": _clean_num(reversed_pat.group(2)),
            "helka": _clean_num(reversed_pat.group(1)),
        }

    # Just gush without helka
    gush_only = re.search(r"(?:בגוש|גוש)\s+([\d,]+)", text)
    if not gush_only:
        gush_only = re.search(r"([\d,]+)\s+(?:שוגב|שוג)", text)
    if gush_only:
        return {"gush": _clean_num(gush_only.group(1))}

    return None


def _extract_purpose(text: str) -> Optional[str]:
    """Extract the land-use purpose (ייעוד) from page text.

    Handles multiple patterns:
    - Normal Hebrew with colon: "ייעוד המגרש/ים הוא: תעשיה קלה"
    - Reversed with colon: ".הכאלמו הלק הישעת :אוה םי/שרגמה דועיי"
    - Reversed with "הינו" (is): "רחסמ וניה שרגמה דועי"

    Args:
        text: Full page text from pdfplumber.

    Returns:
        The extracted purpose string, or None if not found.
    """
    # Try normal Hebrew patterns with colon
    for pattern in PURPOSE_KEYWORDS_NORMAL:
        full_pattern = pattern + r"[^:\n]{0,20}[:：]\s*([^\n.]{3,80})"
        match = re.search(full_pattern, text)
        if match:
            return match.group(1).strip()

    # Reversed pattern: "VALUE וניה/אוה KEYWORD דועיי/דועי"
    reversed_is_pattern = (
        r"([^\n,]{2,40})\s+(?:וניה|אוה)\s+"
        r"(?:(?:םי/?)?שרגמה|עקרקה|ןיעקרקמה)\s+דועיי?"
    )
    match = re.search(reversed_is_pattern, text)
    if match:
        raw = match.group(1).strip().rstrip(".")
        purpose = _reverse_hebrew(raw)
        logger.info("Extracted purpose from reversed 'הינו' pattern: %s", purpose)
        return purpose

    # Reversed with colon: ".VALUE :אוה KEYWORD דועיי"
    reversed_colon_pattern = (
        r"\.([^\n.]{3,40})\s*[:：]\s*אוה\s+"
        r"(?:(?:םי/?)?שרגמה)\s+דועיי?"
    )
    match = re.search(reversed_colon_pattern, text)
    if match:
        raw = match.group(1).strip()
        return _reverse_hebrew(raw)

    # Reversed keyword with colon (limited distance)
    for pattern in PURPOSE_KEYWORDS_REVERSED:
        full_pattern = pattern + r"[^:\n]{0,20}[:：]\s*([^\n.]{3,40})"
        match = re.search(full_pattern, text)
        if match:
            raw = match.group(1).strip()
            return _reverse_hebrew(raw)

    return None


def _score_table(col_indices: dict[str, int]) -> int:
    """Score a table by how many strong plot-related columns it has.

    Tables with more key fields (gush, helka, migrash) score higher.
    A table with only "mitham" gets a low score and can be superseded
    by a better table found on a later page.

    Args:
        col_indices: Dict mapping field names to column indices.

    Returns:
        Score (count of strong fields matched).
    """
    return sum(1 for f in STRONG_FIELDS if f in col_indices)


class TenderPDFExtractor:
    """Extracts גוש, חלקה, and תב"ע data from tender brochure PDFs.

    Uses pdfplumber for text-based extraction. Handles reversed Hebrew text
    that pdfplumber produces from RTL documents.

    Attributes:
        max_pages: Maximum number of pages to scan per PDF.
    """

    def __init__(self, max_pages: int = MAX_PAGES_TO_SCAN) -> None:
        """Initialize the extractor.

        Args:
            max_pages: Maximum pages to scan in each PDF.
        """
        self.max_pages = max_pages

    def extract(self, pdf_path: Path) -> dict:
        """Extract plot data from a tender brochure PDF.

        Main entry point. Scans pages for the plot details table and
        plan number, returning structured data.

        Args:
            pdf_path: Path to the PDF file.

        Returns:
            Dict with keys: plots, taba, purpose, extraction_method,
            source_file, success, errors.
        """
        pdf_path = Path(pdf_path)
        result = {
            "plots": [],
            "taba": None,
            "purpose": None,
            "extraction_method": "pdfplumber",
            "source_file": pdf_path.name,
            "success": False,
            "errors": [],
        }

        if not pdf_path.exists():
            result["errors"].append(f"File not found: {pdf_path}")
            logger.error("File not found: %s", pdf_path)
            return result

        logger.info("Extracting data from: %s", pdf_path.name)

        try:
            result = self._extract_with_pdfplumber(pdf_path, result)
        except Exception as e:
            error_msg = f"pdfplumber extraction failed: {e}"
            result["errors"].append(error_msg)
            logger.exception(error_msg)

        # Determine success
        result["success"] = bool(result["plots"]) or result["taba"] is not None

        if result["success"]:
            logger.info(
                "Extraction successful: %d plots, taba=%s, purpose=%s",
                len(result["plots"]),
                result["taba"],
                result["purpose"],
            )
        else:
            logger.warning("No data extracted from %s", pdf_path.name)

        return result

    def _extract_with_pdfplumber(self, pdf_path: Path, result: dict) -> dict:
        """Extract data using pdfplumber text and table extraction.

        Scans all pages for tables and text. For tables, uses a scoring
        system to prefer tables with more plot-related columns (gush, helka,
        migrash) over weak matches (mitham only).

        Args:
            pdf_path: Path to the PDF file.
            result: Result dict to populate.

        Returns:
            Updated result dict.
        """
        with pdfplumber.open(pdf_path) as pdf:
            pages_to_scan = min(len(pdf.pages), self.max_pages)
            logger.info("Scanning %d pages of %s", pages_to_scan, pdf_path.name)

            # Quick check: read first 2 pages to detect non-land or announcement PDFs
            first_pages_text = ""
            for i in range(min(2, pages_to_scan)):
                first_pages_text += (pdf.pages[i].extract_text() or "") + "\n"

            for kw in NON_LAND_KEYWORDS:
                if kw in first_pages_text:
                    result["errors"].append(f"non_land_tender: matched '{kw}'")
                    logger.info("Skipping non-land tender PDF: %s", pdf_path.name)
                    return result

            all_text_pages: list[str] = []
            best_table_score = 0

            for page_idx in range(pages_to_scan):
                page = pdf.pages[page_idx]
                text = page.extract_text() or ""
                all_text_pages.append(text)
                tables = page.extract_tables()

                # Try to find the best plot details table
                if tables:
                    for table in tables:
                        plots, score = self._parse_plot_table(table, page_idx + 1)
                        if plots and score > best_table_score:
                            result["plots"] = plots
                            best_table_score = score
                            logger.info(
                                "Found plot table on page %d: %d rows, score=%d",
                                page_idx + 1,
                                len(plots),
                                score,
                            )

                # Try to extract plan number
                if result["taba"] is None:
                    plan = _extract_plan_number(text)
                    if plan:
                        result["taba"] = plan

                # Try to extract purpose
                if result["purpose"] is None:
                    purpose = _extract_purpose(text)
                    if purpose:
                        result["purpose"] = purpose

            # Combined text fallback for plan number
            if result["taba"] is None:
                combined = "\n".join(all_text_pages)
                plan = _extract_plan_number(combined)
                if plan:
                    result["taba"] = plan

            # Text-based gush/helka fallback: if plots lack gush, search text
            plots_missing_gush = result["plots"] and all(
                p.get("gush") in (None, "-") for p in result["plots"]
            )
            no_plots = not result["plots"]
            if plots_missing_gush or no_plots:
                combined = "\n".join(all_text_pages)
                text_gush = _extract_gush_helka_from_text(combined)
                if text_gush:
                    logger.info(
                        "Text-based gush/helka fallback: %s", text_gush
                    )
                    if plots_missing_gush:
                        for p in result["plots"]:
                            if p.get("gush") in (None, "-"):
                                p["gush"] = text_gush.get("gush")
                            if p.get("helka") in (None, "-") and "helka" in text_gush:
                                p["helka"] = text_gush["helka"]
                    elif no_plots:
                        result["plots"].append(text_gush)

        return result

    def _parse_plot_table(
        self, table: list[list[Optional[str]]], page_num: int
    ) -> tuple[list[dict], int]:
        """Parse a table to extract plot data if it's the right table.

        Returns plots and a score indicating match quality. Higher scores
        mean more plot-related columns were found.

        Args:
            table: 2D list of cell values from pdfplumber.
            page_num: Page number (for logging).

        Returns:
            Tuple of (plots list, score). Empty list and 0 if not a match.
        """
        if not table or len(table) < 2:
            return [], 0

        header_row = table[0]
        col_indices = _find_column_indices(header_row)

        # Must have at least one strong field
        score = _score_table(col_indices)
        if score < MIN_KEY_COLUMNS:
            # Check if it at least has mitham + area (weak but acceptable)
            has_mitham_plus = "mitham" in col_indices and len(col_indices) >= 2
            if not has_mitham_plus:
                return [], 0

        logger.info(
            "Matched plot table on page %d (score=%d). Columns: %s",
            page_num,
            score,
            col_indices,
        )

        # Parse data rows
        plots = []
        for row_idx, row in enumerate(table[1:], start=1):
            if not row or all(
                cell is None or str(cell).strip() == "" for cell in row
            ):
                continue

            # Skip rows where any mapped cell is suspiciously long (Q&A text)
            has_long_cell = False
            for field_name, col_idx in col_indices.items():
                if col_idx < len(row) and row[col_idx]:
                    if len(str(row[col_idx]).strip()) > 100:
                        has_long_cell = True
                        break
            if has_long_cell:
                continue

            plot: dict[str, Optional[str]] = {}

            # Handle combined gush/helka column
            if "gush_helka" in col_indices:
                combined_idx = col_indices["gush_helka"]
                if combined_idx < len(row):
                    raw_val = _clean_cell(row[combined_idx])
                    if raw_val and "/" in raw_val:
                        parts = raw_val.split("/", 1)
                        plot["gush"] = parts[0].strip()
                        plot["helka"] = parts[1].strip()
                    else:
                        plot["gush"] = raw_val
                        plot["helka"] = raw_val

            # Handle regular columns
            for field_name, col_idx in col_indices.items():
                if field_name == "gush_helka":
                    continue  # Already handled above
                if col_idx < len(row):
                    plot[field_name] = _clean_cell(row[col_idx])

            # Only include rows with at least some data
            if any(v is not None for v in plot.values()):
                plots.append(plot)

        return plots, score


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
    )

    extractor = TenderPDFExtractor()

    test_files = [Path("hoveret_1.pdf"), Path("hoverete_2.pdf")]
    for pdf_file in test_files:
        if pdf_file.exists():
            print(f"\n{'='*60}")
            print(f"Processing: {pdf_file.name}")
            print(f"{'='*60}")
            extracted = extractor.extract(pdf_file)
            import json

            print(json.dumps(extracted, ensure_ascii=False, indent=2))
        else:
            print(f"File not found: {pdf_file}")
