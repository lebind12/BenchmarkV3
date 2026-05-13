import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import PanelScroll from '@/components/common/PanelScroll.vue'

describe('PanelScroll', () => {
  it('renders inner scroll container with panel-scroll class', () => {
    const w = mount(PanelScroll, { slots: { default: '<p>hi</p>' } })
    expect(w.find('[data-testid="panel-scroll"]').classes()).toContain('panel-scroll')
    expect(w.html()).toContain('hi')
  })
  it('renders fade overlay by default', () => {
    const w = mount(PanelScroll)
    expect(w.find('[data-testid="panel-scroll-fade"]').exists()).toBe(true)
  })
  it('omits fade when fade=false', () => {
    const w = mount(PanelScroll, { props: { fade: false } })
    expect(w.find('[data-testid="panel-scroll-fade"]').exists()).toBe(false)
  })
})
