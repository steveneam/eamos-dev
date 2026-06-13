# AI Gateway — pgvector literature RAG (spec)

> **Status:** authored 2026-06-13 (Claude) · D1–D5 RESOLVED (see §3) · **BUILT 2026-06-13 (in-tree, UNCOMMITTED) — see §11. Inert until `rag_enabled` + `LLM_PROVIDER=gateway`; corpus not yet materialized; pre-prod ops still pending.**
> Phase 3 of Steven's session sequence (push/deploy → security gate → this). Follow-on
> roadmap item #1 in `docs/ai-gateway/plan.md` §1: "upgrade the same variant chat's
> grounding from report-payload-only to the literature corpus." Reuses the gateway
> foundation shipped in `ab14824`/`550641d` + the login gate shipped in `449151a`.
>
> This spec lays out the architecture + the decisions that need your sign-off (§3) and
> stops there. No migration, no embedding pipeline, no ChatService edits until approved —
> a pgvector migration is a durable Supabase schema change and Codex is concurrently
> active in the backend, so the contract is reviewed before any code lands.

## 0. Where this sits

Today the Ask-Eamos `/report` chat is grounded **only** in the report payload the FE
posts (`ChatService._build_bounded_context` → an evidence-only JSON of summary rows,
call cards, predictors, expert panel, publication *counts*, etc.). It can reason about
the structured evidence already on the page, but it cannot pull in the **actual
literature** — it sees that there are, say, 14 publications, not what any of them say.

RAG closes that gap: retrieve the most relevant published abstracts for the variant's
gene, inject them into the bounded context as a new evidence block, and let the model
ground its answer in real source text (still cite-bound, still verdict-deferring to the
deterministic ACMG call). This is the biggest UX lift in the roadmap and reuses the
broker, the guard, and the streaming path directly.

## 1. Goal / non-goals

**Goal.** When `LLM_PROVIDER=gateway`, the variant chat retrieves top-k literature
chunks scoped to the variant/gene from a vector store, adds them to the bounded context
under one new allowlisted key, and the model answers grounded in (and citing) them.

**Non-goals (this slice).**
- No `/runs` patient-report chat (separate PHI de-ID boundary — roadmap #3).
- No tool-calling / agentic retrieval loop (roadmap #4). Retrieval is a single
  deterministic pre-step, not a model-driven tool call.
- No new corpus ingestion: we embed the **existing** PubMed-local corpus
  (`services/pubmed_local.py`), not a new crawl.
- No change to the deterministic ACMG verdict authority. Literature explains; it never
  reclassifies.

## 2. Substrate this reuses (verified, 2026-06-13)

| Piece | Where | Reuse |
|---|---|---|
| Gateway broker | `services/ai_gateway/engine.py` | `stream_chat` for the answer. **Chat-only today** (`POST /chat/completions`); no `/embeddings` method yet — see D2. |
| Evidence-only guard | `services/ai_gateway/guard.py` | `ALLOWED_CONTEXT_KEYS` (9 keys) + fail-closed PHI/secret patterns. Retrieval adds **one** key here, deliberately — see §6. |
| Bounded-context builder | `services/chat_service.py::_build_bounded_context` | Single injection point: add `retrieved_literature` to the `context` dict before `assert_evidence_only`. |
| PubMed-local corpus | `services/pubmed_local.py` | Source text. **Abstracts are license-gated**: `abstract_policy_for_license` persists full text only for permissive licenses (CC-BY/CC0/public-domain/US-gov); otherwise `metadata_only_no_abstract`. So the embeddable unit = title + (license-permitted) abstract + keywords. |
| Embeddings hook | `agents/client.py::build_embeddings_model` | Exists, returns `OpenAIEmbeddings(model=settings.openai_embeddings_model)` — OpenAI-direct, **not** via the gateway. A reuse candidate for D2. |
| Supabase `vector` ext | Supabase project | **Available** (`vector` 0.8.0, ivfflat + hnsw), **not yet installed**. Enabling it is a one-line migration — see D1/§5. |
| Materialization pattern | `cli/eamos_pubmed_local_*` (Codex) | Embedding generation is an **offline CLI**, never a startup/deploy download (Render disk guardrail in RISKS.md). |

## 3. Key decisions — need your sign-off

> **RESOLVED 2026-06-13 22:24 +1000 (Steven, via Claude).**
> - **D1 → B — Local sqlite-vec** (Render disk, beside `pubmed_local`). Additive + local; no Supabase migration; minimal Codex overlap. §5 pgvector path is moot.
> - **D2 → A — Gateway embeddings** (`openai/text-embedding-3-small`, 1536-dim, via the broker). One provider + ZDR. Model fixed at materialization.
> - **D3 → confirmed** — hold the existing `pubmed_local` license policy; RAG does not widen the license surface.
> - **D4 → k=5**, gene-filtered, similarity floor, empty-block fallback (never errors).
> - **D5 → confirmed** — add exactly `retrieved_literature` to `ALLOWED_CONTEXT_KEYS`; sanitize snippets; global guard stays the backstop.
>
> Build (§8) is unblocked. Not started — awaiting Steven's "go" + Codex push coordination (nothing pushed yet).

**D1 — Vector store: Supabase pgvector vs local sqlite-vec.** *(the load-bearing one)*
- **A — Supabase pgvector** (the roadmap's named direction). `vector` ext is available;
  one `pgvector_embeddings` table + an hnsw index; retrieval is a SQL `<=>` query over
  the network. Managed, shared across instances, the obvious "real RAG" path.
- **B — Local sqlite-vec, co-located with the PubMed-local SQLite on the Render disk
  (Recommended).** Consistent with the established local-first asset strategy
  (dbSNP/phyloP/ClinGen/PubMed are all local-first on the Render disk; Supabase holds
  *app state*, not bulk genomic corpus). No per-chat network hop, no new Supabase
  coupling, embeddings live beside the text they index.
- **My recommendation: B**, because the corpus is already a local SQLite and the project
  deliberately keeps bulk reference data off Supabase. Choose **A** if you want the
  corpus managed/shared/queryable outside the backend, or if multi-instance scaling is
  imminent. (If A: it's a real migration + the SOLE-backend single-instance reality in
  RISKS.md still applies.)

**D2 — Embedding model / provider.**
- **A — Gateway embeddings** (extend the broker with a small `/embeddings` call, e.g.
  `openai/text-embedding-3-small`, 1536-dim). One key, one provider, ZDR, "reuses the
  broker" as the roadmap says. Tiny cost (~$0.00002/1k tokens), one-time at materialization.
- **B — Existing `OpenAIEmbeddings` hook** — reuses `build_embeddings_model` as-is, but
  it's OpenAI-direct (separate key, bypasses the gateway/ZDR posture).
- **C — Local model** (sentence-transformers, e.g. `all-MiniLM-L6-v2`, 384-dim) — zero
  API cost/keys, runs at materialization on the Render disk; weaker than the OpenAI
  family on biomedical text.
- **My recommendation: A** (gateway embeddings) for one-provider consistency + ZDR;
  fall back to **C** if you want zero external dependency for the corpus. Note: the
  embedding model is **fixed at materialization** — changing it means re-embedding.

**D3 — Corpus & licensing.** Embed title + permitted-abstract + keywords. For
`metadata_only_no_abstract` rows, embed title + keywords only (no body text leaves the
store). Confirm we only persist/retrieve abstract text where `pubmed_local`'s license
policy already permits — RAG must not widen the license surface.

**D4 — Retrieval scope & shape.** Variant chat is gene-scoped, so retrieve **filtered to
the variant's gene(s)** (`variant_summary_rows[].gene`), top-k (recommend k=5), with a
minimum similarity floor; return `{pmid, title, snippet, year, source_url, score}`. No
gene match → empty block (chat falls back to today's report-only grounding, never errors).

**D5 — Guard change.** Add `"retrieved_literature"` to `ALLOWED_CONTEXT_KEYS` and ensure
snippets are shaped so they cannot trip `_FORBIDDEN_SUBSTRINGS` / `_SECRET_PATTERNS`
(see §6). This is the only edit to the security boundary.

## 4. Architecture & data flow

```
OFFLINE (materialization CLI, no startup/deploy download):
  pubmed_local SQLite ──> for each license-permitted article:
      embed(title + abstract + keywords)  ──> vector store (D1)  [+ gene, pmid, year, license]

RUNTIME (per chat turn, only when LLM_PROVIDER=gateway):
  question ──embed──> vector store query (filter gene = variant gene, top-k, score>=floor)
                          └─> retrieved_literature[]  ──┐
  report payload ──> _build_bounded_context ────────────┤──> assert_evidence_only ──> broker.stream_chat
                                                         │
  (mock provider: retrieval is skipped — deterministic mock answer unchanged)
```

Retrieval lives in a new `services/ai_gateway/retrieval.py` (store-agnostic interface so
D1 A/B is swappable), called from `_build_bounded_context`. Embedding of the *question*
at runtime uses the same model chosen in D2.

## 5. pgvector schema + migration *(only if D1 = A; gated)*

```sql
-- supabase/migrations/00NN_literature_embeddings.sql  (NOT applied until approved)
create extension if not exists vector with schema extensions;

create table public.literature_embedding (
  pmid        text primary key,
  gene        text not null,
  title       text not null,
  snippet     text not null,           -- license-permitted; metadata-only rows omit body
  year        int,
  source_url  text,
  license     text not null,
  embedding   extensions.vector(1536)  -- dim per D2 (1536 for text-embedding-3-small)
);
create index on public.literature_embedding using hnsw (embedding extensions.vector_cosine_ops);
create index on public.literature_embedding (gene);
-- RLS: service-role-only (backend-owned); no anon/auth read. Corpus is server-side.
```

If D1 = B (local sqlite-vec), there is **no Supabase migration** — the embeddings live in
the local SQLite next to `pubmed_local`, materialized by the CLI, read by the backend.

## 6. Retrieval → bounded-context contract (the security boundary)

`retrieved_literature` is added to `context` in `_build_bounded_context` **before**
`assert_evidence_only`, so it passes through the existing fail-closed guard. Shape:

```json
"retrieved_literature": [
  {"pmid": "35901234", "title": "...", "snippet": "<=600 chars, prose",
   "year": 2022, "source_url": "https://pubmed.ncbi.nlm.nih.gov/35901234/", "score": 0.83}
]
```

Guard considerations (fail-closed is correct, but must not false-trip on real abstracts):
- Snippets are PubMed abstract prose — they will not contain `patient_id` /
  `patient_context` / `date_of_birth` / `"mrn"` verbatim. Low risk, but a malformed
  abstract could in principle trip the guard and drop the whole context. Mitigation:
  retrieval sanitizes snippets (strip control chars, cap length) and, defensively,
  drops any single snippet that contains a forbidden substring rather than failing the
  whole turn. The `sk-`/`Bearer`/`vck_` secret patterns are vanishingly unlikely in
  abstracts; keep the global guard as the backstop.
- The prompt instructs the model to cite retrieved PMIDs and to **defer the verdict** to
  the deterministic ACMG classification already in the context (verdict-deferral is
  already in `gateway_chat_prompt`).

## 7. Cost, guardrails, gates

- **Embedding cost** is one-time at materialization (corpus-size × model rate); runtime
  cost is one question-embedding per turn (negligible) + the existing chat completion.
- **Inherits the login gate** (`449151a`): retrieval only runs on the authenticated,
  per-user-rate-limited chat path. No new exposure surface.
- **Inherits the launch gates**: inert until `LLM_PROVIDER=gateway` (kept `mock`); FE chat
  stays coming-soon. Materialization is offline; never a deploy/startup download.
- **Provenance logging** extends the existing `{model, finalProvider, generationId, cost}`
  line with retrieved PMIDs + scores (no abstract text in logs).

## 8. Build phases (code-deferred until §3 sign-off)

1. **Store + interface** — `retrieval.py` store-agnostic interface; the D1-A or D1-B
   backing impl; config (`rag_enabled`, store path/conn, `rag_top_k`, `rag_min_score`,
   embedding model/dim).
2. **Embedding materialization CLI** — `cli/eamos_literature_embed_materialize.py`
   (+ preflight), reads `pubmed_local`, writes vectors; manifest/checksum like the other
   materialization CLIs.
3. **Runtime retrieval** — wire `retrieve(question, genes)` into `_build_bounded_context`;
   add the guard key; question-embedding via D2.
4. **Prompt + provenance** — extend `gateway_chat_prompt` to cite retrieved PMIDs; extend
   the log line.
5. **Tests** — retrieval unit tests (gene filter, top-k, floor, empty-fallback); guard
   test (key allowed, forbidden-substring snippet dropped not fatal); contract test
   (outbound payload still allowlist-clean); CLI test; mock-mode skip test.

## 9. Verification

- `cd app/backend && python -m pytest tests/ -q` green (incl. new retrieval/guard tests).
- Offline harness (`fake_gateway.py` + a fixture corpus) proves retrieval→prompt→stream
  end-to-end with **zero spend**, mirroring `chat_smoke.py`.
- `assert_evidence_only` contract test confirms `retrieved_literature` is the only new
  outbound key and PHI/secret patterns still fail closed.
- ruff + app/web tsc clean.

## 10. Open questions / coordination

- **D1–D5 above** — your call before any code.
- **Codex coordination**: the embedding CLI reads `pubmed_local` (Codex's lane) read-only;
  if D1 = A, the Supabase migration should be sequenced with Codex (backend-led contracts,
  no concurrent schema edits). If D1 = B, it's additive + local, minimal overlap.
- **Corpus readiness**: confirm the PubMed-local SQLite is materialized with the genes we
  care about before embedding (today it's gene-scoped/seeded, not a full PubMed mirror).

## 11. Build notes (2026-06-13, Claude — in-tree, UNCOMMITTED)

All five §8 phases landed; verified with `python -m pytest` (new + full backend suite)
and `ruff` clean. Files:

- **`services/ai_gateway/engine.py`** — added `embed(inputs, *, model)` (OpenAI-compatible
  `/embeddings`) and generalized `_send_with_retry(path=...)`. Chat path unchanged.
- **`services/ai_gateway/retrieval.py`** (new) — `Embedder`/`GatewayEmbedder` seam,
  `LiteratureEmbeddingStore` (local SQLite), `LiteratureRetriever`, `inspect_literature_store`,
  `materialize_literature_embeddings`, `build_literature_retriever`.
- **`services/ai_gateway/guard.py`** — `retrieved_literature` allowlisted (D5) + public
  `contains_forbidden_token` (single-sourced forbidden list for snippet dropping).
- **`services/chat_service.py`** — `_retrieved_literature` injects the gene-scoped block into
  `_build_bounded_context` before `assert_evidence_only`; pmid+score provenance log.
- **`agents/prompts.py`** — `gateway_chat_prompt` now cites retrieved PMIDs + keeps verdict-deferral.
- **`core/config.py`** — `rag_*` settings block. **`main.py`** — builds + injects the retriever.
- **CLIs** — `cli/eamos_literature_embed_materialize.py` (+ `_preflight.py`).
- **Tests** — `tests/test_literature_retrieval.py` (retrieval/store/materialize/CLI/preflight),
  plus embed + guard cases in `tests/test_ai_gateway.py` and RAG-wiring cases in
  `tests/test_chat_service.py`.

**Engineering deviation from the D1=B label (intentional):** `numpy` is Windows-excluded in
`requirements.txt` and `sqlite-vec` is not a dependency, so the local store keeps embeddings as
float32 BLOBs and scores them with **pure-Python brute-force cosine over the gene-filtered
candidate set** rather than an ANN index. The corpus is gene-scoped, so candidate sets per query
are tiny and an ANN index buys nothing; this honors D1=B (local, co-located SQLite, no Supabase,
no per-chat network hop) with zero new native/heavy dependency. The `Embedder`/store seams keep
it swappable if a future corpus ever outgrows brute force.

**Not done (deliberate):** corpus not yet materialized (needs the gateway key + credits, an
offline run of the materialize CLI); `rag_enabled` defaults `False` and `LLM_PROVIDER` stays
`mock`, so the slice is inert. `rag_min_score=0.2` is a pre-tune default — verify against live
embeddings during the pre-prod pass. `engine.py` is shared with Codex's broker; the embed method
is additive but sequence the commit with Codex.
