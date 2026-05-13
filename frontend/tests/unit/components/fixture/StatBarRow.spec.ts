import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import StatBarRow from '@/components/fixture/tabs/StatBarRow.vue'

describe('StatBarRow', () => {
  it('renders bar widths proportional to home/away', () => {
    const w = mount(StatBarRow, {
      props: { label: '점유율', home: 60, away: 40, unit: '%' },
    })
    const home = w.find('[data-testid=stat-bar-home]').attributes('style') ?? ''
    const away = w.find('[data-testid=stat-bar-away]').attributes('style') ?? ''
    expect(home).toContain('60%')
    expect(away).toContain('40%')
  })

  it('renders "—" for NULL values', () => {
    const w = mount(StatBarRow, {
      props: { label: '패스 정확도', home: null, away: 82, unit: '%' },
    })
    expect(w.text()).toContain('—')
    expect(w.text()).toContain('82%')
  })
})
