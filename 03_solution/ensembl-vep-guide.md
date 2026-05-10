# Ensembl VEP REST Guide (Practical + JSON Interpretation)

## Goal

Use Ensembl VEP to annotate variants in a reproducible way for our backend:

`raw variant -> normalized effect -> transcript impact -> variant scoring`.

We use this as **evidence enrichment**, not a final clinical verdict source.

---

## Base endpoint formats

### A) Single variant by HGVS

`GET https://rest.ensembl.org/vep/{species}/hgvs/{HGVS}?content-type=application/json`

Example:
`https://rest.ensembl.org/vep/human/hgvs/ENST00000288602.4:c.34G>A?content-type=application/json`

### B) Single variant by region/canonical notation

`GET https://rest.ensembl.org/vep/{species}/region/{region}?content-type=application/json`

Example:
`.../vep/human/region/7 140753336 140753336 G/A` (with proper URL encoding)

### C) Batch mode (recommended)

`POST https://rest.ensembl.org/vep/{species}/id`  (or `/hgvs`)

Headers:
- `Content-Type: application/json`
- `Accept: application/json`

Example payload for HGVS batch:
```json
{
  "hgvs_notations": [
    "ENST00000288602.4:c.34G>A",
    "ENSP00000419060.1:p.V600E"
  ]
}
```

Example payload for rsID batch:
```json
{
  "ids": ["rs142513484", "rs267606609"]
}
```

---

## What the response looks like (common shape)

Top level often is an array; each item is a variant annotation.

```json
[
  {
    "id": "ENST00000288602.4:c.34G>A",
    "input": "ENST00000288602.4:c.34G>A",
    "assembly_name": "GRCh38",
    "seq_region_name": "7",
    "start": 140924670,
    "end": 140924670,
    "strand": -1,
    "allele_string": "G/A",
    "most_severe_consequence": "missense_variant",
    "transcript_consequences": [ ... ],
    "regulatory_feature_consequences": [ ... ],
    "colocated_variants": [ ... ],
    "motif_feature_consequences": [ ... ]
  }
]
```

## Important fields and what they mean

### 1) `assembly_name`
Genome build used (e.g., GRCh38).

### 2) `most_severe_consequence`
The strongest functional class among all transcript results.

### 3) `transcript_consequences[]`
Most used for downstream logic.

Each row typically includes:
- `transcript_id` (e.g., ENST...)
- `gene_id`, `gene_symbol`, `hgnc_id`
- `transcript_id`, `biotype`
- `consequence_terms[]` (e.g., `missense_variant`, `splice_donor_variant`)
- `impact` (`HIGH`/`MODERATE`/`LOW`/`MODIFIER`)
- `variant_allele`
- `cdna_start`, `cds_start`, `protein_start`
- `cdna_end`, `cds_end`, `protein_end`
- `amino_acids`, `sift_score`, `sift_prediction`, `polyphen_score`, `polyphen_prediction`
- `hgvs_c`, `hgvs_p` may appear in other endpoint variants

**How AI should use this:**
- pick one canonical/transcript-normalized interpretation (or report top N),
- use `impact` + consequence terms as a ranking heuristic,
- compute a human-readable phrase like “missense in exon X; SIFT says deleterious/benign” with caveats.

### 4) `colocated_variants[]`
Variant(s) co-located in same locus (population links, existing IDs).

Use as supplementary signal (e.g., rsID context), not primary truth.

### 5) `regulatory_feature_consequences[]` and `motif_feature_consequences[]`
Non-coding/regulatory effects.

Only use if your use-case actually supports non-coding interpretation.

### 6) `distance` and exon-related fields (when present)
Distance-to-exon may indicate positional context; interpret sign/meaning per Ensembl docs.

---

## Quality and reliability notes

- VEP is only one source. Treat every prediction score as *supporting evidence*.
- Prefer `cache` + deterministic fixture during hackathon for reliability.
- If endpoint fails, keep stale/empty fallback and mark as "insufficient coverage".

---

## Retrieval strategy for this project

1. Build adapter method `annotate_variant(payload)`.
2. Call VEP first for each normalized variant.
3. Convert response into a compact local model:
   - gene symbol(s)
   - most severe consequence + impact
   - canonical transcript fields
   - key scores
   - linked ids/positions
4. Persist raw response for audit/debug.
5. Pass compacted output to decision-rules + explanation layer.

---

## Minimal Pydantic-style model (adapter output)

```python
class VepTranscriptImpact(BaseModel):
    transcript_id: str | None = None
    gene_symbol: str | None = None
    gene_id: str | None = None
    consequence_terms: list[str] = []
    impact: str | None = None
    variant_allele: str | None = None
    protein_change: str | None = None
    sift_score: float | None = None
    polyphen_score: float | None = None

class VepVariantAnnotation(BaseModel):
    raw_variant: str
    assembly: str | None = None
    most_severe_consequence: str | None = None
    gene_symbols: list[str] = []
    impacts: list[VepTranscriptImpact] = []
    colocated_count: int = 0
    evidence_fallback_reason: str | None = None
```

---

## Practical endpoint limits and handling

- Set timeouts low (2–5s for web calls in hackathon mode)
- Use retries with jitter
- Cache by variant key
- If you get HTTP 429/5xx, fallback to fixture + warning
- Record `request_error` in run log for auditability

---

## Demo-case mapping: `RPE65 c.260A>G`

For the current demo case, the clean VEP input is the transcript HGVS form:

```http
GET https://rest.ensembl.org/vep/human/hgvs/NM_000329.3:c.260A>G?content-type=application/json
```

### Canonical filter to match the UI search intent
From `transcript_consequences[]`, filter by:
- `gene_symbol == "RPE65"`
- `cds_start == 260`
- `protein_start == 87`

### Canonical transcript facts returned
- `gene_symbol` -> `RPE65`
- `transcript_id` -> `ENST00000262340`
- `biotype` -> `protein_coding`
- `consequence_terms` includes `missense_variant`
- `amino_acids` -> `D/G`
- `protein_start` -> `87`
- `cds_start` -> `260`

### How to reproduce the UI-style consequence percentages
If you count all returned consequence terms across all transcripts for this variant, you get:
- `missense_variant` -> `4 / 9` -> `44.4%`
- `NMD_transcript_variant` -> `4 / 9` -> `44.4%`
- `3_prime_UTR_variant` -> `1 / 9` -> `11.1%`

So the percentages in the UI can be reproduced from the returned transcript consequence mix, rather than from a separate endpoint.

### Important normalization note
RPE65 is on the **minus strand**.
So transcript `c.260A>G` maps to genomic GRCh38 `chr1:68444869 T>C`.
Keep that genomic form for tools like SpliceAI.

### Tool recommendation for this demo
For the demo tool, it is reasonable to hardcode:

```text
hgvs = NM_000329.3:c.260A>G
```
