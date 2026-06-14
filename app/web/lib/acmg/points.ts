// Pure mirror of app/backend/app/services/acmg_points_engine.py — the ONLY
// client-side recompute the ACMG-viz instruments are allowed (spec §5/§3). The
// engine is authoritative for `tier`, `posterior`, `net_points`, etc.; these
// functions exist so the SVG instruments (PosteriorGauge / EvidencePlane /
// PointWaterfall) can DRAW band geometry and self-check against the payload, and
// so the unit test pins us to the engine's exact anchor values. They recompute
// nothing the payload already carries — everything else reads the contract.
//
// Single clinical source: docs/report-acmg-viz/spec.md §3 + the vault
// [[acmg-criteria-and-points-reference]] / ADR-0022. Do not paraphrase the rules
// elsewhere; change them once, here, in lock-step with the backend engine.
//
// MIRRORED (byte-identical) to app/frontend/src/lib/acmg/points.ts, where the
// vitest suite lives (app/web has no test runner — same arrangement as
// lib/workbench/codon-layout.ts). Keep the two copies in sync.

import type { EamosComputedBenignCut, EamosComputedTier } from '@/lib/backend'

/** OddsPath base for one point of evidence (Tavtigian 2020). */
export const ODDS_PATH_BASE = 2.08
/** ACMG/AMP prior probability of pathogenicity (Tavtigian 2020). */
export const PRIOR = 0.1

/** OddsPath = 2.08^net (NOT 2.08^(net/8) — see spec §3). */
export function oddsPath(net: number): number {
  return Math.pow(ODDS_PATH_BASE, net)
}

/**
 * Posterior probability of pathogenicity from the net point score.
 * `posterior = (OddsPath·prior) / ((OddsPath − 1)·prior + 1)`, prior 0.10.
 * Anchors (unit-tested): net 0→10.0% · +6→90.0% · +9→98.8% · +10→99.4% ·
 * −1→5.1% · −7→0.1%.
 */
export function posterior(net: number): number {
  const op = oddsPath(net)
  return (op * PRIOR) / ((op - 1) * PRIOR + 1)
}

/**
 * Integer net cut-points (inclusive lower edges) per benign cut. Tavtigian-2020
 * default (ADR-0022): P ≥+10 · LP +6..+9 · VUS 0..+5 · LB −1..−6 · B ≤−7. The
 * `acgs_panel` exception (LB −1..−5 / B ≤−6) applies only via a VCEP overlay; the
 * FE follows whatever the engine reports in `benign_cut`.
 */
export function netBoundaries(benignCut: EamosComputedBenignCut): {
  pathogenic: number
  likelyPathogenic: number
  vus: number
  likelyBenign: number
} {
  return {
    pathogenic: 10, // ≥ +10
    likelyPathogenic: 6, // +6..+9
    vus: 0, // 0..+5
    likelyBenign: benignCut === 'acgs_panel' ? -5 : -6, // LB lower edge; B is below
  }
}

/**
 * Net-score → tier, mirroring the engine's pure-net mapping. NOTE: the engine's
 * *actual* tier can differ from this (BA1 hard override → Benign; discordance cap
 * → conflicting VUS) — always render `payload.tier` as the verdict; use this only
 * for band geometry and the self-check.
 */
export function tierByNet(net: number, benignCut: EamosComputedBenignCut): EamosComputedTier {
  const b = netBoundaries(benignCut)
  if (net >= b.pathogenic) return 'Pathogenic'
  if (net >= b.likelyPathogenic) return 'Likely Pathogenic'
  if (net >= b.vus) return 'VUS'
  if (net >= b.likelyBenign) return 'Likely Benign'
  return 'Benign'
}

export const TIER_ORDER: readonly EamosComputedTier[] = [
  'Benign',
  'Likely Benign',
  'VUS',
  'Likely Pathogenic',
  'Pathogenic',
]

/** `--cls-*` design tokens per tier (band fill / ink / edge). Reading-Room OKLCH
 *  ramp shared with the hero badge, the call cards, and §1–§3 so colour + word +
 *  glyph read consistently down the whole report. */
export interface TierTokens {
  band: string
  ink: string
  edge: string
}
const TIER_TOKEN_KEY: Record<EamosComputedTier, 'path' | 'lpath' | 'vus' | 'lben' | 'ben'> = {
  Pathogenic: 'path',
  'Likely Pathogenic': 'lpath',
  VUS: 'vus',
  'Likely Benign': 'lben',
  Benign: 'ben',
}
export function tierTokens(tier: EamosComputedTier): TierTokens {
  const k = TIER_TOKEN_KEY[tier]
  return { band: `var(--cls-${k}-bg)`, ink: `var(--cls-${k}-text)`, edge: `var(--cls-${k}-bdr)` }
}

/**
 * The five tier band segments in NET-POINTS space, for the posterior gauge and
 * the waterfall's net→tier axis (matches the vault `posterior-gauge.svg`
 * mockup). The gauge axis is linear in net points — points are linear in
 * log-odds — and the posterior value is labelled at each boundary (so the
 * "compress near 1.0" honesty lives in the labels, not in invisible slivers).
 * Band boundaries sit on the half-integer between net scores so an exact-boundary
 * marker (e.g. net +6) lands inside its own band. Returned low→high
 * (Benign → Pathogenic); `from`/`to` are net values within [domainMin, domainMax].
 */
export interface GaugeBand {
  tier: EamosComputedTier
  from: number
  to: number
}
export function gaugeBands(
  benignCut: EamosComputedBenignCut,
  domainMin = -10,
  domainMax = 13,
): GaugeBand[] {
  const b = netBoundaries(benignCut)
  return [
    { tier: 'Benign', from: domainMin, to: b.likelyBenign - 0.5 },
    { tier: 'Likely Benign', from: b.likelyBenign - 0.5, to: b.vus - 0.5 },
    { tier: 'VUS', from: b.vus - 0.5, to: b.likelyPathogenic - 0.5 },
    { tier: 'Likely Pathogenic', from: b.likelyPathogenic - 0.5, to: b.pathogenic - 0.5 },
    { tier: 'Pathogenic', from: b.pathogenic - 0.5, to: domainMax },
  ]
}

/** The four internal tier dividers (net value + posterior at that net), for
 *  labelling the gauge axis "P≈0.001 · 0.10 · 0.90 · 0.99" under the boundaries. */
export function gaugeBoundaries(
  benignCut: EamosComputedBenignCut,
): { net: number; posterior: number }[] {
  const b = netBoundaries(benignCut)
  return [b.likelyBenign - 0.5, b.vus - 0.5, b.likelyPathogenic - 0.5, b.pathogenic - 0.5].map(
    (net) => ({ net, posterior: posterior(net) }),
  )
}

/** Compact "Tavtigian-2020 points · OddsPath 2.08^net · prior 0.10" stamp string
 *  (spec accessibility bar — a formula stamp on every visual). */
export const POINTS_FORMULA_STAMP =
  'Tavtigian-2020 points · OddsPath 2.08^net · prior 0.10'
