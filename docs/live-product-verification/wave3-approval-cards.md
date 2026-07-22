# Wave 3 material approval cards

Status: approval requested; no card executed

Evidence frozen: 2026-07-22 UTC

These cards are the exact gate required by the live-product completion plan.
This document does **not** authorize a download, build, upload, mount, provider
flip, environment change, cloud mutation, or deployment. Approval is by card
ID. A changed source identity, byte count, checksum, destination, or action
requires a replacement card.

## Recommended approval set

Approve these eight bounded cards together:

```text
APPROVE W3-REF-01, W3-BCF-01, W3-MANE-01, W3-HGNC-01,
W3-GENCC-01, W3-MONDO-01, W3-AM-01, and W3-PAPER-01 exactly
as written in docs/live-product-verification/wave3-approval-cards.md.
Do not execute any item in the deferred/NO-GO table.
```

The listed payloads total 1,796,448,335 bytes (1.673 GiB), plus small source
metadata files. The GRCh38 build needs at least 8 GiB temporary disk. This
approval set does not include the approximately 62 GiB CRISPR index, the
existing 29.55 GB dbSNP object, a VEP cache, OCR models, or restricted
predictors.

## W3-REF-01 — canonical GRCh38.p14 reference bundle

| Field | Frozen value |
| --- | --- |
| Source | NCBI RefSeq `GCF_000001405.40_GRCh38.p14_genomic.fna.gz`, [immutable assembly directory](https://ftp.ncbi.nlm.nih.gov/genomes/all/GCF/000/001/405/GCF_000001405.40_GRCh38.p14/), plus its `assembly_report.txt`, `md5checksums.txt`, and `uncompressed_checksums.txt` |
| Terms/version | NCBI public data and disclaimer; assembly `GCF_000001405.40`, GRCh38.p14, RefSeq annotation release RS_2025_08 |
| Size | source gzip 972,898,531 B; source FASTA 3,339,739,109 B uncompressed; assembly report 80,454 B |
| Checksums | source gzip MD5 `c30471567037b2b2389d43c908c653e1`; uncompressed FASTA MD5 `689762f267eafe361b6ee4b21638eb51`; every received and derived file also gets SHA-256 in the local manifest |
| Destination | `/var/data/eamos/bio_assets/reference/grch38-p14/canonical.fa`, `.fai`, source metadata, and `manifest.json` |
| Builder | new offline `eamos_grch38_runtime_build`: verify upstream identities, map RefSeq accessions through the assembly report, retain only 1–22/X/Y/MT, rename headers to the Batch contract (`1`…`22`,`X`,`Y`,`MT`), build `.fai`, then verify all hashes |
| Runtime mount | existing backend `/var/data/eamos/bio_assets` mount; no public/object URI in API output |
| Cadence | immutable; review NCBI assembly status quarterly, never auto-upgrade |
| Rollback | atomically remove the normalizer manifest or restore the prior manifest; capability returns typed `unavailable` |
| Probe | exact contig set and lengths; `1:68444869=T`; one REF match, one REF mismatch, one left-normalized indel; reject alt/patch contigs |

## W3-BCF-01 — bcftools/htslib 1.24 runtime

| Field | Frozen value |
| --- | --- |
| Sources | [bcftools 1.24](https://github.com/samtools/bcftools/releases/download/1.24/bcftools-1.24.tar.bz2) and [htslib 1.24](https://github.com/samtools/htslib/releases/download/1.24/htslib-1.24.tar.bz2) |
| Terms/version | bcftools 1.24 under the MIT/Expat choice, GSL disabled; htslib 1.24 MIT/Expat with the bundled CRAM code under modified BSD; notices retained |
| Size | 8,272,861 B and 5,004,265 B source archives; derived runtime bundle capped at 64 MiB |
| Checksums | bcftools SHA-256 `8caddc22610ee2851666047c859bb91da0c1e32d0c2ec553db6f153ad130e46f`; htslib SHA-256 `28a8de191381c7a97a35675ceac76fa1ea95e7b678d6a2e9d600a7874e4077de`; record output binary and library SHA-256 values |
| Destination | `/var/data/eamos/bio_assets/runtime/bcftools-1.24/` beside the W3-REF-01 normalizer manifest |
| Builder | pinned Bookworm build container, no GSL/plugins/network after source verification; fixed build argv; record compiler, linked libraries, SBOM, and notices |
| Runtime mount | existing backend data mount; manifest points only to verified paths |
| Cadence | security review monthly; upgrades require a new card and parity matrix |
| Rollback | remove/restore the normalizer manifest; never search the host `PATH` |
| Probe | `bcftools --version`; deterministic split/left-normalize/REF-mismatch matrix against W3-REF-01 |

The Wave 2 manifest's GPL-only enum/notice must be amended to the selected
MIT/Expat build truth before this card can report ready.

## W3-MANE-01 — MANE v1.5 intervals and transcript identity

| Field | Frozen value |
| --- | --- |
| Sources | NCBI MANE v1.5 [RefSeq genomic GFF](https://ftp.ncbi.nlm.nih.gov/refseq/MANE/MANE_human/release_1.5/MANE.GRCh38.v1.5.refseq_genomic.gff.gz) and [summary](https://ftp.ncbi.nlm.nih.gov/refseq/MANE/MANE_human/release_1.5/MANE.GRCh38.v1.5.summary.txt.gz) |
| Terms/version | NCBI public data and disclaimer; MANE v1.5 (Select + Plus Clinical), published 2025-12-04 |
| Size | 8,271,212 B + 1,115,288 B compressed; builder rejects expansion over 256 MiB total |
| Checksums | NCBI publishes no adjacent digest for these two files; enforce the exact byte counts, compute SHA-256 during the approved transfer, and freeze it before build/promotion |
| Destination | `/var/data/eamos/bio_assets/mane/v1.5/` with raw files, normalized interval/tabix index, transcript model, and manifest |
| Builder | new bounded streaming parser; Select/Plus Clinical only; canonical GRCh38 contigs; explicit strand/exon/CDS/splice-flank model; join by HGNC ID; sorted/indexed output |
| Runtime mount | existing backend data mount shared by Batch, Workbench ssODN, Paper resolution, and Report context |
| Cadence | review each MANE release; manual promotion only |
| Rollback | restore the prior versioned manifest or typed `unavailable` |
| Probe | RPE65 `NM_000329.3`, USH2A canonical transcript, plus/minus-strand exon and splice-flank checks, and the v1.5 patch-contig exclusion ledger |

## W3-HGNC-01 — HGNC 2026-07 quarterly symbol snapshot

| Field | Frozen value |
| --- | --- |
| Sources | generation-pinned [complete set](https://storage.googleapis.com/download/storage/v1/b/public-download-files/o/hgnc%2Farchive%2Farchive%2Fquarterly%2Ftsv%2Fhgnc_complete_set_2026-07-07.tsv?generation=1783428431133303&alt=media) and [withdrawn set](https://storage.googleapis.com/download/storage/v1/b/public-download-files/o/hgnc%2Farchive%2Farchive%2Fquarterly%2Ftsv%2Fwithdrawn_2026-07-07.tsv?generation=1783428430916836&alt=media) |
| Terms/version | HGNC imposes no access/use restriction (CC0 posture); quarterly snapshot 2026-07-07 |
| Size | 16,913,890 B + 258,931 B; files are uncompressed TSV |
| Checksums | GCS MD5 `cd41d33955722de9ac0e14a2557ef5fc` and `af5cf8bd3d900fc31eec07b8816e861a`; additionally freeze SHA-256 |
| Destination | `/var/data/eamos/bio_assets/hgnc/2026-07-07/` plus normalized symbol/alias index and manifest |
| Builder | bounded TSV parser; approved/alias/previous/withdrawn mappings; duplicate and ambiguous aliases stay explicit |
| Runtime mount | existing backend data mount |
| Cadence | quarterly |
| Rollback | restore previous snapshot manifest |
| Probe | RPE65 and USH2A approved IDs, a previous symbol, a withdrawn symbol, ambiguity rejection, and unknown symbol |

## W3-GENCC-01 — GenCC new-format weekly snapshot

| Field | Frozen value |
| --- | --- |
| Source | [GenCC new CSV](https://thegencc.org/download/action/submissions-export-csv?format=new), fetched only with expected ETag `3538ff4c3e3f151b47bdffdca2524e1a` |
| Terms/version | CC0 1.0; snapshot timestamp 2026-07-19T06:00:44Z; OMIM rows are excluded by GenCC |
| Size | 26,513,347 B, uncompressed CSV |
| Checksums | server ETag is MD5 `3538ff4c3e3f151b47bdffdca2524e1a`; abort if ETag/size changed; additionally freeze SHA-256 |
| Destination | `/var/data/eamos/bio_assets/gencc/2026-07-19/` plus normalized assertions and manifest |
| Builder | update the bounded parser to the new `sgc_id,version_number,...` format; deduplicate by stable ID/version; preserve submitter, disease, MOI, classification, and date |
| Runtime mount | existing backend data mount |
| Cadence | inspect weekly; promote at most monthly after diff/probes |
| Rollback | restore prior snapshot manifest |
| Probe | known positive and negative disease–gene pairs, version supersession, OMIM absence, unknown disease, and duplicate rejection |

## W3-MONDO-01 — Mondo v2026-07-06

| Field | Frozen value |
| --- | --- |
| Source | immutable [Mondo release asset](https://github.com/monarch-initiative/mondo/releases/download/v2026-07-06/mondo.json) |
| Terms/version | CC BY 4.0; `v2026-07-06`, published 2026-07-07 |
| Size | 107,273,669 B JSON |
| Checksums | upstream GitHub SHA-256 `80b8658b4ec7da7699f7f8f6460425396e42f1bb7fbead837469ebf1907f7c30` |
| Destination | `/var/data/eamos/bio_assets/mondo/v2026-07-06/` plus normalized label/synonym/xref graph and manifest |
| Builder | bounded streaming ontology reader; human-disease scope; obsolete/replacement relations retained; attribution bundled |
| Runtime mount | existing backend data mount |
| Cadence | review monthly; manual promotion |
| Rollback | restore prior release manifest |
| Probe | exact MONDO ID, synonym, obsolete replacement, unknown term, and disease-to-GenCC join |

## W3-AM-01 — AlphaMissense hg38 predictions

| Field | Frozen value |
| --- | --- |
| Source | Zenodo record [10813168](https://zenodo.org/records/10813168), file `AlphaMissense_hg38.tsv.gz` |
| Terms/version | CC BY 4.0 predictions; immutable DOI `10.5281/zenodo.10813168`; not clinically validated or approved |
| Size | 642,961,469 B compressed runtime file; file + derived index/manifest capped at 800 MiB |
| Checksums | upstream MD5 `9fd167735f16a1b87da6eb3e4c25fcb5`; compute source and `.tbi` SHA-256 |
| Destination | `/var/data/eamos/bio_assets/predictors/alphamissense/AlphaMissense_hg38.tsv.gz`, `.tbi`, and manifest |
| Builder | existing `eamos_alphamissense_runtime_materialize`; stream, verify, tabix, manifest, then sanitized preflight; no startup/request download |
| Runtime mount | existing private backend data mount; never frontend-readable |
| Cadence | immutable; review record concept annually |
| Rollback | remove asset configuration and return only AlphaMissense `unavailable` |
| Probe | ready/hash/index checks; one manifested exact hit, one not-found, one allele mismatch, one corrupt-index case; preserve independent predictor behavior |

## W3-PAPER-01 — CC-BY PDF validation corpus

| Field | Frozen value |
| --- | --- |
| Sources | Europe PMC PDFs for [PMC5765404](https://europepmc.org/api/getPdf?pmcid=PMC5765404) (VariantValidator), [PMC6282708](https://europepmc.org/api/getPdf?pmcid=PMC6282708) (`hgvs` package update), [PMC9174243](https://europepmc.org/api/getPdf?pmcid=PMC9174243) (USH2A variant), and [PMC11660784](https://europepmc.org/api/getPdf?pmcid=PMC11660784) (HGVS Nomenclature 2024); each matching [NCBI OA record](https://www.ncbi.nlm.nih.gov/pmc/utils/oa/oa.fcgi?id=PMC11660784) is the license authority |
| Terms/version | each NCBI OA record reports CC BY and `retracted=no`; retrieval snapshot 2026-07-22 |
| Size | 671,725 B + 814,441 B + 3,290,428 B + 2,188,278 B = 6,964,872 B |
| Checksums | endpoint publishes no digest; enforce PMCID/content type/byte count, compute SHA-256 on approved transfer, and freeze before expectations are authored |
| Destination | tracked, attributed `app/backend/tests/fixtures/paper_open_corpus/` with one manifest; no patient upload or private material |
| Builder | new explicit offline corpus fetch/verify command; tests consume only checked-in bytes and never call the network |
| Runtime mount | none; validation-only test corpus |
| Cadence | immutable; replacement needs a new card |
| Rollback | remove the corpus commit and retain the existing Eamos-owned synthetic matrix |
| Probe | PDFium extraction/page/section/span stability; expected mention and bibliography exclusions; deterministic rerun; malformed/blank/deadline controls remain synthetic |

## Already approved and reused; no new material action

- dbSNP `GCF_000001405.40.gz` and `.tbi` already exist in the approved SG
  manifest at 29,552,227,779 B and 3,140,346 B with SHA-256
  `43bb897b69177555a8e9edeb7d8c8ea3e581dddaefadfafe29f36bed0d870574`
  and `d6c38c0b715e5fe16c715f2aaed04b3964ed7f38f00c5921e10afd3649b2b104`.
  Wave 3 may verify and reuse those exact mounted files; it may not download,
  upload, replace, or provider-flip them under this packet.
- Existing tracked GenCC and Mondo files remain the rollback source until the
  new snapshot cards pass. They must not be relabelled as the new releases.

## Deferred / NO-GO in this packet

| Item | Decision and unblock condition |
| --- | --- |
| GRCh38 SpCas9 off-target index | **NO-GO:** estimated ~390M targets/~62 GiB artifact and >=130 GiB build headroom. Needs a separately priced build/runtime target card. |
| UCSC isPcr + `hg38.2bit` | **NO-GO:** commercial-license exception; needs written entitlement and a named binary/source manifest. |
| rs3 0.0.18 | **NO-GO:** its published pins include `scikit-learn<=1.0.2`, incompatible with the Python 3.12 app runtime. Needs an isolated-runtime contract, image-size measurement, and validation card; do not force-install it. |
| R `crisprScore` | **NO-GO:** separate R/Bioconductor runtime footprint and authority choice not frozen. |
| TIDE/TIDER/Tracy | **NO-GO:** Tracy is not TIDE equivalence and there is no approved truth set for efficiency/fit/spectrum claims. Keep HTTP 503/descriptive-only truth. |
| ESM-1b | **NO-GO:** known precomputed scores are non-commercial; MIT-model regeneration needs a compute/reference/MANE output card. |
| CI-SpliceAI and CAPICE | **NO-GO:** exact reviewed releases, full score-cache identities, sizes, and build compute are not frozen. Model presence alone is not execution. |
| REVEL and PrimateAI-3D | **NO-GO:** restricted/unlicensed registry posture and no approved acquisition source. |
| OCR | **NO-GO:** optional; no exact local engine/language-model/license/image-delta card. Paper must report `ocr_required`. |
| Offline VEP cache | **NO-GO:** optional and large; direct Report lookup remains the Batch path. |
| PanelApp/CRISPOR web | **NO-GO:** rights, retention, consent, and network behavior are not approved. |

All deferred capabilities remain visible as typed unavailable/not-assessed.
They must not be hidden, proxied through a different named method, or replaced
with fixtures.
