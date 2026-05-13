import { describe, expect, it } from 'vitest'
import { kstTime, relativeFromNow } from '@/lib/format/datetime'

describe('kstTime', () => {
  it('renders KST time HH:MM', () => {
    // 2026-05-14T10:00:00Z = 19:00 KST
    expect(kstTime('2026-05-14T10:00:00Z')).toBe('19:00')
  })
  it('returns empty for invalid input', () => {
    expect(kstTime('not-a-date')).toBe('')
  })
})

describe('relativeFromNow', () => {
  const now = new Date('2026-05-14T10:00:00Z')
  it('< 60s = 방금 전', () => {
    expect(relativeFromNow('2026-05-14T09:59:30Z', now)).toBe('방금 전')
  })
  it('minutes', () => {
    expect(relativeFromNow('2026-05-14T09:45:00Z', now)).toBe('15분 전')
  })
  it('hours', () => {
    expect(relativeFromNow('2026-05-14T07:00:00Z', now)).toBe('3시간 전')
  })
  it('days', () => {
    expect(relativeFromNow('2026-05-12T10:00:00Z', now)).toBe('2일 전')
  })
})
