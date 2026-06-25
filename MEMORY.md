---
type: project
---

# Eamos Memory

Persistent one-fact memories for generalizable project lessons.

- [[batch-async-upload-progress]] - Batch async upload/progress belongs in shared client helpers, not each UI surface.
- [[graphify-generated-output-hygiene]] - Graphify outputs are local rebuildable artifacts, not source.
- [[batch-cache-preserves-vcf-metadata]] - Batch lookup cache hits must be enriched with current parsed VCF metadata.
- [[batch-dedupe-by-resolved-identity]] - Batch dedupe should use resolved genomic identity and merge richer duplicate metadata before lookup.
- [[generated-artifact-s3-sync-parity]] - Generated SQLite artifact upload and sync both need Supabase S3-compatible transport support when REST service-role credentials are absent.
- [[source-asset-metadata-runtime-separation]] - Private source object metadata can be verified and approved while runtime materializations stay fail-closed until the target service disk is seeded and verified.
- [[eamos-gene-variant-agnostic-invariant]] - Eamos is a gene- and variant-agnostic search/evidence platform; fixes should land at shared normalization, selection, orchestration, or source-cache boundaries with pure/helper regression coverage, not as single-gene patches proven only by browser checks.
- [[eamos-architecture-consistency-gate]] - Architecture work should follow the shared gate skeleton across lookup, analysis, report sections, caches, UI slots, metrics, storage, and production-readiness proof; PubMed/PMC belongs in layered corpus architecture, not huge Postgres blobs.
