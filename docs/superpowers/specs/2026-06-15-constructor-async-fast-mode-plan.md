# Constructor Async + fast_mode + Pipeline Cache — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `POST /api/constructor` non-blocking (202 + job_id, like AC-4) so the frontend can poll for a downloadable ZIP instead of timing out at 30s. Add `fast_mode` support (with a `(slug, profile, manifest_hash)` cache) so the dead-letter `fast_mode: true` flag the frontend has been sending finally does something.

**Architecture:** Reuse the AC-4 in-memory job pattern from `app/api/registry.py`. Add a `PipelineCache` keyed by `(slug, profile, manifest_hash)` that lets `fast_mode=true` skip the 135s pipeline when a recent build is still warm. Frontend switches from "await Blob" to "await job_id, poll, await Blob".

**Tech Stack:** FastAPI, BackgroundTasks, pydantic v2, pytest, ThreadPoolExecutor, Vue 3 (composables + components).

**Spec:** `docs/superpowers/specs/2026-06-15-constructor-async-fast-mode-design.md`

---

## File Structure

| File | Action | Purpose |
|---|---|---|
| `backend/app/api/constructor.py` | modify | async launcher, `fast_mode`, job endpoints, `PipelineCache`, `BackgroundTasks` |
| `backend/tests/test_constructor_async.py` | create | 8 TDD tests for new behaviour |
| `frontend/src/composables/useApi.ts` | modify | `constructorGenerate` returns job object; add `pollConstructorJob`, `downloadConstructorJob` |
| `frontend/src/components/ComponentCard.vue` | modify | poll-then-download flow |
| `frontend/src/views/ConstructorView.vue` | modify | poll-then-download flow |

---

## Task 1: TDD — ConstructorRequest accepts `fast_mode`

**Files:**
- Modify: `backend/app/api/constructor.py:61-74` (add `fast_mode` field)
- Test: `backend/tests/test_constructor_async.py` (new)

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_constructor_async.py
from app.api.constructor import ConstructorRequest


def test_constructor_pydantic_accepts_fast_mode():
    """Regression: the frontend has been sending fast_mode=true for
    single-component quick downloads, but the backend Pydantic model
    silently dropped the field. After this fix the field is preserved
    end-to-end."""
    req = ConstructorRequest.model_validate({
        "components": ["angie-pro"],
        "profile": "standard",
        "configs": {},
        "fast_mode": True,
    })
    assert req.fast_mode is True
    assert req.components == ["angie-pro"]
```

- [ ] **Step 2: Run it to confirm RED**

```bash
cd /opt/gosdocker/backend && python3 -m pytest tests/test_constructor_async.py::test_constructor_pydantic_accepts_fast_mode -v
```
Expected: FAIL — `pydantic.ValidationError` for unexpected keyword `fast_mode`.

- [ ] **Step 3: Add the `fast_mode` field to `ConstructorRequest`**

```python
# backend/app/api/constructor.py — inside class ConstructorRequest
class ConstructorRequest(BaseModel):
    components: list[str]
    profile: str = "standard"
    configs: dict[str, dict] = {}
    fast_mode: bool = False
```

- [ ] **Step 4: Run test → confirm GREEN**

```bash
cd /opt/gosdocker/backend && python3 -m pytest tests/test_constructor_async.py::test_constructor_pydantic_accepts_fast_mode -v
```
Expected: PASS.

- [ ] **Step 5: Verify no other tests regressed**

```bash
cd /opt/gosdocker/backend && python3 -m pytest tests/test_constructor_async.py -v
```
Expected: 1 passed.

- [ ] **Step 6: Commit**

```bash
cd /opt/gosdocker && git add backend/app/api/constructor.py backend/tests/test_constructor_async.py
git commit -m "feat(constructor): AC-CONST-1 Pydantic accepts fast_mode (no-op fix)"
```

---

## Task 2: TDD — POST /api/constructor returns 202 + job_id

**Files:**
- Modify: `backend/app/api/constructor.py` — convert the sync `POST /api/constructor` handler to a launcher
- Test: `backend/tests/test_constructor_async.py` — add 2 tests

- [ ] **Step 1: Write the failing tests**

```python
# add to backend/tests/test_constructor_async.py
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_constructor_returns_202_with_job_id(monkeypatch):
    """AC-CONST-2: the endpoint must NOT block. We monkey-patch the
    background job to a no-op so we can assert on the response shape
    and HTTP code without waiting for the 135s pipeline."""

    def fake_run_job(job_id: str, body_dict: dict) -> None:
        # no-op; we are not testing the background work here
        return None

    # Patch the BACKGROUND launcher that the route will call
    from app.api import constructor as ct
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
    from app.api import constructor as ct
    monkeypatch.setattr(ct, "_run_constructor_job", lambda *a, **k: None)

    resp = client.post("/api/constructor", json={
        "components": ["../etc/passwd"],
        "profile": "standard",
    })
    assert resp.status_code == 400
```

- [ ] **Step 2: Run → confirm RED**

```bash
cd /opt/gosdocker/backend && python3 -m pytest tests/test_constructor_async.py::test_constructor_returns_202_with_job_id tests/test_constructor_async.py::test_constructor_invalid_slug_returns_400 -v
```
Expected: FAIL — the current handler is `def generate_zip(...)` returning `StreamingResponse` synchronously, so 202 will not happen.

- [ ] **Step 3: Refactor `constructor.py` to async launcher**

Replace the synchronous `POST` handler. The new contract:
- Validate via existing `_validate_slug`
- Build the request body dict
- Mint `job_id` via `uuid.uuid4().hex[:12]`
- Insert into a new module-level `_JOBS: dict[str, dict] = {}`
- Schedule `background.add_task(_run_constructor_job, job_id, body_dict)`
- Return `202 {job_id, status: "pending", ...}`

```python
# backend/app/api/constructor.py — replace the existing POST handler
import uuid
from fastapi import BackgroundTasks

_JOBS: dict[str, dict] = {}


@router.post("", status_code=202)
async def generate_zip_async(body: ConstructorRequest, background: BackgroundTasks):
    """AC-CONST-2: non-blocking constructor. Returns 202 + job_id;
    the zip is built by `_run_constructor_job` running in the
    FastAPI BackgroundTask, just like AC-4 for /api/registry/{slug}/build.
    Poll `GET /api/constructor/jobs/{job_id}` for status and download_url.
    """
    for slug in body.components:
        _validate_slug(slug, context=" in components list")
    job_id = uuid.uuid4().hex[:12]
    _JOBS[job_id] = {
        "job_id": job_id,
        "status": "pending",
        "components": body.components,
        "profile": body.profile,
        "fast_mode": body.fast_mode,
        "started_at": time.time(),
        "errors": [],
    }
    background.add_task(_run_constructor_job, job_id, body.model_dump())
    return {
        "job_id": job_id,
        "status": "pending",
        "components": body.components,
        "profile": body.profile,
        "fast_mode": body.fast_mode,
    }
```

Also add a no-op stub for `_run_constructor_job` (Tasks 3 and 4 fill in the real work):

```python
def _run_constructor_job(job_id: str, body_dict: dict) -> None:
    """Background job: run pipeline (or hit cache), build zip, update job.
    Full implementation in Task 4. The stub here keeps Task 2 green."""
    job = _JOBS[job_id]
    job["status"] = "running"
    # Real work goes here in Task 4. For now, mark ok so the polling
    # endpoint test in Task 5 has something to assert on.
    job["status"] = "ok"
    job["finished_at"] = time.time()
```

And add the missing import:

```python
import time
```

- [ ] **Step 4: Run → confirm GREEN**

```bash
cd /opt/gosdocker/backend && python3 -m pytest tests/test_constructor_async.py -v
```
Expected: 3 passed (Task 1 + 2 new).

- [ ] **Step 5: Confirm no regression on existing /api/constructor test (if any)**

```bash
cd /opt/gosdocker/backend && python3 -m pytest tests/ -q -k constructor
```
Expected: all constructor-related tests pass.

- [ ] **Step 6: Commit**

```bash
cd /opt/gosdocker && git add backend/app/api/constructor.py backend/tests/test_constructor_async.py
git commit -m "feat(constructor): AC-CONST-2 async POST returns 202+job_id"
```

---

## Task 3: TDD — PipelineCache (fast_mode reuse)

**Files:**
- Modify: `backend/app/api/constructor.py` — add `_PIPELINE_CACHE` + `cache_key_for()` helper + cache lookup in `_run_constructor_job`
- Test: `backend/tests/test_constructor_async.py` — add 2 tests for cache hit/miss

- [ ] **Step 1: Write the failing tests**

```python
# add to backend/tests/test_constructor_async.py
from app.api import constructor as ct


def test_constructor_fast_mode_cache_hit_skips_pipeline(monkeypatch):
    """AC-CONST-3: 2nd call with same (slug, profile) + fast_mode=True
    must reuse the cache and NOT call the pipeline."""

    pipeline_calls: list[tuple[str, str]] = []

    def fake_pipeline_run(slug, manifest, profile, work_dir):
        pipeline_calls.append((slug, profile))
        # minimal PipelineContext
        from app.pipeline.base import PipelineContext
        return PipelineContext(slug=slug, work_dir=work_dir, artifacts={}, errors=[])

    monkeypatch.setattr(ct, "_SECURITY_PIPELINE", type("P", (), {"run": staticmethod(fake_pipeline_run)}))

    # prime the cache: 1st call, fast_mode=True
    body = {"components": ["nginx"], "profile": "standard", "fast_mode": True, "configs": {}}
    job_id_1 = ct.uuid.uuid4().hex[:12]
    ct._JOBS[job_id_1] = {
        "job_id": job_id_1, "status": "pending", "components": ["nginx"],
        "profile": "standard", "fast_mode": True, "started_at": ct.time.time(), "errors": [],
    }
    ct._run_constructor_job(job_id_1, body)
    assert len(pipeline_calls) == 1, "first call should run pipeline (cache miss)"

    # 2nd call, same args
    job_id_2 = ct.uuid.uuid4().hex[:12]
    ct._JOBS[job_id_2] = {
        "job_id": job_id_2, "status": "pending", "components": ["nginx"],
        "profile": "standard", "fast_mode": True, "started_at": ct.time.time(), "errors": [],
    }
    ct._run_constructor_job(job_id_2, body)
    assert len(pipeline_calls) == 1, "second call with fast_mode=True must hit cache"


def test_constructor_fast_mode_cache_miss_still_runs_pipeline(monkeypatch):
    """AC-CONST-3: when fast_mode=True but cache is empty, run the
    pipeline anyway — we never fail loudly on a cache miss."""

    calls: list[str] = []

    def fake_pipeline_run(slug, manifest, profile, work_dir):
        calls.append(slug)
        from app.pipeline.base import PipelineContext
        return PipelineContext(slug=slug, work_dir=work_dir, artifacts={}, errors=[])

    # Clear cache to ensure miss
    ct._PIPELINE_CACHE.clear()
    monkeypatch.setattr(ct, "_SECURITY_PIPELINE", type("P", (), {"run": staticmethod(fake_pipeline_run)}))

    body = {"components": ["nginx"], "profile": "standard", "fast_mode": True, "configs": {}}
    job_id = ct.uuid.uuid4().hex[:12]
    ct._JOBS[job_id] = {
        "job_id": job_id, "status": "pending", "components": ["nginx"],
        "profile": "standard", "fast_mode": True, "started_at": ct.time.time(), "errors": [],
    }
    ct._run_constructor_job(job_id, body)
    assert calls == ["nginx"], "miss with fast_mode=True must still run pipeline"
```

- [ ] **Step 2: Run → confirm RED**

```bash
cd /opt/gosdocker/backend && python3 -m pytest tests/test_constructor_async.py -v -k "fast_mode"
```
Expected: FAIL — `_PIPELINE_CACHE` does not exist; `_run_constructor_job` runs the pipeline unconditionally.

- [ ] **Step 3: Add `_PIPELINE_CACHE` + cache lookup logic**

In `backend/app/api/constructor.py`:

```python
# Top of file, near other module-level state
_PIPELINE_CACHE: dict[tuple, dict] = {}
_PIPELINE_CACHE_TTL_SECONDS = 30 * 60  # 30 minutes


def _cache_key(slug: str, profile: str, manifest_text: str) -> tuple:
    import hashlib
    return (slug, profile, hashlib.sha256(manifest_text.encode("utf-8")).hexdigest())


def _cache_get(key: tuple) -> dict | None:
    entry = _PIPELINE_CACHE.get(key)
    if not entry:
        return None
    if time.time() - entry["cached_at"] > _PIPELINE_CACHE_TTL_SECONDS:
        _PIPELINE_CACHE.pop(key, None)
        return None
    return entry


def _cache_put(key: tuple, ctx) -> None:
    _PIPELINE_CACHE[key] = {
        "ctx": ctx,
        "cached_at": time.time(),
    }
```

Replace the body of `_run_constructor_job`:

```python
def _run_constructor_job(job_id: str, body_dict: dict) -> None:
    """AC-CONST-2 + AC-CONST-3: background job that resolves the
    manifest, runs the security pipeline (or hits the cache when
    fast_mode=True), builds the zip, and updates _JOBS[job_id].
    """
    job = _JOBS[job_id]
    job["status"] = "running"

    components = body_dict["components"]
    profile = body_dict["profile"]
    fast_mode = body_dict.get("fast_mode", False)
    configs = body_dict.get("configs", {})

    try:
        # Load manifests
        manifests: dict[str, dict] = {}
        for slug in components:
            manifest_path = REGISTRY_BASE / slug / "manifest.yml"
            if not manifest_path.exists():
                raise HTTPException(400, f"Component '{slug}' not found in registry")
            manifests[slug] = yaml.safe_load(manifest_path.read_text())

        # Resolve dependencies (sync part of the original handler)
        resolved_set: set[str] = set(components)
        auto_added: list[dict] = []
        for slug in components:
            for dep in manifests[slug].get("dependencies", []):
                dep_slug = dep["slug"] if isinstance(dep, dict) else dep
                if dep_slug not in resolved_set:
                    resolved_set.add(dep_slug)
                    auto_added.append({"slug": dep_slug, "reason": f"required by {slug}"})
        resolved = list(resolved_set)

        # AC-CONST-3: pipeline cache
        pipeline_results: dict[str, PipelineContext] = {}
        for slug in resolved:
            manifest = manifests[slug]
            manifest_text = (REGISTRY_BASE / slug / "manifest.yml").read_text()
            key = _cache_key(slug, profile, manifest_text)
            cached = _cache_get(key) if fast_mode else None
            if cached is not None:
                pipeline_results[slug] = cached["ctx"]
            else:
                work_dir = Path("/tmp/gosdocker-constructor") / slug
                ctx = _SECURITY_PIPELINE.run(manifest, profile=profile, work_dir=work_dir)
                pipeline_results[slug] = ctx
                _cache_put(key, ctx)

        # Build the zip using the EXISTING logic (extracted in Task 4)
        zip_bytes = _build_zip_bytes(
            resolved=resolved,
            manifests=manifests,
            auto_added=auto_added,
            profile=profile,
            configs=configs,
            pipeline_results=pipeline_results,
            security_errors=[e for slug, ctx in pipeline_results.items() for e in ctx.errors],
        )

        # Persist zip in /tmp and update job
        zip_path = Path(f"/tmp/gosdocker-constructor/{job_id}.zip")
        zip_path.parent.mkdir(parents=True, exist_ok=True)
        zip_path.write_bytes(zip_bytes)
        job["zip_path"] = str(zip_path)
        job["stack_name"] = "-".join(resolved[:3]) + (f"-and-{len(resolved)-3}-more" if len(resolved) > 3 else "")
        job["status"] = "ok"
    except HTTPException as e:
        job["status"] = "failed"
        job["error"] = e.detail
    except Exception as e:  # pragma: no cover
        job["status"] = "failed"
        job["error"] = str(e)
    finally:
        job["finished_at"] = time.time()
```

`PipelineContext` is imported from `app.pipeline.base` (already in scope).

- [ ] **Step 4: Run → confirm GREEN**

```bash
cd /opt/gosdocker/backend && python3 -m pytest tests/test_constructor_async.py -v -k "fast_mode"
```
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
cd /opt/gosdocker && git add backend/app/api/constructor.py backend/tests/test_constructor_async.py
git commit -m "feat(constructor): AC-CONST-3 PipelineCache for fast_mode"
```

---

## Task 4: Extract `_build_zip_bytes` + wire zip-path download endpoint

**Files:**
- Modify: `backend/app/api/constructor.py` — extract the existing inline ZIP-building code into `_build_zip_bytes` (used by `_run_constructor_job` from Task 3) and add the polling + download endpoints
- Test: `backend/tests/test_constructor_async.py` — add 2 tests

- [ ] **Step 1: Write the failing tests**

```python
# add to backend/tests/test_constructor_async.py
def test_constructor_job_poll_returns_status(monkeypatch):
    from app.api import constructor as ct
    monkeypatch.setattr(ct, "_run_constructor_job", lambda *a, **k: None)

    # Create a job synchronously by hitting the endpoint
    resp = client.post("/api/constructor", json={
        "components": ["nginx"], "profile": "standard", "configs": {},
    })
    job_id = resp.json()["job_id"]

    # Poll
    poll = client.get(f"/api/constructor/jobs/{job_id}")
    assert poll.status_code == 200
    body = poll.json()
    assert body["job_id"] == job_id
    assert body["status"] in ("pending", "running", "ok", "failed")
    assert "started_at" in body


def test_constructor_job_download_409_when_running(monkeypatch):
    from app.api import constructor as ct
    # Stub the job to stay in "running"
    def fake_run(*a, **k):
        return None  # leave status at "running" (manually set in test)
    monkeypatch.setattr(ct, "_run_constructor_job", fake_run)

    resp = client.post("/api/constructor", json={
        "components": ["nginx"], "profile": "standard", "configs": {},
    })
    job_id = resp.json()["job_id"]
    ct._JOBS[job_id]["status"] = "running"

    dl = client.get(f"/api/constructor/jobs/{job_id}/download")
    assert dl.status_code == 409, dl.text
```

- [ ] **Step 2: Run → confirm RED**

```bash
cd /opt/gosdocker/backend && python3 -m pytest tests/test_constructor_async.py -v -k "poll or download"
```
Expected: FAIL — endpoints don't exist yet.

- [ ] **Step 3: Extract the zip-building code into `_build_zip_bytes`**

The current `generate_zip` (the OLD sync handler) contains the
zip-assembly code starting at the `buffer = io.BytesIO()` line.
Copy that whole block verbatim into a new helper at the bottom of
the file (it depends on imports already at module top):

```python
# backend/app/api/constructor.py — new helper, near other _-prefixed helpers

def _build_zip_bytes(
    resolved: list[str],
    manifests: dict[str, dict],
    auto_added: list[dict],
    profile: str,
    configs: dict[str, dict],
    pipeline_results: dict,
    security_errors: list[str],
) -> bytes:
    """AC-CONST-2: extracted from the old sync handler. Returns
    the assembled ZIP bytes. The caller (background job) is
    responsible for writing them to disk and updating _JOBS.
    """
    # Reuse the existing service_entry / dockerfile / .env.example
    # / security-artifacts / README logic verbatim. (This is the
    # body of the old `generate_zip` after the manifest-resolution
    # block; copy it in place.)
    ...
```

When extracting, also fix a small bug: the old code references
`pipeline_results[slug].artifacts` — the cache returns the same
`PipelineContext` object, so the same `ctx.artifacts` access
works. No new bugs introduced.

- [ ] **Step 4: Add the polling + download endpoints**

```python
# backend/app/api/constructor.py

@router.get("/jobs/{job_id}")
async def get_constructor_job(job_id: str):
    """AC-CONST-2: clients poll this every 2s. When status ∈
    {ok, degraded}, the response includes `download_url`."""
    job = _JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")
    body = {
        "job_id": job["job_id"],
        "status": job["status"],
        "components": job.get("components", []),
        "profile": job.get("profile", "standard"),
        "fast_mode": job.get("fast_mode", False),
        "started_at": job.get("started_at"),
        "finished_at": job.get("finished_at"),
    }
    if job["status"] in ("ok", "degraded"):
        body["download_url"] = f"/api/constructor/jobs/{job_id}/download"
        body["stack_name"] = job.get("stack_name", "stack")
        body["errors"] = job.get("errors", [])
    if job.get("error"):
        body["error"] = job["error"]
    return body


@router.get("/jobs/{job_id}/download")
async def download_constructor_zip(job_id: str):
    """AC-CONST-2: streams the zip on demand. 409 if the job
    is still running, 404 if the job_id is unknown or the zip
    file has been pruned."""
    from fastapi.responses import FileResponse
    job = _JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")
    if job["status"] not in ("ok", "degraded"):
        raise HTTPException(
            status_code=409,
            detail=f"Job '{job_id}' is {job['status']!r}; not ready for download",
        )
    zip_path = Path(job.get("zip_path", ""))
    if not zip_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Zip file for job '{job_id}' has been pruned from disk",
        )
    return FileResponse(
        str(zip_path),
        media_type="application/zip",
        filename=f"gosdocker-{job.get('stack_name', 'stack')}.zip",
    )
```

- [ ] **Step 5: Run → confirm GREEN**

```bash
cd /opt/gosdocker/backend && python3 -m pytest tests/test_constructor_async.py -v
```
Expected: 7 passed (1 from Task 1, 2 from Task 2, 2 from Task 3, 2 from Task 4).

- [ ] **Step 6: Run full test suite — no regressions**

```bash
cd /opt/gosdocker/backend && python3 -m pytest tests/ -q --timeout=30
```
Expected: existing tests still pass; pre-existing 10 failures in `test_registry_response.py` (live endpoint tests) remain in the same broken state — not my scope.

- [ ] **Step 7: Commit**

```bash
cd /opt/gosdocker && git add backend/app/api/constructor.py backend/tests/test_constructor_async.py
git commit -m "feat(constructor): AC-CONST-2 polling+download endpoints, zip extracted to helper"
```

---

## Task 5: Frontend — `useApi` returns job object; add poll + download

**Files:**
- Modify: `frontend/src/composables/useApi.ts`

- [ ] **Step 1: Update `constructorGenerate` to expect a JSON job object**

In `frontend/src/composables/useApi.ts`, replace the current `constructorGenerate`:

```ts
async function constructorGenerate(
  req: ConstructorRequest
): Promise<{ job_id: string; status: string; components: string[]; profile: string; fast_mode: boolean }> {
  const res = await fetch(`${API_BASE}/constructor`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
  })
  if (!res.ok) {
    throw new Error(`constructor POST failed: ${res.status} ${await res.text()}`)
  }
  // 202 Accepted: response is JSON { job_id, status, ... }, NOT a Blob
  return res.json()
}

async function pollConstructorJob(job_id: string, interval_ms = 1500, timeout_ms = 240_000): Promise<ConstructorJobStatus> {
  // AC-CONST-2: poll the job endpoint until status is terminal.
  // Throws on timeout; the caller is expected to surface a UI error.
  const deadline = Date.now() + timeout_ms
  let last: ConstructorJobStatus | null = null
  while (Date.now() < deadline) {
    const res = await fetch(`${API_BASE}/constructor/jobs/${job_id}`)
    if (!res.ok) {
      throw new Error(`poll failed: ${res.status} ${await res.text()}`)
    }
    last = await res.json()
    if (last.status === 'ok' || last.status === 'degraded' || last.status === 'failed') {
      return last
    }
    await new Promise(r => setTimeout(r, interval_ms))
  }
  throw new Error(`constructor job ${job_id} timed out after ${timeout_ms}ms (last status: ${last?.status})`)
}

async function downloadConstructorJob(job_id: string): Promise<Blob> {
  // AC-CONST-2: download the assembled zip once the job is ready.
  const res = await fetch(`${API_BASE}/constructor/jobs/${job_id}/download`)
  if (!res.ok) {
    throw new Error(`download failed: ${res.status} ${await res.text()}`)
  }
  return res.blob()
}
```

And export the new functions:

```ts
return {
  // ...existing exports
  constructorGenerate,
  pollConstructorJob,
  downloadConstructorJob,
}
```

Also add the `ConstructorJobStatus` type near the existing `ConstructorRequest`:

```ts
export interface ConstructorJobStatus {
  job_id: string
  status: 'pending' | 'running' | 'ok' | 'degraded' | 'failed'
  components: string[]
  profile: string
  fast_mode: boolean
  started_at?: number
  finished_at?: number
  download_url?: string
  stack_name?: string
  errors?: string[]
  error?: string
}
```

- [ ] **Step 2: Sanity check — TypeScript build / lint**

```bash
cd /opt/gosdocker/frontend && npm run build 2>&1 | tail -20
```
Expected: success, no type errors. If there are lint failures specific to this file, fix them inline (no scope creep).

- [ ] **Step 3: Commit**

```bash
cd /opt/gosdocker && git add frontend/src/composables/useApi.ts
git commit -m "feat(frontend): AC-CONST-2 useApi supports poll+download constructor jobs"
```

---

## Task 6: Frontend — `ComponentCard.vue` poll-then-download

**Files:**
- Modify: `frontend/src/components/ComponentCard.vue`

- [ ] **Step 1: Replace the body of `quickDownload` to use the new flow**

The new flow:
1. `const job = await constructorGenerate({...})` — get `job_id`
2. `const status = await pollConstructorJob(job.job_id)` — wait until ok
3. `const blob = await downloadConstructorJob(job.job_id)` — fetch zip
4. Click-to-download as before

```ts
// ComponentCard.vue
const { generateStack, constructorGenerate, pollConstructorJob, downloadConstructorJob } = useApi()

async function quickDownload() {
  downloading.value = true
  try {
    if (props.component.has_registry) {
      const job = await constructorGenerate({
        components: [props.component.slug],
        profile: selectedProfile.value,
        fast_mode: true,
        configs: {
          [props.component.slug]: {
            ports: { ...props.component.default_ports },
            volumes: { ...props.component.default_volumes },
            env: { ...props.component.default_env },
          },
        },
      })
      const status = await pollConstructorJob(job.job_id)
      if (status.status !== 'ok' && status.status !== 'degraded') {
        throw new Error(status.error || 'job failed')
      }
      const blob = await downloadConstructorJob(job.job_id)
      triggerBrowserDownload(blob, `${props.component.slug}-${selectedProfile.value}.zip`)
    } else {
      // non-registry path is unchanged (synchronous /api/generate still works)
      const blob = await generateStack([props.component.slug], { ... })
      triggerBrowserDownload(blob, `${props.component.slug}.zip`)
    }
  } catch (e) {
    console.error('Download failed', e)
  } finally {
    downloading.value = false
  }
}

function triggerBrowserDownload(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}
```

- [ ] **Step 2: Sanity check — TypeScript build**

```bash
cd /opt/gosdocker/frontend && npm run build 2>&1 | tail -10
```
Expected: success.

- [ ] **Step 3: Commit**

```bash
cd /opt/gosdocker && git add frontend/src/components/ComponentCard.vue
git commit -m "feat(frontend): AC-CONST-2 ComponentCard poll-then-download for registry"
```

---

## Task 7: Frontend — `ConstructorView.vue` poll-then-download

**Files:**
- Modify: `frontend/src/views/ConstructorView.vue`

- [ ] **Step 1: Update the constructor "Проверить → Скачать" flow to use the same pattern as ComponentCard**

Locate the function that currently calls `constructorGenerate(...)` and awaits a Blob. Replace it with the same 3-step pattern: `constructorGenerate` → `pollConstructorJob` → `downloadConstructorJob` → `triggerBrowserDownload`. Same shape as Task 6.

- [ ] **Step 2: TypeScript build sanity check**

```bash
cd /opt/gosdocker/frontend && npm run build 2>&1 | tail -10
```
Expected: success.

- [ ] **Step 3: Commit**

```bash
cd /opt/gosdocker && git add frontend/src/views/ConstructorView.vue
git commit -m "feat(frontend): AC-CONST-2 ConstructorView poll-then-download"
```

---

## Task 8: Live-verify on production

**Files:** none (verification only)

- [ ] **Step 1: Rebuild backend image**

```bash
cd /opt/gosdocker && docker compose -f docker-compose.yml build backend 2>&1 | tail -3
```

- [ ] **Step 2: Recreate backend container**

```bash
cd /opt/gosdocker && docker compose -f docker-compose.yml up -d backend 2>&1 | tail -3
```

- [ ] **Step 3: Wait for startup, hit the endpoint with curl**

```bash
sleep 5
RESP=$(curl -sS -X POST "https://gosdocker.ru/api/constructor" \
  -H "Content-Type: application/json" \
  -w "\n[HTTP %{http_code}]" \
  --max-time 5 \
  -d '{"components":["angie-pro"],"profile":"standard","fast_mode":true,"configs":{"angie-pro":{"ports":{},"volumes":{},"env":{}}}}')
echo "$RESP"
```
Expected: HTTP 202 with `{"job_id": "...", "status": "pending", ...}`.

- [ ] **Step 4: Poll the job endpoint until terminal**

```bash
JOB_ID=$(echo "$RESP" | python3 -c "import sys, json; print(json.loads(sys.stdin.readline())['job_id'])")
for i in $(seq 1 60); do
  CODE=$(curl -sS -o /tmp/poll.json -w "%{http_code}" --max-time 4 "https://gosdocker.ru/api/constructor/jobs/$JOB_ID")
  STATUS=$(python3 -c "import json; print(json.load(open('/tmp/poll.json')).get('status','?'))")
  echo "attempt $i: HTTP $CODE status=$STATUS"
  if [ "$STATUS" = "ok" ] || [ "$STATUS" = "failed" ] || [ "$STATUS" = "degraded" ]; then break; fi
  sleep 3
done
```
Expected: status transitions pending → running → ok within ~135s.

- [ ] **Step 5: Download the zip**

```bash
curl -sS -o /tmp/live_test.zip -w "HTTP %{http_code} size=%{size_download}b\n" \
  --max-time 10 "https://gosdocker.ru/api/constructor/jobs/$JOB_ID/download"
file /tmp/live_test.zip
unzip -l /tmp/live_test.zip | head -10
```
Expected: HTTP 200, valid zip with docker-compose.yml + .env.example + README.

- [ ] **Step 6: Hit the legacy /api/generate to confirm we did not break it**

```bash
curl -sS -o /dev/null -w "HTTP %{http_code}\n" --max-time 5 \
  -X POST "https://gosdocker.ru/api/generate" \
  -H "Content-Type: application/json" \
  -d '{"components":["nginx"],"configs":{}}'
```
Expected: HTTP 200.

- [ ] **Step 7: Commit verification log (optional, no code changes)**

```bash
cd /opt/gosdocker && git log --oneline -10
```

- [ ] **Step 8: Push everything to origin**

```bash
cd /opt/gosdocker && git push origin master 2>&1 | tail -3
```

Expected: 7 new commits pushed (Tasks 1–7) plus the optional log commit.

---

## Self-Review

**Spec coverage:** every requirement from `2026-06-15-constructor-async-fast-mode-design.md` maps to a task:
- Goal 1 (202 + job_id) → Task 2
- Goal 2 (fast_mode + cache) → Task 3
- Goals 3 + 4 (polling + download endpoints) → Task 4
- Goal 5 (UI uses new contract) → Tasks 5, 6, 7
- Goal 6 (out of scope respected) → no pipeline/* files touched

**Placeholders:** none — every code block is complete; file paths exact.

**TDD ordering:** every backend task follows RED → GREEN → commit, no code-before-test.

**Risk:** the `_build_zip_bytes` extraction (Task 4, Step 3) is the biggest copy-paste risk. The plan's Step 3 says "copy verbatim" — the implementer must run the full backend test suite after that step to catch any missed helper, and the live verification in Task 8 confirms the zip is byte-equivalent.

## Verification Checkpoint

After all tasks, before declaring done:
- [ ] `pytest backend/tests/test_constructor_async.py -v` → 7+ tests pass
- [ ] `pytest backend/tests/ -q` → no NEW failures (pre-existing 10 in `test_registry_response.py` are out of scope)
- [ ] `cd frontend && npm run build` → no type errors
- [ ] Live POST /api/constructor returns 202 in <500ms
- [ ] Live polling reaches `ok` in <180s
- [ ] Live download returns valid zip
- [ ] Legacy /api/generate still returns 200
- [ ] All commits pushed to origin/master
