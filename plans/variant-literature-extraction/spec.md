# Variant Literature Extraction Spec

**What**

Build **Eamos Proprietary Variant Literature Extractor (EP-VLEx)**, a backend
publication-evidence pipeline for the Variant Evidence Report. It must compute a
variant-specific deduplicated publication count, return the five most recent
publications by default, expose a paginated expansion route for the full set,
and attach snippets showing where the queried variant was mentioned. All article
links point to NCBI PubMed.

**Context**

Today the backend already has `PubmedTool`, `LitVar2Tool`,
`PublicationsCallout`, and `PubMedArticle`. `lookup_service.py` merges LitVar2
PMID stubs into PubMed articles and uses LitVar2 count when available. The
current frontend section renders a flat article list and PubMed links, but it
does not sort recent-first, display mention snippets, or expand from a bounded
top set.

Relevant files:

- `app/backend/app/tools/pubmed.py`
- `app/backend/app/tools/litvar2.py`
- `app/backend/app/services/lookup_service.py`
- `app/backend/app/schemas/run.py`
- `app/backend/app/fixtures/tools/pubmed_fixtures.json`
- `app/backend/app/fixtures/tools/litvar2_fixtures.json`
- `app/backend/tests/test_variant_search_integration.py`
- `app/backend/tests/test_frontend_contract.py`
- `app/frontend/src/components/report/PubMedSection.tsx` (read-only context for
  Codex unless user approves frontend work)

Reference behavior:

- LitVar2 screenshot shows "Showing 1 to 3 of 3 publications", recent sorting,
  section labels such as title/table/supplement, highlighted variant mentions,
  and PMID/PMCID identifiers.
- Local functional literature docs require a parallel PMID aggregator and a
  deduplicated count rather than a stop-at-first-source fallback.

Official API basis:

- NCBI E-utilities: ESearch/ESummary/EFetch for PMID discovery and metadata.
  https://www.ncbi.nlm.nih.gov/books/NBK25499/
- PubTator Central: BioC JSON/XML export for PMID abstracts and PMCID full text.
  https://www.ncbi.nlm.nih.gov/CBBresearch/Lu/Demo/PubTatorCentral/api.html
- PMC developer APIs: open-access full-text BioC and ID conversion when needed.
  https://pmc.ncbi.nlm.nih.gov/tools/developers/

**Requirements**

- EP-VLEx must build a query synonym set containing gene, cDNA HGVS, transcript
  HGVS, protein HGVS, one-letter protein alias, three-letter protein alias,
  rsID when known, and genomic projection when known.
- EP-VLEx must query publication sources in parallel where practical:
  LitVar2, PubMed, ClinVar cited PMIDs, and future local ClinGen PS3/BS3 PMIDs.
- The authoritative total count must be the deduplicated PMID set size. If
  LitVar2 returns a total count but not every PMID, the response must label that
  source limitation and use the deduped PMID count for loaded rows.
- The initial `/api/v1/lookup` payload must return at most five enriched
  publication rows, sorted by publication date descending.
- The full publication set must be accessible through a paginated endpoint with
  bounded `limit` and `offset`.
- Every publication row must include `url =
  https://pubmed.ncbi.nlm.nih.gov/{pmid}/`.
- Every publication row should include at least one snippet when title,
  abstract, PubTator, or PMC text contains a variant synonym.
- When the variant is found only in a table or supplementary material and no
  text snippet is available, the row must expose a labelled status such as
  `reported_in_table_no_text` or `reported_in_supplement_no_text`.
- Snippet text must be extracted from NCBI-provided text sources only. Do not
  scrape publisher pages.
- Fixture mode must return deterministic enriched article rows.
- Live failures must degrade with warning codes and must not make the lookup
  fail when other evidence is available.
- The Patient Report Pipeline (`/runs`) and AlphaMissense remain out of scope.

**Design**

**Backend components**

Add a service module:

`app/backend/app/services/publication_literature.py`

Primary class:

`EamosProprietaryVariantLiteratureExtractor`

Primary public methods:

- `build_for_lookup(variant, evidence_map, limit=5) -> PublicationLiterature`
- `page_publications(request: PublicationPageRequest) -> PublicationLiterature`

Internal EP-VLEx stages:

1. `VariantLiteratureTerms.build(variant)`: produces normalized search terms
   and display aliases.
2. `PublicationPmidAggregator.collect(...)`: collects PMIDs from LitVar2,
   targeted PubMed ESearch, ClinVar citations, and future ClinGen local tables.
3. `PublicationMetadataClient.fetch(pmids)`: batches ESummary/EFetch and
   normalizes title, authors, journal, year, publication date, DOI, PMCID, and
   PubMed URL.
4. `VariantMentionSnippetter.extract(article_text, terms)`: ranks title,
   abstract, PubTator BioC passages, and PMC BioC passages for best snippets.
5. `PublicationLiteratureAssembler.assemble(...)`: sorts date-descending,
   limits/paginates, and emits warnings/source breakdown.

**Pydantic schema**

Add additive models in `app/backend/app/schemas/run.py`:

```python
PublicationTextSection = Literal[
    "title",
    "abstract",
    "body",
    "table",
    "supplement",
    "unknown",
]

PublicationSnippetSource = Literal[
    "pubmed_efetch",
    "pubtator",
    "pmc_bioc",
    "litvar2",
]

PublicationSnippetConfidence = Literal[
    "exact_variant",
    "variant_alias",
    "rsid",
    "gene_variant_context",
    "reported_no_text",
]


class PublicationSnippet(BaseModel):
    section: PublicationTextSection
    text: str
    matched_terms: list[str] = Field(default_factory=list)
    source: PublicationSnippetSource
    confidence: PublicationSnippetConfidence


class PublicationSourceBreakdown(BaseModel):
    litvar2: int = 0
    pubmed: int = 0
    clinvar: int = 0
    clingen: int = 0


class PublicationLiterature(BaseModel):
    total_count: int
    shown_count: int
    offset: int = 0
    limit: int = 5
    sort: Literal["publication_date_desc"] = "publication_date_desc"
    variant_terms: list[str] = Field(default_factory=list)
    source_breakdown: PublicationSourceBreakdown = Field(
        default_factory=PublicationSourceBreakdown
    )
    articles: list[PubMedArticle] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
```

Extend `PubMedArticle` additively:

```python
pmcid: str | None = None
doi: str | None = None
publication_date: str | None = None
snippets: list[PublicationSnippet] = Field(default_factory=list)
source_tags: list[Literal["litvar2", "pubmed", "clinvar", "clingen"]] = Field(default_factory=list)
snippet_status: str | None = None
```

Extend `ReportPayload` additively:

```python
publications_literature: PublicationLiterature | None = None
```

Keep existing `pubmed_articles` and `publications_callout` for compatibility.
When EP-VLEx is available, `pubmed_articles` should mirror
`publications_literature.articles` for the top-five set.

**Expansion endpoint**

Add:

`POST /api/v1/lookup/publications`

Request:

```python
class PublicationPageRequest(BaseModel):
    gene: str
    cdna: str
    transcript: str | None = None
    protein_change: str | None = None
    species: Literal["human", "mouse"] = "human"
    limit: int = Field(default=20, ge=1, le=50)
    offset: int = Field(default=0, ge=0)
```

Response:

`PublicationLiterature`

Mouse behavior should match lookup: return a structured unsupported response or
422, depending on the existing lookup convention selected during implementation.

**Snippet algorithm**

EP-VLEx snippet ranking:

1. Exact cDNA/protein/rsID match in title.
2. Exact cDNA/protein/rsID match in abstract sentence.
3. PubTator variant annotation matching rsID or normalized HGVS in title or
   abstract passage.
4. PMC BioC full-text sentence with exact variant alias.
5. Gene plus variant-alias context in the same sentence.
6. LitVar2-only table/supplement status when PMID is known but no text snippet
   is available.

Snippet extraction rules:

- Split text into conservative sentence windows using punctuation and section
  boundaries.
- Return one best snippet per article initially, with schema allowing more.
- Keep snippets concise enough for a row preview.
- Store `matched_terms` so the frontend can highlight the terms.
- Never mutate source text except whitespace normalization and truncation.

**Lookup wiring**

In `LookupService.lookup()`:

1. Continue running resolver, ClinVar, PubMed, and LitVar2 in the current order.
2. After LitVar2 result is recorded, call EP-VLEx with the resolved variant and
   evidence map.
3. Set:
   - `base_payload.publications_literature`
   - `base_payload.pubmed_articles`
   - `base_payload.publications_callout.total_count`
   - `base_payload.publications_callout.blurb`
4. Preserve fallback behavior if EP-VLEx raises. The report should still return
   with a warning such as `publication_literature_failed:<ExceptionName>`.

**Caching**

Use the existing variant cache path. Store:

- `litvar_id`
- `total_publications`
- `publication_data.summary`
- deduplicated PMIDs
- enriched article metadata/snippets for the first page
- source breakdown

Do not cache unresolved variants, matching the existing no-cache poisoning rule.

**Decisions**

- Decision: Source of truth for article links is always PubMed.
  Alternatives: link to LitVar2, PMC, or publisher pages. PubMed wins because
  the user explicitly requested NCBI PubMed as true source and it is stable.
  Reversible: yes, links can be expanded later with secondary source buttons.

- Decision: Use a paginated expansion endpoint rather than embedding all rows.
  Alternatives: embed all rows in `/lookup`. Pagination wins on latency, rate
  limits, and payload size. Reversible: partly, small counts can still return
  all rows later.

- Decision: Keep ACMG PS3/BS3 assignment out of the first EP-VLEx slice.
  Alternatives: infer PS3/BS3 from snippets. Deferral wins because raw snippets
  are not the same as curated functional evidence strength. Reversible: yes,
  a later functional-evidence classifier can consume EP-VLEx outputs.

- Assumption: ClinGen PS3/BS3 evidence is not yet available in a local table.
  EP-VLEx should define the source interface now and return zero until the data
  source is approved.

**Versions**

No new Python dependency is required for the first implementation. Use existing
`httpx`, `xml.etree.ElementTree`, Pydantic, and FastAPI. External source
contracts are NCBI E-utilities, LitVar2 API endpoints already used by the repo,
PubTator Central BioC export, and optional PMC BioC/ID converter APIs.

**Invariants**

- Article URL invariant: `article.url ==
  f"https://pubmed.ncbi.nlm.nih.gov/{article.pmid}/"`.
- Initial report invariant: `len(publications_literature.articles) <= 5`.
- Count invariant: `publications_callout.total_count ==
  publications_literature.total_count`.
- Sort invariant: initial articles are descending by normalized
  `publication_date`, falling back to `year`.
- Compatibility invariant: existing fixture lookup remains valid when frontend
  ignores `publications_literature`.
- Hold invariant: no `/runs` or AlphaMissense behavior changes.

**Error Behavior**

- LitVar2 unavailable: warn `publication_litvar2_failed:<ExceptionName>` and
  continue with PubMed/ClinVar PMIDs.
- PubMed metadata unavailable: return PMID stubs with PubMed URL and warn
  `publication_pubmed_metadata_failed:<ExceptionName>`.
- PubTator/PMC unavailable: return metadata rows without snippets and warn
  `publication_snippet_source_failed:<source>:<ExceptionName>`.
- No PMIDs: return `total_count=0`, `articles=[]`, no exception.
- Expansion offset beyond count: return `articles=[]` with the same total count.

**Testing Strategy**

- Unit tests for synonym generation, including cDNA, protein one-letter,
  protein three-letter, parentheses, and rsID aliases.
- Unit tests for PMID aggregation and dedupe across LitVar2, PubMed, ClinVar,
  and future ClinGen placeholders.
- Unit tests for snippet ranking: title hit, abstract hit, PubTator annotation,
  PMC full-text hit, table/supplement no-text status, and no-hit behavior.
- Route tests for `/api/v1/lookup/publications` pagination and limit bounds.
- Integration test for `/api/v1/lookup` proving top-five, total count, PubMed
  URL invariant, and snippets in fixture mode.
- Contract canary update for new Pydantic models and optional fields.
- Live smoke, when approved, against `RPE65 p.R118K` or `rs1381010953`, because
  LitVar2 currently resolves it to 3 PMIDs and PubTator returns title/abstract
  variant annotations.

**Out Of Scope**

- Frontend visual implementation, except for a cross-agent request or explicit
  user approval.
- Patient Report Pipeline (`/runs`).
- AlphaMissense.
- Publisher scraping.
- Final ACMG PS3/BS3 assertion from raw snippets.
- New persistent database migrations beyond existing variant cache usage.

Spec written to plans/variant-literature-extraction/spec.md
Review and reply "approve" to proceed, "edit" to revise, or leave feedback.
