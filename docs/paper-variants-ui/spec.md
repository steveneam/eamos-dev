# Paper → Variants — Frontend Surface (sketch / spec)

**Status:** sketch for review (2026-06-14) · **queued to build NEXT session, before the ACMG viz wave**
**Owners:** Claude (frontend, `app/web`) · Codex (backend endpoint, `app/backend`)
**Surface:** net-new `/paper` ingest page (placement to confirm — §3)

---

## 0. What this is

Turn a **publication** (pasted text, `.txt`, or PDF) into a reviewed list of **candidate variants** with full provenance and **fail-closed** clinical gating — then push the validated, source-backed ones into the existing report / variant-library / batch flows. The backend already does the extraction + resolution; this spec is the **frontend that surfaces it** plus the **one HTTP endpoint** Codex needs to add (it's CLI-only today).

This is the UI Steven asked me to sketch when I noted paper→variants is currently a backend/CLI capability with no front door.

---

## 1. Backend reality (grounded — what exists today)

- **Service:** `app/backend/app/services/paper_variants.py` — `PaperVariantsService(settings).extract(text, validate=True) → PaperVariantsResult`. Phase 3 (candidate resolution) is wired through Codex's existing stack: cDNA/genomic → `EamosSearchInputResolver`; protein → source-backed `SearchCandidateResolver`. **Do not duplicate `search_input_*` or add a parallel protein→cDNA resolver.**
- **CLI only:** `cli/eamos_paper_variants.py` (`--text` / `--text-file` / `--pdf`). **There is no HTTP route yet** — that's the backend gap this surface needs (§8).
- **Mock-first:** deterministic regex extractor by default; the gateway extraction path activates only when `LLM_PROVIDER=gateway`. So the UI renders on mock extraction today (inert, `.eamos-mock`), consistent with the rest of the report.
- **Sanitized output (guardrails baked in):** `patient_data: not_used`, `raw_paper_text_in_output: blocked`, `secrets_in_output: blocked`. Only the short `evidence_quote` snippet per candidate is returned — never the full paper text.

### The contract the FE consumes (from `schemas/paper_variants.py`)

```
PaperVariantsResult {
  variants: ValidatedPaperVariant[]
  warnings: string[]
  provenance: string[]
}

ValidatedPaperVariant {
  gene, transcript_hgvs, protein_change, protein_hgvs   // raw extracted strings
  level:   "cdna" | "protein" | "genomic" | "unknown"
  context: "clinical_allele" | "experimental_construct" | "unknown"
  evidence_quote                                         // the supporting sentence
  validated: bool                                        // the fail-closed gate result
  validation_status: string                             // e.g. "validated" | "ambiguous" | "missing"
  variant_id, genomic_hgvs, resolved_candidate_id       // populated ONLY when validated
  source_support: string[]
  source_inputs: SearchInputSourceInputs | null
  candidates: SearchInputCandidate[]                    // SAME type SearchInterpretationPanel renders
  resolver_warnings: string[]
  resolver_provenance: string[]
}
```

**Fail-closed semantics (mirror exactly in the UI):** only a **single high-confidence source-backed candidate** validates (`validated=true` + coordinates populated). Ambiguous suggestions and `experimental_construct` context stay **non-coordinate / non-clinical** — they are shown, but get **no clinical actions**.

---

## 2. Scope

**In:** the `/paper` surface — input zone, extract action, candidate-review table, fail-closed gating, provenance display, and actions on validated rows (Open report / Add to library). FE type mirror in `backend.ts`. Mock-first.

**Out:** any extraction/resolution logic (Codex owns it); PDF parsing (backend `pdf_text`); enabling the gateway path; batch-scale paper queues; a "submit to ClinVar" path.

---

## 3. Placement (the decision to confirm)

**Recommended:** a dedicated lightweight route **`/paper`**, reachable from the workspace switcher (currently Report · Workbench · Batch → add **Paper**). It's an *intake* flow, distinct enough from the three existing surfaces to warrant its own door, and it naturally hands off *into* them (a validated candidate → Open report, or Add to library → Batch).

**Alternatives (call it, Steven):**
- **(b) A drawer on Batch** — Batch is already bulk-variant intake; paper extraction could feed the same `variant-library` store + batch table. Less nav surface, but couples two different input modalities.
- **(c) A mode on the search bar** — the search input already resolves one variant via `EamosSearchInputResolver`; paper-ingest is the bulk version. Tightest reuse, but buries a whole flow inside the search affordance.

A new persistent route/switcher entry is a structural change → **confirm placement before I build** (per the standing rule that durable structural/nav changes need explicit OK).

---

## 4. The flow + wireframe sketch

```
┌─ Paper → Variants ───────────────────────────────────────────────┐
│  Extract variant mentions from a publication. Source-backed only.  │
│                                                                    │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │  [ Paste text ]  [ Upload .txt ]  [ Upload PDF ]           │    │
│  │  ……paper text / drop zone……                               │    │
│  │                                            [ Extract → ]    │    │
│  └──────────────────────────────────────────────────────────┘    │
│  PDF: 12 pages · pdfminer · 1 warning            .eamos-mock      │
│                                                                    │
│  Candidates  ·  8 found · 3 validated · 5 held                     │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │ ✓ RPE65  c.260A>G  p.(…)        clinical · cdna            │    │
│  │   NM_000329.3:c.260A>G | chr1:… [validated]                │    │
│  │   "…the c.260A>G allele segregated…"   [src: VV, ClinVar]  │    │
│  │                          [ Open report ]  [ + Library ]    │    │
│  ├──────────────────────────────────────────────────────────┤    │
│  │ ⚠ ABCA4  p.Gly1961Glu           protein · ambiguous       │    │
│  │   2 candidate transcripts — needs source coordinates      │    │
│  │   [ choose a match ▾ ]   (no clinical action)             │    │
│  ├──────────────────────────────────────────────────────────┤    │
│  │ ⌀ "minigene Δexon3"             experimental construct     │    │
│  │   Non-clinical — shown for context, not resolved          │    │
│  └──────────────────────────────────────────────────────────┘    │
│  Warnings / provenance ▾                                          │
└────────────────────────────────────────────────────────────────┘
```

1. **Input zone** — paste / `.txt` / PDF drop. On PDF, show `page_count · engine · warnings` from the backend.
2. **Extract** → `POST /api/v1/paper-variants/extract` → `PaperVariantsResult`.
3. **Candidate table** — one row per `ValidatedPaperVariant`: gene + the best HGVS, a **level** badge (cdna/protein/genomic), a **context** badge (clinical_allele vs experimental_construct), a **status** glyph (✓ validated / ⚠ ambiguous / ⌀ experimental·missing), the **evidence_quote**, and `source_support` chips. Resolver provenance/warnings in an expander.
4. **Fail-closed gating (safety-critical):**
   - `validated && context==clinical_allele` → primary actions enabled: **Open report** (→ `/report` with `variant_id`/`genomic_hgvs`), **+ Library** (variant-library store).
   - `ambiguous` (multiple candidates) → render the candidate chooser (reuse the `SearchInterpretationPanel` card list); selecting a source-backed match promotes it; **no clinical action until one resolves**.
   - `experimental_construct` / `unknown` → shown for context, **explicitly non-clinical**, no actions.
5. **Bulk action** (validated only): "Add all validated to Library / Batch."

---

## 5. Reuse (no duplication — [[feedback_reuse_assets]])

- **`SearchInterpretationPanel.tsx`** already renders `SearchInputCandidate` cards (display_label, transcript/cDNA/protein/genomic subtitle, `source_support` chips, and the **`!(gene && cdna)` → "Needs source coordinates" disabled state**). Extract that card into a shared `<CandidateCard>` and reuse it for the ambiguous-row chooser — same fail-closed pattern, already built.
- **Variant-library store** (shipped, `project_workspace_rail`) — "+ Library" writes to it; reuse, don't rebuild.
- **Report open path** — reuse the existing search→report navigation (the same `onSelectCandidate` → open `/report` flow).
- **Reading-Room tokens** (`--ink-*`, `--line`, `--warn-*`, `--teal-deep`, `--mono`) + the existing chip/section styling.

---

## 6. Data contract (FE mirror)

Add to `app/web/lib/backend.ts` (FE types must match `schemas/paper_variants.py`): `PaperVariantsResult`, `ValidatedPaperVariant`, `VariantLevel`, `VariantContext`. Reuse the existing `SearchInputCandidate` / `SearchInputSourceInputs` TS types (already mirrored for the search interpretation panel).

A `lib/paperVariants.ts` client: `extractPaperVariants({text?|pdf}, signal) → PaperVariantsResult`, with a `.eamos-mock` fixture (mirror the CLI's mock output) so the surface renders before the endpoint/gateway is live.

---

## 7. Claude ↔ Codex split

| Lane | Work |
|---|---|
| **Codex (`app/backend`)** | Add the **HTTP endpoint** wrapping `PaperVariantsService.extract()` — `POST /api/v1/paper-variants/extract` accepting `{text}` or an uploaded PDF (reuse `pdf_text`), returning the **sanitized** `PaperVariantsResult` + the same CLI-style guardrail/`pdf` meta. Decide auth posture (login-gate + rate-limit, mirroring the chat endpoint, since it can reach the gateway). Keep mock-first. **Backend-led contract — confirm the request/response shape with me before I wire the client.** |
| **Claude (`app/web`)** | The `/paper` surface (input zone, candidate table, fail-closed gating, provenance, actions), the `<CandidateCard>` extraction/reuse, `backend.ts` type mirror + `lib/paperVariants.ts` client + mock fixture, switcher entry, a11y + Reading-Room theming, `.eamos-mock` markers. |

**Gate:** Codex confirms the endpoint contract (path + request + that the response is exactly `PaperVariantsResult` + meta) → Claude builds the FE on the mock, then swaps to live.

---

## 8. Value & impact

- **Value:** a paper-ingest → resolved-variant front door no germline competitor ships with this rigor — provenance-on-every-candidate + fail-closed clinical gating. Feeds the existing report/library/batch surfaces, so it compounds what we have rather than adding a silo.
- **Impact (low risk):** net-new surface but **heavy reuse** (candidate card, library store, report-open path, tokens); **mock-first** so it's inert until the gateway flip; the only safety-critical part is the **fail-closed UX** — it must never present an ambiguous/experimental mention as a clinical, coordinate-resolved variant. Mirrors the backend's own semantics, so FE + BE agree by construction.
- **Dependency:** needs Codex's HTTP endpoint (small) before it's live; renders on mock until then.

---

## 9. Open questions / to confirm

1. **Placement** — `/paper` route (recommended) vs Batch drawer vs search mode (§3). *Primary decision before build.*
2. **Endpoint auth** — login-gated + rate-limited like `/chat/stream`? (lean: yes.)
3. **PDF upload** — multipart to the backend (recommended) vs FE-side text extraction then send text? (lean: backend, reuse `pdf_text`, one engine of record.)
4. **Actions** — confirm "Open report" + "Add to library"; is "Add to Batch" wanted in v1?
5. **`validation_status` enum** — confirm the exact string set Codex emits so the status glyphs map cleanly.

---

## Source connections

- Backend contract: `app/backend/app/schemas/paper_variants.py` · service `app/backend/app/services/paper_variants.py` · CLI `app/backend/app/cli/eamos_paper_variants.py`.
- Reuse: `app/web/components/report/SearchInterpretationPanel.tsx` (candidate card + fail-closed pattern) · variant-library store ([[project_workspace_rail]]).
- Context: AI gateway plan `docs/ai-gateway/plan.md` · memory [[project_ai_gateway]] (paper→variants P1+2 shipped inert) · [[feedback_reuse_assets]].
- Sibling planned work (build AFTER this): `docs/report-acmg-viz/spec.md` ([[project_report_acmg_viz]]).
</content>
