import { describe, it, expect } from 'vitest'
import { calculateSecurityScore, scoreToGrade } from '../../utils/security'
import type { SeverityCount } from '../../utils/security'

describe('calculateSecurityScore', () => {
  it('returns 100 for empty severity counts', () => {
    const severity: SeverityCount = { CRITICAL: 0, HIGH: 0, MEDIUM: 0, LOW: 0, UNKNOWN: 0 }
    expect(calculateSecurityScore(severity)).toBe(100)
  })

  it('deducts 15 per critical vulnerability', () => {
    const severity: SeverityCount = { CRITICAL: 1, HIGH: 0, MEDIUM: 0, LOW: 0, UNKNOWN: 0 }
    expect(calculateSecurityScore(severity)).toBe(85)
  })

  it('deducts 5 per high severity vulnerability', () => {
    const severity: SeverityCount = { CRITICAL: 0, HIGH: 2, MEDIUM: 0, LOW: 0, UNKNOWN: 0 }
    expect(calculateSecurityScore(severity)).toBe(90)
  })

  it('deducts 2 per medium severity vulnerability', () => {
    const severity: SeverityCount = { CRITICAL: 0, HIGH: 0, MEDIUM: 5, LOW: 0, UNKNOWN: 0 }
    expect(calculateSecurityScore(severity)).toBe(90)
  })

  it('deducts 0.5 per low severity vulnerability', () => {
    const severity: SeverityCount = { CRITICAL: 0, HIGH: 0, MEDIUM: 0, LOW: 10, UNKNOWN: 0 }
    expect(calculateSecurityScore(severity)).toBe(95)
  })

  it('clamps score to minimum 0', () => {
    const severity: SeverityCount = { CRITICAL: 10, HIGH: 10, MEDIUM: 10, LOW: 10, UNKNOWN: 0 }
    expect(calculateSecurityScore(severity)).toBe(0)
  })

  it('clamps score to maximum 100', () => {
    const severity: SeverityCount = { CRITICAL: -5, HIGH: 0, MEDIUM: 0, LOW: 0, UNKNOWN: 0 }
    expect(calculateSecurityScore(severity)).toBe(100)
  })

  it('handles mixed severity values correctly', () => {
    const severity: SeverityCount = { CRITICAL: 1, HIGH: 2, MEDIUM: 3, LOW: 4, UNKNOWN: 0 }
    // 100 - (1*15 + 2*5 + 3*2 + 4*0.5) = 100 - (15 + 10 + 6 + 2) = 100 - 33 = 67
    expect(calculateSecurityScore(severity)).toBe(67)
  })
})

describe('scoreToGrade', () => {
  it('returns A for scores >= 90', () => {
    expect(scoreToGrade(100)).toBe('A')
    expect(scoreToGrade(95)).toBe('A')
    expect(scoreToGrade(90)).toBe('A')
  })

  it('returns B for scores 70-89', () => {
    expect(scoreToGrade(89)).toBe('B')
    expect(scoreToGrade(75)).toBe('B')
    expect(scoreToGrade(70)).toBe('B')
  })

  it('returns C for scores 50-69', () => {
    expect(scoreToGrade(69)).toBe('C')
    expect(scoreToGrade(60)).toBe('C')
    expect(scoreToGrade(50)).toBe('C')
  })

  it('returns D for scores 30-49', () => {
    expect(scoreToGrade(49)).toBe('D')
    expect(scoreToGrade(40)).toBe('D')
    expect(scoreToGrade(30)).toBe('D')
  })

  it('returns E for scores < 30', () => {
    expect(scoreToGrade(29)).toBe('E')
    expect(scoreToGrade(10)).toBe('E')
    expect(scoreToGrade(0)).toBe('E')
  })

  it('handles boundary between B and C', () => {
    expect(scoreToGrade(70)).toBe('B')
    expect(scoreToGrade(69)).toBe('C')
  })
})
