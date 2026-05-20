# Variant Literature Extraction Design

**Status:** Draft

**Summary**

The Variant Evidence Report should treat publication evidence as a first-class
variant-specific evidence module, not as a small PubMed decoration. The
recommended design is a backend-owned algorithm named **Eamos Proprietary
Variant Literature Extractor (EP-VLEx)**. EP-VLEx builds a deduplicated PMID
set from LitVar2, PubMed, ClinVar, and future local ClinGen evidence, enriches
the top articles from NCBI metadata, extracts variant-mention snippets from
PubMed/PubTator/PMC text, and exposes a recent-first paginated payload for the
frontend.

**Context And Scope**

Current state:

- `app/backend/app/tools/pubmed.py` fetches up to 10 PubMed records using
  ESearch, ESummary, and EFetch.
- `app/backend/app/tools/litvar2.py` resolves a LitVar2 variant ID and returns
  PMID count plus PMID stubs.
- `app/backend/app/services/lookup_service.py` merges PubMed and LitVar2 into
  `report_payload.pubmed_articles` and updates
  `publications_callout.total_count`.
- `app/frontend/src/components/report/PubMedSection.tsx` renders titles,
  bibliographic metadata, and PubMed links, but has no snippet display,
  recent-first contract, or expansion behavior.

User references:

- LitVar2 screenshot: default row shows PMID/PMCID, title, date, source
  section, and a highlighted variant snippet. The paper link should go to
  NCBI PubMed as the source of truth.
- `Gene Functional Literature Extraction.txt`: recommends a parallel
  aggregator over ClinGen, ClinVar, and PubMed streams with PMID dedupe.
- `Functional Card Display Logic & UI Layout Spec.txt`: asks for a dual
  qualitative/quantitative pattern for lab and functional literature.

Official NCBI sources checked:

- NCBI E-utilities supports PubMed ESearch, ESummary, EFetch, ELink, `retmax`,
  `retstart`, `sort`, and JSON/XML modes:
  https://www.ncbi.nlm.nih.gov/books/NBK25499/
- PubTator Central API exports PubMed abstracts by PMID and full text by PMCID
  in BioC JSON/XML:
  https://www.ncbi.nlm.nih.gov/CBBresearch/Lu/Demo/PubTatorCentral/api.html
- LitVar2 is designed for variant-specific literature retrieval across
  abstracts, full text, and supplementary data:
  https://www.nlm.nih.gov/news/NLM-LitVar-Genetic-Variants-Biomedical.html
- PMC developer APIs expose open-access full-text BioC and ID conversion:
  https://pmc.ncbi.nlm.nih.gov/tools/developers/

This design covers backend publication discovery, count accuracy, snippet
extraction, API shape, caching, and the frontend behavior contract. It does not
implement the visual redesign; Claude can render the UI from the backend
contract after approval.

**Goals**

- Display the correct variant-specific publication count, not a gene-only
  literature count.
- Show the five most recent variant-related publications by default.
- Allow the user to expand or page through the full publication set.
- Show snippets where the queried variant, rsID, cDNA alias, or protein alias
  was mentioned.
- Link every publication title and PMID to `https://pubmed.ncbi.nlm.nih.gov/{pmid}/`.
- Keep the design additive to the current Variant Evidence Report contract.
- Preserve fixture mode and deterministic tests.

**Non-Goals**

- Do not touch the Patient Report Pipeline (`/runs`).
- Do not re-enable, surface, or remove AlphaMissense.
- Do not infer final ACMG PS3/BS3 strength automatically from raw literature in
  the first slice.
- Do not scrape arbitrary publisher pages.
- Do not require a new database runtime before the source-backed payload is
  proven.

**Constraints**

- Backend owns schemas and source-truth behavior. Frontend mirror/render work
  needs coordination because `backend.ts` is a shared contract file.
- NCBI APIs are rate-limited in practice; lookup must bound live calls and use
  cache.
- Full text is only available when NCBI/PubTator/PMC can provide it. Abstract,
  title, table, and supplementary mentions must be labelled by source.
- `USE_REAL_APIS=false` remains the default and must return fixtures.
- Any new fields should be optional or additive so existing report rendering
  does not break.

**Proposed Design**

EP-VLEx is a service-level pipeline under backend ownership. It does not
replace `PubmedTool` or `LitVar2Tool`; it coordinates them and adds the missing
publication evidence layer.

```
Lookup variant
  |
  v
Variant synonym builder
  - gene, transcript HGVS, cDNA HGVS, protein HGVS
  - one-letter and three-letter protein aliases
  - rsID, genomic projection when available
  |
  v
Parallel PMID discovery
  - LitVar2 variant publications
  - PubMed targeted ESearch
  - ClinVar cited PMIDs
  - future local ClinGen PS3/BS3 evidence PMIDs
  |
  v
Master PMID set
  - dedupe by PMID
  - source breakdown
  - total_count
  |
  v
Metadata and snippet enrichment
  - ESummary for dates/title/journal/authors
  - EFetch XML for title and abstract text
  - PubTator BioC for variant/gene annotations
  - PMC BioC for open full text when PMCID exists
  |
  v
Variant Evidence Report payload
  - first 5 most recent articles
  - snippet list and matched terms
  - PubMed source links
  - pagination cursor for expansion endpoint
```

**Architecture Views**

**Runtime view**

`LookupService.lookup()` should call EP-VLEx after the resolver and ClinVar
steps have had a chance to enrich `variant.dbsnp_rsid`. EP-VLEx returns a
publication evidence object that hydrates:

- `ReportPayload.publications_literature` as the structured new module.
- `ReportPayload.pubmed_articles` as a backward-compatible top-five list.
- `PublicationsCallout.total_count` and blurb.

**Expansion view**

The initial `/api/v1/lookup` response should stay bounded. Full expansion should
use a paginated backend route:

`POST /api/v1/lookup/publications`

with the same variant identity plus `limit`, `offset`, and `sort`. This avoids
shipping hundreds of article rows inside the initial report payload while still
supporting "show full number of publications".

**Interfaces And Data**

Additive backend models:

- `PublicationSnippet`: section, text, matched terms, source, confidence.
- `PublicationSourceBreakdown`: counts from LitVar2, PubMed, ClinVar, ClinGen.
- `PublicationLiterature`: total count, shown count, sort, source breakdown,
  articles, variant terms, and warnings.
- Optional fields on `PubMedArticle`: `pmcid`, `publication_date`, `snippets`,
  `source_tags`, and `snippet_status`.

The source link invariant is strict: article URLs are always PubMed URLs, even
when LitVar2, PubTator, or PMC provided the match/snippet.

**Alternatives Considered**

- LitVar2 only: best variant specificity and count, but not enough metadata or
  snippet control for Eamos UI, and it does not cover future ClinGen/ClinVar
  functional evidence streams.
- PubMed only: easy metadata and dates, but can undercount variant-specific
  literature and misses LitVar2 disambiguation.
- Gene-only PubMed count: high volume but clinically noisy and not acceptable
  for a variant evidence report.
- Initial payload contains every article: simple UI but poor latency, high API
  usage, and unnecessary payload size for variants with large literature sets.

**Tradeoffs**

The design adds backend complexity, but the complexity is concentrated in one
named algorithm with deterministic fixtures and tests. The initial report stays
fast by returning top five articles, while expansion uses a dedicated endpoint.
Snippet quality is best when PubTator or PMC full text is available; when only
PubMed metadata exists, the snippet falls back to title/abstract or a labelled
no-text status.

**Cross-Cutting Concerns**

- Privacy: only variant query terms are sent to public NCBI APIs. No patient
  context is included.
- Reliability: every live branch must degrade to fixture/cache with warnings.
- Observability: record source counts, warning codes, and which text source
  supplied each snippet.
- Cost: no paid services or LLM calls are required.
- Rate limits: keep bounded `retmax`, batch ESummary/EFetch by PMID, cache
  results under the existing variant cache path.
- Clinical safety: raw literature snippets are evidence navigation, not final
  ACMG assignment.

**Rollout And Migration**

1. Add fixtures and backend schema fields behind existing fixture/live mode.
2. Implement EP-VLEx with deterministic tests against fixtures.
3. Wire `/lookup` to return top-five recent enriched publications.
4. Add the paginated `/lookup/publications` expansion route.
5. File a cross-agent frontend request for Claude to render the redesigned
   Publication/Literature section from the new payload.
6. Run live smoke against an RPE65 variant with known LitVar2 results, then run
   the full backend suite and contract canary.

**Open Questions**

- Should the initial visible list be exactly five, or should mobile show fewer
  rows with the same backend limit?
- Should functional assay tags be displayed in the same section now, or kept as
  a second Card 3 follow-up after publication snippets land?
- Does the user want "expand all" to load all rows at once for small counts, or
  always page in batches for consistent behavior?

**Decision**

Proceed with EP-VLEx as an additive backend design. It gives the Variant
Evidence Report a source-backed publication count, recent-first top-five list,
PubMed links, and LitVar2-style snippets without touching `/runs`, AlphaMissense,
or Claude-owned visual redesign files.
