"""Verify manifest and pyproject stay in sync."""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent


def test_manifest_loads():
    """The manifest is valid YAML with required fields."""
    manifest = yaml.safe_load((ROOT / "protoagent.plugin.yaml").read_text())
    assert manifest["id"] == "reddit"
    assert manifest["version"]
    assert manifest["config_section"] == "reddit"
    assert "secrets" in manifest
    assert "views" in manifest


def test_version_matches_pyproject():
    """Manifest version == pyproject.toml version (coherence)."""
    manifest = yaml.safe_load((ROOT / "protoagent.plugin.yaml").read_text())

    import tomllib

    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text())
    assert manifest["version"] == pyproject["project"]["version"], (
        f"manifest={manifest['version']} != pyproject={pyproject['project']['version']}"
    )


def test_manifest_secrets():
    """All required secrets are declared."""
    manifest = yaml.safe_load((ROOT / "protoagent.plugin.yaml").read_text())
    secrets = manifest["secrets"]
    for key in ("reddit_client_id", "reddit_client_secret", "reddit_username", "reddit_password"):
        assert key in secrets, f"Missing secret: {key}"


def test_manifest_view_path():
    """View path matches what the router serves."""
    manifest = yaml.safe_load((ROOT / "protoagent.plugin.yaml").read_text())
    views = manifest["views"]
    assert len(views) >= 1
    assert views[0]["path"] == "/plugins/reddit/feed"
    assert not views[0]["path"].startswith("/api")


def test_manifest_config_defaults():
    """Config section has sane defaults."""
    manifest = yaml.safe_load((ROOT / "protoagent.plugin.yaml").read_text())
    cfg = manifest.get("config", {})
    assert isinstance(cfg.get("subreddits"), list)
    assert cfg.get("default_sort") in ("hot", "new", "top", "rising", "controversial")
    assert isinstance(cfg.get("posts_per_page"), int)


def test_manifest_settings_fields():
    """Settings declares UI fields for all config + secret keys."""
    manifest = yaml.safe_load((ROOT / "protoagent.plugin.yaml").read_text())
    settings = manifest.get("settings", [])
    assert len(settings) >= 8, f"Expected at least 8 settings fields, got {len(settings)}"

    keys = {s["key"] for s in settings}
    # All secrets should have settings fields
    for secret in manifest["secrets"]:
        assert secret in keys, f"Secret {secret} missing from settings"
    # Config keys should have settings fields
    for config_key in ("subreddits", "default_sort", "posts_per_page", "time_filter"):
        assert config_key in keys, f"Config key {config_key} missing from settings"


def test_manifest_settings_types():
    """Settings fields use valid types."""
    manifest = yaml.safe_load((ROOT / "protoagent.plugin.yaml").read_text())
    valid_types = {"string", "text", "number", "bool", "select", "string_list", "secret"}
    for field in manifest.get("settings", []):
        assert field["type"] in valid_types, f"Field {field['key']} has invalid type {field['type']}"


def test_manifest_required_secrets():
    """Secret settings are marked required."""
    manifest = yaml.safe_load((ROOT / "protoagent.plugin.yaml").read_text())
    for field in manifest.get("settings", []):
        if field["type"] == "secret":
            assert field.get("required") is True, f"Secret field {field['key']} should be required"
