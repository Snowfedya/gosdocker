import type {
  Category,
  Component,
  Stack,
  ComponentConfig,
  RegistryComponent,
  ConstructorRequest,
  ConstructorDiagnostic,
  SecurityProfile,
  SecurityReport,
} from '../types'

const API_BASE = '/api'

export function useApi() {
  async function fetchCategories(): Promise<Category[]> {
    const res = await fetch(`${API_BASE}/categories`)
    if (!res.ok) throw new Error('Ошибка загрузки категорий')
    return res.json()
  }

  async function fetchComponents(category?: string, registryOnly?: boolean): Promise<Component[]> {
    const params = new URLSearchParams()
    if (category) params.set('category', category)
    if (registryOnly) params.set('registry_only', 'true')
    const qs = params.toString()
    const res = await fetch(`${API_BASE}/components${qs ? `?${qs}` : ''}`)
    if (!res.ok) throw new Error('Ошибка загрузки компонентов')
    return res.json()
  }

  async function fetchStacks(): Promise<Stack[]> {
    const res = await fetch(`${API_BASE}/stacks`)
    if (!res.ok) throw new Error('Ошибка загрузки стеков')
    return res.json()
  }

  async function generateStack(
    slugs: string[],
    config: Record<string, ComponentConfig>,
    security_profile: string = 'basic'
  ): Promise<Blob> {
    const res = await fetch(`${API_BASE}/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ components: slugs, config, security_profile }),
    })
    if (!res.ok) throw new Error('Ошибка генерации')
    return res.blob()
  }

  // --- Registry API ---

  async function fetchRegistry(): Promise<RegistryComponent[]> {
    const res = await fetch(`${API_BASE}/registry`)
    if (!res.ok) throw new Error('Ошибка загрузки реестра')
    return res.json()
  }

  async function fetchRegistryManifest(slug: string): Promise<Record<string, unknown>> {
    const res = await fetch(`${API_BASE}/registry/${slug}`)
    if (!res.ok) throw new Error('Ошибка загрузки манифеста')
    return res.json()
  }

  async function downloadDockerfile(slug: string): Promise<Blob> {
    const res = await fetch(`${API_BASE}/registry/${slug}/dockerfile`)
    if (!res.ok) throw new Error('Ошибка скачивания Dockerfile')
    return res.blob()
  }

  async function downloadManifest(slug: string): Promise<Blob> {
    const res = await fetch(`${API_BASE}/registry/${slug}/manifest`)
    if (!res.ok) throw new Error('Ошибка скачивания манифеста')
    return res.blob()
  }

  // --- Constructor API ---

  async function constructorDiagnostic(
    req: ConstructorRequest
  ): Promise<ConstructorDiagnostic> {
    const res = await fetch(`${API_BASE}/constructor/diagnostic`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(req),
    })
    if (!res.ok) throw new Error('Ошибка диагностики конструктора')
    return res.json()
  }

  async function constructorGenerate(
    req: ConstructorRequest
  ): Promise<Blob> {
    const res = await fetch(`${API_BASE}/constructor`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(req),
    })
    if (!res.ok) throw new Error('Ошибка генерации конструктора')
    return res.blob()
  }

  async function fetchProfiles(): Promise<SecurityProfile[]> {
    const res = await fetch(`${API_BASE}/constructor/profiles`)
    if (!res.ok) throw new Error('Ошибка загрузки профилей')
    return res.json()
  }

  // --- Registry Build + Reports API ---

  async function buildComponent(slug: string, profile: string = 'standard'): Promise<SecurityReport> {
    const res = await fetch(`${API_BASE}/registry/${slug}/build?profile=${encodeURIComponent(profile)}`, {
      method: 'POST',
    })
    if (!res.ok) throw new Error('Ошибка запуска проверки безопасности')
    return res.json()
  }

  async function fetchReports(slug: string): Promise<SecurityReport> {
    const res = await fetch(`${API_BASE}/registry/${slug}/reports`)
    if (!res.ok) throw new Error('Отчёт не найден — сначала запустите проверку')
    return res.json()
  }

  return {
    fetchCategories,
    fetchComponents,
    fetchStacks,
    generateStack,
    fetchRegistry,
    fetchRegistryManifest,
    downloadDockerfile,
    downloadManifest,
    constructorDiagnostic,
    constructorGenerate,
    fetchProfiles,
    buildComponent,
    fetchReports,
  }
}
