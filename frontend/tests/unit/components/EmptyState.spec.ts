import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import EmptyState from '@/components/common/EmptyState.vue'

describe('EmptyState', () => {
  it('shows message and no button by default', () => {
    const w = mount(EmptyState, { props: { message: 'no data' } })
    expect(w.text()).toContain('no data')
    expect(w.find('button').exists()).toBe(false)
  })
  it('shows action button and emits action event', async () => {
    const w = mount(EmptyState, { props: { message: 'x', actionLabel: '재시도' } })
    expect(w.find('button').text()).toBe('재시도')
    await w.find('button').trigger('click')
    expect(w.emitted('action')).toBeTruthy()
  })
})
