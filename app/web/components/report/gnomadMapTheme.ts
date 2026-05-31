// gnomAD world-map palette — the SINGLE source of truth for every map color (D8).
// Re-theme the entire map from this one file. See plans/gnomad-map-redesign.md.
//
// Hex literals only — never CSS var() tokens. These values are used as SVG
// `fill` / `stroke` presentation attributes and alpha-concatenated for glows
// (e.g. `${color}55`), and SVG presentation attributes do NOT resolve CSS custom
// properties. Where a value mirrors a design-system token it is noted so the two
// can be kept in sync by hand (globals.css owns the token; this owns the map).

// ── Neutral 3-tier-by-lightness base (D5) ──────────────────────────────────
// ocean (darkest, deep cool blue) · base land (lighter blue-grey) · tracked
// region with NO data for the queried variant (a flat grey that is deliberately
// distinct from base land, so "we cover this cohort, no signal here" stays
// legible and never reads as a real low-frequency value).
export const GNOMAD_MAP_SURFACE = {
  ocean: '#3a5d80', // lightened mid cool-blue — airier on the warm-white report page (was deep navy)
  baseLand: '#7e94a8', // lighter blue-grey, lifted with the ocean so land stays distinct above it
  noData: '#c6c6c6', // light flat NEUTRAL grey — tracked cohort, variant not observed (D5 tier 3); kept hueless so it reads as N/A and never clashes with the cool-blue ocean or blue-grey base land
  regionStroke: '#2c4b6a', // mid hairline between regions / land — definition without a harsh dark border on the lighter sea
  label: '#eef2f7', // cohort label on the map
  labelActive: '#ffffff', // cohort label when its region is hovered/active
} as const

// ── Threshold-anchored absolute-AF bands (LOCKED 2026-05-31; D4 reversed) ────
// Color by ABSOLUTE group allele frequency against fixed cutoffs — the same
// yardstick for every variant. Reversed vs the old relative ramp so HIGH AF =
// green (common, benign-leaning) and LOW AF = red, agreeing with the report-wide
// green=benign / red=pathogenic convention. ACMG anchors noted; raw group AF is
// the basis for now (per-group FAF95 is parked — BE-3). Ordered high → low.
// Consumed by T5's band-selection logic; bands are consulted ONLY for an
// OBSERVED frequency (AF > 0). Not observed → GNOMAD_MAP_SURFACE.noData (grey,
// never red), which is the honest "absent from this cohort" state.
export interface GnomadAfBand {
  id: 'common' | 'frequent' | 'uncommon' | 'rare'
  /** Inclusive lower bound on absolute group AF for this band. */
  min: number
  /** SVG fill hex. */
  color: string
  /** Legend label. */
  label: string
  /** ACMG frequency criterion this cutoff anchors, if any (benign BA1/BS1 at the
   *  common end; supporting-pathogenic PM2 at the rare end). */
  acmg: 'BA1' | 'BS1' | 'PM2' | null
}

export const GNOMAD_AF_BANDS: readonly GnomadAfBand[] = [
  { id: 'common', min: 0.05, color: '#1aa06d', label: '≥ 5%', acmg: 'BA1' }, // full green
  { id: 'frequent', min: 0.01, color: '#93d6b3', label: '1–5%', acmg: 'BS1' }, // lighter mint — clear daylight from the full BA1 green
  { id: 'uncommon', min: 0.001, color: '#e0a23a', label: '0.1–1%', acmg: null }, // amber (~--warn, lifted for the dark map)
  { id: 'rare', min: 0, color: '#dc5b4f', label: '< 0.1%', acmg: 'PM2' }, // red (~--danger, lifted); very-rare/absent leans pathogenic-supporting
] as const

// ── Hover / active cross-highlight (D7) ─────────────────────────────────────
// Double-stroke yellow halo (dark outer + light inner) so the highlight survives
// over any band fill — red, amber, or green. Reduced-motion is honored at the
// render layer (T7), not here.
export const GNOMAD_MAP_HOVER = {
  haloDark: '#2b2200', // outer stroke — dark, holds contrast over bright fills
  haloLight: '#fde047', // inner stroke — bright yellow (mirrors existing active accent)
} as const
