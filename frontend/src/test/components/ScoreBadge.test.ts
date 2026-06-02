import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import ScoreBadge from '../../components/security/ScoreBadge.vue'

describe('ScoreBadge', () => {
  it('renders score and grade', () => {
    const wrapper = mount(ScoreBadge, {
      props: { score: 85, grade: 'B' },
    })

    expect(wrapper.text()).toContain('85')
    expect(wrapper.text()).toContain('B')
    expect(wrapper.text()).toContain('Скоринг')
  })

  it('applies correct color class for grade A', () => {
    const wrapper = mount(ScoreBadge, {
      props: { score: 95, grade: 'A' },
    })

    const badge = wrapper.find('.rounded-full')
    expect(badge.classes()).toContain('bg-emerald-500')
  })

  it('applies correct color class for grade C', () => {
    const wrapper = mount(ScoreBadge, {
      props: { score: 60, grade: 'C' },
    })

    const badge = wrapper.find('.rounded-full')
    expect(badge.classes()).toContain('bg-amber-400')
  })

  it('applies red color for grade E', () => {
    const wrapper = mount(ScoreBadge, {
      props: { score: 20, grade: 'E' },
    })

    const badge = wrapper.find('.rounded-full')
    expect(badge.classes()).toContain('bg-red-500')
  })

  it('falls back to E color for unknown grades', () => {
    const wrapper = mount(ScoreBadge, {
      props: { score: 50, grade: 'X' as string },
    })

    const badge = wrapper.find('.rounded-full')
    expect(badge.classes()).toContain('bg-red-500')
  })

  it('renders score as tabular-nums for alignment', () => {
    const wrapper = mount(ScoreBadge, {
      props: { score: 100, grade: 'A' },
    })

    const scoreEl = wrapper.find('.tabular-nums')
    expect(scoreEl.exists()).toBe(true)
    expect(scoreEl.text()).toBe('100')
  })
})
