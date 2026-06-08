# Report body — inter-section consistency & rhythm sweep

**Scope:** `/report` body below the hero — `app/web/components/report/**` section blocks + the `ReportClient.tsx` scaffold. Excluded: `VariantHeader.tsx` (hero), `StickyVariantRibbon.tsx` (ribbon), and HGVS-in-mono (changed separately to Inter this session).

**Bottom line:** the report is heavily and well designed. Sections are uniform `<Card>` shells at a single 14px gap; the in-card "inset sub-panel" idiom is ~90% consistent. Findings are the last 10%: a few one-off spacing values, one undefined-token bug, one label bypassing the canonical kicker. Surgical unifications only — no redesign.

## Surface map (render order, from `ReportClient.tsx` → `ReportBody`)
Body = single `flex flex-col gap-3.5` (14px) column. Each numbered section = a `<Card number title meta actions>` shell (`components/ui/Card.tsx`: header `16px 24px`, body `px-6 py-5`, radius 14, `--elev-1`, `0.5px var(--line)`, title 18px Spectral). Sub-blocks inside = "inset sub-panels" (`bg-soft` + `0.5px var(--line)` + `--r-md` + `.eamos-kicker` header).

| # | Section | Role |
|---|---|---|
| — | CallCardsGrid | 4 coloured verdict cards |
| 1 | Clinical evidence | ExpertPanel → ClinVar → Mave → ACMG fold |
| 2 | In-silico predictions | CompositeVerdictBar + CalibratedInSilicoTable → LoF → EamosAcmgClassifier |
| 3 | gnomAD population frequency | AfThermometer → PopulationFrequencySection |
| 4 | Gene & locus context | ReportGeneViewer → ProteinTrack → MolecularContextBlock |
| 5 | Disease & curated variants | DiseaseSection → CuratedVariants → AssociatedConditions → GeneDiseaseBlock |
| 6 | Publication literature | PubMedSection |
| 7 | Active trials & therapies | TrialsSection |
| 8 | AI evidence summary | AIStack |

## Findings + status (this session)

| Fix | Finding | Spec | Status |
|---|---|---|---|
| 1 | Inset sub-panel `marginTop` drift (Mave 16 vs peers 18) → 2px stutter in §1 stack | `MaveFunctionalBlock.tsx` `marginTop: 16`→`18` | ✅ DONE |
| 2 | Inset sub-panel horizontal padding drift (§3/§6 = `14px 18px`, others `14px 16px`) | `AfThermometer.tsx` + `PublicationsCallout.tsx` `padding '14px 18px'`→`'14px 16px'` | ✅ DONE |
| 3 | **Undefined `--ink-1` token** (scale is `--ink`,`--ink-2..5`) → silent colour fallback in §1 met-chip + §2 engine name | `ExpertPanelSection.tsx:27` + `CalibratedInSilicoTable.tsx:428` `var(--ink-1)`→`var(--ink)` | ✅ DONE (real bug) |
| 5 | DiseaseSection field-label hand-rolled (10.5/600) bypasses canonical `.eamos-kicker` (10.5/700) | `DiseaseSection.tsx` → `<div className="eamos-kicker mb-1">` | ✅ DONE |
| 6 | Legacy `--teal-faint` (v1 BACKWARD-COMPAT) on active v2 surfaces | `MolecularContextBlock.tsx:205` + `ProteinTrack.tsx:232/299` `--teal-faint`→`--teal-tint` | ✅ DONE |
| 4 | Inner inset-panel `gap` drift (10/12/16) | Collapse to two steps: 10 (dense) / 14 (roomy). ExpertPanel 16→14, GeneDiseaseBlock 12→14 | ⏸ DEFERRED (most subjective; low value) |

## Flagged — needs Steven approval (NOT auto-applied)
1. **CallCardsGrid radius (10) vs §-Card radius (14)** — probably intentional hierarchy (summary chips vs full sections). Unifying is a deliberate visual call.
2. **Promote inset-panel geometry to a real `--report-subpanel-*` token set** (gap/pad/radius) so it can't drift again — durable, adds 3 `:root` tokens.
3. **Consolidate §3's two "Non-geographic cohorts" headers** into one sub-component — a refactor beyond a rhythm pass.

## Don't-touch (intentional)
- AfThermometer/PublicationsCallout `marginBottom/marginTop: 14` — correct first/last-child offsets (distinct from the inter-panel gap; only horizontal padding touched).
- CallCardsGrid `marginTop:12 / minHeight:158 / radius 10` — distinct summary surface.
- EamosAcmgClassifier / LossOfFunctionBlock mock tints on `--cls-*` — intentional under mock-everything-unwired (`.eamos-mock` present).
- PopulationFrequencySection fixed-height inspector slots — deliberate anti-jitter geometry.
