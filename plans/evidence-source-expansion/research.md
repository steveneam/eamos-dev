# Evidence Source Expansion — Research Record

Status: research complete; implementation not started.

Stamped: 2026-07-17 13:39 +0000 · Codex.

This record covers ESM-1b (the request's “es1mb”), OMIM, LOVD, MaveDB,
OddsPath, REVEL, and readiness for the forthcoming ACMG/AMP/CAP/ClinGen Sequence
Variant Classification standard version 4 (SVC v4). It combines three
independent read-only research lanes with a repository audit. No source was
downloaded into the product, no provider was changed, and no cloud or database
mutation was made.

## Executive Decisions

| Capability | What universal-free changes | Decision now | Gate that remains |
| --- | --- | --- | --- |
| Predictor access | Eamos no longer needs Free/Pro/Max entitlement checks. | Make every technically and legally eligible predictor available to every user. | Model, score-artifact, and upstream database terms still apply. |
| REVEL | No product-tier gate remains. Published ClinGen guidance already supports REVEL as one preselected missense predictor. | Make REVEL the primary missense signal on the computational call card under a versioned current ruleset. | Do not label the ruleset “ACMG v4” until the final standard is published and reviewed. |
| ESM-1b | A clean regeneration path can be available to every user. | Preserve ESM-1b as a distinct calibrated predictor; generate immutable scores offline from pinned inputs and serve exact lookups. | Written source-route decision, corrected calibration, scalable build, provenance, and materialization approval. |
| OMIM | A free user experience removes a commercial product wall; it does not grant OMIM redisplay rights. | Show typed OMIM identifiers and outbound links only when an open/licensed source supplied the cross-reference. | `mim2gene` terms review; signed permission/license before API or content redisplay. |
| LOVD | A free user experience does not unify installation- or record-level rights. | Begin with deep links; then a synthetic-fixture-only, exact-variant, allowlisted adapter containing explicitly policy-approved fields. | Written installation/API terms, record-license handling, privacy review, and a live-launch gate. |
| MaveDB | Eamos's price was not the key gate: MaveDB's official bulk archive and included score sets are CC0. | Proceed with a repaired, versioned CC0-only local lane; keep raw scores neutral and uncurated. | Fix the importer before materialization; pin the archive release, per-score-set license and data-usage policy, target/calibration provenance, and an operator launch approval. |
| OddsPath | No tier gate is relevant. | Keep classification OddsPath and functional-assay OddsPath as two explicitly different concepts. | Versioned ruleset contract, dependency/double-count checks, and assay-specific calibration provenance. |
| SVC v4 | Eamos can prepare its contracts without reserving the feature for paid users. | Build a ruleset-ready contract now and retain the current Richards/Tavtigian label. | Final publication before an adapter; then checksum/DOI pin, clinical review, shadow gold cases, and explicit activation. |

The key licensing rule is simple: **free-of-charge is not the same as
NonCommercial, open source, or permission to redistribute a database**. Eamos's
universal-free decision removes its own entitlement gate; it cannot remove an
upstream author's copyright, database right, contract, attribution, privacy, or
field-of-use restriction.

The current registry's `PUBLIC`, `INTERNAL_FIXTURE`, and `LICENSED` contexts
should not be read as Free/Pro/Max product tiers. They govern distribution and
source handling. Universal-free removes user entitlement checks; source
license, launch, cache, export, and provenance gates remain record-specific.

## Highest-Priority Repository Findings

### 1. The computational evidence path is not safe to extend yet

The current implementation has three coupled correctness problems:

1. `computational_calibration.py` and `CalibratedInSilicoTable.tsx` materially
   mistranscribe the published AlphaMissense and ESM-1b calibration intervals.
   Existing tests preserve those incorrect intervals.
2. `acmg_points_engine.py` chooses the strongest absolute PP3/BP4 result across
   available predictors. Published ClinGen guidance says the computational
   method should be selected in advance and applied consistently, not chosen
   after seeing which predictor yields the strongest answer.
3. `report_call_cards.py` calls the card “Damaging” if any threshold-crossing
   predictor exists, while the frontend tooltip describes a combined call and
   says the tools agree. Correlated predictors are not independent votes.

These problems make calibration repair and a selected-predictor contract a
serial Phase 0 prerequisite. Adding ESM-1b scores or an SVC v4 badge before that
work would amplify an existing error.

### 2. Eamos currently cannot represent all published point intervals

The current evidence model names Supporting, Moderate, Strong, and Very Strong,
but does not faithfully represent the explicit `+3` and `-3` intervals used in
newer point-based calibration work. It also maps a predictor's PP3/BP4 evidence
to final-classification words such as “Pathogenic” and “Likely pathogenic.” A
computational predictor supplies one evidence line; it does not make the final
classification by itself.

The next contract needs exact signed `evidence_points` alongside the evidence
code and human label. Backend arithmetic should use `Decimal`, with canonical
decimal strings at JSON/export boundaries across criterion points, totals, tier
cuts, priors, likelihood-ratio bases, replay hashes, and exports. Current
published profiles use whole points, including
`-8, -4, -3, -2, -1, 0, +1, +2, +3, +4, +8`, without inventing a named
strength for a three-point interval. Public SVC v4 pilot material also shows
fractional values such as `+0.5`, so the future-ready type must be decimal-safe
rather than integer-only.

### 3. Section 5 provenance can disappear and exports are not policy-filtered

The repository's intended source-governance plan has not fully reached the live
contract:

- `AssociatedCondition` and `SourceProvenance` lack source identity, origin,
  match, record-license, launch, cache, and export decisions.
- the private source-table repository emits `status="source_table"`, which the
  schema does not accept;
- orchestration silently drops a provenance row that fails validation; and
- report JSON/copy/HTML/TSV/PDF paths do not consume a backend-computed export
  decision for each source-derived fact.

OMIM, LOVD, and MaveDB must not enter a contract that can lose their origin or
serialize restricted content by accident. This is the second serial Phase 0
prerequisite.

### 4. MaveDB is rights-ready for CC0 data, but its importer is not archive-ready

Eamos already has a useful fail-closed scaffold:

- `mavedb_local.py` accepts operator-supplied JSONL, rejects records whose
  license is not an exact recognized CC0 label, writes a checksummed local
  SQLite asset, and performs no network, provider, Supabase, or deployment
  action;
- the adapter is disabled by default and health reports
  `cc0_import_not_materialized` today;
- `functional_evidence.py` returns a matched score as uncurated functional
  context; and
- `MaveFunctionalBlock.tsx` explicitly declines to infer PS3/BS3.

That scaffold must not ingest a real bulk release yet:

1. `mavedb_functional_score.score_set_id` is the sole primary key, so every
   additional variant in the same score set overwrites the prior variant.
2. A score is reduced to binary `float`, although MaveDB score columns are
   non-prescriptive and can have assay-specific direction, scale,
   normalization, uncertainty, and companion columns.
3. The row lacks variant URN, exact target identity/sequence context, VRS and
   mapped identifiers, score-column metadata, calibration identity/status,
   data-usage policy, retrieval release, and deprecation/supersession state.
4. Text-token matching can conflate target contexts, transcript versions,
   multi-variants, or mapping states; the current fixture does not prove that
   multiple variants from one score set survive.
5. The build ledger describes a Supabase/Postgres route while the implemented
   runtime is file-backed SQLite. The ledger and implementation must agree
   before an operator treats readiness as authoritative.
6. Health, build-ledger, preflight, and request lookup currently call the
   inspector with `verify_checksum=False`, while `ready` alone makes public
   serialization appear allowed.
7. `mavedb_cc0` has no record in the normal data-source registry, so the shared
   acquire/cache/normalize/serialize policy cannot govern it.
8. `FunctionalStudy` lacks archive, license/policy, target/build, match,
   variant-accession, and supersession provenance, and it stores the functional
   score as `float`.
9. The report selects the first MaveDB study and the component hard-codes a
   one-score count, discarding the fact that several assays/score sets can
   match the same variant.

This is a correctness gate, not a reason to abandon MaveDB. A schema-v2 import
and exact target-aware identity should precede the first real materialization.

## ACMG SVC v4, REVEL, and the Computational Call Card

### What is established as of this stamp

- ACMG's own documents-in-development page says the SVC v4.0 standard “will
  soon be released” and describes VUS sub-tiers. It still lists the related
  document as in development; this is not a published final standard.
- Public pilot material describes a draft point-based SVC v4 framework and
  multi-phase testing. A public 2023 prototype illustrates `REVEL 0.822` as
  `+2` points and caps combined in-silico plus regional evidence at four points.
  A 2024 hearing-loss pilot used REVEL as the missense computational method and
  found prediction evidence to be a major reclassification driver, while
  explicitly calling the implementation hybrid because the draft did not yet
  provide all needed missense guidance. A 2026 pilot shows seven output
  classes, three-point bands, and fractional evidence while saying changes
  remain in progress.
- Current peer-reviewed ClinGen guidance already names REVEL among the
  genome-wide missense predictors that can reach strong pathogenic and moderate
  benign evidence. It recommends choosing one tool before seeing a variant's
  result and using that choice consistently.

Therefore the user's product direction is supported: **REVEL should be the
visible anchor of the missense computational card.** The evidence does not yet
support claiming that Eamos is running the final ACMG v4 standard or that the
unpublished final text mandates REVEL.

### REVEL profiles that must remain distinct

The Pejaver 2022 empirical intervals are:

| REVEL score | Evidence | Points |
| --- | --- | ---: |
| `≤ 0.003` | BP4 Very Strong | `-8` |
| `> 0.003` to `0.016` | BP4 Strong | `-4` |
| `> 0.016` to `0.183` | BP4 Moderate | `-2` |
| `> 0.183` to `0.290` | BP4 Supporting | `-1` |
| `> 0.290` to `< 0.644` | Indeterminate | `0` |
| `0.644` to `< 0.773` | PP3 Supporting | `+1` |
| `0.773` to `< 0.932` | PP3 Moderate | `+2` |
| `≥ 0.932` | PP3 Strong | `+4` |

Newer Bergquist work additionally reports this future-point profile:

| REVEL score | Points |
| --- | ---: |
| `≤ 0.016` | `-4` |
| `0.017` to `0.052` | `-3` |
| `0.053` to `0.183` | `-2` |
| `0.184` to `0.290` | `-1` |
| `0.291` to `0.643` | `0` |
| `0.644` to `0.772` | `+1` |
| `0.773` to `0.878` | `+2` |
| `0.879` to `0.931` | `+3` |
| `≥ 0.932` | `+4` |

That table belongs in a separately pinned calibration/ruleset version; it must
not silently change a historical Pejaver result. A CSpec/VCEP profile can cap
or specialize the empirical calibration; a current example maps all `≤0.016`
scores to `-4`. Therefore Eamos needs three separate identities: Pejaver 2022
empirical, a clinically applied current/capped profile, and Bergquist 2025
three-point. The capped profile is the safest proposed default pending explicit
clinical approval of any empirical `-8` use. Bergquist is future-point-ready,
not final SVC v4. Final v4 mapping remains deferred until the final standard can
be transcribed and reviewed.

### Required card behavior

For a missense variant under the current ruleset, the first of the four report
call cards should render the backend-selected REVEL evidence directly:

```text
Computational
REVEL · PP3 Moderate
score 0.822 · +2 points
Eamos missense policy · Pejaver 2022 calibration · <version>
```

The card's surface, border, and dot should use the existing semantic ACMG ramp,
while the words, score, evidence code, and points remain visible:

| Evidence direction | Card treatment |
| --- | --- |
| pathogenic `+4` | red token family |
| pathogenic `+3`, `+2`, or `+1` | orange token family; the detail scale preserves gradation |
| indeterminate `0` | neutral grey token family; this is computational non-evidence, not a Clinical VUS |
| benign `-1` | lime/likely-benign token family |
| benign `-2`, `-3`, `-4`, or `-8` | green token family; the detail scale preserves gradation |
| unavailable/not applicable | neutral grey, explicit reason |

Color is never the only signal. The design must use existing `--cls-*` semantic
tokens, retain the restrained 0.5-pixel clinical hairline, pass contrast checks,
and expose the same meaning through text and accessible names. This follows the
product's “instrument, not marketing” design contract.

If REVEL is unavailable for a missense variant, the card says `REVEL
unavailable`; it does not silently promote AlphaMissense, ESM-1b, CADD, or the
most damaging available result. Other scores remain visible in the detailed
in-silico section. A different primary predictor is legal only when a versioned
ruleset or gene-specific specification selects it in advance. Non-missense
classes use their own rule, for example a splice-specific selector, rather than
forcing REVEL onto an inapplicable variant.

Even for a missense variant, REVEL can count only when the active gene–disease
profile establishes missense as an applicable disease mechanism. Otherwise it
is context-only/not applicable. The application record must also enforce the
published PP3/PM1 shared-signal cap before points are combined.

### Current call-card wording that must be retired

The tooltip currently says the card is Eamos's combined call and that
“Damaging” means the tools agree. The backend can label the card damaging when
only one predictor crosses its tool-native threshold. Both statements should be
replaced by selected-predictor and calibration provenance.

## Calibration Transcription Audit

### AlphaMissense — published Bergquist 2025 table

| AlphaMissense score | Evidence | Points |
| --- | --- | ---: |
| `≤ 0.070` | benign three-point interval | `-3` |
| `0.071` to `0.099` | BP4 Moderate | `-2` |
| `0.100` to `0.169` | BP4 Supporting | `-1` |
| `0.170` to `0.791` | Indeterminate | `0` |
| `0.792` to `0.905` | PP3 Supporting | `+1` |
| `0.906` to `0.971` | PP3 Moderate | `+2` |
| `0.972` to `0.989` | pathogenic three-point interval | `+3` |
| `≥ 0.990` | PP3 Strong | `+4` |

There is no AlphaMissense `-4` interval in this table. Current Eamos code
reverses `0.100–0.169` to pathogenic support, promotes much of the indeterminate
and supporting range, and makes `≥0.990` indeterminate. It must not be used for
clinical points until repaired.

### ESM-1b — published Bergquist 2025 table

| ESM-1b LLR | Evidence | Points |
| --- | --- | ---: |
| `≤ -24.0` | PP3 Strong | `+4` |
| `-23.9` to `-14.0` | pathogenic three-point interval | `+3` |
| `-13.9` to `-12.2` | PP3 Moderate | `+2` |
| `-12.1` to `-10.7` | PP3 Supporting | `+1` |
| `-10.6` to `-6.4` | Indeterminate | `0` |
| `-6.3` to `-3.2` | BP4 Supporting | `-1` |
| `-3.1` to `8.7` | BP4 Moderate | `-2` |
| `≥ 8.8` | benign three-point interval | `-3` |

There is no ESM-1b `-4` interval in this table. Current Eamos promotes the
entire `≤-14.0` interval to +4 and collapses the upper benign side into -2.

Pin the Version of Record, DOI
[`10.1016/j.gim.2025.101402`](https://doi.org/10.1016/j.gim.2025.101402), and
its acquired-document checksum. Its ESM-1b indeterminate upper bound is `-6.4`;
the older `PMC11429929` preprint XML says `-6.2`. Record that discrepancy so an
implementation cannot accidentally transcribe the stale PMC table.

The implementation task must transcribe the peer-reviewed table directly and
pin native score precision or a machine-readable release. It must store
quantization, bounds, inclusivity, checksum, and version, then test every
representable boundary, gap, NaN, and infinity case; an arbitrary floating-
point epsilon around rounded print values is undefined. No hand-maintained
duplicate frontend threshold table should remain.

## ESM-1b

### Existing Eamos work

Checkpoint: 2026-07-17 17:13 +0000 · Codex.

Eamos already has a meaningful base:

- assembly, MANE-context, and local Tabix lookup services;
- a fixture-only clean-regeneration CLI, disk-backed worker, and targeted tests;
- data-source registry and health/ledger hooks; and
- an in-silico catalog row.

The runtime lookup is fail-closed and now disambiguates repeated genomic keys
with transcript/gene/protein context. The missing work is the operator-side
official-weight hash, scorer image digest, full numerical and clinical proof,
full-scale generation, and actual materialization, not a request-time model
service.

### Source and license route

| Component | Observed terms | Research decision |
| --- | --- | --- |
| Meta ESM repository/code | MIT | Pin commit and preserve notice. |
| official Meta ESM1b `.pt` weights | repository tagged MIT; Meta endpoint reports 7,828,576,466 bytes and a multipart ETag, not SHA-256 | Acquire only at the operator gate, preserve terms, and compute SHA-256; do not treat the ETag as a content hash. |
| official Meta Hugging Face conversion | `facebook/esm1b_t33_650M_UR50S` exposes a distinct approximately 2.61 GB `pytorch_model.bin` | Do not substitute it into the pinned fair-esm/ntranos route without a separately proved numerical-parity decision. |
| ntranoslab scoring code | MIT | Suitable pinned reference implementation. |
| precomputed all-human-isoform score archive | hosting Space declares CC BY-NC 4.0 | Do not download, stage, or use without a written NonCommercial determination and attribution decision. |
| clean Eamos regeneration | derived from pinned model/code and independently sourced sequence inputs | Preferred route, with allowlisted input hashes and a reproducible build log proving the NC score archive was not an input. |

The prior clean-regeneration materializer could clear its gate from caller
metadata alone. It is disabled. Runtime activation now requires complete
schema-v2 source-route, input, model, environment, final asset, and index proof;
the route hash and mounted final asset/index identity are verified rather than
trusted as declarations, and fixture manifests remain gated.

The detailed predictor UI currently describes ESM-1b simply as `MIT`. That can
conflate an MIT model/scorer route with the hosted CC BY-NC score archive.
License copy must come from the actual artifact manifest and source route. A
written terms decision for any NC route must confirm that the hosting Space's
license declaration covers the ZIP itself.

### Runtime architecture

Request-time inference is not viable on the 2-GiB syd2 service. The FP32 weights
alone exceed that memory budget, and the API image intentionally has no Torch
stack. Quantizing or changing precision would change the scoring implementation
and require a new numerical-parity and clinical-calibration decision.

The durable architecture is:

```text
versioned MANE sequence inputs
  -> pinned offline ESM1b WT-marginal scorer
  -> per-protein raw shards
  -> transcript/codon mapping
  -> external genomic sort
  -> bgzip + Tabix + immutable manifest
  -> private mounted/object asset
  -> exact request-time lookup on syd2
```

The v1 fixture assembler retains its inputs and output in memory and remains
fixture-only. The v2 worker streams bounded inputs, joins and externally sorts
through SQLite, writes deterministic chromosome shards, and records raw-score
hashes without an embedded `acmg_band`. The fixture worker rejects score or
context inputs above 100,000 rows. Full bgzip/Tabix finalization is held behind
the separate materialization gate.

The reproducible execution contract must pin model
`esm1b_t33_650M_UR50S`, weight URL/SHA-256, Meta and ntranos commits,
`fair-esm`/Torch versions, eval mode, dtype, device, determinism controls,
WT-marginal strategy, and the executable scorer's versioned 1,022-residue
window/512-residue minimum-overlap/scale-20 weighting algorithm. An allowlist
of all input hashes and a reproducible
build log—not a declaration alone—proves the NC archive was not used.
The exact MANE GFF/FASTA and GRCh38 2bit/reference inputs also need canonical
URLs, versions, terms/license snapshots, and SHA-256 hashes; “independently
sourced” is not sufficient provenance.

Legacy assets can embed an `acmg_band` at build time while the runtime also
recalibrates the raw score. That creates two drifting authorities. The durable
asset should carry raw score plus validated build provenance; calibration comes
from one active runtime registry. Otherwise fail closed unless embedded and
active calibration IDs/versions match exactly.

### Frozen v1 scientific scope

- MANE Select v1.5, GRCh38, exact transcript and protein versions.
- Missense single-nucleotide variants only.
- Published WT-marginal log-likelihood ratio, not masked marginal.
- Pinned Brandes/ntranos overlapping-window behavior for sequences over the
  model context limit.
- Explicit no-score for MNV-derived missense, indels, stop-gain, splice, and
  noncoding variants.
- No silent score transfer between isoforms.

Bergquist calibrated precomputed UniProt/isoform contexts. Before transferring
those thresholds to an Eamos MANE-translated RefSeq/Ensembl score, prove exact
protein sequence/context equality or perform later non-overlapping clinical
validation of transportability. Transcript-name reconciliation alone is not
enough.

The materialization contract also needs:

- transcript/gene-aware disambiguation where multiple contexts share one
  genomic `chrom/pos/ref/alt` key, because the current lookup fails closed on
  multiple rows;
- an explicit MANE patch-contig inclusion/reference policy; and
- prediction provenance populated from the validated artifact manifest rather
  than a generic registry source version.

The MANE builder currently serializes its default RefSeq `protein_id` as
`uniprot_isoform`. That field must become a neutral `protein_sequence_id`, with
separate versioned RefSeq, Ensembl, and true UniProt identifiers.

Clinical calibration validation (non-overlapping ClinVar/gnomAD truth sets) and
DMS ranking/biological-effect validation are separate gates. DMS performance
cannot validate PP3/BP4 likelihood-ratio bands.

## OMIM

### What is safe now

Eamos can display an identifier-level cross-reference supplied by an open or
licensed upstream source:

```text
OMIM:204100 · identifier link
Cross-reference supplied by MONDO
```

An OMIM ID is not proof that OMIM supplied the evidence. The origin must name
HGNC, MONDO, HPO, MedGen, or the actual upstream source.

### What remains gated

OMIM's primary publication states that for-profit users, and users who
redisplay or incorporate OMIM into software, need a license. Until written
terms say otherwise, do not publicly ingest or redistribute OMIM titles,
clinical synopses, gene–phenotype associations, inheritance, allelic variants,
API responses, or facts derived from protected content.

`mim2gene.txt` is available without API registration, but is explicitly a
mapping file rather than a gene–phenotype table. It can be evaluated as a
separate source only after terms review and can never be used to infer disease
validity.

For an identifier link, preserve the actual evidence origin rather than
inventing `omim_xref` as its source:

```text
source_id = mondo_disease_ontology   # or the real HGNC/HPO/etc. source
identifier_namespace = OMIM
origin_kind = cross_reference
external_link_provider = omim_web
```

An optional `omim_link_resolver` registry row is non-evidentiary. In contrast,
`omim_mim2gene` and `omim_licensed_api` are genuine upstream source identities
when those routes are approved.

## LOVD

LOVD software being open source does not make every LOVD installation or record
open data. The official materials describe installation-specific rules,
submitter/curator ownership, record-level licenses, no-scraping expectations,
and a basic API limited to non-patient data. Public records visibly vary among
CC BY, CC BY-NC-SA, and no selected license.

The safest progression is:

1. outbound links only;
2. fixture-only adapter for one reviewed, allowlisted installation, using
   hand-authored synthetic JSON/Atom shaped from public API documentation—not a
   copied live response;
3. exact normalized-variant match returning presence, record link,
   assembly/transcript/HGVS, and source-edited date only;
4. written terms and record-license policy; then
5. bounded live basic-API access with an identified User-Agent, no scraping,
   at most five requests/second/domain, and negative caching of at least four
   hours.

The first slice excludes owner/creator names, patient data, phenotypes,
classification, raw payloads, and `Times_reported`. A LOVD record's presence is
not an ACMG assertion and must never affect points. Full case-level data is a
separate licensed and privacy-reviewed project.

A missing record license is `unknown`, and `unknown` is denied. Installation-
level permission is not represented as a record-level license. Parsing and
redaction occur before a value can reach logs, exceptions, analytics, or cache,
and the UI names the installation and exact match level.

Installation and observation identities must be installation-scoped. Do not
accept arbitrary user-supplied LOVD hosts.

## MaveDB

### What is unlocked

MaveDB's current official documentation makes the CC0 subset unusually clear:

- every score set chooses CC0, CC BY 4.0, or CC BY-SA 4.0, with CC0 the
  default and nearly all current datasets reported as CC0;
- the score-set license is present in downloads and API responses;
- the quarterly Zenodo bulk archive at DOI
  `10.5281/zenodo.11201736` contains only CC0 score sets and the archive itself
  is CC0; and
- public API reads require no authentication, although bulk consumers are
  directed to the archive.

Therefore **yes: Eamos can integrate the verified CC0 MaveDB corpus for every
user once the importer and operator gates are repaired.** This was already a
data-rights-safe lane; making Eamos free removes any product-tier ambiguity but
is not what grants the permission. CC BY and CC BY-SA records are outside the
current Eamos gate and need separate attribution/share-alike policy work.

As checked on 2026-07-17, that concept DOI resolves to archive version 4,
published 2026-02-06, with immutable DOI `10.5281/zenodo.18511521`; the current
archive is approximately 1.8 GB and advertises MD5
`1b25ea356d95277b780de1e78e4e995d`. The documented quarterly cadence is not a
freshness guarantee: show the snapshot date, pin the immutable DOI, and compute
Eamos's own SHA-256 during an approved acquisition.

The safest reproducible acquisition route is a specifically pinned Zenodo
archive version, not a moving DOI at runtime and not the AGPL MaveDB server or
Python package embedded into Eamos. Record the resolved release DOI, archive
license, retrieval time, every file name/size/SHA-256, and MaveDB citation.
Verify the publisher-recorded MD5 before parsing. Treat the ZIP and its contents
as hostile: allowlist member names/types; reject traversal, absolute paths, and
symlinks; bound member count, compressed/expanded size, compression ratio,
rows, columns, and cell size; parse under least privilege; and fail atomically.
A small, current-data supplement may later use the public REST API only through
a separately reviewed, bounded backend acquisition job.

A live check also found that the public `/scores` endpoint returned plain CSV
without the documented license header. Treat the archive `main.json` or the
authoritative score-set metadata response as the license source of truth; never
infer permission from a score CSV or an operator-authored JSONL field alone.

### What CC0 does not decide

A score set can carry a free-text data-usage policy in addition to its Creative
Commons license. Until policy precedence and compatibility are reviewed, a
non-empty restrictive or ambiguous policy is held out even when the license
field says CC0. License changes do not retroactively alter an already acquired
copy, so Eamos must preserve the license and policy as obtained with each
immutable release rather than consulting only today's live record.

CC0 applies to the deposited score-set data, not automatically to linked
papers, external raw-data repositories, software, or figures. Preserve DOI,
PMID, and external-resource identifiers as links/provenance; do not copy their
content under the MaveDB license assumption.

### Clinical boundary

MaveDB raw `score` values are not comparable across assays. Eamos must preserve
the score column's meaning, target, experiment, methods, normalization,
direction, uncertainty fields, and any published calibration. A raw score may
appear as neutral uncurated Lab & Functional detail, but cannot change that
card's color or activate PS3/BS3.

MaveDB now supports published calibrations, functional classifications,
ACMG/AMP evidence strengths, mapped variants, and VA-Spec outputs. The bulk
archive contract only guarantees `main.json` metadata plus score/count CSVs,
so the first lane is raw-score-only. Calibration, mapped-VRS, and VA-Spec
objects require a separately pinned API acquisition and rights review; never
assume the score set's CC0 decision licenses separately authored calibration
text. Clinical admission must reject private and RUO calibrations for counting,
distinguish investigator from community calibrations and primary status,
preserve source publications and exact intervals, and pass the assay-validation
requirements in the OddsPath section. MaveDB hosting or primary status alone is
not clinical validation.

All MaveDB links are constructed from a strictly validated URN and a fixed,
allowlisted HTTPS origin. Imported `source_url` values are neither rendered nor
fetched.

## OddsPath and the Current ACMG Engine

“OddsPath” must identify which of two different calculations is meant:

1. **classification-combination OddsPath** — Tavtigian's Bayesian points model,
   currently implemented with prior `0.10`, base `2.08`, and final tier cuts;
2. **functional-assay OddsPath** — Brnich's calibration of PS3/BS3 evidence from
   assay validation data.

The current engine is honestly pinned as `Richards-2015 + Tavtigian-2020
points`. It must keep that label and must not be relabeled SVC v4.

For new rulesets, name the model quantities
`aggregate_evidence_likelihood_ratio`, `prior_odds`, `posterior_odds`, and
`model_posterior`; reserve `functional_assay_oddspath` for the assay calculation.
The current blanket conflict cap is an Eamos-specific legacy behavior unless an
authoritative rule is pinned, so preserve it only for historical replay. Model
BA1 as a standalone classification override, not as `0` points plus a `0.10`
posterior that somehow yields Benign.

For functional evidence, Brnich's reported OddsPath bands are:

| Assay OddsPath | Functional evidence |
| --- | --- |
| `< 0.053` | BS3 Strong |
| `0.053` to `< 0.23` | BS3 Moderate |
| `0.23` to `< 0.48` | BS3 Supporting |
| `0.48` to `2.1` | Indeterminate |
| `> 2.1` to `4.3` | PS3 Supporting |
| `> 4.3` to `18.7` | PS3 Moderate |
| `> 18.7` to `350` | PS3 Strong |
| `> 350` | PS3 Very Strong |

Study or PMID count is not an assay likelihood ratio. Eamos can display
source-asserted PS3/BS3 today with exact provenance, but should count it only
when the active ruleset's source, validation, and dependency requirements pass.
Add assay-specific validation provenance, controls, replicate counts, and a
documented computation before calculating a functional OddsPath itself.
That calculator requires independent truth-set variant IDs, disease-mechanism
and assay relevance, overlap/circularity rejection, a confusion matrix,
pseudocount policy, direction-specific confidence interval, and maximum
supported strength.

The ruleset also needs:

- criteria dependency/exclusion edges to prevent double counting;
- gene/disease-specific ClinGen CSpec overlays;
- versioned population-threshold policies rather than one global PM2/BS1/BA1
  threshold; and
- an explicit status of `published`, `draft`, `shadow`, or `withdrawn`.

## Source Provenance and Persistence Contract

Every source-derived fact needs the following server-owned policy envelope:

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

The convenience permission booleans are projections from versioned
`policy_decisions[]`, not permanent facts copied onto a row. Recompute them
when terms or policy change. The policy engine must be action- and
field-specific, deny unknown actions/fields/licenses, and enforce before
acquisition/cache as well as before report JSON, clipboard, HTML, PDF, TSV, or
API export. Logs, exceptions, analytics, raw-response debugging, backups,
staging, and restore paths are prohibited sinks unless explicitly approved.
The browser displays the decision; it never guesses permission from a source
name.

If persistence is later implemented, reuse the repository's existing
`eamos_private` pattern: private schema, backend-only access, explicit
anon/authenticated grant revocation, RLS as defense in depth, and strict
separation between raw payloads and normalized candidate facts, all still
policy-tagged. Normalization or derivation does not erase upstream rights; only
an explicit public-serialization decision enters the public projection. Unknown
cache rights prohibit persistence.

Supabase's 2026 default-grant change concerns newly created `public`-schema
objects and does not alter custom-schema grants. Eamos must secure
`eamos_private` explicitly regardless of project rollout. The service role
never enters browser code.

## Authoritative Sources

### Standards, calibration, and OddsPath

- [ACMG documents in development](https://www.acmg.net/ACMG/Medical-Genetics-Practice-Resources/Documents_in_Development.aspx)
- [ACMG VUS reporting statement, June 2026](https://www.gimjournal.org/article/S1098-3600%2826%2900901-9/fulltext)
- [Public SVC v4 prototype slides, 2023](https://docs.google.com/presentation/d/1ALrcD3J4ejydWvkUtCfZL_h4Chahj20HSFNM3FPINv0/edit)
- [ACMG SVC v4 pilot poster, 2026](https://www.tempus.com/wp-content/uploads/2026/03/Biesecker-L-et-al_ACMG_Piloting-the-Forthcoming-ACMGAMPCAPClinGen-Standards-for-Sequence-Variant-Classification-_Poster.pdf)
- [Hearing-loss SVC v4 pilot poster, 2024](https://morl.lab.uiowa.edu/sites/morl.lab.uiowa.edu/files/2024-10/Using%20Quantitative%20Variant%20Classification%20to%20Tackle%20the%20VUS%20Problem%20in%20Genetic%20Hearing%20Loss_%20Estella.%20National%20Society%20of%20Genetic%20Counselors%20Conference%20%282024%29.pdf)
- [ClinGen variant-classification guidance](https://www.clinicalgenome.org/tools/clingen-variant-classification-guidance/)
- [Pejaver et al. 2022 PP3/BP4 calibration](https://pmc.ncbi.nlm.nih.gov/articles/PMC9748256/)
- [Bergquist et al. 2025 additional predictor calibration](https://www.ccs.neu.edu/home/radivojac/papers/bergquist_genetmed_2025.pdf)
- [ClinGen CSpec example with capped REVEL profile](https://erepo.genome.network/cspec/ui/svi/doc/1622722963?version=1.0.0)
- [VIPdb machine-readable calibration resource](https://genomeinterpretation.org/vipdb)
- [Tavtigian et al. 2020 Bayesian points](https://pmc.ncbi.nlm.nih.gov/articles/PMC8011844/)
- [Brnich et al. 2019/2020 functional evidence](https://pmc.ncbi.nlm.nih.gov/articles/PMC6938631/)
- [ClinGen CSpec registry](https://erepo.clinicalgenome.org/cspec/)

### ESM-1b

- [Meta ESM repository](https://github.com/facebookresearch/esm)
- [official ESM1b model repository](https://huggingface.co/facebook/esm1b_t33_650M_UR50S)
- [ntranoslab ESM variant scorer](https://github.com/ntranoslab/esm-variants)
- [hosted precomputed score Space](https://huggingface.co/spaces/ntranoslab/esm_variants/tree/main)
- [Brandes et al. 2023](https://www.nature.com/articles/s41588-023-01465-0)
- [NCBI MANE](https://www.ncbi.nlm.nih.gov/refseq/MANE/#Select)
- [CC BY-NC 4.0 legal code](https://creativecommons.org/licenses/by-nc/4.0/legalcode.en)

### OMIM and LOVD

- [OMIM API documentation](https://api.omim.org/api/html)
- [OMIM primary database paper](https://pmc.ncbi.nlm.nih.gov/articles/PMC6323937/)
- [OMIM access agreement](https://omim.org/help/agreement)
- [OMIM `mim2gene.txt`](https://omim.org/static/omim/data/mim2gene.txt)
- [LOVD manual and basic API limits](https://www.lovd.nl/3.0/docs/manual.html)
- [LOVD FAQ and licensing notes](https://www.lovd.nl/3.0/faq)
- [LOVD world-wide API description (separately gated)](https://api.lovd.nl/swagger/)
- [Global Variome shared LOVD documentation](https://databases.lovd.nl/shared/docs/)

### MaveDB

- [MaveDB key concepts and data licensing](https://www.mavedb.org/docs/mavedb/getting-started/key-concepts.html)
- [MaveDB metadata guide: licenses and data-usage policies](https://www.mavedb.org/docs/mavedb/submitting-data/metadata-guide.html)
- [MaveDB downloads and CC0-only Zenodo archive](https://www.mavedb.org/docs/mavedb/finding-data/downloading.html)
- [MaveDB archive version 4, immutable Zenodo record](https://zenodo.org/records/18511521)
- [MaveDB public API quickstart](https://www.mavedb.org/docs/mavedb/programmatic-access/api-quickstart.html)
- [MaveDB score calibrations](https://www.mavedb.org/docs/mavedb/reference/score-calibrations.html)
- [MaveDB citation guidance](https://www.mavedb.org/docs/mavedb/citation.html)
- [CC0 1.0 legal code](https://creativecommons.org/publicdomain/zero/1.0/legalcode.en)
- [MaveDB API source-code repository and AGPL license](https://github.com/VariantEffect/mavedb-api)

### Persistence security

- [Supabase: securing your data](https://supabase.com/docs/guides/database/secure-data)
- [Supabase: private schemas](https://supabase.com/docs/guides/database/tables)
- [Supabase: securing the Data API](https://supabase.com/docs/guides/api/securing-your-api)
- [Supabase 2026 Data API exposure change](https://supabase.com/changelog/45329-breaking-change-tables-not-exposed-to-data-and-graphql-api-automatically)

## Confidence Boundary

This memo is an engineering and source-rights risk assessment, not legal advice
or clinical validation. The implementation plan deliberately treats final SVC
v4 content, OMIM redisplay, LOVD live reuse, non-CC0 MaveDB records, restrictive
MaveDB data-usage policies, and the NC ESM score archive as unresolved until
the named primary evidence or written permission is available.
