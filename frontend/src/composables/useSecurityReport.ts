import { ref, computed } from 'vue'
import type { SecurityReport, Vulnerability } from '../types'
import { calculateSecurityScore, scoreToGrade } from '../utils/security'
import { useApi } from './useApi'

export function useSecurityReport(slug: string) {
  const report = ref<SecurityReport | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  const { fetchReports, buildComponent } = useApi()

  async function load(): Promise<void> {
    loading.value = true
    error.value = null
    try {
      report.value = await fetchReports(slug)
    } catch (e) {
      report.value = null
      error.value = (e as Error).message
    } finally {
      loading.value = false
    }
  }

  async function scan(profile: string = 'standard'): Promise<void> {
    loading.value = true
    error.value = null
    report.value = null
    try {
      report.value = await buildComponent(slug, profile)
    } catch (e) {
      error.value = (e as Error).message
    } finally {
      loading.value = false
    }
  }

  /** Score 0–100 based on Trivy severity counts */
  const score = computed<number>(() => {
    if (!report.value?.trivy) return 100
    return calculateSecurityScore(report.value.trivy.by_severity)
  })

  const scoreGrade = computed<string>(() => scoreToGrade(score.value))

  const totalVulnerabilities = computed<number>(() => {
    return report.value?.trivy?.total_vulnerabilities ?? 0
  })

  const vulnerabilities = computed<Vulnerability[]>(() => {
    return report.value?.trivy?.vulnerabilities ?? []
  })

  const severitySummary = computed(() => {
    if (!report.value?.trivy) return { CRITICAL: 0, HIGH: 0, MEDIUM: 0, LOW: 0, UNKNOWN: 0 }
    return report.value.trivy.by_severity
  })

  return {
    report,
    loading,
    error,
    score,
    scoreGrade,
    totalVulnerabilities,
    vulnerabilities,
    severitySummary,
    load,
    scan,
  }
}
