import { describe, expect, test } from 'vitest'
import { describeStandardizedValue, standardize } from './normalization'

describe('research normalization', () => {
  test('standardizes against the reference population with population standard deviation', () => {
    const result = standardize([10, 20, 30], 30)
    expect(result.mean).toBe(20)
    expect(result.sd).toBeCloseTo(8.1649658)
    expect(result.z).toBeCloseTo(1.2247448)
  })

  test('keeps raw value and percentile beside the z-score', () => {
    expect(describeStandardizedValue([10, 20, 30, 40], 30)).toEqual({
      raw: 30,
      percentile: 75,
      z: expect.any(Number),
      mean: 25,
      sd: expect.any(Number),
    })
  })

  test('uses z=0 for constant reference data instead of inventing separation', () => {
    expect(standardize([4, 4, 4], 4).z).toBe(0)
  })
})
