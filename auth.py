"""Reddit OAuth2 token management — script-app password grant."""

from __future__ import annotations

import logging
import threading
import time
from typing import Optional

log = logging.getLogger(__name__)

TOKEN_URL = "https://www.reddit.com/api/v1/access_token"
TOKEN_BUFFER_SECONDS = 60  # refresh this many seconds before expiry


class RedditAuth:
    """Manages a Reddit OAuth2 access token (script-app password grant).

    The token is lazily fetched on first use and auto-refreshed when expired.
    Thread-safe via a lock.
    """

    def __init__(self, client_id: str, client_secret: str, username: str, password: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.username = username
        self.password = password
        self._token: Optional[str] = None
        self._expires_at: float = 0
        self._lock = threading.Lock()

    @property
    def user_agent(self) -> str:
        return f"protoAgent:reddit-plugin:0.1.0 (by /u/{self.username})"

    def get_token(self) -> str:
        """Return a valid access token, refreshing if needed."""
        with self._lock:
            if self._token and time.time() < self._expires_at - TOKEN_BUFFER_SECONDS:
                return self._token
            return self._refresh()

    def _refresh(self) -> str:
        """Exchange credentials for a new access token."""
        import requests

        resp = requests.post(
            TOKEN_URL,
            auth=(self.client_id, self.client_secret),
            data={
                "grant_type": "password",
                "username": self.username,
                "password": self.password,
            },
            headers={"User-Agent": self.user_agent},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        if "error" in data:
            raise RuntimeError(f"Reddit auth error: {data['error']} — {data.get('message', '')}")
        self._token = data["access_token"]
        self._expires_at = time.time() + data.get("expires_in", 3600)
        log.info("Reddit token refreshed, expires in %ds", data.get("expires_in", 3600))
        return self._token

    def invalidate(self):
        """Force a re-fetch on next call (e.g. after a 401)."""
        with self._lock:
            self._token = None
            self._expires_at = 0
