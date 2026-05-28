"""Integration tests for GosDocker Registry Security Pipeline.

Run against a running backend container:
    API_BASE=http://localhost:8000 python3 -m pytest backend/tests/test_registry.py -v -x

Requires: pytest, httpx
"""

import os
import time
import pytest
import httpx

API_BASE = os.environ.get("API_BASE", "http://localhost:8000")
API_PREFIX = "/api"
KNOWN_SLUG = os.environ.get("TEST_SLUG", "nginx")
UNKNOWN_SLUG = "component-that-does-not-exist-12345"


# --------------- helpers ---------------

def client() -> httpx.Client:
    return httpx.Client(base_url=API_BASE, timeout=120)

def _path(suffix: str) -> str:
    """Prefix an API path with API_PREFIX."""
    return f"{API_PREFIX}{suffix}"


# --------------- fixtures ---------------

@pytest.fixture(scope="module")
def api_ready():
    """Wait for the service to be up."""
    for attempt in range(10):
        try:
            r = httpx.get(f"{API_BASE}{API_PREFIX}/categories", timeout=5)
            if r.status_code == 200:
                return True
        except httpx.ConnectError:
            pass
        time.sleep(1)
    pytest.fail(f"API at {API_BASE}{API_PREFIX} not reachable after 10s")


# --------------- health ---------------

class TestHealth:
    def test_categories_endpoint(self, api_ready):
        with client() as c:
            r = c.get(_path("/categories"))
            assert r.status_code == 200
            data = r.json()
            assert isinstance(data, list)

    def test_registry_list(self, api_ready):
        with client() as c:
            r = c.get(_path("/registry"))
            assert r.status_code == 200
            data = r.json()
            assert isinstance(data, list)
            slugs = [item["slug"] for item in data]
            assert KNOWN_SLUG in slugs, f"Expected '{KNOWN_SLUG}' in registry"


# --------------- registry manifest ---------------

class TestRegistryManifest:
    def test_manifest_known(self):
        with client() as c:
            r = c.get(_path(f"/registry/{KNOWN_SLUG}"))
            assert r.status_code == 200
            data = r.json()
            assert "component" in data
            comp = data["component"]
            assert comp["slug"] == KNOWN_SLUG
            assert "build_method" in comp
            assert "source_url" in comp
            assert "dependencies" in comp

    def test_manifest_unknown(self):
        with client() as c:
            r = c.get(_path(f"/registry/{UNKNOWN_SLUG}"))
            assert r.status_code == 404


# --------------- reports ---------------

class TestReportsEndpoint:
    def test_reports_endpoint_ok(self):
        """GET reports returns a valid report (may already be built)."""
        with client() as c:
            r = c.get(_path(f"/registry/{KNOWN_SLUG}/reports"))
            # May be 200 (cached) or 404 (not built yet) — either is valid
            assert r.status_code in (200, 404)
            if r.status_code == 200:
                data = r.json()
                assert "slug" in data
            else:
                data = r.json()
                assert "detail" in data

    def test_reports_unknown_slug(self):
        with client() as c:
            r = c.get(_path(f"/registry/{UNKNOWN_SLUG}/reports"))
            assert r.status_code == 404


# --------------- build ---------------

class TestBuildEndpoint:
    def test_build_unknown_slug(self):
        """POST to a non-existent component returns 404."""
        with client() as c:
            r = c.post(_path(f"/registry/{UNKNOWN_SLUG}/build"))
            assert r.status_code == 404

    def test_build_default_profile(self):
        """POST with default profile succeeds and returns report."""
        with client() as c:
            r = c.post(_path(f"/registry/{KNOWN_SLUG}/build?profile=standard"))
            assert r.status_code == 200
            data = r.json()
            self._assert_report_shape(data)

    def test_build_basic_profile(self):
        with client() as c:
            r = c.post(_path(f"/registry/{KNOWN_SLUG}/build?profile=basic"))
            assert r.status_code == 200
            data = r.json()
            self._assert_report_shape(data)

    def test_build_hardened_profile(self):
        with client() as c:
            r = c.post(_path(f"/registry/{KNOWN_SLUG}/build?profile=hardened"))
            assert r.status_code == 200
            data = r.json()
            self._assert_report_shape(data)

    def _assert_report_shape(self, data):
        assert "slug" in data
        assert data["slug"] == KNOWN_SLUG
        assert "status" in data
        assert data["status"] in ("ok", "error")
        assert "profile" in data
        assert "sbom" in data
        assert "trivy" in data
        assert "cosign" in data
        # SBOM shape
        if data["sbom"] is not None:
            assert "total_components" in data["sbom"]
            assert "bom_format" in data["sbom"]
        # Trivy shape
        if data["trivy"] is not None:
            assert "total_vulnerabilities" in data["trivy"]
            assert "by_severity" in data["trivy"]
        # Cosign shape
        assert "signed" in data["cosign"]


# --------------- full workflow ---------------

class TestWorkflow:
    def test_build_then_reports(self):
        """Build → GET reports returns the cached report."""
        with client() as c:
            r1 = c.post(_path(f"/registry/{KNOWN_SLUG}/build?profile=standard"))
            assert r1.status_code == 200
            build_data = r1.json()

            r2 = c.get(_path(f"/registry/{KNOWN_SLUG}/reports"))
            assert r2.status_code == 200
            report_data = r2.json()

            assert report_data["slug"] == build_data["slug"]
            assert report_data["profile"] == build_data["profile"]

    def test_build_twice_refreshes(self):
        """Second build with different profile refreshes the report."""
        with client() as c:
            r1 = c.post(_path(f"/registry/{KNOWN_SLUG}/build?profile=basic"))
            assert r1.status_code == 200
            p1 = r1.json()["profile"]

            r2 = c.post(_path(f"/registry/{KNOWN_SLUG}/build?profile=hardened"))
            assert r2.status_code == 200
            p2 = r2.json()["profile"]

            assert p1 == "basic"
            assert p2 == "hardened"

    def test_reports_after_second_build(self):
        """Reports returns the most recent build's profile."""
        with client() as c:
            c.post(_path(f"/registry/{KNOWN_SLUG}/build?profile=hardened"))
            r = c.get(_path(f"/registry/{KNOWN_SLUG}/reports"))
            assert r.status_code == 200
            assert r.json()["profile"] == "hardened"


# --------------- edge cases ---------------

class TestEdgeCases:
    def test_empty_profile_fallback(self):
        """No profile param should use default (standard)."""
        with client() as c:
            r = c.post(_path(f"/registry/{KNOWN_SLUG}/build"))
            assert r.status_code == 200

    def test_invalid_profile(self):
        """Unknown profile should not crash — returns 200 (graceful) or 400."""
        with client() as c:
            r = c.post(_path(f"/registry/{KNOWN_SLUG}/build?profile=nonexistent"))
            assert r.status_code in (200, 400, 422)
