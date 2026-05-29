// Shared ACMG classification → frozen-ramp token resolver.
//
// Single source of truth for mapping a classification string to the
// design-system `--cls-*` tokens. Steven's mandate (2026-05-26):
// P=red, LP=red-orange, VUS=true yellow, LB=lime, B=green. Grey (--cls-na-*)
// is reserved for unresolved / conflicting / no-data / NA — never a tier, and
// it is the fallback for anything we cannot map.
//
// Consumed by ClassificationBadge (the pill) and MatrixTile (the overview
// card fill) so a tier always resolves to the same colour everywhere.

export interface ClassificationConfig {
  bg: string
  text: string
  border: string
  dot: string
}

export type ClassificationTierKey = 'path' | 'lpath' | 'vus' | 'lben' | 'ben' | 'na'

const PATHOGENIC: ClassificationConfig = { bg: 'var(--cls-path-bg)', text: 'var(--cls-path-text)', border: 'var(--cls-path-bdr)', dot: 'var(--cls-path-dot)' }
const LIKELY_PATHOGENIC: ClassificationConfig = { bg: 'var(--cls-lpath-bg)', text: 'var(--cls-lpath-text)', border: 'var(--cls-lpath-bdr)', dot: 'var(--cls-lpath-dot)' }
const VUS: ClassificationConfig = { bg: 'var(--cls-vus-bg)', text: 'var(--cls-vus-text)', border: 'var(--cls-vus-bdr)', dot: 'var(--cls-vus-dot)' }
const LIKELY_BENIGN: ClassificationConfig = { bg: 'var(--cls-lben-bg)', text: 'var(--cls-lben-text)', border: 'var(--cls-lben-bdr)', dot: 'var(--cls-lben-dot)' }
const BENIGN: ClassificationConfig = { bg: 'var(--cls-ben-bg)', text: 'var(--cls-ben-text)', border: 'var(--cls-ben-bdr)', dot: 'var(--cls-ben-dot)' }
export const NA_CONFIG: ClassificationConfig = { bg: 'var(--cls-na-bg)', text: 'var(--cls-na-text)', border: 'var(--cls-na-bdr)', dot: 'var(--cls-na-dot)' }

const CONFIGS: Record<string, ClassificationConfig> = {
  'pathogenic': PATHOGENIC,
  'likely pathogenic': LIKELY_PATHOGENIC,
  'vus': VUS,
  'uncertain significance': VUS,
  'uncertain_significance': VUS,
  'likely benign': LIKELY_BENIGN,
  'benign': BENIGN,
  // Explicit non-tiers → grey, not a verdict colour.
  'conflicting interpretations of pathogenicity': NA_CONFIG,
  'conflicting': NA_CONFIG,
  'not provided': NA_CONFIG,
  'no classification': NA_CONFIG,
  'unknown': NA_CONFIG,
}

/** Resolve a classification string to its ramp config. Unknown / unmapped
 *  classifications fall back to grey-NA, never to a tier. */
export function resolveClassificationConfig(classification: string): ClassificationConfig {
  return CONFIGS[classification.trim().toLowerCase()] ?? NA_CONFIG
}

/** True when the classification maps to a real tier (not grey-NA). Lets
 *  callers decide whether to apply verdict colour at all. */
export function hasClassificationTier(classification: string): boolean {
  const cfg = CONFIGS[classification.trim().toLowerCase()]
  return Boolean(cfg) && cfg !== NA_CONFIG
}
