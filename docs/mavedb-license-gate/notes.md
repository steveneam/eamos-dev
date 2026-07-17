# MaveDB License Gate

Last updated: 2026-07-17 13:39 +0000 - Codex.

This is an engineering risk note, not legal advice.

## Sources Checked

- MaveDB documentation: `https://www.mavedb.org/docs/mavedb/index.html`
- Current MaveDB license and data-usage-policy documentation:
  `https://www.mavedb.org/docs/mavedb/submitting-data/metadata-guide.html`
- Current CC0-only bulk-download documentation and concept DOI:
  `https://www.mavedb.org/docs/mavedb/finding-data/downloading.html` and
  `https://doi.org/10.5281/zenodo.11201736`
- MaveDB API quickstart and citation guidance:
  `https://www.mavedb.org/docs/mavedb/programmatic-access/api-quickstart.html`
  and `https://www.mavedb.org/docs/mavedb/citation.html`
- MaveDB API repository license:
  `https://github.com/VariantEffect/mavedb-api/blob/main/LICENSE`
- GNU AGPLv3 text, including remote-network interaction terms:
  `https://www.gnu.org/licenses/agpl-3.0.html`

## Current Decision

Do not import, vendor, modify, host, containerize, or wrap the AGPL MaveDB
application/API package as an Eamos runtime dependency without legal approval.
A subprocess, CLI, or container boundary may reduce ordinary linking risk, but
it should not be treated as a reliable commercial SaaS workaround for AGPLv3.
Eamos becoming free-of-charge does not remove any applicable AGPL source-
disclosure obligations.

For Eamos, keep MaveDB as a versioned CC0 data-ingestion lane:

- prefer a specifically resolved, immutable version of MaveDB's official
  CC0-only Zenodo archive;
- require authoritative archive and score-set metadata rather than trusting a
  caller-supplied license string;
- quarantine any non-empty restrictive or ambiguous `dataUsagePolicy`;
- accept only CC0 rows in the current launch gate;
- reject CC BY, CC BY-SA, missing-score, and missing-license rows unless a later
  legal/product gate explicitly supports the attribution or share-alike terms;
- preserve archive DOI/hashes, score-set and variant URNs, target/mapping,
  canonical source locator, license snapshot, policy decision,
  deprecation/supersession, and source-version metadata;
- avoid startup downloads, request-time downloads, remote mutation, provider
  flips, or live MaveDB API dependence;
- treat the archive as hostile input: verify its published digest, reject
  traversal/symlinks and unapproved members, enforce compressed/expanded and
  parser-shape limits, and fail atomically;
- derive record links from validated URNs and a fixed allowlisted origin rather
  than trusting imported URLs.

The current implementation in `app/backend/app/services/mavedb_local.py` is a
synthetic-fixture scaffold only. It filters an operator-supplied JSONL license
string to CC0, but it is not an official MaveDB archive parser and is not
approved for real materialization. Its v1 table keys rows only by score-set URN,
so variants within a real score set overwrite one another; it also lacks the
authoritative license/policy, target, calibration, precision, checksum-readiness,
and report provenance required for launch. The active repair plan is
[`plans/evidence-source-expansion/plan.md`](../../plans/evidence-source-expansion/plan.md).
The initial bulk lane is raw-score-only: calibration, mapped-VRS, and VA-Spec
objects require a separately pinned API/source and rights review.

## Practical Boundary

Allowed without changing the current gate:

- Use the existing local materializer only with hand-authored synthetic test
  fixtures.
- Link users back to MaveDB score-set URLs as source provenance.
- Design and test a schema-v2 archive importer without acquiring the live
  corpus.

Not allowed without explicit legal/product approval:

- Importing the AGPL `mavedb` package into Eamos code.
- Bundling or deploying the MaveDB API/server as part of Eamos.
- Putting an AGPL MaveDB container behind an internal API and treating the
  network boundary as a license workaround.
- Expanding the data gate to CC BY or CC BY-SA rows without attribution and
  share-alike handling.
- Materializing a real MaveDB archive with schema v1 or treating a raw score as
  PS3/BS3, OddsPath, or a call-card color.

Calling the hosted public REST API through Eamos's own HTTP client does not
import the AGPL server package. A bounded metadata supplement may be designed
later, but bulk acquisition should use the official archive and must never run
at request time.

## Follow-Up If More Coverage Is Needed

First complete the schema-v2, authoritative-license, exact-match,
checksum-readiness, multi-match report, and no-PS3/BS3 tests in the evidence
expansion plan. After that, an operator may approve one pinned CC0 archive
release for materialization. If CC0-only coverage proves insufficient, use a
separate license matrix for CC BY attribution and CC BY-SA adapted-database
handling. Do not solve broader coverage by embedding the AGPL application code.
