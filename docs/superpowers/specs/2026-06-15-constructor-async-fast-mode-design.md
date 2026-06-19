# Constructor Async + fast_mode + Pipeline Cache — Design

## Context

`POST /api/constructor` in `backend/app/api/constructor.py` is a
synchronous endpoint that runs the full security pipeline
(BuildStep → ScanStep → DependencyCheckStep → PackageStep →
SignStep → RegisterStep) for every component in the user's stack
_before_ assembling the ZIP. For a single registry component like
`angie-pro` the pipeline takes ~135s. The UI sends a 30s fetch
timeout; the browser kills the request and the user sees no
archive. nginx's default 60s `proxy_read_timeout` would help
marginally but the UI UX is still broken: the button spins, the
network tab times out, the user does not know whether to retry.

A second dead-letter bug: the frontend `useApi.constructorGenerate`
sends `fast_mode: true` (ComponentCard.vue:24, useApi.ts:96) for
quick downloads of single registry components, but the backend
Pydantic model `ConstructorRequest` does not declare the field
(`grep -rn "fast_mode" backend/app/` returns 0 matches). The flag
is ignored — the pipeline always runs.

This is the same family of UX bug that `AC-4` already solved for
`POST /api/registry/{slug}/build`: 202 + job_id + polling. We
re-use that pattern.

## Goals

1. `POST /api/constructor` returns **HTTP 202** + `job_id` in
   <100ms, pipeline runs in background.
2. `fast_mode: true` skips the security pipeline when the same
   `(slug, profile, manifest_hash)` triple was built within the
   last 30 minutes (cache hit) OR — for the legacy case where the
   user just wants a compose skeleton — skips pipeline entirely.
3. `GET /api/constructor/jobs/{job_id}` returns status +
   `download_url` when the zip is ready.
4. `GET /api/constructor/jobs/{job_id}/download` streams the
   generated zip on demand.
5. UI polls the job endpoint, sees `status: "ok"` + `download_url`,
   triggers the browser download automatically — no change to
   `ComponentCard.vue` flow beyond the function signature.
6. Pre-existing 502 / pipeline bugs are **out of scope**;
   we do not touch the `pipeline/` modules or the security
   `RunLoop`.

## Non-Goals

- Async retry of a failed pipeline run.
- Persistence of jobs across backend restarts (the AC-4 prototype
  uses an in-memory dict; we keep that for the constructor too and
  add a TODO for Redis later, matching AC-4's comment).
- A "true" streaming ZIP build (we still buffer to memory; the
  pipeline work is the bottleneck, not zip I/O).
- Per-component security scoring. The constructor currently does
  not surface a score; this design does not add one. (AC-5 from
  Phase 06 already covers per-report scoring for `/reports`.)

## Approach

Re-use the AC-4 job pattern from `app/api/registry.py`:

1. Move the synchronous `POST /api/constructor` handler into a
   background-task launcher that:
   - Validates the request
   - Resolves dependencies
   - Creates `_JOBS[job_id]` (status: pending)
   - Returns `202 { job_id, status: "pending" }` immediately
   - Schedules `_run_constructor_job` via `BackgroundTasks`

2. Add a `PipelineCache` keyed by
   `(slug, profile, sha256(manifest_yaml))`:
   - First miss: run the pipeline, persist the resulting
     `PipelineContext.artifacts` paths and pipeline result status
   - Subsequent hits within 30 min: re-use the existing
     artifacts and skip the pipeline entirely
   - Cache lives in memory in a new dict
     `_PIPELINE_CACHE: dict[tuple, CacheEntry]` plus a
     sidecar manifest at
     `/tmp/gosdocker-pipeline-cache/index.json` for visibility

3. Add `fast_mode: bool = False` to `ConstructorRequest`:
   - `fast_mode=False` (default, current behaviour): always
     run pipeline
   - `fast_mode=True`: skip pipeline, use cache if hit; on miss
     run pipeline anyway (so users always get a complete zip)
   - The single-component "quick download" path in
     `ComponentCard.vue` already sends `fast_mode: true`; the
     backend will now honour it.

4. Add two endpoints:
   - `GET /api/constructor/jobs/{job_id}` → status +
     download_url when ready
   - `GET /api/constructor/jobs/{job_id}/download` →
     `StreamingResponse(media_type="application/zip")`

5. The 200-OK path for the zip is **preserved** as a fallback:
   if the request is single-component, profile is "basic", and
   `fast_mode=True`, the legacy synchronous handler can be
   reached at a new internal helper. We do **not** keep a
   separate public endpoint for this — the contract is "always
   202 + job_id" — but the existing `POST /api/constructor` is
   replaced by the async launcher.

## API Contract

### `POST /api/constructor` (changed)

Request (body unchanged except `fast_mode` is now read):

```json
{
  "components": ["angie-pro"],
  "profile": "standard",
  "configs": {"angie-pro": {"ports": {}, "volumes": {}, "env": {}}},
  "fast_mode": true
}
```

Response (HTTP 202):

```json
{
  "job_id": "abc123def456",
  "status": "pending",
  "slug": "angie-pro+1",
  "profile": "standard",
  "fast_mode": true,
  "estimated_seconds": 135
}
```

### `GET /api/constructor/jobs/{job_id}` (new)

While pending/running:

```json
{"job_id": "abc123", "status": "running", "elapsed_seconds": 42}
```

When ready:

```json
{
  "job_id": "abc123",
  "status": "ok",
  "elapsed_seconds": 132,
  "download_url": "/api/constructor/jobs/abc123/download",
  "stack_name": "angie-pro",
  "security_score": null,
  "errors": []
}
```

On failure:

```json
{"job_id": "abc123", "status": "failed", "error": "Component 'foo' not found"}
```

### `GET /api/constructor/jobs/{job_id}/download` (new)

HTTP 200, `Content-Type: application/zip`,
`Content-Disposition: attachment; filename=gosdocker-<stack>.zip`.
Returns 404 if job_id is unknown, 409 if status is not in
{ok, degraded}.

## File Map

| File | Action | Purpose |
|---|---|---|
| `backend/app/api/constructor.py` | modify | add async launcher, `fast_mode` field, job endpoints, `PipelineCache`, `BackgroundTasks` import |
| `backend/app/api/constructor.py:265-281` | refactor | extract pipeline-running block into `_run_constructor_job` |
| `backend/tests/test_constructor_async.py` | create | TDD tests: 202 response, fast_mode cache hit, fast_mode cache miss, download endpoint, polling endpoint |
| `frontend/src/composables/useApi.ts` | modify | `constructorGenerate` returns `{job_id, status, ...}` (JSON), not Blob; new `pollConstructorJob` + `downloadConstructorJob` helpers |
| `frontend/src/components/ComponentCard.vue` | modify | call `pollConstructorJob` then `downloadConstructorJob`, use resulting Blob for the click-to-download flow |
| `frontend/src/views/ConstructorView.vue` | modify | same change for the multi-component "Проверить → Скачать" flow |

## Test Plan

| Test | What it covers |
|---|---|
| `test_constructor_returns_202_with_job_id` | Endpoint is async: response has `job_id`, `status="pending"`, HTTP 202. |
| `test_constructor_fast_mode_cache_hit` | 2nd call with same (slug, profile) + `fast_mode=true` returns job whose pipeline ran 0 times (cache hit). |
| `test_constructor_fast_mode_cache_miss_runs_pipeline` | 1st call with `fast_mode=true` still runs the pipeline (we don't fail loudly on miss). |
| `test_constructor_job_poll_returns_status` | `GET /api/constructor/jobs/{id}` returns current job state. |
| `test_constructor_job_download_streams_zip` | When status=ok, `GET /download` returns HTTP 200, `application/zip`, valid zip magic bytes. |
| `test_constructor_job_download_409_when_running` | When status=pending|running, `/download` returns HTTP 409. |
| `test_constructor_pydantic_accepts_fast_mode` | `ConstructorRequest.model_validate({..., "fast_mode": true})` does not raise (regression test for the dead-letter field). |
| `test_constructor_rejects_unknown_slug` | Pre-existing validation preserved: bad slug → 400. |

All tests run against the live TestClient. Pipeline is monkey-patched
with a fast stub so the test suite runs in <2s.

## Out of Scope (re-stated)

- Pipeline work itself (BuildStep, ScanStep, etc.) — touched only
  via the cache layer
- UI redesign — minimum-change to wire the new API
- 502 / nginx timeout tuning — orthogonal (covered by AC-INF-2)
- Pre-existing parser bug (`Results` vs `results` in trivy) — AC-7
  candidate
- Redis-backed job store — future work, AC-4 already TODOs it

## Open Questions

None. Фёдор already approved approach #4: "глубокий refactor,
202+job_id (как Phase 06 AC-4) + fast_mode + кеш". This spec is
the formal writeup of that conversation.
