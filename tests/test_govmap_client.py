"""Tests for govmap_client module.

Covers URL resolution, batch processing, error handling, and the
build_govmap_url helper. All HTTP calls are mocked.
"""

from unittest.mock import MagicMock, patch

import pytest
import requests

from govmap_client import (
    batch_resolve_govmap_urls,
    build_govmap_url,
    resolve_govmap_url,
)


# ------------------------------------------------------------------
# build_govmap_url
# ------------------------------------------------------------------


class TestBuildGovmapUrl:
    """Tests for the build_govmap_url helper."""

    def test_integer_mishasava(self) -> None:
        assert build_govmap_url(6004120) == (
            "https://www.govmap.gov.il/?app=app07&ma=6004120"
        )

    def test_string_mishasava(self) -> None:
        assert build_govmap_url("123456") == (
            "https://www.govmap.gov.il/?app=app07&ma=123456"
        )


# ------------------------------------------------------------------
# resolve_govmap_url
# ------------------------------------------------------------------


def _mock_response(json_data: dict, status_code: int = 200) -> MagicMock:
    """Create a mock requests.Response with the given JSON data."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data
    resp.raise_for_status.return_value = None
    return resp


class TestResolveGovmapUrl:
    """Tests for resolve_govmap_url."""

    @patch("govmap_client.requests.get")
    def test_successful_resolution(self, mock_get: MagicMock) -> None:
        mock_get.return_value = _mock_response({
            "tabaPlans": [
                {"mishasava": 6004120, "planName": "Test Plan"},
            ],
        })

        result = resolve_govmap_url("33/101/02/24")

        assert result == "https://www.govmap.gov.il/?app=app07&ma=6004120"
        # Verify the plan number was URL-encoded (/ → %2F)
        call_url = mock_get.call_args[0][0]
        assert "33%2F101%2F02%2F24" in call_url

    @patch("govmap_client.requests.get")
    def test_multiple_taba_plans_returns_first(self, mock_get: MagicMock) -> None:
        mock_get.return_value = _mock_response({
            "tabaPlans": [
                {"mishasava": 1111, "planName": "First"},
                {"mishasava": 2222, "planName": "Second"},
            ],
        })

        result = resolve_govmap_url("307-0692160")
        assert result == "https://www.govmap.gov.il/?app=app07&ma=1111"

    @patch("govmap_client.requests.get")
    def test_empty_taba_plans(self, mock_get: MagicMock) -> None:
        mock_get.return_value = _mock_response({"tabaPlans": []})

        result = resolve_govmap_url("nonexistent-plan")
        assert result is None

    @patch("govmap_client.requests.get")
    def test_missing_taba_plans_key(self, mock_get: MagicMock) -> None:
        mock_get.return_value = _mock_response({"someOtherKey": "value"})

        result = resolve_govmap_url("3050356")
        assert result is None

    @patch("govmap_client.requests.get")
    def test_taba_plan_without_mishasava(self, mock_get: MagicMock) -> None:
        mock_get.return_value = _mock_response({
            "tabaPlans": [{"planName": "No ID"}],
        })

        result = resolve_govmap_url("plan-no-id")
        assert result is None

    @patch("govmap_client.requests.get")
    def test_timeout_error(self, mock_get: MagicMock) -> None:
        mock_get.side_effect = requests.exceptions.Timeout("timed out")

        result = resolve_govmap_url("timeout-plan")
        assert result is None

    @patch("govmap_client.requests.get")
    def test_connection_error(self, mock_get: MagicMock) -> None:
        mock_get.side_effect = requests.exceptions.ConnectionError("no conn")

        result = resolve_govmap_url("conn-error-plan")
        assert result is None

    @patch("govmap_client.requests.get")
    def test_http_error(self, mock_get: MagicMock) -> None:
        resp = MagicMock()
        resp.raise_for_status.side_effect = requests.exceptions.HTTPError("500")
        mock_get.return_value = resp

        result = resolve_govmap_url("http-error-plan")
        assert result is None

    @patch("govmap_client.requests.get")
    def test_malformed_json(self, mock_get: MagicMock) -> None:
        resp = MagicMock()
        resp.raise_for_status.return_value = None
        resp.json.side_effect = ValueError("bad json")
        mock_get.return_value = resp

        result = resolve_govmap_url("bad-json-plan")
        assert result is None

    def test_empty_plan_number(self) -> None:
        result = resolve_govmap_url("")
        assert result is None

    def test_none_plan_number(self) -> None:
        # Type hint says str, but defensive coding
        result = resolve_govmap_url(None)  # type: ignore[arg-type]
        assert result is None

    def test_whitespace_only_plan_number(self) -> None:
        result = resolve_govmap_url("   ")
        assert result is None

    @patch("govmap_client.requests.get")
    def test_plan_number_stripped(self, mock_get: MagicMock) -> None:
        mock_get.return_value = _mock_response({
            "tabaPlans": [{"mishasava": 999}],
        })

        resolve_govmap_url("  3050356  ")
        call_url = mock_get.call_args[0][0]
        assert call_url.endswith("/3050356")

    @patch("govmap_client.requests.get")
    def test_null_taba_plans(self, mock_get: MagicMock) -> None:
        mock_get.return_value = _mock_response({"tabaPlans": None})

        result = resolve_govmap_url("null-plans")
        assert result is None


# ------------------------------------------------------------------
# batch_resolve_govmap_urls
# ------------------------------------------------------------------


class TestBatchResolveGovmapUrls:
    """Tests for batch_resolve_govmap_urls."""

    @patch("govmap_client.resolve_govmap_url")
    @patch("govmap_client.time.sleep")
    def test_batch_resolve(
        self, mock_sleep: MagicMock, mock_resolve: MagicMock,
    ) -> None:
        mock_resolve.side_effect = [
            "https://www.govmap.gov.il/?app=app07&ma=111",
            None,
            "https://www.govmap.gov.il/?app=app07&ma=333",
        ]

        result = batch_resolve_govmap_urls(["a", "b", "c"], delay=0.1)

        assert result == {
            "a": "https://www.govmap.gov.il/?app=app07&ma=111",
            "b": None,
            "c": "https://www.govmap.gov.il/?app=app07&ma=333",
        }
        assert mock_resolve.call_count == 3
        # Sleep called between requests (not after last)
        assert mock_sleep.call_count == 2

    @patch("govmap_client.resolve_govmap_url")
    @patch("govmap_client.time.sleep")
    def test_empty_list(
        self, mock_sleep: MagicMock, mock_resolve: MagicMock,
    ) -> None:
        result = batch_resolve_govmap_urls([])
        assert result == {}
        mock_resolve.assert_not_called()
        mock_sleep.assert_not_called()

    @patch("govmap_client.resolve_govmap_url")
    @patch("govmap_client.time.sleep")
    def test_single_item_no_sleep(
        self, mock_sleep: MagicMock, mock_resolve: MagicMock,
    ) -> None:
        mock_resolve.return_value = "https://www.govmap.gov.il/?app=app07&ma=1"

        result = batch_resolve_govmap_urls(["only-one"], delay=0.5)

        assert len(result) == 1
        mock_sleep.assert_not_called()

    @patch("govmap_client.resolve_govmap_url")
    @patch("govmap_client.time.sleep")
    def test_zero_delay(
        self, mock_sleep: MagicMock, mock_resolve: MagicMock,
    ) -> None:
        mock_resolve.return_value = None

        batch_resolve_govmap_urls(["a", "b"], delay=0)
        mock_sleep.assert_not_called()
