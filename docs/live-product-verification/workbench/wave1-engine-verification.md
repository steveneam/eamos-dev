# Workbench Wave 1 Engine Verification

Status: review candidate
Verified: 2026-07-22
Scope: backend Workbench engines and request-lifetime execution only

## Release Claim Posture

Workbench Contract V2 inputs are independently resolved against the configured
sequence source, reference-digest checked, sparse-edit replayed, and
selection-digest checked before an engine receives bases. Results bind back to
the same context digest. Raw selection sequences, AB1 bytes, and subprocess
payloads are not added to disclosures, errors, URLs, or durable state.

An executed result is deliberately reported as `validation_status=unvalidated`
and tied to `workbench_live_product_v2.synthetic`. The current synthetic matrix
is regression evidence, not a clinical or wet-lab validation claim.

| Surface | Current truthful state | Explicitly not claimed |
| --- | --- | --- |
| Primer design | Primer3 runs on the verified edited selection; exact Sanger/qPCR constraints are disclosed. Primer positions map through substitutions, insertions, deletions, delins, and reverse-oriented contexts. | Whole-genome specificity or dbSNP masking when their mounted providers are absent. |
| CRISPR guide discovery | Exact SpCas9 NGG scan on the verified selection, genomic guide/PAM/cut identity, local GC/poly-T descriptive ranking, and in-selection Hsu/MIT risk. | Rule Set 3, efficiency probability, CFD, or genome-wide off-target coverage. |
| CRISPR off-targets | Runs only with a verified guide identity plus an immutable indexed-artifact manifest and SHA-256; each returned site carries an explicit Hsu/MIT cutting score. | Mock sites, CFD, or an unmanifested index. |
| Screening primers | Primer3 runs only on source-verified reference windows; a supplied template must match the verified window. | Generated/mock reference windows. |
| Alignment and AB1 trace alignment | Bounded Biopython or Smith-Waterman alignment on the verified selection; 5,000 bases per input and 4,000,000 matrix cells maximum. | Positional fallback masquerading as alignment. |
| ssODN | Designs a donor only from a local MANE/GRCh38 transcript artifact or source-backed resolver window. HDR efficiency is explicitly `not_assessed`, carries no number, and includes an unavailable capability disclosure. | Fixed or inferred HDR-efficiency values, or a donor derived from fixture-only sequence context. |
| TIDE | Typed HTTP 503 before multipart trace bytes are read. The CLI is labelled descriptive consensus comparison. | Editing efficiency, R-squared, indel spectrum, or TIDE decomposition. |

Legacy fixture mode remains available only when explicitly selected for test or
sample compatibility. Supplying a V2 context always selects the verified live
path and cannot fall through to fixture responses.

## Exact Primer3 Profiles

Both profiles pass these global arguments to `primer3-py`:

```text
PRIMER_TASK=generic
PRIMER_NUM_RETURN=3
PRIMER_OPT_SIZE=20
PRIMER_MIN_SIZE=18
PRIMER_MAX_SIZE=25
PRIMER_MIN_TM=<request tm_min>
PRIMER_OPT_TM=(<request tm_min> + <request tm_max>) / 2
PRIMER_MAX_TM=<request tm_max>
PRIMER_MIN_GC=35.0
PRIMER_MAX_GC=70.0
PRIMER_MAX_NS_ACCEPTED=0
PRIMER_THERMODYNAMIC_OLIGO_ALIGNMENT=1
PRIMER_PRODUCT_SIZE_RANGE=[[<request minimum>, <request maximum>]]
```

Sanger profile `sanger.v1` additionally sets
`PRIMER_MAX_POLY_X=5` and `PRIMER_GC_CLAMP=0`. qPCR profile `qpcr.v1`
sets `PRIMER_MAX_POLY_X=4`, `PRIMER_GC_CLAMP=1`, and
`PRIMER_MAX_END_GC=3`.

Template-only specificity is disclosed as such. Whole-genome specificity is
available only through the fixed-argument UCSC `isPcr` adapter. dbSNP masking
is active only when both a mounted indexed VCF and its index are present; the
adapter performs a bounded interval query and converts variants into Primer3
excluded regions.

## Serial Composition Requests

These requests are documentation only. This wave did not change dependencies,
download assets, materialize an index, mutate a provider, or deploy anything.

| Request | Exact pin / identity | License and footprint | Runtime seam and acceptance check |
| --- | --- | --- | --- |
| Primer3 | `primer3-py==2.3.0` | GPLv2; current installed files are about 12 MB and the CPython 3.12 Linux wheel is about 3.1 MB. Commercial distribution needs license review. [PyPI record](https://pypi.org/project/primer3-py/2.3.0/) | Python import, then a tiny deterministic `design_primers` call for both profiles. Missing/import/runtime failure remains 503; no alternate algorithm. |
| Pairwise alignment and AB1 parsing | `biopython==1.87` | Biopython License; current installed files are about 19.5 MB. [PyPI record](https://pypi.org/project/biopython/1.87/) | Import `Bio.Align` and parse the checked-in synthetic AB1 fixture. The bounded local Smith-Waterman implementation is the alignment fallback; AB1 parsing itself stays unavailable if the parser is missing. |
| Indexed dbSNP reads | `pysam==0.24.0` | MIT; current installed files are about 76.3 MB. [PyPI record](https://pypi.org/project/pysam/0.24.0/) | Open and query a tiny bgzip/tabix VCF fixture, then report only release metadata and counts. No VCF pathname is exposed. Missing VCF/index means `dbsnp_masking:not_assessed`. |
| Rule Set 3 sequence score | `rs3==0.0.18`, wheel SHA-256 `1c10ac0d6be46c2e1a71a3bd400d2b6fefcc7dff19de06c83e0854f16dfd5d2f` | Apache-2.0; wheel 6.2 MB before transitive dependencies. The release is marked alpha. [PyPI record](https://pypi.org/project/rs3/0.0.18/) | Add a structured Python adapter for 30-mer sequence-only scoring, with no request-time network or target-feature retrieval. Health check scores the upstream documented pair and validates finite outputs. Until that adapter and a validation matrix land, V2 says `advanced_on_target_model_unavailable`. |
| crisprScore CFD/MIT and optional Rule Set 3 | R `4.6.x`, Bioconductor `3.23`, `crisprScore==1.16.0`, `crisprScoreData==1.16.0` | MIT for crisprScore; container growth must be measured in the composition lane because R/Bioconductor transitive packages dominate. Bioconductor 3.23 publishes 1.16.0 for R 4.6. [Package record](https://bioconductor.org/packages/release/bioc/html/crisprScore.html) | Existing fixed argv is `Rscript --vanilla <temporary-script>` with JSON on stdin, timeout, no shell, request-time installs disabled, and sanitized stderr. Health check must exercise RuleSet1, RuleSet3, MIT, and CFD separately. V2 fails closed until structured score provenance is returned. |
| Whole-genome primer specificity | UCSC `isPcr` binary plus UCSC `hg38.2bit`, source commit and both SHA-256 values captured in an approved manifest | `isPcr` is a UCSC license exception requiring a separate commercial license; do not bundle or promote before entitlement. [UCSC licensing](https://genome.ucsc.edu/license/) The recorded `hg38.2bit` is 835,393,456 bytes with MD5 `dcc3ea27079aa6dc3f9deccd7275e0f8`. | Fixed argv only: size/perfect/good bounds, mounted two-bit path, `stdin`, `stdout`; primer query on stdin; timeout and bounded parse. Health check must find one known intended amplicon and reject a nonspecific pair. Until license and manifest approval, disclose template-only specificity. |
| Genome-wide SpCas9 index | Schema `eamos.crispr_spcas9_offtargets.v1`, GRCh38 source MD5 above, exact built-artifact SHA-256 and manifest ID required | Preliminary order-of-magnitude is roughly 390 million NGG targets and 62 GB at the current 160-byte estimator; provision at least 130 GB build headroom and measure with the existing estimator before approval. The deployed immutable artifact is likely about 65–70 GB, but its manifest is authoritative. | Run existing `estimate`, `build`, `verify`, and `manifest` commands offline. Acceptance requires build/release match, positive target count meeting the estimate gate, SQLite integrity, manifest SHA-256, and a known-guide smoke. Runtime remains unavailable if any identity field is missing. |
| TIDE replacement evaluation | Candidate only: Tracy `0.8.9`; no accepted runtime pin yet | Tracy is BSD-3-Clause and its latest published release is 0.8.9. [Project and release](https://github.com/gear-genomics/tracy) | Tracy is not automatically equivalent to TIDE. Accept only after the response contract distinguishes descriptive comparison from validated chromatogram-signal decomposition and a truth set establishes efficiency, fit, and spectrum semantics. Current endpoint remains 503. |

The Python `rs3` and R `crisprScore` requests overlap for Rule Set 3. The
composition lane should benchmark one on-target authority, not silently blend
their outputs. `crisprScore` remains the requested CFD/MIT authority because
the current backend already has a fixed, sanitized R boundary.

## Frozen Contract Amendments Applied

### ssODN

`CrisprSsodnDesign.estimated_hdr_efficiency` is now nullable and paired with a
required typed status and capability disclosure:

```text
estimated_hdr_efficiency: float | null
hdr_efficiency_status: executed | not_assessed | unavailable
hdr_efficiency_disclosure: CapabilityExecutionDisclosureV2
```

Contract tests reject a numeric value without an executed disclosure and accept
`not_assessed` with no number. The dedicated ssODN route now returns the donor
sequence when its sequence basis is source-backed, while fixture-only and
insufficient reference windows fail closed with typed client errors. The
separate legacy `CrisprResponse.ssodn` shape remains unchanged and no new value
is fabricated into it.

### TIDE

`CrisprTideResponse` now carries a required `analysis_kind` discriminator and
conditionally validated fields:

```text
analysis_kind=tide
  -> editing_efficiency, r_squared, indel_spectrum, executed disclosure required

analysis_kind=descriptive_trace_comparison
  -> consensus_difference_fraction, sequence_identity, differences required
  -> editing_efficiency, r_squared, indel_spectrum forbidden
```

Contract tests reject descriptive payloads carrying TIDE claims. The contract
amendment does not manufacture validation: until an external truth-set
validation lands, the HTTP route still does not read trace uploads and returns
`crispr_tide_decomposition_unavailable`.

## Security and Negative Evidence

- Context variant, transcript, build, strand, interval, available source
  identity metadata, reference allele, reference digest, sparse edits, and
  effective digest are checked before execution. If the resolver lacks
  versioned source identity metadata, the disclosure omits `source_release`
  and adds an explicit requirement instead of echoing an unverified value.
- Inserted bases intentionally have no genomic coordinate. Guide or primer
  identities crossing a non-contiguous/inserted segment are omitted rather
  than assigned a false locus.
- Subprocess adapters use fixed argument arrays with `shell=False` behavior;
  paths and sequence-bearing stderr are not returned to clients.
- TIDE unavailability is evaluated before multipart bytes are read. AB1 inputs
  are parsed after context verification and retained for request lifetime only.
- Off-target execution requires immutable manifest identity. Mock rows are
  suppressed on Contract V2 and in live configuration.
- Oversized alignment inputs return a typed client error before allocating an
  unbounded dynamic-programming matrix.
- Primer and local CRISPR design reject selections over 20,000 bases; indexed
  dbSNP masking also caps the queried interval at 20,000 bases and returned
  records at 10,000 before declining the assessment.

## Verification Commands

The lane passed the focused sequence-context, primer, CRISPR, off-target,
trace, CLI, and V2 integration suite, including insertion/deletion/delins,
reverse orientation, transcript-minus, distant-UTR selection, digest mismatch,
artifact identity, matrix-limit, and subprocess-sanitization cases.

Release review must also retain these repository ratchets:

```text
pytest -q tests/test_boundary.py tests/test_live_product_contract.py
node scripts/eamos-web-boundary.mjs
git diff --check
```
