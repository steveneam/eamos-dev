# CRISPR ssODN (HDR donor) — lab-protocol spec

Status: **DRAFT for review** · Authored 2026-06-07 (Claude, FE) · Owner of build: backend (Codex) for sequence generation; FE (Claude) for rendering.

Steven flagged that the single-strand oligonucleotide (ssODN) is the **second required
component** of a CRISPR HDR knock-in (the guide is the first), and that our current
HDR-repair output does not match how the lab actually designs and orders them. This spec
captures the lab's documented protocol and the additive backend + FE work to match it.

## Source of truth

Internal CMRI workbook: *"Single strand Oligonucleotides for gRNA RPE65 - 22-05-2023.xlsx"*
(Eye Genetics → StevenE → Projects → RPE65 → Materials and Methods → 3. CRISPR).

**Guardrail:** this workbook and its example 120-nt sequences are **internal CMRI data —
do NOT commit the file or any of its reference sequences into the repo.** Any test fixture
must be derived from **public GRCh38 RPE65 reference** and de-identified. Variant notations
(c./p. HGVS) are public and may be used as test-case identifiers.

## What we have today

`/api/v1/crispr` already returns an `HdrSsodn` (rendered by `crispr/DesignTab.tsx` →
`SsodnBlock`, the "HDR repair (ssODN)" block):

```ts
interface HdrSsodn {
  reference_arm: string
  variant_arm: string
  repair_template: string      // effectively the donor today
  edits_encoded: string[]
  arm_lengths: Record<string, number>   // { left, right }
  estimated_hdr_efficiency: number
}
```

Current backend behaviour: `_build_hdr_ssodn()` uses the resolved `SequenceContext`
target offset/reference/alternate base, takes up to 30 nt left and 30 nt right around a
single-base edit, swaps the edited base, and returns that as `repair_template`. It is a
source-backed SNV repair-preview, not a lab-order ssODN generator. It does **not** yet produce
the 120-nt default donor, use intron-aware genomic sequence, expose user-adjustable donor
length, or implement a real silent PAM-blocking edit path.

## The lab protocol (rules extracted from the workbook)

1. **Length defaults to 120 nt total, but must be user-adjustable.** The workbook examples
   use 120 nt; Eamos should expose that as the default, not a hard-coded limit. Order from
   Sigma, SDS-PAGE purity, lyophilised, lowest yield.
2. **Edited/variant base centred at ~nt 59/60 for the 120-nt default** (middle of the donor).
   For user-selected lengths, centre the edited base in the requested window unless the user
   supplies an explicit offset.
3. **Genomic sequence, intron-inclusive.** The donor covers the genomic region around the
   variant; if the donor window crosses an exon/intron boundary, the **intronic bases are
   included** (the lab writes intronic bases in **lowercase** to mark them).
4. **Arms framed around the target codon.** Lab notation: ~**59 nt downstream** of the
   codon (`_NNN`) and ~**56 nt upstream** (`NNN_`), where `NNN` is the 3-nt target codon.
   (See open question on the exact split / off-by-one.)
5. **Corrective edit = revert the variant codon to wild-type** via the amino-acid/codon
   table. As documented, the donors are **guide-independent** (centred on the codon, not on
   a guide's cut site) and **do not** add a silent PAM-blocking edit.
6. **Output = one orderable donor string** of the requested length, named:
   `ss oligo for {c.HGVS}; {p.HGVS}; {WTcodon} > {VARcodon}`.
7. Benchling counting quirk (informational): Benchling "create annotation" counts *between*
   nucleotides, so a 5021→5140 span reads as 119 but is actually 120. Account for this when
   deriving coordinates from Benchling, not in our own math.

### Tiering in the workbook
Examples are grouped **Pathogenic / Benign / VOUS** — purely how the lab organises its
order list; not a constraint on the generator.

## Gaps (lab protocol vs our current ssODN)

| # | Lab protocol | Current | Severity |
|---|---|---|---|
| 1 | **Genomic, intron-inclusive** (introns lowercase) | cDNA template | **High** — core difference |
| 2 | 120 nt default, user-adjustable length, variant centred by default | symmetric ±60 arms | Med |
| 3 | Corrective-only (codon revert) | corrective **+** silent PAM-block | Med (policy) |
| 4 | Codon-centred, **guide-independent** | guide-centric | Med |
| 5 | Orderable single string + name | 3-arm diff, no copy-to-order | Low (FE) |

## Proposed design

### Backend (Codex) — additive, mock-first

1. **Genomic window source.** Obtain the genomic (intron-aware) reference around the
   variant codon. Reuse the align-engine **BE-4 `/sequence/resolve`** or the gene-viewer
   **`full_locus`** genomic sequence rather than the cDNA template.
2. **ssODN assembly algorithm (deterministic):**
   - Locate the variant codon on the genomic reference.
   - Take a genomic window of `oligo_length` nt, defaulting to 120.
   - Centre the edited base by default. For even lengths, use the lower middle offset
     (`floor((oligo_length - 1) / 2)`, so 120 nt places the edited base at 0-based offset 59).
     Allow an advanced `variant_offset` override when the lab needs asymmetric arms.
   - Apply the **corrective edit** (variant codon → WT codon via codon table).
   - Tag which window positions are **intronic** (for lowercase rendering).
   - Optionally apply a silent **PAM-blocking** edit **only when a guide is supplied and
     the option is enabled** (off by default to match the lab protocol).
   - Compose the final donor sequence + a name string.
3. **Strand:** honour the requested ssODN strand (sense / antisense). RPE65 is minus-strand
   — see open question.

### Contract (additive — keep all existing `HdrSsodn` fields)

```ts
interface CrisprSsodnOptions {
  oligo_length?: number          // default 120; backend validates range, e.g. 60-200 nt
  variant_offset?: number        // optional 0-based edited-base position; default midpoint
  protocol?: 'lab_genomic' | 'guide_pam_block'
}

interface HdrSsodn {
  // ...existing fields unchanged...
  oligo_sequence?: string         // the assembled orderable donor (5'->3')
  oligo_length?: number           // requested/generated length, default 120
  oligo_name?: string             // "ss oligo for c.247T>C; p.Phe83Leu; TTC > CTC"
  variant_offset?: number         // 0-based index of the edited base within oligo_sequence (~59)
  intron_mask?: boolean[]         // per-base: true where genomic position is intronic (lowercase)
  strand?: '+' | '-'              // sense/antisense the oligo is written on
  protocol?: 'lab_genomic' | 'guide_pam_block'   // which generation mode produced it
  arm_lengths: Record<string, number>            // now may be asymmetric (e.g. {left:56,right:59})
}
```

Recommended backend validation for `oligo_length`: default 120, minimum 60, maximum 200
unless Steven chooses tighter lab bounds. Reject values that cannot keep the edited base and
requested edits inside the resolved genomic window.

Both `backend.ts` mirrors (`app/web/lib/backend.ts`, `app/frontend/src/lib/backend.ts`)
stay **byte-identical**. Existing fields and the current behaviour remain valid (the new
fields are optional; the FE degrades gracefully when absent).

### Frontend (Claude) — once the contract lands

- Provide a numeric length control defaulting to **120 nt**. Keep 120 as the visible lab
  default, but allow the user to adjust within backend bounds.
- Render the orderable donor with **intronic bases lowercased** (via `intron_mask`),
  the edited base highlighted at `variant_offset`, and the `oligo_name`.
- **"Copy oligo"** button (copies `oligo_sequence`) + the order note (Sigma · SDS-PAGE ·
  lyophilised) as static helper text.
- Keep the existing 3-arm diff as the explanatory view; add the orderable string above it.
- If `protocol === 'lab_genomic'`, present it as the codon-centred donor (no PAM-block row).

## Test cases (public RPE65, GRCh38)

Validate the generator against public reference for these workbook variants (the full
reference donor sequences stay in the internal workbook only):

- `c.247T>C` (p.Phe83Leu), codon TTC→CTC
- `c.419G>A` (p.Gly140Glu), codon GGG→GAG
- `c.65T>C` (p.Leu22Pro), codon CTG→CCG
- `c.881A>C` (p.Lys294Thr) — example whose 120-mer **spans an intron** (intronic lowercase),
  good for exercising gap #1.
- Include one non-default length case, for example 100 nt or 140 nt, proving the edited base
  remains centred by default and `oligo_length`/`variant_offset` report correctly.

## Open questions (for Steven)

1. **Strand convention** — should the ssODN be written sense or antisense by default?
   (RPE65 is minus-strand; the workbook examples imply a fixed convention — confirm.)
2. **Arm split / length bounds** — use 120 nt as the default and allow user adjustment, but
   confirm backend bounds (proposed 60-200 nt) and whether Steven wants an explicit
   `variant_offset` control exposed in the UI or backend-only for advanced use. Lab notes say
   ~59 downstream + ~56 upstream of the codon (=118 + codon), while rule #1 centres the default
   around 59/60; confirm whether this is Benchling off-by-one (rule #7) or intentional asymmetry.
3. **PAM-block** — keep it strictly off for the lab protocol, or offer it as an opt-in
   enhancement when a guide is selected?

## Out of scope / guardrails

- No commit of the CMRI workbook or its sequences; fixtures from public GRCh38 only.
- Additive contract only; the current guide-centric ssODN keeps working.
- Permissive-license dependencies only; mock-first; GRCh38 default.
