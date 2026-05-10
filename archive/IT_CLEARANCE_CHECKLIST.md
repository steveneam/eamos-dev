# IT Clearance Go-Live Checklist
# Eamos Backend — Outbound Network Access

When IT grants outbound Python network access, complete these steps in order.
All changes are in E:\HSIL-2026\04_demo\app\backend\.env

---

## 1. Environment variables to flip

### Required on day one
| Variable | Current value | Change to |
|---|---|---|
| `USE_REAL_APIS` | `false` | `true` |
| `LLM_PROVIDER` | `mock` | `openai` (when OpenAI key is available) |
| `OPENAI_API_KEY` | _(blank)_ | Paste key from OpenAI dashboard |

### Required for Franklin (auth needed — do last)
| Variable | Current value | Change to |
|---|---|---|
| `FRANKLIN_API_TOKEN` | _(blank)_ | Token from Genoox portal |
| `FRANKLIN_EMAIL` | _(blank)_ | Account email registered with Genoox |
| `FRANKLIN_PASSWORD` | _(blank)_ | Account password registered with Genoox |

### Optional (LangChain tracing)
| Variable | Current value | Change to |
|---|---|---|
| `LANGCHAIN_API_KEY` | _(blank)_ | Key from smith.langchain.com |
| `LANGCHAIN_TRACING_V2` | `false` | `true` (only needed for debugging traces) |

Note: `USE_REAL_APIS=true` is the single gate for all external tool calls.
Flip it first. All other variables can be set in advance.

---

## 2. Domains to whitelist (Python outbound HTTPS/443)

The following hostnames must be reachable from the backend Python process:

| Domain | Used by | Auth required |
|---|---|---|
| `eutils.ncbi.nlm.nih.gov` | ClinVar, PubMed | None (free, rate-limited) |
| `rest.ensembl.org` | Ensembl VEP | None (free) |
| `spliceai-38-xwkwwwxdwq-uc.a.run.app` | SpliceAI | None (free, Broad Institute) |
| `gnomad.broadinstitute.org` | gnomAD | None (free, GraphQL API) |
| `clinicaltrials.gov` | ClinicalTrials.gov v2 | None (free) |
| `api.genoox.com` | Franklin API | Token required |
| `franklin.genoox.com` | Franklin URL construction | None (URL template only) |
| `api.openai.com` | GPT-4o-mini (LLM drafts) | API key required |
| `smith.langchain.com` | LangChain tracing | Key required (optional) |

---

## 3. Validation order

Test tools in this sequence. Each test uses a known variant:
  gene=RPE65, cdna=c.260A>G, transcript=NM_000329.2

### Step 1 — ClinVar (free, no key)
POST to /api/v1/lookup with USE_REAL_APIS=true.
Expected in response: `evidence[].source == "ClinVar"` with
`status == "ok"` and `summary.classification` containing
"Pathogenic" or "Likely pathogenic" for RPE65 c.260A>G.

### Step 2 — Ensembl VEP (free, no key)
Same request. Expected: `evidence[].source == "VEP"` with
`status == "ok"` and `summary.most_severe_consequence` present
(e.g. "missense_variant").

### Step 3 — SpliceAI (free, no key)
Expected: `evidence[].source == "SpliceAI"` with `status == "ok"`
and numeric splice scores (DS_AG, DS_AL, DS_DG, DS_DL) present in summary.
Confirm the endpoint accepts GENE:c.cdna format before going live.

### Step 4 — PubMed (free, no key)
Expected: `evidence[].source == "PubMed"` with `status == "ok"`
and `summary.articles` containing at least one article for RPE65.

### Step 5 — Franklin (auth required — do last)
Set FRANKLIN_EMAIL, FRANKLIN_PASSWORD, FRANKLIN_API_TOKEN.
Expected: `evidence[].source == "Franklin"` with `status == "ok"`.
Franklin requires an authenticated session; confirm token exchange
works before declaring success.

### Step 6 — LLM drafts
Set LLM_PROVIDER=openai and OPENAI_API_KEY.
Repeat the lookup request and confirm `report_payload.ai_clinical_summary`
contains a non-empty, non-mock string in clinical register (active voice,
no hedging openers per CLAUDE.md rules).

---

## 4. Degraded mode — if one tool fails

The backend already supports degraded responses. If a specific tool
fails after going live, it will return `status == "error"` or
`status == "fallback"` in its evidence entry. The report will still
render using data from working tools.

Action for each failure mode:
- **ClinVar fails**: Check NCBI rate limits (3 req/s without API key,
  10 req/s with NCBI_API_KEY). Add NCBI_API_KEY to .env if needed.
- **VEP fails**: Verify rest.ensembl.org is reachable. VEP is the most
  critical tool — without it, genomic coordinates and consequence
  annotation are missing.
- **SpliceAI fails**: Confirm the Broad endpoint is still live at the
  configured URL. This endpoint is not guaranteed permanently.
- **PubMed fails**: Non-critical for clinical use. Report renders without
  publications section.
- **Franklin fails**: Expected initially (auth required). Leave
  FRANKLIN_* blank until credentials are obtained from Genoox.
- **LLM fails**: Set LLM_PROVIDER=mock to revert to rule-based drafts.
  Report still renders; only AI narrative sections are blank.

---

## 5. Post-validation commit checklist

- [ ] USE_REAL_APIS=true confirmed working in .env
- [ ] All five tools return status == "ok" for RPE65 c.260A>G
- [ ] LLM draft text passes clinical register check (no hedging openers)
- [ ] .env is NOT committed to git (verify with git status)
- [ ] GITHUB_PAT rotated (see archive/pat_rotation_checklist.md)
- [ ] JWT_SECRET updated from dev placeholder to a strong random value
  before any multi-user or network-accessible deployment
