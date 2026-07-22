# Report composition and artifact requests

These are requests for the later serial composition/materialization waves. They
are not authorization to download, generate, upload, register, seed, deploy, or
activate any asset. A complete request includes the immutable source/version,
licence decision, checksums, file sizes, reader seam, and fail-closed health
result.

The existing runtime readers use `pysam==0.24.0`; no new report-runtime package
is requested for coordinate-keyed score caches. CI-SpliceAI and CAPICE adapters
read precomputed caches: merely mounting a model does not prove model inference
ran.

| Capability | Exact artifact request | Version/licence gate | Approximate cost | Runtime seam and health check | Fail-closed result |
| --- | --- | --- | --- | --- | --- |
| AlphaMissense | `AlphaMissense_hg38.tsv.gz`, `.tbi`, adjacent immutable manifest with size and checksums | Zenodo 10813168 v3; CC BY 4.0; verify upstream MD5 `9fd167735f16a1b87da6eb3e4c25fcb5` and derived-index checksum | 643 MB plus index; mount/cache, do not bake into image | `TabixTsvPredictorReader`; `inspect_alphamissense_runtime_asset` must be `ready` | Independent predictor `unavailable` with the missing file/index/manifest requirement |
| ESM-1b | Regenerated `esm1b_hg38.tsv.gz`, `.tbi`, manifest recording model, MANE, GRCh38, assembly-code, output and index hashes | Public launch requires regeneration from the MIT model; the known precomputed Hugging Face score zip is CC-BY-NC-4.0 and must not clear the launch gate | Estimated 2–4 GB compressed plus offline build compute | `TabixTsvPredictorReader`; `inspect_esm1b_runtime_asset` must be `ready` with no regeneration gate | ESM-1b alone is unavailable; other predictors remain independent |
| CI-SpliceAI | Complete set: `ci_spliceai.keras`, `hg38_reference.json`, bgzip score VCF, `.tbi`, and sidecar manifests | Self-hosted reviewed release; repository licence recorded as CC BY 4.0; hosted service is not a production dependency | Exact release size and offline compute are still required from the operator; no image bundling | Runtime reads the score cache with `PysamIndexedVcfReader`; all three component inspections must be ready | CI-SpliceAI unavailable with the exact missing component; no proxy SpliceAI claim |
| CAPICE | Complete set: model JSON, bgzip coordinate-keyed feature/score cache, `.tbi`, and sidecar manifests | Pin model/cache source versions and complete licence/provenance review before activation | Exact size/build compute pending; mounted/private cache expected | Runtime reads the cache with `TabixTsvPredictorReader`; model and cache completeness inspection must be ready | CAPICE unavailable; the presence of a model alone is not execution |
| REVEL | Reviewed hg38 score TSV, `.tbi`, and immutable manifest | Registry currently marks the source restricted/unlicensed with no approved source URL or download; resolve terms and exact release before acquisition | Approximately 2 GB plus index | Existing restricted-predictor tabix adapter; `inspect_revel_runtime_assets` must be ready and keep launch metadata | REVEL unavailable; no fixture score or aggregate fallback may substitute |
| PrimateAI-3D | Reviewed hg38 score TSV, `.tbi`, and immutable manifest | Registry currently marks the source restricted/unlicensed and download-unapproved; resolve terms, source URL, and release first | Approximately 10 GB plus index | Existing restricted-predictor tabix adapter; `inspect_primateai3d_runtime_assets` must be ready and keep launch metadata | PrimateAI-3D unavailable; other predictor execution is unaffected |

For every mounted artifact, the operator handoff must provide:

1. source URL/record and immutable release or commit;
2. licence and permitted-field decision;
3. byte size plus upstream and derived SHA256/MD5 values;
4. manifest and index identity;
5. mount/object-cache location through approved configuration, without paths or
   object URIs in public output;
6. sanitized provider-cache/preflight output;
7. one known-hit, one not-found, one identity-mismatch, and one corrupt-artifact
   verification case; and
8. explicit rollback to `unavailable`, never to fixture or a different named
   predictor.
