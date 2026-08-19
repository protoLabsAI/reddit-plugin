"""Test Reddit API client — GET/POST, 401 retry, rate-limit tracking."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from api import RedditAPI  # noqa: E402


@pytest.fixture
def mock_auth():
    auth = MagicMock()
    auth.get_token.return_value = "test_token"
    auth.user_agent = "protoAgent:reddit-plugin:0.1.0 (by /u/test)"
    auth.username = "test"
    return auth


@pytest.fixture
def api(mock_auth):
    return RedditAPI(mock_auth)


def _mock_response(json_data=None, status_code=200, headers=None):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data or {}
    resp.headers = headers or {}
    resp.raise_for_status = MagicMock()
    return resp


class TestRedditAPI:
    @patch("requests.request")
    def test_get_calls_correct_url(self, mock_req, api):
        mock_req.return_value = _mock_response({"data": "test"})
        result = api.get("/r/python/hot", params={"limit": 5})
        assert result == {"data": "test"}
        call_args = mock_req.call_args
        assert call_args[0] == ("GET", "https://oauth.reddit.com/r/python/hot")
        assert call_args[1]["params"] == {"limit": 5}

    @patch("requests.request")
    def test_post_sends_data(self, mock_req, api):
        mock_req.return_value = _mock_response({"success": True})
        result = api.post("/api/vote", data={"id": "t3_abc", "dir": "1"})
        assert result == {"success": True}
        call_args = mock_req.call_args
        assert call_args[0][0] == "POST"
        assert call_args[1]["data"] == {"id": "t3_abc", "dir": "1"}

    @patch("requests.request")
    def test_auth_header_included(self, mock_req, api):
        mock_req.return_value = _mock_response()
        api.get("/test")
        headers = mock_req.call_args[1]["headers"]
        assert headers["Authorization"] == "Bearer test_token"
        assert "protoAgent" in headers["User-Agent"]

    @patch("requests.request")
    def test_401_triggers_retry(self, mock_req, api):
        # First call returns 401, second succeeds
        resp_401 = MagicMock()
        resp_401.status_code = 401
        resp_401.headers = {}

        resp_200 = _mock_response({"retried": True})
        mock_req.side_effect = [resp_401, resp_200]

        result = api.get("/test")
        assert result == {"retried": True}
        assert mock_req.call_count == 2
        api.auth.invalidate.assert_called_once()

    @patch("requests.request")
    def test_rate_limit_headers_tracked(self, mock_req, api):
        mock_req.return_value = _mock_response(
            headers={"x-ratelimit-remaining": "95.0", "x-ratelimit-reset": "300"}
        )
        api.get("/test")
        assert api._rate_remaining == 95.0
        assert api._rate_reset == 300.0
        assert "95 requests remaining" in api.rate_info

    def test_rate_info_default(self, api):
        assert api.rate_info == "no rate data yet"
