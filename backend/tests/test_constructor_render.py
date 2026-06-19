"""Unit tests for app.services.constructor_render.

These are pure-function helpers extracted from app/api/constructor.py
in 2026-06-19 cleanup. The point of the split is to make the
compose-service and readme rendering testable without the FastAPI
surface.
"""
from app.services.constructor_render import build_service_entry, build_readme


class TestBuildServiceEntry:
    def test_minimal_manifest_uses_defaults(self):
        # The caller unwraps manifest['component'] before calling us
        # (see app/api/constructor.py:448).
        slug = "nginx"
        manifest = {
            "name": "Nginx",
            "version": "1.27.0",
            "ports": {"http": 80},
            "default_env": {},
        }
        cfg: dict = {}
        entry = build_service_entry(slug, manifest, cfg)

        assert entry["container_name"] == "nginx"
        assert entry["build"]["context"] == "./build/nginx"
        assert entry["networks"] == ["gosdocker"]
        # Falls back to manifest ports (no user override)
        assert entry["ports"] == ["80:80"]

    def test_user_ports_override_manifest(self):
        manifest = {"ports": {"http": 80}}
        cfg = {"ports": {"8080": 80}}
        entry = build_service_entry("web", manifest, cfg)
        assert entry["ports"] == ["8080:80"]

    def test_secret_env_value_sanitized_to_placeholder(self):
        manifest = {"default_env": {"POSTGRES_PASSWORD": "real-secret"}}
        entry = build_service_entry("db", manifest, {})
        # KEY is preserved, VALUE becomes the secret placeholder so
        # docker compose resolves it from .env at runtime.
        assert entry["environment"]["POSTGRES_PASSWORD"] == "<set-me>"

    def test_user_env_overrides_default(self):
        manifest = {"default_env": {"FOO": "default"}}
        cfg = {"env": {"FOO": "user"}}
        entry = build_service_entry("svc", manifest, cfg)
        assert entry["environment"]["FOO"] == "user"


class TestBuildReadme:
    def test_includes_resolved_components(self):
        manifests = {
            "nginx": {"component": {"name": "Nginx", "version": "1.27"}},
            "pg": {"component": {"name": "Postgres", "version": "16"}},
        }
        text = build_readme(
            resolved=["nginx", "pg"],
            manifests=manifests,
            auto_added=[],
            profile="standard",
        )
        assert "**Nginx** v1.27" in text
        assert "**Postgres** v16" in text
        assert "Профиль безопасности: standard" in text

    def test_auto_added_note_appears(self):
        manifests = {
            "prom": {"component": {"name": "Prometheus", "version": "2.50"}},
        }
        auto_added = [{"slug": "prom", "reason": "grafana requires monitoring"}]
        text = build_readme(
            resolved=["prom"],
            manifests=manifests,
            auto_added=auto_added,
            profile="standard",
        )
        assert "автоматически: grafana requires monitoring" in text

    def test_fast_mode_warning(self):
        text = build_readme(
            resolved=["nginx"],
            manifests={"nginx": {"component": {"name": "N", "version": "1"}}},
            auto_added=[],
            profile="basic",
            with_owasp=False,
        )
        assert "Режим без проверки безопасности" in text
        assert "with_owasp: false" in text

    def test_security_errors_rendered(self):
        text = build_readme(
            resolved=["x"],
            manifests={"x": {"component": {"name": "X", "version": "1"}}},
            auto_added=[],
            profile="standard",
            security_errors=["missing manifest"],
        )
        assert "Предупреждения" in text
        assert "missing manifest" in text

    def test_pipeline_artifacts_listed(self):
        # Minimal duck-typed context with .artifacts dict
        class FakeCtx:
            artifacts = {
                "sbom": "/tmp/x/sbom.json",
                "trivy_report": None,
                "cosign_sig": "/tmp/x/cosign.sig",
            }
        text = build_readme(
            resolved=["svc"],
            manifests={"svc": {"component": {"name": "Svc", "version": "1"}}},
            auto_added=[],
            profile="standard",
            pipeline_results={"svc": FakeCtx()},
        )
        assert "SBOM (CycloneDX)" in text
        assert "Cosign signature" in text
        # Trivy was None — must NOT appear
        assert "Trivy scan report" not in text
