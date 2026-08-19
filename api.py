"""Low-level Reddit API client — all HTTP calls go through here."""

from __future__ import annotations

import logging
from typing import Any, Optional

log = logging.getLogger(__name__)

API_BASE = "https://oauth.reddit.com"


class RedditAPI:
    """Thin wrapper around the Reddit OAuth API.

    Handles auth header injection, User-Agent, rate-limit tracking,
    and single-retry on 401 (token refresh).
    """

    def __init__(self, auth):
        self.auth = auth
        self._rate_remaining: Optional[float] = None
        self._rate_reset: Optional[float] = None

    def get(self, path: str, params: dict | None = None) -> Any:
        """GET a Reddit API endpoint. Returns parsed JSON."""
        return self._request("GET", path, params=params)

    def post(self, path: str, data: dict | None = None) -> Any:
        """POST to a Reddit API endpoint. Returns parsed JSON."""
        return self._request("POST", path, data=data)

    def _request(self, method: str, path: str, *, params=None, data=None, _retried=False) -> Any:
        import requests

        url = f"{API_BASE}{path}"
        headers = {
            "Authorization": f"Bearer {self.auth.get_token()}",
            "User-Agent": self.auth.user_agent,
        }
        resp = requests.request(method, url, headers=headers, params=params, data=data, timeout=15)

        # Track rate limits from response headers
        if "x-ratelimit-remaining" in resp.headers:
            self._rate_remaining = float(resp.headers["x-ratelimit-remaining"])
        if "x-ratelimit-reset" in resp.headers:
            self._rate_reset = float(resp.headers["x-ratelimit-reset"])

        # Auto-retry once on 401 (expired token)
        if resp.status_code == 401 and not _retried:
            log.info("Reddit 401 — refreshing token and retrying")
            self.auth.invalidate()
            return self._request(method, path, params=params, data=data, _retried=True)

        resp.raise_for_status()
        return resp.json()

    @property
    def rate_info(self) -> str:
        """Human-readable rate-limit status."""
        if self._rate_remaining is not None:
            return f"{self._rate_remaining:.0f} requests remaining, resets in {self._rate_reset:.0f}s"
        return "no rate data yet"
