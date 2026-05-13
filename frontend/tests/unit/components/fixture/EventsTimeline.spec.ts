import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import EventsTimeline from '@/components/fixture/EventsTimeline.vue'
import match1 from '@/mocks/data/fixture-detail/match.1000001.json'
import events1 from '@/mocks/data/fixture-detail/events.1000001.json'
import type { MatchDetail, Slice, TimelineEvent } from '@/types/fixtureDetail'

describe('EventsTimeline', () => {
  const slice: Slice<TimelineEvent[]> = {
    status: 'ok',
    value: events1.events as unknown as TimelineEvent[],
    error: null,
  }

  it('renders home events in home column and away in away column', () => {
    const w = mount(EventsTimeline, {
      props: {
        match: match1 as unknown as MatchDetail,
        slice,
      },
    })
    const rows = w.findAll('.events-timeline__row')
    expect(rows.length).toBeGreaterThan(0)
    for (const r of rows) {
      const team = r.attributes('data-team')
      const homeCell = r.find('[data-side=home] button')
      const awayCell = r.find('[data-side=away] button')
      if (team === 'home') {
        expect(homeCell.exists()).toBe(true)
        expect(awayCell.exists()).toBe(false)
      } else {
        expect(awayCell.exists()).toBe(true)
        expect(homeCell.exists()).toBe(false)
      }
    }
  })

  it('exposes aria-label for column headers', () => {
    const w = mount(EventsTimeline, {
      props: {
        match: match1 as unknown as MatchDetail,
        slice,
      },
    })
    const head = w.find('header.events-timeline__head')
    expect(head.html()).toContain('aria-label="홈 이벤트"')
    expect(head.html()).toContain('aria-label="어웨이 이벤트"')
  })

  it('shows empty-NS placeholder when no events and status NS', () => {
    const w = mount(EventsTimeline, {
      props: {
        match: {
          ...(match1 as unknown as MatchDetail),
          status_short: 'NS',
        },
        slice: { status: 'ok', value: [], error: null },
      },
    })
    expect(w.find('[data-testid=events-empty-ns]').exists()).toBe(true)
  })
})
