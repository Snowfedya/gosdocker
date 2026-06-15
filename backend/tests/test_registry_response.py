"""Integration tests for /api/registry/<slug> response shape.

Bug #4: ComponentView.vue references component.registry_url (line 205)
and component.image_source (line 249), but /api/registry/<slug> returns
only the YAML manifest — which has no image_source/registry_url fields.

The endpoint must MERGE DB columns (image, image_source, registry_url,
is_registry) into the response so the frontend can render them.

Run with backend live on http://localhost:8000:
    API_BASE=http://localhost:8000 pytest backend/tests/test_registry_response.py -v

Or use a fake transport to test the response shape without a live backend.
"""
import os
import pytest
import httpx


# ── pure-logic helper: merge manifest with DB row ─────────────────


def merge_registry_response(manifest: dict, db_row: dict) -> dict:
    """Merge YAML manifest with DB component row.

    DB fields win (they're authoritative for image URLs / registry state).
    Manifest contributes version, build_args, security, dependencies.
    """
    out = dict(manifest)  # shallow copy is fine — manifest has no nested dicts we mutate
    comp = dict(out.get("component", {}))
    comp["image"] = db_row.get("image", "")
    comp["image_source"] = db_row.get("image_source", "")
    comp["registry_url"] = db_row.get("registry_url", "")
    comp["is_registry"] = bool(db_row.get("is_registry", False))
    comp["registry_number"] = db_row.get("registry_number")
    out["component"] = comp
    return out


# ── tests for the merge helper (pure, no I/O) ──────────────────────


class TestMergeRegistryResponse:
    def test_db_image_overrides_missing_manifest(self):
        """Manifest has no `image`; DB row provides it."""
        manifest = {"component": {"slug": "clickhouse-redos", "version": "24.3.12.72"}}
        db_row = {
            "image": "clickhouse/clickhouse-server",
            "image_source": "dh-mirror.gitverse.ru",
            "registry_url": "dh-mirror.gitverse.ru/clickhouse/clickhouse-server:24.3",
            "is_registry": False,
            "registry_number": None,
        }
        out = merge_registry_response(manifest, db_row)
        c = out["component"]
        assert c["image"] == "clickhouse/clickhouse-server"
        assert c["image_source"] == "dh-mirror.gitverse.ru"
        assert c["registry_url"] == "dh-mirror.gitverse.ru/clickhouse/clickhouse-server:24.3"
        assert c["is_registry"] is False
        # Manifest fields preserved
        assert c["slug"] == "clickhouse-redos"
        assert c["version"] == "24.3.12.72"

    def test_db_registry_url_is_exposed_to_frontend(self):
        """Frontend (ComponentView.vue:205) needs component.registry_url."""
        manifest = {"component": {"slug": "x"}}
        db_row = {
            "image": "x",
            "image_source": "registry.red-soft.ru",
            "registry_url": "registry.red-soft.ru/ubi8/postgresql-17",
            "is_registry": True,
            "registry_number": "№12345",
        }
        out = merge_registry_response(manifest, db_row)
        assert out["component"]["registry_url"] == "registry.red-soft.ru/ubi8/postgresql-17"

    def test_manifest_only_db_row_missing_does_not_crash(self):
        """If DB row is empty (slug deleted from DB but manifest still on disk), use empty strings."""
        manifest = {"component": {"slug": "ghost"}}
        db_row = {}
        out = merge_registry_response(manifest, db_row)
        c = out["component"]
        assert c["image"] == ""
        assert c["registry_url"] == ""
        assert c["is_registry"] is False
        assert c["registry_number"] is None

    def test_is_registry_boolean_coerced(self):
        """DB stores is_registry as Boolean; ensure it's a plain bool in response."""
        manifest = {"component": {"slug": "x"}}
        db_row = {"is_registry": 1, "image": "x", "image_source": "y", "registry_url": "z"}
        out = merge_registry_response(manifest, db_row)
        assert out["component"]["is_registry"] is True


# ── live integration test (skipped if backend not reachable) ───────


@pytest.fixture
def api_base():
    return os.environ.get("API_BASE", "http://localhost:8000")


@pytest.fixture
def live_manifest(api_base):
    """Skip the integration test if backend is down."""
    try:
        r = httpx.get(f"{api_base}/api/registry/nginx", timeout=3)
        if r.status_code != 200:
            pytest.skip(f"backend not ready: {r.status_code}")
        return r.json()
    except (httpx.ConnectError, httpx.ReadTimeout):
        pytest.skip("backend not reachable on localhost:8000")


class TestLiveEndpoint:
    def test_get_registry_slug_includes_registry_url(self, live_manifest):
        """The /api/registry/<slug> response must include registry_url."""
        comp = live_manifest.get("component", {})
        assert "registry_url" in comp, \
            "BUG: /api/registry/<slug> omits registry_url — ComponentView.vue:205 can't render it"
        assert comp["registry_url"], "registry_url is empty"

    def test_get_registry_slug_includes_image_source(self, live_manifest):
        comp = live_manifest.get("component", {})
        assert "image_source" in comp, \
            "BUG: /api/registry/<slug> omits image_source — ComponentView.vue:249 can't render it"

    def test_get_registry_slug_includes_image(self, live_manifest):
        comp = live_manifest.get("component", {})
        assert "image" in comp
        assert comp["image"], "image is empty"
