# Align Tool — Product-Design Audit (`/workbench`)

> **Status:** 🟡 AUDIT — review-gated. No code lands until Steven OKs the §5 recommendations
> ([[feedback_subagent_recommendations_not_authorization]]). Lane 3 of the 2026-06-09 4-scout
> workbench audit (frontend-design + ui-ux-pro-max). Persisted by the main agent.

Surface: `app/web/components/workbench/align/**` + `workbench.css` (Align blocks). Ground truth read in full: `AlignPanel.tsx`, `ReadRow.tsx`, `PairwiseView.tsx`, `AlignedTrace.tsx`, `read-model.ts`, `abif-parser.ts`, `workbench.css:2011–2851`, tokens in `globals.css`. Skills applied: **frontend-design** (clinical-restraint lens), **ui-ux-pro-max** `--domain ux`/`chart` (cited inline as **[UPM]**). File-level grounding is from direct reads.

> **⚠️ Brief-vs-reality mismatch (read first).** The task brief describes the Align tool as "two SubjectSlots, a 5-tab source switcher, a swap ⇄, a single **Align** CTA (disabled-with-inline-reason), an A/B legend, a collapsed chromatogram `<details>`." **None of that is in the shipped code.** The live tool is a **reference + N-reads, live-auto-align** model: one reference card, one drop-zone for reads, and each read renders its own always-expanded result card with a live alignment (no Align button at all). The brief is describing an **older, retired design** whose CSS is still in the file but orphaned (see §2 / D1). I audited **what actually ships**. The gated spec `docs/workbench-align-msa/spec.md` confirms the current state matches my read.

---

## 1. Snapshot

The Align tool is a **client-side Sanger trace aligner**. A reference/template (auto-seeded from the loaded variant's gene window, or pasted/FASTA-uploaded) sits at top; the user drops one or more `.ab1` chromatograms (or pastes raw sequence) into a dropzone; each read is parsed in-browser (`abif-parser.ts`), **auto-oriented** to best-fit the reference (`bestOrientation`), **Q-trimmed**, and **live-aligned**. Each read becomes a card showing a metric strip (Identity/Coverage/Matches/Mismatches/Gaps/Ref-span/Read-span), a ◀▶ difference navigator, a shared-coordinate REF/READ/trace SVG (the read's peaks are warped so each peak sits under its base column — genuinely good), diff chips, and a het/low-Q quality readout. A FinchTV-style "Find sequence" motif search highlights hits across the reference. It renders in the **wide canvas slot** (`.canvas`, max 1440px, viewer collapses when `align` is active), so horizontal space is generous — not the 360px rail.

It is the most *algorithmically* accomplished tool in the Workbench. The biggest problems versus the Benchling/Apple bar:

1. **The result card has no internal visual hierarchy — it's a flat wall of 7 equal-weight metric tiles + chips + an unlabeled SVG.** The headline answer a user actually wants ("does my read match? where does it differ?") is buried among coordinate-span tiles that read at the same size/weight as Identity. Apple-grade means the eye lands on the answer in <1s; here it scans 7 tiles to assemble it. **[UPM Accessibility/Heading-Hierarchy]**.
2. **The trace SVG has no x-axis position ruler and no y-axis, and its channels are color-only.** **[UPM chart: Trend-Over-Time]** mandates "differentiate series by line style not color alone" + axis labels. There are no reference-coordinate ticks anywhere on the track, so a user cannot say "this mismatch is at position 412" by looking. The 4 trace channels are distinguished purely by `--base-*` hue (drops to D for CVD users on the signal itself).
3. **Discoverability of the power features is poor, and a large block of dead CSS signals design drift.** Mismatch ◀▶ nav only appears after you notice it; the trace **scale controls hide behind a 22px handle** with no label; the Q-trim/Full-read and Trace-shown/hidden toggles are unlabeled-intent text buttons; and ~540 lines of orphaned CSS sit unused.

---

## 2. Interactable inventory + verdict

Every interactive element in the live Align tool, in render order. (`AP`=AlignPanel, `RR`=ReadRow, `PV`=PairwiseView, `AT`=AlignedTrace.)

| # | Element | file:line | Purpose | Verdict | What to do |
|---|---------|-----------|---------|---------|-----------|
| 1 | **"Reset to {gene}"** button (ref) | AP `137-144` | Revert a custom reference to the gene-window seed | **KEEP** | Good — conditional on `reference.custom`. |
| 2 | **"Edit reference / Cancel"** toggle | AP `145-156` | Open the FASTA/paste editor | **IMPROVE** | Make it `aria-expanded`/`aria-controls` (it's a disclosure, not a mode). |
| 3 | **Reference `<textarea>`** | AP `160-166` | Paste FASTA/raw template | **KEEP** | `spellCheck=false` correct. |
| 4 | **"Upload FASTA"** file label | AP `168-179` | Load a `.fasta/.fa/.txt` reference | **KEEP** | Good — the label-wraps-hidden-input pattern (CRISPR's Outcomes tab should copy this). |
| 5 | **"Use this reference"** btn (`btn-teal`) | AP `180-187` | Commit the pasted reference | **KEEP** | `disabled={!refDraft.trim()}` correct. **But disabled state gives no reason** — add inline "Paste a sequence first". **[UPM Disabled-States]**. |
| 6 | **"Identifier search coming…"** hint | AP `188-190` | Tells user Entrez/Ensembl lookup is backend-pending | **KEEP** | Honest COMING-SOON copy. |
| 7 | **Add-reads dropzone** (drag+drop) | AP `202-231` | Drop `.ab1` files to add reads | **IMPROVE** | A thin one-line bar — doesn't read as a *drop target*. Enlarge + add an upload glyph; strengthen `.dragover`. |
| 8 | **"Choose .ab1 files"** btn (`btn-teal`) | AP `214-216` | File picker for reads | **KEEP** | Good. |
| 9 | **"Paste sequence"** toggle | AP `217-219` | Reveal the paste-a-read textarea | **IMPROVE** | Make it `aria-expanded`. Fine as secondary `.align-read-btn`. |
| 10 | **Paste-read `<textarea>`** | AP `234-239` | Paste raw read sequence | **KEEP** | Fine. |
| 11 | **"Add read"** btn (`btn-teal`) | AP `242-244` | Commit pasted read | **KEEP** | `disabled` w/o reason — same fix as #5. |
| 12 | **"Find sequence"** input | AP `263-273` | Motif search over reference (fwd+revcomp) | **KEEP** | Genuinely useful (FinchTV parity). |
| 13 | **◀ Previous match** (find) | AP `276-278` | Step to prev motif hit | **KEEP** | `aria-label` present. |
| 14 | **"N / M" / "No matches"** counter | AP `279-281` | Match position readout | **KEEP** | `tabular-nums` via `.align-find-count`. |
| 15 | **▶ Next match** (find) | AP `282-284` | Step to next motif hit | **KEEP** | `aria-label` present. |
| 16 | **"Clear"** (find) | AP `285-289` | Clear the search | **KEEP** | Fine. |
| 17 | **Base-colour legend A/C/G/T** | AP `302-308` | Names the `--base-*` colours | **KEEP** | Static, correct; the legend that makes the colour encoding legible. |
| 18 | **Orientation `<select>`** (4-way) | RR `103-115` | fwd / rev / complement / revcomp | **IMPROVE** | (a) native `<select>` glyphs (`→←↕⇄`) render in OS font on Windows, off-grammar; (b) no inline explanation of "complement" vs "reverse-complement" — most wet-lab users only need fwd/revcomp. Consider 2-way segmented + the rarer two behind "more", OR add `title` per option. |
| 19 | **"Q-trim / Full read"** toggle | RR `116-125` | Trim low-Q ends vs align whole read | **IMPROVE** | Valuable, but the label conflates state vs action. Use a stateful pattern: label = state, `.active` = on. |
| 20 | **"Trace shown / Trace hidden"** toggle | RR `126-135` | Show/hide chromatogram | **KEEP** (minor) | Same label-ambiguity, lower stakes. Gated to `.ab1` — correct. |
| 21 | **✕ "Remove read"** btn | RR `136-144` | Delete this read card | **KEEP** | `aria-label`+`title` both set; hover→`--err`. Exemplary. (Border hover uses raw `#f3c2c2` — token nit.) |
| 22 | **Mismatches metric (toggle)** | PV `158-165` | Click to show/hide mismatch chips | **IMPROVE** | Clever dual-purpose, but the toggle affordance is nearly invisible — a 9px `▸/▾` caret is the only cue. Give toggle-tiles a distinct affordance. |
| 23 | **Gaps metric (toggle)** | PV `166-173` | Click to show/hide gap chips | **IMPROVE** | Same as #22. Only a button when `gaps>0`. |
| 24 | **◀ Previous difference** | PV `85-87` | Step active diff (scrolls trace) | **KEEP** | Drives the active-ring + smooth-scroll. The single best interaction in the tool. |
| 25 | **"N / M" diff counter** | PV `88-90` | Active-diff position | **KEEP** | `tabular-nums`. |
| 26 | **▶ Next difference** | PV `91-93` | Step active diff | **KEEP** | Good. |
| 27 | **Active-diff label** (`ref 412: A→G`) | PV `94` | Names the current difference | **KEEP** | The most "answer-like" element; promote into the card lede (§4). |
| 28 | **Difference chips** (per diff) | PV `247-256` | Click a chip → jump+highlight | **KEEP** | Great pattern; `.active` ring + scrolls trace. |
| 29 | **Trace scale handle** (22px SVG btn) | AT `140-162` | Reveal peak-intensity + base-spacing sliders | **IMPROVE** | The two most powerful trace controls hide behind an **unlabeled 22px icon**. Discoverability fail — most users never find horizontal zoom. Add a visible "scale" micro-label or pin inline. |
| 30 | **Peak-intensity slider (↕)** | AT `167-171` | Vertical trace scale | **KEEP** | `accent-color: --teal`. Good once discovered (#29). |
| 31 | **Base-spacing slider (↔)** | AT `172-176` | Horizontal compression (moves bases+trace together) | **KEEP** | The shared-coordinate warp is the standout feature. Surface it (#29). |
| — | **Orphaned controls in CSS, never rendered** | css `2475–2672` | (old SubjectSlot/swap/run-button design) | **REMOVE** | `.align-subjects`, `.align-slot*`, `.align-swap`, `.align-run-btn/-reason`, `.align-block-legend`, `.align-trace-disclosure/-summary`, `.align-source-grid/-card/-head`, `.align-status`, `.align-target-card/-pill`, `.chromatogram-base(s)/-qc`, `.align-trace-svg/-basecall-strip` — **0 references** in any `align/*.tsx`. Dead (D1). |

**Net:** No control should be *removed for being purposeless* — every rendered interactable earns its place (this tool is lean). The improvements are about **legibility, label honesty, and discoverability**, plus deleting the dead CSS.

---

## 3. Legibility / visual-hierarchy findings (grounded, token-anchored)

**[L1] The 7-tile metric strip is flat — no primary, no answer.** `PairwiseView.tsx:141-184`, css `.align-summary` `2192-2195`, `.align-metric` `2197-2223`. All 7 metrics render at identical weight/size. Fix: tier them. Promote **Identity** + **the single active-difference label** into a card lede at `--ink` ~15–16px; demote Ref-span/Read-span to a `--ink-4` 11px caption row. The tone classes (`b.ok`/`b.err`/`b.warn`, `2221-2223`) exist but apply emphasis via size, not just colour.

**[L2] The trace has no positional axis.** `AlignedTrace.tsx` — no `<text>` ruler; coordinates only live in diff chips. **[UPM chart]** requires an axis. Fix: render sparse reference-coordinate ticks (every 10 cols) as `--ink-4` 9px mono `<text>` above `REF_Y` (vertical room exists: `Q_TOP=2`, `REF_Y=22`). Without this, "where is this difference" is unanswerable by eye.

**[L3] Trace channels are color-only (CVD-inaccessible signal).** `AlignedTrace.tsx:223-226`, css `.align-trace-channel.{A,T,C,G}` `2414-2417` (stroke = `--base-*` only). The bands + base letters are fine (they carry position/letter), but the overlaid signal polylines are pure hue. Fix: add per-channel `stroke-dasharray`, or document that the called bases are labeled. Lower priority than L1/L2.

**[L4] Het marker is color-only and uses raw hex.** `AlignedTrace.tsx:250-252` (`.chromatogram-het` rect), css `2833` (`fill: #7c5cd6`), `.tag-het` `2851`. A heterozygous call — clinically load-bearing — is signaled solely by a purple band + purple count, no glyph/shape. Fix: (a) add a non-colour cue (1px dashed top edge on the het rect, or a double-peak tick); (b) name the colour once: `--wb-het`, or re-point to `--info-dot` (oklch indigo, CVD-checked, `globals.css:118`). **Flagged in the prior sweep and still unfixed.**

**[L5] Search highlight is a brand-new ungrounded gold.** css `.align-base.search` `2713`, `.search-active` `2714-2718`, `.aln-band.search` `2792-2793` — all `rgba(212,175,55,…)` + outline `#b8860b`. This gold exists nowhere else in the palette. Fix: reuse `color-mix(in oklab, var(--warn) …%, transparent)`, or name `--wb-find` once.

**[L6] Dead chromatogram classes carry the *old* off-token red.** css `.chromatogram-band` `2831` = `rgba(193,58,52,.18)` — a near-miss of `--err`, unused by the live `AlignedTrace` (which correctly uses `color-mix(var(--err) 18%)`). Goes with D1.

**[L7] `formatRange` off-by-one inconsistency.** `PairwiseView.tsx:275-278` returns `${start+1}-${end}`, while `differenceLabel` (`261-269`) uses `referenceIndex+1`/`editedIndex+1`. The spans and the active-diff label use subtly different conventions side-by-side — verify they're consistent for a user cross-referencing span vs chip. Not a styling fix; worth a glance.

**[L8] Native `<select>` orientation glyphs render off-grammar on Windows.** `ReadRow.tsx:23-28`, css `.align-read-select` `2760-2766`. The collapsed select shows the active glyph in the OS UI font. Acceptable for a native control; the fix (custom listbox) is structural → §5.

---

## 4. Flow + eye-guidance (Apple-like seamlessness)

The happy path is **pick reference → drop read → read auto-aligns → read result → navigate diffs**. It mostly works because alignment is live (no Align button to forget). Concrete fixes:

**[F1] Give each result card a lede that *states the answer*.** Restructure the top of `.align-read-card` (`ReadRow.tsx:58-101` head + `PairwiseView` Summary) so the first line reads like a sentence: **"96.2% identity · 1 difference (ref 412 A→G) · 1 het"** with Identity prominent and the active-diff label inline — the data already computed in `differenceLabel` (PV `94`) + head meta. Today that label is buried *below* the metric grid; promote it.

**[F2] Make the difference navigator the visual focal point.** The ◀▶ + active label (PV `83-96`) is the most valuable interaction but sits as a thin row between the metric grid and the trace. Pull it up next to Identity (F1); when there are 0 diffs the "No mismatches or gaps" note (PV `237`) should be a confident green confirmation, not a muted aside — it's the *good* answer.

**[F3] Surface the trace-scale controls instead of hiding them behind a 22px handle.** `AlignedTrace.tsx:140-177`. The horizontal-spacing slider is *the* feature (peak-aligned warp), yet hidden by default (`controlsOpen=false`). Show a compact, labeled scale affordance inline on first render, or persist `controlsOpen` once used. Keep the gating to real `.ab1` traces (correct).

**[F4] Strengthen the dropzone as the primary entry affordance.** `AlignPanel.tsx:202-231`, css `.align-add` `2696-2703`. The first action is "drop a read," but the dropzone is a 1-line bar with a permanent thin dashed border. Make it taller with a centered upload glyph + "Drop .ab1 reads or browse", and make `.dragover` a bolder teal fill.

**[F5] Reduce label ambiguity on the per-read mode toggles (#19/#20).** "Full read" / "Q-trim" / "Trace shown" / "Trace hidden" conflate state and action. Adopt one stateful convention: the label names the **state**, the `.active` class shows it's on (the `.align-read-btn.active` style exists, css `2756`).

**[F6] Motion/a11y seam — smooth-scroll is not reduced-motion-guarded.** `AlignedTrace.tsx:113` uses `behavior: 'smooth'`, and the parsing spinner `@keyframes align-spin` (css `2173`) runs unconditionally. The workbench reduced-motion block (`workbench.css:210-212`) only covers the zoom overlay. DESIGN.md (`99`, `626`) mandates the `prefers-reduced-motion` guard. Fix: gate the smooth-scroll behind `matchMedia('(prefers-reduced-motion)')` (→ `'auto'`), and add the spinner to the reduced-motion block.

---

## 5. 🟡 Durable / structural recommendations (gated — need Steven's OK before code)

Ranked by leverage:

1. **D1 — Delete the orphaned Align CSS (~540 lines, `workbench.css:2475–2672` + scattered `.chromatogram-base(s)/-qc/-dim/-band`, `.align-target-*`, `.align-row/-mark/-base*`, `.align-trace-svg`).** Verified **zero references** in any `align/*.tsx`. The retired SubjectSlot/swap/run-button design the task brief describes. **Highest leverage, lowest risk** — pure deletion, shrinks the file, removes the consistency hazard and the near-miss-red/gold raw hex that lives only in dead rules. Recommend a dedicated "Align dead-CSS sweep" commit. *(Confirm no other surface imports these — grep says align-only.)*

2. **D2 — Restructure the result card into a 3-tier hierarchy (lede → strip → details).** The core of §1/§4. Promote Identity + active-diff into a sentence-lede; keep 5 core stats as a strip; demote Ref/Read-span to a caption. Pairs with the prior sweep's **C5 "unify the result-card primitive across Primer/CRISPR/Align"** — do them together.

3. **D3 — Add a reference-coordinate ruler to the trace track (L2).** Sparse mono ticks every N columns. The single biggest legibility win for "where is this difference."

4. **D4 — Name the off-token colours once (`--wb-het`, `--wb-find`) or re-point to `--info-*`.** Resolves L4+L5 and the het a11y. Recommend **re-pointing to existing `--info-*`** over net-new tokens unless a distinct het hue is clinically required.

5. **D5 — Replace the native orientation `<select>` with a custom listbox** (and consider collapsing 4-way → fwd/revcomp + "more") (L8 / #18). Lowest leverage, highest churn — defer unless Steven wants the polish. `bestOrientation` already makes manual orientation rare.

6. **D6 — (Forward pointer) The gated `docs/workbench-align-msa/spec.md` stacked-MSA redesign** would supersede the per-read-card model entirely. If greenlit, D2/D3 should fold into that effort rather than be done twice.

---

**Files for the caller:** `align/{AlignPanel,ReadRow,PairwiseView,AlignedTrace,read-model,abif-parser}.tsx`; styles `workbench.css` (active Align `2674–2851`; **dead** Align `2475–2672`); tokens `globals.css` (`--base-*` 124-127, `--info-*` 115-118, `--z-*` 190-197, `--dur-*`/`--ease-*` 177-183); reduced-motion gap `workbench.css:210-212`. Prior art: `docs/workbench-report-sweep/workbench-tools.md` (Align P1/P2 — L4/L5 flagged there, still unfixed), gated redesign `docs/workbench-align-msa/spec.md`.
