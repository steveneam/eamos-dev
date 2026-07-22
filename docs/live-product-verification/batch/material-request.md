# Wave 3 Batch material request — approval required, not executed

Lane B deliberately performs no download, source materialization, artifact
build, mount, environment/provider mutation, Supabase write, or deployment.
Release execution remains unavailable until Steven approves an exact Wave 3
card and the resulting artifacts pass functional probes.

## Required runtime/artifact set

| Request | Required identity and probe | Runtime behavior while absent |
| --- | --- | --- |
| Pinned `bcftools` runtime | Exact version, binary SHA-256, licence/SBOM row; fixed-argv `norm --check-ref e -f ... -m -any`; version plus normalize/reference-mismatch probes | Normalization disclosure is `unavailable`; no V2 row is annotated |
| GRCh38 reference | Exact GRCh38 release FASTA, `.fai`, source URL/terms, compressed/uncompressed size, manifest ID, SHA-256, rollback copy; known REF-match and REF-mismatch probes | Same fail-closed normalization state |
| MANE coordinates | Exact Select + Plus Clinical release, GFF/GTF/summary identity, digest and interval-index builder; exon/strand/splice-flank probes | Whole-gene/MANE interval capability unavailable |
| HGNC symbols | Exact complete/withdrawn-symbol release, CC0 terms, digest, alias/previous-symbol builder and probe | Submitted/local names remain custom and unverified |
| GenCC assertions | Exact downloadable CC0 release, digest, validity mapping builder, positive/negative disease-gene probes | Disease-to-gene resolution unavailable |
| Mondo | Exact CC BY 4.0 release, digest, mapping builder and MONDO resolution probes | Disease panel resolution unavailable |
| Optional offline VEP | Exact code/cache versions, code/data terms, cache/reference compatibility, sizes/digests, bounded offline command and parity matrix | Batch continues through direct Report lookup; no VEP claim is shown |

The final approval card must add the exact source URLs, release identifiers,
expected compressed/uncompressed sizes, destination paths, checksums, builder
commands, runtime mounts, update cadence, rollback steps, and functional probes.
Those values are intentionally not guessed here.

## Explicit launch gate

Genomics England PanelApp is a separately named overlay. It remains disabled
pending explicit downstream-use rights approval and may never lend its label to
the custom or permissively built catalog. Network failure never activates the
illustrative catalog as scientific source material.

## Composition requests for Wave 2

- Inject the same direct `LookupService` used by Report at startup; remove lazy
  service-order repair as a release dependency and assert it in preflight.
- Inject a deployment-stable, secret cursor-signing key so snapshot cursors
  survive process restarts without becoming forgeable.
- Construct `BcftoolsBatchNormalizer` only from the approved immutable runtime
  manifest; never infer a host binary or reference path.
- Register executed probes, versions, licences, launch posture, and exact
  unavailable behavior in the shared capability registry.
- Measure container image size, cold start, idle/peak RSS, 150k runtime, and
  lease recovery under the actual free deployment before enabling Batch V2.
