import { describe, expect, it } from 'vitest'
import { CRISPR_TIDE_SAMPLE } from './crispr-tide-sample'

describe('CRISPR_TIDE_SAMPLE', () => {
  it('is observed-only so the UI does not imply a repair predictor is running', () => {
    expect(CRISPR_TIDE_SAMPLE.predicted_available).toBe(false)
    expect(CRISPR_TIDE_SAMPLE.spectrum.every((bin) => bin.predicted == null)).toBe(
      true,
    )
  })
})
