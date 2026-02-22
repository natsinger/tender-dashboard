"""Lightweight brochure analysis for on-demand building rights extraction.

Downloads the פרסום ראשון (first publication) PDF from the Land Authority API,
extracts plan number, gush, helka, lots, and generates a text summary.

This module runs WITHOUT Playwright — it only uses HTTP requests and pdfplumber,
making it safe for Streamlit Cloud deployment.

Usage:
    from brochure_analyzer import download_and_analyze_brochure, trigger_extraction_workflow
    from data_client import LandTendersClient

    client = LandTendersClient()
    result = download_and_analyze_brochure(tender_id=20100316, client=client)
    if result["plan_number"]:
        trigger_extraction_workflow(tender_id=20100316)
"""

import io
import json
import logging
from typing import Any, Dict, List, Optional

import pdfplumber
import requests

from config import _get
from tender_pdf_extractor import TenderPDFExtractor

logger = logging.getLogger(__name__)

# Maximum pages to scan for summary extraction
_SUMMARY_MAX_PAGES = 5

# Section keywords to look for in brochure text (normal + reversed Hebrew)
_SUMMARY_SECTIONS = [
    ("תיאור הנכס", "סכנה רואית"),
    ("ייעוד", "דועיי"),
    ("תנאים", "םיאנת"),
    ("מחיר סף", "ףס ריחמ"),
    ("ערבות", "תוברע"),
    ("תקופת החכירה", "הריכחה תפוקת"),
    ("תכנית בניין עיר", "ריע ןיינב תינכת"),
]

# GitHub API configuration for workflow dispatch
_GH_REPO = "natsinger/tender-dashboard"
_GH_WORKFLOW_FILE = "extract_building_rights.yml"


def find_pirsum_rishon(details: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Find the פרסום ראשון document from tender details.

    Priority order:
    1. MichrazDocList items where Teur contains "פרסום ראשון"
    2. MichrazFullDocument (the complete brochure, always present)

    Args:
        details: Tender details dict from the API.

    Returns:
        Document dict suitable for download_document(), or None.
    """
    # Search MichrazDocList for פרסום ראשון
    for doc in details.get("MichrazDocList", []):
        teur = (doc.get("Teur") or "").strip()
        if "פרסום ראשון" in teur:
            logger.info(
                "Found פרסום ראשון in MichrazDocList (RowID=%s)",
                doc.get("RowID"),
            )
            return doc

    # Fallback: use the full publication document
    full_doc = details.get("MichrazFullDocument")
    if full_doc and full_doc.get("RowID") is not None:
        logger.info("Using MichrazFullDocument as brochure (RowID=%s)", full_doc.get("RowID"))
        return full_doc

    logger.warning("No brochure document found in tender details")
    return None


def generate_brochure_summary(pdf_bytes: bytes) -> str:
    """Extract a concise Hebrew summary from a brochure PDF.

    Scans the first few pages for key sections and builds a structured
    summary with section headers.

    Args:
        pdf_bytes: Raw PDF file content.

    Returns:
        Hebrew summary text (may be empty if extraction fails).
    """
    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            pages_to_scan = min(len(pdf.pages), _SUMMARY_MAX_PAGES)
            all_text = []
            for i in range(pages_to_scan):
                page_text = pdf.pages[i].extract_text() or ""
                all_text.append(page_text)

            combined = "\n".join(all_text)

            if not combined.strip():
                return ""

            # Truncate to reasonable length for display
            # Take first ~2000 chars which usually covers the important info
            summary = combined[:2000].strip()

            # Clean up: collapse multiple blank lines
            lines = summary.split("\n")
            cleaned_lines: List[str] = []
            prev_blank = False
            for line in lines:
                stripped = line.strip()
                if not stripped:
                    if not prev_blank:
                        cleaned_lines.append("")
                    prev_blank = True
                else:
                    cleaned_lines.append(stripped)
                    prev_blank = False

            return "\n".join(cleaned_lines)

    except Exception as exc:
        logger.error("Failed to extract brochure summary: %s", exc)
        return ""


def download_and_analyze_brochure(
    tender_id: int,
    client: Any,
    details: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Download brochure, extract plan info and generate summary.

    Args:
        tender_id: The tender's MichrazID.
        client: LandTendersClient instance.
        details: Pre-fetched tender details (optional, will fetch if None).

    Returns:
        Dict with keys: plan_number, gush, helka, lots, summary, purpose,
        source_doc, success, errors.
    """
    result: Dict[str, Any] = {
        "plan_number": None,
        "gush": None,
        "helka": None,
        "lots": [],
        "summary": "",
        "purpose": None,
        "source_doc": None,
        "success": False,
        "errors": [],
    }

    # Step 1: Get tender details
    if details is None:
        details = client.get_tender_details_cached(tender_id)
    if not details:
        result["errors"].append(f"Could not fetch details for tender {tender_id}")
        return result

    # Step 2: Find the brochure document
    doc = find_pirsum_rishon(details)
    if not doc:
        result["errors"].append("No brochure document found")
        return result

    result["source_doc"] = doc.get("Teur") or doc.get("DocName") or "unknown"

    # Step 3: Download the PDF
    logger.info("Downloading brochure for tender %d...", tender_id)
    pdf_bytes = client.download_document(doc)
    if not pdf_bytes:
        result["errors"].append("Failed to download brochure PDF")
        return result

    logger.info("Downloaded brochure: %d bytes", len(pdf_bytes))

    # Step 4: Extract plan number, gush, helka, lots
    try:
        # Write to a temp BytesIO and use TenderPDFExtractor
        # TenderPDFExtractor expects a Path, so we write to tmp
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(pdf_bytes)
            tmp_path = tmp.name

        from pathlib import Path
        extractor = TenderPDFExtractor()
        extract_result = extractor.extract(Path(tmp_path))

        result["plan_number"] = extract_result.get("taba")
        result["purpose"] = extract_result.get("purpose")
        result["lots"] = extract_result.get("plots", [])

        # Extract gush/helka from first plot if available
        if result["lots"]:
            first_plot = result["lots"][0]
            result["gush"] = first_plot.get("gush")
            result["helka"] = first_plot.get("helka")

        # Clean up temp file
        Path(tmp_path).unlink(missing_ok=True)

    except Exception as exc:
        result["errors"].append(f"PDF extraction failed: {exc}")
        logger.exception("PDF extraction failed for tender %d", tender_id)

    # Step 5: Generate summary
    result["summary"] = generate_brochure_summary(pdf_bytes)

    # Determine success
    result["success"] = bool(result["plan_number"] or result["lots"] or result["summary"])

    if result["success"]:
        logger.info(
            "Brochure analysis complete for tender %d: plan=%s, lots=%d, summary=%d chars",
            tender_id,
            result["plan_number"],
            len(result["lots"]),
            len(result["summary"]),
        )
    else:
        logger.warning("Brochure analysis yielded no data for tender %d", tender_id)

    return result


def trigger_extraction_workflow(tender_id: int) -> bool:
    """Trigger the GitHub Actions building rights extraction workflow.

    Dispatches the extract_building_rights.yml workflow with the given
    tender ID as input.

    Args:
        tender_id: The tender's MichrazID.

    Returns:
        True if the dispatch was accepted (HTTP 204).
    """
    gh_pat = _get("GH_PAT", "")
    if not gh_pat:
        logger.error("GH_PAT not configured — cannot trigger extraction workflow")
        return False

    url = f"https://api.github.com/repos/{_GH_REPO}/actions/workflows/{_GH_WORKFLOW_FILE}/dispatches"
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {gh_pat}",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    payload = {
        "ref": "master",
        "inputs": {
            "tender_id": str(tender_id),
        },
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=15)
        if response.status_code == 204:
            logger.info(
                "Triggered extraction workflow for tender %d", tender_id,
            )
            return True

        logger.error(
            "GitHub dispatch failed (HTTP %d): %s",
            response.status_code,
            response.text[:200],
        )
        return False

    except requests.RequestException as exc:
        logger.error("GitHub dispatch request failed: %s", exc)
        return False
