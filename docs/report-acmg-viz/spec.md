# Report ACMG Visualization Wave + Points Engine — Spec

**Status:** draft for review (interview answers folded in 2026-06-14)
**Owners:** Claude (frontend, `app/web`) · Codex (backend, `app/backend`)
**Surfaces touched:** `/report` only (CallCardsGrid summary + §3 Clinical Consensus / Card 4)
**Source of truth (never duplicate):** the clinical contract lives in the vault — this spec *references* it, it does not restate the math.

---

## 0. What this is (one paragraph)

EAMOS will become **the only variant report that *draws the classification decision*** — an Evidence Plane, a Point Waterfall, and a Posterior Gauge that render the ACMG/AMP points calculation itself, plus a four-axis **Evidence Fingerprint** atop the report. These are the production builds of the clinically-grounded mockups in `Wiki/assets/`. Every one of them consumes a single new backend object — `eamos_computed_classification` — produced by a **Tavtigian-2020 points engine that does not exist yet**. That engine is the linchpin and the natural Claude↔Codex seam: Codex builds the engine + contract; Claude builds the SVG instruments against a frozen mock of that contract; we converge when the contract is populated for real.

---

## 1. Scope (per interview, 2026-06-14)

| Decision | Answer | Consequence |
|---|---|---|
| **Breadth** | Viz wave **+ its backend engine**; reconcile the rest of build-ledger §2 against what's already built | §9 reconciliation; the broader predictor/exome/phenopacket waves are **not** specced here |
| **Verdict model** | **Points engine = primary EAMOS advisory**; the existing Richards-2015 categorical classifier (`EamosAcmgClassifier.tsx`) is **demoted into an audit/expandable detail**, not removed | The curated ClinGen→ClinVar aggregation stays the *precedence* call (unchanged); EAMOS now has **one** headline advisory verdict, not two |
| **v1 cut** | **Hero set + Evidence Fingerprint** | A1 Evidence Plane + A2 Point Waterfall + A3 Posterior Gauge + A4 confidence channel (§3/Card 4) **and** B5 Evidence Fingerprint + posterior chip (CallCardsGrid). Everything else = fast-follow |
| **Drag/what-if card** | **Fast-follow** | Static hero visuals + engine contract prove out first; the draggable Explore card ([[interactive-classification-card]]) lands next |

**v1 (this spec's commitment):** A1, A2, A3, A4, B5 + the points engine + the contract.
**Fast-follow (specced here, built next):** the interactive Explore card; B1 Predictor Forest (§2); B7 Predictor beeswarm (§2, needs a ClinVar P/B reference-set precompute); B2 o/e Constraint Forest (§1/§4); B3 conservation bullet; B4 ancestry strip; B6 plain-language dotplot (§8).

---

## 2. What already exists (reconnaissance — do not rebuild)

**Frontend (`app/web/components/report/`, Next 16 / React 19, Reading Room):**
- `ScoreScale.tsx` — shared `ScaleTrack` + `ScorePin` primitive (used by `CalibratedInSilicoTable`, `AfThermometer`). **This is the seed for the shared `<EvidenceBar>`** — extend it, don't fork.
- `EamosAcmgClassifier.tsx` — current EAMOS auto-verdict = **Richards-2015 categorical count rules** (no points, no posterior). → to be **demoted to audit detail**.
- `CallCardsGrid.tsx`, `CompositeVerdictBar.tsx`, `AcmgGrid.tsx`, `AcmgCriteriaFold.tsx`, `CalibratedInSilicoTable.tsx` — the §3/§2 surfaces these instruments slot into.

**Backend (`app/backend/app/`):**
- `services/clinical_consensus.py` — ClinGen→ClinVar **source aggregation** (the precedence verdict). **Not touched by this spec.**
- `services/computational_calibration.py` — Pejaver/Walker/Bergquist **calibrated bands** for PP3/BP4. **Reused** by the engine.
- `services/pvs1_nmd.py` — PVS1/NMD decision support (the `nmdetective_pvs1` ledger item, `runtime_wired`). **Reused** as the PVS1 strength tree.
- `services/build_ledger.py` — runtime readiness ledger. Confirms: **no points-engine item exists**; the `acmg_classifier` item == `clinical_consensus + computational_calibration`.
- `schemas/run.py` — where the new `eamos_computed_classification` block is added.

**The gap (what to build):** the points combiner that fuses PVS1-tree + calibrated bands + gnomAD/ClinVar evidence into `{net_points, posterior, per_criterion[]}` — and the five SVG instruments that draw it.

---

## 3. The frozen data contract (the coordination artifact)

This is the **single seam** between Codex and Claude. Codex authors it in `schemas/run.py`; Claude builds against a mock fixture of the same shape. **Freeze this before either side writes code.** It reconciles [[eamos-acmg-classifier-tool]] (Transparency output) with [[interactive-classification-card]] (consumed contract).

```ts
interface EamosComputedClassification {
  acmg_version_pin: {                 // emitted on every output (engine spec §In-scope)
    framework: string;                // "Richards-2015 + Tavtigian-2020 points"
    pvs1_revision: string;            // "Abou-Tayoun-2018"
    pp3_calibration: string;          // "Pejaver-2022"
    vcep_id?: string;                 // present only when a VCEP overlay applied
  };
  net_points: number;                 // ΣP − ΣB (seed for the puck / waterfall total)
  sum_pathogenic: number;             // ΣP — Evidence-Plane Y
  sum_benign: number;                 // ΣB — Evidence-Plane X
  tier: "Pathogenic" | "Likely Pathogenic" | "VUS" | "Likely Benign" | "Benign";
  conflict: { is_conflicting: boolean; reason?: string };  // discordance cap → forced VUS
  ba1_override: boolean;              // BA1 hard benign override fired (short-circuits the sum)
  posterior: number;                  // 0..1; OddsPath = 2.08^net, prior 0.10 (see below)
  benign_cut: "tavtigian_2020" | "acgs_panel";             // which ADR-0022 cut applied
  per_criterion: Array<{
    code: string;                     // "PVS1", "PM2", ...
    direction: "pathogenic" | "benign";
    triggered: boolean;               // untriggered codes still emitted (audit completeness)
    applied_strength: "very_strong" | "strong" | "moderate" | "supporting" | null;
    points: number;                   // signed APPLIED points (waterfall bar size)
    evidence_value?: string | number;
    threshold?: string | number;
    source_db?: string;               // "gnomAD v4", "ClinVar", "AlphaMissense", ...
    source_version?: string;
    svi_reference?: string;
  }>;
}
```

**Non-negotiable clinical rules** (binding on engine AND visuals — single source [[acmg-criteria-and-points-reference]] §1–§5; do not paraphrase them here):
- **Posterior:** `OddsPath = 2.08^net` → `posterior = (OddsPath·0.10)/((OddsPath−1)·0.10+1)`. **Not** `2.08^(net/8)`. Verified anchors the FE unit tests must hit: net `0→10.0%` · `+6→90.0%` · `+9→98.8%` · `+10→99.4%` · `−1→5.1%` · `−7→0.1%`.
- **Tier cuts (ADR 0022 default Tavtigian-2020):** P ≥+10 · LP +6..+9 · VUS 0..+5 · LB −1..−6 · B ≤−7. `acgs_panel` exception (LB −1..−5 / B ≤−6) applies **only** via VCEP overlay; the FE reads `benign_cut` and follows it.
- **Variable strength is per-application** — `applied_strength`/`points`, never a fixed code→points map.
- **BA1 = hard override** (not a summand); **discordance cap → conflicting VUS** regardless of net; mutually-exclusive pairs never co-fire; PP5/BP6 demoted.

The Evidence Plane needs `conflict` (hatched marker) and `ba1_override` (legend note); the gauge needs `posterior`; the waterfall needs `per_criterion[].points` + `applied_strength`. **All of it comes from the engine — the FE recomputes nothing except the two pure mirror functions in §5.**

---

## 4. Backend spec — Codex (`app/backend`)

**New module:** `app/backend/app/services/acmg_points_engine.py` — a **separate advisory** object; **must not modify** `clinical_consensus.py`.

**Build order (engine spec [[eamos-acmg-classifier-tool]] Build plan, v1 subset):**
1. **Points core.** `{code → applied_strength} → points → ΣP/ΣB → net → BA1 override → discordance cap → tier(net, benign_cut) → posterior(net)`. Emit the §3 contract + `acmg_version_pin`. Unit-test Tavtigian-2020 worked examples (`1 VStrong + 1 Strong = +12 → P`; `2 Mod + 1 Supp = +5 → VUS`; `PVS1 + PM2_Supporting = +9 → LP`).
2. **Wire existing evidence.** Feed `computational_calibration.py` bands (PP3/BP4) + `pvs1_nmd.py` strength tree (strength-modulated PVS1, not flat Very-Strong) + gnomAD-popmax/ClinVar for PM2/BA1/BS1/BS2/PM1/PM4/PM5/PP2/BP1/BP3/BP7.
3. **Serialize.** Add `eamos_computed_classification` to `schemas/run.py`; populate it in the lookup/report path so `/report` receives it. Keep it **distinct** from `clinical_consensus`.

**v1 boundary:** coverage expansion (auto PS3/BS3 from literature, PM3/BP2 phasing), the VCEP overlay, the AI narration layer, and the benchmark harness are **out of v1** (engine spec phases 3/5/6) — mark them "not assessed" in `per_criterion`. The LLM never activates a criterion or decides a tier (guardrail stays).

**Fast-follow (Codex):** ClinVar ≥2★ P/B **reference-set precompute** per predictor (the load-bearing build-time asset for the B7 beeswarm — [[variant-report-visualizations]] B7); calibrated `position`/CI surfacing for the B1 forest.

**Tests:** the 10 must-get-right rules from [[acmg-criteria-and-points-reference]] §5 as cases; posterior anchor values; BA1 short-circuit; discordance→VUS; mutually-exclusive pairs reject.

---

## 5. Frontend spec — Claude (`app/web`)

**New components** in `app/web/components/report/`:
- `EvidencePlane.tsx` (A1) — ΣB→x, ΣP→y; anti-diagonal P−B tier bands; clean marker vs **hatched conflict marker** (`conflict.is_conflicting`); BA1 legend note (`ba1_override`).
- `PointWaterfall.tsx` (A2) — one signed bar per triggered criterion = **applied** points, labelled `PVS1_Strong +4` / `PM2_Supporting +1`; sums to net against tier ticks; renders as a `<table>` for SR for free.
- `PosteriorGauge.tsx` (A3) — 5 ClinGen bands on the **true logistic scale** (unequal widths; LP/P compress near 1.0); marker at `posterior`.
- `EvidenceFingerprint.tsx` (B5) — four ticks (rarity · predictors · conservation · constraint) on one shared benign↔pathogenic baseline + "N of 4 agree"; **must not look like the ACMG verdict**.
- `ConfidenceChannel.tsx` (A4) — small evidence-quality channel (review-status stars + "n criteria, max strength Strong") beside the verdict. May fold into an existing header rather than a standalone file.

**Shared primitives** in `app/web/lib/acmg/`:
- `points.ts` — `tierByNet(net, benign_cut)` + `posterior(net)`, **pure mirror functions** of the engine. Unit-tested to the §3 anchor values + ADR-0022 band edges. These are the *only* client recompute; everything else reads the payload.
- Extend `ScoreScale.tsx` into the shared `<EvidenceBar>` reused by A2/B5 (and later B1/B2/B3).

**Integration edits:**
- `EamosAcmgClassifier.tsx` → reworked: the **points verdict is the headline EAMOS advisory** (badge + Evidence Plane + Waterfall + Gauge); the Richards categorical output moves **into an expandable audit detail** ("legacy categorical view"). Curated ClinGen→ClinVar stays the precedence call above it.
- `CallCardsGrid.tsx` → mount `EvidenceFingerprint` + posterior chip + confidence channel at the summary.

**Accessibility / theming (production bar, [[design-invariants]]):** every chart `role="img"` + full-sentence `aria-label` + a visually-hidden `<table>` with the real data; **position is the primary encoding** (colour only reinforces; tiers also print the net value/glyph); `prefers-reduced-motion` → static; Reading-Room OKLCH `--cls-*` tokens (no raw hex); a **data-source/formula stamp** on every visual ("Tavtigian-2020 points · OddsPath 2.08^net · prior 0.10").

**Build order:** `points.ts` + tests → A3 gauge (smallest, proves the contract) → A1 plane → A2 waterfall → A4 channel → B5 fingerprint → wire into `EamosAcmgClassifier` + `CallCardsGrid`.

---

## 6. Page / section placement

| Surface (file) | Instruments | Tier |
|---|---|---|
| **CallCardsGrid** (top summary) | B5 Evidence Fingerprint + A3 posterior chip + A4 confidence channel | **v1** |
| **§3 Clinical Consensus / Card 4** (`EamosAcmgClassifier.tsx`) | A1 Evidence Plane + A2 Point Waterfall + A3 Posterior Gauge; Richards → audit detail | **v1** |
| §3 / Card 4 | Interactive Explore (drag what-if) card | fast-follow |
| **§2 In-silico** (`CalibratedInSilicoTable.tsx`) | B1 Predictor Forest, B3 conservation bullet, B7 beeswarm | fast-follow |
| **§1 Population / §4 Gene** | B2 o/e Constraint Forest, B4 ancestry strip | fast-follow |
| §8 AI summary | B6 plain-language quantile dotplot | fast-follow |
| §5–§7 | **none** — list/table is correct; over-vizzing is gloss | — |

Splice / protein-domain / 3D structure are a **different domain** → [[predictor-visuals-build-spec]], not this spec.

---

## 7. Value & impact on what we already have

**Value (the wedge):** the field (VarSome, Franklin, ClinGen VCI, GeneBe, QCI) stops at a criteria checklist + a coloured badge + a 1-D bar. **Nobody draws the decision or fuses the four axes.** Premise-correct claims only (Part F): "first to *draw* the classification decision," "first *draggable* point," "first four-axis *fingerprint*" — **not** "first interactive ACMG" (VarSome already toggles rules).

**Impact / risks to current surfaces:**
- **Third-verdict confusion — resolved by decision:** points engine becomes the single EAMOS advisory; Richards demoted to audit; curated aggregation stays precedence. One headline advisory, clearly labelled "EAMOS-computed · advisory," never overriding curated.
- **Mock-first posture (project norm):** the hero visuals render on a `.eamos-mock` `eamos_computed_classification` fixture until the engine populates it live — consistent with §2 in-silico today. No live behaviour changes until Codex ships the engine and we flip the fixture for the real payload.
- **Engine↔viz drift:** prevented structurally — both cite [[acmg-criteria-and-points-reference]]; the FE `points.ts` mirror functions are unit-tested to the engine's exact anchor values; the FE recomputes nothing else.
- **Clinical-accuracy contract is binding** ([[variant-report-visualizations]] §0): the Evidence Plane must show conflict as a hatched marker (not a "net 0" dot), BA1 as an override (not a summand), variable strength in the waterfall. Getting this wrong is a credibility risk, not a cosmetic one.
- **Drag card mislead risk** — deferred to fast-follow with hard guardrails (never mutates the verdict; ephemeral; visually distinct hypothetical).

---

## 8. Claude ↔ Codex split & sequencing

```
Step 0  (joint)   Freeze the §3 contract in schemas/run.py + a matching FE mock fixture.   ← gate
Step 1  Codex     acmg_points_engine.py core + posterior + tier + version pin + tests.
        Claude    lib/acmg/points.ts + tests; A3 gauge against the mock fixture.
Step 2  Codex     Wire computational_calibration + pvs1_nmd + gnomAD/ClinVar; populate the block.
        Claude    A1 plane, A2 waterfall, A4 channel, B5 fingerprint; wire into Card 4 + CallCardsGrid.
Step 3  (joint)   Swap FE off the mock onto the live payload; browser-verify (0 console errors;
                  plane/waterfall/gauge agree with the engine for every integer net).
Fast-follow       Codex: ClinVar P/B reference precompute (B7) + forest calibration (B1).
                  Claude: Explore drag card; B1/B2/B3/B4/B6/B7.
```

**Coordination rules (per `agent_handoff/README.md`):** backend-led contract; explicit pathspecs only; `graphify update` is Codex's lane; LLM stays `mock`; no flag flips. The contract freeze (Step 0) is the one thing that must be agreed before parallel work starts.

---

## 9. Roadmap reconciliation — "some of it is already built/ready" (your ask)

Verified against `app/backend/app/services/build_ledger.py` (ground truth) vs the build-ledger doc:

| build-ledger §2 item | Code state (ledger) | Real blocker | Verdict |
|---|---|---|---|
| **AlphaMissense / ESM1b / CI-SpliceAI / CAPICE** | `runtime_wired=true`; serialization paths exist | **artifact materialization** (Render disk) — an operator step, not code | **Code-ready, data-unmaterialized.** Feeds B1/B7 — no new predictor *code* needed for the viz |
| **PVS1 / NMDetective-B** | `nmdetective_pvs1` wired (`pvs1_nmd.py`) | — | **Built** — reuse as the engine's PVS1 tree |
| **ClinGen eRepo + CSpec** | `clingen_local_adapter` `runtime_wired=true` (`ClinGenLocalStore` + operator CLI) | operator JSONL materialization | **More built than the doc claims** ("NOT downloaded" is stale — the local store + CLI now exist) |
| **MaveDB** | `runtime_wired=true` | CC0 import materialization + public-field review | Code-ready, unmaterialized |
| **Literature engine / PubMed local** | `runtime_wired=true` (EP-VLEx) | corpus materialization | Code-ready, unmaterialized; inert per memory |
| **AI gateway** | ledger `gateway_planned` / `runtime_wired=false`; code shipped but `LLM_PROVIDER=mock` | broker enable + de-ID/PHI review (operator) | **Shipped-but-inert** (ledger lags the shipped, gated code) |
| **EAMOS points-engine classifier** | **absent** | — | **Genuinely unbuilt — this spec** |
| **Report visualizations** | **absent** | — | **Genuinely unbuilt — this spec** |
| **Exome cascade / phenopackets / phenotype-congruence / OntoGPT** | not in the runtime ledger | not yet in `D:\eamos` | **Genuinely unbuilt + un-mirrored** (future waves) |

**Takeaway:** the predictor/data plumbing the viz consumes is largely **wired and waiting on operator materialization, not on code.** So the viz wave's true blockers are exactly two code builds — the **points engine** (Codex) and the **SVG instruments** (Claude) — plus one fast-follow precompute (ClinVar P/B reference set). The bigger backend waves (exome cascade, phenopackets, congruence) are real future work but **out of scope here**.

---

## 10. Open questions (carry into build)

1. **A4 confidence channel** — standalone component, or fold into the existing Card-4 header? (lean: fold, keep the card calm.)
2. **`acmg_version_pin` shape** — confirm the structured-object form above matches what Codex emits (engine-spec open question).
3. **PP3/BP4 anchor predictor** — AlphaMissense (CC-BY, ADR 0005) vs ESM1b — affects which calibrated band the engine feeds; doesn't change the FE contract.
4. **Splice PP3/BP4** — no commercial-safe SVI-calibrated splice tool; v1 may leave splice criteria "not assessed" (engine-spec open question).
5. **B5 Fingerprint data** — confirm the four axes (rarity/predictors/conservation/constraint) all have a value at report time on mock + live, or render "—" for missing (gnomAD `—`-for-no-data pattern).

---

## Source connections (vault — the linked context)

- **Governing FE spec:** [[variant-report-visualizations]] (Parts A/B/C/E/F) · asset manifest `Wiki/assets/README.md` + the SVG mockups + `acmg-explainer.html`.
- **Clinical single source (engine ↔ viz never drift):** [[acmg-criteria-and-points-reference]] · tier cuts [[0022-acmg-benign-cut-tavtigian-default-acgs-exception]].
- **Backend engine spec:** [[eamos-acmg-classifier-tool]] · decision [[0011-eamos-points-based-acmg-classifier]].
- **Fast-follow build contract:** [[interactive-classification-card]].
- **Economics / readiness:** [[build-ledger]] · runtime ledger [[backend-build-ledger-runtime]] (mirrored in `app/services/build_ledger.py`) · [[as-built-inventory]].
- **IA / theming:** [[0006-shipped-report-information-architecture]] · [[4-card-display]] · [[design-invariants]].
- **Boundary (not this spec):** splice/protein/3D → [[predictor-visuals-build-spec]].
</content>
</invoke>
