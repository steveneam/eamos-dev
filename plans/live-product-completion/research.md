# Live Product Completion — Evidence Baseline

Status: planning evidence; no new lane launched.

Stamped: 2026-07-22 16:29 +0000 · Codex.

## Scope

This baseline covers the four surfaces Steven named for the next parallel
campaign:

1. Workbench;
2. Variant Report;
3. Paper → Variants; and
4. Batch / Compare.

It records what is genuinely wired now, what is source-backed but incomplete,
what is a fixture or heuristic, and what must be built. It is not a launch
receipt. Read the live repository and repeat the matrices before implementation;
provider and deployment state can change.

## Product posture used by this plan

The universal-free product ratchet in `plans/README.md` supersedes historical
Free/Pro/Max, payment-wall, premium-feature, and predictor-entitlement gates.
Provider cost is therefore not a reason to leave a feature mocked or disabled.

“Free” does not erase a provider's software licence, data terms, retention,
privacy, attribution, rate limits, or scientific-validation requirements. Those
remain capability metadata and launch gates, not account tiers.

## What “material is in the repo” means

Small executable fixtures, schemas, manifests, builders, checksums, source
versions, licences, provenance, preflights, and retrieval instructions belong in
Git. Multi-gigabyte genome/model/source artifacts belong in the approved object
or mounted-asset store, with their immutable manifest and build recipe tracked in
Git. A health row saying “ready” without an artifact digest and an executed
functional test is not sufficient.

## Workbench evidence

### What is real today

- Primer design calls Primer3 and returns Primer3 thermodynamic measurements.
  Hairpin, homodimer, heterodimer, Tm, GC, placement, and product fields are not
  merely frontend samples when the backend path succeeds.
- The sequence-context resolver can produce source-backed GRCh38 windows when a
  transcript is supplied. Read-only deployment probes resolved all of these to
  2,001 bp source-backed windows: RPE65 SNV, ABCA4 SNV, USH2A SNV, HBB SNV,
  TP53 SNV, BRCA1 deletion, CFTR deletion, and F8 X-linked SNV.
- CRISPR guide discovery is a real local SpCas9/NGG sequence scan.
- AB1 parsing, Mott trimming, basic peak handling, and pairwise alignment use
  Biopython on their supported paths.
- Human GRCh38 ssODN construction has a source-backed local path for a bounded
  subset of simple cDNA SNVs.
- The deployed provider cache reports large hg38, dbSNP, ClinVar,
  RepeatMasker, phyloP, ClinGen, HMMER, and AlphaMissense assets as present.

### Release blockers

- `PrimerRequest`, `CrisprRequest`, and general `AlignRequest` do not carry a
  transcript. Only `/align/reference` does. The deployment therefore resolved
  the eight-variant reference matrix above, but ordinary Primer/CRISPR requests
  succeeded only for the hard-coded RPE65 canonical transcript; ABCA4, USH2A,
  HBB, TP53, and F8 failed with `workbench_sequence_context_unavailable`.
- `WorkbenchDesignContextV1` is validated but not executed. The backend ignores
  the selection, sequence basis, revision, and digest and redesigns around the
  queried variant window. A distant-exon selection or edited sequence can look
  bound in the UI while the engine uses different bases.
- Primer specificity is exact matching inside the submitted template, not a
  whole-genome screen. A local isPcr provider exists but is not enabled.
- The deployed dbSNP asset is not injected into the Primer3 provider, so primer
  SNP avoidance remains `not assessed` despite the material being present.
- Reverse-strand and splice-crossing genomic placement need a coordinate audit;
  the implementation currently assumes a linear forward template start.
- CRISPR on-target scoring is a local GC/poly-T heuristic. Off-target enumeration
  scans only the 2,001 bp context unless an indexed SQLite artifact is mounted.
- The deployment is in `auto` → explicit mock fallback for CRISPR off-targets;
  the required SQLite artifact is absent. A release request must fail closed,
  not return invented/deidentified loci.
- Advanced `crisprScore` families are disabled and R is absent from the runtime
  image. Rule Set 1/3, CRISPRscan, CRISPRater, CFD, and Lindel all report
  unavailable.
- Guide `cut_position` is a window offset rather than a verified genomic locus.
  Off-target requests accept any syntactically valid GRCh38 locus and do not
  prove that the guide/PAM is present there or bound to the context digest.
- ssODN falls back to a synthesized genomic window outside its narrow supported
  path, supports only simple SNVs in its local transcript path, uses a hard-coded
  `estimated_hdr_efficiency=0.12`, and applies a simplistic PAM-blocking edit.
- The endpoint called TIDE is an observed consensus-string comparison using
  `difflib`; its efficiency and R-squared values are proxies. It does not perform
  chromatogram signal decomposition and must not be released as TIDE.
- General alignment silently becomes positional alignment for large matrices.
  That is not a scientifically valid approximation and must return unavailable
  or use a bounded real aligner.
- Screening-primer generation can fall back to a synthesized reference window
  because the runtime does not inject the real window provider.
- Existing fixtures are concentrated around RPE65. Strand, indel, splice,
  distant-selection, and multi-gene regressions are under-covered.

### CRISPOR decision evidence

Steven's remembered provider is CRISPOR. Its website is free to use, but its
published licence says submitted sequence and genome identifiers are retained
for at least 24 months, and local version 4+ execution has separate organisation
licensing. It is therefore unsuitable as a silent default for user sequence.

The preferred reproducible default is a CRISPOR-equivalent local stack:

- real genome-wide candidate enumeration over the mounted reference;
- Rule Set 3 on-target scoring via a maintained implementation such as `rs3`;
- MIT and CFD off-target scores via the MIT-licensed `crisprScore` algorithms or
  a verified equivalent; and
- explicit algorithm/version/context fields per score.

CRISPOR web can remain an optional, separately consented comparison provider
after terms, retention, and rate limits are surfaced. Relevant primary sources:

- <https://raw.githubusercontent.com/maximilianh/crisporWebsite/master/LICENSE.txt>
- <https://github.com/crisprVerse/crisprScore>
- <https://pypi.org/project/rs3/>

## Variant Report evidence

### What is real today

Read-only calls to the current development deployment resolved and produced
reports for RPE65, ABCA4, USH2A, HBB, BRCA1, and CFTR. Coordinate resolution,
local ClinVar, gene-disease rows, publication discovery, and some gnomAD,
ClinGen, ClinicalTrials.gov, and gene-context paths are real on suitable
variants. Source URLs and source-version fields are present in the response.

The UI reading hierarchy is already implemented. This campaign is a truth and
coverage campaign, not a visual rewrite.

### Release blockers found by the live matrix

- Report completeness varies sharply by variant. A valid report must tolerate
  an honestly empty section, but the current payload often labels a provider
  `local` while its row says `*_not_found`, which can overstate availability.
- Evidence status and rendered provenance disagree in places: local ClinVar and
  source-table evidence can appear as fallback in the report provenance layer.
  One canonical status derivation is required.
- Computational annotations are the largest systematic gap. The live matrix
  reported absent ESM-1b, calibrated SpliceAI, CAPICE, REVEL, and PrimateAI-3D
  artifacts; several non-SNVs correctly had no missense predictor result, but
  the section needs per-predictor applicability rather than one ambiguous
  aggregate status.
- Molecular context was missing for ABCA4, USH2A, HBB, BRCA1, and CFTR, with
  constraint, dosage, structural/CNV, hotspot, or protein-domain hydration
  absent depending on the variant.
- VEP and SpliceAI external calls fell back or timed out for HBB, BRCA1, and
  CFTR. Fallback fixture mismatch warnings correctly prevented RPE65 bleed, but
  a launch path still needs stable local/cache-backed coverage or a truthful
  unavailable state.
- Several sections are lower-match-level gene discovery, not exact-variant
  evidence. Clinical-trial rows must retain that distinction in every display
  and export.
- Source currency/version pins are incomplete for several cache/live sources.
- The same variant/allele can be represented differently across resolvers.
  Cross-source identity and left-normalisation must be asserted, not assumed.

## Paper → Variants evidence

### What Eamos has now

- Authenticated bounded text/PDF input, signature and size checks, temporary-file
  cleanup, rate limiting, deadlines, run persistence, cancel/delete, and safe
  frontend error handling are implemented.
- Candidate resolution is already Eamos-specific and fail closed: candidates
  pass through search-input resolution and remain unresolved when coordinates
  are ambiguous.
- The PDF seam is pluggable, but defaults to pypdf. pdfplumber is optional and
  PyMuPDF/fitz is listed despite its production licensing problem.
- The default `LLM_PROVIDER=mock` path is a deterministic regex extractor, but
  its provenance says `mock_paper_variants_extractor` while the route disclosure
  says `Eamos deterministic extractor`. This is internally contradictory.
- Source metadata is a shallow first-line/DOI/PMID/year heuristic. Page, section,
  span, and extraction-tier provenance are absent.

### Selom reference architecture inspected

The sister Selom repository contains a stronger deterministic paper substrate:

- `app/backend/papers.py`: PDFium page-preserving text and raster extraction,
  pypdf metadata/images, permissive shipped dependencies, and explicit page
  markers. Selom chose PDFium because a real publisher PDF yielded 0 characters
  through pypdf and about 99.6k through PDFium.
- `app/backend/paper_metadata.py`: XMP/text/Info/filename identifier extraction,
  DOI-first OpenAlex → CrossRef → PubMed enrichment, cached and fail soft.
- `app/backend/extract/ingest.py`: a typed main-document plus supplement bundle;
  PDF supplements contribute text and XLSX/CSV supplements expose sheet
  inventories.
- `app/backend/extract/routing/segment.py`: deterministic methods/results/body/
  references/caption segmentation; bibliography exclusion; recovery of
  letter-spaced caption markers, private-use-glyph numbers, line-numbered
  manuscripts, and headerless citation-dense reference tails.
- `app/backend/extract/routing/route.py`: exact and token-canonical recovery
  passes, section weighting, evidence hits, confidence, and a paper-wide
  inventory separated from weaker per-figure attribution.
- `app/backend/extract/routing/verify.py`: AI verifies ambiguous deterministic
  output and proposes vocabulary additions; it never replaces the offline core.

Selom's paper corpus is intentionally absent from this host and is not to be
copied into Eamos. The architecture and permissive dependency choices can be
adapted; Eamos needs its own synthetic and open-access variant-paper corpus with
licence, checksum, and expected-mention manifests.

### Eamos-specific elaboration required

Replace Selom's skill vocabulary with a typed variant-mention grammar and
context router:

- HGVS c./g./n./r./m./p. forms, transcript/accession-qualified forms, rsIDs,
  common legacy forms, substitutions, del/dup/ins/delins, splice forms, and
  deliberately unsupported notations;
- gene/transcript association within page/section/sentence bounds;
- clinical allele, case/proband, family/segregation, experimental construct,
  engineered rescue, comparator/background, and bibliography-only contexts;
- page, section, character span, exact surface text, bounded quote, extraction
  tier, and confidence on every mention;
- grouping of cDNA/protein/genomic/rs representations that refer to the same
  asserted allele without declaring them equivalent until the Eamos resolver
  proves it; and
- references excluded from candidate generation by default.

The deterministic layers should be the ordinary free path. Optional OCR/vision
or gateway adjudication can handle image-only PDFs and ambiguous mentions only
after server disclosure and explicit consent.

## Batch / Compare evidence

### What is real today

- Authenticated upload/create/get/list/page/cancel/delete/export routes exist.
- VCF parsing, size bounds, deduplication, PASS/AF/region/panel filters,
  owner-bound upload refs, limited lookup concurrency, durable workflow rows,
  run history, pagination, and UI progress/resume states are implemented.
- The frontend no longer silently substitutes a completed mock job on ordinary
  Batch request failures.

### Release blockers

- `create_app()` constructs `BatchService` before `LookupService`. The API's
  private `_service()` helper currently repairs that ordering by lazily calling
  `bind_lookup_service()` before upload/create/get/cancel/delete operations, so
  the ordinary HTTP create path is wired today. The service itself nevertheless
  treats a missing lookup service as a successful INFO-passthrough mode. A
  composition refactor, alternate caller, or startup race can therefore produce
  plausible completed rows without Eamos annotation. Startup must inject and
  assert the lookup dependency, and release mode must fail closed if it is
  absent.
- The in-process worker thread is not a durable queue. A process restart can
  leave a persisted running job without a worker lease/recovery path.
- The backend panel catalog is a hand-written local launch list labelled
  `custom`; its own warning says PanelApp/ClinGen/GenCC materialisation is
  pending. Disease resolution is a two-MONDO special case and upload-ref panel
  resolution is unimplemented.
- `app/web/lib/panels.ts` catches every error and falls back to
  `panels.mock.ts`, whose illustrative source/version labels can masquerade as
  PanelApp or ClinGen data. Ordinary live mode must fail closed.
- Batch correctness is not yet ratcheted to “each completed row equals a direct
  single-variant lookup at the same source snapshot.”
- Multi-sample genotype handling, left-normalisation, reference validation,
  duplicate equivalence, post-lookup filtering, restart recovery, load shedding,
  and large export streaming need an explicit matrix.
- The parser materializes every accepted allele into a Python list and rejects
  input after 5,000 parsed variants, before panel/gene filtering. That protects
  the service but prevents an ordinary exome VCF from reaching the feature's
  intended filter-first workflow. The raw-record envelope and the expensive
  annotation envelope must be separate.

### Open-source engine assessment

The Batch implementation should reuse mature genomics primitives and keep the
Eamos-specific work in orchestration, provenance, source reconciliation, and
the Report-equivalence contract. `pysam==0.24.0` is already pinned for
non-Windows backend builds, but the current upload path does not use it.

| Candidate | Useful role | Licence/posture | Decision for Eamos |
| --- | --- | --- | --- |
| `pysam` / HTSlib | Streaming VCF/BCF, BGZF, tabix queries | MIT Python package; wraps the HTSlib family | Preferred in-process parser baseline. Benchmark against `cyvcf2` before freezing, but do not maintain a bespoke VCF parser as the WES engine. |
| `cyvcf2` | Fast VCF/BCF iteration and region queries | MIT | Benchmark challenger when genotype-heavy parsing is the bottleneck; avoid carrying two production parsers after the decision. |
| `bcftools norm/view/filter/csq` | Reference checking, left alignment, multiallelic splitting, filtering, optional haplotype-aware consequences | MIT/Expat or GPL depending build | Preferred normalization oracle and possible bounded subprocess engine. Invoke with a fixed argv, resource limits, private temp paths, no shell, and a pinned binary/SBOM. |
| `vcfanno` | Fast joins from tabix-indexed VCF/BED sources | MIT | Candidate bulk join accelerator for already-filtered rows. Adopt only if it remains byte-for-byte reconcilable with Eamos direct lookup source semantics. |
| Ensembl VEP offline | Transcript consequence, HGVS, JSON/VCF output | Apache-2.0 code; caches/data need their own manifest and terms | Preferred consequence benchmark and likely local engine when the pinned GRCh38/MANE-compatible cache fits deployment. Run offline for privacy. |
| SnpEff/SnpSift | Local consequence and annotation/filtering | MIT; Java runtime and human database require material/runtime budget | Secondary benchmark/fallback candidate, not a second simultaneous truth engine. |
| Nirvana | Broad VCF-to-JSON annotation | PolyForm Strict; upstream says the open-source tool is no longer actively maintained | Reject for the universal Eamos launch stack. |

Primary sources:

- <https://pysam.readthedocs.io/en/stable/api.html#pysam.VariantFile>
- <https://github.com/brentp/cyvcf2>
- <https://samtools.github.io/bcftools/bcftools>
- <https://github.com/brentp/vcfanno>
- <https://www.ensembl.org/info/docs/tools/vep/script/vep_cache.html>
- <https://github.com/Ensembl/ensembl-vep>
- <https://pcingola.github.io/SnpEff/>
- <https://github.com/Illumina/Nirvana>

### Source-backed gene and panel materials

The clean launch substrate is a versioned local build, not a live panel API on
every upload:

- MANE Select + Plus Clinical GFF/GTF/summary files provide GRCh38 transcript
  and exon coordinates. MANE currently exposes bulk GFF3, GTF, FASTA, and
  summary downloads and explicitly matches RefSeq/GENCODE transcripts.
- HGNC's complete and withdrawn-symbol datasets are CC0 and provide approved
  symbols, aliases, prior symbols, and stable HGNC identifiers.
- GenCC's downloadable gene-disease assertions are CC0. OMIM-derived fields are
  intentionally absent from that download and must not be reconstructed.
- Mondo's release artifacts are CC BY 4.0 and provide versioned disease IDs and
  mappings for disease-driven panel resolution.
- Existing Eamos ClinGen, ClinVar, gnomAD, dbSNP, reference, and predictor
  assets remain independently licensed/versioned evidence sources; inclusion
  in a Batch join does not change their terms.

Genomics England PanelApp is useful as a separately identified comparison
source, but its December 2019 terms prohibit commercial and diagnostic use
without a separate agreement and impose downstream restrictions on PanelApp
outputs. A free Eamos price does not itself satisfy those terms. It must remain
launch-gated unless the rights are cleared; its labels may never be attached to
the CC0/custom catalog.

Primary sources:

- <https://www.ncbi.nlm.nih.gov/refseq/MANE/>
- <https://hgnc.genenames.org/>
- <https://search.thegencc.org/download>
- <https://mondo.monarchinitiative.org/pages/download/>
- <https://prod-media-panelapp.genomicsengland.co.uk/media/files/GEL_-_PanelApp_Terms_of_Use_December_2019.pdf>

### Recommended WES/panel-first pipeline

1. Admit `.vcf` and `.vcf.gz` for GRCh38 called sites; add BCF only after format
   parity tests. Reject gVCF blocks, WGS-scale uploads, cohort-scale matrices,
   unsupported contigs/builds, and SV/CNV claims with a typed explanation.
2. Stream the file once. Validate header/build/reference dictionary, split
   alleles, preserve sample/genotype provenance, and apply cheap PASS/quality/
   region filters without retaining the full file in memory.
3. Normalize and verify REF against the pinned GRCh38 reference. Record the
   original allele and the normalized canonical allele; never silently repair a
   bad REF.
4. Intersect with source-backed MANE gene/exon plus configured splice-flank
   intervals, whole-gene bounds, or a validated capture BED and the chosen
   GenCC/custom gene set. This happens before expensive annotation. Treat input
   `GENE`/`ANN` values as provenance rather than the filtering authority.
5. Deduplicate equivalent normalized alleles while retaining every originating
   row/sample. Enforce the expensive-work cap on variants remaining after this
   filter, not on all raw exome records.
6. Run the shared local annotation core or pinned offline VEP/bulk join over the
   filtered set. Reconcile each returned field to the same source snapshot and
   semantics used by direct Report lookup. Apply consequence/frequency/
   classification/evidence filters only after annotation, recording unavailable
   sources separately from true non-matches.
7. Persist only owner-bound job state and normalized result/provenance by
   default. Raw VCF bytes and unneeded genotype fields expire on consume,
   cancel, failure, restart recovery, and delete.
8. Page and stream exports server-side. The browser never holds the whole exome
   result set merely to filter or download it.

The first supported envelope is single/proband and small-family WES or targeted
panels. The existing 5,000-row limit becomes an initial **post-filter annotation
cap**, subject to measurement. Raw compressed bytes, decompressed bytes, record
count, sample count, post-filter rows, memory, wall time, and queue concurrency
receive separate neutral limits derived from benchmarks on the actual free
deployment. WGS can follow only after a streaming/storage/queue budget proves
it; it is not a paid tier.

## Cross-surface conclusion

The four surfaces have substantial real infrastructure, but UI completion and
request wiring have outpaced scientific execution in several places. The next
campaign must use one rule everywhere: a release feature is either executed by
the named algorithm/provider over the declared input, or it is visibly
unavailable. A request that returns a fixture, heuristic proxy, unrelated
window, VCF passthrough, or invented locus is not a live implementation.
