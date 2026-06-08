# /report v3 — Hero, Call Cards & Dense Evidence/Data-Viz Design Audit

> Scout lane: `VariantHeader`, `CallCardsGrid`, `CompositeVerdictBar`, §1–§3 dense evidence + data-viz.
> Grounded in `DESIGN.md`, `app/web/app/globals.css`, `lib/classification.ts`.
> Skills used: **frontend-design** + **ui-ux-pro-max** (cited inline: bullet/gauge AAA pattern, heatmap legend rules, contrast 4.5:1, color-not-only, no-emoji-icons).
> _Persisted by main agent — scout's direct `.md` write was harness-blocked._

## 1. Snapshot

The evidence surface is dense and mostly token-disciplined — the body consistency pass already landed (`--ink` fixes, `--report-subpanel-*` geometry, `.eamos-kicker` normalisation), and the foundations are sound: `lib/classification.ts` is the single ramp source; `StackedCountBar`, `ProteinTrack`, and `EvidenceBar` all consume `--cls-*` tokens. But **the badge/chip/tier/scale vocabulary has drifted into ~five private dialects** — the canonical `ClassificationBadge` pill (radius-full, dot, uppercase, tracked) coexists with CallCards badges (radius 7, no dot, sentence-case), MAVE PS3/BS3 and LoF PVS1 chips (radius 999, no dot, no tracking), two Free/Pro tag styles, and two info-ⓘ affordances. The "where does this score sit on a graded benign↔pathogenic scale" idea is drawn **three incompatible ways** (continuous gradient + pin in §2; banded bullet bar in §3; segmented active-cell strip in §1). The most serious issues are honesty/a11y: white numerals on the light VUS/LB ramp dots fail contrast, the hero "1,204 views / 5 Jun 2026" reads as real behind one small chip, hardcoded `misOe`/`misZ` sit at full weight beside live LOEUF, and the §3 AF ramp is a *different* green→red than the rest of the report. Excellent bones; needs one badge/scale vocabulary + a mock-honesty sweep.

## 2. Findings

### P0 — bugs · invariant violations · mock-looks-real · a11y

**[P0] White count numerals fail contrast on light VUS / Likely-benign ramp dots** · `ui/StackedCountBar.tsx:111-123`
Every segment paints `color:'#fff'` numerals on `DOT_TOKEN[verdict]`. `--cls-vus-dot` is `oklch(80% 0.155 90)` and `--cls-lben-dot` is `oklch(71% 0.150 140)` (globals.css :94,:99) — white on 80%/71%-lightness yellow/lime is well under 4.5:1 (ui-ux-pro-max `color-contrast`, High). Used by the ClinVar submitter mix (`ClinVarBlock.tsx:132`) and composite verdict (`CompositeVerdictBar.tsx:55`); the count IS the data.
**Fix:** drop hardcoded `#fff`; choose label ink per segment from `--cls-{tier}-text` (a `TEXT_ON_DOT` map mirroring `DOT_TOKEN`). Path/LP/Ben keep white; VUS/LB → `--cls-vus-text`/`--cls-lben-text`.
**Why:** the only quantitative payload is unreadable on the two lightest tiers.

**[P0] Hero engagement metrics read as real data; only one small chip flags them** · `report/VariantHeader.tsx:180-190`
`<b>1,204</b> views` and `Updated <b>5 Jun 2026</b>` render in full ink/bold/tabular-nums, identical to every live number; the sole signal is a detached `preview` chip + `aria-label`. Violates globals.css :388-407 ("a placeholder metric never reads as a real number").
**Fix:** tag the *values*, not the row — wrap `1,204` and `5 Jun 2026` in `.eamos-mock` (or dim to `--ink-4`, drop bold), as `CalibratedInSilicoTable` tags placeholder rows. The `Updated` date should be live or absent, not invented.
**Why:** P0 mock-looks-real on the most-glanced element.

**[P0] §1 Card verdict accent is declared, passed, and silently dropped** · `ui/Card.tsx:27-46` · `ReportClient.tsx:725`
`CardProps.verdict` is documented ("3px frozen-ramp accent on the left border") and ReportClient passes `verdict={verdict}`, but the `Card` destructure (lines 38-46) omits `verdict` — never read, no accent renders. The intended left-rule tying §1 to the hero badge is dead.
**Fix:** consume `verdict`, resolve via `resolveClassificationConfig`, render a 3px left border in `cfg.dot` — or remove the prop + the pass-through (but the comment at `ReportClient.tsx:719` still promises it).
**Why:** a documented hierarchy cue is missing; the prop lies about behaviour.

**[P0] Hardcoded illustrative LOEUF/missense constraint at live-data weight** · `report/AfThermometer.tsx:300-346`
`misOe=0.94`, `misZ=1.86` (and LOEUF/pLI fallbacks `0.41`/`0.86`) render through the identical `ConstraintGauge` as live data, distinguished only by a small `Mock` chip. The Missense gauge's entire readout, pin, status word ("Not constrained"), and Z badge are fabricated yet visually identical to the live LoF gauge beside it.
**Fix:** when `mock`, also de-emphasise value text (`--ink-4`) + pin, and/or overlay the `.eamos-mock` hatch on the gauge track. Same for the `loeufMock` fallback.
**Why:** constraint numbers drive PM2/PP2 reasoning; a full-weight fabricated one is a clinical-honesty risk.

**[P0] §3 AF-thermometer ramp differs from the page classification ramp** · `report/gnomadMapTheme.ts:46-51` → `AfThermometer.tsx:211-213`
The AF band fills come from `GNOMAD_AF_BANDS` raw hex (`#1aa06d/#93d6b3/#e0a23a/#dc5b4f`, map-tuned for the dark SVG ocean) while the constraint gauges *directly below in the same component* use `--cls-*-dot` tokens (`AfThermometer.tsx:73-84`). One panel stacks two different green→red ramps; neither benign-green matches `--cls-ben-dot`.
**Fix:** render the thermometer *bar* (a report element, not the SVG map) from `--cls-*`: BA1→`--cls-ben-dot`, BS1→`--cls-lben-dot`, intermediate→`--cls-vus-dot`, PM2→`--cls-lpath-dot`. Keep raw `GNOMAD_AF_BANDS` for the actual SVG map fills only (where CSS vars can't resolve, per that file's header).
**Why:** the AF axis is the same benign↔pathogenic ramp; off-ramp hex breaks "colour means the same everywhere."

**[P0] Info-popover uses raw black shadow, banned by DESIGN** · `report/PopulationFrequencySection.tsx:1479`
`boxShadow:'0 10px 30px rgba(0,0,0,0.16)'` — ad-hoc shadow over pure black. DESIGN.md bans raw `box-shadow` (depth only via `--elev-*`) and pure black (use `--ink`).
**Fix:** `boxShadow:'var(--elev-3)'` (the `--ink`-based overlay token).
**Why:** invariant; the overlay reads heavier/cooler than the token system.

### P1 — inconsistency · hierarchy

**[P1] Five badge/chip dialects where there should be one** · Canonical `ui/ClassificationBadge.tsx:50-66` (radius-full, 6px dot, 11px uppercase tracked). Drifts: `CallCardsGrid.tsx:246-261` (radius 7, no dot, 10.5px 700, sentence-case); `MaveFunctionalBlock.tsx:73-84` (radius 999, no dot, 10px); `LossOfFunctionBlock.tsx:97-99` (radius 999, no dot, 12px); `EamosAcmgClassifier.tsx:106-123` (radius 999, *has* 8px dot, 13px); plus two Free/Pro renderings — `CalibratedInSilicoTable.tsx:367-388` `TierTag` (filled tinted pill) vs `LossOfFunctionBlock.tsx:39-51` `ToolTag` (bare coloured text).
**Fix:** one `<EvidenceChip>` primitive (radius, padding, optional dot, optional uppercase); route all verdict/strength/tier chips through it; standardise Free/Pro on `TierTag`'s filled-pill form. (Structural — 🟡.)
**Why:** clinician re-learns "what a coloured pill means" per section.

**[P1] Three incompatible "score-on-a-graded-scale" visualisations** · §2 `EvidenceBar` (`CalibratedInSilicoTable.tsx:260-329`: gradient bands + down-triangle pin); §3 `AfThermometer`/`ConstraintGauge` (`:208-250`,`:134-152`: banded bullet bar + triangle/haloed-line pin + threshold tick); §1 MAVE Brnich ladder (`MaveFunctionalBlock.tsx:109-137`: segmented strip + active-cell underline, no pin). All answer the same benign↔pathogenic placement question; ui-ux-pro-max bullet-chart (AAA) is the right shared idiom.
**Fix:** converge on bullet-bar-with-pin (the §3 thermometer is the strongest execution); MAVE ladder + §2 EvidenceBar share that geometry + pin glyph. (Structural — 🟡.)
**Why:** consistency is the core ask; one scale idiom on a dense page.

**[P1] Two different info-ⓘ affordances** · `PopulationFrequencySection.tsx:1451` uses a `ⓘ` unicode glyph in a pill button; `AfThermometer.tsx:35-64` `InfoHint` hand-builds a bordered italic "i" span — different shape, icon, and interaction (popover vs native `title`). The `ⓘ` is a font glyph (inconsistent cross-platform; DESIGN restricts iconography).
**Fix:** one `InfoHint`/`InfoPopover` primitive with one inline-SVG "i" mark — popover variant for rich content, hover for one-liners, same glyph.
**Why:** the help affordance should be one recognisable thing.

**[P1] `borderRadius:7` magic number breaks the radius scale** · `CallCardsGrid.tsx:253` (badges), `PopulationFrequencySection.tsx:334` (`TabButton`). Tokens are `--r-sm:6/--r-md:10/--r-lg:14` (globals.css :142-144); 7 is off-scale, only here.
**Fix:** `var(--r-sm)`. **Why:** token discipline.

**[P1] Call cards use radius 10, §-Cards radius 14 — two card geometries** · `CallCardsGrid.tsx:301,353` (radius 10, pad 15/16) vs `ui/Card.tsx:52,74` (`rounded-[14px]`, pad 16/24). They sit directly adjacent (`ReportClient.tsx:713`→`:721`).
**Fix:** one report-card radius, or make "tighter call-card tier" an explicit token (`--r-md` cards vs `--r-lg` sections), not 10-vs-14 drift. (Visual — 🟡.)
**Why:** adjacent cards with different corners read as accidental.

**[P1] CallCards label is Spectral 600; §-Card titles are Spectral 400** · `CallCardsGrid.tsx:230-241` (`--display`, 18px, 600) vs `ui/Card.tsx:136-137` (`font-normal` 400, 18px). DESIGN's serif authority comes from low weight (DESIGN.md :366); 600 Spectral is off-register and reads clotted at 18px.
**Fix:** Spectral 400 (match section titles), or if more rank is wanted use Inter 600 (sans) — don't bold the serif.
**Why:** off-register vs the §-headers beside it.

**[P1] `AcmgGrid` met-cells flatten all strengths to one red / one green** · `report/AcmgGrid.tsx:44-56` + `globals.css:680-683`. A met PVS1 (Very Strong) and met PP3 (Supporting) both render `.acmg-cell.met` (same `--cls-path-bg`) — strength, the thing a curator reads, is discarded.
**Fix:** modulate met-cell fill by strength band (Very-Strong/Strong→`--cls-path-*`; Moderate→mid; Supporting→`--cls-lpath-*`), mirroring `TIER_META` in `CalibratedInSilicoTable.tsx:138-146`.
**Why:** the most important attribute of a met criterion is invisible.

**[P1] MolecularContext and AfThermometer both render LOEUF/pLI, two ways** · `MolecularContextBlock.tsx:222-257` (dotted-underline mono `ChipRow`) vs `AfThermometer.tsx:317-331` (coloured `ConstraintGauge`). Both in §3/§4-adjacent cards (`ReportClient.tsx:842`→`:899`); the reader sees gene constraint twice with no "same datum" signal.
**Fix:** one home — the `ConstraintGauge` is stronger; `MolecularContextBlock` drops its duplicate LOEUF/pLI row, keeping only ClinGen dosage / CNVs / conservation. (IA — 🟡.)
**Why:** duplicated data in divergent dialects is the clearest drift symptom.

**[P1] Decorative hex gradient on the map panel** · `PopulationFrequencySection.tsx:390` — `linear-gradient(180deg,#f8fbfd,#f1f6f8)` is raw hex, off-palette, colour-on-colour. DESIGN.md :16 permits a gradient only as a ≤4% functional wash.
**Fix:** flat `var(--bg-soft)` (or `--bg-tint` wash). **Why:** invariant + dodges tokens.

### P2 — polish

**[P2] `FlagChip` uses ✓/✗/– text glyphs as status icons** · `LossOfFunctionBlock.tsx:63-72`. Glyphs render inconsistently; ✓/✗ lean on colour (ui-ux-pro-max `color-not-only`). **Fix:** small inline-SVG check/cross (reuse the `Star` SVG approach) or ensure the label text alone carries yes/no. Minor (label is explicit).

**[P2] `EvidenceBar` captions at 9–9.5px dip below the readable floor** · `CalibratedInSilicoTable.tsx:319-327`. DESIGN's smallest label is 10.5px; 9px mono on `--ink-5` is borderline. **Fix:** floor at 10px, endpoints `--ink-5`→`--ink-4`.

**[P2] `ProteinTrack` AM heatmap reuses the exact classification ramp** · `report/ProteinTrack.tsx:155-162,310`. Token-correct, but a continuous tolerance heatmap in the five discrete *verdict* colours risks "red heat band reads as Pathogenic call." ui-ux-pro-max heatmap guidance wants a labelled continuous intensity ramp distinct from categorical verdict colour + numeric legend ticks. **Fix:** continuous interpolated green→red ramp + 0/0.5/1 legend ticks. Low priority (hover gives values).

**[P2] `--report-subpanel-*` tokens cover outer panels but not the inner tiles** · inner tiles use ad-hoc `padding:'8px 10px'` (`AfThermometer.tsx:121`, `LossOfFunctionBlock.tsx:56`, `MaveFunctionalBlock.tsx:160`). **Fix:** add a `--report-tile-pad` token (or reuse `--report-subpanel-pad`).

**[P2] `EvidenceBar` pin and `AfThermometer` pin are near-identical, not shared** · `CalibratedInSilicoTable.tsx:300-316` vs `AfThermometer.tsx:217-249` (7px triangle + haloed line, line 12px vs 16px). **Fix:** extract `<ScorePin>`; folds into the converged scale-bar work (🟡).

## 3. 🟡 FLAGGED — needs Steven's OK (durable / structural / visual)

1. **Unified evidence-chip primitive** (P1 five-dialects) — one `<EvidenceChip>` re-routing CallCards / MAVE / LoF / Eamos-ACMG / Tier tags, built to the `ClassificationBadge` spec; Free/Pro standardised on `TierTag`'s filled pill.
2. **Converge the three score-scale visualisations** onto bullet-bar-with-pin (P1 + shared-pin P2) — touches §1 MAVE ladder, §2 EvidenceBar, §3 thermometer/gauge; visible redraw.
3. **Call-card geometry/type decision** (radius 10/pad 15-16/Spectral-600 vs §-Card 14/16-24/400) — align or make the tighter tier an explicit token.
4. **ACMG criterion-strength colouring in `AcmgGrid`** (P1) — changes how the 28-box grid reads in both §1 and the auto-classifier (shared component).
5. **De-duplicate gnomAD constraint** between `MolecularContextBlock` and `AfThermometer` (P1) — content/IA change.

## 4. Quick wins (token-only, safe now)

- `StackedCountBar.tsx:111` — `#fff` → per-tier `--cls-{tier}-text` map. **(P0)**
- `PopulationFrequencySection.tsx:1479` — `boxShadow:'var(--elev-3)'`. **(P0)**
- `PopulationFrequencySection.tsx:390` — `background:'var(--bg-soft)'`. **(P1)**
- `CallCardsGrid.tsx:253` & `PopulationFrequencySection.tsx:334` — `borderRadius:7` → `var(--r-sm)`. **(P1)**
- `VariantHeader.tsx:182-187` — wrap `1,204`/`5 Jun 2026` in `.eamos-mock` (or dim+unbold). **(P0)**
- `Card.tsx:38-46` — add `verdict` to the destructure + render the 3px `cfg.dot` left rule (or delete the prop + `ReportClient.tsx:725` pass). **(P0)**
- `CalibratedInSilicoTable.tsx:319-327` — `fontSize` 9/9.5 → 10, `--ink-5` → `--ink-4`. **(P2)**
- `AfThermometer.tsx:300-346` — when `mock`, value text + pin → `--ink-4`. **(P0, one component.)**

---

_Seam note: the rail/ribbon, gene/disease/pubs/trials sections, and the `PopulationFrequencySection` world-map internals were out of scope here (only its header/tab/thermometer/legend/popover chrome). The contrast P0 was verified numerically against the OKLCH lightness of the `--cls-*-dot` tokens (VUS L=80%, LB L=71% → white-text fail)._
