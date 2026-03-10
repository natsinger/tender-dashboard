"""
GovMap TABA plan resolver.

Resolves RMI plan numbers to GovMap URLs by querying the GovMap
internal TABA search API to obtain the mishasava ID, then building
the viewer URL.

Usage:
    from govmap_client import resolve_govmap_url, batch_resolve_govmap_urls
    url = resolve_govmap_url("33/101/02/24")
    # => "https://www.govmap.gov.il/?app=app07&ma=6004120"
"""

import logging
import time
from urllib.parse import quote

import requests

logger = logging.getLogger(__name__)

_GOVMAP_BASE = "https://www.govmap.gov.il"
_TABA_API = f"{_GOVMAP_BASE}/api/taba/taba/plan"
_MISHASAVA_API = f"{_GOVMAP_BASE}/api/taba/taba/mishasava/exact"
_VIEWER_URL = f"{_GOVMAP_BASE}/?app=app07&ma="
_REQUEST_TIMEOUT = 10


def build_govmap_url(mishasava: int | str) -> str:
    """Build a GovMap viewer URL from a mishasava ID.

    Args:
        mishasava: The numeric plan identifier from GovMap.

    Returns:
        Full GovMap viewer URL.
    """
    return f"{_VIEWER_URL}{mishasava}"


def _is_pure_numeric(value: str) -> bool:
    """Check if a string is a pure numeric ID (likely a mishasava)."""
    return value.isdigit() and len(value) >= 4


def _verify_mishasava(mishasava: str) -> bool:
    """Verify a mishasava ID exists in GovMap by calling the exact lookup.

    Args:
        mishasava: Numeric ID to verify.

    Returns:
        True if GovMap recognises this ID.
    """
    url = f"{_MISHASAVA_API}/{mishasava}"
    try:
        resp = requests.get(url, timeout=_REQUEST_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        plans = data.get("tabaPlans")
        return bool(plans and isinstance(plans, list) and len(plans) > 0)
    except (requests.exceptions.RequestException, ValueError):
        return False


def _search_by_plan_number(plan_number: str) -> str | None:
    """Search GovMap TABA API by plan number text.

    Args:
        plan_number: Plan number string (e.g. "33/101/02/24").

    Returns:
        GovMap viewer URL, or None.
    """
    encoded = quote(plan_number.strip(), safe="")
    url = f"{_TABA_API}/{encoded}"

    try:
        resp = requests.get(url, timeout=_REQUEST_TIMEOUT)
        resp.raise_for_status()
    except requests.exceptions.Timeout:
        logger.warning("GovMap API timeout for plan_number=%s", plan_number)
        return None
    except requests.exceptions.RequestException as exc:
        logger.warning(
            "GovMap API request failed for plan_number=%s: %s",
            plan_number, exc,
        )
        return None

    try:
        data = resp.json()
    except ValueError:
        logger.warning(
            "GovMap API returned non-JSON response for plan_number=%s",
            plan_number,
        )
        return None

    taba_plans = data.get("tabaPlans")
    if not taba_plans or not isinstance(taba_plans, list):
        return None

    for plan in taba_plans:
        mishasava = plan.get("mishasava")
        if mishasava:
            return build_govmap_url(mishasava)

    return None


def resolve_govmap_url(plan_number: str) -> str | None:
    """Resolve an RMI plan number to a GovMap viewer URL.

    Strategy:
    1. If the plan_number is a pure numeric string (4+ digits), treat it
       as a potential mishasava ID — verify via the exact lookup endpoint.
       If valid, build the URL directly (no search needed).
    2. Otherwise, search the TABA API by plan number text.

    Args:
        plan_number: The plan number as it appears in the tenders table
            (e.g. "33/101/02/24", "307-0692160", "3050356").

    Returns:
        GovMap viewer URL string, or None if the plan could not be
        resolved (no match, network error, or missing mishasava).
    """
    if not plan_number or not plan_number.strip():
        logger.debug("resolve_govmap_url called with empty plan_number")
        return None

    cleaned = plan_number.strip()

    # Strategy 1: pure numeric → likely a mishasava ID already
    if _is_pure_numeric(cleaned):
        if _verify_mishasava(cleaned):
            logger.info(
                "plan_number=%s is a valid mishasava ID (direct)",
                cleaned,
            )
            return build_govmap_url(cleaned)
        logger.debug(
            "plan_number=%s is numeric but not a valid mishasava", cleaned,
        )

    # Strategy 2: search by plan number text
    result = _search_by_plan_number(cleaned)
    if result:
        logger.info("Resolved plan_number=%s via search", cleaned)
        return result

    logger.debug("Could not resolve plan_number=%s", cleaned)
    return None


def batch_resolve_govmap_urls(
    plan_numbers: list[str],
    delay: float = 0.3,
) -> dict[str, str | None]:
    """Resolve multiple plan numbers to GovMap URLs with rate limiting.

    Args:
        plan_numbers: List of plan number strings to resolve.
        delay: Seconds to wait between API requests (rate limiting).

    Returns:
        Dict mapping each plan_number to its GovMap URL (or None).
    """
    results: dict[str, str | None] = {}
    total = len(plan_numbers)
    logger.info("Starting batch resolve for %d plan numbers", total)

    for i, plan_number in enumerate(plan_numbers):
        results[plan_number] = resolve_govmap_url(plan_number)

        if (i + 1) % 10 == 0:
            logger.info(
                "Batch progress: %d/%d resolved", i + 1, total,
            )

        # Rate limit: sleep between requests (skip after last one)
        if i < total - 1 and delay > 0:
            time.sleep(delay)

    logger.info(
        "Batch resolve complete: %d/%d resolved successfully",
        sum(1 for v in results.values() if v is not None),
        total,
    )
    return results
