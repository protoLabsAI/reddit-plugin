"""Test Reddit OAuth2 auth module — token caching, refresh, invalidation."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from auth import RedditAuth  # noqa: E402


@pytest.fixture
def auth():
    return RedditAuth("test_id", "test_secret", "test_user", "test_pass")


def _mock_token_response(token="abc123", expires_in=3600):
    """Create a mock requests.post response for token exchange."""
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"access_token": token, "expires_in": expires_in, "token_type": "bearer"}
    resp.raise_for_status = MagicMock()
    return resp


class TestRedditAuth:
    def test_user_agent_format(self, auth):
        ua = auth.user_agent
        assert "protoAgent:reddit-plugin" in ua
        assert "test_user" in ua

    @patch("requests.post")
    def test_get_token_fetches_on_first_call(self, mock_post, auth):
        mock_post.return_value = _mock_token_response("fresh_token")
        token = auth.get_token()
        assert token == "fresh_token"
        mock_post.assert_called_once()

    @patch("requests.post")
    def test_get_token_caches(self, mock_post, auth):
        mock_post.return_value = _mock_token_response("cached_token", 3600)
        t1 = auth.get_token()
        t2 = auth.get_token()
        assert t1 == t2 == "cached_token"
        # Only one HTTP call — second call used cache
        assert mock_post.call_count == 1

    @patch("requests.post")
    def test_invalidate_forces_refresh(self, mock_post, auth):
        mock_post.return_value = _mock_token_response("token1")
        auth.get_token()
        assert mock_post.call_count == 1

        auth.invalidate()
        mock_post.return_value = _mock_token_response("token2")
        token = auth.get_token()
        assert token == "token2"
        assert mock_post.call_count == 2

    @patch("requests.post")
    def test_refresh_on_expiry(self, mock_post, auth):
        # Set a token that's already expired
        mock_post.return_value = _mock_token_response("expired", 0)
        auth.get_token()

        # Next call should refresh
        mock_post.return_value = _mock_token_response("refreshed", 3600)
        token = auth.get_token()
        assert token == "refreshed"
        assert mock_post.call_count == 2

    @patch("requests.post")
    def test_auth_error_raises(self, mock_post, auth):
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {"error": "invalid_grant", "message": "bad password"}
        resp.raise_for_status = MagicMock()
        mock_post.return_value = resp

        with pytest.raises(RuntimeError, match="Reddit auth error"):
            auth.get_token()

    @patch("requests.post")
    def test_credentials_sent_correctly(self, mock_post, auth):
        mock_post.return_value = _mock_token_response()
        auth.get_token()

        call_args = mock_post.call_args
        # auth= is passed as a kwarg
        assert call_args.kwargs.get("auth") == ("test_id", "test_secret")
        data = call_args.kwargs.get("data", {})
        assert data["grant_type"] == "password"
        assert data["username"] == "test_user"
        assert data["password"] == "test_pass"
