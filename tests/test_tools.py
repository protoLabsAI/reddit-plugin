"""Test Reddit tools — creation, count, format helpers."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools import make_tools, _format_post, _format_comment  # noqa: E402


@pytest.fixture
def mock_api():
    api = MagicMock()
    api.auth = MagicMock()
    api.auth.username = "testuser"
    return api


@pytest.fixture
def config():
    return {
        "subreddits": ["LocalLLaMA", "langchain", "claudeai"],
        "default_sort": "hot",
        "posts_per_page": 25,
        "time_filter": "day",
    }


@pytest.fixture
def tools(mock_api, config):
    return make_tools(mock_api, config)


class TestToolCreation:
    def test_creates_15_tools(self, tools):
        assert len(tools) == 15

    def test_all_tools_have_names(self, tools):
        names = [t.name for t in tools]
        assert "reddit_feed" in names
        assert "reddit_post" in names
        assert "reddit_comments" in names
        assert "reddit_search" in names
        assert "reddit_user" in names
        assert "reddit_user_posts" in names
        assert "reddit_subscriptions" in names
        assert "reddit_saved" in names
        assert "reddit_inbox" in names
        assert "reddit_comment" in names
        assert "reddit_vote" in names
        assert "reddit_save_item" in names
        assert "reddit_subscribe" in names
        assert "reddit_submit" in names
        assert "reddit_message" in names

    def test_all_tools_have_descriptions(self, tools):
        for t in tools:
            assert t.description, f"Tool {t.name} has no description"


class TestFormatHelpers:
    def test_format_post_basic(self):
        raw = {
            "data": {
                "name": "t3_abc123",
                "title": "Test Post",
                "author": "testuser",
                "subreddit": "python",
                "subreddit_prefixed": "r/python",
                "score": 42,
                "num_comments": 10,
                "url": "https://example.com",
                "permalink": "/r/python/comments/abc123/test_post/",
                "selftext": "Hello world",
                "created_utc": 1700000000,
                "is_self": True,
                "over_18": False,
            }
        }
        p = _format_post(raw)
        assert p["id"] == "t3_abc123"
        assert p["title"] == "Test Post"
        assert p["author"] == "testuser"
        assert p["score"] == 42
        assert "reddit.com" in p["permalink"]

    def test_format_post_deleted_author(self):
        raw = {"data": {"title": "Deleted", "permalink": "/r/test/x/"}}
        p = _format_post(raw)
        assert p["author"] == "[deleted]"

    def test_format_post_truncates_selftext(self):
        raw = {"data": {"selftext": "x" * 1000, "permalink": "/r/t/x/"}}
        p = _format_post(raw)
        assert len(p["selftext"]) == 500

    def test_format_comment_basic(self):
        raw = {
            "kind": "t1",
            "data": {
                "name": "t1_def456",
                "author": "commenter",
                "body": "Great post!",
                "score": 15,
                "created_utc": 1700000000,
                "permalink": "/r/python/comments/abc/test/def456/",
            },
        }
        c = _format_comment(raw)
        assert c["id"] == "t1_def456"
        assert c["author"] == "commenter"
        assert c["body"] == "Great post!"
        assert c["depth"] == 0

    def test_format_comment_with_replies(self):
        raw = {
            "data": {
                "name": "t1_parent",
                "author": "parent",
                "body": "Top comment",
                "score": 10,
                "permalink": "/r/t/c/x/y/",
                "replies": {
                    "data": {
                        "children": [
                            {
                                "kind": "t1",
                                "data": {
                                    "name": "t1_child",
                                    "author": "child",
                                    "body": "Reply",
                                    "score": 3,
                                    "permalink": "/r/t/c/x/z/",
                                },
                            }
                        ]
                    }
                },
            }
        }
        c = _format_comment(raw)
        assert len(c["replies"]) == 1
        assert c["replies"][0]["depth"] == 1


class TestReadTools:
    def test_reddit_feed_uses_config_defaults(self, tools, mock_api, config):
        mock_api.get.return_value = {"data": {"children": []}}
        tool = next(t for t in tools if t.name == "reddit_feed")
        result = tool.invoke({})
        # Should have called with combined subreddits
        call_args = mock_api.get.call_args
        assert "LocalLLaMA+langchain+claudeai" in call_args[0][0]

    def test_reddit_feed_specific_sub(self, tools, mock_api):
        mock_api.get.return_value = {"data": {"children": []}}
        tool = next(t for t in tools if t.name == "reddit_feed")
        result = tool.invoke({"subreddit": "python", "sort": "new"})
        call_args = mock_api.get.call_args
        assert "/r/python/new" in call_args[0][0]

    def test_reddit_search_global(self, tools, mock_api):
        mock_api.get.return_value = {"data": {"children": []}}
        tool = next(t for t in tools if t.name == "reddit_search")
        tool.invoke({"query": "test query"})
        call_args = mock_api.get.call_args
        assert call_args[0][0] == "/search"
        assert call_args[1]["params"]["q"] == "test query"

    def test_reddit_search_scoped(self, tools, mock_api):
        mock_api.get.return_value = {"data": {"children": []}}
        tool = next(t for t in tools if t.name == "reddit_search")
        tool.invoke({"query": "test", "subreddit": "python"})
        call_args = mock_api.get.call_args
        assert "/r/python/search" in call_args[0][0]


class TestWriteTools:
    def test_comment_rejects_empty(self, tools):
        tool = next(t for t in tools if t.name == "reddit_comment")
        result = tool.invoke({"parent_id": "t3_abc", "text": ""})
        assert "Error" in result

    def test_vote_validates_direction(self, tools):
        tool = next(t for t in tools if t.name == "reddit_vote")
        result = tool.invoke({"thing_id": "t3_abc", "direction": 5})
        assert "Error" in result

    def test_submit_rejects_empty_title(self, tools):
        tool = next(t for t in tools if t.name == "reddit_submit")
        result = tool.invoke({"subreddit": "test", "title": "", "text": "body"})
        assert "Error" in result

    def test_message_rejects_missing_fields(self, tools):
        tool = next(t for t in tools if t.name == "reddit_message")
        result = tool.invoke({"to": "", "subject": "hi", "text": "body"})
        assert "Error" in result
