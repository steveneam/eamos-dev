---
type: memory
topic: batch
---

# Batch Cache Preserves VCF Metadata

When Batch caches lookup results by genomic `variant_key`, a later request for the same coordinate may carry richer parser metadata (`GENE`, `HGVS_C`, `HGVS_P`, `AF`) than the original coordinate-only lookup.

General lesson: cache hits should preserve source-backed classification/evidence, but still enrich missing display and navigation metadata from the current parsed variant. Otherwise a valid cached coordinate-only result can make the UI look as if Eamos does not know the gene or cDNA, even though the VCF/parser/resolver path already supplied it.

What got easier next time:

- Reproduce cache issues with a two-step service test: first cache coordinate-only, then submit the same genomic key with richer parsed metadata.
- Check both directions in browser verification: POST payload contains `gene`/`variant`, and paged Batch response returns `gene`/`hgvs_c`/report links.
- Treat frontend VCF INFO parsing and backend cache enrichment as complementary: frontend inline submissions should carry common INFO fields plus structured `chrom`/`pos`/`ref`/`alt`/`filter`/`info_af`, while server upload parsing remains the authoritative path for large VCFs.
