import { describe, expect, it } from 'vitest'
import {
  isArmsUnsupportedError,
  parsePrimerConstraints,
  primerErrorMessage,
} from './primer-form'

describe('parsePrimerConstraints', () => {
  it('accepts trimmed numeric strings and decimal Tm values', () => {
    const result = parsePrimerConstraints({
      tmMin: ' 58.5 ',
      tmMax: '62',
      productMin: '300',
      productMax: '700',
    })

    expect(result.ok).toBe(true)
    if (result.ok) {
      expect(result.values).toEqual({
        tmMin: 58.5,
        tmMax: 62,
        productMin: 300,
        productMax: 700,
      })
    }
  })

  it('rejects blank and non-numeric fields before the request is sent', () => {
    expect(
      parsePrimerConstraints({
        tmMin: '',
        tmMax: '62',
        productMin: '300',
        productMax: '700',
      }),
    ).toEqual({
      ok: false,
      error: 'Enter numeric values for Tm and product-size constraints.',
    })

    expect(
      parsePrimerConstraints({
        tmMin: 'abc',
        tmMax: '62',
        productMin: '300',
        productMax: '700',
      }).ok,
    ).toBe(false)
  })

  it('rejects inverted Tm and product-size windows', () => {
    expect(
      parsePrimerConstraints({
        tmMin: '64',
        tmMax: '62',
        productMin: '300',
        productMax: '700',
      }),
    ).toEqual({
      ok: false,
      error: 'Tm min must be less than or equal to Tm max.',
    })

    expect(
      parsePrimerConstraints({
        tmMin: '58',
        tmMax: '62',
        productMin: '900',
        productMax: '700',
      }),
    ).toEqual({
      ok: false,
      error: 'Product min must be less than or equal to product max.',
    })
  })

  it('rejects out-of-range and fractional product-size constraints', () => {
    expect(
      parsePrimerConstraints({
        tmMin: '44',
        tmMax: '62',
        productMin: '300',
        productMax: '700',
      }).ok,
    ).toBe(false)

    expect(
      parsePrimerConstraints({
        tmMin: '58',
        tmMax: '62',
        productMin: '300.5',
        productMax: '700',
      }),
    ).toEqual({
      ok: false,
      error: 'Product-size constraints must be whole base-pair values.',
    })
  })
})

describe('primerErrorMessage', () => {
  it('extracts FastAPI detail strings', () => {
    expect(
      primerErrorMessage(
        new Error(JSON.stringify({ detail: 'primer_mode_arms is not implemented' })),
      ),
    ).toBe('primer_mode_arms is not implemented')
  })

  it('formats FastAPI validation detail arrays', () => {
    expect(
      primerErrorMessage(
        new Error(
          JSON.stringify({
            detail: [{ loc: ['body', 'tm_min'], msg: 'Input should be greater than 45' }],
          }),
        ),
      ),
    ).toBe('tm_min: Input should be greater than 45')
  })

  it('detects ARMS unsupported messages after formatting', () => {
    const message = primerErrorMessage(
      new Error(JSON.stringify({ detail: 'primer_mode_arms is not implemented' })),
    )

    expect(isArmsUnsupportedError(message)).toBe(true)
    expect(isArmsUnsupportedError('This request harms no constraints')).toBe(false)
  })
})
