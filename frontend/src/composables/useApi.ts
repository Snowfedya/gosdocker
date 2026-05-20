import type { Category, Component, Stack, ComponentConfig } from '../types'

const API_BASE = '/api'

export function useApi() {
  async function fetchCategories(): Promise<Category[]> {
    const res = await fetch(`${API_BASE}/categories`)
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.detail || 'Ошибка загрузки категорий')
    }
    return res.json()
  }

  async function fetchComponents(category?: string): Promise<Component[]> {
    const url = category
      ? `${API_BASE}/components?category=${encodeURIComponent(category)}`
      : `${API_BASE}/components`
    const res = await fetch(url)
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.detail || 'Ошибка загрузки компонентов')
    }
    return res.json()
  }

  async function fetchStacks(): Promise<Stack[]> {
    const res = await fetch(`${API_BASE}/stacks`)
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.detail || 'Ошибка загрузки стеков')
    }
    return res.json()
  }

  async function generateStack(
    slugs: string[],
    config: Record<string, ComponentConfig>
  ): Promise<Blob> {
    const res = await fetch(`${API_BASE}/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ components: slugs, config })
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.detail || 'Ошибка генерации')
    }
    return res.blob()
  }

  return {
    fetchCategories,
    fetchComponents,
    fetchStacks,
    generateStack
  }
}