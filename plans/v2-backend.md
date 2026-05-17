# v2 Backend Plan — Codex

## Status (2026-05-15)

| ID | Milestone | Status |
| -- | --------- | ------ |
| BE-1 | Franklin archive | ✅ Done — moved to `archive/franklin/`, removed from registry/services/rules/config/env/tests. `rg -n franklin app` returns no matches. |
| BE-2 | Lookup payload v2 | ✅ Done — six new optional fields on `ReportPayload`, RPE65 fixture at `app/backend/app/fixtures/lookup_v2_modules.json`. Lookup route returns the new modules (locus_context with 5 nearby variants + 11 codon cells, etc.). |
| BE-3 | Lookup-scoped chat endpoint | ✅ Done — `POST /api/v1/chat` and `POST /api/v1/chat/stream` live. Mock-mode returns variant-aware response. |
| BE-4 | Workbench engine stubs | ✅ Done — `POST /api/v1/primer | /crispr | /align`. Fixture responses: 3 primer pairs (one ★), 3 gRNAs + ssODN, 4 trace channels × 80 samples. |
| BE-5 | Test sweep | ✅ Done — `test_franklin_removed.py` added; `test_frontend_contract.py` extended for new models. Historical FE-3.5 sync point; superseded by BE-6's synced 40/40 PASS. |
| BE-6 | Report v2 payload mock-fidelity | ✅ Done (2026-05-15, Codex agent `a862070de2d41f104`). Additive schema fields; `lookup_v2_modules.json` rewritten to mirror the 6 frontend SAMPLE constants; `test_frontend_contract.py` extended. Synced with FE-3.6 → 40/40 PASS. |
| BE-7 | Workbench fixture fidelity | ✅ Done (2026-05-15). `primer/crispr/align_rpe65.json` tightened to mock-JS values. Ambiguities surfaced: CRISPR kept 3 guides (mock shows 6 w/ per-guide `recommended`/`cas`, no schema slot); HDR efficiency `12–18%`→midpoint `0.15`; alignment mismatch index 13→14 for internal consistency. |
| BE-8 | Input normalization | ✅ Done & live-verified (2026-05-16). `normalize_variant_query()` (gene/transcript-prefix strip + whitespace collapse, never lowercases HGVS) + `CANONICAL_TRANSCRIPTS`. `test_lookup_normalize.py` green. |
| BE-9 | VariantValidator coords-resolver | ✅ Done & live-verified (2026-05-16). Queries the transcript accession (`NM_000329.3:c.260A>G`, not the gene form) → `genomic_hg38 == 1-68444869-T-C` confirmed live. |
| BE-10 | Strict-genomic plugin loop | ✅ Done & live-verified (2026-05-16). `STRICT_GENOMIC_PLUGINS` 3-phase loop; gnomAD/SpliceAI `live` after resolver in the Claude-run smoke. |
| BE-11 | LitVar2 + Publications accuracy | ✅ Done & live-verified (2026-05-16). PubMed broadened to gene + OR(cdna/protein/rsID) with gene-only fallback → **10 live articles**; LitVar2 queries the ClinVar-derived rsID + parses `pmids`/`pmids_count`; `publications_callout.total_count` falls back to merged-article count when LitVar2 legitimately returns 0. **Zero schema change** (40/40 holds). |
| BE-12 | Search robustness / error contract | ✅ Done & live-verified (2026-05-16). Frozen `warnings` codes; never-raise graceful fallback (`live_fetch_failed:<Exc>`) confirmed live on transient gnomAD/SpliceAI timeouts. |
| BE-13 | Persistent variant cache | ✅ Done & live-verified (2026-05-16). `variant_cache_repo.py`; **upsert guarded on successful genomic resolution** (no cache poisoning); cache-hit + `?refresh=true` bypass confirmed live. |

FE-3.5 (frontend contract sync + component wiring) is ✅ Done as of 2026-05-15: `backend.ts` interfaces added, `RPE65_SAMPLE` populated, the 6 components wired to `payload.*`. `tsc --noEmit` clean. This exposed the fidelity gap BE-6 closes.

Codex session id (resumable): `019e26bf-c0db-7b03-aff3-a5303bac4eed`. Resume with `codex resume 019e26bf-c0db-7b03-aff3-a5303bac4eed`.

---

You (Codex) are picking up the backend half of the Eamos v2 rebuild. This plan is self-contained — every file path, schema, and verification step is here. You don't need to read the HTML mocks or the frontend plan.

## Context (1 paragraph)

Eamos is a genomic variant lookup tool. Frontend (React/Vite) is being expanded to render new modules on the variant report and a new "Workbench" surface (sequence viewer + design tools). Your job is to:

1. Archive the Franklin tool (Genoox is a competitor — we're cutting them out).
2. Extend `ReportPayload` with six new fields the new report modules consume.
3. Add a lookup-scoped chat endpoint (`POST /api/v1/chat`) — siblings the existing run-scoped `POST /api/v1/runs/{run_id}/chat/stream`, which stays unchanged.
4. Add three Workbench engine endpoints (`POST /api/v1/primer`, `/api/v1/crispr`, `/api/v1/align`) returning canned sample data — real engines come later.
5. Update tests.

Default mode is `USE_REAL_APIS=false` / `LLM_PROVIDER=mock`. Everything works offline against fixtures.

## Coordination with frontend (Claude Code)

Claude Code is porting design mocks in parallel. Your contract surface:

| Frontend | Backend |
| -------- | ------- |
| `app/frontend/src/lib/backend.ts` | `app/backend/app/schemas/*.py` |
| `app/frontend/src/lib/sample-report.ts` | `app/backend/app/fixtures/tools/*.json` |

When you add a new Pydantic field, expect Claude Code to add the matching TypeScript interface field. The test `app/backend/tests/test_frontend_contract.py` enforces this — it must stay passing.

**Sync point** — after each milestone, run:

```bash
cd app/backend && python -m pytest tests/ -q
```

All tests must pass before the next milestone starts.

---

## BE-1 — Franklin archive

Franklin is a competitor. Remove from the active codebase; preserve under `archive/` for reference.

**Move** (create directories as needed):

```
archive/franklin/
  franklin.py                     ← from app/backend/app/tools/franklin.py
  franklin_fixtures.json          ← from app/backend/app/fixtures/tools/franklin_fixtures.json
  franklin-api-field-guide.md     ← from docs/architecture/franklin-api-field-guide.md
```

**Delete from `app/tools/registry.py`** — remove the `"franklin"` key and its import.

**Drop from `app/services/workflow.py`** and `app/services/lookup_service.py` — remove all references to `"franklin"` in the tool loops, evidence tuples, and any helper functions.

**Drop from `app/rules/clinic_rules.py`** — any `franklin`-keyed evidence weighting.

**Drop Franklin settings from `app/core/config.py`**: any `franklin_*` fields (`franklin_email`, `franklin_password`, `franklin_api_token`, `franklin_base_url`, etc.).

**Update `.env.example`** — remove `FRANKLIN_*` lines.

**Update tests** — `app/backend/tests/test_real_agent_smoke.py`, `test_run_flow.py`, `test_search_api.py` — remove any Franklin assertions.

**Update CLAUDE.md indices** — `app/backend/app/tools/CLAUDE.md` (remove the `franklin.py` row) and `app/backend/app/fixtures/tools/CLAUDE.md`.

**Verify**:

```bash
cd app/backend
python -m pytest tests/ -q
grep -r "franklin" app/                 # should be empty
grep -r "Franklin" app/                 # should be empty
```

If `grep` returns anything in `app/`, that's a leak. (References in `docs/` / `archive/` / `CHANGELOG.md` are fine — historical context is preserved there.)

## BE-2 — Lookup payload v2

Extend `ReportPayload` (in `app/backend/app/schemas/run.py`) with six new fields that drive the new frontend report modules. Then plumb them through `app/services/lookup_service.py` so `POST /api/v1/lookup` returns them.

**Add new Pydantic models** at the top of `app/backend/app/schemas/run.py` (before `ReportPayload`):

```python
from typing import Literal

ClassificationTier = Literal["pathogenic", "likely_pathogenic", "vus", "likely_benign", "benign"]
AcmgVerdict = Literal["met", "not_met", "not_assessed"]
PredictorVerdict = Literal["damaging", "tolerated", "uncertain"]


class NearbyVariant(BaseModel):
    cds_pos: int                       # codon offset from query variant centre, -45..+45
    classification: ClassificationTier
    hgvs: str                          # e.g. "c.272A>G"
    clinvar_id: str | None = None


class CodonCell(BaseModel):
    codon_number: int                  # absolute codon number (e.g. 87 for c.260)
    aa_ref: str                        # one-letter AA
    is_query: bool = False             # the codon containing the queried variant


class LocusContext(BaseModel):
    """Region viewer payload — drives <LocusContext /> on the report."""
    gene: str
    centre_cdna: str                   # the queried variant cDNA, e.g. "c.260A>G"
    nearby_variants: list[NearbyVariant] = Field(default_factory=list)
    codon_strip: list[CodonCell] = Field(default_factory=list)  # 11 codons centred on query


class PredictorCard(BaseModel):
    """One card in the <InSilicoGrid />."""
    name: Literal["REVEL", "AlphaMissense", "MetaLR", "SpliceAI"]
    score: float                       # 0..1
    threshold: float                   # 0..1
    verdict: PredictorVerdict
    source_url: str | None = None


class InSilicoPredictions(BaseModel):
    cards: list[PredictorCard] = Field(default_factory=list)
    consensus_note: str                # e.g. "Predictors converge on damaging."


class AcmgCriterion(BaseModel):
    code: Literal[
        "PVS1",
        "PS1", "PS2", "PS3", "PS4",
        "PM1", "PM2", "PM3", "PM4", "PM5", "PM6",
        "PP1", "PP2", "PP3", "PP4", "PP5",
        "BA1",
        "BS1", "BS2", "BS3", "BS4",
        "BP1", "BP2", "BP3", "BP4", "BP5", "BP6", "BP7",
    ]
    verdict: AcmgVerdict
    note: str | None = None


class AcmgCriteriaScaffold(BaseModel):
    criteria: list[AcmgCriterion] = Field(default_factory=list)
    disclaimer: str = "Supporting evidence, not classification."


class CuratedVariantsDistribution(BaseModel):
    """3×4 heat matrix. Rows × cols flattened — 12 cells."""
    cells: dict[str, int] = Field(default_factory=dict)
    # keys: "pathogenic_lof", "pathogenic_missense", "pathogenic_noncoding",
    #       "pathogenic_synonymous", "vus_lof", "vus_missense", ...
    # 12 entries total.
    total: int
    reading: str                       # one-line summary


class AssociatedCondition(BaseModel):
    name: str
    case_count: int
    evidence_level: Literal["definitive", "strong", "moderate", "limited"]
    inheritance: Literal["AR", "AD", "XL", "MT"]
    source: str                        # e.g. "OMIM #204100"


class PublicationsCallout(BaseModel):
    total_count: int
    scholar_url: str
    ai_summary_prompt: str             # text to drop into Ask Eamos when "AI summary" clicked
```

**Add the six new optional fields** to `ReportPayload` (preserve existing fields):

```python
class ReportPayload(BaseModel):
    # ... existing fields unchanged ...
    locus_context: LocusContext | None = None
    in_silico_predictions: InSilicoPredictions | None = None
    acmg_criteria_scaffold: AcmgCriteriaScaffold | None = None
    curated_variants_distribution: CuratedVariantsDistribution | None = None
    associated_conditions: list[AssociatedCondition] = Field(default_factory=list)
    publications_callout: PublicationsCallout | None = None
```

**Populate these fields in `app/services/lookup_service.py`**. For the v2 cycle, use fixture data — real data ingestion is M-002.

Create a new fixture file `app/backend/app/fixtures/lookup_v2_modules.json` with sample data for RPE65 c.260A>G:

```json
{
  "RPE65": {
    "c.260A>G": {
      "locus_context": {
        "gene": "RPE65",
        "centre_cdna": "c.260A>G",
        "nearby_variants": [
          { "cds_pos": -30, "classification": "likely_pathogenic", "hgvs": "c.230T>C", "clinvar_id": "1234" },
          { "cds_pos": -12, "classification": "vus",                "hgvs": "c.248G>A", "clinvar_id": "5678" },
          { "cds_pos": 0,   "classification": "likely_pathogenic", "hgvs": "c.260A>G", "clinvar_id": "1421454" },
          { "cds_pos": 8,   "classification": "benign",             "hgvs": "c.268C>T", "clinvar_id": "9101" },
          { "cds_pos": 23,  "classification": "pathogenic",         "hgvs": "c.283G>A", "clinvar_id": "1121" }
        ],
        "codon_strip": [
          { "codon_number": 82, "aa_ref": "L", "is_query": false },
          { "codon_number": 83, "aa_ref": "V", "is_query": false },
          { "codon_number": 84, "aa_ref": "G", "is_query": false },
          { "codon_number": 85, "aa_ref": "K", "is_query": false },
          { "codon_number": 86, "aa_ref": "Y", "is_query": false },
          { "codon_number": 87, "aa_ref": "D", "is_query": true  },
          { "codon_number": 88, "aa_ref": "L", "is_query": false },
          { "codon_number": 89, "aa_ref": "H", "is_query": false },
          { "codon_number": 90, "aa_ref": "P", "is_query": false },
          { "codon_number": 91, "aa_ref": "I", "is_query": false },
          { "codon_number": 92, "aa_ref": "T", "is_query": false }
        ]
      },
      "in_silico_predictions": {
        "cards": [
          { "name": "REVEL",        "score": 0.78, "threshold": 0.50, "verdict": "damaging",   "source_url": "https://sites.google.com/site/revelgenomics" },
          { "name": "AlphaMissense","score": 0.71, "threshold": 0.564,"verdict": "damaging",   "source_url": "https://alphamissense.hegelab.org" },
          { "name": "MetaLR",       "score": 0.62, "threshold": 0.50, "verdict": "damaging",   "source_url": null },
          { "name": "SpliceAI",     "score": 0.12, "threshold": 0.20, "verdict": "tolerated",  "source_url": "https://spliceailookup.broadinstitute.org" }
        ],
        "consensus_note": "Three of four predictors converge on damaging; SpliceAI shows no splice impact."
      },
      "acmg_criteria_scaffold": {
        "criteria": [
          { "code": "PVS1", "verdict": "not_met",       "note": null },
          { "code": "PS1",  "verdict": "not_met",       "note": null },
          { "code": "PS2",  "verdict": "not_assessed",  "note": null },
          { "code": "PS3",  "verdict": "not_assessed",  "note": null },
          { "code": "PS4",  "verdict": "not_assessed",  "note": null },
          { "code": "PM1",  "verdict": "not_met",       "note": null },
          { "code": "PM2",  "verdict": "met",           "note": "Absent from gnomAD v4 (>250k alleles)." },
          { "code": "PM3",  "verdict": "not_assessed",  "note": null },
          { "code": "PM4",  "verdict": "not_met",       "note": null },
          { "code": "PM5",  "verdict": "met",           "note": "Different missense at same codon previously classified pathogenic." },
          { "code": "PM6",  "verdict": "not_assessed",  "note": null },
          { "code": "PP1",  "verdict": "not_assessed",  "note": null },
          { "code": "PP2",  "verdict": "not_met",       "note": null },
          { "code": "PP3",  "verdict": "met",           "note": "Multiple in-silico predictors agree on damaging." },
          { "code": "PP4",  "verdict": "met",           "note": "Phenotype highly specific for RPE65-related disease." },
          { "code": "PP5",  "verdict": "not_assessed",  "note": null },
          { "code": "BA1",  "verdict": "not_met",       "note": null },
          { "code": "BS1",  "verdict": "not_met",       "note": null },
          { "code": "BS2",  "verdict": "not_assessed",  "note": null },
          { "code": "BS3",  "verdict": "not_assessed",  "note": null },
          { "code": "BS4",  "verdict": "not_assessed",  "note": null },
          { "code": "BP1",  "verdict": "not_met",       "note": null },
          { "code": "BP2",  "verdict": "not_assessed",  "note": null },
          { "code": "BP3",  "verdict": "not_met",       "note": null },
          { "code": "BP4",  "verdict": "not_met",       "note": null },
          { "code": "BP5",  "verdict": "not_assessed",  "note": null },
          { "code": "BP6",  "verdict": "not_assessed",  "note": null },
          { "code": "BP7",  "verdict": "not_met",       "note": null }
        ],
        "disclaimer": "Supporting evidence, not classification."
      },
      "curated_variants_distribution": {
        "cells": {
          "pathogenic_lof": 42,
          "pathogenic_missense": 28,
          "pathogenic_noncoding": 9,
          "pathogenic_synonymous": 0,
          "vus_lof": 3,
          "vus_missense": 51,
          "vus_noncoding": 18,
          "vus_synonymous": 12,
          "benign_lof": 0,
          "benign_missense": 7,
          "benign_noncoding": 31,
          "benign_synonymous": 24
        },
        "total": 225,
        "reading": "Most pathogenic RPE65 variants are loss-of-function or missense in the catalytic domain."
      },
      "associated_conditions": [
        { "name": "Leber congenital amaurosis 2",      "case_count": 187, "evidence_level": "definitive", "inheritance": "AR", "source": "OMIM #204100" },
        { "name": "Retinitis pigmentosa 20",           "case_count":  62, "evidence_level": "strong",     "inheritance": "AR", "source": "OMIM #613794" }
      ],
      "publications_callout": {
        "total_count": 816,
        "scholar_url": "https://scholar.google.com/scholar?q=RPE65+c.260A%3EG",
        "ai_summary_prompt": "Summarise the key publications on RPE65 c.260A>G in plain language for a clinician."
      }
    }
  }
}
```

**In `lookup_service.py`**, after the existing `ReportPayload` is built, load this fixture keyed by `(gene, cdna)` and attach the six new fields. If no fixture entry matches, leave them as `None` / empty list.

**Verify**:

```bash
cd app/backend
python -m pytest tests/test_frontend_contract.py -q
# All seven existing parametrised cases pass. (Claude Code will extend this test for the new fields.)

curl -X POST http://localhost:8000/api/v1/lookup \
  -H "Content-Type: application/json" \
  -d '{"gene":"RPE65","cdna":"c.260A>G"}' | jq .report_payload.locus_context
# Should return the locus_context object with 5 nearby variants and 11 codon cells.
```

## BE-3 — Lookup-scoped chat endpoint

The existing endpoint `POST /api/v1/runs/{run_id}/chat/stream` is scoped to a run. The new endpoint is scoped to a lookup result (or Workbench session) — no run required.

**Create `app/backend/app/api/routes/chat.py`**:

```python
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import StreamingResponse

from app.schemas.chat import ChatRequest, ChatResponse

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
def chat(payload: ChatRequest, request: Request) -> ChatResponse:
    service = getattr(request.app.state, "chat_service", None)
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Chat service is unavailable.",
        )
    return service.respond(payload)


@router.post("/stream")
def chat_stream(payload: ChatRequest, request: Request) -> StreamingResponse:
    service = getattr(request.app.state, "chat_service", None)
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Chat service is unavailable.",
        )
    return StreamingResponse(service.respond_stream(payload), media_type="text/plain")
```

**Extend `app/backend/app/schemas/chat.py`** — add request/response models for the new endpoint:

```python
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.run import ReportPayload


WorkbenchTool = Literal["viewer", "primer", "crispr", "align", "compare"]


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class WorkbenchEdit(BaseModel):
    position: int                      # codon offset
    ref_base: Literal["A", "T", "C", "G"]
    new_base: Literal["A", "T", "C", "G", "del"]
    consequence: str                   # "Missense p.Asp87Gly" / "Frameshift" / etc.


class WorkbenchContext(BaseModel):
    active_tool: WorkbenchTool
    scratchpad: list[WorkbenchEdit] = Field(default_factory=list)
    selected_primer_pair: int | None = None
    selected_guide: int | None = None


class ChatRequest(BaseModel):
    question: str
    variant_context: ReportPayload
    history: list[ChatMessage] = Field(default_factory=list)
    workbench: WorkbenchContext | None = None


class ChatResponse(BaseModel):
    answer: str
```

**Register the router** in `app/backend/app/main.py` — add `app.include_router(chat.router)` next to the other route registrations.

**Wire `chat_service`** in `app/main.py:create_app` — instantiate a `ChatService` and attach as `app.state.chat_service`. Reuse the existing chat logic if there's a service; otherwise create a thin wrapper:

```python
# app/backend/app/services/chat_service.py
class ChatService:
    def __init__(self, settings, llm_client):
        self.settings = settings
        self.llm = llm_client

    def respond(self, payload: ChatRequest) -> ChatResponse:
        # Mock: echo the question with variant context
        if self.settings.llm_provider == "mock":
            return ChatResponse(answer=self._mock_answer(payload))
        # Live: call LLM with system prompt extended for workbench context
        return ChatResponse(answer=self.llm.complete(self._build_prompt(payload)))

    def respond_stream(self, payload: ChatRequest):
        text = self.respond(payload).answer
        for word in text.split():
            yield word + " "

    def _mock_answer(self, payload: ChatRequest) -> str:
        gene = payload.variant_context.variant_summary_rows[0].gene if payload.variant_context.variant_summary_rows else "this variant"
        tool = payload.workbench.active_tool if payload.workbench else "lookup"
        return f"[mock] Asked about {gene} in {tool} mode: {payload.question}"

    def _build_prompt(self, payload: ChatRequest) -> str:
        base = "You are Eamos, a genomic evidence assistant. Cite source databases with bracket tags like [CV] [gn] [SA] [AM] [RV] [OM] [CT] [UP] [PP]. Never provide diagnoses."
        if payload.workbench:
            wb = payload.workbench
            base += f"\nWorkbench context: active tool = {wb.active_tool}. Scratchpad has {len(wb.scratchpad)} edits."
        return f"{base}\n\nQuestion: {payload.question}"
```

**Verify**:

```bash
cd app/backend
python -m pytest tests/ -q
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"question":"Is this pathogenic?","variant_context":{"patient_id":"demo","variant_summary_rows":[{"gene":"RPE65"}]}}'
# Returns ChatResponse with mocked answer mentioning RPE65.
```

## BE-4 — Workbench engine stubs

Three endpoints returning canned data shaped like the responses from the v2 sample data. Real engines (Primer3 / CRISPOR / Needleman–Wunsch / AB1 parser) are M-002.

**Create `app/backend/app/api/routes/workbench.py`**:

```python
from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter
from app.schemas.workbench import (
    PrimerRequest, PrimerResponse,
    CrisprRequest, CrisprResponse,
    AlignRequest, AlignResponse,
)

router = APIRouter(prefix="/api/v1", tags=["workbench"])

FIXTURES_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "workbench"


def _load(name: str) -> dict:
    return json.loads((FIXTURES_DIR / name).read_text())


@router.post("/primer", response_model=PrimerResponse)
def design_primers(payload: PrimerRequest) -> PrimerResponse:
    return PrimerResponse(**_load("primer_rpe65.json"))


@router.post("/crispr", response_model=CrisprResponse)
def design_guides(payload: CrisprRequest) -> CrisprResponse:
    return CrisprResponse(**_load("crispr_rpe65.json"))


@router.post("/align", response_model=AlignResponse)
def align(payload: AlignRequest) -> AlignResponse:
    return AlignResponse(**_load("align_rpe65.json"))
```

**Create `app/backend/app/schemas/workbench.py`** with the request/response models. Match the field names in `e:\Web tool\Claude Design\Workbench\primer.js`, `crispr.js`, `alignment.js`:

```python
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


# ─────────── Primer ───────────

PrimerMode = Literal["sanger", "qpcr", "arms"]


class PrimerRequest(BaseModel):
    gene: str
    cdna: str
    mode: PrimerMode = "sanger"
    tm_min: float = 58.0
    tm_max: float = 62.0
    product_size_min: int = 300
    product_size_max: int = 700
    avoid_snps: bool = True


class PrimerPair(BaseModel):
    index: int
    forward: str
    reverse: str
    tm_forward: float
    tm_reverse: float
    gc_forward: float
    gc_reverse: float
    product_size: int
    specificity_hits: int
    notes: str = ""
    recommended: bool = False


class PrimerResponse(BaseModel):
    mode: PrimerMode
    pairs: list[PrimerPair] = Field(default_factory=list)


# ─────────── CRISPR ───────────

CasEnzyme = Literal["SpCas9", "SaCas9", "Cas12a"]


class CrisprRequest(BaseModel):
    gene: str
    cdna: str
    cas: CasEnzyme = "SpCas9"
    strand_filter: Literal["both", "plus", "minus"] = "both"
    off_target_tolerance: int = 3


class CrisprGuide(BaseModel):
    index: int
    cut_position: int                # absolute cdna position
    strand: Literal["+", "-"]
    guide: str                       # 20 nt
    pam: str                         # e.g. "AGG"
    on_target_score: float           # 0..1
    off_target_score: float          # 0..1
    gc_percent: float
    notes: str = ""


class HdrSsodn(BaseModel):
    reference_arm: str
    variant_arm: str
    repair_template: str
    edits_encoded: list[str] = Field(default_factory=list)
    arm_lengths: dict[str, int] = Field(default_factory=dict)
    estimated_hdr_efficiency: float


class CrisprResponse(BaseModel):
    cas: CasEnzyme
    guides: list[CrisprGuide] = Field(default_factory=list)
    ssodn: HdrSsodn | None = None


# ─────────── Alignment ───────────

class AlignRequest(BaseModel):
    gene: str
    cdna: str
    user_sequence: str | None = None
    ab1_blob_base64: str | None = None


class TraceChannel(BaseModel):
    base: Literal["A", "T", "C", "G"]
    values: list[float]              # 0..1 normalised channel signal per sample


class AlignResponse(BaseModel):
    reference: str
    sanger_read: str
    match_line: str                  # "|" at matches, " " at mismatches
    mismatch_positions: list[int] = Field(default_factory=list)
    target_position: int
    trace_channels: list[TraceChannel] = Field(default_factory=list)
    base_calls: list[str] = Field(default_factory=list)
    q_scores: list[int] = Field(default_factory=list)
```

**Create fixture files** in `app/backend/app/fixtures/workbench/`:

- `primer_rpe65.json` — at least one ★ recommended pair + 2 alternates, RPE65 c.260 region. Borrow numerics from `e:\Web tool\Claude Design\Workbench\primer.js` (the sample data block at the top of that file).
- `crispr_rpe65.json` — 3 gRNAs + ssODN block. Borrow from `crispr.js`.
- `align_rpe65.json` — reference + Sanger read (1 mismatch at target), 4 trace channels (~80 samples each), base calls, Q-scores. Borrow from `alignment.js`. Keep arrays compact — ~80 samples is enough for the chromatogram to render correctly.

**Register the router** in `app/main.py`.

**Verify**:

```bash
cd app/backend
python -m pytest tests/ -q
curl -X POST http://localhost:8000/api/v1/primer  -H "Content-Type: application/json" -d '{"gene":"RPE65","cdna":"c.260A>G"}' | jq .
curl -X POST http://localhost:8000/api/v1/crispr  -H "Content-Type: application/json" -d '{"gene":"RPE65","cdna":"c.260A>G"}' | jq .
curl -X POST http://localhost:8000/api/v1/align   -H "Content-Type: application/json" -d '{"gene":"RPE65","cdna":"c.260A>G"}' | jq .
# Each returns the corresponding fixture.
```

## BE-5 — Test sweep

**Add `app/backend/tests/test_franklin_removed.py`**:

```python
"""Smoke test that Franklin is fully archived."""
import importlib
import pkgutil
from pathlib import Path

import pytest

import app

APP_ROOT = Path(app.__file__).parent


def test_franklin_module_does_not_exist():
    franklin_path = APP_ROOT / "tools" / "franklin.py"
    assert not franklin_path.exists(), "Franklin tool should be archived, not active."


def test_franklin_fixture_does_not_exist():
    fixture_path = APP_ROOT / "fixtures" / "tools" / "franklin_fixtures.json"
    assert not fixture_path.exists(), "Franklin fixture should be archived, not active."


def test_no_franklin_imports():
    """No module under app/ should import franklin."""
    leaks = []
    for module_info in pkgutil.walk_packages([str(APP_ROOT)], prefix="app."):
        module = importlib.import_module(module_info.name)
        source_path = getattr(module, "__file__", None)
        if not source_path:
            continue
        text = Path(source_path).read_text(encoding="utf-8")
        if "franklin" in text.lower():
            leaks.append(module_info.name)
    assert not leaks, f"Franklin references leaked into: {leaks}"
```

**Extend `app/backend/tests/test_frontend_contract.py`** — the existing parametrized test asserts every Pydantic field has a TS counterpart. Add cases for the six new `ReportPayload` fields and the new schemas (`LocusContext`, `NearbyVariant`, `CodonCell`, `InSilicoPredictions`, `PredictorCard`, `AcmgCriterion`, `AcmgCriteriaScaffold`, `CuratedVariantsDistribution`, `AssociatedCondition`, `PublicationsCallout`, `ChatRequest`, `ChatResponse`, `ChatMessage`, `WorkbenchContext`, `WorkbenchEdit`, `PrimerRequest`, `PrimerResponse`, `PrimerPair`, `CrisprRequest`, `CrisprResponse`, `CrisprGuide`, `HdrSsodn`, `AlignRequest`, `AlignResponse`, `TraceChannel`).

(Claude Code will land the TS interfaces on the frontend side — this test will fail until both halves are in place. That's the desired sync point.)

**Final verify**:

```bash
cd app/backend
python -m pytest tests/ -q
# All tests pass except potentially test_frontend_contract.py, which waits on frontend.

grep -ri "franklin" app/ tests/        # should be empty
```

## BE-6 — Report v2 payload mock-fidelity

**Problem.** FE-3.5 wired the six report v2 components to `payload.*`, but Codex's `lookup_v2_modules.json` fixture carries less than the **Report Page v2** mock shows. The components still embed richer `SAMPLE` blocks (ported from the mock) as prop fallbacks, so payload-driven rendering visually regresses vs the mock. Close the gap so the live payload is mock-faithful and the frontend can delete the lossy fallbacks (FE-3.6).

**Fidelity source of truth.** The `SAMPLE` / default constants currently in these six frontend files ARE the mock-faithful values. Read them and mirror their content into the fixture:

| File | Constants to mirror |
| ---- | ------------------- |
| `app/frontend/src/components/report/LocusContext.tsx` | `SAMPLE_NEARBY` (11 variants), `SAMPLE_CODONS` (11 codons w/ DNA + `Asp → Gly`), the `coords` default string |
| `app/frontend/src/components/report/InSilicoGrid.tsx` | `SAMPLE_CARDS` (per-card descriptive verdict text), `SAMPLE_CONSENSUS` |
| `app/frontend/src/components/report/AcmgCriteriaFold.tsx` | `SAMPLE_INTRO`, `SAMPLE_NOTE` |
| `app/frontend/src/components/report/CuratedVariantsGrid.tsx` | `SAMPLE_ROWS` counts (210/187/6/3 …), `sub` default, `SAMPLE_READING` |
| `app/frontend/src/components/report/AssociatedConditions.tsx` | `SAMPLE` (5 conditions w/ split `metaTag`/`src`), `sub` default |
| `app/frontend/src/components/report/PublicationsCallout.tsx` | `DEFAULT_BLURB` |

**Schema changes** (`app/backend/app/schemas/run.py`) — additive only; do not rename or drop existing fields (the `test_frontend_contract.py` canary depends on every field having a TS twin):

```python
class CodonCell(BaseModel):
    codon_number: int
    aa_ref: str                      # 1-letter, UNCHANGED (existing contract)
    aa_alt: str | None = None        # 1-letter alt for the query codon, e.g. "G" (Gly)
    dna_ref: str = ""                # reference codon triplet, e.g. "GAC"
    dna_alt: str | None = None       # variant codon triplet for query, e.g. "GGC"
    is_query: bool = False

class NearbyVariant(BaseModel):
    cds_pos: int
    classification: ClassificationTier
    hgvs: str
    clinvar_id: str | None = None
    protein_change: str | None = None   # e.g. "p.Asp79Gly" — for the dot tooltip title

class LocusContext(BaseModel):
    gene: str
    centre_cdna: str
    coords: str = ""                 # "chr1 : 68,444,849 — 68,444,889  ·  RPE65 exon 4  ·  (+) strand"
    nearby_variants: list[NearbyVariant] = Field(default_factory=list)  # 11, matching SAMPLE_NEARBY
    codon_strip: list[CodonCell] = Field(default_factory=list)          # 11, matching SAMPLE_CODONS

class PredictorCard(BaseModel):
    name: Literal["REVEL", "AlphaMissense", "MetaLR", "SpliceAI"]
    score: float
    threshold: float
    verdict: PredictorVerdict
    verdict_label: str = ""          # descriptive, e.g. "Pathogenic supporting" / "No splice impact"
    source_url: str | None = None

class AcmgCriteriaScaffold(BaseModel):
    criteria: list[AcmgCriterion] = Field(default_factory=list)
    intro: str = ""                  # SAMPLE_INTRO prose
    note: str = ""                   # SAMPLE_NOTE prose
    disclaimer: str = "Supporting evidence, not classification."

class CuratedVariantsDistribution(BaseModel):
    cells: dict[str, int] = Field(default_factory=dict)   # mirror SAMPLE_ROWS counts
    row_totals: dict[str, int] = Field(default_factory=dict)  # {"pathogenic":406,"vus":426,"benign":454}
    total: int
    subtitle: str = ""               # "1,286 classified variants · ClinVar + UniProt"
    reading: str

class AssociatedCondition(BaseModel):
    name: str
    case_count: int
    evidence_level: Literal["definitive", "strong", "moderate", "limited"]
    inheritance: Literal["AR", "AD", "XL", "MT"]
    db_tag: str                      # "#204100" / "No OMIM entry" / "Orphanet ORPHA:71862"
    db_tag_bold: str | None = None   # "OMIM" (rendered bold) — None when no DB prefix
    source_list: str                 # "OMIM · Monarch · DECIPHER · GenCC · ClinGen"

class PublicationsCallout(BaseModel):
    total_count: int
    scholar_url: str
    blurb: str = ""                  # DEFAULT_BLURB descriptive sentence
    ai_summary_prompt: str
```

`ReportPayload` keeps `associated_conditions: list[AssociatedCondition]`. The list subtitle ("5 conditions · …") stays a frontend-static string — not a backend field.

**Fixture.** Rewrite `app/backend/app/fixtures/lookup_v2_modules.json` for `RPE65 / c.260A>G` so every value equals the mirrored SAMPLE constants:
- `codon_strip`: 11 codons 82–92 with correct `aa_ref` (Y,R,E,P,V,D,K,T,V,A,I → matching SAMPLE_CODONS), `dna_ref` triplets (TAT,CGG,GAA,CCT,GTG,GAC,AAG,ACA,GTC,GCC,ATT), query codon 87 `aa_alt="G"`, `dna_alt="GGC"`, `is_query=true`.
- `nearby_variants`: 11 entries; query at `cds_pos=0`; classifications + hgvs + protein_change mirroring SAMPLE_NEARBY's 11 titles. Spread `cds_pos` so the frontend mapping (`left = 50 + cds_pos/span*50`) lands dots at a visually equivalent density.
- predictor `verdict_label`, ACMG `intro`/`note`, distribution `row_totals`/`subtitle`, condition `db_tag`/`source_list` (5 conditions), publications `blurb` — all from the SAMPLE constants.

**Tests.** Extend `app/backend/tests/test_frontend_contract.py` with the new fields (`aa_alt`, `dna_ref`, `dna_alt`, `coords`, `protein_change`, `verdict_label`, `intro`, `note`, `row_totals`, `subtitle`, `db_tag`, `db_tag_bold`, `source_list`, `blurb`). It will fail until FE-3.6 lands the matching TS — that is the planned sync point.

**Verify**:

```bash
cd app/backend && python -m pytest tests/ -q
curl -X POST http://localhost:8000/api/v1/lookup -H "Content-Type: application/json" \
  -d '{"gene":"RPE65","cdna":"c.260A>G"}' | jq '.report_payload.locus_context.codon_strip[5]'
# codon 87: aa_ref "D", aa_alt "G", dna_ref "GAC", dna_alt "GGC", is_query true
```

## BE-7 — Workbench fixture fidelity

BE-4 created `app/backend/app/fixtures/workbench/{primer,crispr,align}_rpe65.json` by "borrowing numerics" from the Workbench mock JS. Tighten them to exact mock fidelity so FE-6/FE-7 render identically to **Eamos Workbench v1**.

- Read `e:\Web tool\Claude Design\Workbench\primer.js`, `crispr.js`, `alignment.js` sample-data blocks.
- Make each fixture an exact transcription: same primer pairs/Tm/GC/product sizes (★ pair flagged), same 3 gRNAs + ssODN arms/efficiency, same ~80-sample 4-channel trace + base calls + Q-scores + the single target mismatch.
- No schema changes expected (BE-4 models stand). If a mock field has no schema slot, surface it — don't silently drop.

**Verify**: `pytest tests/ -q`, then `curl` each endpoint and diff key fields against the mock JS.

---

# Variant-search-engine integration (BE-8 … BE-13)

Source plan: `C:\Users\seamegdool\.claude\plans\before-you-beging-the-groovy-swan.md`.
Adapts the external `variant-search-engine` design's **concepts** (input cleaning,
LitVar2 publications, VariantValidator strict coords, an expandable strict-genomic
plugin loop, a persistent cache) into Eamos's FastAPI tool-registry + React report
page. The external standalone `server.py`/`dashboard.html` are **not** added
verbatim. Incoherence pass (2026-05-16) ground-truthed every "Eamos reality"
claim below against live code — all confirmed.

**Ownership for this batch:** Codex owns BE-8…BE-13 (`app/backend/**` only).
Claude Code owns FE-14 + the BE-12 frontend half (`app/frontend/**` only). The
only soft-coupling point is the **frozen `warnings` codes** in BE-12 — both sides
build to those exact strings, no wait. Dependency order: **BE-8 → BE-9 → BE-10 →
BE-11 → BE-12 → BE-13**. BE-9 is the linchpin; BE-11 is independent of BE-9/10
(parallelizable); BE-13 depends on BE-8 (key) + BE-9/10/11 (what it caches).

**Watch-outs (do not relearn):** `use_real_apis` is global, default stays
`False`, opt-in via env only. Never `lower()` HGVS (`A>G` / `p.Asp87Gly` are
case-significant). VEP does **not** set `genomic_hg38` (stays `""` from
`lookup_service.py:86`). New tools must **never raise** — always self-fallback to
fixture, mirroring `pubmed.py`/`gnomad.py`. BE-11 is deliberately zero-schema so
the contract test cannot break and there is no irreversible
`backend.ts`/`sample-report.ts` migration — keep it that way.

## BE-8 — Input normalization

Pasted Franklin-style input like `RPE65:c.260A>G` currently becomes a malformed
`transcript_hgvs`. Add a single normalization function and wire it at both
species callsites.

**New** — `normalize_variant_query(gene, cdna, transcript) -> (gene, hgvs, transcript, kind)`
top-level in `app/backend/app/services/lookup_service.py`. Rules:
`gene.strip().upper()`; strip a leading `GENE:` or `NM_/ENST` accession+colon
from `cdna`; collapse internal whitespace; **preserve HGVS case** (the external
`lower()` rule is explicitly rejected — `A>G`/`p.Asp87Gly` are case-significant);
classify `kind ∈ {cdna, rsid, protein, genomic, unknown}`.

**Wire** — replace the inline logic at `lookup_service.py:62-63` (mouse) and
`:77-79` (human) with calls to `normalize_variant_query`. (Frontend mirror
`cleanQuery()` in `app/frontend/src/lib/variant-format.ts` is FE-14 — Claude
Code's, not Codex's.)

**Verify**:

```bash
cd app/backend && python -m pytest tests/test_lookup_normalize.py -q
curl -X POST http://localhost:8000/api/v1/lookup -H "Content-Type: application/json" \
  -d '{"gene":"RPE65","cdna":"RPE65:c.260A>G"}'
curl -X POST http://localhost:8000/api/v1/lookup -H "Content-Type: application/json" \
  -d '{"gene":"RPE65","cdna":"c.260A>G"}'
# Both produce an identical transcript_hgvs.
```

## BE-9 — VariantValidator coords-resolver tool (the linchpin)

`ensembl_vep.py._fetch_live` never sets `variant.genomic_hg38` (confirmed: stays
`""` from `lookup_service.py:86`), so gnomAD degrades to `live_stub`
(`gnomad.py:80-94`). This tool resolves strict VCF coords and mutates the shared
variant so the strict-genomic plugins can run.

**New** — `app/backend/app/tools/variant_validator.py`: `source="variant_validator"`,
`fixture_name="variant_validator_fixtures.json"`, subclass `FixtureBackedTool`,
**exact same** `use_real_apis`/try/except-fallback shape as `pubmed.py`
(`if not use_real_apis or variant is None → fixture`; `try _fetch_live except
Exception → status="fallback"` + `live_fetch_failed:<ExceptionName>` warning).
Live: `GET {variant_validator_base_url}/VariantValidator/variantvalidator/GRCh38/{gene}:{hgvs}/all`
→ parse `primary_assembly_loci.grch38.vcf` → `{chr,pos,ref,alt}`. **Mutates**
`variant.genomic_hg38 = f"{chr}-{pos}-{ref}-{alt}"` (+ `variation_type` /
`consequence` only if blank). Secondary fallback: derive coords from the existing
VEP `raw` payload before giving up. **Never raises.**

**Config** — add `variant_validator_base_url: str = "https://rest.variantvalidator.org"`
to `app/backend/app/core/config.py` next to `clinvar_base_url` (line 42).

**Fixture** — `app/backend/app/fixtures/tools/variant_validator_fixtures.json`:
real GRCh38 VCF for RPE65 c.260A>G captured from a live smoke run (do **not**
invent the coordinates).

**Docs** — when this tool lands, add a `variant_validator` row to the tool tables
in `README.md` (~line 130) and `app/backend/README.md` (~line 56) and the
`app/backend/app/tools/CLAUDE.md` index. (Per `plans/README.md` rule #3, the
milestone-shipper updates the shared docs after the code change.)

**Verify**:

```bash
$env:USE_REAL_APIS="true"; curl -X POST http://localhost:8000/api/v1/lookup \
  -H "Content-Type: application/json" -d '{"gene":"RPE65","cdna":"c.260A>G"}'
# report_payload.variant_summary_rows[0].genomic_hg38 populated.
# Offline (USE_REAL_APIS unset): fixture coords returned, no raise.
```

## BE-10 — Explicit strict-genomic plugin loop

Make the resolve→plugin→annotate ordering explicit so adding a future
coords-keyed DB is one tuple entry, zero `lookup_service` change.

**New** — `STRICT_GENOMIC_PLUGINS = ("gnomad", "spliceai")` in
`app/backend/app/tools/registry.py` + a contract docstring: "a
`FixtureBackedTool` whose `get_evidence` reads `variant.genomic_hg38`, degrading
to `live_stub` if absent" — gnomAD already models exactly this
(`gnomad.py:80-94`).

**Refactor** — the `for name in ('vep','spliceai','clinvar','gnomad','pubmed')`
loop at `lookup_service.py:110` into 3 documented phases with the **same**
`evidence`/`evidence_map`/`evidence_statuses` accumulation (no behaviour change
for existing tools): (1) **resolve** = `vep` → `variant_validator`; (2) iterate
`STRICT_GENOMIC_PLUGINS`; (3) **annotate** = `clinvar`, `pubmed`, `litvar2`.
Document that phases 1-2 mutate the shared `SimpleNamespace` variant (the risk
the explicit phases mitigate).

**Verify**:

```bash
$env:USE_REAL_APIS="true"; curl -X POST http://localhost:8000/api/v1/lookup \
  -H "Content-Type: application/json" -d '{"gene":"RPE65","cdna":"c.260A>G"}'
# gnomAD evidence status == "live" (was "live_stub" before BE-9/BE-10).
cd app/backend && python -m pytest tests/ -q   # 40/40 unchanged
```

## BE-11 — LitVar2 tool + Publications accuracy

The Publications section is currently 100% static fixture
(`lookup_v2_modules.json → publications_callout`). LitVar2 *complements*
PubMed (variant-precise count/IDs) — it does **not** replace `pubmed.py`, whose
URLs are already correct (`https://pubmed.ncbi.nlm.nih.gov/{pmid}/`,
`pubmed.py:113`).

**New** — `app/backend/app/tools/litvar2.py`: `source="litvar2"`,
`fixture_name="litvar2_fixtures.json"`, same FixtureBackedTool shape. Live:
`{litvar2_base_url}/variant/autocomplete/?query={gene} {hgvs}` → `litvar_id`,
then `{litvar2_base_url}/variant/get/{litvar_id}/publications` → PMIDs/count.
`summary = {litvar_id, total_publications, articles:[{pmid, title,
url=https://pubmed.ncbi.nlm.nih.gov/{pmid}/}], scholar_url}`. Register in
`build_tool_registry`; add `litvar2_base_url: str = "https://www.ncbi.nlm.nih.gov/research/litvar2-api"`
to `config.py`; add `litvar2_fixtures.json` with an RPE65 sample.

**Publications wiring** in `lookup_service.py` *after* `base_payload` is built
(reassign, mirroring the `draft_render` field reassignment at lines 233-237 —
the `**_lookup_v2_modules` spread at line 219 sets the fixture default, explicit
reassignment overrides it): `publications_callout.total_count` = LitVar2 live
count else `len(pubmed_articles)`; `scholar_url` = LitVar2 else URL-encoded
Scholar query; `blurb` = composed sentence (fixture blurb as fallback); merge
LitVar2 PMIDs into `pubmed_articles` (union by `pmid`, dedupe, normalize URL).

**Schema — ZERO changes.** `PublicationsCallout`/`PubMedArticle` already
suffice. `backend.ts`/`sample-report.ts`/`test_frontend_contract.py` untouched
(stays 40/40). Deliberate: no irreversible migration. Keep it this way.

**Docs** — when this tool lands, add a `litvar2` row to the tool tables in
`README.md` + `app/backend/README.md` + `app/backend/app/tools/CLAUDE.md`
(per `plans/README.md` rule #3).

**Verify**:

```bash
$env:USE_REAL_APIS="true"; curl -X POST http://localhost:8000/api/v1/lookup \
  -H "Content-Type: application/json" -d '{"gene":"RPE65","cdna":"c.260A>G"}'
# .report_payload.publications_callout.total_count is real;
# every merged article url == https://pubmed.ncbi.nlm.nih.gov/{pmid}/
cd app/backend && python -m pytest tests/test_frontend_contract.py -q   # 40/40
```

## BE-12 — Search robustness / error contract

Machine-readable warning codes; HTTP 200 is kept (no error-status change). The
codes are the **only** soft-coupling point with the frontend (FE-14) — they live
in the existing `LookupResponse.warnings: list[str]` field, **not** a schema
change.

### Frozen `warnings` codes — BE-12 ⇄ FE-14 contract

> **Do not change these strings without updating both `v2-backend.md` (Codex)
> and `v2-frontend.md`/FE-14 (Claude Code) in the same change.** Frozen
> 2026-05-16 in Step 0c so both sides build to the same constants with no wait.

| Code string | Backend emits when | FE-14 reaction |
| ----------- | ------------------ | -------------- |
| `input_unparseable:<kind>` | `normalize_variant_query` cannot classify the query. `<kind>` ∈ `{cdna,rsid,protein,genomic,unknown}`. Also set `report_payload.limitations` to a human sentence. | Inline malformed-input hint near the search box. No retry. (Client-side `classify()==unknown` short-circuits *before* the request — this code covers the server-confirmed case.) |
| `no_genomic_resolution` | Every coords resolver failed (VEP → VariantValidator → VEP-`raw` fallback all gave nothing). | "We couldn't resolve this variant" panel — visually **distinct** from a generic network failure. No auto-retry. |
| `live_fetch_failed:<ExceptionName>` | A tool's live call raised and it fell back to fixture. **This is the existing shape** already emitted by `pubmed.py:41` / `gnomad.py:64` — the suffix is `type(exc).__name__` (e.g. `live_fetch_failed:ConnectError`), the **exception class name, NOT the tool name**. (Incoherence finding #6, 2026-05-16: the source plan wrote `live_fetch_failed:<Tool>`; the real contract is `<ExceptionName>`.) | Treat as transient → show a retry affordance. FE-14 keys on the `live_fetch_failed:` **prefix only**; it must never parse or branch on the suffix. |

**Backend** — emit `input_unparseable:<kind>` + populate `report_payload.limitations`
on unparseable input; emit `no_genomic_resolution` when all resolvers fail; leave
the existing `live_fetch_failed:<ExceptionName>` path as-is (do not rename it to
match the source plan's `<Tool>` notation — the frozen contract above is the real
one). All transient failures keep HTTP 200 + `status="fallback"`.

**Verify**:

```bash
cd app/backend && python -m pytest tests/ -q   # 40/40 unchanged (no schema change)
curl -X POST http://localhost:8000/api/v1/lookup -H "Content-Type: application/json" \
  -d '{"gene":"RPE65","cdna":"???not-a-variant???"}'
# warnings contains input_unparseable:<kind>; report_payload.limitations populated.
```

## BE-13 — Persistent variant cache (build now, on Eamos's DB)

Build the 30-day cache on Eamos's **existing** SQLAlchemy `database_url` — **not**
a separate `variant_universal_cache.db`.

**New** — `app/backend/app/repos/variant_cache_repo.py` following the existing
`*_repo.py` pattern (`reports_repo.py`/`search_repo.py`), using the engine/session
from `app/core/db.py` + `settings.database_url`. Table `variant_cache(query_string
UNIQUE, litvar_id, total_publications, publication_data JSON-text,
strict_genomic_cache JSON-text, created_at)`; create on startup the same way
other repos' tables are created.

**Config** — `cache_ttl_days: int = 30` in `config.py`.

**Wrap** `lookup_service.lookup`: after BE-8 normalization, key = normalized
query string. **Cache active only when `use_real_apis` is true** (fixtures are
deterministic/fast; caching them would mask fixture edits). Fresh hit
(`age < cache_ttl_days`) → hydrate resolved coords + LitVar2 publications +
strict-genomic plugin evidence from cache, skip the live resolve+plugin calls.
Miss/expired → run the phases, then write cache. Provide a cache-bypass
(`?refresh=1` on the route or a request flag) and clean expired rows on read.

**Verify**:

```bash
cd app/backend && python -m pytest tests/test_variant_cache.py -q   # hit/miss/expiry
$env:USE_REAL_APIS="true"
# two consecutive identical live curls — the 2nd is served from cache
# (assert via a source marker / log line).
```

## BE-8…BE-13 end-to-end verification

```powershell
cd app/backend; python -m pytest tests/ -q                          # 40/40 stays green
$env:HSIL_RUN_LIVE_API_SMOKE="1"; python -m pytest tests/test_real_agent_smoke.py -q
# Manual, real APIs (opt-in):
$env:USE_REAL_APIS="true"; python -m uvicorn app.main:create_app --factory
curl -X POST http://localhost:8000/api/v1/lookup -H "Content-Type: application/json" -d '{\"gene\":\"RPE65\",\"cdna\":\"RPE65:c.260A>G\"}'
# expect: genomic_hg38 populated; gnomad status "live"; publications_callout.total_count real;
#         article urls = pubmed.ncbi.nlm.nih.gov/{pmid}/; 2nd identical call served from cache
```

---

## Out of scope (M-002 follow-ups)

- Real Primer3 invocation (replace BE-4 stub)
- Real CRISPOR invocation
- Real Needleman–Wunsch + biopython AB1 parsing
- Live `/api/v1/chat` calls to Anthropic / OpenAI (mock-mode only for v2)
- Live data feeds for the six new `ReportPayload` fields (fixtures for v2)
- Mouse mm39 paths for `/api/v1/primer`, `/crispr`, `/align`

---

## Working style for Codex

- Touch only the files listed per milestone. Don't refactor adjacent code.
- Match existing patterns: fixture-backed tools subclass `FixtureBackedTool` in `app/tools/base.py`; services live in `app/services/`; routes register via `app.include_router(...)` in `app/main.py`.
- Don't add error handling for impossible scenarios. Trust internal callers.
- Don't add backward-compatibility shims for Franklin (the user explicitly wants it removed).
- Stop after each milestone for a sync check. Report what you changed + the test command output.
- If you hit ambiguity, surface it — don't pick silently. The frontend plan and shared contract are the tie-breakers.
