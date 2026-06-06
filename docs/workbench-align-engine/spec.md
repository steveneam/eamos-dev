# Spec — Align tool backend engine (Sanger trace analysis + alignment + reference fetch)

> Status: **DRAFT for Steven review → Codex (backend).** FE Align v2 (reference + N reads, client-side ABIF parse, chromatograms, auto-orient, Q-trim, quality-aware mismatch, het detect, motif search) is built and verified with real RPE65 VUS1 `.ab1` files. This spec moves the **heavy/robust analysis to the Python/FastAPI backend** for accuracy, and adds reference-by-accession fetch. Backed by three research sweeps (Sanger-trace algorithms · alignment engines · viz/UX) — see "Evidence" below. Backend is **Codex's lane**; FE swaps its client logic for these endpoints behind the same UI (no UI rebuild).

## Context / why

The client-side v1 uses simple heuristics: a sliding-window Q-trim, a naive secondary/primary peak ratio for het, and a positional/Smith-Waterman pairwise aligner. These are fine for display and quick feedback but **not robust enough for clinical variant validation** (e.g. confirming an iPSC-RPE RPE65 edit). Real `.ab1` reads exposed the gaps: low % identity from the collapsed-intron reference, over/under-aggressive trimming (one read trimmed to a 10 bp core), and ratio-only het flagging that needs noise-floor + flanking context. The backend (Biopython already present) should own parsing-robustness, trimming, het/indel detection, and the alignment engine; the FE keeps rendering.

Steven's decisions this cycle: **client parse now + backend for robustness (CAR)**; **contiguous genomic reference = a later phase**; **reference import via paste/FASTA now + accession-search (Entrez/Ensembl/RefSeq) = backend**.

## Goals

1. **Robust trace analysis endpoint** — parse `.ab1`, return trace + Phred + Mott-trim range + het calls + per-base confidence. Always-on (parsing a blob needs no external APIs, so NOT behind the global `USE_REAL_APIS` flag).
2. **Robust alignment** — semi-global affine-gap aligner (read↔reference) returning a CIGAR → reference-coordinate mismatch/indel table; multi-read consensus.
3. **Reference-by-accession fetch** — resolve Entrez gene id / Ensembl id / RefSeq accession → reference sequence + provenance, for the Align reference picker.
4. **(Phase 2) CRISPR-edit deconvolution** — control vs edited trace → indel spectrum (for edit-validation).

Keep all existing contracts additive + mock-first. No regression to `/api/v1/align`, primer, crispr.

## Engine choices (research-backed — all MIT/BSD/permissive)

| Concern | Adopt | Why / source |
| --- | --- | --- |
| AB1 parse | **Biopython `Bio.SeqIO` ABI** (already in stack) | `DATA9-12` channels, `PCON2` Phred, `PLOC2` peaks, `FWO_1` order. Existing `trace_parser.py` already does this. |
| Quality trim | **Modified Mott** (port Biopython `_abi_trim`, ~15 lines), cutoff Q20 (vs Biopython's lenient Q13) + optional 15 bp hard end-clips | Phred standard; deterministic, O(n). Replaces FE sliding-window. |
| Het / mixed-base | **PHFinder 3-index**: Main Ratio + Secondary Ratio (±3 bp flanking) + Average Quality, all must pass | Validated (27/30 heteroplasmies); flanking index kills single-spike false positives that plague naive ratio (our FE over-flagged 261→tuned). `scipy.signal.find_peaks(prominence=…)`, noise floor = 5th pct of baseline. |
| Pairwise align | **WFA2 via `pywfa`**, `span="ends-free"` (semi-global), affine gaps | `pip install pywfa`, MIT, maintained 2026. Ends-free = read-vs-longer-reference + soft-clips noisy ends; affine = proper indels. Fallback: `parasail` `sg_qb` or Biopython `PairwiseAligner` (Gotoh). |
| Multi-read consensus | **abPOA via `pyabpoa`** → consensus, then WFA-align consensus to reference | `pip install pyabpoa`, MIT, 2026. This abPOA→WFA pipeline = Benchling's ClustalO→SW template/consensus, faster + cleaner API. |
| CRISPR decompose (Phase 2) | **Tracy `decompose`** (BSD, subprocess) — or port TIDE/DECODR **NNLS** via `scipy.optimize.nnls` | Tracy works at signal level (robust to het indels), no gRNA needed, emits BCF. **Avoid ICE (non-commercial), DECODR/SeqScreener (closed).** |
| Reference fetch | Entrez E-utilities / Ensembl REST / RefSeq via existing sequence-context infra | For accession→sequence. Cache; respect rate limits. |

**Licensing guardrail:** ship only MIT/BSD/permissive (Biopython, pywfa, pyabpoa, Tracy=BSD, parasail, edlib). Do **not** vendor ICE, DECODR, MUSCLE5, or GPL libs (sangerseqR, Teal, ProSeqViewer) into the product.

## Proposed contracts (additive; Codex owns final shape + the two `backend.ts` mirrors)

1. **`POST /api/v1/align/trace`** (NEW, always-on) — `{ ab1_blob_base64 }` →
   `{ base_calls[], q_scores[], peak_locations[], trace_channels[{base,values}], trim:{start,end,method}, het:[{index, main_ratio, flank_ratio, avg_q}], warnings[] }`.
   The FE swaps `abif-parser.ts` + `analyzeRead`'s trim/het for this behind the same UI (falls back to the client parser when offline → mock-first).
2. **`POST /api/v1/align`** (EXTEND, keep current single-read shape working) — accept `{ reference?, reads:[{label, user_sequence?|ab1_blob_base64?, orientation?:"auto"|"forward"|"reverse"}] }`; return per-read `{ cigar, ref_start, ref_end, identity, mismatches:[{ref_pos, read_pos, ref_base, read_base, confidence}], indels[], oriented }` + optional `consensus` when >1 read. WFA ends-free + affine. `orientation:"auto"` = align both, pick better (server-side auto-orient).
3. **`POST /api/v1/sequence/resolve`** (NEW) — `{ accession }` (Entrez gene id / Ensembl ENSG/ENST / RefSeq NM_/NG_) → `{ sequence, label, provenance:{source, id, region}, warnings[] }`. Powers the Align reference accession-search. Mock-first for the RPE65 default.
4. **(Phase 2) `POST /api/v1/align/decompose`** — `{ control_ab1, edited_ab1, cut_site? }` → `{ indels:[{size, seq, fraction}], r2 }` (Tracy or NNLS).

## Build phasing (Codex)

- **BE-1:** `/align/trace` (Biopython parse + Mott trim + PHFinder het + find_peaks). Unit-test against a checked-in RPE65 VUS1 `.ab1` fixture. → FE swaps parse/trim/het behind a feature flag, keeps client fallback.
- **BE-2:** `/align` WFA semi-global (pywfa) single-read + auto-orient + reference-coord mismatch/indel table. → FE swaps its client aligner; keeps `compareSequences` offline fallback.
- **BE-3:** multi-read consensus (pyabpoa → WFA). → FE adds a consensus row.
- **BE-4:** `/sequence/resolve` accession fetch. → FE reference picker gains "search accession".
- **BE-5 (Phase 2):** `/align/decompose` (Tracy) for CRISPR edit validation.
- **Separate, later (also Steven-flagged):** contiguous **genomic reference window** (no collapsed introns) so gDNA Sanger reads align cleanly out-of-the-box — viewer/backend work, its own spec.

## FE integration points (Claude's lane — mostly already built)

- Behind the same v2 UI: `read-model.ts` `analyzeRead`/`abif-parser.ts` get a backend path (call `/align/trace` + `/align`), with the current client logic as the offline/mock fallback (mock-first invariant).
- Reference picker gains an "accession" source calling `/sequence/resolve` (joins paste/FASTA already shipped).
- **FE viz steals** (separate FE follow-ups, from the viz/UX research, NOT Codex): IGV Phred→opacity mismatch coloring; Benchling trim-fade + interactive trim handles; Nightingale coordinated multi-track scroll; canvas virtualization (`@tanstack/react-virtual` + per-row canvas) for many reads; consensus row; export (PNG/SVG/FASTA). Candidate reusable libs: `bio-parsers` (AB1), `seqviz` (template row), `FeatureViewerTypeScript` (annotation track). These are quality/scale upgrades to the current SVG renderer.

## Invariants / guardrails

- Additive only; `/api/v1/align` current `{gene,cdna,user_sequence,ab1_blob_base64}` keeps working. Mock-first everywhere (offline → client fallback / fixtures).
- `/align/trace` must run **without** `USE_REAL_APIS` (pure blob parse, no external call).
- Permissive licenses only (see guardrail above).
- Both `backend.ts` mirrors byte-identical; tsc/pytest/ruff/black green.

## Out of scope

- Full client-side WASM aligner (future; block-aligner is the target if needed).
- Re-basecalling (Tracy basecall) unless traces prove unreliable; PeakTrace (commercial).
- Protein/MSA phylogenetics (MAFFT/MUSCLE) — not the amplicon-validation use case.
- The contiguous genomic-reference window (its own later spec).

## Evidence (research sweeps, 2026-06-06)

- **Sanger-trace algorithms:** Biopython AbiIO; Mott trim; PHFinder 3-index het (PMC10516101); Tracy (BSD, PMC7071639) decompose; TIDE NNLS (PMC4267669); `scipy.signal.find_peaks` prominence + noise floor. Avoid ICE/DECODR (license).
- **Alignment engines:** WFA2/`pywfa` (MIT, ends-free semi-global, affine) top pick; abPOA/`pyabpoa` (MIT) consensus top pick; parasail/edlib/Biopython fallbacks; minimap2/ksw2 overkill for amplicons.
- **Viz/UX:** IGV Phred-opacity; Benchling template-pinned + trim-fade; SnapGene IUPAC find; Nightingale coordinated scroll; canvas virtualization; reusable `bio-parsers`/`seqviz`/`FeatureViewerTypeScript`.
  (Full reports retained in session notes / `~/.claude/plans/next-session-eamos.md`.)
