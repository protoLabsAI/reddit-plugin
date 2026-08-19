"""reddit — a protoAgent plugin (scaffolded by plugin-devkit)."""

from __future__ import annotations

from langchain_core.tools import tool


def register(registry):
    """Wire this plugin's contributions into the agent (ADR 0018)."""

    @tool
    def reddit_hello(name: str = "world") -> str:
        """Say hello — replace with your tool's real work."""
        return f"hello, {name}, from reddit"
    registry.register_tool(reddit_hello)

    from fastapi import APIRouter
    from fastapi.responses import HTMLResponse, JSONResponse
    router = APIRouter()

    @router.get("/view")
    async def _view():
        # Four rules (ADR 0026/0038): serve the declared path · gate DATA (not the page)
        # · slug-aware base · link the DS kit (CSS + JS). Untrusted/generated HTML → nest
        # it in an <iframe sandbox="allow-scripts"> with NO same-origin.
        return HTMLResponse(
            "<!doctype html><html><head><meta charset='utf-8'>"
            # Slug-aware base: "" on the host, "/agents/<slug>" through the fleet proxy.
            "<script>window.__base=location.pathname.split('/plugins/')[0];"
            "var l=document.createElement('link');l.rel='stylesheet';"
            "l.href=window.__base+'/_ds/plugin-kit.css';document.head.appendChild(l);</script>"
            "<style>body{margin:0;padding:32px;background:var(--pl-color-bg);"
            "color:var(--pl-color-fg);font-family:var(--pl-font-sans,system-ui)}</style>"
            "</head><body><h1>reddit</h1><p id='out'>Loading…</p>"
            # plugin-kit.js is an ES module — a dynamic import() carries the slug-aware base.
            # initPluginView() runs the token/theme handshake; apiFetch() is slug-aware AND
            # attaches the bearer, so gated /api/plugins/reddit/* data loads under a token gate.
            "<script type='module'>"
            "const kit=await import(window.__base+'/_ds/plugin-kit.js');"
            "kit.initPluginView();"
            "const r=await kit.apiFetch('/api/plugins/reddit/hello');"
            "document.getElementById('out').textContent=(await r.json()).message;"
            "</script></body></html>"
        )
    # Two-router pattern (ADR 0026): the PAGE is PUBLIC (an iframe page-load can't carry a
    # bearer), so it mounts under /plugins/reddit; its DATA is gated under /api/plugins/reddit,
    # which the operator bearer protects and kit.apiFetch() authenticates.
    registry.register_router(router, prefix="/plugins/reddit")

    data = APIRouter()

    @data.get("/hello")
    async def _hello():
        return JSONResponse({"message": "Hello from reddit!"})
    registry.register_router(data, prefix="/api/plugins/reddit")

    # Event bus (ADR 0039) — coordinate without importing other plugins:
    #   registry.emit("did_something", {"id": 1})   # → "reddit.did_something" on the bus
    #   registry.on("other-plugin.*", lambda evt: ...) # react to anyone's events
