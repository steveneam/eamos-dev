# ClinVar Guide (ESearch/ESummary + Practical Use)

## Goal

Use ClinVar as a second evidence source for variant interpretation.

**Interpretation rule:** ClinVar helps provide:
- clinical classification snapshots
- evidence breadth (how much has been submitted)
- trait/gene links and location context

It is not a final decision engine.

---

## Method A (recommended for hackathon): NCBI E-utilities

### 1) Find variant candidates

**Endpoint:**
`GET https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=clinvar&term=...&retmode=json`

Search terms can be:
- `BRCA1[gene]`
- `NM_007294.4(BRCA1):c.1974G>C[p.Met658Ile][gene]`
- `VCV000054425[accession]`
- `rsid[uid]` style variations

**What it returns:**
- `esearchresult.count`
- `idlist` (ClinVar variation IDs)

**Use case for backend:**
- resolve user input into one or more candidate ClinVar IDs.

---

### 2) Fetch per-variant summary records

**Endpoint:**
`GET https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=clinvar&id={clinvar_id}&retmode=json`

Replace `{clinvar_id}` with one from step 1.

**Typical important fields** (`result[<id>]`):
- `accession`, `accession_version` (e.g., `VCV000054425`, versioned)
- `title` (human readable variant label)
- `obj_type` (single nucleotide variant / indel / etc.)
- `genes[]`
  - `symbol`, `geneid`, `strand`, `source`
- `variation_set[]`
  - `variation_loc[]` with chromosome/position/build and change boundaries
  - `variation_name`, `cdna_change`, `aliases`
  - `allele_freq_set[]` with source+value
- `germline_classification`
  - `description` (e.g., Pathogenic)
  - `review_status` (e.g., criteria provided, single submitter)
  - `last_evaluated`
  - `trait_set[]` (linked conditions)
- `oncogenicity_classification` / `clinical_impact_classification`
- `supporting_submissions`
  - `scv` / `rcv` IDs (submission IDs)
- `molecular_consequence_list` (e.g., frameshift, intron)

**Example (partial) JSON shape:**
```json
{
  "accession": "VCV004818740",
  "title": "NM_007294.4(BRCA1):c.3896_3912delinsTGC (p.Gln1299fs)",
  "obj_type": "Indel",
  "genes": [{"symbol":"BRCA1","geneid":"672","strand":"-","source":"submitted"}],
  "variation_set": [
    {
      "variation_name": "NM_007294.4(BRCA1):c.3896_3912delinsTGC (p.Gln1299fs)",
      "variation_loc": [{"chr":"17","start":"4309...","assembly_name":"GRCh38","status":"current"}],
      "allele_freq_set": [{"source":"gnomAD","value":"0.00005"}]
    }
  ],
  "germline_classification": {
    "description": "Pathogenic",
    "review_status": "criteria provided, single submitter",
    "last_evaluated": "2026/01/29 00:00",
    "trait_set": [{"trait_name":"Inherited breast and ovarian cancer susceptibility"}]
  }
}
```

**AI interpretation guidance:**
- treat `description` as **strength category**, not diagnosis
- count evidence from `supporting_submissions` and review status
- if multiple entries disagree, surface it explicitly.

---

## Method B: Bulk data (for speed/stability)

If API is flaky, use ClinVar release files (monthly/weekly) downloaded from NCBI distribution.

Workflow:
1. pull release file (local cache)
2. preload relevant records for your target diseases into a local index
3. query by:
   - gene symbol
   - variation name pattern
   - canonical ClinVar accession

This avoids live API failure and is easier for repeatable hackathon demos.

---

## Data interpretation playbook for AI agent

### Before use
- Validate variant is mapped to the same genome build used by your system (usually GRCh38 in VEP pipeline).
- Ensure one-to-one or one-to-many mapping is handled.

### In workflow
- `germline_classification.description` -> classification label for explanation
- `review_status` -> confidence/quality tier
- `trait_set` -> disease context
- `variation_set.variation_loc` + `genes` -> genomic/clinical alignment check
- `allele_freq_set` -> rarity context (not alone causality)

### For ranking
Prefer a conservative score, e.g.
- pathogenicity_class_count
- review status confidence tier
- number of supporting submissions

But never use raw ClinVar labels as sole decision trigger.

### For prompt generation
Use strict format:
- "ClinVar (last evaluated: date): Germline classification = X, review status = Y"
- if low confidence: append "conflicting evidence / limited submitters".

---

## Common gotchas

- esummary fields can vary by record type (`obj_type`), so code defensively.
- Some IDs return minimal records.
- Allele frequency fields can be duplicate/overlapping; dedupe as needed.
- Always include an explicit fallback: "ClinVar evidence not available for this exact variant".

---

## Minimal query pattern you can copy

```bash
# 1) Search
curl 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=clinvar&term=BRCA1[gene]&retmode=json&retmax=5'

# 2) Pull summary
curl 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=clinvar&id=4818740&retmode=json'
```

---

## Recommended API policy in this project

1. Keep ClinVar in the **evidence layer**.
2. Cache responses for demo cases.
3. Tag all outputs with `source: ClinVar` and `timestamp`.
4. Never let ClinVar override rule-based referral logic without clinician review.

---

## Demo-case mapping: `RPE65 c.260A>G`

For the current demo case, the clean ClinVar conversion is:

### Search once
```http
GET https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=clinvar&term=RPE65%5Bgene%5D%20AND%20c.260A%3EG&retmode=json&retmax=1
```

Observed resolution:
- `idlist[0] = 1421454`

### Stable summary fetch
```http
GET https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=clinvar&id=1421454&retmode=json
```

### Useful fields for this case
- `title` -> `NM_000329.3(RPE65):c.260A>G (p.Asp87Gly)`
- `genes[0].symbol` -> `RPE65`
- `protein_change` -> `D87G`
- `obj_type` -> `single nucleotide variant`
- `molecular_consequence_list[0]` -> `missense variant`
- `germline_classification.description` -> `Uncertain significance`
- `germline_classification.trait_set[].trait_name` ->
  - `Leber congenital amaurosis 2`
  - `Retinitis pigmentosa 20`

### Tool recommendation for this demo
For the demo tool, it is reasonable to hardcode:

```text
clinvar_id = 1421454
```

and call `esummary` directly, instead of re-searching every time.
