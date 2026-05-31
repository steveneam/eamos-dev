// gnomAD world-map basemap generator (plans/gnomad-map-redesign.md T3).
// Build-time only. Turns Natural Earth country polygons (public-domain data,
// vendored via the `world-atlas` devDependency) into projected, land-clipped
// region path data for the /report gnomAD map. Nothing here ships to the client
// bundle: it emits a checked-in generated TS data asset (gnomadMapGeometry
// .generated.ts) that WorldFrequencyMap imports. See plans/gnomad-map-redesign.md
// (D1-D3).
//
// Run:  node app/web/scripts/build-gnomad-basemap.mjs
//   (or  npm run gen:gnomad-map  from app/web/)
//
// Pipeline (idempotent — same inputs always emit byte-identical output):
//   1. Load Natural Earth 50m topology (countries + land objects).
//   2. Group each country geometry into its gnomAD region via REGION_COUNTRIES
//      (numeric ISO id) / REGION_COUNTRIES_BY_NAME (id-less disputed features).
//   3. topojson `merge()` each region's members into one MultiPolygon, dissolving
//      internal borders — land-clipped by construction, so no ocean spill (D3).
//   4. Project every region + the full land outline through ONE shared
//      geoNaturalEarth1 fit to VIEW_BOX, so all layers share a coordinate system.
//   5. Emit GNOMAD_MAP_LAND (base-land layer) + GNOMAD_MAP_REGIONS (tracked
//      groups) as a generated TS module.

import { createRequire } from 'node:module'
import { readFileSync, writeFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, resolve, relative } from 'node:path'
import { feature, merge } from 'topojson-client'
import { geoNaturalEarth1, geoPath } from 'd3-geo'
import { geoStitch } from 'd3-geo-projection'
import {
  REGION_COUNTRIES,
  REGION_COUNTRIES_BY_NAME,
} from '../components/report/region-countries.ts'

const requireFrom = createRequire(import.meta.url)
const scriptDir = dirname(fileURLToPath(import.meta.url))

// ---- Config: the single place to retune the basemap build ----
// Natural Earth resolution. 110m is the standard d3 world-overview tier and the
// right call here: D2 is a no-zoom flagship map, and `merge()` dissolves internal
// borders so region accuracy comes from WHICH countries are grouped, not coastline
// detail. 110m keeps all 3 id-less disputed features (Kosovo / N. Cyprus /
// Somaliland), gives clean continental silhouettes, and emits a ~12x smaller asset
// than 50m (≈60KB vs ≈700KB of land path) — 50m's noise is unwanted at this scale.
const SOURCE = 'world-atlas/countries-110m.json'
// Nominal fit box for the projection; the EMITTED viewBox is then cropped tight
// to the inhabited-land bbox (below), so dead Pacific / Southern-Ocean space is
// dropped rather than letterboxed. T6 reads the emitted GNOMAD_MAP_VIEW_BOX.
const NOMINAL_BOX = { width: 2000, height: 857 }
// Tight-crop breathing room around the coastlines, as a fraction of content size.
// Slightly generous so New Zealand / the eastern Pacific edge isn't flush.
const PAD = 0.02
// Dropped from the base-land outline so the frame can crop tight to the real
// continental edges:
//  • Antarctica — no ancestry signal, only dead vertical space.
//  • Fiji — straddles the antimeridian, so geoStitch throws specks to BOTH the
//    far-left (empty mid-Pacific) and far-right (past New Zealand) edges,
//    distorting the frame. It's an invisible base-land speck at this scale, so
//    dropping it lets the frame sit on Alaska (W) ↔ New Zealand (E) — balanced.
const EXCLUDE_NAMES = new Set(['Antarctica', 'Fiji'])
// Path-coordinate precision (fractional digits). 1 → 0.1px at a 2000px viewBox =
// sub-pixel, visually lossless, and keeps the shipped asset small. This is the
// "simplify" step: full 50m point COUNT (smooth curves) at trimmed precision.
const DIGITS = 1
// Stable emit order for regions (matches the GnomadGeographicGroup union).
const GROUP_ORDER = ['afr', 'amr', 'eas', 'fin', 'mid', 'nfe', 'sas']
// Generated, checked-in TS asset the component imports.
const OUTPUT = resolve(scriptDir, '../components/report/gnomadMapGeometry.generated.ts')

function loadTopology() {
  return JSON.parse(readFileSync(requireFrom.resolve(SOURCE), 'utf8'))
}

function buildProjection(land) {
  // Fit the Natural Earth projection to the nominal box from the full land
  // outline so every region shares one coordinate system.
  return geoNaturalEarth1().fitSize([NOMINAL_BOX.width, NOMINAL_BOX.height], land)
}

// Bucket each country geometry into its gnomAD region. Returns the per-group
// geometry arrays plus diagnostics (matched-by-name + unmatched feature names)
// so the T3 review can confirm region coverage by eye.
function groupCountries(geometries) {
  const idToGroup = new Map()
  for (const [group, ids] of Object.entries(REGION_COUNTRIES)) {
    for (const id of ids) idToGroup.set(id, group)
  }

  const groups = {}
  const matchedByName = []
  const unmatched = []
  for (const geom of geometries) {
    const numericId = geom.id == null ? null : Number(geom.id)
    let group = numericId != null ? idToGroup.get(numericId) : undefined
    const name = geom.properties?.name
    if (!group && name && REGION_COUNTRIES_BY_NAME[name]) {
      group = REGION_COUNTRIES_BY_NAME[name]
      matchedByName.push(name)
    }
    if (!group) {
      unmatched.push(name ?? `id:${geom.id}`)
      continue
    }
    ;(groups[group] ??= []).push(geom)
  }
  return { groups, matchedByName, unmatched }
}

// France's Natural Earth geometry bundles French Guiana (and other Atlantic DOM
// specks). Dissolved into NFE, French Guiana renders as a stray European-coloured
// dot inside South America — geographically correct, but reads as a bug. Drop the
// western-hemisphere polygons (min longitude in the Americas) from France's
// MultiPolygon in place, so both the base land and the NFE region lose them.
function dropWesternHemispherePolygons(topology, geom) {
  if (!geom || geom.type !== 'MultiPolygon' || !Array.isArray(geom.arcs)) return
  const { coordinates } = feature(topology, geom).geometry
  const kept = []
  coordinates.forEach((polygon, index) => {
    const minLon = Math.min(...polygon.flat(1).map(([lon]) => lon))
    if (minLon > -20) kept.push(geom.arcs[index])
  })
  geom.arcs = kept
}

// d3 geoPath already rounds to `digits` fractional places; this is just a guard
// for older d3-geo that lacks .digits() (round each coordinate token).
function roundPath(d) {
  return d.replace(/-?\d+\.\d+/g, (m) => String(Math.round(Number(m) * 10 ** DIGITS) / 10 ** DIGITS))
}

function emit({ viewBox, landPath, regions }) {
  const regionLines = regions
    .map(
      (r) =>
        `  { group: '${r.group}', countries: ${r.countries}, labelX: ${r.labelX}, labelY: ${r.labelY}, d: ${JSON.stringify(r.d)} },`,
    )
    .join('\n')

  return `// AUTO-GENERATED by app/web/scripts/build-gnomad-basemap.mjs — DO NOT EDIT BY HAND.
// Regenerate:  npm run gen:gnomad-map   (from app/web/)
// Source: Natural Earth via the public-domain world-atlas \`${SOURCE}\` (no attribution
// required, D1). Region polygons are dissolved from member-country geometry and
// projected with geoNaturalEarth1 fit to VIEW_BOX, so they are land-clipped by
// construction (no ocean spill, D3). See plans/gnomad-map-redesign.md (T3).

import type { GnomadGeographicGroup } from './region-countries'

export interface GnomadMapRegion {
  /** gnomAD geographic genetic-ancestry group this dissolved region represents. */
  group: GnomadGeographicGroup
  /** Member country polygons merged into this region (provenance / sanity-check). */
  countries: number
  /** Projected SVG path data (geoNaturalEarth1, fit to GNOMAD_MAP_VIEW_BOX). */
  d: string
  /** Area-weighted projected centroid (same viewBox coords as \`d\`) — on-map label anchor. */
  labelX: number
  labelY: number
}

/** Coordinate space of every path below — cropped tight to inhabited land.
 *  Consume as the SVG viewBox: \`0 0 \${width} \${height}\`. */
export const GNOMAD_MAP_VIEW_BOX = { width: ${viewBox.width}, height: ${viewBox.height} } as const

/** Full land outline — the neutral base-land layer drawn under the regions (D5). */
export const GNOMAD_MAP_LAND: string =
  ${JSON.stringify(landPath)}

/** Dissolved, projected, land-clipped region polygons (tracked groups only). */
export const GNOMAD_MAP_REGIONS: GnomadMapRegion[] = [
${regionLines}
]
`
}

function main() {
  const topology = loadTopology()
  const allGeoms = topology.objects.countries.geometries
  // Strip French Guiana et al. from France before any merge (keeps it out of both
  // the base land and the NFE region). France = ISO numeric 250.
  const france = allGeoms.find((g) => Number(g.id) === 250)
  if (france) dropWesternHemispherePolygons(topology, france)
  // Base land = every inhabited country dissolved (Antarctica excluded). geoStitch
  // repairs polygons that wrap the antimeridian (Russia/Fiji) before projection.
  const inhabited = allGeoms.filter((g) => !EXCLUDE_NAMES.has(g.properties?.name))
  const baseLand = geoStitch(merge(topology, inhabited))

  const projection = buildProjection(baseLand)
  const path = geoPath(projection)
  if (typeof path.digits === 'function') path.digits(DIGITS)

  // Tight-crop: shift the projection so the inhabited-land bbox sits at the origin
  // with a small pad, then emit that bbox as the viewBox — drops the dead Pacific /
  // Southern-Ocean margin instead of letterboxing the whole globe.
  const [[x0, y0], [x1, y1]] = path.bounds(baseLand)
  const padX = (x1 - x0) * PAD
  const padY = (y1 - y0) * PAD
  const [tx, ty] = projection.translate()
  projection.translate([tx - x0 + padX, ty - y0 + padY])
  const viewBox = {
    width: Math.ceil(x1 - x0 + 2 * padX),
    height: Math.ceil(y1 - y0 + 2 * padY),
  }

  const { groups, matchedByName, unmatched } = groupCountries(inhabited)

  const landPath = roundPath(path(baseLand) ?? '')
  const regions = []
  const round1 = (n) => Math.round(n * 10 ** DIGITS) / 10 ** DIGITS
  for (const group of GROUP_ORDER) {
    const members = groups[group]
    if (!members?.length) continue
    // merge() dissolves shared borders between member countries into one
    // MultiPolygon — the region edge is built FROM coastlines, so it can never
    // spill into the ocean.
    const merged = merge(topology, members)
    const d = roundPath(path(merged) ?? '')
    // Area-weighted projected centroid → a stable build-time on-map label anchor,
    // in the same cropped viewBox coords as `d`. T6 draws the group code here.
    const [cx, cy] = path.centroid(merged)
    regions.push({ group, countries: members.length, d, labelX: round1(cx), labelY: round1(cy) })
  }

  writeFileSync(OUTPUT, emit({ viewBox, landPath, regions }), 'utf8')

  console.log('[gnomad-basemap] generated (T3)')
  console.log(`  source            ${SOURCE}`)
  console.log(`  inhabited land    ${inhabited.length} features (Antarctica excluded)`)
  console.log(`  viewBox (tight)   ${viewBox.width} x ${viewBox.height}`)
  console.log(`  matched by name   ${matchedByName.length ? matchedByName.join(', ') : '(none)'}`)
  console.log(`  regions emitted   ${regions.length}/${GROUP_ORDER.length}`)
  for (const r of regions) {
    console.log(`    ${r.group}  ${String(r.countries).padStart(2)} countries  ${r.d.length} path chars  label ${r.labelX},${r.labelY}`)
  }
  console.log(`  base land         ${landPath.length} path chars`)
  console.log(`  output            ${relative(resolve(scriptDir, '../..'), OUTPUT).replace(/\\/g, '/')}`)
  console.log(`  unmatched land    ${unmatched.length} features (base land — render uncolored)`)
}

main()
