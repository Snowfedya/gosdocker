// Bug #18 (18 Jun 2026, runtime-confirmed on /catalog):
// Clicking "Скачать Docker образ" on a component card (e.g. Angie PRO)
// hangs the UI in "Подготовка..." for 3+ minutes because the card calls
// constructorGenerate WITHOUT with_owasp: false, so the backend runs the
// full security pipeline.
//
// These tests pin down the contract: ComponentCard.quickDownload must
// call constructorGenerate with with_owasp: false so the fast path is
// taken.

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'

// Mock the composable BEFORE importing the component.
const constructorGenerateMock = vi.fn()
const generateStackMock = vi.fn()

vi.mock('../../composables/useApi', () => ({
  useApi: () => ({
    constructorGenerate: constructorGenerateMock,
    generateStack: generateStackMock,
    buildComponent: vi.fn(),
    fetchCategories: vi.fn(),
    fetchComponents: vi.fn(),
    fetchStacks: vi.fn(),
    fetchReports: vi.fn(),
    constructorDiagnostic: vi.fn(),
  }),
}))

import ComponentCard from '../../components/ComponentCard.vue'
import type { Component } from '../../types'

const baseComponent: Component = {
  slug: 'angie-pro',
  name: 'Angie PRO',
  description: 'Test',
  version: '1.10.0',
  category: 'web-servers',
  category_label: 'Web',
  source: 'registry',
  is_registry: true,
  has_registry: true,
  default_ports: { '80': 80 },
  default_volumes: {},
  default_env: {},
  tags: [],
}

const routes = [
  { path: '/component/:slug', name: 'component', component: { template: '<div/>' } },
]

beforeEach(() => {
  constructorGenerateMock.mockReset()
  generateStackMock.mockReset()
  // Default: resolve immediately with a tiny blob so the function unwinds.
  constructorGenerateMock.mockResolvedValue(new Blob())
  generateStackMock.mockResolvedValue(new Blob())
})

async function mountCard(component: Partial<Component> = {}) {
  const router = createRouter({ history: createMemoryHistory(), routes })
  await router.push('/')
  await router.isReady()
  const wrapper = mount(ComponentCard, {
    props: { component: { ...baseComponent, ...component } as Component },
    global: { plugins: [router] },
  })
  return wrapper
}

describe('ComponentCard — quickDownload AC-CONST-4 fast-path', () => {
  it('registry component: sends with_owasp=false to constructorGenerate (Bug #18)', async () => {
    const wrapper = await mountCard({ is_registry: true, has_registry: true })
    await wrapper.find('button.flex-1').trigger('click')
    await flushPromises()

    expect(constructorGenerateMock).toHaveBeenCalledTimes(1)
    const req = constructorGenerateMock.mock.calls[0][0]
    expect(req.with_owasp).toBe(false) // Bug #18: must take fast path
  })

  it('non-registry component: still does NOT call constructorGenerate (only generateStack)', async () => {
    const wrapper = await mountCard({ is_registry: false, has_registry: false })
    await wrapper.find('button.flex-1').trigger('click')
    await flushPromises()

    expect(constructorGenerateMock).not.toHaveBeenCalled()
    expect(generateStackMock).toHaveBeenCalledTimes(1)
  })

  it('sends the expected profile + configs structure for the registry path', async () => {
    const wrapper = await mountCard({ is_registry: true, has_registry: true })
    await wrapper.find('button.flex-1').trigger('click')
    await flushPromises()

    const req = constructorGenerateMock.mock.calls[0][0]
    expect(req.components).toEqual(['angie-pro'])
    expect(req.profile).toBe('standard')
    expect(req.configs['angie-pro']).toBeDefined()
    expect(req.configs['angie-pro'].ports).toEqual({ '80': 80 })
  })
})
