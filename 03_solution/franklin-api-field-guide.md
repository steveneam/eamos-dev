# Franklin / Genoox API Field Guide (v1)

## Why this matters

For the current backend direction, the most valuable Franklin endpoints are:

1. **Parse Variant** — convert messy user/lab variant text into a structured canonical variant
2. **Search Variant** — look up a single variant and retrieve interpretation-oriented annotations
3. **Get WB results** — fetch case/workbench variants with sample-level evidence and classification

These three endpoints map cleanly to the backend workflow:

`input text -> normalize variant -> enrich variant -> build recommendation draft`

---

## 1) POST Parse Variant

**Endpoint:** `https://franklin.genoox.com/api/parse_search`

**Purpose:**
Parse free-text variant input such as HGVS-like notation into a structured variant object.

### Request body
```json
{
  "search_text_input": "vhl:c.293A>C"
}
```

### Response shape
```json
{
  "response_type": "SNP_VARIANT",
  "snp_variants": [...],
  "best_variant_option": {...}
}
```

### Meaning of top-level fields
- `response_type` — what Franklin thinks the parsed thing is, e.g. SNP/CNV-style response lane
- `snp_variants` — all candidate parsed SNP variants matching the input text
- `best_variant_option` — Franklin’s preferred parse to use as the canonical option

### Meaning of variant fields
- `chrom` — chromosome
- `pos` — parsed position in Franklin’s compact representation
- `ref` — reference allele
- `alt` — alternate allele
- `transcripts` — transcript accessions that match the parsed notation
- `canonical_tanscript` — Franklin’s chosen canonical transcript (note: key is misspelled in API response)
- `warnings` — parse ambiguities or caution flags

### `to_full_variant`
This is Franklin’s more explicit normalized genomic object.

- `chrom` — chromosome
- `start`, `end` — genomic interval for the variant
- `ref`, `alt` — alleles
- `is_old` — whether the notation is considered old/legacy
- `reference_version` — genome build such as `HG19`
- `insertion`, `deletion` — structural flags
- `smallest_ref_range_if_applicable` — normalized genomic range metadata
- `variant_type.value` — internal Franklin variant type enum value

### Important caution
The `Parse Variant` response appears to use a more internal/full-range coordinate representation than the simpler `Search Variant` response.
Do **not** assume `pos`, `start`, and `start_position` from other endpoints are interchangeable without validating coordinate semantics first.

### How an AI agent should use this endpoint
Use it as a **normalization step**, not as the final source of truth.

Good uses:
- convert user text into a structured variant key
- choose one canonical transcript for downstream processing
- detect ambiguous/invalid input via `warnings`

Bad uses:
- making clinical claims directly from parse output

---

## 2) GET Search Variant

**Endpoint:** `https://api.genoox.com/v2/search/snp/?search_text=...`

**Purpose:**
Take one variant query string and return an interpretation-oriented enriched variant object.

### Top-level response shape
```json
{
  "variant": {...},
  "annotations": {...},
  "classification": {...},
  "variant_franklin_link": "..."
}
```

### `variant`
This is the normalized variant identity.

- `chromosome` — chromosome
- `start_position` — variant start position
- `end_position` — variant end position
- `ref` — reference allele
- `alt` — alternate allele
- `variation_type` — e.g. `SNP`

### `annotations.transcripts`
Multiple transcript views may be returned.

Each transcript object may include:
- `transcript_type` — source namespace such as `REFSEQ` or `ENSEMBL`
- `gene` — gene symbol
- `region` — genomic context such as `EXONIC` / `OTHER_REGION`
- `effect` — effect class such as `NON_SYNONYMOUS`
- `transcript` — transcript accession
- `hgvc_p` — protein-level HGVS effect
- `hgvc_c` — coding DNA HGVS effect
- `transcripts_count` — number of transcripts affected / available in this context
- `exon_number` — exon index for this transcript mapping
- `transcript_exon_count` — total exon count in transcript
- `closest_exon` — nearest exon index
- `closest_distance_to_exon` — distance to exon boundary / region marker (treat sign convention as Franklin-specific until validated)

### `annotations.frequencies`
Population frequency information.

Possible fields:
- `aggregated_frequency` — Franklin’s combined/summary frequency
- `max_gnomad_frequency` — maximum gnomAD subpopulation frequency
- `exac_frequency.af` — ExAC allele frequency
- `exac_frequency.an` — ExAC allele number
- `onek_frequency` — 1000 Genomes frequency block
- `esp_frequency.af` — ESP allele frequency
- `exome_gnomad_frequency.af` — gnomAD exome frequency
- `genome_gnomad_frequency.af` — gnomAD genome frequency
- similar nested `an` values — allele counts used to compute those frequencies

### `annotations.predictions`
Computational pathogenicity / impact features.

- `dbsnp` — dbSNP rs identifier
- `aggregated_predictions` — Franklin composite prediction score
- `revel` — REVEL missense pathogenicity score
- `fathmm` — FATHMM functional impact score
- `metalr` — MetaLR pathogenicity score
- `genocanyon` — functional potential score
- `gerp` — evolutionary conservation score
- `sift` — SIFT score (lower is generally more damaging)
- `fitcons` — predicted functional consequence score
- `splice_ai` — splice disruption prediction score
- short keys like `mt` / `ma` appear to be Franklin shorthands for prediction tools and should be validated before hard-coding their labels in UI

### `annotations.clinical_evidences`
Evidence buckets from known clinical sources.

- `clinvar.submissions_by_classification[]`
  - `level` — classification bucket such as `PATHOGENIC`, `LIKELY_PATHOGENIC`, `UNCERTAIN_SIGNIFICANCE`
  - `count` — number of submissions in that bucket
- `uniprot` — protein/functional evidence block if available

### `classification`
Franklin’s interpretation summary.

- `acmg_classification` — overall ACMG-style result (e.g. `PATHOGENIC`)
- `acmg_rules[]` — rule-level evidence table
  - `name` — ACMG rule, e.g. `PM2`, `PP3`, `PS4`
  - `is_met` — whether the rule was met
  - `influence` — strength/category of that rule
  - some endpoints also include `weight`

### `variant_franklin_link`
Direct URL to Franklin’s variant page for manual review.

### How an AI agent should use this endpoint
Good uses:
- enrich a normalized variant with transcript/gene/hgvs names
- summarize population rarity
- surface conflicting clinical evidence
- build a draft explanation of why a variant might matter

Bad uses:
- turning raw prediction scores into final clinical advice without disease-specific rules or human review

---

## 3) GET Get WB results

**Endpoint:** `https://api.genoox.com/v1_2/analysis/workbench?analysis_id=...`

**Purpose:**
Return variants already present in a Franklin workbench analysis, including sample-level metrics and richer case/workbench context.

### Top-level response
```json
{
  "variants": [ ... ]
}
```

Docs say this also includes case details, though the example body shown in the docs is dominated by `variants`.

### Each `variants[]` item
#### `variant`
Same identity block as above:
- `chromosome`
- `start_position`
- `end_position`
- `ref`
- `alt`
- `variation_type`

#### `sample_data`
This is case/sample-specific sequencing or call-quality information.

- `confidence_level` — Franklin confidence bucket for the call
- `depth` — total read depth
- `depth_ref` — reference-supporting reads
- `depth_alt` — alternate-supporting reads
- `vaf` — variant allele fraction
- `quality` — variant call quality
- `zygosity` — genotype state such as `HET`
- `gq` — genotype quality
- `pl` — phred-scaled genotype likelihoods

#### `annotations`
Same family as `Search Variant`, but usually richer in case context.

- `transcripts` — transcript-level mappings
- `frequencies` — population frequency evidence
- `predictions` — computational features
- `clinical_evidences` — clinical evidence summaries
- `internal_frequency`
  - `internal_frequency` — occurrence frequency in Franklin’s internal cohort / workspace context
  - `internal_sample_count` — count of internal observed samples

#### `classification`
Similar ACMG block, but the workbench example includes more detail.

- `acmg_classification` — Franklin’s overall classification
- `acmg_rules[]`
  - `name`
  - `weight` — Franklin scoring weight for that rule
  - `is_met`
  - `influence`

#### `priority`
- `score` — Franklin prioritization score for ranking variants inside the case/workbench

#### `variant_franklin_link`
Direct manual-review link to that variant page.

#### `filter_tree_labels.labels[]`
Likely internal/workflow labels used in Franklin filters.

- `label_name` — workflow/filter tag name
- `label_color` — display color

These are useful for analyst workflow context, but not strong clinical evidence by themselves.

### How an AI agent should use this endpoint
This is the best endpoint when you already have a Franklin `analysis_id`.

Good uses:
- get the whole case variant list
- rank candidates by case-specific signal
- read QC + population + evidence + classification in one place
- draft a review summary for a human reviewer

Bad uses:
- blindly trusting `priority.score` as the sole decision-maker
- using internal labels as if they were external clinical evidence

---

## Recommended agent interpretation order

### If input is messy variant text
1. `Parse Variant`
2. choose `best_variant_option`
3. call `Search Variant`
4. add external/disease-specific rules
5. produce draft for clinician review

### If input is a Franklin analysis/case
1. `Get WB results`
2. filter/rank variants
3. extract strongest transcript + evidence + classification
4. apply disease/referral rule layer
5. produce clinician-review draft

---

## What not to over-trust

Do not let the agent treat these as stand-alone truth sources:
- raw pathogenicity scores
- single prediction tools
- internal filter labels
- ACMG result without disease-specific context
- coordinate fields without validating genome build and positional semantics

---

## Best practical use in the project

For this hackathon, Franklin is strongest as:
- an **upstream structured evidence source**,
- a **variant normalization/search layer**,
- and a **case/workbench source** if access exists.

It should feed a narrower disease/referral decision workflow rather than becoming the whole product.

---

## Demo-case mapping: `RPE65 c.260A>G`

For the current demo case, the clean Franklin conversion is:

### Normalization request
```http
POST https://franklin.genoox.com/api/parse_search
Content-Type: application/json

{
  "search_text_input": "RPE65:c.260A>G"
}
```

Observed parse result:
- transcript -> `NM_000329`
- normalized genomic form -> `chr1:68910552 T>C` on `HG19`

### Enrichment request
```http
GET https://api.genoox.com/v2/search/snp/?search_text=RPE65:c.260A%3EG
Authorization: Bearer <FRANKLIN_TOKEN>
```

Important:
- the richer Franklin search endpoint requires auth
- the UI notions of `reference = hg38` and `type = germline` were **not** confirmed here as public query parameters for this endpoint
- treat those as tool assumptions or post-fetch constraints unless your Franklin tenant exposes a more specific endpoint

### Tool recommendation for this demo
For the demo tool, it is reasonable to hardcode:

```text
search_text = RPE65:c.260A>G
```

and then:
1. use `parse_search` if you need normalization,
2. use the authenticated `v2/search/snp` endpoint for interpretation-oriented evidence.
