# Eamos AI Gateway Evidence-Grounded Chat & Extraction

Status: Active backend prototype (inert until `LLM_PROVIDER=gateway`)
Type: AI orchestration layer — broker + evidence-only guard + literature RAG + structured extraction
Owner: Claude (one-off FE+BE exception for the AI-gateway build)
Added: 2026-06-13 23:16 +1000 - Claude
Last updated: 2026-06-13 23:16 +1000 - Claude

## What It Does

Routes Eamos's variant chat and structured-extraction features through the Vercel
AI Gateway (OpenAI-compatible, Groq primary → Amazon Bedrock failover) behind an
Eamos-original guardrail spine. Four cooperating pieces:

1. **Broker** (`ai_gateway/engine.py`) — thin OpenAI-compatible httpx transport:
   `complete()`, true-token `stream_chat()`, and `embed()`, with provider-order
   failover, 429/5xx backoff, and best-effort routing/cost metadata capture.
2. **Evidence-only outbound guard** (`ai_gateway/guard.py`) — fail-closed allowlist
   assertion on the serialized chat context: only the known evidence keys may leave
   the server, and PHI-/secret-shaped tokens are refused. This is the de-ID-lite
   boundary for the variant-centric `/report` surface (not full name/DOB/MRN
   stripping, which belongs to the patient-report flow).
3. **Literature RAG** (`ai_gateway/retrieval.py` + `eamos_literature_embed_*` CLIs) —
   a **local-first, license-aware, gene-scoped** vector store: the offline CLI reads
   the PubMed-local corpus, embeds license-permitted abstracts (title + permitted
   body + keywords) via the gateway, and writes a SQLite asset on the Render disk;
   at chat time the question is embedded, filtered to the variant's gene(s), scored
   by brute-force cosine over that small candidate set, sanitized, and injected as a
   `retrieved_literature` block. Empty-fallback (never errors); inert unless
   `rag_enabled`.
4. **Structured extraction substrate** (`ai_gateway/structured.py`) — `extract_structured`:
   prompt for one JSON object, parse + Pydantic-validate, and on failure send one
   bounded "repair" turn quoting the error. Reusable by every structured gateway
   feature. Consumers:
   - **messy-text→JSON** search-input path (`build_gateway_search_input_chain`, see
     [Search Input AI Extractor](./search-input-ai.md)).
   - **paper→variants** (`services/paper_variants.py`, `schemas/paper_variants.py`,
     `cli/eamos_paper_variants.py`): extract variant mentions from publication text,
     then **gate each candidate through `VariantValidatorTool`** — a candidate is only
     surfaced as `validated` when VariantValidator resolves it to a GRCh38 coordinate,
     so hallucinated/malformed variants are dropped. Mock-first regex extractor offline.

## Why It Is Eamos-Original

The broker is a generic transport; the original part is the **guardrail orchestration**:

- **Verdict-deferral** — the system prompt makes Eamos's deterministic ACMG
  classification authoritative; the model explains evidence but may never assert a
  differing tier (`gateway_chat_prompt`).
- **Evidence-only allowlist** — outbound context is asserted against the exact key set
  the bounded-context builder emits; one new key (`retrieved_literature`) was added
  deliberately, with snippet sanitization + single-sourced forbidden-token dropping.
- **Local-first, license-aware RAG** — embeddings live beside the corpus on the Render
  disk (no Supabase coupling, no per-chat network hop), the license policy is held
  exactly (metadata-only rows carry no body text), retrieval is gene-scoped, and
  materialization is an explicit offline action (never a startup/deploy download).
- **Validate-and-repair** — schema enforcement is done in-house because the gateway is
  OpenAI-compatible REST without provider-side structured output.

## Source Of Truth

- Broker / guard / RAG / structured: `app/backend/app/services/ai_gateway/{engine,guard,retrieval,structured}.py`
- Chat service wiring: `app/backend/app/services/chat_service.py`
- Adapters + prompts: `app/backend/app/agents/client.py`, `app/backend/app/agents/prompts.py`
- CLIs: `app/backend/app/cli/{eamos_literature_embed_materialize,eamos_literature_embed_preflight,chat_smoke}.py`
- Offline gateway double: `app/backend/scripts/fake_gateway.py`
- Config: `app/backend/app/core/config.py` (`ai_gateway_*`, `rag_*`)
- API: `POST /api/v1/chat`, `POST /api/v1/chat/stream`
- Tests: `app/backend/tests/{test_ai_gateway,test_ai_gateway_structured,test_literature_retrieval,test_chat_service}.py`
- Plans/specs: `docs/ai-gateway/plan.md`, `docs/ai-gateway-rag/spec.md`, `docs/ai-gateway/local-testing.md`

## Relationship To Other Entries

- Complements **[EP-VLEx](./ep-vlex.md)** (variant-literature *extraction*): RAG adds
  semantic *retrieval/grounding* over the same PubMed-local corpus; it does not replace
  EP-VLEx's variant-linked literature evidence.
- Provides the gateway provider path consumed by
  **[Search Input AI Extractor](./search-input-ai.md)** (messy-text→JSON).

## Caveats

- **Inert by default**: requires `LLM_PROVIDER=gateway` + `AI_GATEWAY_API_KEY`; RAG also
  requires `rag_enabled` + a materialized store. Prod stays `mock` until the pre-prod
  enable pass (re-mint key off-transcript + paid credits + materialize corpus).
- RAG uses brute-force cosine over the gene-filtered candidate set (no ANN index) —
  appropriate because the corpus is gene-scoped; the store/embedder seams keep it
  swappable if a future corpus outgrows it.
- `rag_min_score` is a pre-tune default; verify against live embeddings at enable time.
- ZDR is a gateway team-level setting, not a per-request flag.
