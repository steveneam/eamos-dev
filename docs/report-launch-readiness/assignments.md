# /report Launch-Readiness — Assignments

Status: Draft for review (Claude, 2026-06-23). Source: a read-only launch
audit of the report surface this session (FE `app/web/components/report/**` +
backend report/lookup path) plus Claude's own verification. Severity calls are
Claude's, not the raw audit's — the audit over-weighted some items (e.g. GDPR
framing on a missing timestamp); those are de-rated here.

Lanes: **[Codex]** backend/data-plumbing, **[Claude]** frontend/UI/states.
Priority: **P0** = launch blocker, **P1** = important pre-launch, **P2** = polish.

Cross-refs: data-currency ties into `docs/local-evidence-freshness/plan.md`
(Phase 0.1 backend freshness block + Phase 4.1 FE provenance line, the latter
already built this session). Contracts stay backend-led — Claude mirrors the
shape Codex emits; Codex should confirm field names before Claude wires them.

---

## P0 — Launch blockers

### P0.1 — Report-level data currency + provenance `[Codex backend]` (+ `[Claude]` done)
The report had no "data as of" disclosure. **Claude shipped the FE line this
session** (`DataCurrencyLine`, under the variant header) — it renders from the
real per-source `fetched_at` on evidence rows today and auto-upgrades to a
backend freshness block when present. Codex owes the backend side:
- Emit the per-asset freshness block (`docs/local-evidence-freshness/plan.md`
  Task 0.1): `materialized_at`, `upstream_released_at`, `tier`, `status`,
  `staleness_days` in `provider-cache` **and** a report-payload field
  (propose `report_data_currency: {sources: [...], generated_at}`) so the FE
  line shows the upstream "as of" date, not just fetch time.
- Populate `VariantReportHeader.updated_at` (`run.py` — schema field exists,
  never set) and add a report-level `report_generated_at`.
- Confirm the field name so Claude wires `freshness={...}` (currently `null`).
- Acceptance: no path/secret/object-URI leak; FE line shows ClinVar/ClinGen
  "as of" dates from the live block.

### P0.2 — gnomAD population frequency: no silent blank `[Codex]` + `[Claude]`
On gnomAD fetch failure the call card ships `source_status` = `missing`/`failed`
(`report_call_cards.py`) and the section can render blank with no user-facing
reason.
- `[Codex]`: ensure `source_status` is reliably populated and a machine-readable
  reason rides along.
- `[Claude]`: `PopulationFrequencySection` renders an explicit "frequency data
  unavailable" card when `source_status !== live`, never a blank section.

### P0.3 — Gene viewer: no silent disappearance `[Claude]`
`/report` makes a separate inline `/api/v1/viewer` call (`ReportGeneViewer`).
On failure the exon/protein track silently vanishes. Add an error boundary +
explicit "gene context unavailable" fallback. (BRCA1 protein architecture itself
is verified working on prod incl. the new curated seed — this is the failure-path
gap, not a data gap.)

---

## P1 — Important pre-launch

### P1.1 — ClinGen Expert-Panel uses a consensus snapshot, not the Evidence Repo `[Codex]`
`lookup_sections.py` emits `clingen_vcep_evidence_repo_source_cache_not_integrated`;
the expert panel falls back to a clinical-consensus snapshot (ClinVar + cached
VCEP), so `ExpertPanelPartialNote` always renders. The report is *honest* about
this (so not P0), but it is the biggest scientific-credibility gap. Integrate the
ClinGen Evidence Repository source-cache and ship live VCEP records; the FE note
then becomes conditional, not permanent. Steven to decide if expert-panel
attribution must be live for launch (→ promote to P0) or can ship labelled-partial.

### P1.2 — In-silico calibration fields null `[Codex]` + `[Claude]`
`ComputationalPredictorRow` calibration fields (`calibrated_label`,
`calibration_bucket`/`method`/`version`) are often null → blank cells in
`CalibratedInSilicoTable`. `[Codex]`: populate from the evidence map.
`[Claude]`: hide/placeholder rows lacking a bucket instead of showing blanks.

### P1.3 — ClinVar gene-distribution index missing → empty curated-variants grid `[Codex]` + `[Claude]`
`lookup_service.py` excludes request-time gene-wide aggregation until a bounded
gene-distribution index exists (`_clinvar_distribution_runtime_path()` → None),
so `CuratedVariantsDistribution` is empty. `[Codex]`: build the bounded index
(this is the same M9 `clinvar_gene_distribution_excluded_pending_index` boundary)
or confirm it stays off for launch. `[Claude]`: render "coming soon / unavailable"
instead of an empty heatmap.

### P1.4 — Source version pins `[Codex]`
No per-source data-version (gnomAD r4.1 vs r3.1, dbSNP build, ClinVar release).
Add `source_versions`/version pins to the payload so the FE currency line and
exports can cite versions, not just dates. Folds into P0.1's freshness block.

### P1.5 — Protein-domain warnings surfaced, not buried `[Claude]`
When the protein track is partial/unavailable the backend emits warnings
(`protein_domain_track_unavailable:*`) that the report doesn't surface. Render
`ProvenanceNote` for protein-domain (and publication-snippet) warnings so a
degraded track is visible, not silent.

---

## P2 — Polish

- **Publications double-fetch** `[Codex]`+`[Claude]`: `LOOKUP_EAGER_RESPONSE_EXCLUDE`
  drops `publications_literature` from the eager response, forcing a second
  `/lookup/sections` round-trip even though data is inline. Decide always-inline
  vs always-lazy; FE skips the fetch if data is already present.
- **Trials freshness** `[Codex]`+`[Claude]`: add `fetched_at` to trial rows;
  render "last updated" so closed trials aren't shown as active.
- **ACMG assertion provenance** `[Claude]`: visually distinguish
  `source_asserted` vs `eamos_hint` vs `not_assessed` in `AcmgCriteriaFold`.
- **Advisory labelling** `[Claude]`: label `AdvisorySummaryStrip` clearly as the
  Eamos points advisory, distinct from the clinical classification.
- **Search dead-end** `[Claude]`: `SearchInterpretationPanel` offers next steps
  when `candidates[]` is empty.

---

## Claude's FE queue (for tracking — not Codex's)
P0.2 (pop-freq empty state) · P0.3 (gene-viewer error boundary) · P1.2 (in-silico
placeholder rows) · P1.3 (curated-variants empty state) · P1.5 (protein/snippet
provenance notes) · P2 ACMG/advisory/search items. P0.1 FE line is **done**;
wiring `freshness` to the live block is blocked on Codex confirming the payload
field name.
