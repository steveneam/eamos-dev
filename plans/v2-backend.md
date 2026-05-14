# v2 Backend Plan — Codex

## Status (2026-05-15)

| ID | Milestone | Status |
| -- | --------- | ------ |
| BE-1 | Franklin archive | ✅ Done — moved to `archive/franklin/`, removed from registry/services/rules/config/env/tests. `rg -n franklin app` returns no matches. |
| BE-2 | Lookup payload v2 | ✅ Done — six new optional fields on `ReportPayload`, RPE65 fixture at `app/backend/app/fixtures/lookup_v2_modules.json`. Lookup route returns the new modules (locus_context with 5 nearby variants + 11 codon cells, etc.). |
| BE-3 | Lookup-scoped chat endpoint | ✅ Done — `POST /api/v1/chat` and `POST /api/v1/chat/stream` live. Mock-mode returns variant-aware response. |
| BE-4 | Workbench engine stubs | ✅ Done — `POST /api/v1/primer | /crispr | /align`. Fixture responses: 3 primer pairs (one ★), 3 gRNAs + ssODN, 4 trace channels × 80 samples. |
| BE-5 | Test sweep | ✅ Done — `test_franklin_removed.py` added; `test_frontend_contract.py` extended for new models. Pytest: 36 passed, 4 skipped. Only failure is `test_frontend_contract.py` — waiting on frontend (FE-3.5) to add the TypeScript interfaces. That's the planned sync point. |

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
