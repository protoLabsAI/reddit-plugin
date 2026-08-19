"""Integration test — load the plugin via the testkit, verify register() works."""

from __future__ import annotations


def test_plugin_loads(plugin):
    """The plugin loads as a package without errors."""
    assert plugin is not None
    assert hasattr(plugin, "register")


def test_register_succeeds(plugin, registry):
    """register() completes without raising (no secrets → tools skipped, view + skill registered)."""
    plugin.register(registry)


def test_view_routers_registered(plugin, registry):
    """register() registers both page and data routers."""
    plugin.register(registry)
    # FakeRegistry stores routers as (prefix, router) tuples
    assert len(registry.routers) >= 2
    prefixes = [prefix for prefix, _router in registry.routers]
    assert "/plugins/reddit" in prefixes
    assert "/api/plugins/reddit" in prefixes


def test_skill_dir_registered(plugin, registry):
    """register() registers the skills directory."""
    plugin.register(registry)
    assert len(registry.skill_dirs) >= 1


def test_no_tools_without_secrets(plugin, registry):
    """Without secrets, no tools are registered (graceful degradation)."""
    plugin.register(registry)
    # The FakeRegistry's host is None → no secrets → no tools
    assert len(registry.tools) == 0


def test_module_imports():
    """Key modules are importable host-free."""
    import importlib
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    auth = importlib.import_module("auth")
    api = importlib.import_module("api")
    tools = importlib.import_module("tools")
    view = importlib.import_module("view")
    assert hasattr(auth, "RedditAuth")
    assert hasattr(api, "RedditAPI")
    assert hasattr(tools, "make_tools")
    assert hasattr(view, "make_routers")
