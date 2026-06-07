# Spec — CRISPR off-target screening (enumerate → curate → primer panel → export)

> Status: **DRAFT for Steven review → Codex (backend off-target enumeration) + Claude (FE screening surface).** Automates a currently-manual wet-lab workflow (Steven 2026-06-07). The off-target **site enumeration** is net-new backend; everything downstream **reuses the existing Primer infrastructure**. Mock-first throughout; all contracts additive (no change to the guide-design `CrisprGuide.off_target_score` scalar or the Design two-table).

## Context / why

CRISPR off-target validation today is manual: run an off-target predictor, export **all** candidate sites, pick the **top few** by score + gene relevance, draw a screening window around each, design PCR primers, then PCR + Sanger each locus to check for unintended edits. Steven: *"people who do off-target screening need to do this process manually — I'm helping them expedite it,"* and *"since we have the primer infrastructure in place, this would integrate well."*

Reference artifact (a real CMRI run, **internal lab data — keep OUT of the repo**): `…\Eye Genetics\Taya\CRISPR & PE info\11.1 HDR Cor ABCA4\…\11.1 c2 and c3 ABCA4 gRNA Off-Target Sequencing.xlsx` — the ABCA4 HDR guide "11.1 Cor". Four sheets map exactly onto the pipeline below.

## The workflow (from the reference workbook)

1. **"All" (51 rows)** — every predicted off-target for the guide:
   `Sequence(20-mer) · PAM · Score(CFD-like 0–1; on-target row = 100 / 0 mm) · Gene(SYMBOL:ENSG or intergenic) · Chromosome · Strand(±1) · Position · Mismatches · On-target · genome_build(GRCh38.p14)`.
2. **"Sites for screening" (10 rows)** — top-N curated off-targets (ranked by score, coding-gene relevance) + a **±400 bp screening window**: `start · end · region(chrN:s-e) · point(chrN:pos)`.
3. **"Primers" (10 × F/R)** — **screening primers** per site: `name(11.1_Cor_OTS_1_F/R) · sequence · product_length · "Other products"(in-silico PCR specificity: NONE or alternate amplicon sizes)`.

**Pipeline to automate:** enumerate all off-targets → rank & select top-N → derive ±flank windows → design screening primers per window → **export the panel** (mirrors the workbook).

## Goals

1. **Off-target enumeration endpoint** — genome-wide PAM + mismatch search for a guide, scored + gene-annotated (the only net-new capability).
2. **Top-N selection + window derivation** — rank by score/relevance, pick N, draw ±flank windows (deterministic; FE-owned, user-overridable).
3. **Screening-primer design per region** — reuse the primer engine on each window's reference sequence; emit specificity ("Other products").
4. **Export** the screening panel (sites + primers) — TSV/CSV/XLSX mirroring the workbook.

## Engine choices (off-target search — permissive licenses only)

| Concern | Adopt | Why / source |
| --- | --- | --- |
| Genome-wide off-target search | **Cas-OFFinder** (BSD-2) | PAM + up-to-k mismatch genome search; no gRNA training needed; scriptable; widely used. |
| Off-target score / ranking | **CFD** (Doench 2016) per-site + **MIT specificity** aggregate | The workbook "Score" is a CFD-like 0–1 per site. CFD ranks individual sites; MIT score = overall guide specificity. |
| Gene annotation at locus | **Ensembl/RefSeq GTF** interval lookup (existing source infra) | Map each hit → gene SYMBOL:ENSG + biotype (protein_coding flag drives "relevance"); null = intergenic. |
| Region → reference sequence | **align-engine BE-4 `/sequence/resolve`**, extended for `chrN:start-end` regions (or a sibling `/sequence/region`) | The screening primers must be designed against the locus's reference sequence. Synergy with the Align backend spec. |
| Screening-primer design | **the existing internal primer engine**, fed the region sequence | Reuse — emit the existing `PrimerPair` shape + an `other_products` specificity field. |

**Licensing guardrail:** BSD/MIT/permissive only (Cas-OFFinder = BSD-2). Do **not** vendor non-commercial / closed predictors.

## Proposed contracts (additive; Codex owns final shape + both `backend.ts` mirrors)

1. **`POST /api/v1/crispr/offtargets`** (NEW, mock-first) —
   `{ guide, pam, enzyme, genome_build?, max_mismatches?, on_target_locus? }` →
   `{ genome_build, sites: OffTargetSite[] }`
   where `OffTargetSite = { sequence, pam, score, mismatches, gene|null, gene_id|null, biotype|null, chromosome, strand:'+'|'-', position, on_target:boolean }`.

2. **`POST /api/v1/crispr/screening-primers`** (NEW) **or** extend `POST /api/v1/primer` with a region/sequence input —
   current `PrimerRequest` is **gene/cdna-scoped** (`{gene, cdna, mode, tm_*, product_size_*, avoid_snps}`); screening is **region-scoped**, so add (additively) `{ template_sequence | region:{chromosome,start,end,genome_build}, naming_prefix? }` → returns `ScreeningPrimer` pairs:
   `{ site#, point, name_forward, name_reverse, forward, reverse, tm_forward, tm_reverse, gc_*, product_size, other_products, recommended? }` — reuses the `PrimerPair` shape + `other_products` (alternate amplicon sizes from an in-silico PCR specificity pass).

3. **(reuse/extend) region → sequence** — align-engine **BE-4 `/sequence/resolve`** extended to accept a `chrN:start-end` region (or a new `/sequence/region`), so the FE/BE can fetch the reference window each primer pair is designed against.

## Selection / window logic (deterministic — FE-owned, user-overridable)

- **Rank:** `score` desc; mark **relevance** = `gene_id != null && biotype == 'protein_coding'`.
- **Default pick:** top-N (N ≈ 10) preferring coding hits + high score; always include any ≤1-mismatch sites. User edits the selection (checkbox column) in the FE.
- **Window:** `start = position − FLANK`, `end = position + FLANK` (default FLANK = 400, adjustable) → `region = chrN:start-end`, `point = chrN:position`.

## Frontend (Claude) responsibilities

- New **"Off-target screening"** surface in the CRISPR tool (3rd sub-tab beside Design/Outcomes, or a Design section):
  - Run enumeration for the active guide → **OffTargetSite table** (reuse `.tool-table`; sortable by score/mismatch; gene column; on-target row pinned; base-coloured 20-mer via `--base-*`).
  - **Top-N selection** (checkbox column + "auto-pick top N" + score/mismatch/coding filters) → derive windows (the "Sites for screening" view).
  - Per selected site → **screening primer pairs** (reuse the Primer property-table rendering + `PrimerPair` shape) with product size + `other_products` specificity.
  - **Export panel** (TSV/CSV/XLSX) mirroring the three workbook sheets (All / Sites for screening / Primers).
  - **Mock-first:** an `OFFTARGET_SAMPLE` fixture (de-identified, shaped from the workbook) so the FE renders offline ahead of the backend.

## Build phasing

- **BE-1 (Codex):** `/api/v1/crispr/offtargets` — Cas-OFFinder genome search + CFD score + GTF gene annotation + on-target flag. Unit-test vs a checked-in fixture. Mock-first.
- **BE-2 (Codex):** region → sequence (extend BE-4) + screening-primer design over the region (reuse internal primer engine; emit `other_products`).
- **FE-1 (Claude):** off-target table + top-N selection + window derivation (mock `OFFTARGET_SAMPLE`).
- **FE-2 (Claude):** screening-primer panel (reuse primer property table) + export.
- **FE-3 (Claude):** wire FE to the BE endpoints behind the same UI; keep mock fallback.

## Decisions / Assumptions

- Genome build **GRCh38** default (workbook used GRCh38.p14).
- Default flank **±400 bp**, default **N = 10** — both user-adjustable.
- Off-target **SITE enumeration is net-new backend**; the guide-design scalar `CrisprGuide.off_target_score` is unchanged/kept.
- The reference workbook is **internal CMRI data** → any fixture must be **de-identified**; do **not** commit the `.xlsx`.
- Licensing: Cas-OFFinder (BSD-2) / CFD only; no non-commercial predictors.

## Non-goals

- No new off-target *prediction model* research (use established Cas-OFFinder + CFD).
- No automated primer **ordering** / vendor integration.
- No change to the Design two-table or the scalar `off_target_score`.
- Not flipping `use_real_apis`; mock-first throughout.

## Evidence

- Reference workbook (internal): ABCA4 "11.1 Cor" gRNA off-target sequencing — 4 sheets (All 51 / Sites for screening 10 / Primers 10×F/R / scratch). Demonstrates the exact manual pipeline this feature automates.
