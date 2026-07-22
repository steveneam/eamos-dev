# Live Product Completion — Release Specification

Status: proposed contract for Steven review; not frozen and not launched.

Stamped: 2026-07-22 16:29 +0000 · Codex.

## Outcome

Eamos ships Workbench, Variant Report, Paper → Variants, and Batch / Compare as
one coherent, universally free product in which every displayed result is bound
to the actual input and truthfully identifies its algorithm, provider, source,
artifact, applicability, and validation state.

The release may show an unavailable or not-applicable state. It may not quietly
replace a live request with a fixture, mock, illustrative row, heuristic proxy,
unrelated sequence window, VCF passthrough, or stale result from another input.

## Definitions

### Executed

The named implementation ran on the declared input and produced the returned
output. The response records the exact algorithm/provider version and all
required input context.

### Source-backed

A result derives from an identified source record or immutable local artifact.
The response records source identity, version/release, retrieval or
materialisation time, match level, and warnings.

### Deterministic local

A documented deterministic algorithm ran inside Eamos. This can be a real
implementation; “deterministic” is not synonymous with “mock.” Its scientific
claim must exactly match what it computes.

### Fixture

A small committed example used by tests or an explicit demo. A fixture is
allowed only behind an explicit demo/test switch and must remain visually and
structurally distinguishable from release output.

### Mock / illustrative

Invented output that demonstrates a shape or UI. It is prohibited from ordinary
release request paths.

### Unavailable / not assessed / not applicable

Typed, successful truth states. They include the missing requirement and do not
invent a value. “Unavailable” is preferred over a fake success.

## Universal-free and provider policy

1. No capability in this specification is gated by a paid Eamos account tier.
2. Operational rate, file-size, concurrency, and abuse controls remain neutral
   safety limits.
3. Provider cost can influence implementation architecture but cannot turn a
   result into a mock.
4. External transmission of sequence, trace, publication, or cohort material
   requires a server-issued disclosure and explicit user consent when the input
   leaves Eamos.
5. A provider's code/data licence and retention terms remain launch metadata.
6. A local, reproducible, licence-clean implementation is preferred where it
   can meet the scientific contract.

## Proposed shared execution disclosure

The serial contract lane will name and freeze the actual Pydantic/TypeScript
shape. It must cover at least:

```text
capability_id
claim
execution: eamos_local | mounted_artifact | external_provider | fixture | unavailable
algorithm_id
algorithm_version
provider_id
provider_version
input_scope
source_status
source_record_ids
source_release
materialized_at
artifact_manifest_id
artifact_sha256
applicability
validation_status
validation_matrix_id
retention
consent_required
warnings
requirements
```

Every surface may add domain fields, but it may not create a competing meaning
for execution/source status. Existing `SourceDisclosure`,
`ProcessingDisclosureV1`, source provenance, and capability-health shapes should
be consolidated or bridged rather than multiplied without a migration plan.

## Workbench contract

### Exact context binding

- Every Primer, CRISPR, ssODN, screening-primer, alignment, and outcome request
  carries or resolves a transcript/build context.
- The backend resolves the immutable source sequence, validates selection
  coordinates and reference bases, replays sparse edits, recomputes the context
  digest, and rejects a mismatch.
- A result echoes the verified context identity, selection, sequence basis,
  revision, and digest.
- A guide carries a verified genomic protospacer/PAM/cut locus, strand, build,
  and context digest. Off-target analysis accepts the verified guide identity,
  not an unrelated free-form locus.
- Changing context marks existing results stale; it never relabels them current.

### Primer

- Primer3 measurements are returned with Primer3 version and exact global/
  sequence arguments used.
- Sanger and qPCR modes have explicit, tested constraint profiles.
- Secondary-structure fields distinguish hairpin, homodimer, heterodimer, and
  any unsupported assay.
- Specificity is whole-genome when claimed. Template-only specificity is
  labelled template-only.
- dbSNP avoidance uses the mounted release and reports the overlap rule,
  especially the 3′-end policy.
- Reverse-strand, exon-spanning, intronic, UTR, distant-exon, indel-adjacent,
  and no-candidate cases are tested.

### CRISPR

- Supported nuclease/PAM combinations are explicit and deployment-derived.
- On-target scores identify the algorithm and required sequence context. A GC
  heuristic is not called Rule Set 3 or an efficiency probability.
- Genome-wide off-target enumeration uses a verified GRCh38 index/search engine
  and returns candidate sequence, PAM, strand, locus, mismatch/bulge details,
  search bounds, and enumeration completeness.
- MIT and CFD scores identify the algorithm implementation and version.
- CRISPOR web, if enabled, is opt-in and discloses its input-retention terms.
- ssODN supports only variant/edit classes it can prove; SNV, deletion,
  insertion, delins, strand orientation, homology arms, PAM blocking, and
  recutting risk each have typed state.
- No fixed HDR-efficiency number is emitted unless a validated model actually
  ran; otherwise the field is absent/not assessed.
- Screening primers use real reference windows for real off-target loci.

### TIDE / outcomes

- A feature named TIDE consumes chromatogram signal data and performs a
  documented decomposition compatible with the scientific claim. It reports
  alignment window, decomposition range, indel spectrum, goodness-of-fit,
  uncertainty/significance fields supported by the method, and quality checks.
- Consensus-string comparison may remain as a separately named descriptive
  trace comparison, but it is not TIDE.
- Raw AB1 data is request-lifetime only unless the user deliberately saves a
  disclosed artifact.

### Alignment and viewer

- Pairwise alignment never silently switches to positional comparison.
- Matrix/length limits produce a typed unavailable state or route to a real
  bounded aligner.
- AB1 parsing, quality trimming, mixed-peak handling, indel cases, reverse
  complement, and corrupt input have fixtures.
- Full-locus viewer tracks and sequence are source-backed per gene/transcript;
  unavailable tracks stay empty and labelled.

## Variant Report contract

- A report can be complete with unavailable sections; completeness means every
  section has an honest state, not that every database has a hit.
- One canonical variant identity links transcript, genomic build, normalised
  allele, rs/ClinVar identifiers, and source match records.
- Every report fact records match level: exact allele, transcript, protein,
  gene, gene-disease, condition, or discovery-only.
- Evidence list, report provenance, call cards, section signals, exports, and
  UI badges derive source status from one canonical rule.
- Each computational predictor has its own applicability and execution state.
  Non-missense variants do not receive missense scores and do not make the whole
  section falsely “broken.”
- ACMG output distinguishes source classifications, Eamos-computed evidence,
  unmet criteria, unavailable evidence, and non-clinical guidance.
- Publication and trial rows retain exact-variant versus lower-match-level
  scope in display and export.
- Cache/source version, materialisation time, upstream release, staleness, and
  stale-on-failure status are visible and exportable.
- No RPE65 or other fixture facts attach to a mismatched live variant.

## Paper → Variants contract

### Document model

The serial contract lane will define a versioned document bundle containing a
main PDF or text source plus optional supplements. Raw bytes/text remain
ephemeral by default. Durable records keep safe metadata, hashes, processing
state, bounded evidence spans, and results.

Per PDF, ingestion returns:

- page count and page-preserving text;
- engine and engine version;
- embedded metadata and resolved bibliographic metadata with provenance;
- per-page extraction quality;
- scanned/image-only or garbled-text detection;
- warnings and next requirements; and
- an input digest used to bind all mentions/results.

### Deterministic extraction layers

The ordinary free path adapts Selom's layered design:

1. **L1 structured:** exact HGVS/accession/rsID grammar in a bounded sentence or
   structured table/caption context, with explicit gene/transcript association.
2. **L2 recovery:** safe normalisation of line wraps, unicode punctuation,
   letter-spaced markers, split HGVS tokens, and bounded cross-line association.
3. **L3 document inventory:** high-recall paper-wide mention inventory over all
   non-reference text, with duplicates grouped but no forced allele equivalence.
4. **L4 optional verifier:** consented AI/OCR/vision adjudicates ambiguous or
   image-only cases and can propose vocabulary/grammar fixtures; it does not
   replace the deterministic result or auto-edit the curated grammar.

References are excluded from candidate generation by default. A candidate from
a reference list can be inspected as excluded evidence but cannot become an
actionable variant.

### Mention and resolution model

Every mention records page, section, character span, exact text, bounded quote,
gene/transcript evidence, notation type, biological context, extraction layer,
confidence, and warnings. Resolution is a separate Eamos gate. Only a unique,
source-backed resolved allele enables Report, Workbench, Library, or Batch
actions.

Clinical/case alleles, family segregation, experimental constructs, engineered
rescue variants, wild-type/background comparators, and ambiguous mentions are
distinct contexts. The product never upgrades a construct mention into a
patient allele.

### PDF and metadata implementation

- Prefer PDFium for robust page text/raster, pypdf for metadata/images, and
  optional pikepdf for XMP, matching the permissive Selom path.
- Remove or hard-gate PyMuPDF/fitz from the production path unless its licence is
  explicitly cleared.
- DOI-first metadata resolution uses local/cache sources where present, then a
  fail-soft OpenAlex → CrossRef → PubMed chain with versioned provenance.
- A blank/scanned PDF returns `ocr_required`, not a successful zero-candidate
  extraction.

## Batch / Compare contract

- V1 is explicitly WES/targeted-panel first: GRCh38 called-site VCF and VCF.gz,
  single/proband or bounded small-family input, SNVs and supported short indels.
  BCF is admitted only after parity tests. gVCF blocks, WGS-scale uploads,
  cohort-scale matrices, unsupported builds/contigs, and unimplemented SV/CNV
  claims fail with typed guidance instead of partial success.
- The runtime composition root injects the same `LookupService` used by direct
  lookup; a boot/preflight assertion fails if Batch would use INFO passthrough.
  The service has no successful release-mode path when that dependency is
  absent.
- For the same normalised variant and source snapshot, a completed Batch row
  equals the direct lookup summary on every shared field.
- VCF INFO values remain input provenance, never a substitute for Eamos output.
- Ingestion is streaming and bounded. Raw records may exceed the annotation cap
  so a normal exome can be filtered; the implementation does not materialize
  the full VCF or genotype matrix before filtering.
- Reference validation, left normalization, parsimonious representation, and
  multiallelic splitting use a pinned tested engine/reference. Original and
  normalized representations are both retained in result provenance. A REF
  mismatch is never silently corrected.
- PASS/quality/region and source-backed gene-interval intersection run before
  expensive annotation. The release cap applies to unique normalized variants
  remaining after filtering; it is not a raw-record cap masquerading as WES
  support.
- Gene filtering is coordinate-based, not trusted from an input `GENE`/`ANN`
  field. Users can select whole-gene, MANE exon + configured splice flank, or a
  validated custom capture BED scope; the exact interval artifact/build is
  recorded. Input gene/consequence fields remain provenance only.
- Pre-annotation filters (PASS, QUAL, region, gene/capture scope, bounded
  genotype/depth) and post-annotation filters (consequence, population
  frequency, ClinVar/source classification, and applicable predictor/evidence
  state) are distinct. Every exclusion has a counted reason, and an unavailable
  source is not silently treated as a negative match.
- Every row records normalisation/resolution state, per-field source state,
  warnings, and an actionable canonical report URL only when resolvable.
- Jobs use an owner-bound durable queue/lease or an equivalently restart-safe
  mechanism. A restart recovers or truthfully fails an in-flight job.
- Upload refs are single-use, owner-bound, expiring, and cleaned on consume,
  cancel, delete, expiry, and crash recovery. Raw VCF is not persisted by
  default.
- Paging and export do not require rendering or collecting the full cohort in
  the browser.
- Panel catalogs are source-backed with version, release, URL, gene-level
  confidence/provenance, and interval-build provenance. A handcrafted launch
  list is `custom`, not PanelApp/ClinGen.
- The launch catalog is built from permissibly reusable, version-pinned HGNC,
  MANE, GenCC, and Mondo artifacts. PanelApp remains a separately named,
  launch-gated overlay unless its downstream-use terms are cleared; free Eamos
  access does not override its licence.
- Offline/network failures never activate the illustrative panel catalog in
  ordinary live mode.
- Resource controls separately bound compressed bytes, decompressed bytes, raw
  records, samples, post-filter unique variants, memory, wall time, and queue
  concurrency. Their values come from synthetic WES benchmarks on the approved
  free deployment and are not account tiers.

## Capability/material registry

The campaign creates one machine-readable registry covering all four surfaces.
For each capability it records:

- owner module and route;
- algorithm/provider and version;
- code/data licence and launch posture;
- required artifact(s), expected digest/size/mount, and builder command;
- health/preflight check;
- fixture and live validation matrix IDs;
- deployment state; and
- exact unavailable/failed behavior.

Health derives from executed probes. File existence alone is not readiness.

## Required validation matrices

### Shared variant set

At minimum:

| Case | Purpose |
|---|---|
| RPE65 NM_000329.3 c.260A>G | current positive control |
| ABCA4 NM_000350.3 c.5435T>A | long retinal gene / non-default transcript |
| USH2A NM_206933.4 c.2276G>T | long reverse-context retinal gene |
| HBB NM_000518.5 c.20A>T | common pathogenic SNV / dense literature |
| TP53 NM_000546.6 c.215C>G | cancer gene / alternate context |
| BRCA1 NM_007294.4 c.68_69delAG | deletion / reverse strand |
| CFTR NM_000492.4 c.1521_1523delCTT | in-frame deletion |
| F8 NM_000132.4 c.6046C>T | chromosome X / reverse strand |

Add synthetic insertion, duplication, splice, delins, invalid reference, no-PAM,
no-primer, long-alignment, corrupt AB1, and ambiguous transcript controls.

### Paper corpus

Use small generated PDFs plus legally usable open-access documents covering:

- single- and two-column selectable text;
- split/garbled HGVS and unicode punctuation;
- line-numbered preprint and caption/references variants;
- image-only/scanned input;
- main PDF plus PDF/XLSX/CSV supplement;
- cDNA, genomic, protein, rsID, indel, splice, and legacy mentions;
- construct-only, clinical allele, comparator, family, and bibliography-only
  negative controls; and
- multiple genes/variants with representations that do and do not resolve to
  one allele.

Every corpus item has source/licence/checksum, expected mentions, exclusions,
resolution outcomes, and mutation-test variants.

### Batch corpus

Cover small hg38 VCF, gzipped VCF, optional BCF parity, single/proband and
small-family genotypes, missing gene, genomic only, cDNA-only,
SNV/indel/dup/splice, duplicate representations, bad REF, mixed contig naming,
PASS/AF/region/panel filters, restart/cancel/delete, maximum accepted rows,
paging, and streaming export. Add synthetic 25k/75k/150k-record WES-shaped
files whose post-filter sets are 0/10/500/5,000/over-cap, plus explicit gVCF,
WGS-shaped, cohort-scale, build-mismatch, symbolic-ALT, and decompression-bomb
rejections. No patient VCF is committed.

## Release gates

1. All focused and full backend/web suites green.
2. `app/backend/tests/test_boundary.py`, `scripts/eamos-web-boundary.mjs`, and
   the frontend-contract canary green.
3. No ordinary client fetch catches an error and substitutes a scientific
   fixture or illustrative result.
4. Capability registry and provider-cache health agree with executed probes.
5. The full variant, Paper, and Batch matrices pass locally and against the
   approved deployment.
6. Privacy assertions prove raw sequence, PDF text, AB1 data, VCF rows, tokens,
   and notes are absent from URLs/logs/errors and obey disclosed retention.
7. Each large artifact has an immutable manifest and a successful functional
   probe on its deployed mount.
8. Browser proof covers keyboard, screen reader, reduced motion, failure,
   unavailable, stale, partial, mobile, and large-data states.
9. Every provider/source mutation, materialisation, environment flip, and deploy
   has its separately approved receipt.

## Explicit non-goals

- Reintroducing paid account tiers.
- Presenting research output as a clinical diagnosis or laboratory-validated
  classification.
- Committing multi-gigabyte source artifacts to Git.
- Sending user sequence, trace, paper, or cohort data to an external service
  without disclosure/consent.
- Calling an observed string comparison TIDE, a local-window scan genome-wide,
  or a VCF INFO value an Eamos lookup.
