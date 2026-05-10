# SpliceAI Guide (API + Practical Use)

## Goal

Use SpliceAI as a **supporting splice-effect predictor** inside the evidence layer.

Best use:
- intronic or near-splice variants
- non-obvious splice-impact questions
- adding one more signal before drafting a recommendation

Do **not** use it as a final clinical decision engine by itself.

---

## Public API path we can call

The most practical public path is the Broad SpliceAI lookup service.

### Base URLs
- GRCh37:
  - `https://spliceai-37-xwkwwwxdwq-uc.a.run.app/spliceai/`
- GRCh38:
  - `https://spliceai-38-xwkwwwxdwq-uc.a.run.app/spliceai/`

### Query format
`GET /spliceai/?hg=<37|38>&variant=<chrom-pos-ref-alt>&distance=<n>&mask=<0|1>`

Example:
```text
https://spliceai-38-xwkwwwxdwq-uc.a.run.app/spliceai/?hg=38&variant=chr8-140300616-T-G&distance=50&mask=1
```

### Required parameters
- `hg` — genome build (`37` or `38`)
- `variant` — variant in `chrom-pos-ref-alt` format

### Optional parameters
- `distance` — model search window distance
- `mask` — `0` = raw scores, `1` = masked scores

**Important note:**
The public README describes `distance` default as `50`, but observed live responses can return a different implicit value if you omit it. For reliability, **always set `distance` explicitly**.

---

## Example response shape

Observed live response for:
`?hg=38&variant=chr8-140300616-T-G&distance=50&mask=1`

```json
{
  "distance": 50,
  "variant": "chr8-140300616-T-G",
  "hg": "38",
  "mask": 1,
  "genomeVersion": "38",
  "chrom": "8",
  "pos": 140300616,
  "ref": "T",
  "alt": "G",
  "scores": [
    {
      "DS_AG": "0.04",
      "DS_AL": "0.83",
      "DS_DG": "0.00",
      "DS_DL": "0.00",
      "DP_AG": -32,
      "DP_AL": -2,
      "DP_DG": 43,
      "DP_DL": -2,
      "g_id": "ENSG00000167632.19",
      "g_name": "TRAPPC9",
      "t_id": "ENST00000438773.4",
      "t_priority": "MS",
      "t_refseq_ids": ["NM_001160372.4"],
      "t_strand": "-",
      "t_type": "protein_coding"
    }
  ]
}
```

---

## What the JSON fields mean

### Top-level fields
- `variant` — original query variant string
- `hg` / `genomeVersion` — genome build used by the model
- `chrom`, `pos`, `ref`, `alt` — parsed variant identity
- `distance` — search window used by the model
- `mask` — whether masked or raw interpretation mode was used
- `scores[]` — one row per transcript/gene-context result

### Main `scores[]` fields
#### Delta score fields
- `DS_AG` — delta score for **acceptor gain**
- `DS_AL` — delta score for **acceptor loss**
- `DS_DG` — delta score for **donor gain**
- `DS_DL` — delta score for **donor loss**

These are the main splice-impact outputs.
Higher values generally mean **stronger predicted splice disruption / creation effect**.

#### Delta position fields
- `DP_AG`
- `DP_AL`
- `DP_DG`
- `DP_DL`

These indicate the predicted position offset of the splice event relative to the variant.
Treat them as **model-relative offsets**, not a simple exon number.

#### Transcript / gene identity fields
- `g_id` — Ensembl gene id
- `g_name` — gene symbol
- `t_id` — Ensembl transcript id
- `t_refseq_ids[]` — linked RefSeq transcript ids
- `t_priority` — transcript priority marker from the service
- `t_type` — transcript biotype
- `t_strand` — strand orientation

#### Transcript structure fields
- `EXON_STARTS[]`
- `EXON_ENDS[]`
- `CDS_START`
- `CDS_END`
- `EXON_FRAMES[]`

These are useful for debugging and transcript context, but they are usually **not** needed in the main product response.

#### Other score-detail fields
- `DS_AG_REF`, `DS_AL_REF`, `DS_DG_REF`, `DS_DL_REF`
- `DS_AG_ALT`, `DS_AL_ALT`, `DS_DG_ALT`, `DS_DL_ALT`

These separate reference-vs-alt score components.
They are useful for deeper analysis, but not required in the first UI.

- `SCORES_FOR_INSERTED_BASES`
  - relevant for insertion-style cases
  - can often be ignored in v1 unless the lane depends on insertions

---

## How an AI agent should use SpliceAI

### Good uses
- add splice-impact evidence for intronic / splice-region variants
- rank whether a variant deserves closer splice-focused review
- support draft wording like:
  - "model predicts strong acceptor loss"
  - "splice effect signal is weak / absent"

### Bad uses
- making final referral decisions from SpliceAI alone
- calling a variant pathogenic solely from a high delta score
- presenting the output as clinician-final truth

---

## Recommended adapter output

Do not expose the whole raw response everywhere.
Normalize it into something compact like:

```python
class SpliceAiTranscriptScore(BaseModel):
    gene_symbol: str | None = None
    transcript_id: str | None = None
    refseq_ids: list[str] = []
    acceptor_gain: float | None = None
    acceptor_loss: float | None = None
    donor_gain: float | None = None
    donor_loss: float | None = None
    top_delta_score: float | None = None
    priority: str | None = None

class SpliceAiEvidence(BaseModel):
    variant: str
    genome_build: str
    distance: int
    mask: int
    top_transcript: SpliceAiTranscriptScore | None = None
    max_delta_score: float | None = None
    evidence_note: str | None = None
```

---

## Practical project recommendation

For this project, use SpliceAI as:
- **a secondary evidence provider after VEP**,
- especially when the variant could affect splicing,
- with fixture caching for demo stability.

### Safe call pattern
1. normalize variant
2. call VEP
3. if splice-region / intronic suspicion exists, call SpliceAI
4. merge into evidence bundle
5. feed summary into deterministic rules + draft layer

---

## Operational cautions

- The public service is meant for **interactive use**, not batch processing.
- Expect rate limiting if you hit it heavily.
- For demos or repeated tests, cache known responses.
- If this becomes core to the workflow, consider running a local containerized instance.
- Always set both `distance` and `mask` explicitly.

---

## Best default settings for this app

Unless the lane needs something else:
- `hg=38`
- `distance=50`
- `mask=1` for interpretation-facing outputs

If you want raw exploratory analysis later, use `mask=0` separately.

---

## Demo-case mapping: `RPE65 c.260A>G`

SpliceAI cannot take the transcript HGVS string directly.
For this demo case, first normalize to the genomic GRCh38 form.

Important:
- `RPE65` is on the **minus strand**
- transcript `c.260A>G` becomes genomic `chr1:68444869 T>C`

### Request that matches the desired demo result
```http
GET https://spliceai-38-xwkwwwxdwq-uc.a.run.app/spliceai/?hg=38&variant=chr1-68444869-T-C&distance=500&mask=0
```

### Result fields to read
From `scores[0]`:
- `DS_AL` -> `0.12` -> Acceptor loss
- `DS_DL` -> `0.04` -> Donor loss
- `DS_AG` -> `0.00` -> Acceptor gain
- `DS_DG` -> `0.00` -> Donor gain

### Important note
If you use `mask=1` for this case, the donor-loss signal is masked to `0.00`.
If you send `A>G` instead of genomic `T>C`, you will not get the intended result.

### Tool recommendation for this demo
For the demo tool, it is reasonable to hardcode:

```text
hg = 38
variant = chr1-68444869-T-C
distance = 500
mask = 0
```
