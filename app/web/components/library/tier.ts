// ClassificationTier ↔ colour bridge — the ONE place that reconciles the two
// forms in the codebase: backend `ClassificationTier` is underscore-form
// ('likely_pathogenic'), but the shared resolveClassificationConfig() keys on
// space-form ClinVar strings ('likely pathogenic'). Passing a raw tier straight
// in silently greys out the two multi-word tiers — so saved cards, nearby
// variants, and the related lanes all colour through here instead.
import type { ClassificationTier } from '@/lib/backend'
import { resolveClassificationConfig, NA_CONFIG, type ClassificationConfig } from '@/lib/classification'

const TIER_LABEL: Record<ClassificationTier, string> = {
  pathogenic: 'pathogenic',
  likely_pathogenic: 'likely pathogenic',
  vus: 'vus',
  likely_benign: 'likely benign',
  benign: 'benign',
}

const TIER_SHORT: Record<ClassificationTier, string> = {
  pathogenic: 'P',
  likely_pathogenic: 'LP',
  vus: 'VUS',
  likely_benign: 'LB',
  benign: 'B',
}

const TIER_DOT_SUFFIX: Record<ClassificationTier, string> = {
  pathogenic: 'path',
  likely_pathogenic: 'lpath',
  vus: 'vus',
  likely_benign: 'lben',
  benign: 'ben',
}

/** The `.lib-dot` modifier class for a tier (`cls-path` … `cls-na`). The CSS
 *  maps each to its `--cls-*-dot` colour; unknown → neutral `cls-na`. */
export function tierDotClass(tier?: ClassificationTier | null): string {
  return tier ? `cls-${TIER_DOT_SUFFIX[tier]}` : 'cls-na'
}

/** Colour config (bg/text/border/dot) for a stored or nearby tier; neutral
 *  --cls-na when the tier is unknown. */
export function tierConfig(tier?: ClassificationTier | null): ClassificationConfig {
  if (!tier) return NA_CONFIG
  return resolveClassificationConfig(TIER_LABEL[tier])
}

/** Short ACMG label (P/LP/VUS/LB/B) for a tier, or null when unknown. */
export function tierShort(tier?: ClassificationTier | null): string | null {
  return tier ? TIER_SHORT[tier] : null
}

/** Normalize a free ClinVar-ish verdict string (e.g. "Likely pathogenic",
 *  "Uncertain significance", "VUS") → a ClassificationTier, or undefined when
 *  it isn't one of the five tiers (conflicting / not provided / unknown). */
export function tierFromText(s?: string | null): ClassificationTier | undefined {
  if (!s) return undefined
  switch (s.trim().toLowerCase()) {
    case 'pathogenic':
      return 'pathogenic'
    case 'likely pathogenic':
    case 'likely_pathogenic':
      return 'likely_pathogenic'
    case 'vus':
    case 'uncertain significance':
    case 'uncertain_significance':
    case 'variant of uncertain significance':
      return 'vus'
    case 'likely benign':
    case 'likely_benign':
      return 'likely_benign'
    case 'benign':
      return 'benign'
    default:
      return undefined
  }
}
