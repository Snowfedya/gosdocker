export interface SeverityCount {
  CRITICAL: number
  HIGH: number
  MEDIUM: number
  LOW: number
  UNKNOWN: number
}

/** Score 0–100 based on Trivy severity counts */
export function calculateSecurityScore(bySeverity: SeverityCount): number {
  const raw = 100 - (bySeverity.CRITICAL * 15 + bySeverity.HIGH * 5 + bySeverity.MEDIUM * 2 + bySeverity.LOW * 0.5)
  return Math.max(0, Math.min(100, Math.round(raw)))
}

/** Convert numeric score (0–100) to letter grade A–E */
export function scoreToGrade(score: number): string {
  if (score >= 90) return 'A'
  if (score >= 70) return 'B'
  if (score >= 50) return 'C'
  if (score >= 30) return 'D'
  return 'E'
}
