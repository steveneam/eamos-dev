# Phase 3 + 4 — ground-truth contract reference

> Verifier: Claude (spec/ground-truth agent), 2026-06-06. READ-ONLY pass over
> `app/web`. Every claim below is `file:line` against the live tree. This is the
> contract you code against — where the spec guessed wrong, the **⚠ SPEC IS WRONG**
> rows are authoritative.
>
> Scope confirmations you already made (re-confirmed, not re-derived):
> store exports + `SavedVariant`/`Folder` + dedupe id `query.toLowerCase()` +
> event `eamos:library-change`/`storage` (`lib/variant-library.ts:1-107`);
> `LibraryStore` is declared but **not** exported (`variant-library.ts:19`);
> `<WorkRail>`/`<WorkRailSection>` exist as described; compare-stash writer is
> **`stashCompareVariants`** not `writeCompareVariants`.

---

## 0. TL;DR — the things most likely to bite you

| # | Gotcha | Where |
| - | ------ | ----- |
| A | **There is no on-page `<LocusContext>` component.** `locus_context.nearby_variants` is only consumed by the **export** libs today (`report-html.ts:388`, `report-tsv.ts:197`). Your `<RelatedVariants>` is the *first* on-page reader. | §2 |
| B | **`resolveClassificationConfig()` is keyed on SPACE strings** (`'likely pathogenic'`), but `ClassificationTier` / `NearbyVariant.classification` are **UNDERSCORE** (`'likely_pathogenic'`). Passing a raw tier in → silent grey-NA fallback for the two multi-word tiers. You MUST map tier→label first. | §4 |
| C | The spec's `writeCompareVariants` does not exist. Use **`stashCompareVariants(variants, source)`**, sessionStorage key `eamos.compare.v1`, shape `CompareStash`. | §0 / Q-tray |
| D | `header.cdna` / `header.transcript` / `header.protein_change` are all **optional** (`?`). Only `header.gene` is required. Plan the fallback to `row0` exactly as the ribbon does. | §1 |
| E | Full transcript HGVS (`NM_…:c.…`) is **NOT** a single header field. It lives on `variant_summary_rows[0].transcript_hgvs` (already combined `NM_…:c.…`), or recompose `header.transcript + ':' + header.cdna`. | §7 |

---

## 1. Report payload type + header identity (spec Q1)

The rail receives `activeState.data`, type **`LookupResponse`** (`ReportClient.tsx:90` defines `state.data: LookupResponse`; imported from `@/lib/backend` at `ReportClient.tsx:56-63`).

| Spec claim | Real symbol | file:line | OK? |
| ---------- | ----------- | --------- | --- |
| rail receives `activeState.data` = `LookupResponse` | `LoadState … { kind:'ready'; … data: LookupResponse }` | `ReportClient.tsx:90` | ✅ |
| `LookupResponse.report_payload` | `report_payload: ReportPayload` | `backend.ts:310` | ✅ |
| `report_payload.report_profile.header` | `ReportPayload.report_profile?: VariantReportProfile` → `.header?: VariantReportHeader` | `backend.ts:111`, `backend.ts:1127` | ✅ (both optional — `?`) |
| header `.gene` | `gene: string` (**required**) | `backend.ts:820` | ✅ |
| header `.cdna` | `cdna?: string \| null` (**optional**) | `backend.ts:822` | ⚠ optional |
| header `.transcript` | `transcript?: string \| null` (**optional**) | `backend.ts:821` | ⚠ optional |
| header `.protein_change` | `protein_change?: string \| null` (**optional**) | `backend.ts:823` | ⚠ optional |
| header `.classification` (verdict for the open-report dot) | `classification?: string \| null` (**free string, not a tier enum**) | `backend.ts:825` | ⚠ free string |

`VariantReportHeader` full field list (`backend.ts:818-829`): `display_name`(req), `gene`(req), `transcript?`, `cdna?`, `protein_change?`, `genomic_hg38?`, `classification?`, `classification_source?`, `verification_badges:string[]`, `source_urls:string[]`.

### StickyVariantRibbon fallback — how identity is derived (authoritative pattern to copy)

`row0 = payload.variant_summary_rows[0]` (`ReportClient.tsx:530`). The ribbon derivation, **copy this exactly** for the Save-current CTA fallback:

```
ribbonGene        = header?.gene ?? row0?.gene ?? undefined        // ReportClient.tsx:575
transcriptHgvs    = row0?.transcript_hgvs ?? null                  // :576  (e.g. "NM_206933.4:c.2276G>T")
ribbonTranscript  = header?.transcript ?? transcriptHgvs?.split(':')[0] ?? undefined   // :577
ribbonHgvsC       = header?.cdna       ?? transcriptHgvs?.split(':')[1] ?? undefined   // :578
ribbonHgvsP       = header?.protein_change ?? row0?.protein_change ?? undefined        // :579
```

`VariantSummaryRow` shape (`backend.ts:57-64`): `gene`, `transcript_hgvs`, `protein_change`, `genomic_hg38`, `variation_type`, `consequence` — **all `string | null`**. So `variant_summary_rows[0]` can be `undefined` (empty array) AND every field nullable; guard both.

**Save-current identity recipe (verified):**
- `gene = header?.gene ?? row0?.gene` → if null, button disabled ("No variant identity available").
- compact `cdna = header?.cdna ?? row0?.transcript_hgvs?.split(':')[1]`.
- `query = \`${gene} ${cdna}\`.trim()` — matches the round-trip key (§5). Note `ReportClient` itself builds `queryLabel = \`${gene} ${cdna}\`.trim() || q` from **URL params**, not the payload (`ReportClient.tsx:413`). The spec sketch passes `query={queryLabel}` — fine, but `queryLabel` is the URL gene+cdna (uppercased gene from the URL), which is exactly what `reportHrefForQuery` round-trips.

---

## 2. `locus_context.nearby_variants` (spec Q2)

| Spec claim | Real symbol | file:line | OK? |
| ---------- | ----------- | --------- | --- |
| `report_payload.locus_context` exists | `locus_context?: LocusContext \| null` | `backend.ts:101` | ✅ optional |
| `LocusContext.nearby_variants` | `nearby_variants: NearbyVariant[]` (**required array** on LocusContext) | `backend.ts:455` | ✅ |
| consumed by an on-page `<LocusContext>` component | **NO SUCH COMPONENT** — only export libs read it (`report-html.ts:388`, `report-tsv.ts:197`) | — | ⚠ SPEC IS WRONG |

`LocusContext` full shape (`backend.ts:451-457`): `gene:string`, `centre_cdna:string`, `coords?:string`, `nearby_variants:NearbyVariant[]`, `codon_strip:CodonCell[]`.

`NearbyVariant` (`backend.ts:434-440`):

| Field | Type | Required? |
| ----- | ---- | --------- |
| `cds_pos` | `number` | required |
| `classification` | `ClassificationTier` (**underscore enum** — see §4) | required |
| `hgvs` | `string` | required |
| `clinvar_id` | `string \| null` | **optional** (`?`) |
| `protein_change` | `string \| null` | **optional** (`?`) |

⚠ **SPEC IS WRONG (component name):** the spec's lane-1 row says "(`<LocusContext>`)". No such component exists; `<RelatedVariants>` is the first on-page consumer of `nearby_variants`. The export reader (`report-html.ts:388-409`) is the only precedent and shows the column order it uses: `cds_pos · hgvs · protein_change · classification · clinvar_id`.

For lane-1 report links, `reportHrefForQuery(\`${locus.gene} ${nv.hgvs}\`)` works **only if `nv.hgvs` is a bare `c.…`** (it is — `NearbyVariant.hgvs` is the cDNA HGVS, no transcript prefix, per the export usage). `reportHrefForQuery` regex `VARIANT_LIKE` matches `c.` (`variant-search.ts:6`). ✅

---

## 3. `associated_conditions` (spec Q3)

| Spec claim | Real symbol | file:line | OK? |
| ---------- | ----------- | --------- | --- |
| `report_payload.associated_conditions` | `associated_conditions?: AssociatedCondition[]` | `backend.ts:105` | ✅ optional array |
| `AssociatedCondition.name` | `name: string` | `backend.ts:507` | ✅ |
| `.case_count` | `case_count: number` | `backend.ts:508` | ✅ |
| evidence-level field | **`evidence_level: EvidenceLevel`** (not `evidence`/`level`) | `backend.ts:509` | ✅ exact name |

`AssociatedCondition` full (`backend.ts:506-515`): `name`, `case_count`, `evidence_level`, `inheritance: InheritancePattern`, `source: string`, `db_tag?`, `db_tag_bold?`, `source_list?`.
`EvidenceLevel = 'definitive' | 'strong' | 'moderate' | 'limited'` (`backend.ts:503`).
`InheritancePattern = 'AR' | 'AD' | 'XL' | 'MT'` (`backend.ts:504`).
On-page renderer precedent: `<AssociatedConditions data={payload.associated_conditions} />` (`ReportClient.tsx:852`).

---

## 4. `ClassificationTier` + `--cls-*` token map (spec Q4)

**Definition:** `backend.ts:417-423`
```ts
export type ClassificationTier =
  | 'pathogenic' | 'likely_pathogenic' | 'vus' | 'likely_benign' | 'benign'
```
(5 values, underscore form. No `'unknown'`/`'conflicting'` member — that's `VariantClassification` at `backend.ts:1332`, a *different* enum that DOES add `'unknown'`.)

### Every `--cls-*` token (defined `globals.css:81-109`)

| Tier group | bg | text | bdr | dot |
| ---------- | -- | ---- | --- | --- |
| pathogenic | `--cls-path-bg` (`:81`) | `--cls-path-text` (`:82`) | `--cls-path-bdr` (`:83`) | `--cls-path-dot` (`:84`) |
| likely pathogenic | `--cls-lpath-bg` (`:86`) | `--cls-lpath-text` (`:87`) | `--cls-lpath-bdr` (`:88`) | `--cls-lpath-dot` (`:89`) |
| vus | `--cls-vus-bg` (`:91`) | `--cls-vus-text` (`:92`) | `--cls-vus-bdr` (`:93`) | `--cls-vus-dot` (`:94`) |
| likely benign | `--cls-lben-bg` (`:96`) | `--cls-lben-text` (`:97`) | `--cls-lben-bdr` (`:98`) | `--cls-lben-dot` (`:99`) |
| benign | `--cls-ben-bg` (`:101`) | `--cls-ben-text` (`:102`) | `--cls-ben-bdr` (`:103`) | `--cls-ben-dot` (`:104`) |
| **NA / neutral** | `--cls-na-bg` (`:106`) | `--cls-na-text` (`:107`) | `--cls-na-bdr` (`:108`) | `--cls-na-dot` (`:109`) |

✅ Neutral/NA token group **exists** (`--cls-na-*`, `globals.css:106-109`); it maps to `var(--bg-soft)`/`var(--ink-3)`/`var(--line)`/`var(--ink-4)`. Use it for the saved-card dot when classification is unknown.

### tier → token: USE THE SHARED RESOLVER, but translate the key first

Canonical resolver: **`resolveClassificationConfig(classification: string): ClassificationConfig`** (`lib/classification.ts:46`) returning `{bg,text,border,dot}` (note: field is **`border`**, not `bdr`, on the returned object — `classification.ts:12-17`). Also exports `hasClassificationTier(s): boolean` (`:52`) and `NA_CONFIG` (`:26`).

⚠ **SPEC IS WRONG (silent mis-color trap).** `resolveClassificationConfig` keys (`classification.ts:28-42`) are **space/lowercase strings**: `'pathogenic'`, `'likely pathogenic'`, `'vus'`, `'likely benign'`, `'benign'`. The `ClassificationTier` enum is **underscore**: `'likely_pathogenic'`, `'likely_benign'`. So:

| You pass | Resolver result |
| -------- | --------------- |
| `'pathogenic'` | ✅ PATHOGENIC |
| `'vus'` | ✅ VUS |
| `'benign'` | ✅ BENIGN |
| `'likely_pathogenic'` (raw tier) | ❌ falls through to **grey NA_CONFIG** |
| `'likely_benign'` (raw tier) | ❌ falls through to **grey NA_CONFIG** |

**Required:** translate `ClassificationTier` → space label before calling, e.g. a local `TIER_LABEL: Record<ClassificationTier,string> = { pathogenic:'pathogenic', likely_pathogenic:'likely pathogenic', vus:'vus', likely_benign:'likely benign', benign:'benign' }`, then `resolveClassificationConfig(TIER_LABEL[nv.classification])`. (No existing helper does this translation — `MatrixTile.tsx:50` only ever feeds it `tile.primary_label`, already a human string; verified no `_`→` ` shim exists.)

Alternative the CSS already encodes: the `.locus-dot.{p|lp|vus|lb|b}` suffix classes (`globals.css:428-432`) — but that mapping ALSO lives nowhere in TS today (the export libs render plain text, not dots). If you prefer class-based dots, the suffix convention is `p / lp / vus / lb / b`; you still author the tier→suffix map yourself.

The `header.classification` (open-report dot) is a **free string** (`backend.ts:825`), already space-form ClinVar-style (e.g. `"Likely pathogenic"`), so it can go straight into `resolveClassificationConfig` — same path `ClassificationBadge` uses (`ClassificationBadge.tsx:46`). Only the `NearbyVariant`/stored-tier path needs the underscore translation.

---

## 5. `reportHrefForQuery` round-trip (spec Q5)

**Signature:** `reportHrefForQuery(raw: string): string | null` (`variant-search.ts:40`). Returns `null` for empty/whitespace.

Round-trip of a saved `query` like `"USH2A c.2276G>T"`:
1. `structuredVariantFromText("USH2A c.2276G>T")` (`variant-search.ts:23`) → `direct` regex `^([A-Za-z][A-Za-z0-9-]+)\s+(.+)$` matches `gene="USH2A"`, rest `"c.2276G>T"`.
2. `normaliseVariantToken("c.2276G>T")` → `VARIANT_LIKE` `/^(c\.|p\.|g\.|m\.|n\.|rs\d|chr|\d+[-:])/i` matches `c.` → returns `"c.2276G>T"` (`variant-search.ts:6,18`).
3. → `{ gene:'USH2A', variant:'c.2276G>T' }` → `new URLSearchParams({ gene:'USH2A', cdna:'c.2276G>T' })` → **`/report?gene=USH2A&cdna=c.2276G%3ET`** (`variant-search.ts:44-47`).

✅ Round-trips, and the URL matches the live sample-report href `/report?gene=USH2A&cdna=c.2276G%3ET` used as the demo redirect (`ReportClient.tsx:105`). The `gene` is uppercased by `structuredVariantFromText` (`variant-search.ts:27`), so case in the saved `query` is normalized on the way out.

Caveat for stored full-transcript queries: if you ever feed `reportHrefForQuery` a **transcript-qualified** string like `"NM_206933.4:c.2276G>T"`, `structuredVariantFromText` returns `null` (no `GENE <space> variant` split) → it falls back to `{ q: text }` → `/report?q=…`, which routes through the backend resolver, NOT the direct gene+cdna path. **So keep the round-trip key as the compact `"GENE c.…"` form** (matches locked decision §3). Store `hgvs_full` for display only, never as the href source.

---

## 6. Report module anchors in `ReportBody` (spec Q6)

Actual `<div id="…" className="scroll-mt-24" />` anchors, **document order**, with the rendered section + label + conditional status. All in `ReportClient.tsx`:

| Order | `id=` | file:line | Human label (Card title) | Conditional? |
| ----- | ----- | --------- | ------------------------ | ------------ |
| 1 | `population_frequency` | `:670` | "gnomAD population frequency" (Card #1) | ⚠ **YES** — anchor always renders, but the **Card only renders when `populationSection` truthy** (`:671`); `populationSection` is null when `populationTarget?.match_level === 'unavailable'` (`:617-621`). Probe `getElementById` or pass rendered ids. |
| 2 | `evidence_by_source` | `:696` | "In-silico predictions" (Card #2) | No (always rendered) |
| 3 | `clinical_evidence` | `:719` | "Clinical evidence" (Card #3) | No |
| 4 | `gene_context` | `:761` | "Gene & locus context" (Card #4) | No |
| 5 | `associated_conditions` | `:826` | "Disease & curated variants" (Card #5) | No (Card always renders) |
| 5b | `curated_variants` | `:827` | (second anchor into the SAME Card #5) | No — duplicate anchor into one card; pick `associated_conditions` for the nav row, ignore `curated_variants` or treat as alias |
| 6 | `publications` | `:870` | "Publication literature" (Card #6, via `<LazySection>`/`PubMedSection`) | Lazy — anchor always present; content hydrates async |
| 7 | `trials` | `:897` | "Active trials & approved therapies" (Card #7) | No |
| 8 | `ai_summary` | `:921` | "AI evidence summary" (Card #8) | No |

⚠ **SPEC IS WRONG (anchor list).** The spec §2.6 lists `gene_context` as `"gene_context"` ✅ but the spec narrative also writes the order with labels "Summary/Population, In-silico, Clinical evidence, Gene & locus, Disease & conditions, Publications, Trials, AI summary" — that's 8 labels for **9 anchors** (it silently merges the `associated_conditions`+`curated_variants` pair, which is correct, AND it never mentions there's no `summary`/`ai_summary` distinction issue). Net: the real id set is exactly the 9 above; `curated_variants` is a second anchor inside Card #5, not its own section. There is **no** `gene_context` vs `gene_disease` split and **no** standalone summary anchor — `MatrixOverture` (`:661`) is the top lookahead but carries no `scroll-mt` id.

Only **`population_frequency`** is genuinely conditionally *empty* (anchor present, card absent). Everything else: the anchor and its card both render unconditionally on the `ready` state. Safest nav strategy (matches spec §2.6 fallback): after mount, `document.getElementById(id)` filter — an anchor with no following card still resolves to a 0-height div at the bottom-of-its-slot, so also verify a sibling card exists if you want to hide the Population row when empty. Cleaner: derive the "Population present" flag from the same `populationSection` truthiness you can't see from the nav — so prefer probing for the Card, or have `ReportBody` pass the rendered id list down (spec already lists this as the chosen approach).

---

## 7. Full transcript HGVS at save-time (spec Q7 + locked decision §3 `hgvs_full?`)

⚠ **There is no single `header.hgvs_full` field.** The full transcript-qualified HGVS (`NM_206933.4:c.2276G>T`) is assembled, never stored whole on the header. Sources, in priority order:

| Source | Value | file:line | Notes |
| ------ | ----- | --------- | ----- |
| `variant_summary_rows[0].transcript_hgvs` | already-combined `"NM_206933.4:c.2276G>T"` | `backend.ts:60` (type), used `ReportClient.tsx:576` | **Best single source.** This is exactly the string you want for `hgvs_full`. `string \| null` — guard. |
| `header.transcript` + `':' + header.cdna` | recompose `"NM_206933.4" + ":" + "c.2276G>T"` | `backend.ts:821,822` | Fallback when `row0` absent. Both optional — only build if both present. |
| `header.genomic_hg38` | `"1-216247118-C-A"` style | `backend.ts:824` | NOT transcript HGVS; don't use for `hgvs_full`. |

**Save-time recipe for `hgvs_full?`:**
```
hgvs_full =
  row0?.transcript_hgvs
  ?? (header?.transcript && header?.cdna ? `${header.transcript}:${header.cdna}` : undefined)
```
This mirrors how the ribbon reconstructs the copy label (`ReportClient.tsx:591`: `${ribbonTranscript}:${ribbonHgvsC}`). Store `hgvs_full` for the disclosure UI only; keep `query` = compact `"GENE c.…"` as the href key (§5).

For the **classification at save-time** (locked decision §2, `classification?: ClassificationTier`): the report exposes `header.classification` as a **free string** (`backend.ts:825`), e.g. `"Likely pathogenic"` — NOT a `ClassificationTier` enum value. To store a `ClassificationTier`, you must normalize the free string → tier (lowercase + `' '`→`'_'`, then validate against the 5 enum values), or store the raw string and translate at render. The existing `deriveClassificationVerdict()` (`ReportClient.tsx:1133`) maps the free string → the `Verdict` display union (`'Pathogenic'|'Likely pathogenic'|…`) and is the closest precedent, but it returns the **space-form display** union, not the underscore `ClassificationTier`. No existing helper returns a `ClassificationTier` from the header string — you'll author that normalization.

---

## 8. Compare tray writer (spec §2.5 — confirm stash)

⚠ **SPEC IS WRONG:** `writeCompareVariants` does not exist. Use:

| Symbol | Signature | file:line |
| ------ | --------- | --------- |
| writer | `stashCompareVariants(variants: ParsedVariant[], source: string): void` | `variant-file.ts:92` |
| reader | `readCompareVariants(): CompareStash \| null` | `variant-file.ts:102` |
| key | `'eamos.compare.v1'` (sessionStorage) | `variant-file.ts:84` |
| shape | `CompareStash { savedAt: number; source: string; variants: ParsedVariant[] }` | `variant-file.ts:86-90` |

`ParsedVariant` here is the **`lib/variant-file` one** (`variant-file.ts:9-16`): `{ raw: string; gene: string|null; variant: string|null; query: string }` — this is the type `stashCompareVariants` expects, and the same shape `saveVariants`/`saveVariant` consume from the store.
⚠ Do NOT confuse it with `backend.ts:1838` `ParsedVariant` (the batch one — superset with `chrom/pos/ref/alt/warnings[]`). Two different `ParsedVariant` types exist; the tray + library store use the `variant-file` one.

To build a tray `ParsedVariant` from a `SavedVariant`: `{ raw: sv.raw, gene: sv.gene, variant: sv.variant, query: sv.query }` — field-for-field compatible (`variant-library.ts:3-11` ↔ `variant-file.ts:9-16`). Source label e.g. `"Compare tray"`. No new writer needed — the spec's "add `writeCompareVariants` if missing" is moot.

---

## 9. Quick reference — confirmed import surface for the new components

| Need | Import from | Confirmed export | file:line |
| ---- | ----------- | ---------------- | --------- |
| store reads/writes | `@/lib/variant-library` | `getLibrary, saveVariants, removeVariant, isSaved, subscribe`, types `SavedVariant`, `Folder` | `variant-library.ts:3,13,29,58,84,92,99` |
| `LibraryStore` type | `@/lib/variant-library` | **NOT exported yet** (`interface LibraryStore` at `:19` is module-private) — you export it | `variant-library.ts:19` |
| compact-query href | `@/lib/variant-search` | `reportHrefForQuery`, `structuredVariantFromText` | `variant-search.ts:40,23` |
| compare stash | `@/lib/variant-file` | `stashCompareVariants`, `readCompareVariants`, types `ParsedVariant`, `CompareStash` | `variant-file.ts:92,102,9,86` |
| tier → tokens | `@/lib/classification` | `resolveClassificationConfig`, `hasClassificationTier`, `NA_CONFIG`, type `ClassificationConfig` | `classification.ts:46,52,26,12` |
| payload types | `@/lib/backend` | `LookupResponse, ReportPayload, VariantReportHeader, VariantSummaryRow, LocusContext, NearbyVariant, AssociatedCondition, ClassificationTier, EvidenceLevel` | `backend.ts:307,82,818,57,451,434,506,417,503` |
| existing tier→config consumer (pattern to copy) | — | `ClassificationBadge` (`ClassificationBadge.tsx:46`), `MatrixTile` (`MatrixTile.tsx:50`) | — |
```
