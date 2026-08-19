"""reddit — Reddit integration for protoAgent."""

from __future__ import annotations

import logging

log = logging.getLogger(__name__)


def register(registry):
    """Wire Reddit tools, view, and skill into the agent."""

    # ── Config + secrets ────────────────────────────────────────
    cfg = registry.config or {}
    secrets: dict = {}
    try:
        host_cfg = registry.host.config()
        secrets = host_cfg.get("secrets", {})
    except Exception:
        pass

    client_id = secrets.get("reddit_client_id", "")
    client_secret = secrets.get("reddit_client_secret", "")
    username = secrets.get("reddit_username", "")
    password = secrets.get("reddit_password", "")

    # ── Auth + API client (lazy — constructed only when secrets present) ──
    api = None
    if all([client_id, client_secret, username, password]):
        try:
            from .auth import RedditAuth
            from .api import RedditAPI

            auth = RedditAuth(client_id, client_secret, username, password)
            api = RedditAPI(auth)
            log.info("Reddit API client initialized for u/%s", username)
        except Exception:
            log.exception("Failed to initialize Reddit API client")

    # ── Tools (only if API is available) ────────────────────────
    if api:
        try:
            from .tools import make_tools

            tools = make_tools(api, cfg)
            registry.register_tools(tools)
            log.info("Registered %d Reddit tools", len(tools))
        except Exception:
            log.exception("Failed to register Reddit tools")
    else:
        log.warning(
            "Reddit plugin: no credentials configured — tools disabled. "
            "Set reddit_client_id, reddit_client_secret, reddit_username, "
            "reddit_password in secrets.yaml."
        )

    # ── Console view ────────────────────────────────────────────
    try:
        from .view import make_routers

        page_router, data_router = make_routers(api, cfg)
        registry.register_router(page_router, prefix="/plugins/reddit")
        registry.register_router(data_router, prefix="/api/plugins/reddit")
    except Exception:
        log.exception("Failed to register Reddit view routers")

    # ── Skill directory ─────────────────────────────────────────
    try:
        registry.register_skill_dir("skills")
    except Exception:
        log.exception("Failed to register Reddit skills")
