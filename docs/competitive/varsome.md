# Varsome — Competitive Analysis

> Created 2026-05-27 (Claude). Source: 33 screenshots in
> `c:\Users\seamegdool\Desktop\Claude code and website tips\EAMOS Web Tool\Competition\Varsome`
> + live WebFetch on `varsome.com/` and the TP53 R175L variant page. Four
> parallel subagent lenses synthesised here: UX/visual/IA, feature inventory,
> tech stack/perf, and business model/moat. Action items live in
> `plans/v2-redesign-impeccable.md` §10 "Competitor steals."

---

## 0. TL;DR

Varsome is a **card-grid CSR Angular SPA over a token-auth REST API**, fast-
feeling because of progressive per-card hydration and lazy heavy widgets. Its
**information architecture (6×4 summary-card matrix above a single-page report
with section panels that expand below) is the single strongest pattern on the
site** and we should adopt it. Its **content moat (citation depth, ClinGen VCEP
narrative, 25+ in-silico predictors, named community contributions)** is real
but not a ten-year moat if we start now. Its **execution is dated** — generic
spinner, broken mobile, Cloudflare/reCAPTCHA-gated variant URLs, no SSR, weight-
700 chrome — which is exactly where Eamos's Reading Room direction can
leapfrog. Its **business model (opaque enterprise pricing + visible Premium
gating + a "Cite VarSome" button on every page driving citations to the 2018
Bioinformatics paper)** is ruthless and worth half-copying: Eamos should ship
the Cite button now and reject the "results are incomplete unless you pay"
modal.

**Steven's observations all confirmed:** Feedback/Cite chip bottom-left, colored
pathogenicity bars + ClinVar stars on cards, variant-vs-gene publication count
toggle, publication-detail modal with backdrop blur and PubMed/DOI/PDF links,
activity strip on landing (messy but a flywheel), greyed-Premium gating, dense
Region Browser, one-section-at-a-time bottom expand (clean desktop, bad mobile).

---

## 1. Design system fingerprint

**Palette (sampled).** A two-pole identity: deep navy chrome (`~#0F2942`) over
warm off-white canvas (`~#F4F6F8`). Pathogenicity is the only real chromatic
system — a four-stop semantic ramp:

- Pathogenic red `~#D7392A`
- Likely-Pathogenic / "Moderate" orange `~#E5732A`
- Uncertain amber `~#F1B43C`
- Benign green `~#3FAE57` / teal CTA `~#22B19A`

Greyscale is flat: disabled, no-data, AND premium-gated tiles all share the
same `~#A0A6AE` text on `~#F1F2F3` — intentional collapse (premium and
absence look identical until you read the badge).

**Typography.** Single sans family (Open Sans or similar humanist grotesque),
two weights only (400/600). Body ~13px on the report, ~12px inside cards.
Numerals are proportional, not tabular — metric strips wobble.

**Density and rhythm.** Extremely dense. The header tile grid packs **24 tiles
in a 6-column × 4-row matrix above the fold at 1440px**. 4px spacing base with
8/12/16 stops; tile gutter ~6px. The identity is "Bloomberg terminal for
variants" — utilitarian, hairline 1px dividers, no soft shadows.

**Iconography.** Plain monochrome teal FontAwesome-ish glyph set. The only
branded mark is a green-orange-yellow tick that doubles as the Premium badge.

---

## 2. Information architecture

### Landing page
Three-zone layout (navy top nav, centered search hero with `hg38/hg19` realm
selector + "Examples" disclosure, persistent right rail "Recent VarSome
activity" ~280px live on the empty-state landing). Footer carries a hidden
Feedback/Cite chip bottom-left (`Feedback and cite button bottom left.png`).

### Variant report — the strongest IA pattern
A **24-tile "card matrix"** sits above the variant header and acts as both a
TL;DR *and* a navigation index (`Report page One page.png`). Each tile is a
section preview (title + key value + mini-vis). Clicking a tile expands a
**single full-width section panel** beneath the grid (`ClinVar section.png`,
`Clingen section.png`, `Publications.png` all share identical panel chrome).

This is what Steven called the "one-page report with bottom-expand" — confirmed.
Only one expanded panel at a time. State is **client-only** — no URL fragment,
no route change — so the section is **unshareable and not back-button-friendly**
(technical weakness, easy win for us).

### Sticky elements
Navy header + a slate "variant ribbon" (`chr17-7675088-C-A (TP53:p.R175L)`)
with action buttons (Submit to ClinVar, Classify, Share, API Link, Favorites)
stay fixed. The bottom-left Feedback/Cite chip is also globally pinned.

---

## 3. Pathogenicity colour system — three uses, one ramp

The strongest pattern on the site. The ramp shows up three ways:

1. **Horizontal stacked bars with inline numerals.** ClinVar shows
   `[red:3][orange:3]` — a literal proportional split of submitter calls
   (`Cards - sections 3.png`, `ClinVar section.png`). In-Silico Predictors
   does the same: `[red:6][amber:1]` across calibrated engines
   (`In silco predictions.png`). Counts are printed *inside* the bar segments
   in white. **Legible at thumbnail size** — that's what makes the grid
   scannable.

2. **ClinVar review stars rendered inline.** Three filled + one empty
   (`★★★☆`) next to "Likely Pathogenic", ~10px (`Cards - sections 3.png`).
   Maps to ClinVar's own 0–4 star convention — instantly familiar to clinical
   users.

3. **Left-edge accent strip.** Every verdict card carries a 3–4px coloured
   left border in the same ramp. Grey premium/no-data tiles drop the border
   entirely — **absence of colour signals absence of signal**.

4. **ClinGen criteria pills (`Clingen section.png`).** ACMG codes rendered as
   filled pills in the ramp (PP4, PM1, PM5 orange; BS3_Supporting green;
   PS4_Moderate, PP3_Moderate red). "Criteria Not Met" pills go grey.
   **Semantic colour carries the entire meaning of each criterion** — no
   legend needed.

---

## 4. Feature and content inventory

### Full report section list (variant page)

1. **General Information** — chr/pos, REF/ALT, type, cytoband, HGVS, RS ID +
   dbSNP, gene symbol, UCSC/Mastermind/TraP cross-links, **"Viewed N times"
   counter** + "Connect with past/future viewers" CTA.
2. **Genes** — gene symbol pill.
3. **PharmGKB** *(PREMIUM)*.
4. **Transcripts** — RefSeq + Ensembl tables: coding impact, HGVS coding,
   HGVS Protein, exon location, protein position, splice distance, MANE
   Select, TSL, APPRIS, UniProt accession.
5. **Splicing Data** — **SpliceVault** (top 4 mis-splicing events, GTEx + SRA
   read counts, cryptic distance, in-frame Y/N, splice junction coords) +
   **SpliceVarDB** *(PREMIUM)*.
6. **Region Browser** — multi-track genome viewer (see §6).
7. **Germline Classification** — Varsome's own ACMG engine verdict.
8. **ClinVar** — clinical sig, type, **review status (gold-star)**, last
   evaluation, number of submitters, "10 publications", full table of
   accessions/submissions with conditions, MedGen/MeSH/Mondo/OMIM/Orphanet
   refs, PMIDs. "Submit to ClinVar" button.
9. **LOVD** *(PREMIUM)*.
10. **UniProt Variants** — annotation ID, protein, transcript, somatic
    status, **associated diseases table**.
11. **Frequencies** — gnomAD Exomes + Genomes (mean cov, median cov, % over
    20x) with version stamps.
12. **MitoMap**.
13. **Deafness Variation Database**.
14. **OMIM** *(PREMIUM)*.
15. **Conservation Scores** — phyloP100.
16. **In-Silico Predictors** — composite verdict bar + table (see §5).
17. **ClinGen** — pathogenicity, **Expert Panel attribution (e.g. TP53 VCEP)**,
    disease + MONDO link, inheritance mode, **criteria-met chips** (PP4, PM1,
    PM5, PM2_Supporting, BS3_Supporting, PS4_Moderate, PP3_Moderate),
    criteria-not-met chips, and a long **"Evidence submitted by expert"
    narrative** (`Clingen section.png`).
18. **Expression Data** — top tissue + count.
19. **GWAS**.
20. **Structural Variants** — same viewer chassis as Region Browser, SV-filtered.
21. **Beacon Network**.
22. **Protein Viewer** — 3D molecule (see §6).
23. **Community Contributions** — linked publications, user classifications,
    comments (`Community contribution.png`).
24. **Publications** — count split + tagged list (see §5).

### Evidence sources catalogue
ClinVar, ClinGen (with VCEP expert panel attribution), UniProt, gnomAD
Exomes v4 + Genomes v3, MitoMap, LOVD, Deafness Variation DB, OMIM, PharmGKB,
GWAS Catalog, SpliceVault (Dawes 2023), SpliceVarDB, Beacon Network,
SwissModel, MedGen, MeSH, Mondo, Orphanet, PubMed, MANE, APPRIS, Ensembl,
RefSeq, dbSNP, UCSC, Mastermind, TraP, phyloP100, and ~25 in-silico
predictors (see §5).

### Proprietary algorithms (their "secret sauce")
- **Germline Classification engine** — automated ACMG/AMP with rule-attributed
  evidence rows (PM1, PS3, etc.), each rule citing the underlying data sources
  that triggered it. Header carries editable transcript, "Auto/clinical
  evidence" toggle, ACMG points badge ("9 points · +0.4"), "Show hidden
  criteria" toggle, "Submit to ClinVar" button. Honest upsell modal: *"Varsome
  does not include all possible data sources. For the most accurate
  classification upgrade to Premium"* (`Propietary variant classification 2.png`).
- **Somatic Classification engine** (AMP/CGC/ESMO) — referenced in nav, not in
  this screenshot batch.
- **Calibrated in-silico verdicts** — each external predictor's raw score is
  re-mapped to ACMG-compatible Pathogenic Strong / Moderate / Uncertain
  buckets.
- **SpliceVault default curation rules** (max 2 exons skipped, cryptics ±600
  nt) on top of the raw dataset.

---

## 5. The two best sections in detail

### In-silico predictor table
Header: composite verdict bar ("**PP3: Pathogenic Moderate**", 6 vs 1 vote
bar), toggles for "Show raw data" and "Alphabetically". Columns:
**Engine | Calibrated Prediction | Score | Version**. Coloured labels (red
Pathogenic Strong, orange Pathogenic Moderate, amber Uncertain).

Free tier visible: **EVE** (0.9133, Pathogenic Strong), **AlphaMissense**
(0.9907, Pathogenic Moderate), **BLOSUM** (-6, Uncertain).

Premium-gated: **SIFT, SIFT4G, PROVEAN, MVP, MutPred, MutPred2, PrimateAI,
LIST-S2, MutationTaster, FATHMM, FATHMM-MKL, FATHMM-XF, LRT, DEOGEN2, M-CAP,
CADD, EIGEN, EIGEN-PC, ESM1b, gMVP, VARITY_R, VARITY_ER, VARITY_ER_LOO,
VARITY_R_LOO, PhACTboost…** — at least **25 distinct predictors**, names and
empty rows fully rendered so the gap is visible.

### Publications system
- **Dual count toggle**: radio between *"72 publications related to this
  variant"* vs *"55,326 publications related to gene TP53"*.
- Per-row: title, journal + year, authors, **citation count badge** (e.g. "30
  citations"), **"Linked by:" provenance** (ClinVar, CancerHotspots, GDC,
  cBioPortal, Varsome AI), and **coloured tag chips** (TP53, breast cancer,
  li-fraumeni syndrome, missense).
- Search-for-tags box, page-size selector, **"Order by: Relevance"** sort,
  **"Show Tags Timeline"** toggle, **Link publication** button (community).
- Click → **floating modal with the page blurred behind it**: full abstract,
  tag pills, PMID, **PubMed link, DOI link, AND PDF button**, like/comment
  counts. Best-in-class section on the site.

---

## 6. Tools beyond the report

- **Region Browser** (`Region browser.png`) — hg38, chr+range box with
  -/+/prev/next, lane stack: cytoband strip, base ruler, **coloured DNA
  letters track**, **Conservation Scores histogram (red→green)**,
  **Transcripts lane with amino-acid translation strip**, **UniProt Protein
  Regions lane**, **Pathogenicity lane**. Per-lane FILTERS chevrons + a
  Settings rail (Saved / Settings). IGV-class density. Looks **custom
  SVG/Canvas**, not IGV.js or JBrowse — styling and "FILTERS" chrome are
  bespoke. Almost certainly lazy-loaded.
- **Structural Variants** — same chassis as Region Browser, SV-track focused.
- **3D Protein Viewer** (`Protein viewer.png`) — SwissModel structure picker,
  transcript link, **Show panel** with colour-coded variant overlays
  (Pathogenic red, LP orange, VUS yellow, LB light-green, Benign dark-green,
  **Current Variant magenta**). Click residue for details. Space-filling
  rendering with class colour overlay suggests **NGL Viewer or Mol\***.
  Multi-MB WebGL bundle — they only load it when the user opens the card.
- **Single Reads (NGS/Sanger)** entry on landing page examples.
- **CNV / SV ingest** — example queries include `chr17:37800000:L100000:DUP`.

---

## 7. Technical stack and rendering

| Layer | Best guess | Confidence | Evidence |
| ---- | ---- | ---- | ---- |
| Frontend framework | **AngularJS or early Angular** (CSR SPA) | Medium-high | Full-screen "Loading, please wait…" spinner replacing an empty shell is the classic Angular fingerprint, not React/Next hydration. No `__NEXT_DATA__`, `__NUXT__`, or `data-reactroot` in fetched HTML. Saphetor's historical job postings advertised Angular. |
| CSS | Custom / Bootstrap-era grid + custom CSS, not Tailwind | High | Uniform fixed-row card grid, semantic class names (`section2`), no utility-class density in extracted HTML. |
| Hosting / CDN | `assets.varsome.com` (app) + `landing.varsome.com` HubSpot (marketing) | High | Marketing pages 302 to HubSpot. Two-stack split. |
| API / BFF | Django REST, token-auth, `api.varsome.com` | High | `/lookup/{ref}/{variant}`, `/region_variants/`, batch POST up to 1000 items, `Authorization: Token …`. |
| Anti-bot | Google reCAPTCHA on `/variant/*` | Confirmed | Direct deep-link returned a reCAPTCHA challenge. They protect the expensive route, not the landing. |

**Rendering strategy: pure client-side SPA.** Variant route serves an empty
shell + JS bundle that fetches data after mount. The sitemap is enormous
(~40 paginated files × 1000s of variants each) — they rely on sitemaps to feed
bots, not SSR.

### Performance — "lightning fast" is perception, not actual speed
- Shell + JS bundle is aggressively cached, so subsequent navigations feel
  instant.
- First paint is fast because **there's nothing to paint** — spinner shows up
  in <500ms.
- Cards render as a **skeleton grid with category labels first**, then each
  card fills in **independently** as its API call returns (`Cards - section
  1/2.png` show staggered hydration, not blocking).
- **Heavy widgets (Region Browser, 3D Protein Viewer) are lazy-loaded on
  expand** — they don't ship in the initial bundle.
- BUT: on a cold variant the spinner can sit for several seconds while N
  parallel API calls resolve. **Fast enough, not actually fast.**

### Section-expand mechanic — client-only state, unshareable
Clicking a card opens its detail section inline below the grid. No URL
fragment, no route change — **the section is unshareable, the back button
doesn't work**. Easy win for Eamos: same UX with App Router segments
(`/report/{id}#frequencies`) or route nesting.

### Publication-modal mechanic
Centered overlay card with darkened semi-transparent backdrop blurring/dimming
the page behind it — standard `backdrop-filter: blur()` + rgba scrim. Modal
not a route, URL doesn't change. **Worth copying** (the abstract-in-modal keeps
report scroll). **Worth improving** — add focus-trap, `aria-modal`, ESC handler,
and a shareable URL pattern (`?pub=PMID:12345`).

---

## 8. Business model and content moat

### Pricing — opaque, contact-sales-gated
**Four editions, zero public pricing** (`Pricing or Contact.png`):
- **VarSome Clinical** (CE-IVDR Class C, clinical labs, HIPAA)
- **VarSome Premium** (subscription unlock — predictors + premium DBs)
- **VarSome API** (programmatic)
- **VarSome Insights** (enterprise / cohort)

Sales motion is **enterprise B2B by default**, with Premium as the only
self-serve on-ramp. Three audiences on the same surface: clinical labs
(regulated high-ACV), research PIs/biotech (Premium + API), pharma (Insights).
No `/pricing/` URL exists (404).

### Premium gating — brutal but legible
On TP53 R175L they show **3 free predictors** (EVE, AlphaMissense, BLOSUM
with scores) and **15+ premium predictors fully rendered with engine names,
green PREMIUM badges, and "Only available in VarSome Premium subscribers"**.
The data is **teased, never blurred** — the user knows exactly what they're
missing. PharmGKB, LOVD, OMIM, SpliceVarDB cards are also Premium-only. The
sitewide upsell modal — *"Warning: VarSome does not include all possible
data sources. For the most accurate classification upgrade to Premium"* —
weaponises FOMO at decision time. Scummy-feeling but ruthlessly effective;
**we should adopt the gating pattern and reject the warning modal.**

### "Cite VarSome" — the academic moat lynchpin
Two grey buttons pinned bottom-left of every page (`Feedback and cite button
bottom left.png`). The Cite button likely opens a modal with their flagship
paper (Kopanos et al. 2018, *Bioinformatics*, "VarSome: the human genomic
variant search engine", DOI 10.1093/bioinformatics/bty897) which has
**~2,500+ Google Scholar citations**. Every grad student who used Varsome to
look up a variant cites this paper in their thesis, which compounds SEO +
credibility + investor narrative. **Highest-leverage 1-day feature for academic
adoption. Ship it now.**

### Citation/publication moat
TP53 R175L: **72 publications for the variant, 55,326 for the gene**. Per-row
metadata: title, journal, year, authors, citation count, abstract, tags
(rs IDs, HGVS, disease), and **"Linked by:" provenance from ClinVar / GDC /
cBioPortal / Varsome AI**. Replication cost: multi-year text-mining over
PubMed/Europe PMC, plus tag extraction and continuous re-indexing.
**Realistically 2–4 engineer-years to a credible v1, but not a ten-year moat
with modern LLM entity extraction.**

### Community and lock-in
- Per-variant: **Classify this variant** (flag CTA), **Link publication**
  (paste PMID/DOI), **User Comments** (login-gated).
- Claim of **500,000+ healthcare professionals and researchers** in community.
- **Activity strip on landing** shows real-time named contributions:
  *"Mendel Roth [Genben Lifesciences] classified APOC3:c.166G>C as Uncertain
  Significance"*, *"Ioannis Liopetas linked the publication … to
  ADAMTS10:c.1040G>A"*. Lab affiliations attached — **free corporate-logo
  placement that doubles as social proof and SEO**.

### Social-proof telemetry
*"This variant has been viewed 2,660 times on VarSome"* + **"Connect with
past and future viewers"** (`Number of times viewed.png`). Triple-purpose:
credibility, FOMO, network-effect tease. **Wrong tone for a clinical decision
tool — flag as anti-pattern for Eamos.**

### Customer + funding signals
Parent: **Saphetor SA** — Switzerland (EPFL Innovation Park, Lausanne),
offices in Boston and Athens. **CE-IVDR Class C certified** (clinical-grade EU
regulation). GA4GH member. APAC distribution via **Sciencewerke** (AU/MY/SG/TH)
— Australian channel partner, no direct AU office. Customer claims include
Gencell Pharma, IntegraGen, LongSeq, TrioLab Oy.

---

## 9. Gap analysis vs. Eamos

| Feature | Varsome | Eamos status |
| ---- | ---- | ---- |
| Variant header (chr/pos/REF/ALT/cytoband/RS) + cross-DB links | Full | **Has** |
| 6×4 summary card overview above body | Yes | **Missing** (Eamos uses linear sections) |
| ClinVar full table (accessions/submissions/PMIDs) | Yes | **Partial** (classification only) |
| ClinGen VCEP narrative + criteria chips | Yes | **Missing** |
| Proprietary ACMG/AMP classification engine | Yes (germline + somatic) | **Partial** — `AcmgCriteriaFold` scaffolding, no engine |
| Calibrated in-silico verdict table (~25 engines) | Yes | **Partial** — REVEL / AlphaMissense / MetaLR / SpliceAI Δ via `InSilicoGrid` |
| AlphaMissense | Yes (visible) | **Decided-against on display** (data kept, hidden 2026-05-19) |
| Splicing — SpliceVault top-4 mis-splice events | Yes | **Missing** (only SpliceAI Δ) |
| RefSeq + Ensembl transcripts table (MANE/APPRIS/TSL) | Yes | **Missing** |
| gnomAD exomes/genomes coverage table | Yes | **Partial** — frequency only |
| UniProt Variants → associated diseases | Yes | **Missing** |
| Region Browser (IGV-class multi-track viewer) | Yes (tight) | **Partial** — Workbench sequence viewer + locus context lanes |
| Structural Variants browser | Yes | **Missing** |
| 3D Protein Viewer with variant overlay | Yes (SwissModel) | **Missing** (AlphaFold link only) |
| Publications: variant vs gene count split | Yes | **Missing** |
| Publications: PubMed + DOI + PDF + citations + tags + modal | Yes | **Partial** — PubMed list with abstracts |
| Community classifications / comments / link-publication | Yes | **Missing** (AskEamos chat parked) |
| Live activity stream on landing | Yes | **Missing** |
| Variant view counter | Yes | **Missing** |
| "Submit to ClinVar" funnel | Yes | **Missing** |
| Conservation track (phyloP100) | Yes | **Partial** — conservation in Workbench viewer |
| Expression Data (top tissue / count) | Yes | **Missing** |
| Active trials / approved therapies | Not visible on report | **Has** — ClinicalTrials.gov section (**Eamos advantage**) |
| Primer / CRISPR / Align / Compare tools | No | **Has** — Workbench (**Eamos advantage**) |
| Plain-language HGVS decoder | No (expert audience assumed) | **Has** (**Eamos advantage**) |
| Click-base consequence preview | No | **Has** — Workbench (**Eamos advantage**) |
| Cite + Feedback dock | Yes | **Missing** |
| Tiered Premium gating with PREMIUM pill | Yes | **Missing** — `/pricing` exists, no in-report gates |

### 9.1 Where Eamos already wins (structural advantages Varsome can't easily copy)

These are existing Eamos features Varsome lacks — they should anchor our
positioning copy, not get rebuilt:

1. **Plain-language hero search.** Codex's `SearchInputInterpretation`
   contract (see `app/backend/app/services/search_input_resolver.py` + the
   `/api/v1/lookup/parse` endpoint) parses raw inputs like
   `"CFTR Leu441 frameshift"` and returns ranked candidates with
   interpretation chips, auto-selecting when there's exactly one
   high-confidence match. Varsome's search is structured-only with
   "Examples" disclosure — users either know HGVS or fall off.
2. **AskEamos (parked, but conceptual category).** Variant-page-aware AI Q&A.
   Backend `/api/v1/chat` exists; FE stays COMING SOON until API key budget
   approved ([[feedback_askeamos_parked]]). Varsome has no equivalent —
   when unparked, this is a *category* differentiator, not just a feature.
3. **Workbench: Primer / CRISPR / Align / Compare tools.** None of these
   exist on Varsome at any tier. Plus the **click-to-edit base** in the
   sequence viewer with live consequence preview — unique to Eamos.
4. **Plain-language HGVS decoder.** Varsome assumes an expert audience.
   Eamos decodes `c.524G>T (p.R175L)` into plain-English semantics inline,
   lowering the barrier for non-specialist clinicians.
5. **ClinicalTrials.gov / approved therapies surfacing on the report.**
   Varsome doesn't connect variants to active trials or approved therapies
   on the report. Eamos already has this in §6 of the report layout.
6. **Reading Room design language (warm-white OKLCH, Spectral serif display,
   ruled column, GenomicFlow).** Generationally ahead visually — Varsome's
   chrome reads as 2015–2017.
7. **AU-first positioning.** Saphetor's APAC presence is via distributor
   (Sciencewerke) — no direct AU office. Eamos has AU domain (eamos.com.au)
   + AU ABN + AU healthcare regulatory familiarity.
8. **Source-cache architecture + local-first data-source strategy** (Codex
   lane). Reduces dependence on external API uptime, supports offline /
   sovereign-data deployments — Varsome is pure CSR-over-REST and has no
   equivalent story.

---

## 10. What Varsome does poorly — Eamos opportunities

1. **Mobile is broken and disclaimed.** The live HTML carries *"This website
   may not work correctly with your screen size"*. The 24-tile header grid
   doesn't survive below ~1100px and one-section-at-a-time on a phone loses
   the matrix overview at exactly the moment the user needs it.
2. **Premium-gated tiles indistinguishable from no-data tiles** at a glance —
   same grey. Information-density loss.
3. **Generic full-screen spinner** — no skeletons, no progressive paint on
   first load.
4. **Activity feed + "viewed 2,660 times" + "Connect with viewers"** smell of
   social-network LARPing on a clinical tool.
5. **No type hierarchy in the report** — every tile title is the same size +
   weight; the eye has nothing to grab.
6. **Dated chrome** — navy + green CTA, hard 1px borders, FontAwesome glyphs.
   Reads as 2015–2017.
7. **Publications section list view** is a wall of text with low-contrast
   tags; the long descriptions hurt scannability.
8. **No SSR for variant pages.** Hurts SEO depth (compensated by sitemaps +
   reCAPTCHA gate), cold-load perf, and users on slow networks.
9. **Section state is client-only** — sections aren't linkable or back-button-
   friendly.
10. **reCAPTCHA on the main variant URL** is hostile — kills sharing, kills
    LLM/agent traffic, kills paste-this-URL-into-ChatGPT workflows.
11. **Bundle weight** — pure CSR Angular SPA in 2026 is heavy. Our Next 16
    RSC + selective hydration should produce a smaller TTI on cold variant
    once benchmarked.

---

## 11. Steal candidates — ranked

(Action items and milestone mapping live in
`plans/v2-redesign-impeccable.md` §10 "Competitor steals." Summary here.)

### Tier 1 — high value, low-medium effort
1. **Publication modal (PubMed + DOI + PDF + citation count + abstract +
   backdrop blur)** — biggest single delight, cheap. Add focus-trap and a
   shareable URL pattern Varsome lacks.
2. **Variant-vs-gene publication count toggle** — one boolean state, huge
   perceived depth.
3. **Bottom-left global Feedback + Cite chip.** Cite = academic moat lynchpin.
4. **Horizontal stacked-count bar with inline numerals** on ClinVar /
   in-silico cards (red→yellow→green ramp we already have in OKLCH).
5. **ClinVar review-star glyph next to verdict** — clinical users expect it,
   free trust signal.
6. **Coloured left-edge accent on cards** — 3px left border in pathogenicity
   colour when a verdict exists; absent = no verdict.

### Tier 2 — high value, medium effort
7. **Card-matrix header on `/report`** — above-the-fold tile grid where each
   tile = section preview + nav target. Don't ape 24 tiles, aim for 10–12
   substantive ones. **Single biggest IA upgrade.** Use URL fragments or
   route segments so sections are linkable (the bug Varsome shipped).
8. **ACMG criteria as coloured pills (met / not met)** — grey not-met,
   ramp-coloured met. Replaces a legend with the colours themselves.
9. **Sticky variant ribbon with action cluster** (HGVS + Copy / Share /
   Export / Save / Cite).
10. **Calibrated in-silico verdict table** (composite bar + per-engine
    calibrated label + raw score + version stamp). Substantial upgrade to
    `InSilicoGrid` even with just 4 engines.
11. **ClinGen VCEP criteria-chip block with expert narrative** — most
    authoritative section on the page; ClinGen is the next public source
    after ClinVar.
12. **Premium-locked card pattern that *shows what's behind the wall*** —
    row labels visible, scores blurred / Premium-badged. Don't ship the
    "results incomplete unless you pay" modal — erodes trust.

### Tier 3 — strategic, longer effort
13. **Proprietary ACMG classification engine** — long-term moat;
    `AcmgCriteriaFold` is already scaffolded to attach a rules engine to.
14. **Publication index with LLM-assisted entity extraction over PubMed
    Central OA + Europe PMC** — variant-vs-gene counts, "Linked by:"
    provenance, tag chips. ~1 engineer-quarter to a credible v1 instead of
    Varsome's multi-year mining.
15. **SpliceVault top-4 mis-splice events.**
16. **3D Protein Viewer with variant-coloured overlay + magenta current
    variant** (NGL or Mol\* + AlphaFold/SwissModel).
17. **Region Browser multi-track depth** — DNA letters / conservation
    histogram / amino-acid strip / UniProt regions / pathogenicity lane.
    Workbench already has the viewer chassis.

### Anti-patterns to reject
- Full-screen spinner with no skeleton.
- "This website may not work correctly with your screen size" — design
  mobile-first from the start.
- "Viewed N times" + "Connect with past and future viewers" — wrong tone.
- Free-text user comments (moderation tax, cold-start ugly).
- Real-time activity strip until volume justifies it (cold start is brutal).
- "Warning: results incomplete unless you pay" upsell modal.
- reCAPTCHA on shareable variant URLs.
- Greying premium and no-data identically.
- Body type with serif (we already have this guard — Reading Room is
  display-only serif).

### Positioning wedge
Varsome's UX feels like 2018 with paid surcharges. Eamos's Reading Room
direction (warm-white OKLCH, Spectral display, ruled column, GenomicFlow) is
*visually* a generation ahead. Three structural advantages anchor the pitch
(see §9.1 for the full list):

- **"Clinical-grade interpretation that's actually readable"** — Reading
  Room vs. Varsome's Bloomberg-terminal density.
- **"AI-native search and Q&A"** — plain-language hero search (Codex's
  `SearchInputInterpretation` already ships) and AskEamos (parked but a
  category Varsome lacks entirely).
- **"Transparent free tier, no Premium gates on the answer"** — reject
  Varsome's "warning: results incomplete unless you pay" modal; gate
  *additional* sources, never the verdict.
- **AU-first** (eamos.com.au, AU ABN) — Varsome has a distributor here
  (Sciencewerke), not a direct presence.

---

## 12. Sources

- 33 screenshots in `c:\Users\seamegdool\Desktop\Claude code and website
  tips\EAMOS Web Tool\Competition\Varsome\` (referenced inline by filename).
- Live WebFetch on `https://varsome.com/` (landing) and
  `https://varsome.com/variant/hg38/NM_000546(TP53)%3AArg175Leu` (variant
  page — Cloudflare/reCAPTCHA-gated; HTML shell extracted).
- Saphetor public materials (CE-IVDR Class C certification, GA4GH membership,
  APAC distributor Sciencewerke, Kopanos et al. 2018 *Bioinformatics*).
- Synthesised from four parallel subagent lenses
  (UX/visual/IA · feature inventory · tech/perf · business/moat),
  2026-05-27 by Claude.
