"""Tests for /api/registry/{slug}/build async flow (AC-4).

The frontend's `buildComponent()` (in useApi.ts) calls
POST /api/registry/{slug}/build, gets back 202 + job_id, and is
expected to poll GET /api/registry/{slug}/jobs/{job_id} until the
job reaches ok/degraded/failed — then surface the report.

Bug #17 (16 Jun 2026, runtime-confirmed by user report):
  - POST /api/registry/angie-pro/build?profile=standard returns
    202 + {job_id: "708ee5c5027d", status: "pending"} (good).
  - GET /api/registry/angie-pro/jobs/708ee5c5027d returns 200 with
    the job entry (good — registry._JOBS is keyed by job_id).
  - But GET /api/constructor/jobs/708ee5c5027d (which the frontend
    used to poll generically) returns 404 because constructor._JOBS
    and registry._JOBS are TWO DIFFERENT DICT INSTANCES.

The contract this test enforces: **a job created via
/api/registry/{slug}/build MUST be retrievable via
/api/registry/{slug}/jobs/{job_id} until it finishes.**

We don't test the frontend's polling here — that's a separate
vitest for useApi.buildComponent (frontend/tests/useApi.test.ts
in the redesign tree; the live /opt/gosdocker/frontend/ tree has
no test directory, see VKR-Lesson-58). This test pins the BACKEND
contract the frontend depends on.
"""
import time
import uuid

import pytest
from fastapi.testclient import TestClient

from app.api import registry as rg
from app.main import app


client = TestClient(app)


def _fake_run_no_op(slug: str, profile: str, job_id: str) -> None:
    """No-op pipeline stub: leave the job as 'pending' forever.

    We don't want the real 135s pipeline in unit tests — we just
    want to assert that the job_id returned by POST /build is
    retrievable from GET /jobs/{job_id}.
    """
    return None


def test_registry_build_returns_202_with_job_id(monkeypatch):
    """AC-4 contract: POST /api/registry/{slug}/build returns 202 + job_id."""
    monkeypatch.setattr(rg, "_run_pipeline_job", _fake_run_no_op)

    resp = client.post(
        "/api/registry/angie-pro/build",
        params={"profile": "standard"},
    )
    assert resp.status_code == 202, resp.text
    body = resp.json()
    assert "job_id" in body and len(body["job_id"]) >= 8
    assert body["status"] == "pending"
    assert body["slug"] == "angie-pro"
    assert body["profile"] == "standard"


def test_registry_build_job_is_retrievable_via_get_jobs(monkeypatch):
    """AC-4 contract: the job_id returned by POST /build MUST be
    retrievable from GET /api/registry/{slug}/jobs/{job_id}.

    This is the polling endpoint the frontend hits. If the job is
    missing here, the UI shows "error: HTTP 404" after 2s of polling.
    """
    monkeypatch.setattr(rg, "_run_pipeline_job", _fake_run_no_op)

    post = client.post(
        "/api/registry/angie-pro/build",
        params={"profile": "standard"},
    )
    assert post.status_code == 202
    job_id = post.json()["job_id"]

    get = client.get(f"/api/registry/angie-pro/jobs/{job_id}")
    assert get.status_code == 200, (
        f"Frontend polls /api/registry/{{slug}}/jobs/{{job_id}} — "
        f"expected 200 (job exists), got {get.status_code} {get.text}"
    )
    body = get.json()
    assert body["job_id"] == job_id
    assert body["slug"] == "angie-pro"
    assert body["status"] == "pending"  # we left it as pending


def test_registry_build_then_poll_then_succeeds(monkeypatch):
    """AC-4 happy path: POST /build → poll → eventually ok with report.

    We monkey-patch _run_pipeline_job to flip the job to 'ok' and
    attach a tiny report dict, then assert GET /jobs/{id} surfaces it.
    """
    fake_report = {
        "slug": "angie-pro",
        "profile": "standard",
        "status": "ok",
        "degraded": False,
        "trivy_skipped": False,
        "errors": [],
        "sbom": None,
        "trivy": None,
        "owasp": None,
        "cosign": {"signed": False, "public_key": None, "signature": None},
        "security_score": None,
    }

    def fake_run(slug: str, profile: str, job_id: str) -> None:
        rg._JOBS[job_id]["status"] = "ok"
        rg._JOBS[job_id]["finished_at"] = time.time()
        rg._JOBS[job_id]["report"] = fake_report

    monkeypatch.setattr(rg, "_run_pipeline_job", fake_run)

    post = client.post(
        "/api/registry/angie-pro/build",
        params={"profile": "standard"},
    )
    job_id = post.json()["job_id"]

    # Give the BackgroundTask a tick to run (it runs after the
    # response is sent in FastAPI's test client).
    time.sleep(0.05)

    get = client.get(f"/api/registry/angie-pro/jobs/{job_id}")
    assert get.status_code == 200
    body = get.json()
    assert body["status"] == "ok"
    assert "report" in body
    assert body["report"]["slug"] == "angie-pro"
    assert body["report"]["status"] == "ok"


def test_registry_get_jobs_404_for_unknown_job_id():
    """Defensive: GET /jobs/{unknown} → 404, not 500."""
    resp = client.get("/api/registry/angie-pro/jobs/nonexistent_job_id_zzz")
    assert resp.status_code == 404


def test_registry_get_jobs_404_for_wrong_slug(monkeypatch):
    """Defensive: GET /jobs/{id} under a different slug → 404.

    Prevents a job from one component being read under another's URL.
    """
    monkeypatch.setattr(rg, "_run_pipeline_job", _fake_run_no_op)

    post = client.post(
        "/api/registry/angie-pro/build",
        params={"profile": "standard"},
    )
    job_id = post.json()["job_id"]

    # Try the same job_id under a DIFFERENT slug
    resp = client.get(f"/api/registry/nginx/jobs/{job_id}")
    assert resp.status_code == 404
