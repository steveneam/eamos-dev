# MaveDB License Gate

Last updated: 2026-06-27 18:05 +1000 - Codex.

This is an engineering risk note, not legal advice.

## Sources Checked

- MaveDB documentation: `https://www.mavedb.org/docs/mavedb/index.html`
- MaveDB data-format and score-set license documentation:
  `https://www.mavedb.org/docs/mavedb/data_formats.html`
- MaveDB API repository license:
  `https://github.com/VariantEffect/mavedb-api/blob/main/LICENSE`
- GNU AGPLv3 text, including remote-network interaction terms:
  `https://www.gnu.org/licenses/agpl-3.0.html`

## Current Decision

Do not import, vendor, modify, host, containerize, or wrap the AGPL MaveDB
application/API package as an Eamos runtime dependency without legal approval.
A subprocess, CLI, or container boundary may reduce ordinary linking risk, but
it should not be treated as a reliable commercial SaaS workaround for AGPLv3.

For Eamos, keep MaveDB as a licensed data-ingestion lane:

- ingest only operator-supplied score rows;
- require row-level license metadata;
- accept only CC0 rows in the current launch gate;
- reject CC BY, CC BY-SA, missing-score, and missing-license rows unless a later
  legal/product gate explicitly supports the attribution or share-alike terms;
- preserve source accession, source URL, license, and source-version metadata;
- avoid startup downloads, request-time downloads, remote mutation, provider
  flips, or live MaveDB API dependence.

This matches the current implementation in
`app/backend/app/services/mavedb_local.py`: the materializer builds a local
SQLite source asset from operator-supplied JSONL and filters accepted records to
CC0 before they can appear in functional evidence.

## Practical Boundary

Allowed without changing the current gate:

- Use the existing local materializer on reviewed JSONL rows whose score-set
  license is CC0.
- Link users back to MaveDB score-set URLs as source provenance.
- Report MaveDB rows as uncurated functional evidence unless a separate curation
  source asserts ACMG evidence strength.

Not allowed without explicit legal/product approval:

- Importing the AGPL `mavedb` package into Eamos code.
- Bundling or deploying the MaveDB API/server as part of Eamos.
- Putting an AGPL MaveDB container behind an internal API and treating the
  network boundary as a license workaround.
- Expanding the data gate to CC BY or CC BY-SA rows without attribution and
  share-alike handling.

## Follow-Up If More Coverage Is Needed

If CC0-only coverage proves insufficient, the next architecture-safe step is a
separate license matrix for MaveDB score-set licenses, attribution display,
share-alike implications, and commercial launch policy. Do not solve that by
embedding the AGPL application code.
