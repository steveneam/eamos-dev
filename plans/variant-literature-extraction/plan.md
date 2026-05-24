# Variant Literature Extraction Plan

Source: `plans/variant-literature-extraction/spec.md`

Status update: 2026-05-19 19:56 +1000 - Codex implemented the backend
EP-VLEx slice covering Tasks 1-4 plus the Task 6 backend smoke/docs work.
Task 5 remains a frontend handoff for Claude because Codex did not edit
Claude-owned frontend render files or `backend.ts`.

Clarification from user, 2026-05-19: EP-VLEx is the general
variant-publication inventory. The Variant Evidence Report should display only
the first five rows initially, but the count/expansion path should represent
all publications the backend can identify for the variant. The functional card
is separate: it should count studies that performed functional work on the
variant, using functional-study screening tags/signals from ClinGen, ClinVar,
or PubMed. Do not treat the publication inventory count as the functional
study count, and do not force both cards through the exact same script.

Shared decisions before implementation:

- The custom algorithm name is **Eamos Proprietary Variant Literature Extractor
  (EP-VLEx)**.
- Publication title and PMID links always go to PubMed.
- The initial Variant Evidence Report payload returns five recent publications.
- Full expansion is paginated through a backend endpoint.
- The first slice exposes snippets and functional-literature navigation, but
  does not auto-assign final ACMG PS3/BS3 strength.
- Codex owns backend schemas/services/tests. Claude owns frontend visual render
  unless the user explicitly asks Codex to touch frontend contract/render files.

## Task 1 - Backend Contract And Fixtures - DONE 2026-05-19

**Goal**

Add the additive backend schema needed for EP-VLEx and deterministic fixtures
for an enriched publication section.

**Context**

`ReportPayload` already has `pubmed_articles` and `publications_callout`.
The new shape should be additive and should preserve current clients that only
read `pubmed_articles`.

**Relevant Files Or References**

- `app/backend/app/schemas/run.py`
- `app/backend/app/fixtures/tools/pubmed_fixtures.json`
- `app/backend/app/fixtures/tools/litvar2_fixtures.json`
- `app/backend/tests/test_frontend_contract.py`
- `plans/variant-literature-extraction/spec.md`

**Proposed Approach**

Add `PublicationSnippet`, `PublicationSourceBreakdown`,
`PublicationLiterature`, optional enriched fields on `PubMedArticle`, and
optional `ReportPayload.publications_literature`. Update backend fixtures so
fixture mode includes top-five-like enriched article rows with snippets.

**Acceptance Criteria**

- Existing lookup fixture tests still pass when the frontend ignores the new
  field.
- `PublicationsCallout.total_count` remains present and consistent.
- Fixture `PubMedArticle.url` values all point to PubMed.
- Contract canary covers the new backend models. If frontend mirror work is not
  approved for Codex, file a cross-agent request for Claude to mirror the
  additive TypeScript fields.

**Source Reference**

`plans/variant-literature-extraction/spec.md` sections "Pydantic schema" and
"Invariants".

**Verify**

`cd app/backend && python -m pytest tests/test_frontend_contract.py tests/test_variant_search_integration.py -q`

**Out Of Scope**

Frontend rendering and live API calls.

**Implementation note:** `PublicationLiterature`, `PublicationSnippet`, source
breakdown, enriched optional `PubMedArticle` fields, and optional
`ReportPayload.publications_literature` are implemented. Fixture
publication count now reflects the deduped RPE65 variant-specific PMID set
(3 rows) instead of the older broad count. Frontend mirror fields are listed in
the contract canary as pending and filed as a cross-agent request.

## Task 2 - EP-VLEx Synonym Builder And PMID Aggregator - DONE 2026-05-19

**Goal**

Implement the backend algorithm core that builds variant aliases and creates a
deduplicated PMID set.

**Context**

The current implementation merges PubMed and LitVar2 after lookup, but does not
centralize source breakdown, ClinVar citation PMIDs, or future ClinGen functional
PMIDs.

**Relevant Files Or References**

- `app/backend/app/services/publication_literature.py` (new)
- `app/backend/app/tools/pubmed.py`
- `app/backend/app/tools/litvar2.py`
- `app/backend/app/services/lookup_service.py`
- `app/backend/tests/`
- Local doc: `Gene Functional Literature Extraction.txt`

**Proposed Approach**

Create `EamosProprietaryVariantLiteratureExtractor` with a synonym builder and
`PublicationPmidAggregator`. Use LitVar2 summary PMIDs, PubMed targeted search,
ClinVar raw cited PMIDs where available, and a stubbed ClinGen source interface
that returns empty until a local source is approved. Deduplicate with a PMID set
and preserve per-source tags for each article.

**Acceptance Criteria**

- Alias generation covers gene, cDNA, transcript HGVS, protein HGVS,
  one-letter protein alias, three-letter protein alias, rsID, and genomic alias
  when available.
- Duplicate PMIDs from LitVar2 and PubMed count once.
- Source breakdown exposes counts per source.
- If one source fails, remaining sources still produce a result with a warning.

**Source Reference**

`plans/variant-literature-extraction/spec.md` sections "Backend components" and
"Requirements".

**Verify**

`cd app/backend && python -m pytest tests/test_publication_literature.py -q`

**Out Of Scope**

Snippet extraction and API route wiring.

**Implementation note:** `EamosProprietaryVariantLiteratureExtractor` builds
gene/cDNA/transcript/protein one-letter/protein three-letter/rsID/genomic terms,
dedupes PMIDs across PubMed, LitVar2, and ClinVar citation-like structures, and
skips failed live-source fallback fixture rows so unrelated fallback data is
not counted.

## Task 3 - Metadata And Snippet Extraction - DONE 2026-05-19

**Goal**

Attach recent-first metadata and LitVar2-style mention snippets to PMID rows.

**Context**

PubMed EFetch can provide title/abstract XML. PubTator can provide BioC JSON
with gene/variant annotations for PMIDs and PMCID full text. PMC can provide
open-access BioC full text when available.

**Relevant Files Or References**

- `app/backend/app/services/publication_literature.py`
- `app/backend/app/tools/pubmed.py`
- NCBI E-utilities docs: https://www.ncbi.nlm.nih.gov/books/NBK25499/
- PubTator API docs:
  https://www.ncbi.nlm.nih.gov/CBBresearch/Lu/Demo/PubTatorCentral/api.html
- PMC APIs: https://pmc.ncbi.nlm.nih.gov/tools/developers/

**Proposed Approach**

Batch ESummary/EFetch requests for metadata and abstracts. Query PubTator BioC
for annotated passages. Query PMC BioC for PMCID full text when available and
bounded. Rank snippets by exact variant/title, exact variant/abstract,
PubTator annotation, PMC text, gene-plus-variant context, then LitVar2 table or
supplement no-text status.

**Acceptance Criteria**

- Articles sort by publication date descending with year fallback.
- The five initial articles have PubMed URLs and normalized publication dates
  when metadata provides them.
- Snippet extraction returns matched terms and source labels.
- Table/supplement-only hits receive a labelled no-text status instead of a
  fabricated snippet.
- No publisher pages are scraped.

**Source Reference**

`plans/variant-literature-extraction/spec.md` sections "Snippet algorithm" and
"Error Behavior".

**Verify**

`cd app/backend && python -m pytest tests/test_publication_literature.py tests/test_tool_invariants.py -q`

**Out Of Scope**

Functional assay classification and frontend highlighting.

**Implementation note:** Initial snippets are title/abstract sentence snippets
from NCBI PubMed EFetch text already returned by `PubmedTool`; LitVar2/ClinVar
PMID-only rows are labelled with no-text statuses instead of fabricated
snippets. PubTator/PMC full-text snippets remain a future quality upgrade.

## Task 4 - Lookup Wiring, Cache, And Expansion Route - DONE 2026-05-19

**Goal**

Wire EP-VLEx into Variant Evidence Report lookup and expose a paginated
publication expansion endpoint.

**Context**

`LookupService.lookup()` already updates `publications_callout` and writes
publication data into the variant cache. The new implementation should preserve
that path and avoid poisoning the cache for unresolved variants.

**Relevant Files Or References**

- `app/backend/app/services/lookup_service.py`
- `app/backend/app/api/routes/lookup` or existing lookup route module
- `app/backend/app/repos/variant_cache_repo.py`
- `app/backend/app/core/db.py`
- `app/backend/tests/test_variant_cache.py`
- `plans/variant-literature-extraction/spec.md`

**Proposed Approach**

Call EP-VLEx after LitVar2 evidence is available. Populate
`publications_literature`, mirror its articles into `pubmed_articles`, and set
the callout count. Add `POST /api/v1/lookup/publications` with bounded
pagination. Cache total count, PMID set, source breakdown, first page metadata,
and snippet data.

**Acceptance Criteria**

- `/api/v1/lookup` returns at most five enriched publication rows.
- `publications_callout.total_count` equals
  `publications_literature.total_count`.
- `/api/v1/lookup/publications` returns deterministic pages and enforces
  `limit <= 50`.
- Cache hits do not call live discovery again for fresh records.
- Unresolved variants are not cached.

**Source Reference**

`plans/variant-literature-extraction/spec.md` sections "Expansion endpoint",
"Lookup wiring", and "Caching".

**Verify**

`cd app/backend && python -m pytest tests/test_variant_search_integration.py tests/test_variant_cache.py tests/test_publication_literature.py -q`

**Out Of Scope**

Frontend expand/collapse UI.

**Implementation note:** `/api/v1/lookup` now returns at most five
publication/literature rows and mirrors them to `pubmed_articles`.
`POST /api/v1/lookup/publications` returns bounded pages (`limit <= 50`).
Resolved live-mode cache records now store PubMed summary data and the EP-VLEx
first page so PubMed/LitVar2 publication discovery is not re-run on fresh cache
hits.

## Task 5 - Frontend Handoff For Publication/Literature Section - OPEN

**Goal**

Give Claude a clear contract for rendering the redesigned Publication/Literature
section on the Variant Evidence Report page.

**Context**

Claude is already planning the landing page, Variant Evidence Report page, and
Workbench page redesign. Codex should not edit Claude frontend files in this
session.

**Relevant Files Or References**

- `app/frontend/src/components/report/PubMedSection.tsx`
- `app/frontend/src/components/report/PublicationsCallout.tsx`
- `app/frontend/src/pages/ReportPage.tsx`
- LitVar2 screenshot supplied by the user
- `plans/variant-literature-extraction/spec.md`

**Proposed Approach**

File a cross-agent request after backend contract approval. The UI should show
"Showing 1-5 of N publications", render five recent cards with snippet and
matched-term highlighting, keep PubMed links, and use the expansion route for
more rows.

**Acceptance Criteria**

- Default UI displays five recent publications when at least five exist.
- It displays the correct total publication count.
- Each row shows title, PMID, date, journal/authors, snippet, and PubMed link.
- Expand/page controls fetch more rows without implying unshown rows were not
  counted.

**Source Reference**

User brief plus `plans/variant-literature-extraction/design.md`.

**Verify**

Claude-owned browser verification after frontend implementation.

**Out Of Scope**

Codex frontend edits without explicit user approval.

## Task 6 - Live Smoke And Documentation Sync - DONE 2026-05-19

**Goal**

Prove the source-backed path works against known NCBI data and record the
limitations clearly.

**Context**

A live check during planning showed LitVar2 resolves `RPE65 p.R118K` /
`rs1381010953` to a LitVar2 variant ID with 3 PMIDs, and PubTator returns
variant annotations for PMID `36142423`. This makes it a good smoke fixture.

**Relevant Files Or References**

- `plans/variant-literature-extraction/design.md`
- `plans/variant-literature-extraction/spec.md`
- `app/backend/README.md`
- `plans/v2-backend.md`
- `PROGRESS.md`

**Proposed Approach**

Run focused backend tests, full backend tests, and one approved live smoke with
`USE_REAL_APIS=true` for `RPE65 p.R118K` or `rs1381010953`. Update backend docs
and progress notes after code is verified.

**Acceptance Criteria**

- Live smoke returns 3 total publications for the known LitVar2 example unless
  NCBI data has changed, in which case the fresh count is recorded.
- PMID links point to PubMed.
- At least the title or abstract snippet is returned for PMID `36142423`.
- Full backend tests pass.
- Docs record source limitations, rate-limit behavior, and snippet provenance.

**Source Reference**

Official NCBI docs linked in the spec plus the planning live-smoke observation.

**Verify**

`cd app/backend && python -m pytest tests/ --disable-warnings`

Optional approved live smoke:

`USE_REAL_APIS=true` backend lookup for `RPE65 p.R118K` or `rs1381010953`.

**Out Of Scope**

Commit, push, stash, reset, clean, or unrelated backend work.

**Implementation note:** Live publications-only smoke for user-supplied
`USH2A c.2276G>T, p.Cys759Phe` returned HTTP 200 with 13 deduped PMIDs, first
page of 5 rows, `rs752238803` in variant terms, and no warnings after fixing
LitVar2 path escaping for IDs containing `@`/`#`. Full backend suite passed
after the fix.

**Functional-card note:** not implemented in this task. It should be a separate
functional-evidence extractor/count using functional tags/signals, not
`PublicationLiterature.total_count`.

## Task 7 - Publications-Over-Time Timeline - DONE 2026-05-24

**Goal**

Expose publication-count-per-year data for a frontend line graph in the
Publication/Literature expansion box.

**Implementation note:** added an additive
`PublicationLiterature.publication_timeline` group with
`publications_by_year: [{year, count}]` sorted ascending, `total_with_year`,
and `total_without_year`. The aggregation runs over the full deduplicated
EP-VLEx publication set before pagination, so the timeline is not limited to
the initially shown rows. Fixture-mode RPE65 PubMed rows now carry
deterministic `publication_date` values for 2022, 2023, and 2024. Both
`backend.ts` mirrors and `test_frontend_contract.py` were updated together.

**Verify**

`cd app/backend && python -m pytest tests/test_publication_literature.py tests/test_variant_search_integration.py tests/test_frontend_contract.py -q`

`cd app/backend && python -m pytest tests/ -q`

**Out of scope:** frontend line-graph rendering, gene-viewer conservation or
ClinVar enrichment, `/runs`, and AlphaMissense.
