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


def resolve_govmap_url(plan_number: str) -> str | None:
    """Resolve an RMI plan number to a GovMap viewer URL.

    Queries the GovMap TABA search API to find the mishasava ID
    for the given plan number, then builds the viewer URL.

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
        logger.debug(
            "No tabaPlans found for plan_number=%s", plan_number,
        )
        return None

    for plan in taba_plans:
        mishasava = plan.get("mishasava")
        if mishasava:
            govmap_url = build_govmap_url(mishasava)
            logger.info(
                "Resolved plan_number=%s → mishasava=%s",
                plan_number, mishasava,
            )
            return govmap_url

    logger.debug(
        "tabaPlans found but no mishasava for plan_number=%s", plan_number,
    )
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
