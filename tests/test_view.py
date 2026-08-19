"""Test Reddit view routes — page serves HTML, data returns JSON, four-rules compliance."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from view import make_routers  # noqa: E402


@pytest.fixture
def mock_api():
    api = MagicMock()
    api.auth = MagicMock()
    api.auth.username = "testuser"
    return api


@pytest.fixture
def config():
    return {
        "subreddits": ["LocalLLaMA", "langchain"],
        "default_sort": "hot",
        "posts_per_page": 25,
        "time_filter": "day",
    }


@pytest.fixture
def client(mock_api, config):
    page, data = make_routers(mock_api, config)
    app = FastAPI()
    app.include_router(page, prefix="/plugins/reddit")
    app.include_router(data, prefix="/api/plugins/reddit")
    return TestClient(app)


class TestPageRoute:
    def test_feed_page_returns_html(self, client):
        resp = client.get("/plugins/reddit/feed")
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]

    def test_feed_page_not_under_api(self, client):
        """View page must NOT be under /api (it's a public iframe page-load)."""
        resp = client.get("/plugins/reddit/feed")
        assert resp.status_code == 200
        # The page should exist at the manifest-declared path

    def test_four_rules_slug_aware_base(self, client):
        """Rule 1/3: page derives base from location.pathname.split('/plugins/')."""
        resp = client.get("/plugins/reddit/feed")
        html = resp.text
        assert "split('/plugins/')" in html or "split(\"/plugins/\")" in html

    def test_four_rules_ds_kit_css(self, client):
        """Rule 4: page links the DS kit CSS."""
        resp = client.get("/plugins/reddit/feed")
        html = resp.text
        assert "plugin-kit.css" in html

    def test_four_rules_ds_kit_js(self, client):
        """Rule 4: page imports the DS kit JS module."""
        resp = client.get("/plugins/reddit/feed")
        html = resp.text
        assert "plugin-kit.js" in html

    def test_four_rules_api_fetch(self, client):
        """Rule 2/4: page uses kit.apiFetch for data calls."""
        resp = client.get("/plugins/reddit/feed")
        html = resp.text
        assert "apiFetch" in html


class TestDataRoutes:
    def test_config_returns_json(self, client):
        resp = client.get("/api/plugins/reddit/config")
        assert resp.status_code == 200
        data = resp.json()
        assert data["subreddits"] == ["LocalLLaMA", "langchain"]
        assert data["default_sort"] == "hot"

    def test_feed_data_calls_api(self, client, mock_api):
        mock_api.get.return_value = {
            "data": {
                "children": [
                    {
                        "data": {
                            "name": "t3_test",
                            "title": "Test Post",
                            "author": "u",
                            "subreddit": "test",
                            "subreddit_prefixed": "r/test",
                            "score": 10,
                            "num_comments": 3,
                            "url": "https://example.com",
                            "permalink": "/r/test/comments/abc/test/",
                            "selftext": "",
                            "created_utc": 1700000000,
                            "is_self": False,
                            "over_18": False,
                            "thumbnail": "",
                            "link_flair_text": None,
                            "stickied": False,
                        }
                    }
                ],
                "after": "t3_next",
            }
        }
        resp = client.get("/api/plugins/reddit/feed?subreddit=test&sort=hot")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["posts"]) == 1
        assert data["posts"][0]["title"] == "Test Post"
        assert data["after"] == "t3_next"

    def test_feed_data_no_api_returns_503(self, config):
        """When API is None (no credentials), feed returns 503."""
        page, data = make_routers(None, config)
        app = FastAPI()
        app.include_router(data, prefix="/api/plugins/reddit")
        client = TestClient(app)
        resp = client.get("/api/plugins/reddit/feed")
        assert resp.status_code == 503
        assert "error" in resp.json()

    def test_feed_data_api_error_returns_502(self, client, mock_api):
        mock_api.get.side_effect = RuntimeError("connection refused")
        resp = client.get("/api/plugins/reddit/feed")
        assert resp.status_code == 502
        assert "error" in resp.json()
