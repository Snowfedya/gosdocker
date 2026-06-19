# Fix "Запустить проверку" Button — Returns Job, UI Shows Fake 100/A + Errors

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** "Запустить проверку безопасности" on `/components/{slug}` must actually trigger a real scan and show a meaningful result. Today it POSTs to `/registry/{slug}/build` (which returns `{job_id, status: "pending"}` async job), the frontend assigns that to `report` directly, and `SecuritySummary` renders fake **Скоринг 100 / A** + **❌ Ошибки** because `status !== "ok"` and `trivy` is missing.

**Architecture:**
- Backend: add `POST /api/registry/{slug}/scan` (sync or near-sync) that returns a real `SecurityReport` directly. Or keep /build as 202+job and have frontend **poll** for completion, then `fetchReports()`.
- Frontend: `buildComponent()` should either (a) poll the new job, or (b) call a new `scanComponent()` endpoint that returns the report. Whichever route is chosen, `SecuritySummary` must receive a valid `SecurityReport` with `status: "ok"|"degraded"|"failed"`, not a `{job_id}` object.
- `SecuritySummary` score fallback (`if (!props.report?.trivy) return 100`) must be replaced: if trivy is missing, show **"Не сканировано"** instead of a misleading 100.

**Tech Stack:** FastAPI, Pydantic, Vue 3, TypeScript, vitest, pytest.

---

## Root Cause (from runtime)

```
[Frontend] buildComponent() — POST /api/registry/{slug}/build
[Backend]  run_pipeline() — returns {"job_id":"abc", "status":"pending", ...}
[Frontend] report.value = buildComponent(...) → report = {job_id, status:"pending"}
[UI]       SecuritySummary:65 — status !== "ok" → "❌ Ошибки"
[UI]       SecuritySummary:17 — report.trivy is undefined → score = 100, grade = "A"
[UI]       SecuritySummary:23 — report.sbom is undefined → depCount = 0
```

Result: user sees **Скоринг: 100, Grade: A, "❌ Ошибки", 0 dependencies** all at once — a logical impossibility that the security-aware user correctly identified as a bug.

## Acceptance Criteria

- [ ] Pressing "Запустить проверку безопасности" with a valid slug returns a real `SecurityReport` (status ∈ {ok, degraded, failed}, trivy + sbom populated as much as possible).
- [ ] `SecuritySummary` shows a real score, not the default 100.
- [ ] When the report is genuinely clean (no vulns found AND scan actually ran), the badge is "✅ Успешно", NOT "❌ Ошибки".
- [ ] When trivy is missing (truly not scanned), UI shows "Не сканировано" (not a fake 100).
- [ ] Frontend types: `buildComponent`/`scanComponent` return type matches reality.
- [ ] Backend: tests for the new or fixed endpoint pass.
- [ ] Frontend: tests for `SecuritySummary` for missing trivy, status="ok", status="pending" cases pass.

---

## Task 1: Add failing test for the SecuritySummary score fallback (frontend TDD)

**Files:**
- Modify: `frontend/src/test/components/SecuritySummary.test.ts` (or create)

- [ ] **Step 1.1: Read existing tests** to understand the structure.

```bash
cd /opt/gosdocker/frontend
ls src/test/components/
cat src/test/components/SecuritySummary.test.ts 2>/dev/null || echo "no test yet"
```

- [ ] **Step 1.2: Write failing test — when `report.trivy` is missing, score must be `null` and a "Не сканировано" placeholder must render.**

```typescript
import { mount } from '@vue/test-utils'
import { describe, it, expect } from 'vitest'
import SecuritySummary from '../../components/security/SecuritySummary.vue'

describe('SecuritySummary', () => {
  it('does NOT show 100 score when trivy is missing', () => {
    const wrapper = mount(SecuritySummary, {
      props: {
        report: { status: 'ok', sbom: { total_components: 0 } } as any,  // trivy missing
        loading: false,
        error: null,
        slug: 'angie-pro',
      },
    })
    expect(wrapper.text()).not.toContain('100')
    expect(wrapper.text()).toMatch(/Не сканировано|Не запущено|--/i)
  })
})
```

- [ ] **Step 1.3: Run the test and verify it FAILS.**

```bash
cd /opt/gosdocker/frontend && pnpm test -- SecuritySummary 2>&1 | tail -20
```

Expected: FAIL — "100" is present, "Не сканировано" is not.

- [ ] **Step 1.4: Commit failing test.**

```bash
cd /opt/gosdocker && git add frontend/src/test/components/SecuritySummary.test.ts
git commit -m "test(frontend): SecuritySummary must not show 100 when trivy is missing"
```

---

## Task 2: Replace the misleading 100 fallback in SecuritySummary

**Files:**
- Modify: `frontend/src/components/security/SecuritySummary.vue:16-23`

- [ ] **Step 2.1: Edit the `score` computed to return `null` when trivy is missing.**

Old (line 16-19):
```ts
const score = computed(() => {
  if (!props.report?.trivy) return 100
  return calculateSecurityScore(props.report.trivy.by_severity)
})
```

New:
```ts
const score = computed<number | null>(() => {
  if (!props.report?.trivy) return null
  return calculateSecurityScore(props.report.trivy.by_severity)
})
```

- [ ] **Step 2.2: Update the `grade` computed to handle null score.**

Old (line 21):
```ts
const grade = computed(() => scoreToGrade(score.value))
```

New:
```ts
const grade = computed(() => {
  if (score.value === null) return '–'  // em-dash placeholder
  return scoreToGrade(score.value)
})
```

- [ ] **Step 2.3: Update the template to render "Не сканировано" when trivy is missing.**

Find the section that renders `{{ score }}` and `{{ grade }}`. Wrap them so when `score === null`, show "Не сканировано":

```html
<div class="text-xs text-gray-500 dark:text-slate-400">Скоринг</div>
<div class="text-lg font-bold text-gray-900 dark:text-white tabular-nums">
  <template v-if="score !== null">{{ score }}</template>
  <template v-else>
    <span class="text-sm font-normal text-gray-400">Не сканировано</span>
  </template>
</div>
```

For the grade circle, render `–` (em-dash) when score is null, and apply a neutral gray color. The `gradeColors` map needs a new key for the unknown case.

In `<script setup>`:
```ts
const gradeColors: Record<string, string> = {
  A: 'bg-emerald-500 text-white',
  B: 'bg-blue-500 text-white',
  C: 'bg-amber-400 text-white',
  D: 'bg-orange-500 text-white',
  E: 'bg-red-500 text-white',
  '–': 'bg-gray-300 text-gray-600',
}
```

- [ ] **Step 2.4: Run the failing test from Task 1; it should now PASS.**

```bash
cd /opt/gosdocker/frontend && pnpm test -- SecuritySummary 2>&1 | tail -10
```

Expected: PASS.

- [ ] **Step 2.5: Run the full frontend test suite to check for regressions.**

```bash
cd /opt/gosdocker/frontend && pnpm test 2>&1 | tail -15
```

Expected: all green. If existing tests fail because they passed `score: 100, grade: 'A'` and now expect different output, fix the test data — but the production code should never be tricked into showing 100 again.

- [ ] **Step 2.6: Commit.**

```bash
cd /opt/gosdocker && git add frontend/src/components/security/SecuritySummary.vue
git commit -m "fix(frontend): SecuritySummary shows 'Не сканировано' instead of fake 100"
```

---

## Task 3: Add backend test that /build returns a job_id, not a SecurityReport

**Files:**
- Modify or create: `backend/tests/test_registry.py`

- [ ] **Step 3.1: Find existing tests for /build.**

```bash
cd /opt/gosdocker/backend && grep -n "build" tests/test_registry.py | head -10
```

- [ ] **Step 3.2: Add a test that documents the actual response shape.**

```python
def test_build_returns_job_id_not_security_report(client, valid_slug):
    """AC-4: POST /build must return a 202+job_id, not a SecurityReport.
    Frontend code that treats this response as a SecurityReport is a bug —
    this test pins the contract so the bug can't regress silently."""
    r = client.post(f"/api/registry/{valid_slug}/build?profile=standard")
    assert r.status_code == 202
    body = r.json()
    assert "job_id" in body
    assert body["status"] in ("pending", "running")  # async
    # Must NOT contain SecurityReport fields
    assert "trivy" not in body
    assert "sbom" not in body
    assert "security_score" not in body
```

- [ ] **Step 3.3: Run the test; it should pass immediately (this is a contract test).**

```bash
cd /opt/gosdocker/backend && python3 -m pytest tests/test_registry.py::test_build_returns_job_id_not_security_report -v 2>&1 | tail -10
```

Expected: PASS.

- [ ] **Step 3.4: Commit.**

```bash
cd /opt/gosdocker && git add backend/tests/test_registry.py
git commit -m "test(backend): pin /build contract — returns job_id, not SecurityReport"
```

---

## Task 4: Fix frontend buildComponent to poll for the report

**Files:**
- Modify: `frontend/src/composables/useApi.ts:159-165`
- Modify: `frontend/src/composables/useSecurityReport.ts:26-37`
- Modify: `frontend/src/views/ComponentView.vue:81-92`

- [ ] **Step 4.1: Add a new `scanComponent(slug, profile)` function in `useApi.ts` that POSTs /build, polls the job, and returns the final SecurityReport.**

Insert after `buildComponent` (line 165):

```ts
async function scanComponent(slug: string, profile: string = 'standard'): Promise<SecurityReport> {
  // POST /build returns a job_id; poll /registry/{slug}/jobs/{job_id}
  // until status is final, then call fetchReports to get the actual report.
  const startRes = await fetch(`${API_BASE}/registry/${slug}/build?profile=${encodeURIComponent(profile)}`, {
    method: 'POST',
  })
  if (!startRes.ok) throw new Error('Не удалось запустить сканирование')
  const { job_id } = await startRes.json()
  if (!job_id) throw new Error('Сервер не вернул job_id')

  // Poll every 2s, max 5 minutes
  const deadline = Date.now() + 5 * 60_000
  while (Date.now() < deadline) {
    await new Promise((r) => setTimeout(r, 2000))
    const r = await fetch(`${API_BASE}/registry/${slug}/jobs/${job_id}`)
    if (!r.ok) continue
    const job = await r.json()
    if (job.status === 'ok' || job.status === 'degraded' || job.status === 'failed') {
      // Job is final — fetch the actual report
      return await fetchReports(slug)
    }
  }
  throw new Error('Сканирование не завершилось за 5 минут')
}
```

- [ ] **Step 4.2: Export scanComponent.**

In the return object at the bottom of `useApi.ts` (line 173-187), add:
```ts
scanComponent,
```

- [ ] **Step 4.3: Update useSecurityReport.ts `scan()` to use `scanComponent` instead of `buildComponent`.**

```ts
const { fetchReports, scanComponent } = useApi()

async function scan(profile: string = 'standard'): Promise<void> {
  loading.value = true
  error.value = null
  report.value = null
  try {
    report.value = await scanComponent(slug, profile)
  } catch (e) {
    error.value = (e as Error).message
  } finally {
    loading.value = false
  }
}
```

- [ ] **Step 4.4: ComponentView.vue — no change needed if it just calls `runSecurityScan` which calls `buildComponent`. Update it to use `scanComponent` for clarity:**

In `ComponentView.vue:81-92`:
```ts
async function runSecurityScan() {
  const slug = route.params.slug as string
  reportLoading.value = true
  reportError.value = null
  report.value = null
  try {
    report.value = await scanComponent(slug, selectedProfile.value)  // was buildComponent
  } catch (e) {
    reportError.value = (e as Error).message
  } finally {
    reportLoading.value = false
  }
}
```

Add to the imports: `import { useSecurityReport } from '../composables/useSecurityReport'` is already there. Need to add `const { scanComponent } = useApi()` or import directly.

- [ ] **Step 4.5: Run the frontend tests.**

```bash
cd /opt/gosdocker/frontend && pnpm test 2>&1 | tail -15
```

Expected: all green.

- [ ] **Step 4.6: Commit.**

```bash
cd /opt/gosdocker && git add frontend/src/composables/useApi.ts frontend/src/composables/useSecurityReport.ts frontend/src/views/ComponentView.vue
git commit -m "fix(frontend): 'Run security scan' now polls for the actual report"
```

---

## Task 5: Live verification

- [ ] **Step 5.1: Deploy the changes.**

```bash
cd /opt/gosdocker && /usr/bin/docker compose -f /opt/gosdocker/docker-compose.yml up -d --build backend frontend 2>&1 | tail -3
sleep 10
```

- [ ] **Step 5.2: Press the button via curl. Verify that the API now actually returns a SecurityReport shape (or poll completes).**

```bash
# Trigger the scan
START=$(curl -sS -X POST "https://gosdocker.ru/api/registry/angie-pro/build?profile=standard" --max-time 5)
echo "Start: $START"
JOB=$(echo "$START" | python3 -c "import sys, json; print(json.load(sys.stdin)['job_id'])")

# Poll for the job to finish
for i in $(seq 1 60); do
  J=$(curl -sS "https://gosdocker.ru/api/registry/angie-pro/jobs/$JOB" --max-time 3)
  S=$(echo "$J" | python3 -c "import sys, json; print(json.load(sys.stdin).get('status'))")
  echo "  t=+$((i*2))s status=$S"
  if [ "$S" = "ok" ] || [ "$S" = "degraded" ] || [ "$S" = "failed" ]; then
    break
  fi
  sleep 2
done

# Now fetch the actual report
curl -sS "https://gosdocker.ru/api/registry/angie-pro/reports" --max-time 5 | python3 -m json.tool | head -20
```

- [ ] **Step 5.3: Open https://gosdocker.ru/components/angie-pro in browser, click "Запустить проверку", wait 30-60s, then check:**
  - The "❌ Ошибки" badge is GONE if the report is `ok` or `degraded`.
  - The "Скоринг" shows the **actual score** (e.g. 100 if trivy found 0 vulns, or lower if any).
  - If trivy is genuinely missing, "Скоринг" shows "Не сканировано" (not 100).
  - "Зависимостей в SBOM" shows the real count (not 0 unless genuinely 0).

- [ ] **Step 5.4: Run the full test suite one last time.**

```bash
cd /opt/gosdocker/backend && python3 -m pytest tests/ --ignore=tests/test_pipeline.py -q --timeout=30 2>&1 | tail -5
cd /opt/gosdocker/frontend && pnpm test 2>&1 | tail -10
```

Expected: 107+ passed backend, all green frontend.

- [ ] **Step 5.5: Commit any pending changes and push.**

```bash
cd /opt/gosdocker && git status
git push origin master
```

---

## Risks & Tradeoffs

- **Polling vs WebSocket**: I'm using 2s polling. Real-time would be nicer but requires WebSocket infra we don't have. Polling is the existing pattern (AC-4 already uses it for /registry/build).
- **5 min timeout**: scans have failed at 180s before (OWASP DC). 5 min is generous but won't catch a hung process. If we hit it, user sees an error and can retry.
- **Score fallback**: "Не сканировано" is honest but less reassuring than "100". A defense-in-depth user prefers the honest answer.
- **Scope**: I'm fixing the *frontend* root cause (the type mismatch and the misleading 100). I'm NOT fixing the *backend* root cause (Trivy scans the wrong artifact, OWASP is a placeholder, cosign is unsigned). Those are deeper issues and out of scope for this bug.

## Open Questions

- None blocking. The plan is concrete and self-contained.
