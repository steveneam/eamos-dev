# Search Bar AI Input Spec

Status: Draft for user review
Owner: Codex
Last updated: 2026-05-21 18:31 +1000

## What

Build the Variant Evidence Report search bar around one raw input field that
accepts exact variant syntax and plain-language variant descriptions. The
backend Eamos Search Input Resolver remains the source of truth for parsing,
normalization, source-specific identifiers, and evidence lookup inputs. AI is
an optional extraction fallback for plain language; it proposes structured
candidate intent, then deterministic validation and source-backed candidate
resolution decide whether the report can run, auto-select one variant, or show
ranked choices.

## Context

The current web lookup contract requires structured fields:
`LookupRequest.gene`, `cdna`, optional `transcript`, optional
`protein_change`, and `species`.

Relevant current code:

- `app/backend/app/schemas/lookup.py` defines `LookupRequest`,
  `LookupResponse`, and publication paging requests.
- `app/backend/app/api/routes/lookup.py` exposes `POST /api/v1/lookup` and
  `POST /api/v1/lookup/publications`.
- `app/backend/app/services/lookup_service.py` owns report generation and
  already calls `EamosSearchInputResolver`.
- `app/backend/app/services/search_input_resolver.py` now exposes
  `parse_search_text()` and `EamosSearchInputResolver.resolve_text()`.
- `app/backend/app/cli/eamos_search_input.py` proves the resolver can parse a
  single search-box string and emit source-specific bundles.
- `app/backend/app/agents/client.py` has existing mock/OpenAI provider patterns
  and structured-output usage for other LLM flows.

The gap is the production web contract: the frontend search bar still needs to
send structured fields or duplicate parsing. Because the search bar is the
main product surface, the contract should let the frontend send exactly what
the user typed and let the backend return a transparent interpretation.

## Requirements

1. `POST /api/v1/lookup` must remain backward compatible with the existing
   structured request shape.
2. `POST /api/v1/lookup` must also accept a raw search string through a
   canonical `search_text` field.
3. `query` may be accepted as an alias for `search_text`, but backend and
   frontend documentation should use `search_text` to avoid ambiguity with the
   existing response `query` field and the separate search API.
4. The frontend must not split gene/cDNA/transcript itself. It sends raw text
   or structured legacy fields; the backend parses.
5. Add a parse-preview endpoint, `POST /api/v1/lookup/parse`, that returns the
   backend interpretation without running the full evidence stack.
6. Deterministic parsing must run first for HGVS, transcript HGVS,
   gene-prefixed cDNA, rsID, RefSeq genomic HGVS, and gnomAD/VCF-style genomic
   IDs.
7. AI extraction must only run when deterministic parsing is unknown,
   gene-missing, or plain-language-like input is detected.
8. AI extraction must return structured fields, confidence, assumptions, and
   warnings. It must not directly create final report evidence or source
   calls.
9. The deterministic resolver must validate AI-proposed fields before lookup.
10. Protein-level or codon-level descriptions must be expanded into candidate
    nucleotide/cDNA positions where transcript context allows. For codon `n`,
    the codon anchor is coding DNA positions `3n-2`, `3n-1`, and `3n`; frameshift
    candidates may include indels/duplications/delins at or near that anchor.
11. Source-backed candidate resolution must check reported variants before
    asking the user. If exactly one reported candidate matches the interpreted
    intent, the system should auto-select it and continue.
12. If two or more plausible reported candidates match the interpreted intent,
    the system should present ranked options and let the user choose.
13. If the user input is slightly off, such as a nearby cDNA position or allele
    that does not match a reported source record, the system should return
    closest source-backed recommendations rather than a dead-end message.
14. The search bar must not show user-facing copy equivalent to "we cannot find
    the variant" or "we do not understand the input." Internally the backend can
    use structured statuses, but the UI output should be recommendations,
    interpretation choices, or focused next actions.
15. Exact deterministic inputs should not require a visible "AI mode" toggle.
16. The UI should expose the interpretation cleanly: for example,
    "Interpreted as CFTR p.Leu441fs" plus either one auto-selected source-backed
    match or ranked choices.
17. The system must preserve the original submitted text, normalized fields,
    parser mode, source-input readiness, warnings, and assumptions for audit.
18. Patient Report Pipeline (`/runs`) and AlphaMissense remain out of scope.

## Design

### Product Behavior

Use one seamless search bar. Do not put a primary "AI mode" toggle in front of
the user.

The backend classifies each submission into one of these modes:

- `structured`: existing `gene` plus `cdna` request.
- `deterministic`: raw search text parsed without AI.
- `ai_assisted`: AI extracted candidate fields and deterministic validation
  accepted them.
- `auto_resolved`: source-backed candidate resolution found exactly one
  reported variant for a protein/codon-level or slightly-off input.
- `needs_selection`: multiple plausible source-backed candidates exist; the
  user should choose one.
- `suggestions`: the exact input did not match a reportable variant, but the
  backend has ranked nearby or related recommendations.

Examples:

- `RPE65:c.260A>G` -> deterministic lookup.
- `NM_000329.3(RPE65):c.1301C>T (p.Ala434Val)` -> deterministic lookup.
- `1-68449890-C-T` -> deterministic genomic lookup.
- `a frameshift beginning at Leucine 441, in the cystic fibrosis gene` ->
  AI-assisted extraction can propose `CFTR` and `p.Leu441fs`. The backend then
  expands the codon anchor and checks reported variants. If one reported
  candidate matches, it auto-selects that candidate. If several match, it
  returns ranked options.
- `RPE65:c.259A>G` when no exact source record exists -> suggestions such as
  nearby reported `RPE65` variants in the same transcript/codon window, ranked
  by source support, distance, and consequence similarity. Do not show a
  dead-end "not found" state.
- `the Stargardt gene variant` -> suggestions or selection choices based on
  disease/gene hints when available, otherwise a focused prompt asking for the
  gene or variant form.

### Backend Request Contract

Change `LookupRequest` additively while preserving legacy clients:

```python
class LookupRequest(BaseModel):
    search_text: str | None = Field(default=None, min_length=1, max_length=512)
    query: str | None = Field(default=None, min_length=1, max_length=512)
    gene: str | None = Field(default=None, min_length=1, max_length=64)
    cdna: str | None = Field(default=None, min_length=1, max_length=256)
    transcript: str | None = Field(default=None, max_length=64)
    protein_change: str | None = Field(default=None, max_length=128)
    species: Literal["human", "mouse"] = "human"
    confirmed_interpretation: bool = False
    selected_candidate_id: str | None = Field(default=None, max_length=128)
```

Validation rules:

- Accept existing structured requests with `gene` and `cdna`.
- Accept raw requests with `search_text` or `query`.
- Reject payloads that provide both raw input and structured input unless the
  implementation explicitly proves they normalize to the same interpretation.
  The first slice should reject mixed input for clarity.
- Reject blank raw input.
- If raw lookup finds multiple candidates, return a structured selection
  response rather than running a report against a guess. A later request with
  `selected_candidate_id` can run the chosen candidate.
- Legacy structured unknown input may keep the current 200-with-warning
  behavior for backward compatibility, but new raw search UX should present
  recommendations instead of a dead-end.

### Parse Preview Contract

Add:

`POST /api/v1/lookup/parse`

Request:

```python
class SearchInputParseRequest(BaseModel):
    search_text: str = Field(min_length=1, max_length=512)
    species: Literal["human", "mouse"] = "human"
    allow_ai: bool = True
    resolve_coordinates: bool = False
```

Response:

```python
class SearchInputSourceInputs(BaseModel):
    variant_validator: str | None = None
    ensembl_vep: str | None = None
    gnomad: str | None = None
    spliceai: str | None = None
    clinvar: str | None = None
    literature_terms: list[str] = Field(default_factory=list)


class SearchInputCandidate(BaseModel):
    candidate_id: str
    display_label: str
    gene: str
    cdna: str | None = None
    transcript: str | None = None
    protein_change: str | None = None
    genomic_hg38: str | None = None
    genomic_hgvs: str | None = None
    match_reason: str
    source_support: list[str] = Field(default_factory=list)
    source_count: int = 0
    distance: str | None = None
    confidence: Literal["high", "medium", "low"] = "medium"
    warnings: list[str] = Field(default_factory=list)


class SearchInputInterpretation(BaseModel):
    submitted_text: str
    mode: Literal[
        "structured",
        "deterministic",
        "ai_assisted",
        "auto_resolved",
        "needs_selection",
        "suggestions",
    ]
    confidence: Literal["high", "medium", "low"]
    gene: str | None = None
    cdna: str | None = None
    transcript: str | None = None
    protein_change: str | None = None
    normalized_query: str | None = None
    query_kind: str | None = None
    genomic_hg38: str | None = None
    genomic_hgvs: str | None = None
    source_inputs: SearchInputSourceInputs | None = None
    requires_confirmation: bool = False
    exact_variant_available: bool = True
    auto_selected_candidate_id: str | None = None
    candidates: list[SearchInputCandidate] = Field(default_factory=list)
    ui_prompt: str | None = None
    assumptions: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    provenance: list[str] = Field(default_factory=list)


class SearchInputParseResponse(BaseModel):
    interpretation: SearchInputInterpretation
```

`LookupResponse` should add the same optional interpretation:

```python
class LookupResponse(BaseModel):
    query: str
    species: str
    report_payload: ReportPayload
    evidence: list[EvidenceSourceSummary]
    warnings: list[str]
    search_interpretation: SearchInputInterpretation | None = None
```

### Service Flow

Introduce a small orchestrator, for example
`app/backend/app/services/search_input_interpreter.py`.

Flow:

1. Strip and bound input.
2. Try `parse_search_text()` and `EamosSearchInputResolver.resolve_text()`.
3. If deterministic result has a known kind and sufficient fields, return a
   high-confidence interpretation.
4. If the parsed result is protein/codon-level, no-hit, or near-miss, run
   candidate resolution against source-backed records before asking the user.
5. If deterministic result is incomplete or unknown and AI is enabled, call
   the AI extractor.
6. Validate AI candidate fields by passing them back through
   `EamosSearchInputResolver`.
7. Apply candidate gating:
   - exact HGVS/genomic/rsID accepted: `requires_confirmation=false`.
   - one source-backed candidate for a protein/codon/no-hit input:
     `mode=auto_resolved`, `auto_selected_candidate_id=<id>`, then proceed.
   - multiple source-backed candidates: `mode=needs_selection` with ranked
     candidates.
   - no precise source-backed candidate: `mode=suggestions` with nearest
     options or a focused prompt for the missing piece.
8. `LookupService.lookup()` uses the interpretation to build the existing
   structured lookup path and then returns the interpretation in the response.

### Candidate Resolution

Add a source-backed candidate resolver, for example
`app/backend/app/services/search_candidate_resolver.py`.

The candidate resolver handles two high-value cases:

1. **Protein/codon-level intent.** For `GENE p.Leu441fs` or "frameshift
   beginning at Leucine 441", resolve the transcript, compute the codon anchor
   positions, generate candidate lookup terms around that anchor, and query
   reported source records. For codon `n`, the basic coding DNA positions are
   `3n-2`, `3n-1`, and `3n`; frameshift alleles may be indels/duplications/
   delins at or near those positions, so the resolver should search source
   records by gene + protein/codon consequence rather than inventing one exact
   allele.
2. **Near-miss exact input.** For a cDNA/genomic input with no exact source
   support, search nearby same-gene/same-transcript reported variants and rank
   likely intended matches. A one-base coordinate shift, allele typo, or nearby
   codon miss should return candidate recommendations.

Candidate source priority for the first implementation:

- ClinVar exact/nearby reported records using the existing ClinVar tool or a
  small candidate-search method.
- Existing variant cache and fixture records when available.
- VariantValidator/VEP normalization where useful for transcript/genomic
  consistency.
- Future MyVariant/local variant index once implemented.

Ranking signals:

- exact gene/transcript match;
- exact protein position/consequence match;
- exact cDNA match;
- cDNA coordinate distance;
- same codon before nearby codon;
- ClinVar/VCV reported record support;
- additional source support from gnomAD, literature, or cache;
- lower warning count.

Auto-selection rule: if there is exactly one high-confidence source-backed
candidate after ranking and deduplication, proceed with it. If there are two or
more high/medium-confidence candidates, return them for user selection.

### AI Extraction

Add a mock-first AI extractor service only after the deterministic web contract
lands.

Recommended model-facing structured output:

```python
class SearchInputAiExtraction(BaseModel):
    gene: str | None = None
    gene_alias: str | None = None
    cdna: str | None = None
    transcript: str | None = None
    protein_change: str | None = None
    genomic_hint: str | None = None
    variant_class: Literal[
        "snv",
        "missense",
        "nonsense",
        "frameshift",
        "splice",
        "deletion",
        "insertion",
        "duplication",
        "delins",
        "unknown",
    ] = "unknown"
    disease_context: str | None = None
    confidence: Literal["high", "medium", "low"] = "low"
    assumptions: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
```

Prompt rules:

- Extract only what is present or strongly implied.
- Do not invent cDNA or genomic coordinates from a protein-only description.
- It may derive codon anchors and candidate search windows from protein-level
  text, but final cDNA/genomic auto-selection requires source-backed support.
- Prefer gene symbols over disease names.
- If a disease name maps to more than one plausible gene, return low
  confidence and a warning.
- Return protein-level HGVS when the user provides amino-acid position and
  consequence.
- Mark uncertain or incomplete inputs rather than forcing a report.

Mock mode should not call a live model. It can return deterministic fixture
outputs for tests such as the CFTR Leu441 frameshift example, or it can return
no extraction and force clarification. Tests should not require network.

### RAG Recommendation

Do not add vector RAG in the first implementation slice.

Use "RAG-lite" curated reference data first:

- approved gene aliases and disease-to-gene hints;
- canonical/MANE transcript hints already present in resolver maps or source
  lookups;
- accepted HGVS examples and Eamos parser examples;
- common plain-language consequence terms such as frameshift, splice donor,
  deletion, duplication, and nonsense.

If vector retrieval is added later, it should retrieve only curated Eamos
reference material and source dictionaries for the extraction prompt. It must
not retrieve arbitrary literature to decide the submitted variant identity.

### Frontend Handoff

Frontend implementation is Claude-owned unless explicitly redirected.

Recommended search-bar behavior:

- One input field.
- No primary AI toggle.
- Show interpretation chips after parse:
  `Gene CFTR`, `Protein p.Leu441fs`, `1 reported match selected` or
  `3 possible matches`.
- If high confidence, allow immediate report generation.
- If medium confidence and there is one source-backed candidate, allow report
  generation with visible interpretation.
- If multiple candidates exist, show a compact picker and make the user choose.
- If no exact candidate exists, show closest recommendations and focused next
  actions, not a failure message.
- Show accepted examples in help text or a compact popover, not as a large
  instructional panel.
- Keep an advanced details drawer with source-input readiness for debugging:
  VariantValidator/VEP, gnomAD, SpliceAI, ClinVar, literature.

## Decisions

- Decision: The backend resolver is authoritative.
  - Alternatives: frontend parsing or LLM-only parsing.
  - Reason: source identifiers and HGVS normalization need auditability and
    tests.
  - Reversible: no, this is a core safety invariant.

- Decision: Use seamless AI fallback, not a primary AI toggle.
  - Alternatives: explicit AI mode toggle, two separate search boxes.
  - Reason: the product is the search bar; users should not choose parser
    internals. The backend can still reveal when AI was used.
  - Reversible: yes; a toggle can be added later as an advanced option.

- Decision: Canonical field name is `search_text`; accept `query` only as an
  alias.
  - Alternatives: use only `query`.
  - Reason: `query` already appears in response/search contexts; `search_text`
    is clearer for the web search bar.
  - Reversible: yes.

- Decision: Add parse-preview before full AI integration.
  - Alternatives: wire AI and lookup in one slice.
  - Reason: deterministic preview gives immediate frontend value and lowers
    blast radius.
  - Reversible: yes, but the endpoint remains useful.

- Decision: Auto-select one source-backed candidate from protein/codon or
  near-miss input.
  - Alternatives: always ask the user to specify the exact cDNA/genomic allele.
  - Reason: the search bar is the product; when sources identify one plausible
    reported variant, forcing the user to do the mapping wastes effort.
  - Reversible: yes; confidence thresholds can be tightened.

- Decision: RAG is not first-slice scope.
  - Alternatives: build vector retrieval immediately.
  - Reason: the highest-value data is structured aliases and resolver facts,
    not semantic document search.
  - Reversible: yes.

## Invariants

- Exact HGVS/genomic input must not be changed by AI.
- AI must never invent final cDNA or genomic coordinates from protein-only
  text. It may produce candidate intent that source-backed resolution checks.
- One auto-selected candidate must have source support and pass deterministic
  normalization.
- Multiple plausible source-backed candidates must be shown for selection
  rather than silently picking one.
- Full source lookup must use deterministic source-specific bundles.
- gnomAD and SpliceAI remain genomic-coordinate driven.
- ClinVar should prefer resolved NC genomic HGVS when available.
- EP-VLEx receives a term bundle, not one brittle identifier.
- Existing structured lookup clients continue to work.
- Patient Report Pipeline (`/runs`) remains untouched.
- AlphaMissense remains on hold.

## Error Behavior

- Blank raw search text: HTTP 422.
- Raw text plus structured fields: HTTP 422 in the first slice.
- Deterministic unknown input on parse endpoint: HTTP 200 with
  `mode=suggestions`, `confidence=low`, candidate recommendations when
  available, and a focused next-action prompt.
- Raw lookup input with multiple candidates: return a structured selection
  response carrying `mode=needs_selection` and candidates. Do not run the full
  Variant Evidence Report against an arbitrary guess.
- Protein/codon-level lookup without an exact allele: run candidate resolution.
  Auto-select exactly one source-backed high-confidence match; otherwise return
  ranked choices or suggestions.
- No exact source record: return closest source-backed recommendations or
  examples of accepted formats. Avoid user-facing "not found" / "cannot
  understand" copy.
- AI service unavailable: return deterministic interpretation, candidate
  suggestions, or focused next actions; do not fail exact deterministic inputs.
- Live coordinate resolution failure: preserve parser output and warnings; do
  not attach unrelated fixture coordinates.

## Testing Strategy

- Unit tests for `LookupRequest` validation: legacy structured, raw
  `search_text`, alias `query`, mixed-mode rejection, blank rejection.
- Unit tests for parse-preview deterministic inputs:
  `RPE65:c.260A>G`,
  `NM_000329.3(RPE65):c.1301C>T (p.Ala434Val)`,
  `1-68449890-C-T`,
  `8:140300616 T>G`,
  simple insertion/deletion gnomAD-style IDs.
- Route tests for `POST /api/v1/lookup` with raw exact inputs returning the
  same normalized report result as legacy structured input.
- Route tests for `POST /api/v1/lookup/parse` returning source-input bundles
  without running full evidence tools.
- Mock AI extractor tests for:
  `a frameshift beginning at Leucine 441, in the cystic fibrosis gene` ->
  candidate `CFTR`, `p.Leu441fs`, followed by auto-selection when the candidate
  resolver has one source-backed match and `needs_selection` when it has
  multiple matches.
- Candidate resolver tests for nearby cDNA no-hit input returning ranked
  alternatives instead of a dead-end state.
- Ambiguity tests for disease-only or multi-gene plain language returning
  choices or focused next actions.
- Contract canary updates for new schemas and pending frontend mirror fields.
- Focused backend verification:

```bash
cd app/backend
python -m ruff check app tests
python -m black --check --target-version py310 app tests
python -m pytest tests/test_lookup_normalize.py tests/test_search_input_resolver.py tests/test_variant_search_integration.py tests/test_frontend_contract.py -q
```

## Out Of Scope

- Frontend implementation and browser verification.
- Patient Report Pipeline (`/runs`).
- AlphaMissense re-enable.
- Vector RAG infrastructure.
- New external source providers.
- Final clinical classification from plain-language input.
- Guessing a final cDNA/genomic allele from a protein-only description without
  source support.
