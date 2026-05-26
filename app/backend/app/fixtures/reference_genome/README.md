# Reference Genome Fixture Methods

This fixture is the Task 4 tiny, checked-in reference model for
`ReferenceGenomeStore`. It is not a biological reference asset and does not
replace `hg38.2bit`.

## Provenance

- Fixture file: `hg38_tiny.json`.
- Runtime source ID: `ucsc_hg38_2bit`, matching the data-source registry row.
- Source metadata is intentionally shaped like the real local asset metadata:
  source ID, source URL, source version, fixture path, checksum, reader, local
  asset path, local MD5, and local size.
- Sequence data is synthetic and tiny so default tests do not require network,
  Supabase, a 2bit reader, or the full ignored `hg38.2bit`.

## Coordinate Protocol

- Caller inputs use 1-based inclusive genomic coordinates.
- The fixture reader converts to Python slicing with:
  - `zero_based_start = start - 1`
  - `zero_based_end_exclusive = end`
- Returned windows include both caller coordinates and internal slice
  coordinates so future real readers can be checked against the same protocol.

## Alias Protocol

- Chromosome aliases are explicit fixture metadata, not guessed from arbitrary
  strings.
- The store normalizes `chr` prefixes case-insensitively.
- `MT` normalizes to `M`.
- RefSeq aliases such as `NC_000001.11` resolve only when present in fixture
  metadata.

## Validation Protocol

- Unknown chromosomes raise `ReferenceGenomeStoreError` with code
  `unknown_chromosome`.
- Unsupported builds raise `unsupported_build`.
- Invalid 1-based windows raise `invalid_coordinates`.
- Windows beyond the fixture sequence length raise `out_of_bounds`.
- `validate_reference_base` uppercases single-base expectations and returns a
  structured match/mismatch result. Multi-base or unsupported expectations
  return `invalid_expected_base` without reading a sequence window.

## Algorithms And Equations

- Window extraction: `sequence[start - 1 : end]`.
- Reference-base validation: exact equality of the observed one-base window and
  the normalized expected base.
- Fixture checksum: SHA-256 over canonical sorted records formatted as
  `<chrom>\t<sequence>\n`.

Future local stores should keep this pattern: checked-in method notes beside
fixtures/adapters, explicit source provenance, coordinate equations, algorithm
choices, and fail-closed validation behavior.
