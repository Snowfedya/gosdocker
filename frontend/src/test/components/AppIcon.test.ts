import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import AppIcon from '../../components/AppIcon.vue'

describe('AppIcon', () => {
  it('renders an SVG element', () => {
    const wrapper = mount(AppIcon, {
      props: { name: 'home' },
    })

    expect(wrapper.find('svg').exists()).toBe(true)
  })

  it('renders with default class when no custom class provided', () => {
    const wrapper = mount(AppIcon, {
      props: { name: 'home' },
    })

    const svg = wrapper.find('svg')
    expect(svg.classes()).toContain('w-5')
    expect(svg.classes()).toContain('h-5')
  })

  it('uses custom class when provided', () => {
    const wrapper = mount(AppIcon, {
      props: { name: 'home', class: 'w-8 h-8 text-red-500' },
    })

    const svg = wrapper.find('svg')
    expect(svg.classes()).toContain('w-8')
    expect(svg.classes()).toContain('h-8')
    expect(svg.classes()).toContain('text-red-500')
  })

  it('renders catalog icon with correct SVG paths', () => {
    const wrapper = mount(AppIcon, {
      props: { name: 'catalog' },
    })

    expect(wrapper.find('svg').html()).toContain('M4 4h6v6')
  })

  it('renders close icon with X paths', () => {
    const wrapper = mount(AppIcon, {
      props: { name: 'close' },
    })

    expect(wrapper.find('svg').html()).toContain('M6 18L18 6')
  })

  it('renders empty SVG for unknown icon names', () => {
    const wrapper = mount(AppIcon, {
      props: { name: 'nonexistent-icon' },
    })

    const svg = wrapper.find('svg')
    expect(svg.exists()).toBe(true)
    // Should not contain any path data
    expect(svg.find('path').exists()).toBe(false)
  })

  it('renders each known icon name without error', () => {
    const icons = [
      'catalog', 'registry', 'constructor', 'stacks', 'download',
      'settings', 'search', 'check', 'check-circle', 'close',
      'arrow-right', 'arrow-down', 'document', 'document-text',
      'code', 'external-link', 'shield', 'globe', 'database',
      'folder', 'chart', 'home', 'warning', 'info', 'port',
      'key', 'refresh', 'menu', 'sun', 'moon', 'spinner',
      'clock', 'user', 'heart', 'star', 'cube', 'layers',
      'server', 'github',
    ]

    icons.forEach((name) => {
      const wrapper = mount(AppIcon, { props: { name } })
      expect(wrapper.find('svg').exists()).toBe(true)
    })
  })
})
