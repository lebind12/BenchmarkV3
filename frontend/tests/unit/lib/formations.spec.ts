import { describe, it, expect } from 'vitest'
import { resolveFormation } from '@/lib/formations'

describe('resolveFormation', () => {
  it('returns rows for 4-3-3', () => {
    expect(resolveFormation('4-3-3')).toEqual([1, 4, 3, 3])
  })
  it('returns rows for 4-2-3-1', () => {
    expect(resolveFormation('4-2-3-1')).toEqual([1, 4, 2, 3, 1])
  })
  it('falls back to 4-4-2 on null', () => {
    expect(resolveFormation(null)).toEqual([1, 4, 4, 2])
  })
  it('falls back on unknown', () => {
    expect(resolveFormation('99-99')).toEqual([1, 4, 4, 2])
  })
})
