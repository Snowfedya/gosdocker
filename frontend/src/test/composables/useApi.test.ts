import { describe, it, expect, vi, beforeEach } from 'vitest'
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

  describe('buildComponent', () => {
    it('posts to build endpoint with profile', async () => {
      mockFetch.mockResolvedValueOnce({ ok: true, json: () => Promise.resolve({ slug: 'nginx', status: 'ok' }) })

      const { buildComponent } = useApi()
      const result = await buildComponent('nginx', 'standard')

      expect(mockFetch).toHaveBeenCalledWith('/api/registry/nginx/build?profile=standard', { method: 'POST' })
      expect(result).toEqual({ slug: 'nginx', status: 'ok' })
    })

    it('uses default profile when not specified', async () => {
      mockFetch.mockResolvedValueOnce({ ok: true, json: () => Promise.resolve({}) })

      const { buildComponent } = useApi()
      await buildComponent('nginx')

      expect(mockFetch).toHaveBeenCalledWith('/api/registry/nginx/build?profile=standard', { method: 'POST' })
    })
  })

  describe('generateStack', () => {
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

  describe('fetchReports', () => {
    it('fetches security report for a slug', async () => {
      mockFetch.mockResolvedValueOnce({ ok: true, json: () => Promise.resolve({ slug: 'nginx' }) })

      const { fetchReports } = useApi()
      const result = await fetchReports('nginx')

      expect(mockFetch).toHaveBeenCalledWith('/api/registry/nginx/reports')
      expect(result).toEqual({ slug: 'nginx' })
    })
  })
})
