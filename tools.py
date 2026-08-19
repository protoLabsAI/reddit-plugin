"""Reddit tools — 15 agent-facing tools for reading and interacting with Reddit."""

from __future__ import annotations

import json
import logging

from langchain_core.tools import tool

log = logging.getLogger(__name__)


# ── Formatters ──────────────────────────────────────────────────


def _format_post(p: dict) -> dict:
    """Extract useful fields from a Reddit post thing."""
    d = p.get("data", p)
    return {
        "id": d.get("name", d.get("id", "")),
        "title": d.get("title", ""),
        "author": d.get("author", "[deleted]"),
        "subreddit": d.get("subreddit_prefixed", f"r/{d.get('subreddit', '')}"),
        "score": d.get("score", 0),
        "upvote_ratio": d.get("upvote_ratio"),
        "num_comments": d.get("num_comments", 0),
        "url": d.get("url", ""),
        "permalink": f"https://reddit.com{d['permalink']}" if d.get("permalink") else "",
        "selftext": (d.get("selftext", "") or "")[:500],
        "created_utc": d.get("created_utc"),
        "is_self": d.get("is_self", False),
        "over_18": d.get("over_18", False),
        "thumbnail": d.get("thumbnail"),
        "link_flair_text": d.get("link_flair_text"),
    }


def _format_comment(c: dict, depth: int = 0) -> dict:
    """Extract useful fields from a Reddit comment."""
    d = c.get("data", c)
    result = {
        "id": d.get("name", d.get("id", "")),
        "author": d.get("author", "[deleted]"),
        "body": (d.get("body", "") or "")[:1000],
        "score": d.get("score", 0),
        "created_utc": d.get("created_utc"),
        "depth": depth,
        "permalink": f"https://reddit.com{d['permalink']}" if d.get("permalink") else "",
    }
    replies = d.get("replies")
    if isinstance(replies, dict):
        children = replies.get("data", {}).get("children", [])
        result["replies"] = [
            _format_comment(ch, depth + 1) for ch in children if ch.get("kind") == "t1"
        ]
    return result


# ── Tool Factory ────────────────────────────────────────────────


def make_tools(api, config: dict) -> list:
    """Create all Reddit tools bound to the given API client and config."""

    # ── Read Tools ──────────────────────────────────────────────

    @tool
    def reddit_feed(
        subreddit: str = "",
        sort: str = "",
        limit: int = 0,
        time_filter: str = "",
    ) -> str:
        """Get posts from a subreddit feed. Returns post titles, scores, authors, and links.

        Args:
            subreddit: Subreddit name without r/ prefix (e.g. 'LocalLLaMA'). Omit to use configured defaults.
            sort: Sort order — hot, new, top, rising, controversial. Omit for plugin default.
            limit: Number of posts (1-100). Omit for plugin default.
            time_filter: Time filter for top/controversial — hour, day, week, month, year, all.
        """
        try:
            sub = subreddit or "+".join(config.get("subreddits", ["all"]))
            s = sort or config.get("default_sort", "hot")
            lim = limit or config.get("posts_per_page", 25)
            params: dict = {"limit": min(lim, 100)}
            if s in ("top", "controversial"):
                params["t"] = time_filter or config.get("time_filter", "day")
            data = api.get(f"/r/{sub}/{s}", params=params)
            posts = [_format_post(p) for p in data.get("data", {}).get("children", [])]
            return json.dumps(posts, indent=2)
        except Exception as e:
            return f"Error fetching Reddit feed: {e}"

    @tool
    def reddit_post(post_id: str) -> str:
        """Get a single Reddit post with its top comments.

        Args:
            post_id: The post ID (e.g. 't3_abc123' or just 'abc123').
        """
        try:
            pid = post_id.replace("t3_", "")
            data = api.get(f"/comments/{pid}", params={"limit": 10, "depth": 3})
            result: dict = {}
            if isinstance(data, list) and len(data) >= 1:
                post_children = data[0].get("data", {}).get("children", [])
                if post_children:
                    result["post"] = _format_post(post_children[0])
            if isinstance(data, list) and len(data) >= 2:
                comments = data[1].get("data", {}).get("children", [])
                result["comments"] = [
                    _format_comment(c) for c in comments if c.get("kind") == "t1"
                ]
            return json.dumps(result, indent=2)
        except Exception as e:
            return f"Error fetching Reddit post: {e}"

    @tool
    def reddit_comments(post_id: str, sort: str = "best", limit: int = 25) -> str:
        """Get the comment tree for a Reddit post.

        Args:
            post_id: The post ID (e.g. 't3_abc123' or just 'abc123').
            sort: Comment sort — best, top, new, controversial, old, qa.
            limit: Max comments to return (1-100).
        """
        try:
            pid = post_id.replace("t3_", "")
            data = api.get(
                f"/comments/{pid}",
                params={"sort": sort, "limit": min(limit, 100), "depth": 5},
            )
            comments = []
            if isinstance(data, list) and len(data) >= 2:
                children = data[1].get("data", {}).get("children", [])
                comments = [_format_comment(c) for c in children if c.get("kind") == "t1"]
            return json.dumps(comments, indent=2)
        except Exception as e:
            return f"Error fetching comments: {e}"

    @tool
    def reddit_search(
        query: str,
        subreddit: str = "",
        sort: str = "relevance",
        time_filter: str = "all",
        limit: int = 25,
    ) -> str:
        """Search Reddit posts by keyword. Can search globally or within a specific subreddit.

        Args:
            query: Search query string.
            subreddit: Optional subreddit to search within (without r/ prefix).
            sort: Sort results by — relevance, hot, top, new, comments.
            time_filter: Time filter — hour, day, week, month, year, all.
            limit: Max results (1-100).
        """
        try:
            path = f"/r/{subreddit}/search" if subreddit else "/search"
            params = {
                "q": query,
                "sort": sort,
                "t": time_filter,
                "limit": min(limit, 100),
                "restrict_sr": "true" if subreddit else "false",
                "type": "link",
            }
            data = api.get(path, params=params)
            posts = [_format_post(p) for p in data.get("data", {}).get("children", [])]
            return json.dumps(posts, indent=2)
        except Exception as e:
            return f"Error searching Reddit: {e}"

    @tool
    def reddit_user(username: str) -> str:
        """Get a Reddit user's profile information.

        Args:
            username: Reddit username (without u/ prefix).
        """
        try:
            data = api.get(f"/user/{username}/about")
            d = data.get("data", data)
            sub = d.get("subreddit", {}) if isinstance(d.get("subreddit"), dict) else {}
            return json.dumps(
                {
                    "name": d.get("name"),
                    "link_karma": d.get("link_karma"),
                    "comment_karma": d.get("comment_karma"),
                    "created_utc": d.get("created_utc"),
                    "is_gold": d.get("is_gold"),
                    "verified": d.get("verified"),
                    "subreddit": sub.get("display_name_prefixed"),
                    "description": (sub.get("public_description", "") or "")[:500],
                },
                indent=2,
            )
        except Exception as e:
            return f"Error fetching user profile: {e}"

    @tool
    def reddit_user_posts(username: str, sort: str = "new", limit: int = 25) -> str:
        """Get a Reddit user's submission history.

        Args:
            username: Reddit username (without u/ prefix).
            sort: Sort order — hot, new, top, controversial.
            limit: Max posts (1-100).
        """
        try:
            data = api.get(
                f"/user/{username}/submitted",
                params={"sort": sort, "limit": min(limit, 100)},
            )
            posts = [_format_post(p) for p in data.get("data", {}).get("children", [])]
            return json.dumps(posts, indent=2)
        except Exception as e:
            return f"Error fetching user posts: {e}"

    @tool
    def reddit_subscriptions() -> str:
        """List the user's subscribed subreddits. Returns subreddit names, subscriber counts, and descriptions."""
        try:
            subs = []
            after = None
            for _ in range(5):  # max 5 pages
                params: dict = {"limit": 100}
                if after:
                    params["after"] = after
                data = api.get("/subreddits/mine/subscriber", params=params)
                children = data.get("data", {}).get("children", [])
                for c in children:
                    d = c.get("data", {})
                    subs.append(
                        {
                            "name": d.get("display_name"),
                            "title": d.get("title"),
                            "subscribers": d.get("subscribers"),
                            "description": (d.get("public_description", "") or "")[:200],
                            "over18": d.get("over18", False),
                        }
                    )
                after = data.get("data", {}).get("after")
                if not after:
                    break
            return json.dumps(subs, indent=2)
        except Exception as e:
            return f"Error fetching subscriptions: {e}"

    @tool
    def reddit_saved(limit: int = 25) -> str:
        """Get the user's saved posts and comments on Reddit.

        Args:
            limit: Max items to return (1-100).
        """
        try:
            username = api.auth.username
            data = api.get(f"/user/{username}/saved", params={"limit": min(limit, 100)})
            items = []
            for child in data.get("data", {}).get("children", []):
                if child.get("kind") == "t3":
                    items.append({"type": "post", **_format_post(child)})
                elif child.get("kind") == "t1":
                    items.append({"type": "comment", **_format_comment(child)})
            return json.dumps(items, indent=2)
        except Exception as e:
            return f"Error fetching saved items: {e}"

    @tool
    def reddit_inbox(filter: str = "unread", limit: int = 25) -> str:
        """Check the user's Reddit inbox messages.

        Args:
            filter: Which messages — inbox, unread, messages, sent, comments, selfreply, mentions.
            limit: Max messages (1-100).
        """
        try:
            valid = ("inbox", "unread", "messages", "sent", "comments", "selfreply", "mentions")
            endpoint = f"/message/{filter}" if filter in valid else "/message/inbox"
            data = api.get(endpoint, params={"limit": min(limit, 100)})
            messages = []
            for child in data.get("data", {}).get("children", []):
                d = child.get("data", {})
                messages.append(
                    {
                        "id": d.get("name"),
                        "author": d.get("author"),
                        "subject": d.get("subject"),
                        "body": (d.get("body", "") or "")[:500],
                        "created_utc": d.get("created_utc"),
                        "new": d.get("new", False),
                        "type": d.get("type"),
                        "context": d.get("context"),
                    }
                )
            return json.dumps(messages, indent=2)
        except Exception as e:
            return f"Error fetching inbox: {e}"

    # ── Write Tools ─────────────────────────────────────────────

    @tool
    def reddit_comment(parent_id: str, text: str) -> str:
        """Post a comment or reply on Reddit.

        Args:
            parent_id: The fullname of the thing to reply to (e.g. 't3_abc123' for a post, 't1_def456' for a comment).
            text: The comment text (markdown supported).
        """
        if not text or not text.strip():
            return "Error: comment text cannot be empty."
        try:
            api.post("/api/comment", data={"thing_id": parent_id, "text": text})
            return f"Comment posted successfully on {parent_id}."
        except Exception as e:
            return f"Error posting comment: {e}"

    @tool
    def reddit_vote(thing_id: str, direction: int = 1) -> str:
        """Upvote, downvote, or remove vote on a Reddit post or comment.

        Args:
            thing_id: The fullname of the post or comment (e.g. 't3_abc123' or 't1_def456').
            direction: 1 for upvote, -1 for downvote, 0 to remove vote.
        """
        if direction not in (1, 0, -1):
            return "Error: direction must be 1 (upvote), -1 (downvote), or 0 (remove vote)."
        try:
            api.post("/api/vote", data={"id": thing_id, "dir": str(direction)})
            labels = {1: "Upvoted", -1: "Downvoted", 0: "Vote removed on"}
            return f"{labels[direction]} {thing_id}."
        except Exception as e:
            return f"Error voting: {e}"

    @tool
    def reddit_save_item(thing_id: str, unsave: bool = False) -> str:
        """Save or unsave a Reddit post or comment to your saved list.

        Args:
            thing_id: The fullname of the post or comment (e.g. 't3_abc123').
            unsave: If true, unsave the item instead.
        """
        try:
            endpoint = "/api/unsave" if unsave else "/api/save"
            api.post(endpoint, data={"id": thing_id})
            action = "Unsaved" if unsave else "Saved"
            return f"{action} {thing_id}."
        except Exception as e:
            return f"Error saving item: {e}"

    @tool
    def reddit_subscribe(subreddit: str, unsubscribe: bool = False) -> str:
        """Subscribe or unsubscribe from a subreddit.

        Args:
            subreddit: Subreddit name without r/ prefix.
            unsubscribe: If true, unsubscribe instead.
        """
        try:
            action = "unsub" if unsubscribe else "sub"
            api.post("/api/subscribe", data={"action": action, "sr_name": subreddit})
            verb = "Unsubscribed from" if unsubscribe else "Subscribed to"
            return f"{verb} r/{subreddit}."
        except Exception as e:
            return f"Error managing subscription: {e}"

    @tool
    def reddit_submit(
        subreddit: str,
        title: str,
        text: str = "",
        url: str = "",
        kind: str = "self",
    ) -> str:
        """Submit a new post to a subreddit.

        Args:
            subreddit: Subreddit name without r/ prefix.
            title: Post title.
            text: Post body text (for self/text posts, markdown supported).
            url: URL (for link posts).
            kind: Post type — 'self' for text post, 'link' for link post.
        """
        if not title or not title.strip():
            return "Error: post title cannot be empty."
        if kind == "self" and not text.strip():
            return "Error: text post body cannot be empty."
        if kind == "link" and not url.strip():
            return "Error: link post URL cannot be empty."
        try:
            post_data: dict = {
                "sr": subreddit,
                "kind": kind,
                "title": title,
                "resubmit": "true",
            }
            if kind == "self":
                post_data["text"] = text
            else:
                post_data["url"] = url
            api.post("/api/submit", data=post_data)
            return f"Post submitted to r/{subreddit}."
        except Exception as e:
            return f"Error submitting post: {e}"

    @tool
    def reddit_message(to: str, subject: str, text: str) -> str:
        """Send a private message to a Reddit user.

        Args:
            to: Reddit username to send to (without u/ prefix).
            subject: Message subject line.
            text: Message body (markdown supported).
        """
        if not to or not subject or not text:
            return "Error: recipient, subject, and message text are all required."
        try:
            api.post("/api/compose", data={"to": to, "subject": subject, "text": text})
            return f"Message sent to u/{to}."
        except Exception as e:
            return f"Error sending message: {e}"

    return [
        reddit_feed,
        reddit_post,
        reddit_comments,
        reddit_search,
        reddit_user,
        reddit_user_posts,
        reddit_subscriptions,
        reddit_saved,
        reddit_inbox,
        reddit_comment,
        reddit_vote,
        reddit_save_item,
        reddit_subscribe,
        reddit_submit,
        reddit_message,
    ]
