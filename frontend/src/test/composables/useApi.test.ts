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
