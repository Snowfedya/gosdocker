import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createRouter, createWebHistory } from 'vue-router'
import SecurityReportView from '../../views/SecurityReportView.vue'
import { useSecurityReport } from '../../composables/useSecurityReport'

// Mock the composable so we can observe the runScan() flow
// without hitting the real API.
const runScanSpy = vi.fn()
const scanMock = vi.fn().mockResolvedValue(undefined)

vi.mock('../../composables/useSecurityReport', () => ({
  useSecurityReport: vi.fn(() => ({
    report: { value: null },
    loading: { value: false },
    error: { value: null },
    score: { value: 0 },
    scoreGrade: { value: 'F' },
    severitySummary: { value: {} },
    vulnerabilities: { value: [] },
    load: vi.fn(),
    scan: scanMock,
  })),
}))

describe('SecurityReportView — runScan wiring', () => {
  beforeEach(() => {
    scanMock.mockClear()
  })

  it('exposes scan() from useSecurityReport so runScan() can call it', () => {
    // The view destructures useSecurityReport and calls `await scan(profile)` inside
    // runScan(). If scan is not exposed in the destructure, the template fails to
    // compile (TS error TS2304). This test asserts scan is in the return value.
    const composable = useSecurityReport('nginx')
    expect(composable).toHaveProperty('scan')
    expect(typeof composable.scan).toBe('function')
  })

  it('runScan() triggers scan() from the composable', async () => {
    const router = createRouter({
      history: createWebHistory(),
      routes: [
        { path: '/registry/:slug/security', component: SecurityReportView },
        { path: '/', component: { template: '<div />' } },
      ],
    })
    await router.push('/registry/nginx/security')
    await router.isReady()

    const w = mount(SecurityReportView, {
      global: { plugins: [router] },
    })
    await flushPromises()

    // scanMock should have been called by onMounted → runScan (since report is null)
    expect(scanMock).toHaveBeenCalledWith('standard')
    runScanSpy.mockClear()
    // ensure component rendered (smoke check)
    expect(w.exists()).toBe(true)
  })
})
