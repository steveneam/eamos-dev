# Batch V2 security evidence

The lane was implemented under the repository's evidence-first and vibe-code
security checks because it crosses authentication, uploads, durable user data,
subprocesses, and exports.

| Boundary | Control and evidence |
| --- | --- |
| Authorization | Upload refs, jobs, recovery records, paging, cancellation, deletion, and export use both owner user ID and provider; cross-owner tests return 404 |
| Uploads | Multipart size check plus streamed compressed/decompressed/record/line/time bounds; opaque `0600` file; single use; expiry/crash cleanup targets only `batch-*.upload` regular files |
| De-identification | Client filename and VCF sample names are discarded; only server-issued sample keys enter results |
| Parser | `pysam`/HTSlib is the V2 reader; unsupported formats/classes/contigs/cohorts fail before annotation |
| Subprocess | Absolute executable/reference paths, verified reference digest and `.fai`, fixed argv, `shell=False`, private temp directory, bounded timeout, sanitized errors |
| Durable state | Raw/body keys are rejected by the workflow repository; lease SQLite is mode `0600` and contains no variants, genotypes, or VCF bytes |
| Paging | V2 cursors are HMAC authenticated and bound to the immutable source snapshot; cross-snapshot/tamper tests fail |
| Exports | Owner check precedes terminal-only streaming; CSV/TSV formula prefixes are neutralized; JSONL is schema-filtered; VCF omits sample/genotype columns; digest/row/snapshot receipts are deterministic |
| Scientific trust | V2 INFO fields never satisfy computed output; normalization, interval sources, Report V2 state, and panel material fail closed. The legacy sampleless compatibility path is visibly non-V2 and never promotes submitted protein, classification, or frequency values |

Residual composition risks are explicit: the cursor secret must be stable and
secret-backed, the direct LookupService must be startup-injected, and container
resource measurements must pass before release. The framework multipart parser
spools the request before the bounded VCF reader takes ownership; the Wave 2
container gate must verify request/body limits for chunked uploads as well as
declared `Content-Length`. Scientific source downloads remain behind the
separate Wave 3 approval gate.
