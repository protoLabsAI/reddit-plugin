"""Reddit console view — subreddit feed reader."""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import HTMLResponse, JSONResponse

log = logging.getLogger(__name__)

VIEW_HTML = Path(__file__).parent / "view.html"


def make_routers(api, config: dict):
    """Create the page (public) and data (gated) routers."""

    page = APIRouter()
    data = APIRouter()

    @page.get("/feed")
    async def feed_page():
        """Serve the subreddit feed view HTML."""
        html = VIEW_HTML.read_text() if VIEW_HTML.exists() else "<h1>Reddit view.html not found</h1>"
        return HTMLResponse(html)

    @data.get("/config")
    async def get_config():
        """Return the plugin's configured subreddits and defaults."""
        return JSONResponse(
            {
                "subreddits": config.get("subreddits", []),
                "default_sort": config.get("default_sort", "hot"),
                "posts_per_page": config.get("posts_per_page", 25),
            }
        )

    @data.get("/feed")
    async def feed_data(
        subreddit: str = "",
        sort: str = "",
        limit: int = 0,
        after: str = "",
    ):
        """Return subreddit feed posts as JSON (paginated)."""
        if not api:
            return JSONResponse(
                {"error": "Reddit not configured — add credentials to secrets.yaml"},
                status_code=503,
            )
        sub = subreddit or "+".join(config.get("subreddits", ["all"]))
        s = sort or config.get("default_sort", "hot")
        lim = limit or config.get("posts_per_page", 25)
        params: dict = {"limit": min(lim, 100)}
        if s in ("top", "controversial"):
            params["t"] = config.get("time_filter", "day")
        if after:
            params["after"] = after
        try:
            resp = api.get(f"/r/{sub}/{s}", params=params)
            children = resp.get("data", {}).get("children", [])
            posts = []
            for child in children:
                d = child.get("data", {})
                posts.append(
                    {
                        "id": d.get("name", ""),
                        "title": d.get("title", ""),
                        "author": d.get("author", "[deleted]"),
                        "subreddit": d.get("subreddit", ""),
                        "subreddit_prefixed": d.get("subreddit_prefixed", ""),
                        "score": d.get("score", 0),
                        "num_comments": d.get("num_comments", 0),
                        "url": d.get("url", ""),
                        "permalink": f"https://reddit.com{d.get('permalink', '')}",
                        "selftext": (d.get("selftext", "") or "")[:300],
                        "created_utc": d.get("created_utc"),
                        "is_self": d.get("is_self", False),
                        "over_18": d.get("over_18", False),
                        "thumbnail": d.get("thumbnail", ""),
                        "link_flair_text": d.get("link_flair_text"),
                        "stickied": d.get("stickied", False),
                    }
                )
            return JSONResponse(
                {
                    "posts": posts,
                    "after": resp.get("data", {}).get("after"),
                    "subreddit": sub,
                    "sort": s,
                }
            )
        except Exception as e:
            log.exception("Reddit feed error")
            return JSONResponse({"error": str(e)}, status_code=502)

    return page, data
