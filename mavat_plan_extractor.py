import logging
import re
from pathlib import Path
from typing import Optional, Any
import pdfplumber

# Import the existing client
try:
    from mavat_client import MavatClient
except ImportError:
    # Fallback for running as script from different dir
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from mavat_client import MavatClient

logger = logging.getLogger(__name__)

class MavatPlanExtractor:
    """Coordinator for searching, downloading, and extracting data from Mavat plans."""

    def __init__(self, output_dir: str = "data/mavat_cache"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.client = MavatClient(output_dir=self.output_dir)

    def process_plan(self, plan_input: str) -> dict[str, Any]:
        """Full flow: Download PDF -> Extract Data -> Return Result.
        
        Args:
            plan_input: Plan Number (e.g. "102-0909267") OR Mavat URL.
        """
        
        result = {
            "plan_number": plan_input,
            "status": "pending",
            "pdf_path": None,
            "extracted_data": {},
            "error": None
        }

        # Check if input is a URL with MP_ID
        mp_id_match = re.search(r"/SV4/1/(\d+)", plan_input)
        
        logger.info(f"Starting Mavat process for {plan_input}")
        
        if mp_id_match:
            mp_id = mp_id_match.group(1)
            logger.info(f"Detected MP_ID {mp_id} from URL")
            download_res = self.client.download_by_mp_id(mp_id)
        else:
            download_res = self.client.download_horaot(plan_input)
        
        if download_res["status"] != "success":
            result["status"] = "download_failed"
            result["error"] = download_res.get("error", "Unknown download error")
            return result

        pdf_path = Path(download_res["file_path"])
        result["pdf_path"] = str(pdf_path)

        # 2. Extract
        try:
            extracted = self._parse_pdf(pdf_path)
            result["extracted_data"] = extracted
            result["status"] = "success"
        except Exception as e:
            logger.error(f"Extraction failed: {e}")
            result["status"] = "extraction_failed"
            result["error"] = str(e)

        return result

    def _parse_pdf(self, pdf_path: Path) -> dict[str, Any]:
        """Parse the PDF to find key zoning information."""
        data = {
            "text_preview": "",
            "keywords_found": []
        }
        
        with pdfplumber.open(pdf_path) as pdf:
            # Read first few pages for summary
            full_text = ""
            for i, page in enumerate(pdf.pages[:10]): # Scan first 10 pages
                text = page.extract_text()
                if text:
                    full_text += text + "\n"
            
            data["text_preview"] = full_text[:500] + "..." # First 500 chars

            # Simple Keyword Search (Proof of Concept)
            keywords = ["זכויות בניה", "שטח עיקרי", "שטח שירות", "קומות"]
            for kw in keywords:
                if kw in full_text:
                    data["keywords_found"].append(kw)
                    
            # TODO: Add complex table extraction here
            
        return data

# Singleton instance provided for ease of use
extractor = MavatPlanExtractor()
