# AI Gateway — paper→variants hardening (spec)

> **Status:** draft for review · authored 2026-06-14 (Claude). Builds on the
> already-shipped paper→variants slice (gateway structured extraction +
> VariantValidator gate) catalogued under `eamos-ai-gateway`. Triggered by a
> real-world test: running the slice on a published RPE65 functional-study PDF
> (`Mutation of key residues of RPE65 abolishes its enzymatic role…`) surfaced
> three gaps at once. This spec plans the fixes, **reusing existing Eamos
> resolution machinery** rather than rebuilding it.

## 0. What the real paper exposed

The RPE65 paper (6 pp) yielded **0** candidates from the current slice because:

1. **Input is a PDF**, not text — the service takes a `paper_text` string.
2. **The engine is cDNA-only** — the mock regex (and a naive prompt) miss the
   paper's mutations, which are written as **protein residues** (`H241A`,
   `C231S`, `His241→Ala`, …), not `c.` HGVS. Even with perfect text, nothing
   matched.
3. **Schema/validation is cDNA-centric** — `transcript_hgvs` + a VariantValidator
   gate that needs a DNA-level allele. Protein-only mentions can't be
   coordinate-validated directly.

## 1. The reframing (drives the design)

The paper's mutations are **engineered experimental constructs** (site-directed
mutagenesis of catalytic residues), not patient variants. Two consequences:

- Many aren't **SNV-reachable** (His→Ala needs ≥2 nt changes), so they have **no
  single genomic coordinate** — that's a *category to recognize*, not a bug.
- Their value is **functional evidence** ("residue X mutated → abolishes
  isomerohydrolase"), distinct from a clinical allele.

So the goal is not "coordinate-validate everything" — it is **extract the right
kind of variant and resolve each kind appropriately**: clinical alleles →
coordinates; experimental constructs → labelled functional evidence.

## 2. Decisions (locked)

- **D1 — PDF engine: pluggable, `pypdf` default.** One `pdf_text` ingestion
  utility with a config-selectable engine, reusing the existing
  `ReportPdfTool` seam. Default `pypdf` (BSD, already a dep, commercial-safe);
  upgrade to `pdfplumber` (MIT) or PyMuPDF/`fitz` (fastest, **AGPL — needs an
  Artifex commercial licence for the SaaS**) behind a flag, no caller changes.
- **D2 — Reuse the existing resolution stack for Gap 3** (the correction):
  do **not** build a new protein→cDNA codon enumerator. Eamos already resolves
  variants through:
  - **Eamos Local Coordinate Resolver** (`eamos_coordinate_resolver.py` /
    `search_input_resolver.py::EamosSearchInputResolver.resolve(gene, cdna,
    transcript=, protein_change=)`) — gene/transcript/cDNA → GRCh38 VCF identity.
    Its own caveat: *protein-only descriptions do not uniquely define a genomic
    coordinate and must be paired with a source-backed DNA-level candidate.*
  - **Source-Backed Candidate Resolution** (`search_input_interpreter.py`,
    `search_candidate_resolver.py`) — maps protein/ambiguous intent to known
    source-backed candidates (e.g. `CFTR:p.Leu441del` → curated allele), with
    modes `deterministic | auto_resolved | needs_selection | suggestions`.

  These are the catalogued proprietary assets `eamos-local-coordinate-resolver`,
  `candidate-resolution`, and `eamos-search-input`.

## 3. Plan by gap

### Gap 1 — PDF ingestion (offline-buildable now)
- `services/pdf_text.py` (or extend `ReportPdfTool`): `extract(file_path|bytes,
  engine=settings.pdf_text_engine) -> {text, page_count, warnings}`. Default
  `pypdf`; `pdfplumber`/`fitz` behind `pdf_text_engine`.
- Wire ingress: CLI `--pdf <path>`; later an upload endpoint reusing intake's
  upload plumbing (`upload_dir`, `max_upload_mb`, `.pdf` validation).

### Gap 2 — Protein-aware extraction
- **Prompt** (`paper_variants_prompt`): extract protein-residue notation
  (`H241A`, `His241Ala`, prose) and normalize to HGVS `p.` form; flag a `context`
  hint (clinical allele vs experimental construct) when the text supports it.
- **Mock** (`PaperVariantsService._mock_extract`): add a protein-substitution
  regex (reuse the residue scan) so offline dev/tests aren't cDNA-blind.
- **LLM quality** is the real engine — **gated on the gateway enable pass**.

### Gap 3 — Schema + tiered resolution (reuse the stack)
- **Schema** (`schemas/paper_variants.py`): keep `transcript_hgvs` optional; add
  `protein_hgvs` (normalized `p.…`), a `level` discriminator
  (`cdna|protein|genomic`), and `context` (`clinical_allele|experimental_construct`).
- **Gate → resolution tiers** (replaces the direct VariantValidator-only gate):
  - `cdna`/`genomic` → `EamosSearchInputResolver.resolve(gene, cdna=…)` →
    `genomic_hg38`/`genomic_hgvs` (local-first; VariantValidator stays the
    offline oracle, not the hot path).
  - `protein` + clinical → **source-backed candidate resolution**
    (`search_candidate_resolver`): `auto_resolved` → coordinates;
    `needs_selection`/`suggestions` → surfaced as ranked candidates.
  - `protein` + experimental construct (no source-backed candidate) →
    **functional-evidence record**, explicitly *not* coordinate-validated.
- **Status enum:** `resolved | candidates | protein_only_unresolved |
  experimental_construct | missing`.

## 4. Phasing

| Phase | Scope | Needs gateway? |
|---|---|---|
| 1 | `pdf_text` util (pypdf, pluggable) + PDF CLI ingress | No — now |
| 2 | Protein-aware mock + prompt + schema (`level`/`context`/`protein_hgvs`) | No — now |
| 3 | Tiered resolution via `EamosSearchInputResolver` + source-backed candidates | No — now |
| 4 | LLM extraction quality on real PDFs; clinical-vs-construct from the model | Yes — enable pass |

Phases 1–3 are deterministic and offline-testable (reusing existing resolvers);
only extraction *quality* waits on the gateway flip.

## 5. Reuse map (do not rebuild)

| Need | Existing asset | Catalogue id |
|---|---|---|
| PDF→text | `tools/report_pdf.py::ReportPdfTool` | — |
| cDNA→GRCh38 | `services/eamos_coordinate_resolver.py`, `search_input_resolver.py` | `eamos-local-coordinate-resolver` |
| protein/ambiguous→candidate | `search_input_interpreter.py`, `search_candidate_resolver.py` | `candidate-resolution` |
| structured extract+repair | `services/ai_gateway/structured.py` | `eamos-ai-gateway` |
| coordinate oracle (offline) | `tools/variant_validator.py` | — |

## 6. Verification

- `pytest` green for new pdf-ingest / protein-extraction / tiered-resolution
  tests (mock-first, offline; injected resolver fakes + one real-fixture path).
- ruff clean; the slice stays inert until `LLM_PROVIDER=gateway`.
- Re-run the RPE65 paper offline: protein constructs surface as
  `experimental_construct` functional-evidence records (not bogus coordinates);
  any clinical cDNA/known allele resolves via the existing stack.

## 7. Open items / coordination

- Gap 3 wiring touches the search-input/candidate-resolution lane — **Codex's
  catalogued lane**. The resolver interfaces are stable, but confirm the exact
  `search_candidate_resolver` entry point + coordinate the contract before code.
- Phase 4 needs the gateway enable pass (off-transcript key re-mint + credits).
- Catalogue: fold these files into the `eamos-ai-gateway` entry once Codex's
  active `index.json` round settles.

## 8. Ask-Eamos verification pass over the source paper (planned — Steven 2026-06-20)

The `/paper` Ask-Eamos rail is **not** a generic chat over the extracted list — it
should run a **semantic pass over the dropped-in / attached paper(s)** to *verify
each candidate is genuinely the right variant* before the user trusts it. The
deterministic/regex + tiered-resolution pipeline above answers "what strings look
like variants and where do they resolve"; this pass answers "is this mention a
real reported allele **in this paper**, or a false positive from somewhere it
shouldn't count."

Edge cases the pass must catch (fail-closed — when unsure, downgrade, don't assert):

- **Reference / bibliography section** — an `c.`/`p.` token inside a cited paper's
  title or a reference list is **not** a variant this paper reports.
- **Background / "previously reported"** mentions vs the paper's **own** findings —
  flag provenance (this paper's result vs a recounted prior one).
- **Experimental constructs vs clinical alleles** — already a `context` discriminator
  (§3); the pass should corroborate it from surrounding prose, not just the token.
- **Figure/table captions, supplementary, primer/oligo sequences** — coordinate-ish
  strings that aren't reported patient variants.

Design constraints (consistent with the per-surface scoping model, [[project_ai_gateway]]):

- **Scoped context, like every Ask-Eamos surface** — grounded only in *this* paper's
  resolved candidates + their `evidence_quote` + section provenance, never a
  free-floating chat (enforced now by `ChatRequest`'s require-a-scoped-context
  validator). Needs a `PaperContext` shape (candidates + sources + per-candidate
  section/locus) added to `ChatRequest` + the guard allowlist, mirroring how
  `WorkbenchContext` was added.
- **Reuse, don't rebuild** — the verification leans on the same structured-extraction
  + source-backed resolution stack (§5); the chat pass *adjudicates* provenance, it
  doesn't re-extract from scratch.
- **Provenance, not raw text** — keep the sanitized-output guarantees (short
  `evidence_quote` snippets only, never the full paper body leaving the server).
- Gateway-gated; renders inert (`.eamos-mock`) until `LLM_PROVIDER=gateway`, like the
  rest of the slice.

This is a Paper-surface follow-on; the cross-surface chat foundation (optional
`variant_context` + scoped-context validator + report-less grounding) already
landed with the Workbench slice.
