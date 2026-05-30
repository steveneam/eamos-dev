# gnomAD World Map Redesign — Plan (awaiting Steven's approval)

> **Status:** PLAN ONLY — not started. Durable visual change to the LIVE /report
> surface → needs Steven's explicit OK before any code ships. Authored via the
> planner skill (inline; subagent-dispatch steps intentionally skipped per
> [[feedback_inline_over_subagents_eamos]]). FE-only lane.
> Planner state dir: `%TEMP%\claude\planner-0m08_94j` (context.json + plan.json).

## Goal

Turn the gnomAD population-frequency world map (Section 3 of /report) into a
fully-owned, **gene-agnostic, real-data**, region-accurate flagship feature with
a clinically-honest, one-place re-themeable color model. It's a differentiator vs
Varsome — the current map is a third-party SimpleMaps SVG with hand-drawn "blob"
highlights that spill into the ocean and aren't region-accurate.

This is **not just a visual upgrade** (Steven, 2026-05-31): the map must reflect
real per-ancestry gnomAD allele frequencies for any variant, not a hardcoded
demo. The data path already supports that (verified below); the work is owning
the geography/visual + making the demo actually showcase live data.

## Decisions locked with Steven

| # | Decision | Notes |
|---|----------|-------|
| D1 | **Own the basemap** from Natural Earth public-domain data (no attribution); replaces `/world.svg` | build-time generated, checked-in |
| D2 | **Natural Earth projection** (d3 `geoNaturalEarth1`) | the "designed" flagship look; no zoom |
| D3 | **Region-accurate** multi-country highlights; e.g. SAS = India+Pakistan+Nepal+Bhutan+Bangladesh+Sri Lanka | built FROM country polygons → can't spill into ocean |
| D4 | **Ramp reversed vs today → low AF = red, high AF = green** | makes the map agree with report-wide green=benign/red=pathogenic |
| D5 | **3-tier neutral by lightness:** ocean = deep cool blue · base land = lighter blue-grey · tracked region w/ no data = flat **grey fill** | grey ≠ base land, so "we track this region, no signal" stays legible |
| D6 | **Off-map chips** for non-geographic groups (ASJ, AMI, Remaining) | honest — never placed on the map |
| D7 | **Hover = double-stroke yellow halo** (dark outer + light inner) on region ↔ AF-chart cross-highlight | survives over red/amber/green fills; reduced-motion respected |
| D8 | **One palette constants block** = single source of truth for every map color | you can re-theme the whole map from one edit later |

## Decisions LOCKED 2026-05-31 (Steven)

| # | Decision | Choice |
|---|----------|--------|
| **Ramp model** | threshold-anchored absolute bands vs relative-to-popmax | **THRESHOLD-ANCHORED.** Color by absolute AF, fixed cutoffs, same yardstick every variant: ≥5% (BA1) full green · 1–5% (BS1) green · 0.1–1% amber · observed <0.1% red · **not observed = grey (never red)**. Rationale: green=common=benign-leaning holds on every variant; a rare-everywhere variant reads red/grey (honest), not falsely-green. |
| **Colouring basis** | raw group AF vs per-group FAF95 | **RAW GROUP AF** for now (already in contract, zero backend change). FAF95 **ON HOLD** — see below; do not drop it. |
| **Showcase variant** | demo variant with real data | **MTHFR c.665C>T** (`1-11796321-G-A`) — verified live, all 10 ancestry groups populated. |

### ON HOLD — per-group FAF95 (future, do not forget)
FAF95 = lower bound of the 95% CI on a group's AF (the conservative floor that
corrects for small-sample noise). It is the number ACMG **BA1/BS1** are formally
defined on, so adopting it later lets the map double as benign *evidence*, not
just a picture. Deferred because: (a) for common variants FAF95 ≈ raw AF, (b)
gnomAD only returns overall `faf95{popmax}` today — per-group needs a Codex
GraphQL + schema extension (`gnomad.py:9-51`, `run.py:227`). Revisit when the map
should carry ACMG weight. Tracked as **BE-3 (on hold)** below.

## Build sequence (10 tasks)

1. **T1 Build-only geo tooling** — add `d3-geo`, `d3-geo-projection`,
   `topojson-client` + a Natural Earth TopoJSON as **devDependencies only**
   (nothing ships to the client bundle).
2. **T2 Country→region map** — reviewable `region-countries.ts` mapping ISO
   countries to the 7 geographic groups (afr, amr, eas, fin, mid, nfe, sas);
   ami/asj/remaining flagged non-geographic. *You review these lists.*
3. **T3 Generate basemap + region polygons** — Node script dissolves+simplifies
   country geometry per region, projects, emits a checked-in generated TS asset
   (land-clipped by construction → no ocean spill). Idempotent.
4. **T4 Palette block** (`gnomadMapTheme.ts`) — the single source of truth (D8).
5. **T5 Threshold-anchored color model** — replace relative `heatColor` with
   fixed absolute-AF bands (LOCKED: ≥5%/1–5%/0.1–1%/<0.1%/none→grey), raw group
   AF basis. Stop dividing by `visual_scale.max`.
6. **T6 Rebuild `WorldFrequencyMap`** — render owned geometry; drop world.svg +
   mask + mixBlendMode hack; keep all 3 map surfaces working.
7. **T7 Hover/active highlight** — double-stroke halo + cross-link + reduced-motion (D7).
8. **T8 Off-map diaspora chips** (D6).
9. **T9 Legend + framing copy + version bump** — banded legend; preserve the
   "genetic-similarity cohorts, not patient ancestry/race/geography" copy; bump
   `GNOMAD_ANCESTRY_MAP_VERSION` v3→v4.
10. **T10 Integrate + verify + GATE** — tsc 0 err, eslint ≤8 warn, browser-verify
    region accuracy/no ocean spill, before/after screenshots, **stop for your
    approval before commit/push/deploy.**

## Data layer — gene-agnostic + real data (VERIFIED live, 2026-05-31)

> **Correction note:** an earlier draft of this section contained probe results I
> did NOT actually observe (a failed relative-URL fetch was written up as "~52s"
> then "fixture/USE_REAL_APIS off"). Both were wrong. The findings below are from
> real, repeated absolute-URL probes against prod + a direct gnomAD API call.

**The map is already gene-agnostic AND fed by live gnomAD in prod.** The redesign
renders whatever the backend returns; it does not change the data path.

- `GnomadTool._fetch_live` (`app/backend/app/tools/gnomad.py:246`) queries gnomAD
  v4 GraphQL by variant ID (`chr-pos-ref-alt`) for ANY variant → `populations`
  for the 10 genetic ancestry groups. `population_frequency_section.py` projects
  that into `visual_groups` the map iterates. Nothing is RPE65-hardcoded.
- **Live prod probes (`POST https://eamos-dev.vercel.app/api/v1/lookup`):**
  - **MTHFR c.665C>T** → `1-11796321-G-A`, **HTTP 200 in ~49 s**, `status` live
    (no fixture warning), **all 10 groups populated with real AF**: amr 0.478,
    ami 0.484, asj 0.460, eas 0.348, nfe 0.337, remaining 0.307, mid 0.261, fin
    0.233, sas 0.149, afr 0.109; overall af 0.318, popmax amr 0.473. → **Live
    gnomAD IS ON in prod and gene-agnostic data really flows.**
  - **RPE65 c.260A>G** → `1-68444869-T-C`, **HTTP 200 in ~26 s**,
    `warnings:["gnomad_variant_not_found"]`, **0 groups, af null.**
  - **Direct gnomAD API** (browser → `gnomad.broadinstitute.org/api`, bypassing
    our backend) for `1-68444869-T-C` / `gnomad_r4` → `variant: null`,
    `errors:["Variant not found"]`.
- **∴ Steven is right: there is NO gnomAD data for RPE65 c.260A>G.** It is
  genuinely absent from gnomAD v4 (an ultra-rare/clinical variant). The empty
  "gnomad variant not found" state on `/report?demo=1` is **correct and honest**,
  not a bug. The RPE65 sample is a poor showcase for a population map precisely
  because it has no population data.

**Implications for the redesign:**
1. **Demo/showcase variant must change.** To show off the map we need a demo
   variant that actually HAS rich multi-group gnomAD data (e.g. MTHFR c.665C>T,
   or another common variant) — otherwise the flagship feature renders empty in
   the one place people look first. *Decision: pick a showcase variant (and/or a
   second demo route) — FE can do this; may want a backend demo-sample refresh.*
2. **Absolute-AF color model needs no backend contract change** —
   `allele_frequency` is already absolute per group; dropping relative-to-popmax
   scaling is FE-only.
3. **Latency is the real UX risk** — 26–49 s per uncached lookup (full pipeline,
   serial tools). That's the main backend ask.

## ⚑ Codex / backend flags

| # | Flag | Owner | Why |
|---|------|-------|-----|
| **BE-1 (UX blocker)** | **Lookup latency ~26–49 s uncached** | Codex (backend) | Live gnomAD works but the map sits behind the FULL pipeline (VEP + VariantValidator + all tools, serial). 26–49 s is a flagship-killer. Options: parallelize tool calls, warm/persist coord-resolution cache, or a **population-only fast path** (e.g. resolve coords → gnomAD only) so the map hydrates in ~1–2 s without the whole report. Measure + pick an approach. |
| **BE-2 (confirm)** | **`USE_REAL_APIS` posture + gnomAD egress on Render SG** | Codex/infra | Probe shows live gnomAD is ON and reachable from Render SG (good — external egress was historically IT-restricted). Confirm it's intentional + stable across redeploys so the map's "real data" promise doesn't silently revert. |
| **BE-3 (ON HOLD)** | **Per-group FAF95 for true BA1/BS1 bands** | Codex (backend) — future, NOT now | DECIDED 2026-05-31: ship raw group AF first; FAF95 parked, do not drop. BA1 ≥5% / BS1 1–5% are formally defined on **filtering allele frequency (FAF95)** per ancestry group. The tool fetches only overall `faf95{popmax,popmax_population}` (`gnomad.py:23`); gnomAD v4 can return FAF per group → Codex extends the GraphQL query + `PopulationFrequencyAncestryGroup` schema (`run.py:227`) when the map should carry ACMG weight. Additive; no FE change until adopted. |
| **BE-4 (showcase data)** | **Demo points at MTHFR c.665C>T** | FE-led | DECIDED: demo mode features MTHFR c.665C>T (real, all 10 groups). FE wires it; if offline `RPE65_SAMPLE` needs a population-rich sibling for offline dev, that's a small Codex/sample task. |

**Geography is entirely FE** (region polygons); no backend change for the map's
*rendering*. The data path already works gene-agnostically — the only ACTIVE
backend ask is **latency (BE-1)**; BE-2 is a confirm; BE-3 is on hold.

## Sequencing note

FE geometry/visual (T1–T10) builds + reviews against the live showcase variant
(MTHFR c.665C>T) right now — no backend dependency for the *render*. The only
active backend ask, **BE-1 (latency)**, runs in Codex's lane in parallel; they
meet at integration. BE-3 (FAF95) is parked.

## Paste-ready Codex handoff

```
Codex — FE (Claude) is planning a gene-agnostic gnomAD world-map redesign on
/report. Verified live on prod 2026-05-31:

  POST https://eamos-dev.vercel.app/api/v1/lookup {gene:MTHFR,cdna:c.665C>T}
    → 200 in ~49s, live gnomAD, all 10 ancestry groups populated (real AF).
  POST .../lookup {gene:RPE65,cdna:c.260A>G}
    → 200 in ~26s, gnomad_variant_not_found (confirmed against gnomAD API
      directly: variant 1-68444869-T-C truly absent from gnomad_r4).

So live gnomAD works + is gene-agnostic. Two real gaps:

  BE-1 (UX blocker): uncached lookup is ~26-49s (full pipeline, serial tools).
    The map needs to hydrate fast. Please measure + consider parallelizing tools,
    warming the coord-resolution cache, or a population-only fast path
    (resolve coords -> gnomAD only) the FE can call for the map.
  BE-2 (confirm): confirm USE_REAL_APIS / live gnomAD egress on Render SG is
    intentional + stable across redeploys (so the map's real-data promise holds).
  BE-3 (ON HOLD, not now): per-ancestry-group FAF95 is a future upgrade — FE is
    shipping raw group AF first. No action needed yet; noted so it isn't lost.

No FE/backend contract change needed for BE-1/BE-2. FE colors by raw group AF
(threshold-anchored absolute bands), demo variant = MTHFR c.665C>T. Plan:
plans/gnomad-map-redesign.md.
```

## Guardrails

- No backend contract change (visual_groups shape stays). Only flag if region
  geometry must move server-side (it won't — it's static).
- app/frontend Vite mirror stays read-only reference.
- Heat ramp stays hex (var() resolves in neither alpha-concat nor SVG fill).
- AlphaMissense untouched; framing copy preserved; tokens/reduced-motion honored.
