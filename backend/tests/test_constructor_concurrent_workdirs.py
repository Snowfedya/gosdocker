"""Regression test: concurrent /api/constructor jobs must NOT share a work_dir.

Bug: when two POST /api/constructor requests fire in parallel with
overlapping components (e.g. both include 'redis'), each job's pipeline
runs against the SAME on-disk directory
(`/tmp/gosdocker-constructor/{slug}/`). With two jobs that means two
parallel BuildStep / ScanStep / SignStep processes race to write
`redis.tar`, `redis-cosign.sig`, `redis-trivy.json`, etc. into the
same path. The second writer's `docker run` may read half-written
artifacts from the first, or the `cosign sign-blob` call may fail
because the tar is being rewritten under it. Empirically the second
job hangs for >3 minutes and never reaches `status="ok"`.

This test pins the contract: each job_id must be assigned a unique
work_dir, and `_run_constructor_job` must pass that work_dir down to
the pipeline. The check is structural (paths differ) and runtime
(two jobs both reach `ok` within 30s of stubbed pipeline).
"""
import time
import threading
import uuid

import pytest
from fastapi.testclient import TestClient

from app.api import constructor as ct
from app.main import app


client = TestClient(app)


def _stub_pipeline_with_workdir_capture(captured):
    """Replace _SECURITY_PIPELINE.run with a no-op stub that records
    the work_dir it was called with. Sleeps 100ms so two parallel jobs
    actually overlap."""

    class _StubCtx:
        def __init__(self, work_dir):
            self.work_dir = work_dir
            self.artifacts = {}
            self.errors = []
        def log(self, *a, **kw):
            pass

    def _stub_run(manifest, profile="standard", work_dir=None):
        captured.append(("pipeline.run", str(work_dir), manifest.get("component", {}).get("slug")))
        time.sleep(0.1)  # force overlap window
        return _StubCtx(work_dir)

    return _stub_run


def test_concurrent_jobs_get_distinct_work_dirs(monkeypatch):
    """Two simultaneous jobs that share component 'redis' must each
    receive a work_dir that does NOT collide with the other's. The
    bug was a fixed `/tmp/gosdocker-constructor/{slug}/` path shared
    by every job touching the same slug."""

    captured = []

    monkeypatch.setattr(
        ct._SECURITY_PIPELINE, "run", _stub_pipeline_with_workdir_capture(captured)
    )

    # Two distinct job_ids, each with the same single component.
    # We call _run_constructor_job directly (not through HTTP) so we
    # can synchronise on completion via a thread + Event.
    results = {}
    barrier = threading.Barrier(2)

    def _runner(job_id, body):
        barrier.wait()  # ensure both threads enter _run_constructor_job
        try:
            ct._run_constructor_job(job_id, body)
        finally:
            results[job_id] = ct._JOBS[job_id].copy()

    body = {"components": ["redis"], "profile": "standard",
            "fast_mode": True, "configs": {}}
    job_ids = [uuid.uuid4().hex[:12] for _ in range(2)]
    for jid in job_ids:
        ct._JOBS[jid] = {
            "job_id": jid, "status": "pending", "components": ["redis"],
            "profile": "standard", "fast_mode": True,
            "started_at": time.time(), "errors": [],
        }

    threads = [threading.Thread(target=_runner, args=(jid, body)) for jid in job_ids]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10)

    # Both jobs must have reached a terminal state, not stuck in "running".
    for jid in job_ids:
        assert jid in results, f"job {jid} never returned from _run_constructor_job"
        status = results[jid].get("status")
        assert status == "ok", (
            f"job {jid} status={status!r}; expected 'ok'. "
            f"Concurrent work_dir collision likely caused a deadlock."
        )

    # The structural fix: each job_id must map to its own work_dir,
    # so the two pipelines' on-disk paths must differ.
    seen = [(args[1], args[2]) for args in captured if args[0] == "pipeline.run"]
    assert len(seen) == 2, f"expected 2 pipeline.run calls, got {captured!r}"
    paths = [s[0] for s in seen]
    assert paths[0] != paths[1], (
        f"Both jobs shared the same work_dir {paths[0]!r}. "
        f"This is the root cause of the concurrent-download deadlock."
    )

    # Each captured work_dir must reference *some* job_id, not just the
    # slug. The two threads' pipeline.run order is not deterministic, so
    # check membership rather than positional correspondence.
    for path in paths:
        assert any(jid in path for jid in job_ids), (
            f"work_dir {path!r} does not reference any known job_id "
            f"({job_ids!r}). A concurrent job on the same slug would "
            f"still share /tmp/gosdocker-constructor/{{slug}}/."
        )
