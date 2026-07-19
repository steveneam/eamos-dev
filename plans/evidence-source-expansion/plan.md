# Evidence Source Expansion — Implementation Plan

Status: Phase 0 complete at `49cdacb`; Phase 1 and the synthetic-fixture Phase 2
are complete at `b7c41c7`; the safe OMIM cross-reference Phase 3, fixture-only
LOVD Phase 4, code-only MaveDB Phase 5, and code-only ruleset hardening Phase 6
completed and passed their full local verification boundaries on 2026-07-19.
Phase 7 still requires the final published standard. Full ESM-1b
model/corpus acquisition, scoring, bgzip/Tabix materialization, upload,
activation, licensed-content ingestion, provider/deployment changes, and
Supabase mutation remain separate gates.

Stamped: 2026-07-19 08:39 +0000 · Codex.

## Goal

Expand Eamos's universally free evidence surface with a clinically defensible
REVEL-led computational card, a scalable clean-regenerated ESM-1b path, safe
OMIM, LOVD, and MaveDB integration slices, clearer OddsPath handling, and a versioned
route to the final ACMG/AMP/CAP/ClinGen SVC v4 standard.

This began as a plan-ahead artifact during the Phase-3c soak. Steven authorized
the code-eligible Phase 3-6 sequence on 2026-07-19. That authorization still
does not cover source materialization, a provider or environment change,
Supabase mutation, deployment action, licensed-content ingestion, or SVC v4
activation.

Research and source evidence live in
[`research.md`](research.md). Existing implementation context remains in:

- [`plans/variant-report-experience/plan.md`](../variant-report-experience/plan.md)
  — current report hierarchy and the four-card invariant;
- [`docs/report-acmg-viz/spec.md`](../../docs/report-acmg-viz/spec.md) — points
  engine and classification-visualization contract;
- [`docs/free-in-silico-predictors/plan.md`](../../docs/free-in-silico-predictors/plan.md)
  — universal-free predictor catalog;
- [`docs/report-section-5-source-governance/plan.md`](../../docs/report-section-5-source-governance/plan.md)
  — intended source-governance behavior; and
- [`docs/backend-build-ledger-runtime/materialization-plan.md`](../../docs/backend-build-ledger-runtime/materialization-plan.md)
  — operator/materialization boundary.

Where an older document asks whether AlphaMissense or ESM-1b should anchor
missense PP3/BP4, this plan records the founder's new direction: **REVEL is the
primary missense computational signal**. Phase 0 must freeze the exact applied
profile; “REVEL/Pejaver” alone is not a sufficient version pin. AlphaMissense,
ESM-1b, and other engines remain visible predictor detail; they are not silently
stacked or cherry-picked.

## Report Architecture Reconciliation

The four cards are intentionally different evidence axes with different input
parameters. This plan preserves that design exactly:

| Top card | Its own controlling parameter | Its own color meaning | Must not control |
| --- | --- | --- | --- |
| **Computational** | versioned, preselected predictor evidence; REVEL for a generally applicable missense rule | PP3/BP4 direction and strength for this one evidence line | Clinical, Population, or Lab card color; final classification |
| **Clinical Consensus** | curated ClinGen/VCEP precedence, then ClinVar aggregate | source-reported classification/conflict | Eamos computational result |
| **Population Frequency** | gnomAD AF/AC/popmax and applicable BA1/BS1/PM2 policy | common/benign support, rare/pathogenic support, intermediate, or unavailable | predictor or clinical-consensus color |
| **Lab & Functional** | source-asserted PS3/BS3 direction, conflict, review-required, or no data | functional deficit/normal/conflict/uncurated/no-data | publication count alone or computational result |

No card inherits another card's color. The cards do not visually “vote,” and
their colors are not a substitute for the points calculation. The full
Eamos-computed advisory, evidence plane, waterfall, posterior gauge, criteria,
and provenance remain the auditable classification surface below the top
summary.

The retired standalone Evidence Fingerprint and mini-dashboard are not restored.
This work changes the semantics and clarity of the existing Computational card,
not the report hierarchy.

## Frozen Product and Clinical Invariants

1. Universal-free means no paid entitlement gate for any eligible predictor.
   It does not override upstream licenses, database terms, privacy, or
   attribution.
2. The backend selects and calibrates evidence. The frontend renders the
   backend decision and never re-derives clinical meaning from raw scores.
3. A computational score produces PP3/BP4 evidence, not a standalone final
   Pathogenic/Benign classification.
4. One missense predictor is selected before its result is seen. Do not choose
   the most extreme available score and do not count correlated predictors as
   independent PP3/BP4 evidence.
5. The general missense selector is REVEL only after the active gene–disease
   profile establishes missense as an applicable disease mechanism. Otherwise
   REVEL is context-only/not applicable. A CSpec can specialize or override the
   choice only through an explicit versioned rule.
6. A non-missense variant uses a versioned class-appropriate selector or is
   marked not applicable; REVEL is not forced onto splice, stop, indel, or
   noncoding variants.
7. Missing REVEL produces `REVEL unavailable`; no silent fallback is promoted
   to the card's primary signal.
8. The current engine keeps the label `Richards-2015 + Tavtigian-2020 points`.
   No surface says Eamos is running SVC v4 until the final standard is pinned,
   implemented, and activated.
9. Color always has redundant text, score/points, and a dot or position cue.
   Only existing semantic `--cls-*` tokens carry clinical meaning.
10. Source policy is decided server-side before public serialization or export.
11. No LLM activates criteria, chooses a predictor, calculates points, or
    decides a tier.

## Commercial-Gate Reconciliation

The implementation audit must split two concepts that older plans sometimes
put under one “commercial” label:

- **Eamos entitlement:** obsolete. Remove Free/Pro/Max checks, premium badges,
  and paid unlock logic from every legally eligible predictor.
- **Upstream source permission:** still active. Preserve license, terms,
  attribution, cache, export, provenance, and launch gates per artifact/source.

Existing source-policy values such as `PUBLIC`, `INTERNAL_FIXTURE`, and
`LICENSED` describe a distribution context, not a subscription tier. Do not
delete those protections as part of universal-free work. A later behavior-
preserving rename to `DistributionContext` can reduce ambiguity, but it is not
required for the first card change.

For ESM-1b, a proved clean regeneration can receive a different source-policy
decision from the NC precomputed archive. For OMIM and LOVD, removing Eamos's
price does not change the upstream decision at all. MaveDB's verified CC0 bulk
subset is eligible regardless of Eamos's price; non-CC0 records, free-text
data-usage policies, and the AGPL application code remain separate gates.

## Target Contract

### Computational evidence decision

The schema-first contract should add a typed computational decision used by the
call card, detailed predictor table, and points engine:

```text
ruleset_id
ruleset_version
standard_label
standard_status: published | draft | shadow | withdrawn
application_id
gene_id
disease_id
transcript_id
protein_id
normalized_variant_id
variant_scope
mechanism_applicability
evidence_family: PP3_BP4 | SPLICE | other
selected_predictor_id
selection_policy
selection_rationale
declared_fallback_policy
applicability: applicable | not_applicable | unavailable | not_assessed
raw_score: backend Decimal; canonical decimal-string JSON/export
calibration_normalized_score: backend Decimal; canonical decimal-string JSON/export
score_unit
score_native_precision
score_quantization_rule
evidence_code: PP3 | BP4 | null
evidence_points: backend Decimal; canonical signed-decimal-string JSON/export
evidence_label
calibration_id
calibration_version
interval_lower: backend Decimal | null; canonical decimal-string JSON/export
interval_lower_inclusive
interval_upper: backend Decimal | null; canonical decimal-string JSON/export
interval_upper_inclusive
dependency_group
counted_status: counted | context_only | separate_mechanism | rejected
non_counted_reason
tool_version
model_version
data_version
source_version
source_url
source_retrieved_at
source_checksum
alternates[]
warnings[]
```

Backend arithmetic uses `Decimal`; JSON and exports use one canonical decimal
string. This applies to raw/normalized scores, interval bounds,
criterion/application points, pathogenic and benign totals, net points, tier
cutoffs, prior, likelihood-ratio base, posterior-model inputs, replay hashes,
and exports—not only the computational field. Current
published profiles emit whole numbers, but the public SVC v4 pilot includes
fractional evidence. A named strength remains optional because `+3`, `-3`, and
fractional values have no faithful Supporting/Moderate/Strong label.

`alternates[]` exposes other predictor scores for audit and detail. It cannot
change `selected_predictor_id`, `evidence_code`, or `evidence_points`.

### Source fact policy envelope

Every OMIM-, LOVD-, MaveDB-, or other source-derived fact carries:

```text
source_id
source_record_id
source_version
source_url
retrieved_at
origin_kind: direct | cross_reference | derived
match_level
record_license
terms_version_or_hash
license_gate
launch_gate
public_serialization_allowed
export_allowed
cache_allowed
attribution
policy_version
decision_reason
decision_at
policy_decisions[]: { action, field, outcome, reason, decided_at }
```

The three convenience booleans are computed projections from
`policy_decisions[]` under `policy_version`, not permanent truths stored on a
fact. Recompute them when source terms or Eamos policy changes. The engine must
decide per action and field—for example acquire, normalize, cache, publicly
serialize, product-export, log, analyze, back up, stage, and restore—with
deny-by-default behavior for an unknown action, field, or license.

Normalize private source-table operational status to the existing `local`
status and add a separate `storage_kind`; do not invent an operational status
that the live schema rejects.

### Ruleset registry

The engine needs an immutable ruleset record containing:

```text
ruleset_id
framework_name
framework_version
publication_doi_or_url
document_checksum
effective_date
status: published | draft | shadow | withdrawn
prior_decimal
likelihood_ratio_base_decimal
tier_definitions
criterion_definitions
predictor_selection_rules
dependency_and_exclusion_edges
standalone_overrides
cspec_overlay_version
activated_at
```

Draft records are research/shadow inputs only. They never label a report as
clinically active.

## Computational Card Specification

### Missense example

```text
Computational
REVEL · PP3 Moderate
score 0.822 · +2 points
Eamos missense policy · Pejaver 2022 calibration · <version>
```

The lede names the selected predictor and evidence band. The first badge names
the score at pinned native precision and the points. The source line separates
Eamos's applied policy from its published calibration basis.
Other predictors remain in the detailed In-silico chapter; directional
alternate-predictor badges do not appear on the compact card because they would
visually recreate predictor voting.

### Independent card color mapping

| Computational result | Surface/border/dot | Required text |
| --- | --- | --- |
| PP3 `+4` | red token family | `REVEL · PP3 Strong`, score, `+4 points` |
| PP3 `+3`, `+2`, `+1` | orange token family | exact evidence band/interval, score, signed points |
| indeterminate `0` | neutral grey token family | `REVEL · Indeterminate`, score, `0 points`; this is not a Clinical VUS |
| BP4 `-1` | lime/likely-benign token family | `REVEL · BP4 Supporting`, score, `-1 point` |
| BP4 `-2`, `-3`, `-4`, `-8` | green token family | exact evidence band/interval, score, signed points |
| unavailable/not applicable | neutral grey token family | explicit reason; never `Uncertain` if the real state is missing |

The detailed score scale can preserve more gradation than the compact card.
The card itself stays calm: restrained tint, 0.5-pixel hairline, no decorative
gradient, no animation beyond existing state transitions, and no color-only
meaning.

### Copy changes

Retire:

- “Eamos's combined call from the in-silico predictors”; and
- “the tools agree.”

Replace with:

> The preselected computational evidence for this variant class. For missense
> variants with an established missense disease mechanism, the current applied
> profile uses REVEL with published ClinGen PP3/BP4 calibration. Other
> predictors are shown below for context and are not counted as independent
> votes.

The card names only its applied published ruleset. SVC v4 draft monitoring stays
in admin/research provenance and never appears as a clinical-card badge.

## Phase 0 — Serial Safety and Contract Freeze

Phase 0 is one serial, lead-owned change. No implementation lane forks until it
is merged and its contract is frozen.

### 0A. Repair the computational evidence foundation

- Transcribe the peer-reviewed AlphaMissense and ESM-1b calibration tables
  directly into one executable backend registry.
- Create distinct identities for the Pejaver 2022 empirical REVEL calibration
  (including its `-8` interval), the clinically applied capped profile, and the
  Bergquist 2025 three-point calibration. Bergquist is future-point-ready, not
  final SVC v4.
- Use the capped profile as the proposed safe general default pending explicit
  clinical approval of both that profile and any use of the empirical `-8`
  band. A CSpec profile remains a separately versioned override.
- Pin native score precision or a machine-readable calibration release. Store
  raw and calibration-normalized scores, quantization, exact interval bounds,
  inclusivity, checksum, and version. Do not invent behavior in gaps created by
  rounded printed thresholds.
- Test every representable boundary and adjacent quantized value under the
  pinned precision; do not use an undefined floating-point epsilon.
- Migrate the full points calculation to backend `Decimal` and canonical
  decimal-string JSON/exports; preserve `±3` and future fractional values
  without coercion.
- Stop mapping predictor evidence to standalone final-classification buckets.
- Replace strongest-result selection with the versioned preselection policy.
- Require versioned gene–disease missense-mechanism applicability before the
  selected REVEL result can be counted.
- Ensure PP3 and BP4 are mutually exclusive for one decision and that alternate
  predictors cannot add duplicate criteria.
- Enforce the applicable published dependency/cap between PP3 computational
  evidence and PM1 regional evidence before any selected REVEL result can be
  counted.
- Remove manually duplicated frontend thresholds or generate the frontend
  display metadata from the backend source of truth.
- Update Pydantic first, then `app/web/lib/backend.ts`, then the frontend
  contract canary.

Until this phase lands, AlphaMissense and ESM-1b calibration rows must not be
newly activated for clinical points.

### 0B. Harden source provenance and export policy

- Extend `AssociatedCondition`, `SourceProvenance`, and fact-level records with
  the frozen policy envelope.
- Fix live `source_table` provenance validation instead of silently dropping
  rows.
- Make failed provenance construction a visible warning/test failure, not a
  quiet fallback.
- Apply server-side public/export filtering before report JSON, copy, HTML,
  PDF, TSV, and API serialization.
- Extend the policy engine from action-agnostic field lists to action-specific
  field decisions, separating public serialization from product export.
- Enforce policy before acquisition/cache and again at every output sink.
- Add deny-by-default tests for unknown and protected OMIM/LOVD/MaveDB actions,
  fields, and licenses, including logs, exceptions, analytics, raw-response
  debugging, staging, backups, and restore.
- Recompute policy decisions after a terms-version change rather than trusting
  stored permission booleans.
- Audit fixtures for copied OMIM names, case counts, and source strings that
  currently imply OMIM evidence rather than an identifier cross-reference.

### 0C. Freeze the MaveDB source and report contract

- Add registry identities for `mavedb_cc0_bulk` and an optional later
  `mavedb_public_api_metadata`; the build-ledger label alone is not a source
  policy record.
- Freeze separate archive, score-set, target, variant-score, and match records.
  Reserve a separately sourced calibration contract without assuming the bulk
  archive contains or licenses calibration/VA-Spec objects. Require variant
  URN, score-set URN, exact target identity, license snapshot, data-usage-policy
  decision, archive proof, and deprecation/supersession state.
- Extend the backend and TypeScript functional-evidence contracts so every
  MaveDB match carries exact numeric/source provenance and match level.
- Replace the single-study report prop with a collection and specify how
  multiple exact score-set measurements render without aggregation.
- Require both upstream archive hash verification and local logical checksum
  verification before `ready` or public serialization. A request may reuse a
  verified startup/preflight state; it may not silently turn verification off.
- Freeze matching precedence as exact VRS/genomic identity, then exact
  target-accession-version plus MAVE-HGVS, otherwise no match. Initially reject
  ambiguous sequence-only, multi-target, and multi-variant contexts.
- Keep raw MaveDB measurements neutral and uncurated. Remove any layout/copy
  that implies a raw score is itself OddsPath or an ACMG strength.

### Phase 0 exit gate

- frozen backend and TypeScript contracts;
- every calibration boundary test green;
- selected-predictor and no-double-count tests green;
- source provenance survives orchestration;
- MaveDB archive/license proof and checksum state gate readiness;
- restricted fields absent from every export format;
- structural boundary guards and frontend-contract canary green; and
- clinical review of wording and color-state examples.

## Phase 1 — REVEL-Led Computational Card

Implementation checkpoint: 2026-07-17 17:13 +0000 · Codex.

- The backend-selected REVEL decision now owns the call-card label, score,
  code, points, theme, and provenance while alternate predictors remain
  context-only and splice evidence stays separate.
- Browser proof covers pathogenic, indeterminate, benign, unavailable, and
  not-applicable states at 390, 768, 1024, and 1440 pixels. The mobile
  carousel keeps its compact dots inside 24-by-24-pixel tap targets; the
  refined mobile Lighthouse accessibility score is 97.

### Backend

- Add the clinically approved capped REVEL profile as the initial applied
  selector; keep `revel_pejaver_2022_empirical` and
  `revel_bergquist_2025_three_point` as distinct, non-interchangeable profile
  IDs. Do not activate the empirical `-8` band without explicit approval.
- Populate the typed computational decision from report annotations.
- Make call-card labels, badges, theme, and provenance from that decision.
- Preserve alternate predictor rows without letting them alter the selected
  evidence.
- Emit explicit applicable, not-applicable, unavailable, and indeterminate
  states.
- Require an established missense disease mechanism in the active gene–disease
  profile; otherwise emit context-only/not applicable with zero counted
  evidence.
- Keep splice and other variant classes on separate selectors; where no
  validated selector exists, emit not assessed.

### Frontend

- Render the backend-selected REVEL label, score, code, and points.
- Apply the Computational-only color mapping above.
- Preserve the other three cards' existing independent color derivations.
- Replace the combined-call tooltip and add a concise ruleset/provenance line.
- Make text/ARIA convey every state without color.
- Keep detailed AlphaMissense, ESM-1b, REVEL, SpliceAI, and other rows in the
  In-silico chapter.
- Replace any detailed “consensus” callout with explicit accounting, for
  example `REVEL counted · AlphaMissense/ESM-1b context only · SpliceAI separate
  mechanism`.

### Tests and visual proof

- REVEL boundary and missing-score cases.
- A test proving an extreme alternate score cannot replace REVEL.
- A test proving the four cards each retain their own theme input.
- Contract tests for ruleset/calibration provenance.
- Keyboard and screen-reader names.
- High-contrast, grayscale, and color-vision review.
- Browser screenshots at approximately 390, 768, 1024, and 1440 pixels for
  pathogenic, indeterminate, benign, unavailable, and not-applicable states.

## Phase 2 — ESM-1b Clean Offline Regeneration

Implementation checkpoint: 2026-07-17 17:13 +0000 · Codex.

- The fixture-only source route, exact long-protein tiling contract, bounded
  streamed parser, SQLite join/sort, deterministic chromosome shards, raw-score
  manifest, contextual duplicate handling, and fail-closed runtime proof gate
  are implemented and tested. Fixture score/context inputs have a hard
  100,000-row ceiling.
- The old materializer is disabled because a nullable `license_gate` was not
  build proof. Only a complete release-ready schema-v2 manifest whose declared
  route hash and final asset/index names, sizes, and SHA-256 values match the
  mounted files can eventually clear the runtime launch gate.
- The official Meta `.pt` object publishes a multipart ETag, not SHA-256. Its
  acquisition/hash, scorer image digest, full numerical parity, transport and
  clinical validation, 2-GiB runtime proof, and final materialization remain
  explicit exit gates. No model, score archive, or corpus was downloaded.

### Freeze the scientific build

- source route: pinned official ESM1b model/code plus independently sourced
  MANE sequences; do not use the CC BY-NC score archive without written terms
  that explicitly cover the ZIP rather than only the hosting Space;
- sequence/reference inputs: canonical MANE GFF/FASTA and GRCh38
  2bit/reference URLs, exact versions, terms/license snapshots, and SHA-256
  hashes in the source-route record and artifact manifest;
- execution contract: model `esm1b_t33_650M_UR50S`, exact weight URL/SHA-256,
  Meta and ntranos commits, `fair-esm`/Torch versions, eval mode, dtype, device,
  determinism controls, and scorer container/environment hash;
- score: published WT-marginal LLR;
- long proteins: a versioned 1,022-residue window, 512-residue minimum overlap,
  sigmoid scale 20, and exact pinned ntranos weighting behavior. The helper's
  unused default is 511, but the executable scorer calls it with 512;
- scope: MANE Select v1.5, GRCh38, exact versions, missense SNVs only; and
- identifiers: separate RefSeq, Ensembl, UniProt, and neutral protein-sequence
  identifiers.

The first route is frozen to primary chromosomes from the pinned UCSC
`hg38.2bit`. MANE v1.5 patch-contig genes are excluded with an explicit
64-gene skipped ledger; they must not disappear silently or be marked covered.

### Build a scalable worker

- isolated, locked GPU/large-RAM environment outside the request service;
- streamed input and output, disk-backed joins, deterministic shards, external
  genomic sort, bgzip/Tabix;
- manifest hashes for model, code, sequence inputs, raw shards, final data, and
  index; and
- allowlisted input hashes plus a reproducible build log proving the NC
  precomputed archive was not an input. A declaration alone is insufficient.

The immutable asset carries raw scores and validated build provenance, not an
authoritative `acmg_band`. Remove/ignore the current embedded band, or fail
closed unless its calibration ID/version exactly matches the active registry.
Runtime predictions take model, MANE, reference, scorer, and artifact versions
from the validated manifest—not a generic registry source version. UI license
copy is likewise artifact-route/manifest-derived; never label ESM-1b simply
`MIT` when a CC BY-NC score route also exists.

### Validate before materialization

- scorer numerical parity for short and over-context proteins;
- exact sequence/context equality with the calibrated UniProt/isoform resource,
  or a later non-overlapping clinical validation demonstrating that Bergquist
  thresholds transport to MANE-translated RefSeq/Ensembl contexts;
- transcript/protein/codon reconciliation and skipped-case ledger;
- transcript/gene-aware disambiguation when multiple contexts share one
  genomic `chrom/pos/ref/alt` key; duplicate-key coverage and fail-closed tests;
- row/coverage/checksum reconciliation;
- independent temporal ClinVar/gnomAD clinical calibration validation without
  refitting;
- separate DMS ranking/biological-effect evaluation that is not treated as
  validation of PP3/BP4 likelihood-ratio bands;
- gene-stratified performance and duplicate-position controls; and
- actual 2-GiB runtime lookup latency, concurrency, RSS, corruption, and
  missing-index failure tests.

ESM-1b remains an alternate detailed predictor under the current general
missense ruleset. A later ruleset may select it explicitly; no threshold is
borrowed by ESM-1v or ESM-2.

Materializing or uploading the full asset is a separate operator gate.

## Phase 3 — Safe OMIM Cross-Reference Slice

Implementation checkpoint: 2026-07-19 05:44 +0000 · Codex.

- `OmimCrossReference` now carries the actual supplying source/record, policy
  envelope, `cross_reference` origin, OMIM namespace, phenotype-versus-gene
  entry type, fixed `omim_web` provider, canonical HTTPS URL, and explicit
  `identifier_only` evidence role. Current approved suppliers are phenotype
  identifiers from MONDO, HPO, ClinGen, and GenCC; no gene-entry supplier is
  activated by this slice.
- Private clinical-source normalization preserves MONDO/HPO supplier ownership.
  Bare or malformed OMIM identifiers, unknown suppliers, wrong entry types,
  substituted URLs, stale/absent policy decisions, and unverified legacy
  fixture labels fail closed and are not publicly rendered.
- The report UI links only typed, server-permitted OMIM identifiers and labels
  them as non-evidentiary cross-references with their supplying source. It no
  longer turns legacy OMIM tokens or provenance URLs into an OMIM evidence row.
- `omim_mim2gene` and `omim_licensed_api` are reserved registry identities with
  empty public fields, explicit protected fields, and disabled acquisition,
  cache, provider, and runtime gates. No parser, download, API client, content,
  provider, persistence, or cloud mutation was added.
- The cross-reference path cannot create gene-disease validity; focused denial,
  source-policy, orchestration, contract, and client-link regressions are green.
  `npm run verify` passed end to end in 212.1 seconds.

1. Preserve the supplying source as `source_id`; store `OMIM` as the identifier
   namespace, `cross_reference` as origin, and `omim_web` as the external link
   provider. An `omim_link_resolver` row, if useful, is explicitly
   non-evidentiary.
2. Reserve genuine source identities for `omim_mim2gene` and
   `omim_licensed_api` when those routes are approved.
3. Render `OMIM:<id>` and an outbound link only when the supplying source and
   its permission are known.
4. Label origin explicitly, for example `cross-reference supplied by MONDO`.
5. Preserve gene versus phenotype MIM entry type.
6. Remove any implication that an identifier is OMIM-derived disease evidence.
7. Keep title, synopsis, inheritance, gene–phenotype association, allelic
   variant, API payload, and derived protected facts denied by default.
8. Evaluate `mim2gene` only after a written terms decision, and enforce in code
   that its parser cannot emit gene–disease validity.

An OMIM API integration begins only after signed terms define permitted display,
cache, export, backup, public-API, and ML/RAG uses.

## Phase 4 — LOVD Link and Fixture Pilot

Implementation checkpoint: 2026-07-19 06:13 +0000 · Codex.

- One registry identity and typed installation contract pin Global Variome
  shared LOVD to `https://databases.lovd.nl/shared`; arbitrary hosts and record
  namespaces cannot enter the report. Live access and positive caching are
  disabled, while the future-live rate and negative-cache minimums are frozen.
- The adapter has no network capability and accepts only bounded, hand-authored
  synthetic JSON/Atom documents. It rejects DTD/entities and projects the
  allowed basic-record scalars before any validation or fixed-code failure.
- Exact build, versioned RefSeq transcript, and coding HGVS equality is
  required. Missing/unknown licenses, ambiguous matches, mismatches, malformed
  canonical links, and policy drift fail closed; only the synthetic
  `CC-BY-4.0` example can form an observation.
- Backend `extra=forbid` models and the independent frontend safe projection
  exclude patient/person, phenotype, classification, submitter/curator,
  case-count, `Times_reported`, raw-payload, and unrecognized policy metadata.
  Cache, product export, log, analysis, backup, staging, restore, and raw-debug
  decisions remain denied; product-export serialization removes the section.
- The report uses neutral product tokens and the required presence-only copy,
  names the installation and exact match, and links only the validated origin.
  LOVD input cannot activate ACMG or change any of the four call cards/themes.
- Focused safety/contract/neutrality tests and full `npm run verify` passed; the
  full boundary completed in 302.4 seconds with 186 web tests, the complete
  backend suite, and the production build. No live/source/cloud mutation ran.

1. Add installation-scoped source and observation models.
2. Allowlist one reviewed Global Variome shared LOVD installation.
3. Build a fixture-only JSON/Atom adapter for exact normalized/HGVS matches.
   Fixtures are hand-authored synthetic documents based only on the documented
   schema—never copied live records or patient/submitter/curator material.
4. Return only presence, record link, build/transcript/HGVS, source-edited time,
   and policy/provenance.
5. Exclude people, patients, phenotypes, classification, case counts,
   `Times_reported`, and raw payloads.
6. State in the UI: `Matching LOVD basic record; presence is not a
   classification.`
7. Prove LOVD can never activate an ACMG criterion or change any call-card
   color.
8. Test transcript-version drift, assembly mismatch, ambiguous matches, unknown
   licenses, installation namespaces, negative caching, and rate limits.

Missing record license is `unknown`, and `unknown` is denied. Do not represent
installation permission as a record license. Parse and redact before logging,
exception construction, analytics, or cache writes; the UI always names the
installation and match level.

Only after written API/reuse permission may a live adapter use an identified
User-Agent, at most five requests/second/domain, no scraping, a minimum
four-hour negative cache, and an approved positive-cache policy. Full
case-level data remains a separate licensed/privacy project.

## Phase 5 — MaveDB CC0 Import Repair and Materialization

The existing read-only lane is a scaffold, not a deployable corpus importer.
Complete these steps before acquiring or materializing a real release:

1. Replace schema v1's `score_set_id` primary key with the official variant URN
   plus a unique `(score_set_urn, variant_urn)` constraint and exact target
   identity. Preserve MAVE-HGVS and VRS/mapped identifiers where supplied.
   Prove that thousands of variants in one score set and the same variant in
   multiple score sets remain distinct.
2. Inventory and fixture-test the pinned archive schema, then stream only its
   documented `main.json` plus score CSVs rather than an underspecified generic
   JSONL; do not unpack or load the corpus into memory. Preserve the available
   experiment/score-set/target identity, methods and assay context,
   score-column metadata, normalization and direction, uncertainty fields, and
   superseded-by relationships. Treat this bulk lane as raw-score-only; do not
   claim that it supplies calibrations, mapped VRS, or VA-Spec objects.
3. Store raw numeric values as exact source strings plus parsed `Decimal`; do
   not round through binary float. A generic field named `Functional score`
   must not imply that higher, lower, or zero has a universal meaning.
4. Prefer one explicitly approved, immutable version of the CC0-only Zenodo
   archive. Pin its release DOI, archive and score-set licenses, MaveDB citation,
   retrieval timestamp, file names/sizes/SHA-256 hashes, and source schema
   version. Verify the publisher's recorded MD5 before parsing, then compute
   SHA-256 for Eamos provenance. Never download on startup or request.
   Extraction must allowlist member names/types, reject absolute/traversal
   paths and symlinks, bound member count, compressed and expanded bytes,
   compression ratio, rows, columns, and cell size, and fail atomically with
   safe temporary-file cleanup under least privilege.
5. Establish permission only by joining each score file to the authoritative
   archive metadata; never trust a caller-supplied `"license": "CC0"` field or
   a score CSV alone. Continue to reject CC BY, CC BY-SA, missing, and unknown
   licenses. Hold out CC0 records with a non-empty restrictive or ambiguous
   data-usage policy until a versioned policy decision approves the intended
   acquire, cache, display, export, backup, and analysis actions.
6. Preserve linked DOI/PMID/raw-data/software identifiers as links only; their
   content and licenses are not inherited from MaveDB CC0.
   Derive every MaveDB record URL from a strictly validated URN and one fixed,
   allowlisted HTTPS origin; never render, redirect to, or fetch an imported
   `source_url`.
7. Make lookup target-, transcript-, assembly-, and mapping-aware. Fail closed
   on multi-target, multi-variant, deprecated, ambiguous, or mismatched records;
   do not use loose token coincidence as an exact clinical match.
8. Render every exact score-set match as a separate neutral `Uncurated` Lab &
   Functional measurement; do not select only the first or hard-code a
   one-score count. Raw matches cannot set the card color, activate PS3/BS3, or
   affect points.
9. Design calibration/mapped-VRS/VA-Spec acquisition as a separately pinned,
   rights-reviewed API lane. Never inherit the score set's CC0 decision onto
   separately authored calibration text. Treat a published calibration as
   candidate source-asserted context only; before counting it, require
   non-RUO status, provider/primary provenance, exact boundaries and OddsPath,
   source publications, and all Phase 6 assay-validation and dependency gates.
10. Reconcile health/build-ledger storage language with the actual local
    SQLite runtime, add schema-v2 migration/rejection behavior, then run
    multi-row, counterfeit-license, duplicate-context, precision,
    license/policy, deprecation, checksum-required readiness, corruption,
    hostile-archive/path, canonical-link, multiple-match rendering, and
    no-leak tests.

Materialization of the approved archive and any runtime/provider enablement
remain explicit operator actions after this code and clinical review is green.

Completion receipt — 2026-07-19 07:05 +0000 · Codex: Phase 5 now streams only
the documented root `main.json` and score CSV members from an already-acquired
ZIP into schema v2. It preserves authoritative experiment, score-set, target,
variant, method, identifier, exact source-number/`Decimal`, uncertainty,
deprecation, member-digest, and immutable-release provenance while rejecting
unknown/restricted policy, identity drift, ambiguous/deprecated matches, stale
schema signatures, and hostile archive structures with fixed safe codes. The
report renders every permitted exact score-set match independently as neutral
`Uncurated` context; MaveDB input cannot activate PS3/BS3, points, or clinical
color. Focused evidence/contract tests and structural ratchets passed, followed
by full `npm run verify` in 224.9 seconds: 11 Node ratchets, 25 Vitest files / 188
tests, the complete backend suite, lint/format/type checks, and the 17-route
production build. No real archive acquisition/materialization, live request,
upload, provider/deploy change, Supabase mutation, or cleanup occurred.

## Phase 6 — Current OddsPath and Ruleset Hardening

- Name aggregate model quantities directly:
  `aggregate_evidence_likelihood_ratio`, `prior_odds`, `posterior_odds`, and
  `model_posterior`. Reserve `functional_assay_oddspath` for an independently
  validated assay calculation.
- Preserve the current formula, prior/base, posterior anchors, tier cuts, and
  any custom conflict cap only in a version-pinned historical replay profile.
  Do not carry an uncited blanket conflict cap into a new current ruleset.
- Represent BA1 as a standalone classification override. Do not present
  `points=0`, posterior `0.10`, and a Benign tier as one coherent Bayesian
  calculation.
- Expand evidence dependency/exclusion edges beyond the Phase 0 PP3/PM1 and
  single-PP3/BP4 minimum.
- Treat Brnich functional OddsPath as assay-validation output, not a study-count
  transform.
- Before Eamos computes PS3/BS3 strength, require disease-mechanism/assay
  relevance, independent pathogenic and benign truth-set variant IDs,
  truth/evaluation-set overlap and circularity rejection, confusion matrix,
  pseudocount policy, direction-specific OddsPath and confidence interval,
  maximum supported strength, curator, validation date, source, and version.
- Keep source-asserted PS3/BS3 visible with exact provenance; count it only when
  the active ruleset's source, validation, and dependency requirements pass.
  Never infer or upgrade it from study count.
- Add versioned ClinGen CSpec overlays with a deterministic precedence rule and
  auditable diff from the general ruleset.
- Replace global one-size PM2/BS1/BA1 assumptions with versioned gene/disease
  policies where authoritative specifications exist.

Completion receipt — 2026-07-19 08:39 +0000 · Codex: Phase 6 now publishes
honestly named aggregate model quantities under the version-pinned Eamos
historical replay profile, keeps its custom conflict cap explicit, and models
BA1 as a stand-alone override with no point-model posterior. Typed functional
admission calculates Brnich assay OddsPath from independent truth controls and
a confusion matrix, enforces confidence, strength, source, version, exact
context, single-selection, exclusion, and independent-evidence gates, and keeps
unvalidated source assertions visible but uncounted. Versioned population
policies now resolve by exact gene/disease context; ClinGen RPE65 GN120 has
deterministic precedence and a serialized diff from the general policy. The
web report mirrors the contract, labels fixed frequency bands as general
orientation, and renders BA1's model posterior as accessible N/A. Focused
checks passed, followed by full `npm run verify` in 310.2 seconds: 11 Node
ratchets, 26 Vitest files / 193 tests, the complete backend suite, lint,
formatting, type checks, and the 17-route production build. No gated source,
cloud, deployment, Supabase, Render, cleanup, new-ruleset, or SVC v4 action
occurred.

## Phase 7 — Final SVC v4 Integration

This phase starts only when the final standard is publicly available.

1. Acquire the final document through an approved source; record title, DOI or
   canonical URL, publication date, checksum, and effective date.
2. Create a new immutable ruleset record. Never edit the historical
   Richards/Tavtigian ruleset in place.
3. Transcribe every criterion, point value, dependency, override, exclusion,
   evidence-family name, and tier/sub-tier definition with dual review.
4. Confirm the final missense computational rule and REVEL's exact role. Retain
   the current REVEL selector only where the final text supports it.
5. Extend output/UI for any final VUS sub-tier definitions without guessing
   draft cutoffs.
6. Run both rulesets in shadow on curated gold cases and representative live
   variants; report every criteria, point, posterior, tier, and wording diff.
7. Obtain clinical sign-off and explicit activation approval.
8. Switch by ruleset ID/feature gate, preserve rollback, and keep both
   provenance trails visible.

No report says `ACMG v4` while this phase is in draft, shadow, or review.

## Source and Launch Gates

| Item | Code may proceed | Data/live use requires |
| --- | --- | --- |
| REVEL current card | after Phase 0 contract/correctness | approved score source/version and registry policy |
| ESM-1b worker | yes, against small approved fixtures | source-route decision, build proof, materialization/upload approval |
| NC ESM score archive | no | written NonCommercial determination and attribution plan |
| OMIM cross-reference link | after provenance fix | permitted supplying source |
| OMIM `mim2gene` | parser/fixture only after terms review | documented import/redistribution permission |
| OMIM API/content | no | signed license/permission and field policy |
| LOVD link | yes | reviewed canonical host/URL |
| LOVD fixture adapter | yes | reviewed fixture fields and terms snapshot |
| LOVD live API | no | written reuse/cache/export permission |
| LOVD case-level data | no | contract, security/privacy/DPA, retention, and geography review |
| MaveDB schema-v2/fixture work | yes | synthetic fixtures and frozen source contract only |
| MaveDB CC0 bulk archive | no materialization in this slice | resolved Zenodo release, hashes, license/policy review, corrected importer, operator approval |
| MaveDB API supplement | no | bounded backend acquisition design, source terms/policy review, and operator approval |
| MaveDB CC BY / CC BY-SA | no | attribution/share-alike policy and explicit approval |
| MaveDB AGPL application/package | no | separate legal/architecture approval |
| SVC v4 shadow adapter | only after final publication | checksum pin and clinical transcription review |
| SVC v4 active label | no until Phase 7 exit | clinical sign-off and explicit activation |
| Supabase persistence | plan/test locally | separate migration/cloud approval |

## Persistence Security

If source persistence is approved later:

- reuse the existing `eamos_private` schema pattern;
- keep `eamos_private` outside Data API exposed schemas;
- keep raw payloads and normalized candidate facts separately policy-tagged;
  normalization never makes a fact public-safe;
- allow only explicitly public-serialization-approved facts into a public
  projection, and prohibit persistence while cache rights are unknown;
- revoke schema, object, and default privileges from `PUBLIC`, `anon`, and
  `authenticated`;
- grant only the backend role the minimum required privileges;
- use RLS as defense in depth, not as the only barrier;
- avoid browser-accessible functions/views. If one is unavoidable, use a
  security-invoker view, revoke function execution from `PUBLIC`, and do not
  use `SECURITY DEFINER` without a separate audit;
- keep service-role credentials backend-only; and
- test public, authenticated, export, error, and operational paths for denial.

Before licensed persistence, written terms must cover replicas, PITR, backups,
staging, retention, deletion, and restore behavior. Verification must exercise
the operator-level backup inclusion, retention, and restore policy—not merely a
query-path denial.

No migration or Supabase mutation is part of this planning slice.

## Proposed Parallel Implementation Sprint

This work has four useful lanes only **after Phase 0 is merged and the contract
is frozen**. Mode B is recommended because the work is long-running,
full-stack, and source/cloud cautious. Steven approves the partition and
launches each lane; Codex is the lead and sole merger. Lane agents push, mark
their board row `review`, and do not merge.

### Frozen seam

- Pydantic computational/source/ruleset contracts;
- `app/web/lib/backend.ts` mirror;
- calibration record shape and ruleset/source IDs;
- selected-predictor semantics;
- source policy envelope; and
- frontend contract canary.

Any lane needing to alter that seam stops and requests a re-plan.

### Lanes and owned globs

| Lane | Branch | Exclusive owned globs | Depends on | Merge order |
| --- | --- | --- | --- | ---: |
| A — ACMG/OddsPath rules | `agent/evidence/acmg-rules` | `app/backend/app/services/acmg_points_engine.py`; future ruleset modules; `app/backend/app/services/functional_evidence.py`; their focused backend tests | Phase 0 | 1 |
| B — REVEL computational card | `agent/evidence/revel-card` | `app/backend/app/services/report_call_cards.py`; focused call-card tests; `app/web/components/report/CallCardsGrid.tsx`; focused web tests | Phase 0; builds against frozen fixture | 2 |
| C — ESM-1b offline worker | `agent/evidence/esm1b-worker` | `app/backend/app/services/esm1b_*`; ESM CLIs; ESM tests; ESM-specific operator docs | Phase 0 | 3 |
| D — OMIM/LOVD/MaveDB safe adapters | `agent/evidence/source-adapters` | gene-disease/LOVD/MaveDB adapter modules; source-adapter fixtures/tests; source-specific docs | Phase 0 | 4 |

The lead owns all shared schemas, `app/web/lib/backend.ts`, registry records,
exports, migrations, CI/workflow files, `COORDINATION.md`, and integration
edits. No lane edits those paths. There is one web writer: Lane B.

### Exact launch package

Run from the repository root only after the Phase 0 freeze commit is on `main`:

```bash
git worktree add .claude/worktrees/evidence-acmg-rules -b agent/evidence/acmg-rules main
git worktree add .claude/worktrees/evidence-revel-card -b agent/evidence/revel-card main
git worktree add .claude/worktrees/evidence-esm1b-worker -b agent/evidence/esm1b-worker main
git worktree add .claude/worktrees/evidence-source-adapters -b agent/evidence/source-adapters main
```

Then open one Claude or Codex session in each worktree and paste its approved
lane brief. Backend dependencies are shared only if already present; no lane
changes a provider, runs a migration, downloads source corpora, uploads an
artifact, or deploys production.

The lead merges serially in the table order. Before each merge: inspect
`git log --name-only main..<lane>`, rebase onto current `main`, run the lane
gates and CI, review the diff, and pause for Steven's explicit merge approval.
Never merge red or accept an out-of-glob edit.

## End-to-End Acceptance

### Clinical correctness

- Current and final-v4 rulesets are never conflated.
- Every predictor profile pins score precision, quantization, ordered interval
  semantics, inclusivity, and checksum, with boundary, gap, NaN, and infinity
  tests.
- REVEL selection is predetermined, versioned, and visible.
- Gene–disease missense-mechanism applicability is required before REVEL is
  counted.
- Alternate predictors cannot replace or stack with the selected result.
- A profile change creates a new replayable run; historical outputs never
  silently reclassify.
- A predictor result is never worded as a final classification.
- Classification and functional OddsPath are unambiguous.
- Dependencies, overrides, and conflicts are represented and tested.

### Four-card product behavior

- All four top cards remain present and in their locked order.
- Each card's text and color derive only from its own evidence axis.
- Computational visibly names REVEL for applicable missense cases.
- Clinical, Population, and Lab are unchanged by REVEL availability or score.
- Computational indeterminate stays neutral; the Clinical card alone uses the
  VUS tier/color when its source classification is VUS.
- Every state remains legible in grayscale and to assistive technology.
- No retired dashboard/fingerprint layer returns.

### Source governance

- OMIM link-only, LOVD fixture-only, and MaveDB synthetic-fixture-only defaults
  are enforced until their respective gates pass.
- No protected/unknown-license fields leak through JSON, copy, HTML, PDF, TSV,
  logs, errors, cache, or public APIs.
- Origin, record license, terms hash, cache/export decisions, and attribution
  survive orchestration.
- LOVD presence cannot influence ACMG evidence.
- A raw MaveDB score remains neutral uncurated context and cannot influence
  ACMG evidence or any call-card color.

### Engineering gates

- focused backend and web tests;
- `app/backend/tests/test_boundary.py`;
- `scripts/eamos-web-boundary.mjs`;
- `app/backend/tests/test_frontend_contract.py`;
- typecheck, lint, format, production build, and `git diff --check`;
- local FE-to-BE report smoke;
- representative browser/accessible-theme proof; and
- full `npm run verify` before the final implementation slice is proposed for
  merge.

## Decisions Still Requiring Written Answers

1. OMIM: exact display/cache/export/API/backup/RAG permissions and attribution.
2. LOVD: basic-API reuse, per-record license discovery, TTLs, attribution, and
   `Times_reported` meaning; separate case-level privacy terms.
3. MaveDB: exact Zenodo release approval, treatment of non-empty data-usage
   policies, and whether later CC BY/CC BY-SA support is worth its policy cost.
4. ESM-1b: formal clean-regeneration source-route record and whether any NC
   archive use is categorically prohibited.
5. Final SVC v4: clinical reviewer/approver and activation owner after
   publication.
6. Persistence: whether approved source facts remain file-backed or receive a
   separately authorized private-schema migration.

These answers affect later launch gates, not the Phase 0 correctness work.
