"""Coordinator for searching, downloading, and extracting data from Mavat plans.

Full pipeline: search for plan → download הוראות PDF → extract building rights
table (Section 5) and keyword data.

Usage:
    from mavat_plan_extractor import MavatPlanExtractor

    ext = MavatPlanExtractor()
    result = ext.process_plan("102-0909267")
    print(result)
"""

import logging
import re
from pathlib import Path
from typing import Any

import pdfplumber

from building_rights_extractor import extract_building_rights

try:
    from mavat_client import MavatClient
except ImportError:
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from mavat_client import MavatClient

logger = logging.getLogger(__name__)


class MavatPlanExtractor:
    """Coordinator for searching, downloading, and extracting data from Mavat plans."""

    def __init__(self, output_dir: str = "data/mavat_cache") -> None:
        """Initialize the extractor.

        Args:
            output_dir: Directory for cached downloads and extracted data.
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.client = MavatClient(output_dir=self.output_dir)

    def process_plan(self, plan_input: str) -> dict[str, Any]:
        """Full flow: Download PDF → Extract Data → Return Result.

        Args:
            plan_input: Plan number (e.g. "102-0909267") OR Mavat URL.

        Returns:
            Dict with keys: plan_number, status, pdf_path, extracted_data, error.
        """
        result: dict[str, Any] = {
            "plan_number": plan_input,
            "status": "pending",
            "pdf_path": None,
            "extracted_data": {},
            "error": None,
        }

        # Check if input is a URL with MP_ID
        mp_id_match = re.search(r"/SV4/1/(\d+)", plan_input)

        logger.info("Starting Mavat process for %s", plan_input)

        if mp_id_match:
            mp_id = mp_id_match.group(1)
            logger.info("Detected MP_ID %s from URL", mp_id)
            download_res = self.client.download_by_mp_id(mp_id)
        else:
            download_res = self.client.download_horaot(plan_input)

        if download_res["status"] != "success":
            result["status"] = "download_failed"
            result["error"] = download_res.get("error", "Unknown download error")
            return result

        pdf_path = Path(download_res["file_path"])
        result["pdf_path"] = str(pdf_path)

        # Extract data from PDF
        try:
            extracted = self._parse_pdf(pdf_path, plan_input)
            result["extracted_data"] = extracted
            result["status"] = "success"
        except Exception as e:
            logger.error("Extraction failed: %s", e)
            result["status"] = "extraction_failed"
            result["error"] = str(e)

        return result

    def _parse_pdf(self, pdf_path: Path, plan_number: str) -> dict[str, Any]:
        """Parse the PDF to extract zoning information.

        Extracts:
        1. Building rights table (Section 5) via building_rights_extractor
        2. Keyword presence for quick filtering

        Args:
            pdf_path: Path to the downloaded PDF.
            plan_number: Plan number for metadata.

        Returns:
            Dict with text_preview, keywords_found, and building_rights.
        """
        data: dict[str, Any] = {
            "text_preview": "",
            "keywords_found": [],
            "building_rights": None,
        }

        # Extract building rights table (Section 5)
        rights_result = extract_building_rights(pdf_path, plan_number=plan_number)
        if rights_result["success"]:
            # Strip internal _raw data before storing
            clean_rows = []
            for row in rights_result.get("rows", []):
                clean_rows.append({k: v for k, v in row.items() if k != "_raw"})
            rights_result["rows"] = clean_rows
            data["building_rights"] = rights_result
            logger.info(
                "Extracted %d building rights rows from %s",
                len(clean_rows), pdf_path.name,
            )
        else:
            logger.warning(
                "Building rights extraction failed: %s",
                rights_result.get("errors"),
            )
            data["building_rights"] = rights_result

        # Keyword search for quick filtering
        with pdfplumber.open(pdf_path) as pdf:
            full_text = ""
            for page in pdf.pages[:10]:
                text = page.extract_text()
                if text:
                    full_text += text + "\n"

            data["text_preview"] = full_text[:500] + "..."

            keywords = ["זכויות בניה", "שטח עיקרי", "שטח שירות", "קומות"]
            for kw in keywords:
                if kw in full_text:
                    data["keywords_found"].append(kw)

        return data


# Singleton instance provided for ease of use
extractor = MavatPlanExtractor()
