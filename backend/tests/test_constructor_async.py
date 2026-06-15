"""Tests for /api/constructor async + fast_mode + pipeline cache (AC-CONST-2/3).

Covers:
  AC-CONST-1: ConstructorRequest accepts fast_mode (regression — was dead-letter).
  AC-CONST-2: POST /api/constructor returns 202 + job_id (non-blocking).
  AC-CONST-3: PipelineCache: fast_mode=True on a warm (slug, profile) skips pipeline.
  AC-CONST-2: GET /api/constructor/jobs/{job_id} returns status + download_url.
  AC-CONST-2: GET /api/constructor/jobs/{job_id}/download returns 409 while running.
"""
import time
import uuid

import pytest
from fastapi.testclient import TestClient

from app.api import constructor as ct
from app.main import app
from app.pipeline.base import PipelineContext


# Module-level TestClient so tests can use it without depending on a
# pytest fixture (some tests only need monkeypatch). Mirrors the
# pattern in tests/test_constructor_port_conflict.py which uses a
# fixture, but kept inline so the suite runs in any order.
client = TestClient(app)


# ── AC-CONST-1: Pydantic accepts fast_mode (regression for dead-letter field) ──


def test_constructor_pydantic_accepts_fast_mode():
    """Regression: the frontend has been sending fast_mode=true for
    single-component quick downloads, but the backend Pydantic model
    must accept the field (was a no-op drop before; see spec)."""
    from app.api.constructor import ConstructorRequest

    req = ConstructorRequest.model_validate({
        "components": ["angie-pro"],
        "profile": "standard",
        "configs": {},
        "fast_mode": True,
    })
    assert req.fast_mode is True
    assert req.components == ["angie-pro"]


# ── AC-CONST-2: POST /api/constructor returns 202 + job_id (non-blocking) ──


def test_constructor_returns_202_with_job_id(monkeypatch):
    """AC-CONST-2: endpoint must NOT block. We monkey-patch the
    background job to a no-op so we can assert on the response shape
    and HTTP code without waiting for the 135s pipeline."""

    def fake_run_job(job_id: str, body_dict: dict) -> None:
        return None  # no-op; do not advance status

    monkeypatch.setattr(ct, "_run_constructor_job", fake_run_job)

    resp = client.post("/api/constructor", json={
        "components": ["nginx"],
        "profile": "standard",
        "configs": {},
    })
    assert resp.status_code == 202, resp.text
    body = resp.json()
    assert "job_id" in body and len(body["job_id"]) >= 8
    assert body["status"] == "pending"
    assert body["components"] == ["nginx"]


def test_constructor_invalid_slug_returns_400(monkeypatch):
    """Pre-existing validation: bad slug → 400, not 202."""
    monkeypatch.setattr(ct, "_run_constructor_job", lambda *a, **k: None)

    resp = client.post("/api/constructor", json={
        "components": ["../etc/passwd"],
        "profile": "standard",
    })
    assert resp.status_code == 400


# ── AC-CONST-3: PipelineCache for fast_mode reuse ──


def test_constructor_fast_mode_cache_hit_skips_pipeline(monkeypatch):
    """AC-CONST-3: 2nd call with same (slug, profile) + fast_mode=True
    must reuse the cache and NOT call the pipeline a 2nd time."""
    pipeline_calls: list[str] = []

    def fake_pipeline_run(manifest, profile, work_dir):
        pipeline_calls.append(work_dir.name)  # work_dir is /tmp/.../<slug>
        return PipelineContext(manifest=manifest, profile=profile, work_dir=work_dir)

    class _StubPipeline:
        @staticmethod
        def run(manifest, profile, work_dir):
            return fake_pipeline_run(manifest, profile, work_dir)

    monkeypatch.setattr(ct, "_SECURITY_PIPELINE", _StubPipeline)
    ct._PIPELINE_CACHE.clear()

    body = {"components": ["nginx"], "profile": "standard", "fast_mode": True, "configs": {}}

    # 1st call: cache miss → run pipeline
    job_id_1 = uuid.uuid4().hex[:12]
    ct._JOBS[job_id_1] = {
        "job_id": job_id_1, "status": "pending", "components": ["nginx"],
        "profile": "standard", "fast_mode": True, "started_at": time.time(), "errors": [],
    }
    ct._run_constructor_job(job_id_1, body)
    assert len(pipeline_calls) == 1, "first call should run pipeline (cache miss)"

    # 2nd call: cache hit → skip pipeline
    job_id_2 = uuid.uuid4().hex[:12]
    ct._JOBS[job_id_2] = {
        "job_id": job_id_2, "status": "pending", "components": ["nginx"],
        "profile": "standard", "fast_mode": True, "started_at": time.time(), "errors": [],
    }
    ct._run_constructor_job(job_id_2, body)
    assert len(pipeline_calls) == 1, "second call with fast_mode=True must hit cache"


def test_constructor_fast_mode_cache_miss_still_runs_pipeline(monkeypatch):
    """AC-CONST-3: when fast_mode=True but cache is empty, run the
    pipeline anyway — we never fail loudly on a cache miss."""
    calls: list[str] = []

    class _StubPipeline:
        @staticmethod
        def run(manifest, profile, work_dir):
            calls.append(work_dir.name)
            return PipelineContext(manifest=manifest, profile=profile, work_dir=work_dir)

    ct._PIPELINE_CACHE.clear()
    monkeypatch.setattr(ct, "_SECURITY_PIPELINE", _StubPipeline)

    body = {"components": ["nginx"], "profile": "standard", "fast_mode": True, "configs": {}}
    job_id = uuid.uuid4().hex[:12]
    ct._JOBS[job_id] = {
        "job_id": job_id, "status": "pending", "components": ["nginx"],
        "profile": "standard", "fast_mode": True, "started_at": time.time(), "errors": [],
    }
    ct._run_constructor_job(job_id, body)
    assert calls == ["nginx"], "miss with fast_mode=True must still run pipeline"


# ── AC-CONST-2: Polling + download endpoints ──


def test_constructor_job_poll_returns_status(monkeypatch):
    monkeypatch.setattr(ct, "_run_constructor_job", lambda *a, **k: None)

    resp = client.post("/api/constructor", json={
        "components": ["nginx"], "profile": "standard", "configs": {},
    })
    job_id = resp.json()["job_id"]

    poll = client.get(f"/api/constructor/jobs/{job_id}")
    assert poll.status_code == 200
    body = poll.json()
    assert body["job_id"] == job_id
    assert body["status"] in ("pending", "running", "ok", "failed")
    assert "started_at" in body


def test_constructor_job_download_409_when_running(monkeypatch):
    monkeypatch.setattr(ct, "_run_constructor_job", lambda *a, **k: None)

    resp = client.post("/api/constructor", json={
        "components": ["nginx"], "profile": "standard", "configs": {},
    })
    job_id = resp.json()["job_id"]
    # Force the job into 'running' (the stubbed launcher does nothing).
    ct._JOBS[job_id]["status"] = "running"

    dl = client.get(f"/api/constructor/jobs/{job_id}/download")
    assert dl.status_code == 409, dl.text


def test_constructor_job_unknown_returns_404(monkeypatch):
    monkeypatch.setattr(ct, "_run_constructor_job", lambda *a, **k: None)
    resp = client.get("/api/constructor/jobs/nonexistent-id")
    assert resp.status_code == 404
