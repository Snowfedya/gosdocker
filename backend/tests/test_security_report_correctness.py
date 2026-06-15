"""Tests for Phase 06 — security report correctness.

Covers AC-1, AC-2, AC-3, AC-4.
"""
import json
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest


# ─────────────────────────────────────────────────────────────
# AC-1: Degraded mode propagated correctly
# ─────────────────────────────────────────────────────────────


def _trivy_summary_with(vulns):
    return {
        "total_vulnerabilities": len(vulns),
        "by_severity": {
            "CRITICAL": sum(1 for v in vulns if v["severity"] == "CRITICAL"),
            "HIGH": sum(1 for v in vulns if v["severity"] == "HIGH"),
            "MEDIUM": sum(1 for v in vulns if v["severity"] == "MEDIUM"),
            "LOW": sum(1 for v in vulns if v["severity"] == "LOW"),
            "UNKNOWN": sum(1 for v in vulns if v["severity"] == "UNKNOWN"),
        },
        "vulnerabilities": vulns,
    }


def test_degraded_build_produces_degraded_report(tmp_path, monkeypatch):
    """AC-1: When no artifacts produced (build degraded), status='degraded', not 'ok'."""
    from app.api.registry import _build_report_from_context
    # Empty artifacts (build skipped, no files produced)
    report = _build_report_from_context("angie-pro", "standard", {}, ["Build skipped: network unavailable"])
    assert report["degraded"] is True
    assert report["status"] == "degraded"
    assert "Build skipped" in str(report["errors"])


def test_successful_build_produces_ok_report(tmp_path):
    """AC-1: When artifacts present, status='ok', degraded=False."""
    from app.api.registry import _build_report_from_context
    trivy_path = tmp_path / "trivy.json"
    trivy_path.write_text(json.dumps(_trivy_summary_with([])))
    sbom_path = tmp_path / "sbom.json"
    sbom_path.write_text(json.dumps({"total_components": 5}))
    artifacts = {"trivy_report": str(trivy_path), "sbom": str(sbom_path)}
    report = _build_report_from_context("angie-pro", "standard", artifacts, [])
    assert report["degraded"] is False
    assert report["status"] == "ok"


def test_trivy_skipped_flag_when_no_trivy_artifact():
    """AC-1: trivy block has trivy_skipped=True (or trivy is None) when no scan ran."""
    from app.api.registry import _build_report_from_context
    report = _build_report_from_context("angie-pro", "standard", {}, ["Build skipped"])
    # When trivy artifact absent, trivy field should signal 'not scanned'
    trivy = report["trivy"]
    if trivy is not None:
        assert trivy.get("trivy_skipped") is True


# ─────────────────────────────────────────────────────────────
# AC-2: Trivy fallback to source image
# ─────────────────────────────────────────────────────────────


def test_scan_target_picks_built_image_when_present():
    """AC-2: When gosdocker/<slug>:latest exists, scan that (our artifact)."""
    from app.pipeline.scan import _scan_target_for_slug
    with patch("app.pipeline.scan._local_image_exists", return_value=True):
        target = _scan_target_for_slug("angie-pro", "dh-mirror.gitverse.ru/riftbit/angie:latest")
    assert target == "gosdocker/angie-pro:latest"


def test_scan_target_falls_back_to_source_image():
    """AC-2: When gosdocker/<slug>:latest missing, scan manifest image (fallback)."""
    from app.pipeline.scan import _scan_target_for_slug
    with patch("app.pipeline.scan._local_image_exists", return_value=False):
        target = _scan_target_for_slug("angie-pro", "dh-mirror.gitverse.ru/riftbit/angie:latest")
    assert target == "dh-mirror.gitverse.ru/riftbit/angie:latest"


def test_local_image_exists_handles_docker_error():
    """AC-2: _local_image_exists returns False on docker error, not raise."""
    from app.pipeline.scan import _local_image_exists
    with patch("app.pipeline.scan.subprocess.run",
               side_effect=FileNotFoundError("docker not found")):
        result = _local_image_exists("gosdocker/x:latest")
    assert result is False


# ─────────────────────────────────────────────────────────────
# AC-3: Cache invalidation on manifest mtime
# ─────────────────────────────────────────────────────────────


def test_cache_invalidates_when_manifest_newer(tmp_path, monkeypatch):
    """AC-3: If manifest mtime > cache mtime, return None (rebuild needed)."""
    monkeypatch.setattr("app.api.registry.REPORTS_DIR", tmp_path / "reports")
    monkeypatch.setattr("app.api.registry.REGISTRY_BASE", tmp_path / "registry")
    (tmp_path / "registry" / "angie-pro").mkdir(parents=True)
    manifest = tmp_path / "registry" / "angie-pro" / "manifest.yml"
    manifest.write_text("slug: angie-pro\n")
    (tmp_path / "reports" / "angie-pro").mkdir(parents=True)
    cache = tmp_path / "reports" / "angie-pro" / "latest.json"
    cache.write_text(json.dumps({"status": "ok"}))
    # Manifest older than cache → cache valid
    assert _load_cache("angie-pro") is not None
    # Update manifest → newer than cache → cache invalid
    time.sleep(0.05)
    manifest.write_text("slug: angie-pro\nv: 2\n")
    assert _load_cache("angie-pro") is None


def test_cache_valid_when_manifest_older(tmp_path, monkeypatch):
    """AC-3: If manifest mtime < cache mtime, cache is valid."""
    monkeypatch.setattr("app.api.registry.REPORTS_DIR", tmp_path / "reports")
    monkeypatch.setattr("app.api.registry.REGISTRY_BASE", tmp_path / "registry")
    (tmp_path / "registry" / "angie-pro").mkdir(parents=True)
    manifest = tmp_path / "registry" / "angie-pro" / "manifest.yml"
    manifest.write_text("slug: angie-pro\n")
    (tmp_path / "reports" / "angie-pro").mkdir(parents=True)
    cache = tmp_path / "reports" / "angie-pro" / "latest.json"
    cache.write_text(json.dumps({"status": "ok"}))
    assert _load_cache("angie-pro") is not None


def test_cache_loads_when_no_manifest(tmp_path, monkeypatch):
    """AC-3: If manifest missing, cache is still returned (no regression)."""
    monkeypatch.setattr("app.api.registry.REPORTS_DIR", tmp_path / "reports")
    monkeypatch.setattr("app.api.registry.REGISTRY_BASE", tmp_path / "registry")
    (tmp_path / "reports" / "angie-pro").mkdir(parents=True)
    cache = tmp_path / "reports" / "angie-pro" / "latest.json"
    cache.write_text(json.dumps({"status": "ok"}))
    # No manifest dir
    assert _load_cache("angie-pro") is not None


def _load_cache(slug: str):
    from app.api.registry import _load_report_cache
    return _load_report_cache(slug)


# ─────────────────────────────────────────────────────────────
# AC-4: Async build via BackgroundTasks
# ─────────────────────────────────────────────────────────────


def test_build_returns_202_with_job_id(monkeypatch):
    """AC-4: POST /build is async, returns 202 + job_id; does not block on pipeline."""
    from fastapi.testclient import TestClient
    from app.main import app
    from app.api import registry as registry_mod

    # AC-4: stub the heavy pipeline so the test runs in milliseconds
    monkeypatch.setattr(registry_mod, "_run_pipeline_job",
                        lambda slug, profile, job_id: None)
    client = TestClient(app)
    r = client.post("/api/registry/angie-pro/build?profile=standard")
    assert r.status_code == 202
    body = r.json()
    assert "job_id" in body
    assert body["status"] == "pending"
    assert body["slug"] == "angie-pro"


def test_jobs_endpoint_returns_status(monkeypatch):
    """AC-4: GET /jobs/<job_id> returns current job status (pending/running/ok/degraded/failed)."""
    from fastapi.testclient import TestClient
    from app.main import app
    from app.api import registry as registry_mod
    import time as _time

    monkeypatch.setattr(registry_mod, "_run_pipeline_job",
                        lambda slug, profile, job_id: None)
    client = TestClient(app)
    r = client.post("/api/registry/angie-pro/build?profile=standard")
    assert r.status_code == 202
    job_id = r.json()["job_id"]
    r2 = client.get(f"/api/registry/angie-pro/jobs/{job_id}")
    assert r2.status_code == 200
    body = r2.json()
    assert body["job_id"] == job_id
    assert body["status"] == "pending"
    assert body["slug"] == "angie-pro"
    assert body["profile"] == "standard"


def test_jobs_endpoint_404_for_unknown_job():
    """AC-4: GET /jobs/<id> returns 404 for unknown job_id."""
    from fastapi.testclient import TestClient
    from app.main import app
    client = TestClient(app)
    r = client.get("/api/registry/angie-pro/jobs/nonexistent_id")
    assert r.status_code == 404
