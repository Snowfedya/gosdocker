import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { useApi } from '../../composables/useApi'

const mockFetch = vi.fn()
globalThis.fetch = mockFetch

beforeEach(() => {
  mockFetch.mockReset()
})

describe('useApi', () => {
  describe('fetchCategories', () => {
    it('fetches categories from /api/categories', async () => {
      const categories = [{ id: '1', name: 'Web', slug: 'web', icon: 'globe', description: null, sort_order: 1, components_count: 5, registry_count: 2, community_count: 3 }]
      mockFetch.mockResolvedValueOnce({ ok: true, json: () => Promise.resolve(categories) })

      const { fetchCategories } = useApi()
      const result = await fetchCategories()

      expect(mockFetch).toHaveBeenCalledWith('/api/categories')
      expect(result).toEqual(categories)
    })

    it('throws on non-ok response', async () => {
      mockFetch.mockResolvedValueOnce({ ok: false })

      const { fetchCategories } = useApi()
      await expect(fetchCategories()).rejects.toThrow('Ошибка загрузки категорий')
    })
  })

  describe('fetchComponents', () => {
    it('fetches components without params', async () => {
      mockFetch.mockResolvedValueOnce({ ok: true, json: () => Promise.resolve([]) })

      const { fetchComponents } = useApi()
      await fetchComponents()

      expect(mockFetch).toHaveBeenCalledWith('/api/components')
    })

    it('passes category as query param', async () => {
      mockFetch.mockResolvedValueOnce({ ok: true, json: () => Promise.resolve([]) })

      const { fetchComponents } = useApi()
      await fetchComponents('web')

      expect(mockFetch).toHaveBeenCalledWith('/api/components?category=web')
    })

    it('passes registry_only flag', async () => {
      mockFetch.mockResolvedValueOnce({ ok: true, json: () => Promise.resolve([]) })

      const { fetchComponents } = useApi()
      await fetchComponents(undefined, true)

      expect(mockFetch).toHaveBeenCalledWith('/api/components?registry_only=true')
    })
  })

  describe('fetchStacks', () => {
    it('fetches stacks from /api/stacks', async () => {
      mockFetch.mockResolvedValueOnce({ ok: true, json: () => Promise.resolve([]) })

      const { fetchStacks } = useApi()
      await fetchStacks()

      expect(mockFetch).toHaveBeenCalledWith('/api/stacks')
    })
  })

  describe('buildComponent (AC-4 async scan)', () => {
    it('posts config and returns blob', async () => {
      const blob = new Blob()
      mockFetch.mockResolvedValueOnce({ ok: true, blob: () => Promise.resolve(blob) })

      const { generateStack } = useApi()
      const result = await generateStack(['nginx', 'postgres'], { nginx: { ports: {}, volumes: {}, env: {} } })

      expect(mockFetch).toHaveBeenCalledWith('/api/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ components: ['nginx', 'postgres'], config: { nginx: { ports: {}, volumes: {}, env: {} } }, security_profile: 'basic' }),
      })
      expect(result).toBe(blob)
    })

    it('throws PortConflictError on 409 with structured detail', async () => {
      // Backend returns FastAPI-style 409 with detail.conflicts
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 409,
        json: () => Promise.resolve({
          detail: {
            error: 'port_conflict',
            conflicts: [
              { host_port: 80, services: ['nginx', 'angie-pro'] },
              { host_port: 443, services: ['nginx', 'angie-pro'] },
            ],
          },
        }),
      })

      const { generateStack } = useApi()
      let caught: unknown
      try {
        await generateStack(['nginx', 'angie-pro'], { nginx: { ports: {}, volumes: {}, env: {} } })
      } catch (e) {
        caught = e
      }
      expect(caught).toBeDefined()
      // The thrown error must expose .conflicts and .status for the UI
      const err = caught as { name?: string; status?: number; conflicts?: unknown[]; message?: string }
      expect(err.name).toBe('PortConflictError')
      expect(err.status).toBe(409)
      expect(Array.isArray(err.conflicts)).toBe(true)
      expect(err.conflicts).toHaveLength(2)
      expect((err.conflicts![0] as { host_port: number }).host_port).toBe(80)
      // Message must mention the first conflict for fallback display
      expect(err.message).toMatch(/порт|80|nginx/i)
    })

    it('throws a generic Error on 500 without detail', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        json: () => Promise.reject(new Error('not json')),
      })

      const { generateStack } = useApi()
      await expect(generateStack(['nginx'], { nginx: { ports: {}, volumes: {}, env: {} } }))
        .rejects.toThrow(/Ошибка генерации/)
    })
  })

  describe('constructorGenerate (AC-CONST-4 fast-path for cards)', () => {
    // Bug #18 (18 Jun 2026, runtime-confirmed by user report on /catalog):
    //  - ComponentCard.quickDownload calls constructorGenerate WITHOUT
    //    `with_owasp: false`. Backend defaults with_owasp=True → runs
    //    full OWASP / Trivy / Cosign pipeline. Result: clicking
    //    "Скачать Docker образ" on Angie PRO from /catalog hangs the
    //    UI for 3+ minutes in "Подготовка..." state.
    //  - The fix is in ComponentCard.vue, not in useApi.ts. The
    //    test below documents the contract: constructorGenerate
    //    accepts a `with_owasp` field in ConstructorRequest. The
    //    ComponentCard fix is then a one-line `with_owasp: false`
    //    addition, verified by inspecting the request body that
    //    gets sent.
    //
    // We don't test the full submit-poll-download cycle here —
    // that's already covered by buildComponent. We test only that
    // the request body includes with_owasp: false when the caller
    // sets it.

    it('passes with_owasp=false through to POST /api/constructor body', async () => {
      mockFetch.mockResolvedValueOnce({ ok: true, json: () => Promise.resolve({ job_id: 'jid' }) })
      // Simulate a fast job that finishes immediately.
      mockFetch.mockResolvedValueOnce({ ok: true, json: () => Promise.resolve({ status: 'ok', zip_path: '/tmp/jid.zip' }) })
      // The download endpoint.
      mockFetch.mockResolvedValueOnce({ ok: true, blob: () => Promise.resolve(new Blob()) })

      const { constructorGenerate } = useApi()
      await constructorGenerate({
        components: ['angie-pro'],
        profile: 'standard',
        fast_mode: true,
        with_owasp: false,           // <-- the contract being enforced
        configs: { 'angie-pro': { ports: { 80: 8080 }, volumes: {}, env: {} } },
      })

      // First call = the POST. Inspect its body.
      const postCall = mockFetch.mock.calls[0]
      expect(postCall[0]).toBe('/api/constructor')
      const opts = postCall[1] as RequestInit
      const body = JSON.parse(opts.body as string)
      expect(body.with_owasp).toBe(false)
      expect(body.components).toEqual(['angie-pro'])
    })
  })

  describe('fetchReports', () => {
    it('fetches security report for a slug', async () => {
      mockFetch.mockResolvedValueOnce({ ok: true, json: () => Promise.resolve({ slug: 'nginx' }) })

      const { fetchReports } = useApi()
      const result = await fetchReports('nginx')

      expect(mockFetch).toHaveBeenCalledWith('/api/registry/nginx/reports')
      expect(result).toEqual({ slug: 'nginx' })
    })
  })

  describe('buildComponent (AC-4 async scan)', () => {
    // AC-4: buildComponent must submit-then-poll-then-return, not
    // return the {job_id, status:'pending'} envelope as a report.
    // The old code did `return res.json()` directly, which caused
    // SecuritySummary to render `pending` as if it were a finished
    // report (no sbom/trivy/owasp/security_score fields). The new
    // contract: poll every ~2s until the job reaches {ok, degraded},
    // then return job.report. On `failed`, throw the job's error.

    afterEach(() => {
      vi.useRealTimers()
    })

    it('submits, polls, and returns job.report when status becomes ok', async () => {
      vi.useFakeTimers()
      const fakeReport = {
        slug: 'angie-pro',
        profile: 'standard',
        sbom: { packages: [] },
        trivy: { vulnerabilities: [] },
        owasp: { score: 95 },
        security_score: 95,
      }
      // 1) submit returns 202 + job_id
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ job_id: 'abc123', slug: 'angie-pro', profile: 'standard', status: 'pending' }),
      })
      // 2) first poll: still running
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ job_id: 'abc123', status: 'running' }),
      })
      // 3) second poll: ok with report
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ job_id: 'abc123', status: 'ok', report: fakeReport }),
      })

      const { buildComponent } = useApi()
      const resultPromise = buildComponent('angie-pro', 'standard')

      // advance through the two setTimeout(2000) waits inside the poll loop
      await vi.advanceTimersByTimeAsync(2000)
      await vi.advanceTimersByTimeAsync(2000)

      const result = await resultPromise

      // First call: POST submit
      expect(mockFetch.mock.calls[0][0]).toBe('/api/registry/angie-pro/build?profile=standard')
      expect(mockFetch.mock.calls[0][1].method).toBe('POST')
      // Second + third calls: GET poll
      expect(mockFetch.mock.calls[1][0]).toBe('/api/registry/angie-pro/jobs/abc123')
      expect(mockFetch.mock.calls[2][0]).toBe('/api/registry/angie-pro/jobs/abc123')
      // Returned value is the inner report, NOT the job envelope
      expect(result).toEqual(fakeReport)
      expect((result as any).status).toBeUndefined()
    })

    it('throws on failed status with backend error message', async () => {
      vi.useFakeTimers()
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ job_id: 'fail1', status: 'pending' }),
      })
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ job_id: 'fail1', status: 'failed', error: 'docker pull failed: 404' }),
      })

      const { buildComponent } = useApi()
      const resultPromise = buildComponent('angie-pro', 'standard')
      // Attach a no-op rejection handler before advancing timers so
      // the test framework's unhandled-rejection tracker doesn't
      // trip on the microtask that resolves the throw. The actual
      // assertion below is what validates the error.
      resultPromise.catch(() => {})
      await vi.advanceTimersByTimeAsync(2000)
      await expect(resultPromise).rejects.toThrow('Сканирование не удалось: docker pull failed: 404')
    })

    it('throws with HTTP status on submit pre-flight 4xx', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
        json: () => Promise.resolve({ detail: "Component 'bogus' not found in registry" }),
      })

      const { buildComponent } = useApi()
      await expect(buildComponent('bogus', 'standard')).rejects.toThrow(
        "Ошибка запуска проверки: Component 'bogus' not found in registry",
      )
    })
  })
})
