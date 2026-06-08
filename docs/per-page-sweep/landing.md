# Landing page (`/`) — UI/UX sweep

Surface: marketing/entry page. Brand register ("Reading Room" warm-paper, cream
L2/L3 page-turn rhythm). Assessed against `DESIGN.md` + `app/web/app/globals.css`
tokens, with `frontend-design` craft principles and `ui-ux-pro-max` guidance
(landing, ux, typography, color domains).

Scope note: this is a **polish/consistency** sweep, not a redesign. Findings match
the existing idiom; structural/visual changes are quarantined in §4.

---

## 1. Surface map

| File | Role |
| ---- | ---- |
| `app/web/app/page.tsx` | Route shell — renders `<LandingClient/>`. |
| `components/landing/LandingClient.tsx` | Page composition: hero (badge, h1, subhead, search, Try chips) + section order. |
| `components/landing/LandingNav.tsx` | Sticky brand nav — logo, centered links ⇄ pinned compact search (GSAP scroll handoff), AuthMenu, mobile menu. |
| `components/landing/EamosSearch.tsx` | The one freeform search bar (hero + compact). Paperclip attach, drag-drop, submit. The page's primary action. |
| `components/landing/GenomicFlow.tsx` | Hero backdrop — abstract twin-strand SVG flow + warm halo. |
| `components/landing/SourceStrip.tsx` | "Powered by" source pill row. |
| `components/landing/MetricBelt.tsx` | "How the evidence reads" — four-call-card report specimen ("open page"). |
| `components/landing/HowItWorks.tsx` | 3-station 3/6/3 asymmetric grid with mono code-block visuals. |
| `components/landing/FeaturesGrid.tsx` | gnomAD map hero + asymmetric screenshot grid + Workbench "in development" tile. |
| `components/landing/Testimonials.tsx` | Founder quote block. |
| `components/landing/Pricing.tsx` | Audience toggle + 3 plan cards / enterprise card. |
| `components/landing/Faq.tsx` | Accordion (4 Q/A). |
| `components/landing/SiteFooter.tsx` | Logo, 3 link columns, legal row. |
| `components/landing/ui/LandingHeading.tsx` | Canonical `LandingH2` / `LandingH3`. |
| `components/landing/ui/Pill.tsx` | Shared `.eamos-pill` + hover/focus styles. |
| `components/landing/ui/TextLink.tsx` | Shared `.eamos-text-link` + hover/focus styles. |
| `components/landing/Reveal.tsx` | Scroll fade-and-rise wrapper. |

Token defs (`globals.css`): hero `oklch(96–98% …)` cream stops; `--em` teal axis;
`--page-bg / -deep / -card / -line` warm-paper register.

---

## 2. Findings

### P0 — broken / jarring

**F1 · Anchor links jump under the sticky nav (no scroll-padding).**
`LandingNav.tsx:174-184` + `SiteFooter.tsx:34-37` link to `#features`, `#how`,
`#faq`, `#pricing`; the nav is `position: sticky; height: var(--nav-h)` (60px,
`LandingNav.tsx:96,113`). No `scroll-padding-top` exists anywhere
(`globals.css` — confirmed absent), so every in-page jump lands ~60px too high and
the section heading is hidden behind the bar. Also no `scroll-behavior: smooth`, so
the jump is instant.
*Violates:* ui-ux-pro-max ux `Smooth Scroll` (Severity High — "Anchor links should
scroll smoothly to target section") and `fixed-element-offset` ("Fixed navbar must
reserve safe padding for underlying content"). **P0** (every nav/footer anchor is affected).

**F2 · Hero subhead and two card metas are missing terminal punctuation.**
`LandingClient.tsx:99` ("…one clear, sourced report" — no period),
`FeaturesGrid.tsx:73-76` gnomAD caption *does* end in a period but
`MetricBelt.tsx:119-125` intro paragraph ends "…the source it came from." (OK)
while the hero subhead and the Workbench caption mix styles. The hero subhead is the
most-read sentence on the page and reads as truncated. *Violates:* frontend-design
copy precision / editorial polish. **P0** (hero is the focal sentence).

### P1 — clear polish wins

**F3 · Hardcoded hex / rgba that duplicate or bypass tokens.**
Multiple brand-surface components hand-roll colours that a token already covers:
- `MetricBelt.tsx:76` `border: '#cbe3d8'` = the existing `--teal-bdr` token
  (`globals.css:69`). Same value, should be `var(--teal-bdr)`.
- `MetricBelt.tsx:78` source badge `bg:'#eef6ff' border:'#c9ddf5' color:'#1d4f7a'`
  and `:265` warning text `'#7a4b10'`, `:79` `'#633806'` — these are the
  Population/source "info-blue" + warn-text values. `globals.css` already ships
  `--info-bg/-text/-bdr` (`:115-118`) and `--warn-text` (`:75`); the info pills
  here predate those tokens and now duplicate them off-token.
- `HowItWorks.tsx:99,129` `'#04140e'`, `Pricing.tsx:251,303,349` `'#04140e'`,
  `EamosSearch.tsx:31` `'#04140e'` — the "ink-on-teal" CTA text colour is repeated as
  a raw hex in 4 files with no shared token.
- `FeaturesGrid.tsx:157,189` `rgba(16,185,129,…)` and
  `EamosSearch.tsx:27-29,44-49` `rgba(52,211,153,…)`/`rgba(16,185,129,…)` glows —
  emerald-500/400 literals, not the `--em` axis.
*Violates:* DESIGN.md "Tokens, not magic numbers" + ui-ux-pro-max `color-semantic`
("Define semantic color tokens … not raw hex in components"). **P1.**

**F4 · HowItWorks code-blocks use near-black `rgba(0,0,0,.22–.32)` on a cream
ground.** `HowItWorks.tsx:129` (`rgba(0,0,0,0.32)` featured / `0.22` bookends).
On the `--page-bg-deep` cream section this paints a muddy charcoal panel — it's the
only near-black surface on the entire landing and breaks the warm-paper register
(everything else is cream/teal/ink). The mono text inside is `--hero-ink-2` (a warm
dark), which on a 22–32% black overlay sits at borderline contrast. *Violates:*
DESIGN.md "No pure black (#000000)" + warm-paper consistency; ui-ux-pro-max
`consistency` / `color-accessible-pairs`. **P1.**

**F5 · Two competing eyebrow/kicker systems — editorial-template fingerprint.**
DESIGN.md typography §"Editorial-template guard" says *at most one* deliberate kicker
on the page (the hero badge). The hero has its badge (`LandingClient.tsx:46-70`,
correct), but `HowItWorks.tsx:108-113` adds a per-step uppercase tracked kicker
("Single query" / "Parallel sweep" / "Instant rendering"). Per the guard these
in-card *step* kickers are explicitly allowed ("step kickers … are not section
grammar and are fine") — so this is **borderline, not a violation**. The real
inconsistency: `MetricBelt.tsx:208-217` card titles are `10px/700/uppercase` mono-ish
labels, while `HowItWorks` step kickers are `10.5px/600/uppercase` and `SiteFooter`
column labels are `10.5px/600/uppercase` and `SourceStrip` "Powered by" is
`10.5px/600/uppercase` — four *almost*-identical micro-label specs (10/10.5px,
600/700, 0.08–0.16em tracking) that should be one. *Violates:* DESIGN.md
"one canonical type spec per role"; ui-ux-pro-max `font-scale`. **P1.**

**F6 · Section vertical rhythm is nearly uniform `py-28`, flattening hierarchy.**
`MetricBelt` `py-28`, `HowItWorks` `py-28`, `FeaturesGrid` `py-28`, `Testimonials`
`py-28`, `Pricing` `py-28`, `Faq` `py-28`; only `SourceStrip` (`py-9`) and the hero
(`96px 0 112px`) differ. Every major section gets identical 112px top+bottom padding,
so the page reads as undifferentiated bands — there's no spacing cue for "this section
is a peer vs. a climax." frontend-design + ui-ux-pro-max `whitespace-balance` ("use
whitespace to … separate sections") favour a small rhythm tier (e.g. lighter padding
on the short FAQ/Testimonial, heavier around the Pricing climax). **P1** (this is a
refinement, not a bug — keep `py-28` as the base, vary 1–2 sections).

**F7 · Pricing price figures aren't tabular; plan-card price uses mono but the
audience toggle can shift width.** `Pricing.tsx:150-160` prices are
`var(--mono)` (good, mono is tabular by default), but the `$0` free price vs `$XX`
paid prices have different glyph counts and the cards rely on `formatAud`. Minor.
The larger gap: `MetricBelt.tsx` metric badges ("Max AMR 0.182%", "AC 2357") are
`var(--bg-soft)` proportional Inter (`:77`), not mono — numeric metrics in a
data-specimen context read better tabular. *Violates:* ui-ux-pro-max `number-tabular`
("Use tabular/monospaced figures for data columns … to prevent layout shift"). **P1.**

**F8 · EamosSearch `light` tone uses raw `rgba(15,23,42,…)` slate shadows.**
`EamosSearch.tsx:44,48-49` `glowFocus/glowHero/glowHover` are
`rgba(15,23,42,…)` — that's cool slate (`#0f172a`), the exact thing the Reading-Room
migration moved *off* ("never slate", `globals.css:48`). On the warm-cream hero the
focus ring's teal part is correct (`rgba(29,158,117,…)`) but the drop-shadow base is
cool. The dark tone (`:27-29`) is even further off-palette (`rgba(0,0,0,.7)` +
emerald literals). *Violates:* DESIGN.md "No ad-hoc box-shadow — depth only via
`--elev-*`" + warm-neutral mandate. **P1** (the search is the hero element; its glow
should sit on the warm/`--em` axis).

### P2 — nice-to-have

**F9 · Hero "Try" chip divider is a literal `|` glyph.**
`LandingClient.tsx:126-132` renders a pipe character at `opacity:0.5` as a separator
between the example chips and the Sample-VCF action. A 1px hairline
(`--hero-line`) `<span>` would read cleaner and match the surface's hairline grammar.
**P2.**

**F10 · MetricBelt empty/missing states say "No badges reported" / "Missing source".**
`MetricBelt.tsx:255-257` + the Computational card's `'computational_annotations_not_found'`
warning are honest, but on a *marketing specimen* a "Missing source" / "No
Computational Data" card is the first thing a prospect reads as a negative. This is a
hand-authored constant (`:52-60`), not live data — consider a specimen variant whose
Computational card is populated, OR soften the empty copy. *Borderline product
decision — flagged, not specced.* ui-ux-pro-max `empty-states`. **P2.**

**F11 · `<blockquote>` opening curly-quote is a separate 48px decorative glyph
above the quote.** `Testimonials.tsx:23-25` stacks a standalone `"` then the
blockquote — visually fine, but the glyph is `aria-hidden` *and* the blockquote text
also begins mid-sentence with no quote, so the decoration floats. Minor. **P2.**

**F12 · Hero subhead measure is wider than ideal.** `LandingClient.tsx:95`
`maxWidth: 580` at 18px ≈ 70–80 chars/line on desktop — slightly above the 60–75
sweet spot. ui-ux-pro-max `line-length`. **P2** (tighten to ~520).

---

## 3. Implementation spec (P0/P1)

**F1 — scroll-padding + smooth scroll.** In `globals.css`, add to the `html` rule
(`globals.css:313`):
```css
html {
  background: var(--bg-soft);
  scroll-padding-top: calc(var(--nav-h) + 12px);   /* clear the sticky nav */
  scroll-behavior: smooth;                          /* reduced-motion guard at :349 already resets to auto */
}
```
No component change needed; `--nav-h` (60px) already exists (`globals.css:145`).

**F2 — hero subhead punctuation.** `LandingClient.tsx:99`:
`…returns one clear, sourced report` → `…returns one clear, sourced report.`
Audit the other section subheads for the same and make terminal punctuation
consistent (the gnomAD/MetricBelt paragraphs already end in periods — match them).

**F3 — replace duplicate hex with tokens.**
- `MetricBelt.tsx:76` `border: '#cbe3d8'` → `border: 'var(--teal-bdr)'`.
- `MetricBelt.tsx:78` source badge → `bg:'var(--info-bg)' border:'var(--info-bdr)'
  color:'var(--info-text)'` (the info-blue token trio, `globals.css:115-118`).
- `MetricBelt.tsx:79` warning `color:'#633806'` → `var(--warn-text)`;
  `:265` `'#7a4b10'` → `var(--warn-text)` (both are the dark-amber warn text).
- Add one shared token for ink-on-teal CTA text. In `globals.css` `:root`, after
  `--em-tint` (`:241`): `--em-ink: #04140e;  /* text on a solid --em fill */`.
  Then replace `'#04140e'` with `var(--em-ink)` in
  `HowItWorks.tsx:99`, `Pricing.tsx:251,303,349`, `EamosSearch.tsx:31` (sendIcon).
- `FeaturesGrid.tsx:157` radial `rgba(16,185,129,0.10)` →
  `color-mix(in oklab, var(--em) 10%, transparent)`;
  `:189` `rgba(16,185,129,0.12)` → `color-mix(in oklab, var(--em) 12%, transparent)`.

**F4 — recolour HowItWorks code-blocks to the warm register.**
`HowItWorks.tsx:129` `background: isFeatured ? 'rgba(0,0,0,0.32)' : 'rgba(0,0,0,0.22)'`
→ use the deeper cream inset, not black:
`background: isFeatured ? 'var(--page-bg-deep)' : 'var(--page-bg)'` with the existing
`0.5px solid var(--hero-line)` border, OR a faint teal wash
`color-mix(in oklab, var(--em) 6%, var(--page-card))`. Keep the mono text but darken
it to `--hero-ink` for contrast on the lighter ground (`:135` `color:'var(--hero-ink-2)'`
→ `'var(--hero-ink)'`; the last-line teal accent at `:143` stays `--em-bright`).

**F5 — unify the micro-label spec.** Pick one canonical eyebrow/label token-set and
apply to `SourceStrip` "Powered by", `SiteFooter` column titles, `HowItWorks` step
kickers, and `MetricBelt` card titles: `fontSize: 10.5px; fontWeight: 600;
letterSpacing: 0.12em; textTransform: uppercase; color: var(--hero-ink-3)` (the
SourceStrip/HowItWorks value is the most common — converge the other two onto it).
Note `MetricBelt.tsx:210-214` is `10px/700/0.08em/--ink-4`; bump to the shared
`10.5/600/0.12em`. (Small, mechanical; consider a tiny `LandingEyebrow` primitive
under `components/landing/ui/` mirroring the LandingHeading pattern — **see §4**, as
adding a primitive is a structural choice.)

**F6 — section rhythm tiers.** Keep `py-28` as the base. Reduce the two *short*
sections to `py-24` (`Faq.tsx:45`, `Testimonials.tsx:7`) and keep Pricing/HowItWorks/
Features at `py-28`. This is a one-class change per file (`py-28` → `py-24`); do not
restructure. Optional and reversible — apply only if it reads better in browser.

**F7 — tabular metric badges.** `MetricBelt.tsx:236-251` metric badge `<span>`: add
`fontVariantNumeric: 'tabular-nums'` to the badge style (cheap, no font swap) so
"0.182%" / "2357" align. Leave `source`/`acmg` badges as-is.

**F8 — warm the search glow.** `EamosSearch.tsx` `TONES.light` (`:44-49`): replace the
`rgba(15,23,42,…)` shadow bases with the warm ink used by elevation tokens, or simplify
to the tokenized elevation + teal ring:
`glowFocus: 'var(--elev-1), 0 0 0 4px color-mix(in oklab, var(--em) 16%, transparent)'`,
`glowHero: 'var(--elev-1)'`,
`glowHover: 'var(--elev-2), 0 0 0 4px color-mix(in oklab, var(--em) 16%, transparent)'`.
This puts the search depth on `--elev-*` (DESIGN.md mandate) + the `--em` ring axis.
For the `dark` tone (`:27-29`) swap the emerald literals to
`color-mix(in oklab, var(--em) 14–55%, transparent)` and drop `rgba(0,0,0,.7)` to a
warm-ink shadow; keep the values visually equivalent.

**F9 — replace pipe glyph with a hairline.** `LandingClient.tsx:126-132`: swap the
`|` `<span>` for `<span aria-hidden style={{width:1,height:14,
background:'var(--hero-line)'}} className="mx-1" />`.

---

## 4. Flagged — needs Steven approval (do NOT default-do)

- **A new `LandingEyebrow` primitive** (F5 cleanup). Adding a shared component under
  `components/landing/ui/` is a structural/system change (parallels LandingHeading).
  The *recolour/unify of existing labels* is safe polish; introducing the new
  primitive is the part to confirm.
- **F6 spacing-tier change.** Altering section padding shifts the page's overall
  vertical proportion — a visible, durable rhythm change across the surface. Spec'd as
  reversible/optional; get a browser look + OK before shipping.
- **F10 specimen content.** Changing the MetricBelt specimen variant (so the
  Computational card isn't empty) or softening "Missing source"/"No Computational
  Data" copy is a product/marketing decision, not a polish call.
- **HowItWorks code-block surface (F4) — visual direction.** Recolouring the only
  near-black panels on the page to cream is correct per DESIGN.md, but it's a
  noticeable visual shift in a hero-adjacent section; confirm the cream/teal-wash
  direction before applying.

---

## 5. Don't-touch (intentional)

- **No `backdrop-filter: blur` on the sticky nav / mobile menu / search.** Deliberate
  (`LandingNav.tsx:104-106,239-241`, `EamosSearch.tsx:32-34,52`) — DESIGN.md bans it
  on sticky/overlay elements (mobile typing lag). The opaque `--nav-bg` is correct.
- **No `translateY` lift on pricing cards / pills.** `Pricing.tsx:30-37` border-only
  hover is user-mandated (DESIGN.md "Banned hover affordances", 2026-05-26).
- **Asymmetric grids** (HowItWorks 3/6/3, FeaturesGrid 4/2 + full-width) are
  deliberate anti-template layout, not misalignment.
- **`prefers-reduced-motion` guard** is present and global (`globals.css:349-355`);
  every motion component (`Reveal`, `GenomicFlow`, `Faq`, nav GSAP) honours it.
- **Sequence/AA/classification hex tokens** in `globals.css` (`--base-*`, `--aa-*`,
  `--cls-*`) are canonical product tokens — not landing concerns, leave alone.
- **`--em-deep: #156b50` as a hex** (`globals.css:238`) is the brand-teal-deep anchor,
  intentionally a fixed hex (logo equity), not a candidate for OKLCH conversion.
- **HGVS in mono** in MetricBelt header (`:149-157`) — per the task brief the HGVS→Inter
  move is being handled by the orchestrator; not reported here.
