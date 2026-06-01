"""Unit tests for the DependencyResolver.

These tests are fast — no API calls, no Docker — just pure logic.
Run with: python3 -m pytest backend/tests/test_dependency_resolver.py -v
"""
import pytest
from app.services.dependency_resolver import DependencyResolver


# ── fixtures ──────────────────────────────────────────────────

@pytest.fixture
def resolver():
    """Standard resolver with known graph."""
    return DependencyResolver()


@pytest.fixture
def empty_resolver():
    """Resolver with no dependencies defined."""
    return DependencyResolver(
        graph={},
        providers={},
        preferred={},
    )


# ── basic resolution ──────────────────────────────────────────

class TestBasicResolution:
    def test_empty_selection(self, resolver):
        assert resolver.resolve([]) == []

    def test_single_no_deps(self, resolver):
        result = resolver.resolve(["nginx"])
        assert "nginx" in result
        assert len(result) == 1

    def test_single_with_dep(self, resolver):
        """nextcloud requires database → adds postgresql."""
        result = resolver.resolve(["nextcloud"])
        assert "nextcloud" in result
        assert "postgresql" in result


# ── dependency auto-add ───────────────────────────────────────

class TestDependencyAutoAdd:
    def test_grafana_requires_both(self, resolver):
        """grafana needs monitoring + database → adds prometheus + postgresql."""
        result = resolver.resolve(["grafana"])
        assert "grafana" in result
        assert "prometheus" in result
        assert "postgresql" in result
        assert len(result) == 3

    def test_dependency_already_satisfied(self, resolver):
        """postgresql already selected → no redundant add."""
        result = resolver.resolve(["nextcloud", "postgresql"])
        assert "nextcloud" in result
        assert "postgresql" in result
        assert len(result) == 2

    def test_multiple_components_same_dep(self, resolver):
        """both nextcloud and grafana need database → only one postgresql added."""
        result = resolver.resolve(["nextcloud", "grafana"])
        assert "nextcloud" in result
        assert "grafana" in result
        assert "postgresql" in result
        assert "prometheus" in result
        # Assert each slug appears at most once
        for slug in result:
            assert result.count(slug) == 1


# ── alternative providers ─────────────────────────────────────

class TestAlternativeProviders:
    def test_preferred_provider(self, resolver):
        """database uses preferred provider 'postgresql', not 'postgresql-redos'."""
        result = resolver.resolve(["nextcloud"])
        assert "postgresql" in result
        assert "postgresql-redos" not in result

    def test_fallback_when_preferred_unavailable(self):
        """If preferred provider is removed from providers, fallback to first available."""
        r = DependencyResolver(
            graph={"app": {"database"}},
            providers={"database": {"postgresql-redos"}},
            preferred={"database": "postgresql"},  # postgresql not in available — fallback
        )
        result = r.resolve(["app"])
        assert "postgresql-redos" in result

    def test_no_provider_available(self):
        """Component needs a dependency type with zero providers → no crash, returns component alone."""
        r = DependencyResolver(
            graph={"app": {"missing-type"}},
            providers={},
            preferred={},
        )
        result = r.resolve(["app"])
        assert "app" in result
        # No providers to add — no crash


# ── resolve_with_metadata ─────────────────────────────────────

class TestResolveWithMetadata:
    def test_auto_added_tracking(self, resolver):
        resolved, auto_added = resolver.resolve_with_metadata(["nextcloud"])
        assert "nextcloud" in resolved
        assert len(auto_added) == 1
        assert auto_added[0]["slug"] == "postgresql"
        assert "required by nextcloud" in auto_added[0]["reason"]
        assert auto_added[0]["provides"] == "database"

    def test_no_auto_added(self, resolver):
        resolved, auto_added = resolver.resolve_with_metadata(["nginx"])
        assert len(auto_added) == 0
        assert resolved == ["nginx"]


# ── edge cases ────────────────────────────────────────────────

class TestEdgeCases:
    def test_unknown_slug(self, resolver):
        """Unknown slug (not in graph) → added as-is with no deps."""
        result = resolver.resolve(["unknown-component"])
        assert "unknown-component" in result

    def test_duplicate_slugs(self, resolver):
        """Duplicate input slugs → deduplicated."""
        result = resolver.resolve(["nginx", "nginx", "nginx"])
        assert result.count("nginx") == 1

    def test_all_components_together(self, resolver):
        """All known components at once → no conflicts."""
        all_slugs = [
            "nextcloud", "grafana",
            "postgresql", "postgresql-redos",
            "nginx", "angie-pro", "prometheus",
        ]
        result = resolver.resolve(all_slugs)
        for slug in all_slugs:
            assert slug in result
