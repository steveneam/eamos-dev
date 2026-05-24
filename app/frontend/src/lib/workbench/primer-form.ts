export interface PrimerConstraintInput {
  tmMin: string
  tmMax: string
  productMin: string
  productMax: string
}

export interface PrimerConstraintValues {
  tmMin: number
  tmMax: number
  productMin: number
  productMax: number
}

export type PrimerConstraintResult =
  | { ok: true; values: PrimerConstraintValues }
  | { ok: false; error: string }

const TM_MIN = 45
const TM_MAX = 75
const PRODUCT_MIN = 50
const PRODUCT_MAX = 2000

const ARMS_MARKERS = ['primer_mode_arms', 'arms']

function readNumber(value: string): number | null {
  const trimmed = value.trim()
  if (!trimmed) return null

  const parsed = Number(trimmed)
  return Number.isFinite(parsed) ? parsed : null
}

export function parsePrimerConstraints(
  input: PrimerConstraintInput,
): PrimerConstraintResult {
  const tmMin = readNumber(input.tmMin)
  const tmMax = readNumber(input.tmMax)
  const productMin = readNumber(input.productMin)
  const productMax = readNumber(input.productMax)

  if (
    tmMin === null ||
    tmMax === null ||
    productMin === null ||
    productMax === null
  ) {
    return {
      ok: false,
      error: 'Enter numeric values for Tm and product-size constraints.',
    }
  }

  if (tmMin < TM_MIN || tmMin > TM_MAX || tmMax < TM_MIN || tmMax > TM_MAX) {
    return {
      ok: false,
      error: `Tm constraints must be between ${TM_MIN} and ${TM_MAX} deg C.`,
    }
  }

  if (tmMin > tmMax) {
    return { ok: false, error: 'Tm min must be less than or equal to Tm max.' }
  }

  if (
    productMin < PRODUCT_MIN ||
    productMin > PRODUCT_MAX ||
    productMax < PRODUCT_MIN ||
    productMax > PRODUCT_MAX
  ) {
    return {
      ok: false,
      error: `Product-size constraints must be between ${PRODUCT_MIN} and ${PRODUCT_MAX} bp.`,
    }
  }

  if (!Number.isInteger(productMin) || !Number.isInteger(productMax)) {
    return {
      ok: false,
      error: 'Product-size constraints must be whole base-pair values.',
    }
  }

  if (productMin > productMax) {
    return {
      ok: false,
      error: 'Product min must be less than or equal to product max.',
    }
  }

  return {
    ok: true,
    values: { tmMin, tmMax, productMin, productMax },
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}

function stringifyDetail(detail: unknown): string | null {
  if (typeof detail === 'string') return detail

  if (Array.isArray(detail)) {
    const parts = detail.map(stringifyDetail).filter((part) => part !== null)
    return parts.length > 0 ? parts.join('; ') : null
  }

  if (isRecord(detail)) {
    const message = detail.msg ?? detail.message ?? detail.error
    if (typeof message !== 'string') return null

    const loc = detail.loc
    if (Array.isArray(loc) && loc.length > 0) {
      const field = loc[loc.length - 1]
      return typeof field === 'string' || typeof field === 'number'
        ? `${field}: ${message}`
        : message
    }

    return message
  }

  return null
}

function extractApiError(message: string): string | null {
  try {
    const body = JSON.parse(message) as unknown
    if (!isRecord(body)) return null
    return stringifyDetail(body.detail ?? body.message ?? body.error)
  } catch {
    return null
  }
}

export function primerErrorMessage(error: unknown): string {
  const fallback = 'Primer design failed'
  const message =
    error instanceof Error
      ? error.message
      : typeof error === 'string'
        ? error
        : fallback

  return extractApiError(message) ?? (message || fallback)
}

export function isArmsUnsupportedError(message: string): boolean {
  const normalized = message.toLowerCase()
  return (
    normalized.includes(ARMS_MARKERS[0]) ||
    new RegExp(`\\b${ARMS_MARKERS[1]}\\b`).test(normalized)
  )
}
