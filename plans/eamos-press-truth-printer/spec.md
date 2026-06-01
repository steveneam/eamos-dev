# `eamos_press` — backend truth-printer / claim-provenance debugger

**Status:** contract design (Claude, 2026-06-01) — *for Codex review before backend implementation.*
**Owner of contract:** Claude (frontend-facing / report "claim" semantics).
**Owner of implementation:** Codex (backend, `app/backend/app/cli/eamos_press.py`).
**Lane:** read-only debug/QA layer. **Not** a new UI surface, **not** a new product endpoint.

---

## 1. Why this exists (the motivating bug)

The landing "Try" chip `USH2A c.2276G>T` runs a live report. Its **Population
Frequency** call-card pill currently renders:

> **Low Frequency (0.182% max AF)**  ·  badges: `PM2` · `Max AMR: 0.182%` · `AC 2357`

`PM2` means *"absent or rare in population databases."* But the authoritative
source for this variant — the **ClinGen Hearing Loss VCEP** worksheet
(expert-panel reviewed) — asserts the **opposite**:

> `BS1` **met** (`assertion_level: vcep_specified`): *"The filtering allele
> frequency … in the Latino population in gnomAD is 0.17% … meets the threshold
> … for considering strong evidence against pathogenicity (BS1)."*

The card's **own** gnomAD facts corroborate `BS1`, not `PM2`: joint AF 0.146%,
popmax (amr) 0.182%, **AC 2357**, AN 1.61M, **5 homozygotes**. 0.182% is ~18×
the PM2 frequency threshold (0.0001), and PM2 in recessive disease expects ~no
homozygotes.

**The pill states the opposite of the source.** Today this is only catchable by
a human who happens to open the ClinGen rationale. We need a backend
**truth-printer** that, for any variant, prints each pill/report claim next to
the exact source facts that justify it, classifies the claim's support level,
and **fails an assertion** when a claim is contradicted or unsupported — *before*
more UI polish.

This is not a one-off USH2A fix. It is the QA harness that makes "every pill is
source-backed" a testable invariant.

---

## 2. What it prints (per the ask)

For a variant (e.g. `USH2A:c.2276G>T`), for each section's pills/claims:

1. **Generated pill/report text** — exactly as the UI renders it (primary label
   + badges + meta line), pulled from the assembled `ReportPayload`.
2. **Source facts used for each claim** — the specific evidence values the claim
   was (or should have been) derived from.
3. **Source status** — `live` · `cache` · `fixture` · `missing` · `stale`
   (+ pass-through `fallback`/`degraded`/`error`/`failed`).
4. **Provenance IDs / URLs** — gnomAD variant URL, ClinVar/ClinGen accession,
   **PMIDs**, **NCT IDs**, source query strings.
5. **Claim level** — `variant_specific` · `gene_level` · `disease_level` ·
   `unsupported`.
6. **Warnings** — when a pill overclaims, is contradicted by its own source, or
   lacks direct support.

---

## 3. Command shape (matches existing `app/backend/app/cli/*` conventions)

```
python -m app.cli.eamos_press "USH2A:c.2276G>T" \
  --sections pills,popfreq,publications,trials \
  --explain-pill \
  --assert-source-backed-pills \
  --compact
```

Conventions mirror `eamos_search_input.py`: `argparse`,
`prog="python -m app.cli.eamos_press"`, positional query (quote if spaced),
`main(argv) -> int`, JSON via `json.dumps(..., indent=None if compact else 2,
sort_keys=True)`, settings via `get_settings()`.

| Flag | Default | Effect |
| ---- | ------- | ------ |
| `query` (positional) | — | Variant text. Accepts `GENE:c.x`, `GENE c.x`, rsID, genomic. Reuses `parse_search_text` / the search-input resolver. |
| `--sections a,b,c` | `pills,popfreq,publications,trials` | Comma list. Section keys in §5: `pills`, `popfreq`, `publications`, `trials`, `clinical` (ClinVar+ClinGen consensus), `acmg`, `disease` (MONDO/OMIM/inheritance/penetrance), `gene` (gene-level metrics), `protein` (protein metrics/domains). `all` = every implemented section. |
| `--explain-pill` | off | Expand each claim with the full `source_facts` block + the derivation note (which fact → which clause of the rendered text). Off = headline verdict only. |
| `--assert-source-backed-pills` | off | Turn the report into a test: **exit 2** if any selected claim is `unsupported` or `contradicted`. Exit 0 otherwise. (See §6.) |
| `--assert-no-overclaim` | off | Softer gate: exit 2 only on `contradicted` claims (an explicit, labeled `gene_level` claim under a variant does **not** fail). |
| `--compact` | off | Compact JSON instead of indented. |
| `--gene` / `--transcript` / `--protein` | — | Disambiguators when the query text omits them (same as `eamos_search_input`). |
| `--base-url URL` | — | Degraded mode: read an already-deployed report over HTTP instead of running in-process. Only payload-visible facts are available (no raw ACMG worksheet → contradiction checks that need the worksheet downgrade to `unverifiable`, never silently pass). |
| `--refresh` | off | Bypass source cache (forces `live` where `USE_REAL_APIS`). |

**Execution model (recommended): in-process.** Run the lookup orchestrator and
**tap** three objects it already produces — `report_payload`, `evidence_map`,
`evidence_statuses` — then evaluate claims against them. This is required because
the decisive fact for the USH2A bug (the ClinGen `acmg_worksheet` criteria with
`assertion_level`) lives in `evidence_map`, **not** in `ReportPayload`. The
`--base-url` path is a fallback that sees only what the JSON payload exposes.

> **Codex decision point:** expose the orchestrator's `(report_payload,
> evidence_map, evidence_statuses)` to the CLI via a thin in-process entry
> (preferred), **or** add a debug-only `?debug=evidence` projection to the
> existing lookup route. Do not fabricate a parallel evidence path — reuse the
> one `/report` already runs through, so the CLI verifies *what users see*.

---

## 4. Output schema (frontend-facing / debug contract)

Top level:

```jsonc
{
  "query": "USH2A:c.2276G>T",
  "resolved": { "gene": "USH2A", "transcript_hgvs": "c.2276G>T",
                "protein_change": "p.Cys759Phe", "variant_id": "1-216247118-C-A",
                "genomic_hg38": "1-216247118-C-A" },
  "mode": "in_process" | "http",
  "source_statuses": { "gnomad": "cache", "clingen": "cache", ... },
  "sections": [ Section, ... ],
  "summary": { "claims_total": 9, "variant_specific": 4, "gene_level": 3,
               "unsupported": 2, "contradicted": 1, "unverifiable": 0 },
  "assert": { "mode": "source_backed_pills", "passed": false,
              "failed_claim_ids": ["popfreq.pm2_badge", "trials.NCT05919342"] }
}
```

Each `Section`:

```jsonc
{
  "section": "popfreq",
  "title": "Population Frequency",
  "source_status": "cache",
  "claims": [ Claim, ... ]
}
```

Each `Claim` — the core record:

```jsonc
{
  "claim_id": "popfreq.pm2_badge",
  "rendered_text": "PM2",                  // the exact string the UI shows
  "rendered_in": "call_card.support_badge",// where on the page it appears
  "claim_kind": "acmg_frequency_code",     // typed claim (see §5 per section)
  "claim_level": "unsupported",            // variant_specific|gene_level|disease_level|unsupported
  "verdict": "contradicted",               // supported|downgraded|unsupported|contradicted|unverifiable
  "source_facts": [                        // shown fully under --explain-pill
    { "source": "clingen_vcep_worksheet", "field": "BS1.state", "value": "met",
      "assertion_level": "vcep_specified",
      "note": "VCEP asserts BS1 (freq too HIGH) — strong benign on the freq axis" },
    { "source": "gnomad", "field": "popmax_frequency", "value": 0.001817,
      "note": "0.182% >> PM2 threshold 0.0001 (~18x)" },
    { "source": "gnomad", "field": "homozygote_count", "value": 5,
      "note": "PM2 in recessive disease expects ~0 homozygotes" }
  ],
  "provenance": [
    "ClinGen ERepo accession 3b9c6310-…",
    "https://gnomad.broadinstitute.org/variant/1-216247118-C-A?dataset=gnomad_r4"
  ],
  "warnings": ["pill_claim_contradicts_source:PM2_vs_BS1"]
}
```

`verdict` ladder (drives assertions):

| verdict | meaning | `--assert-source-backed-pills` | `--assert-no-overclaim` |
| ------- | ------- | :---: | :---: |
| `supported` | claim backed by a variant-keyed fact | pass | pass |
| `downgraded` | claim is real but only gene/disease-level support exists, **and the text honestly says so** | pass | pass |
| `unsupported` | no backing fact (e.g. trial row with `matched_terms: []`) | **fail** | pass |
| `contradicted` | a source fact asserts the opposite (PM2 vs BS1) | **fail** | **fail** |
| `unverifiable` | needed fact not reachable in current mode (e.g. `--base-url` can't see the worksheet) | pass (but counted) | pass |

---

## 5. Section inventory — the signal already exists in the payload

The report already computes most of what the truth-printer needs. `eamos_press`
*collates and asserts*; it does not recompute evidence. Mapping:

### 5a. `pills` (the four call cards) — `report_payload.call_cards.cards[]`
Source: `app/backend/app/services/report_call_cards.py`.
- Per card already present: `primary_label`, `support_badges[].text/kind`,
  `source_status`, `provenance[]`, `warnings[]`, `ui_color_theme`.
- **Claims to extract per card:** (1) `primary_label` (the verdict word), (2)
  each ACMG `support_badge` (`PM2`/`BS1`/`PP3`/`PS3_Supporting`/…), (3) each
  metric badge (`AC 2357`, `Max AMR: 0.182%`).
- **Binding for ACMG-code badges:** resolve against
  `evidence_map["clinical_consensus"]["acmg_worksheet"].criteria[]` —
  `{code, state, assertion_level, rationale}`. A displayed ACMG code is:
  - `supported` if a worksheet row has `code == X, state == met`;
  - **`contradicted`** if the worksheet asserts the *opposing* code on the same
    axis as `met` (frequency axis: `{PM2}` vs `{BS1, BA1}`; computational axis:
    `{PP3}` vs `{BP4}`) — **this is the USH2A PM2-vs-BS1 case**;
  - **`unsupported`** if no worksheet row carries the code at any allowed level
    (note: today `report_call_cards._first_acmg_badge_from_consensus` only
    accepts `assertion_level in {source_asserted, eamos_hint}` — so a
    `vcep_specified` BS1 is silently dropped and an Eamos-hinted PM2 can leak
    through; the truth-printer must read **all** assertion levels and label the
    leak rather than inherit the filter).
  - `eamos_hint`-derived codes must be labeled `claim_source: eamos_hint`, never
    presented as if source-asserted.
- **Lab & Functional card — dual-badge: curator sets the verdict, Eamos counts
  the volume (full design `plans/functional-card/spec.md`).** Three separated
  elements; the truth-printer asserts each:
  - **Verdict (primary label + ACMG badge):** must be **curator-sourced**
    (ClinGen → ClinVar). `functional_evidence.py` already enforces this (PubMed
    hits carry no PS3/BS3), so the truth-printer's job is to **verify the
    invariant holds in the deployed build**: `functional_verdict_not_curator_
    sourced` → `contradicted` if any displayed PS3/BS3 ever traces to a
    PubMed-only hit. State ∈ {strong_deficit, emerging_deficit, normal, conflict,
    uncurated, none}; `conflict`/`uncurated` are honest non-classifications, not
    Eamos verdicts.
  - **Volume badge (count):** the deduped 3-stream aggregate (ClinGen evidence
    PMIDs ∪ ClinVar citation PMIDs ∪ PubMed functional-keyword search) —
    `claim_kind: functional_study_count`, `claim_level: variant_specific`,
    `verdict: supported`. Flag `count_not_three_stream_aggregate` if it is a
    single-source value; the count must NEVER drive the verdict or the PS3
    strength (Strong vs Supporting is the curator's, not the count's).
  - **Colour** tracks the functional state (red/green/yellow/blue/grey), NOT the
    overall ClinGen pathogenicity. Source attribution (`via ClinGen` / `via
    ClinVar`) must be present on any PS3/BS3 badge — it is the provenance.
  - USH2A:c.2276G>T → expected **conflict** (reduced-penetrance hypomorph, no
    VCEP functional PS3/BS3); the truth-printer prints which sources/papers set
    the state so a v1 `uncurated` landing (missing per-paper direction) is
    surfaced, not papered over.

### 5b. `popfreq` — `report_payload.population_frequency_detail`
Source: `report_call_cards.build_population_frequency_detail` + gnomAD summary.
- Facts already present: `allele_frequency`, `allele_count`, `allele_number`,
  `homozygote_count`, `popmax_frequency/population`, per-`genetic_ancestry_groups`
  `af/ac/an/hom`, `dataset`, `sequencing_type`, `flags`, `source_url`.
- **Claims:** the `primary_label` band (`Absent`/`Rare`/`Low Frequency`/`Common`/
  `Very Common`) and the `PM2/BS1/BA1` frequency badge.
- **Checks:**
  - Band-vs-data: `Low Frequency` uses `max(af, popmax)` = 0.182%, but the **amr
    joint group is 0.212%** — `max_af` understates grpmax. Emit
    `band_max_af_understated` (informational, not a fail).
  - **PM2/BS1/BA1 vs gnomAD numbers** + **vs worksheet** (see 5a). This is where
    the USH2A `contradicted` verdict fires.
  - `homozygote_count > 0` while a rarity code (`PM2`) is shown → contributing
    warning `rarity_code_with_homozygotes`.

### 5c. `publications` — `report_payload.pubmed_articles[]` + `publications_callout`
Source: `app/backend/app/services/publication_literature.py`.
- Facts already present per article: `pmid`, `snippet_status`
  (`exact_variant_snippet` / `gene_only_no_variant` / `abstract_only_no_variant`
  / `reported_in_litvar2_no_text` / …), `snippets[].matched_terms`,
  `source_tags` (`litvar2`/`pubmed`/`clinvar`/`clingen`). Headline:
  `publications_callout.scope_counts.{variant,gene}` with `count_kind` + `query`.
- **Claims & levels:**
  - Headline count "190 publications" → `count_kind: deduped_pmids`, scope
    `variant`, but it is a **litvar2** variant-scope count (`source_breakdown:
    {litvar2:190, pubmed:8}`). Claim level `variant_specific` **only if** labeled
    as litvar2 variant-scope; emit `headline_count_source:litvar2` so the UI
    can't imply "190 hand-read variant papers."
  - Per displayed article: `exact_variant_snippet` → `variant_specific`;
    `gene_only_no_variant` → `gene_level` (must not be shown as if it discusses
    the variant); `*_no_text` → `unverifiable` with the source tag as provenance.
  - **Provenance must include PMIDs** and the exact `query` string used.

### 5d. `trials` — `report_payload.report_profile.therapies_trials`
Source: `app/backend/app/tools/clinical_trials.py`.
- Facts already present per row: `nct_id`, `match_level`
  (`variant_level`/`gene_level`/`disease_level`/`unavailable`), `matched_terms`,
  `warnings` (`…discovery_only…`, `…gene_level_match…`), section `warnings`
  (`clinical_trials_variant_level_not_found`, `…using_lower_match_level`).
- **Claims & levels:**
  - Row `match_level` maps straight to `claim_level`. USH2A: **all rows
    `gene_level`** → every trial claim is `gene_level`, none `variant_specific`.
  - **`matched_terms == []` → `unsupported`** (`match_without_matched_terms`).
    USH2A surfaces NCT05919342 ("…earlY Heart Failure…"), NCT07529860 ("AI-based
    Echocardiography…"), NCT05705869 — **cardiac trials with empty matched_terms
    under a retinal variant.** These must fail `--assert-source-backed-pills`.
  - Provenance = NCT IDs + the ClinicalTrials.gov query term + the discovery-only
    disclaimer.

### 5e. `clinical` — ClinVar + ClinGen consensus
Source: `report_call_cards._clinical_consensus_card`, `report_payload.acmg_classification` (text snapshot), `report_profile.acmg_worksheet.{classification, classification_source}`, `evidence_map["clinvar"|"clingen"]`.
- Facts present: `classification`, `review_status`, `accession`, `conditions`,
  `classification_source` (`ClinGen` vs `ClinVar`), `submitter_counts` (ClinVar).
- **Claims:** the "Pathogenic" verdict word + the `ClinGen/VCEP: reviewed by
  expert panel` / `ClinVar: <review_status>` badge + the accession.
- **Checks / claim level:** all `variant_specific` (keyed to VCV / ERepo
  accession). Verdict `supported` when the displayed classification ==
  `acmg_worksheet.classification` **and** the badge's `classification_source`
  matches the accession's namespace. **Flag `source_label_mismatch`** if a card
  says "ClinGen/VCEP" but the accession is a ClinVar VCV (or vice-versa) — the
  two are conflated today (`_clinical_consensus_card` falls back ClinGen→ClinVar
  silently). USH2A: classification `Pathogenic`, source `ClinGen` (expert panel)
  → `supported`. The `acmg_classification` *text snapshot* ("ClinVar currently
  lists … Pathogenic") must declare which source it quoted (it says ClinVar while
  the worksheet source is ClinGen — emit `consensus_source_drift` for review).

### 5f. `acmg` — the structured criteria layer
Source: `report_profile.acmg_worksheet.criteria[]` = `{code, state, strength,
assertion_level, rationale, source, evidence_refs[]}`; also the (currently empty)
`report_payload.acmg_criteria_scaffold`.
- **This is the authoritative ACMG truth and the de-conflictor for every ACMG
  badge elsewhere.** There are *four* ACMG representations in play —
  (1) call-card `support_badges`, (2) `report_profile.acmg_worksheet.criteria`,
  (3) `acmg_criteria_scaffold` (empty here), (4) the raw ClinGen
  `expert_panel.criteria` in `evidence_map` (where BS1 carries
  `assertion_level: vcep_specified`). The `acmg` section **lists every applied
  code once** with its strength + `assertion_level` + `evidence_refs`, then every
  ACMG-code claim in §5a binds back to it.
- **Checks:**
  - `badge_not_in_worksheet` — a call-card ACMG badge with no matching criterion
    (the USH2A `PM2` leak: `PM2` is shown but the worksheet's frequency axis row
    is `BS1 met`, not `PM2`).
  - `worksheet_code_dropped_by_badge_filter` — a `met` criterion the call-card
    filter hides because its `assertion_level` isn't in
    `{source_asserted, eamos_hint}` (the `vcep_specified` BS1).
  - `assertion_level` must always be surfaced; an `eamos_hint` code may never be
    rendered as if `source_asserted` / `vcep_specified`.
  - `rationale_is_placeholder` — several USH2A criteria carry the templated
    rationale "Population-frequency criterion summarized without raw source
    metrics…"; flag so QA knows the displayed rationale isn't the real VCEP text.
  - `evidence_refs` are provenance: accessions + PMIDs the code rests on.

### 5g. `disease` — MONDO / OMIM / inheritance / penetrance
Source: `report_profile.disease_mechanism` = `{primary_condition, disease_ids[],
inheritance, penetrance, gene_disease_validity, mechanism, provenance, warnings}`;
`report_payload.associated_conditions`.
- **Claim level = `disease_level`** by definition (these describe the disease,
  not the variant).
- **Checks:** when `disease_ids == []` / `primary_condition == null` (USH2A's
  current state) the section reports `missing` — it must **not** let downstream
  prose imply a named disease that has no resolved MONDO/OMIM ID. Surface the
  pre-existing honesty warning `penetrance_not_source_backed` verbatim. Each
  disease ID (MONDO:…, OMIM:…, Orphanet:…) is its own provenance entry with its
  resolver source (HGNC/gene_disease). `gene_disease_validity` (ClinGen GenCC)
  is a `disease_level` claim with its own source URL.

### 5h. `gene` — gene-level metrics
Source: `report_profile.gene_context_snapshot` (`gene_length`, `cds_length`,
`protein_length`, `ensembl_gene_id`, `exons[]`, `strand`, `chromosome`) +
`molecular_context.{loeuf, clingen_haploinsufficiency, overlapping_cnvs}`.
- **Claim level = `gene_level`.** LOEUF / pLI / haploinsufficiency describe the
  gene's constraint, never the variant.
- **Checks:** `gene_context_snapshot.source_status` is `missing` for USH2A and
  most fields are null → report `missing`, never interpolate a gene length or
  constraint score. A constraint claim shown without a backing `loeuf`/`pli`
  value → `unsupported`. Provenance = Ensembl gene ID + gnomAD constraint URL.

### 5i. `protein` — protein metrics & domains
Source: `molecular_context.{protein_position, codon_change, domain, hotspot_flag,
protein_domain_track}` + protein annotation (Pfam/UniProt) when present.
- **Claim level:** `variant_specific` for the residue claim (position 759,
  TGC>TTC → Cys→Phe), `gene_level` for the domain track.
- **Key USH2A catch — `protein_change_derivable_not_surfaced`:**
  `molecular_context` resolves `protein_position: 759` and `codon_change:
  TGC>TTC` (i.e. p.Cys759Phe), yet `variant_summary_rows[0].protein_change` and
  `gene_context_snapshot.variant.hgvs_p` are `null`. The header pill therefore
  omits the protein change that the evidence already knows — and the literature
  matcher loses the `p.Cys759Phe` / `C759F` aliases that drive
  `exact_variant_snippet` hits. The truth-printer flags the inconsistency between
  two payload fields derived from the same evidence. `domain`/`hotspot_flag` are
  `null` here → no domain/hotspot claim may be asserted (`missing`).

> Order follows the ask: `pills, popfreq, publications, trials` first, then
> `clinical, acmg, disease, gene, protein`. All reuse the identical `Claim`
> shape; `--sections all` runs every one.

---

## 6. Acceptance criteria → how this contract meets them

| Ask | Mechanism |
| --- | --------- |
| `USH2A:c.2276G>T` exposes the inaccurate pill claim clearly | `popfreq.pm2_badge` claim → `verdict: contradicted`, `source_facts` show VCEP `BS1 met` + gnomAD popmax 0.182% + 5 hom, `warnings:[pill_claim_contradicts_source:PM2_vs_BS1]`. Visible in plain `--explain-pill` output. |
| Unsupported/overbroad pill text **fails an assertion**, not just a visual review | `--assert-source-backed-pills` → **exit 2**; `assert.failed_claim_ids` lists `popfreq.pm2_badge` (contradicted) + the 3 empty-`matched_terms` trial rows (unsupported). Wire into pytest as a regression: `assert main([...]) == 2` today; the fix flips it to `0`. |
| Publications & trials show exact query/match reason + variant-vs-gene/disease level | Each pub claim carries `snippet_status` + `matched_terms` + `query`; each trial claim carries `match_level` + `matched_terms` + NCT query term. `claim_level` field is explicit. |
| Keep it a debugging/truth-printer layer, not a new UI surface | CLI under `app/backend/app/cli/`, read-only, reuses the existing orchestrator/payload. No route, no component, no schema mutation. |
| Coordinate with Codex before backend implementation | This doc is the pre-implementation contract; the §3 "Codex decision point" + §7 enumerate the only backend touch-points. |

---

## 7. Backend touch-points for Codex (minimal)

1. **Evidence tap (the only real new wiring):** a thin in-process function that
   returns `(report_payload, evidence_map, evidence_statuses)` for a resolved
   variant, reusing the exact path `/report` runs. No recompute, no new source.
2. **`app/backend/app/cli/eamos_press.py`:** argparse front end (this contract),
   plus a pure `evaluate_claims(payload, evidence_map, statuses) -> sections`
   module (`app/backend/app/services/claim_provenance.py` suggested) so the
   evaluator is unit-testable without the CLI.
3. **`stale` derivation:** source-cache rows persist `fetched_at` (confirmed by
   Codex 2026-06-01) → derive `stale` from `cache` + age > threshold where a
   repository row is available. Payload-only facts with no source-cache timestamp
   stay non-stale → `unverifiable`, never guessed.
4. **No change** to `ReportPayload`, routes, or the frontend. The
   `acmg_worksheet` already exists in evidence; the truth-printer just reads all
   `assertion_level`s instead of the call-card's narrowed filter.

**Resolved by Codex (2026-06-01):**
- (a) **In-process tap** — no `?debug=evidence` HTTP projection unless a specific
  security/product reason emerges later.
- (b) `PS3_Supporting` is an **Eamos functional-literature derivation**, declared
  provenance `eamos_functional_literature:publication_functional_evidence`. If the
  truth-printer ever sees it presented as ClinGen/VCEP provenance →
  **`contradicted` (red)**.
- (c) Source-cache rows persist `fetched_at` → `stale` uses it where rows exist;
  payload-only facts without a timestamp → `unverifiable`.

---

## 8. Demo-sample audit mode (Codex's ask)

Codex independently checked the example pills against live output and asked for
the same harness to gate **which variants are allowed as the public demo
sample**. Same engine, one extra mode:

```
python -m app.cli.eamos_press "USH2A:c.2276G>T" --audit-demo-sample --compact
```

Emits a `demo_audit` block and exits 2 if the variant is **not** demo-safe:

```jsonc
"demo_audit": {
  "allowed_as_primary_demo_sample": false,
  "completeness": { "popfreq": "complete", "clinical": "complete",
                    "publications": "complete", "trials": "degraded",
                    "computational": "missing", "gene": "missing",
                    "protein": "partial" },
  "blocking": [
    "trials.unsupported_rows:3 (matched_terms=[] cardiac trials)",
    "popfreq.contradicted:PM2_vs_BS1" ],
  "metric_sources": { "popfreq": "cache", "clinical": "cache",
                      "publications": "cache", "trials": "cache" }
}
```

**Demo-safe gate** (all must hold): the four primary metric sections
(`popfreq, clinical, publications, trials`) are `live`/`cache` (not
`missing`/`fixture`/`fallback`); each has ≥1 `variant_specific` claim; **no**
`contradicted` claims; **no** `unsupported` trial rows. This is the
"data-quality correction, not copy cleanup" check Codex asked for:

- **`RPE65 c.260A>G`** fails (ClinVar VUS, gnomAD not found, no popfreq metrics,
  no functional evidence) → it stays a *negative/missing-data control*, not a
  showcase. (Removal from hero/demo surfaces is a **frontend follow-up Claude
  owns once the harness is green/red**, and needs Steven's OK as a visible
  content change — it is **not** done in this contract task. Keep RPE65 c.260A>G
  in Gene Viewer fixtures/preflight; that lane is unaffected.)
- **`USH2A c.2276G>T`** fails *today* only on the trials false-positives + the
  PM2/BS1 contradiction; it becomes demo-safe once those are fixed (it already
  has the best PopFreq + ClinVar + exact-publication showcase).
- **`BRCA1 c.5266dupC`** — strong ClinVar/gnomAD/publications audit candidate but
  also exposes an empty-`matched_terms` trial; oncology, not retinal.

**Trials bug (shared finding, regression-worthy):** a row with
`matched_terms == []` must **not** be promoted to `gene_level` just because the
query fell back to a bare gene search. Today USH2A admits unrelated
heart-failure/cardiology rows and BRCA1 has ≥1 empty-`matched_terms` trial. The
truth-printer makes this assertable (§5d → `unsupported`); the *fix* lives in
`clinical_trials.py` (drop/flag empty-`matched_terms` rows) with regression
coverage — a separate, Codex-owned backend change this harness justifies.

---

## 9. Relationship to the proprietary systems (and where a CLI helps)

### 9a. Does EP-VLEx (the proprietary LitVar2/PubMed extractor) fit — or does the CLI better it?
**It fits as the upstream producer; the CLI does not replace it, it makes its
output testable — and closes a gap EP-VLEx can't see alone.**

[EP-VLEx](../../docs/proprietary/ep-vlex.md) (`publication_literature.py`)
already computes precisely the `publications` signal `eamos_press` consumes:
`snippet_status` (`exact_variant_snippet` vs `gene_only_no_variant`),
`matched_terms`, `source_tags`, and `scope_counts` (`count_kind` + `query` +
`source_breakdown`). `eamos_press --sections publications` **reads** that output;
it must not re-implement alias generation or PMID aggregation.

The CLI *betters* it in three ways EP-VLEx was never meant to do itself:
1. **Turns provenance labels into asserted invariants.** Today nothing fails
   when a `gene_only_no_variant` article is rendered as if it discusses the
   variant. The CLI's `claim_level`/`verdict` makes that a pass/fail.
2. **Cross-source reconciliation.** USH2A's headline is litvar2=190 vs pubmed=8.
   EP-VLEx *records* the breakdown; the CLI *flags* the divergence so "190
   publications" can't imply 190 hand-read variant papers.
3. **Closes the alias-loss loop with §5i.** The USH2A
   `protein_change_derivable_not_surfaced` bug means EP-VLEx never receives the
   `p.Cys759Phe` / `C759F` aliases (`VariantLiteratureTerms.build` reads
   `variant.protein_change`, which is `null`). That silently lowers its
   exact-match rate. EP-VLEx alone can't detect the missing input; the CLI's
   cross-section check (protein vs publications) surfaces the upstream gap.

### 9b. Whole-catalogue survey — what a CLI can optimize, and how it integrates
The [proprietary catalogue](../../docs/proprietary/README.md) has seven systems.
Two CLI families apply: **(A)** printing-press *generated* CLIs (wrap an HTTP
endpoint from our `/openapi.json` — the backend verify CLI already built);
**(B)** hand-built `app/cli/` debug/truth-printers (for internal services with no
HTTP surface — `eamos_search_input`, and now `eamos_press`).

| Proprietary system | Existing CLI? | CLI opportunity | Family |
| --- | --- | --- | --- |
| **EP-VLEx** (publications) | `lookup publications` endpoint → already in the backend verify CLI | `eamos_press --sections publications` adds the assertion layer (9a) | A + B |
| **Variant Report Data Orchestrator** | none | **`eamos_press` is its truth-printer** — the highest-value integration; nothing else inspects its assembled claims | B |
| **Search Input Resolver** | `eamos_search_input` ✓ | reused by `eamos_press` for query→variant resolution (no new CLI) | B |
| **Candidate Resolution** (interpreter) | none | small win: an `--explain-candidates` mode (why candidate X won) — fold into `eamos_press` resolution block, not a new tool | B |
| **Search Input AI Extractor** | `search_input_ai_smoke` ✓ | adequate | B |
| **Local-First Source Model Workflows** | `warm_source_cache` ✓ | **a source-status/freshness audit** (live/cache/fixture/stale across all local sources) directly feeds the truth-printer's `source_status` + `stale` derivation (§7.3) — the natural next `app/cli/` tool | B |
| **gnomAD Ancestry Map** | n/a (frontend geometry) | not a CLI candidate; the separate gnomAD **data** CLI is the already-approved task | — |

**Integration verdict:** `eamos_press` is the unifying truth-printer that ties
EP-VLEx (publications), the orchestrator (every report section), and — once a
source-freshness audit exists — the local-source model into one terminal QA
surface. The printing-press *generated* backend CLI already exposes the same
endpoints as a thin HTTP client; the two are complementary (generated client for
calling, hand-built truth-printer for *asserting*). No proprietary system needs
to be rewritten — each is read, surfaced, and made assertable. New catalogue
entry for `eamos_press` to be added on implementation (Codex owns the entry per
catalogue convention).

---

## 10. Out of scope (explicit)

- No fix to the PM2/BS1 bug itself in this task — the truth-printer's job is to
  *expose and assert* it. The fix (likely widening
  `_first_acmg_badge_from_consensus` to honor `vcep_specified` and prefer the
  source-asserted frequency code over an Eamos hint) is a separate change, gated
  on this harness going green↔red correctly first.
- No new external data source. No gnomAD CLI work (that is the separately
  approved, still-pending task).
- No LLM. Pure deterministic fact-binding.
