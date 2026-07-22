# Lane P — deterministic Paper → Variants evidence

Evidence stamp: `2026-07-22T19:01:41Z`
Branch: `agent/live/paper-deterministic`
Frozen contract ancestor: `641c0e5`

## Delivered boundary

Lane P implements request-lifetime, deterministic L1–L3 extraction for JSON text and
page-preserving PDF text. It keeps mention extraction separate from allele resolution:
a mention is evidence that notation appeared in the document, while only an independently
source-backed resolver candidate or approved coordinate resolver may emit a resolved canonical
variant. Bundled candidate examples are fixtures and cannot validate or action-enable a row.

The document graph binds safe metadata, SHA-256 input digests, page number, section, exact
half-open character span, a bounded quote, biological context, deterministic digest, and a
per-mention resolution disclosure. Bibliography-only, experimental-construct, engineered-rescue,
and comparator/background contexts never become clinical alleles by inference. Main text and
text/CSV supplements can share one graph through the internal service boundary.

No dependency, corpus, source artifact, OCR model, external AI service, external metadata
provider, cloud resource, or deploy setting was installed, downloaded, materialized, or changed.
The only committed corpus is Eamos-owned synthetic text.

## Deterministic validation matrix

| Matrix slice | Expected invariant | Automated evidence |
| --- | --- | --- |
| Accession-qualified HGVS | Transcript and exact surface are retained | `test_typed_grammar_covers_accession_hgvs_rsid_splice_indel_and_legacy` |
| `c.`, `g.`, `n.`, `r.`, `m.`, `p.`, rsID, IVS | Typed grammar emits the correct frozen notation class | `test_typed_grammar_matrix` |
| Substitution, splice, deletion, insertion, duplication, delins, frameshift | Bounded grammar accepts typed forms without an unbounded token | `test_typed_grammar_matrix` |
| Line/space recovery | L2 normalizes notation but keeps the exact original span | `test_recovery_layer_preserves_exact_split_surface_and_span`, `test_recovery_canonicalizes_prefix_operation_and_bases_without_changing_span` |
| Section routing | Explicit and headerless reference tails are always excluded | `test_references_are_inventoried_but_always_bibliography_only`, `test_headerless_reference_tail_is_excluded_from_resolution_context` |
| Caption routing | Figure/table caption lines receive explicit evidence sections | `test_figure_and_table_caption_lines_have_explicit_sections` |
| Biological context | Case/proband, family, construct, rescue, and comparator stay distinct | `test_contexts_remain_distinct` |
| Association window | Gene/transcript inference cannot cross sections or an unbounded distance | `test_gene_association_does_not_cross_section_or_unbounded_distance` |
| Fixture truth | Static candidate examples cannot validate or create canonical output | `test_deterministic_extract_blocks_fixture_resolution_and_unknown` |
| Source gate | Only a non-fixture candidate with declared source support resolves; injected mounted records are not mistaken for bundled fixtures | `test_source_backed_resolution_is_the_only_action_enabling_path`, `test_injected_source_records_are_not_misclassified_as_bundled_fixtures`, `test_candidate_without_source_support_cannot_enable_action` |
| Submitted coordinate | A submitted genomic identifier alone is not independent source evidence | `test_submitted_genomic_identifier_requires_independent_source_verification` |
| Gateway isolation | An injected provider chain cannot replace deterministic mentions | `test_deterministic_output_is_stable_and_gateway_chain_cannot_replace_it` |
| Provider isolation | Generic live-API flags cannot silently enable coordinate-provider calls for Paper input | `test_default_paper_resolver_stays_offline_even_when_generic_live_apis_are_enabled` |
| PDF quality | Blank/image-only requires OCR; garbled text requires review | `test_blank_pdf_reports_ocr_requirement`, `test_api_blank_pdf_returns_typed_ocr_requirement` |
| PDF resource gates | File, page, object, character, encryption, and parser errors fail without partial text | `test_file_page_and_object_budgets_fail_closed`, `test_character_budget_fails_closed_without_partial_text`, `test_password_encrypted_pdf_fails_closed` |
| CLI quality parity | CLI blank/garbled inputs fail with the same typed requirements and no path echo | `test_cli_fails_honestly_for_garbled_text_and_blank_pdf` |
| Evidence bounds | Overlong tokens and mention floods cannot exceed frozen model bounds | `test_overlong_tokens_cannot_escape_frozen_evidence_bounds`, `test_mention_flood_is_bounded_before_resolution_or_schema_construction` |
| Synthetic corpus | License, expected mentions/exclusions, and file hashes are pinned | `test_synthetic_corpus_manifest_hashes_and_expectations_are_self_owned` |

Synthetic fixture hashes:

- `clinical-contexts.txt`: `483679d31f87015113010579910b9b6b6fe2a20b2c190a14a660b359cbc765f2`
- `recovery-contexts.txt`: `7087ffb28aed0625ca1c3dbae6a66c067d339639df132a8f49a66ba694fa6dbd`

## Hostile-input controls

| Trust boundary | Control and fail-closed result |
| --- | --- |
| Authentication and abuse | Existing authenticated principal plus the chat-class rate limiter run before body parsing. |
| JSON envelope | Declared and streamed request bytes are capped before JSON decoding; validation and parse errors do not echo input. |
| Multipart envelope | One file, at most two fields, a 64 KiB non-file part cap, sanitized multipart errors, and a conservative early `Content-Length` rejection. |
| Uploaded PDF | Generic server tempfile, 64 KiB streaming copy/hash, configured byte limit, MIME allow-list, `%PDF-` magic, no client filename in output, and `finally` cleanup of every form file/tempfile. |
| PDF parser | File, page, object, declared stream, image-per-page, per-page character, and total character limits; PDF parsing and resolution share a bounded semaphore/deadline; typed parser errors contain error class only. |
| Text quality | Empty/image-only and wholly garbled inputs return typed OCR/review requirements instead of a false zero-result success. |
| Grammar | Bounded accessions, positions, bases, amino-acid sequences, recovery whitespace, exact spans (180 characters), and 500 mentions per bundle. Truncation is explicit as `paper_mention_limit_exceeded:500`. |
| Persistence | No upload handle, host path, user filename, full source document, provider secret, or legacy evidence quote is stored. V2 persists only bounded evidence spans and safe metadata. |
| Resolution | Default resolution stays offline. Fixture rows, missing source support, submitted coordinates without independent provenance, and resolver failures remain unvalidated with no canonical variant. |
| Logs and CLI | Failures log/emit typed classes or codes only; no raw paper text, exception message, or input path is emitted. CLI reads files with bounded/streaming I/O. |

Manual linear/adversarial timing smoke on the lane worktree (single process, not a benchmark):

```text
plain_1m bytes=1120000 mentions=0 seconds=0.1509
adversarial_protein_150k bytes=150000 mentions=0 seconds=0.0323
overlong_tokens_1m bytes=1000970 mentions=0 seconds=0.1206
mention_flood_275k bytes=213893 mentions=500 warnings=1 seconds=0.1120
```

## Exact unresolved dependency and material requests

These are requests for the composition/dependency owner, not changes made by Lane P.

1. **Primary PDF engine:** pin
   [`pypdfium2==5.12.1`](https://pypi.org/project/pypdfium2/5.12.1/) and retain `pypdf`
   as a typed fallback. PyPI reports BSD-3-Clause/Apache-2.0 project licensing plus bundled
   PDFium/third-party notices, and a 3.7 MB manylinux x86-64 wheel. Composition must record the
   installed/image delta and preserve all bundled notices. The adapter seam already exists in
   `pdf_text.py`. Health must exercise page count, selectable text, a blank scanned page, a
   malformed PDF, deadline behavior, and the exact loaded engine/version; startup/import success
   alone is insufficient.
2. **Optional PDF repair/XMP:** if composition wants a repair-first boundary, separately review and
   pin [`pikepdf==10.10.0`](https://pypi.org/project/pikepdf/10.10.0/) under MPL-2.0. The current
   release page exposes a 23.9 MB source distribution, so native qpdf/build requirements and final
   image delta must be measured before approval. Current extraction does not require pikepdf.
3. **XLSX supplements:** only if XLSX ingestion is approved, pin
   [`openpyxl==3.1.5`](https://pypi.org/project/openpyxl/3.1.5/) (MIT) together with
   [`defusedxml==0.7.1`](https://pypi.org/project/defusedxml/0.7.1/) (PSF). The openpyxl project
   explicitly warns that default XML parsing does not protect against quadratic blowup or billion
   laughs attacks. The implementation must additionally cap archive bytes, decompressed bytes,
   entry count, worksheets, rows, columns, cells, shared strings, and formula/external-link use;
   it must never persist raw workbook contents. No XLSX parser exists in this lane.
4. **OCR:** provide a separately licensed, local-only OCR engine/model and measured image delta if
   scanned PDFs are release scope. No external OCR provider is authorized. Until then the typed
   result is `ocr_required`; it must not be presented as “no variants found.”
5. **Validation material:** mount a licensed/source-versioned allele resolver artifact (or an
   approved source-backed local resolver) before allowing Paper → Variants to drive actions.
   Bundled search-candidate fixtures intentionally stay unavailable for resolution.
6. **Scientific corpus:** approve a legally reusable open-access PDF/supplement corpus with pinned
   checksums, licenses, expected inclusions/exclusions, and no patient-identifying material. Lane P
   downloaded no publication corpus; its matrix is synthetic and therefore validates mechanics,
   not clinical recall.

## Known residuals and integration requests

- `asyncio.wait_for(run_in_threadpool(...))` bounds the response but cannot kill a parser thread.
  Composition should run PDF parsing in a resource-capped worker process before treating hostile
  PDFs as fully isolated. Declared stream limits are defense in depth; pypdf may allocate while
  decompressing before the post-extraction character cap runs.
- Starlette may spool a file part while parsing multipart before application-level streaming copy
  verifies the exact file size. The envelope and `Content-Length` controls reduce this exposure,
  but a server/proxy request-body cap is still required.
- PDFium, pikepdf, openpyxl, defusedxml, OCR, and a source-backed allele artifact are absent in the
  current environment. Their capability paths remain typed unavailable or unimplemented.
- Metadata is embedded/bounded-text only. Crossref, OpenAlex, PubMed, and other external enrichment
  were not authorized and are not called.
- The frozen V2 upload-ref request schema has no owner-bound upload-store route in Lane P scope.
  Wave integration must resolve upload refs under the authenticated owner, re-check size/hash, then
  build the internal main-plus-supplement document graph. The internal service already supports
  text/CSV supplements.
- Existing gateway-configured disclosure/consent behavior is retained for compatibility even
  though L1–L3 never calls the injected provider chain. A future L4 endpoint/flag needs a serial
  contract/route decision so local deterministic extraction and optional external adjudication
  have distinct disclosures.

## Verification commands

Final local results:

```text
74/74 focused Paper/PDF/extraction tests passed.
401/401 live-contract/frontend-contract/workflow/rate-limit/boundary tests passed.
The complete 1,915-test backend collection reached 100% with only the repository's expected skips.
ruff check: passed for every owned Python path.
black --check: passed for every owned Python path.
git diff --check: passed.
eamos-web-boundary: clean (292 tracked app/web files).
evidence-security triage: 1,030 tracked text files scanned; Lane P produced only
expected inventory leads for the reviewed upload surface and the test's fail-if-network guard.
No Lane P secret/authentication/high-priority lead was emitted.
```

Commands:

```bash
PYTHONPATH=app/backend app/backend/.venv/bin/pytest -q \
  app/backend/tests/test_paper_variants.py \
  app/backend/tests/test_pdf_text.py \
  app/backend/tests/test_paper_extract_grammar.py \
  app/backend/tests/test_paper_extract_pipeline.py

PYTHONPATH=app/backend app/backend/.venv/bin/pytest -q \
  app/backend/tests/test_live_product_contract.py \
  app/backend/tests/test_frontend_contract.py \
  app/backend/tests/test_product_workflow_api.py \
  app/backend/tests/test_rate_limits.py \
  app/backend/tests/test_boundary.py

PYTHONPATH=app/backend app/backend/.venv/bin/pytest -q app/backend/tests
node scripts/eamos-web-boundary.mjs
```

Warning-only pytest output consists of existing Starlette/httpx deprecations and short test JWT
fixture keys; no production key or secret was used.
