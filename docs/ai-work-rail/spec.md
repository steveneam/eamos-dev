# Ask Eamos — AI Work-Rail Mode

> **Status:** spec for review (authored 2026-06-11, Claude FE). Structural change
> to persistent chrome (the shared `<WorkRail>`) + the /report layout — needs
> Steven's go before code ships. Grounded in the real components:
> `components/layout/{WorkRail.tsx,work-rail.css,RailFoot.tsx}`,
> `components/auth/AuthMenu.tsx`, `components/aistack/{AIStack,EvidenceSummary,AskEamos}.tsx`,
> `components/report/ReportClient.tsx`. ui-ux-pro-max `ux` pass applied (see §2).

## 1. Problem & intent

Steven (2026-06-11): the **Ask Eamos LLM should appear via an AI toggle at the top
of the work-rail** — toggling it dedicates the whole rail to the chatbot/LLM, with
the option to **expand the rail to ~half the page**. The **account cluster** at the
rail foot should read as a compact **icon** (Claude-desktop sidebar grammar) and
**must disappear while in AI mode**. And — **all of §8 (the AI evidence summary)
moves out of the report bottom into that AI rail**: "having the AI summary towards
the bottom doesn't really do anything for productivity."

Constraints carried in:
- The chat is **imminent, not parked**: Steven is starting the AI-gateway build soon
  (`Wiki/product/ai-gateway-build-{kickoff,dossier}.md` — the variant chat is
  **feature 6, the RAG chatbot**: Vercel AI SDK v6 `useChat`/`streamText`, Llama-3.3-70B
  via the gateway, Render-brokered SSE behind the de-ID boundary, pgvector citations).
  So build the rail **real-ready, not a dead placeholder**: `AskEamos` already streams
  via `streamChat(runId, …)` gated on `runId`, so lighting it up is a backend wiring
  flip, not a frontend rebuild. Today (no endpoint) it renders its honest disabled
  state ("Variant-aware chat is coming. We're wiring it to this report next."). The
  **AI evidence summary is deterministic** (real, source-anchored) and renders now.
- `<WorkRail>` is **shared** by /report, /workbench, /compare. The AI capability is
  added to the shared shell but **only /report wires it** for now (it owns the AI
  summary payload). Surfaces that don't pass an AI panel are visually unchanged.
- Reading-room vocabulary (DESIGN.md): `--bg` surface, 0.5px `--line` hairlines,
  `--ink*` text ramp, `--teal*` brand, `--dur-1/2` + `--ease-standard/emphasized`
  motion, `--z-*` stacking scale, `--r-sm/md/lg` radii. Tokens, never hex.

## 2. UX guardrails (ui-ux-pro-max `ux` pass)

| Rule | Applied as |
| --- | --- |
| **Navigation · Active State** | The mode toggle is a segmented control; the active mode gets a teal-tint fill + sharp `--ink` label, the inactive a muted `--ink-3`. Never color-only — the active fill + weight both signal. |
| **Layout · Z-Index Management** | Expanded rail and drawer use the existing `--z-rail` / `--z-drawer` / `--z-scrim` scale — no arbitrary z-values. |
| **Animation · Duration / Easing** | Mode + width changes ride the rail's existing `flex-basis/width` `--dur-2 --ease-emphasized` transition; the body cross-fades ≤200ms. |
| **Animation · Reduced Motion** | `prefers-reduced-motion` already disables rail transitions in work-rail.css; extend the rule set to the new AI elements. |
| **Feedback · Empty States** | The parked chat shows a *guiding* coming-soon state (what it will do + a disabled, explained input), not a dead box. |
| **Forms · Disabled states** | Chat input keeps `disabled` + reduced emphasis + the "Coming soon" pill (already in `AskEamos`). |
| **Touch targets ≥44px** | Toggle segments, expand button, account icon all ≥44px hit area (hit-slop where the glyph is smaller). |
| **Primary action** | The rail has ONE primary affordance per mode: in Library it's the search/sections; in AI it's the chat input. Account is subordinate (foot, muted). |

## 3. State model

The rail gains a **mode** and an AI-only **width**, orthogonal to the existing
collapse/drawer machinery:

```
mode      : 'library' (default) | 'ai'
aiWide    : false (rail width) | true (~half page)      // only meaningful when mode==='ai'
collapsed : existing 48px icon-rail (inline, ≥1200)     // unchanged
drawer    : existing off-canvas overlay (<1200)         // unchanged
```

Width resolution (`--rail-live-w`, published for the sticky ribbon offset):

| State | inline width | drawer width |
| --- | --- | --- |
| library / ai (narrow) | `--rail-w` 336px | `min(336px, 86vw)` |
| ai + wide | `--rail-w-ai` = `min(52vw, 760px)` | `min(560px, 94vw)` |
| collapsed | 48px | n/a |

**Persistence:** mode + aiWide are **ephemeral React state** (default `library`,
not wide) — each report opens in Library mode (the primary nav). Collapse pref
keeps persisting as today. *Deep-link / persist of AI mode is parked as a future
nice-to-have (ux Deep-Linking rule) — not v1.*

## 4. The toggle — top of the rail

The rail **head** today is `[ ‹collapse chevron› · TITLE · ‹action› ]`. The static
`TITLE` is replaced by a **segmented mode toggle**; in AI mode an **expand-width**
button appears in the action slot:

```
LIBRARY MODE (default, 336px)              AI MODE (336px)                    AI MODE · WIDE (~half page)
┌─────────────────────────────┐   ┌─────────────────────────────┐   ┌───────────────────────────────────────────┐
│ ‹  [▤ Library |✦ Ask Eamos] │   │ ‹  [▤ Library|✦ Ask Eamos] ⤢│   │ ‹  [▤ Library | ✦ Ask Eamos ]            ⤡ │
├─────────────────────────────┤   ├─────────────────────────────┤   ├───────────────────────────────────────────┤
│ SAVED VARIANTS              │   │ ✦ Ask Eamos   RPE65:c.260A>G│   │ ✦ Ask Eamos              RPE65:c.260A>G    │
│ FOLDERS                     │   │ ───────────────────────────│   │ ──────────────────────────────────────────│
│ RELATED VARIANTS            │   │ AI EVIDENCE SUMMARY         │   │  AI EVIDENCE SUMMARY                        │
│ ON THIS PAGE                │   │ Synthesised from sources…   │   │  Synthesised from the source databases…     │
│                             │   │ RPE65 c.260A>G; ClinVar     │   │  RPE65 c.260A>G; ClinVar classification:    │
│                             │   │ Uncertain significance; 10  │   │  Uncertain significance; 10 publications.   │
│ ··· (sections) ···          │   │ publications identified.    │   │                                             │
│                             │   │ ───────────────────────────│   │  ─────────────────────────────────────────│
├─────────────────────────────┤   │ ✦ Ask about this variant    │   │  ✦ Ask Eamos about this variant  [SOON]     │
│ [N] account ▾   ‹icon-led›  │   │ [ chat is coming … ]  ↑(off)│   │  [ Variant-aware chat is coming …  ] ↑(off) │
└─────────────────────────────┘   └─────────────────────────────┘   └───────────────────────────────────────────┘
        foot visible                   foot HIDDEN                          foot HIDDEN
```

- **Segmented control** sits where the title was. Two segments, leading monochrome
  glyph each (`▤` list / `✦` sparkle), active = `--teal-tint` fill + `--ink` label,
  inactive = transparent + `--ink-3`. One pill, sliding-active look; 44px tall hit area.
- **Collapse chevron** unchanged at far left (collapses the whole rail to 48px).
- **Expand-width button** (`⤢`/`⤡`) appears in the head's right only in AI mode —
  toggles `aiWide`. aria-label flips "Expand panel" / "Collapse panel width".
- **Collapsed icon-rail (48px):** the segmented control reduces to a single `✦`
  button = "Open Ask Eamos" → expands the rail *and* switches to AI mode (one click
  out of the icon rail, straight into the assistant).

## 5. AI-mode body

Rendered in place of the section list when `mode==='ai'` (the section list stays
mounted, just `display:none`, so Library state is preserved):

1. **AI header strip** — `✦ Ask Eamos` label + the context chip (`RPE65:c.260A>G`,
   mono). Thin `--line` divider under it.
2. **AI evidence summary** — the relocated `EvidenceSummary`, in a **rail-fit
   variant** (`variant="rail"`): drop the nested card border/radius (the rail *is*
   the surface), trim padding `22/26 → 0`, keep the teal "Synthesised from sources"
   note + the summary paragraphs + warning chips. (Its now-removed duplicate inner
   title — de-duped this session — is exactly the header the rail strip replaces.)
3. **Ask Eamos chat** — the relocated `AskEamos`, coming-soon state: disabled
   textarea with the guiding placeholder ("Variant-aware chat is coming. We're
   wiring it to this report next."), the `Coming soon` pill, the cite/disclaimer
   footnote. Suggestion chips stay hidden while disabled (already the case).

Both already exist; the work is a **rail-fit style variant**, not new copy.

## 6. Account foot → icon, hidden in AI

- **Library mode:** the foot keeps the `AuthMenu` rail-foot row but **icon-led** —
  avatar/door glyph is the anchor, the email/label is secondary and truncates
  (Claude-desktop grammar). The **parked "Ask Eamos · Soon" launcher row is removed**
  from the foot: its job is now the rail toggle, so keeping it would be a second,
  redundant Ask entry point. (`RailFoot` becomes just the account control.)
- **AI mode:** the entire `.work-rail-foot` is **hidden** (`display:none` via an
  `.is-ai` shell class) — the rail is dedicated to the assistant, per Steven.
- Account popover still portals upward to `<body>` (unchanged), so it escapes the
  rail overflow.

## 7. Report changes

- **Remove §8** — delete the `<Card number={8} …><AIStack/></Card>` block from
  `ReportClient` (and its `#ai_summary` anchor + the ReportSectionNav entry). The
  numbered chain becomes 1–7. `VariantDecoder` (the optional non-numbered block)
  stays where it is.
- **Pass the AI surface up** — `WorkRail` gains `aiPanel?: ReactNode`. ReportClient
  passes `<AIStack payload contextLabel/>` (or EvidenceSummary+AskEamos directly) as
  `aiPanel`; WorkRail renders it in AI mode. No `aiPanel` → no AI toggle (workbench/
  compare unchanged).

## 8. Component / prop deltas

| File | Change |
| --- | --- |
| `layout/WorkRail.tsx` | New props `aiPanel?: ReactNode`, `aiTitle?: string` (default "Ask Eamos"). New state `mode`, `aiWide`. Segmented toggle in head (only when `aiPanel`). Expand-width button in AI. `.is-ai` / `.is-ai-wide` shell classes; `--rail-live-w` resolves to AI-wide. Body shows `aiPanel` vs `children`. Foot hidden in AI mode. |
| `layout/work-rail.css` | `--rail-w-ai`; `.is-ai` / `.is-ai-wide` width rules; segmented-toggle styles; AI-body wrapper + header strip; foot-hide; expand-button; extend the `prefers-reduced-motion` block. |
| `layout/RailFoot.tsx` | Drop the parked Ask launcher row; keep `<AuthMenu placement="rail-foot">`. |
| `auth/AuthMenu.tsx` | rail-foot variant → icon-led (avatar/door anchor, label secondary). Light touch; behavior unchanged. |
| `aistack/EvidenceSummary.tsx` | Add `variant?: 'card' \| 'rail'` — rail drops the card chrome + trims padding. (Inner duplicate header already removed.) |
| `aistack/AIStack.tsx` | Thread `variant` to EvidenceSummary; same stack for the rail. |
| `report/ReportClient.tsx` | Remove §8 Card; pass `aiPanel`. |
| `report/ReportSectionNav.tsx` | Drop the AI-summary nav entry (no longer in the column). |

## 9. Out of scope / parked

- **The LLM backend itself** — the AI gateway (`ai_engine.py` broker, SSE route,
  pgvector RAG, feature-6 chatbot) is its own build, starting soon. This pass builds
  the **rail shell + relocation** so the chat slots in with no shell change. Keep
  `AskEamos`'s streaming scaffold intact; the backend agent may later swap it to AI
  SDK `useChat` (kickoff Phase 6) behind the same rail.
- AI toggle on /workbench + /compare (shared capability, not wired this pass).
- URL/persisted AI mode (ephemeral, default Library this pass).
- Any change to the deterministic summary's content/sources.

## 10. Craft synthesis — impeccable + ui-ux-pro-max + frontend-design

The three-skill pass (Steven's standing rule, [[feedback_uiux_audit_three_skills]]).
These are the decisions that make it feel premium and on-brand, not generic:

**Segmented toggle — active state with three cues, no color-only, no side-stripe.**
A pill *track* (`--bg-soft`, 0.5px `--line`) holding a sliding *thumb* (a single
`--bg` surface with `--elev-1` + 0.5px `--line`). The thumb slides via `transform:
translateX` (impeccable: never animate layout props), so the motion is GPU-cheap and
jank-free. Active label inks to `--ink` + weight 600; inactive `--ink-3`. The one
place brand teal enters: the `✦` sparkle on the *active* "Ask Eamos" segment tints
`--teal` (a quiet signal that this is the assistant); the `▤` list glyph stays
monochrome. Net: elevation + ink + a brand cue all signal the active mode.

**Mode switch = one orchestrated reveal (not scattered micro-interactions).** On
Library→AI the section list cross-fades out (opacity, ≤140ms) and the AI panel rises
in: header strip → summary → chat stagger by ~40ms each on a 6px `translateY` with
`--ease-emphasized` (ease-out). frontend-design's "high-impact moment" done once,
cleanly. Reduced-motion: instant swap, no transform.

**Width expand = the reading payoff.** Rail `flex-basis/width` transition is the
established rail pattern (kept for consistency); the output reflows to the other
half and `--rail-live-w` updates so the ribbon recenters. At 760px the summary prose
relaxes from ~45ch to ~70ch (within the 65–75ch cap) — expanding is *for reading the
synthesis*, which is the honest reason to widen.

**AI summary = editorial prose, no nested card.** impeccable: nested cards are always
wrong, and §8 today is a card-in-card. The rail variant DROPS all card chrome — the
rail *is* the surface. Set as: a small-caps `--ink-3` "AI EVIDENCE SUMMARY" kicker, a
slim inline `--teal-deep` "Synthesised from sources" line (with the spark glyph, not
a filled box), then the summary in Inter 13.5/1.6 `--ink-2`, warning chips below.
Varied vertical rhythm (kicker tight, prose generous), not uniform padding.

**Coming-soon chat = guiding, not dead.** The disabled input keeps its guiding
placeholder + `Coming soon` pill, AND the example-question chips render as *muted,
disabled previews* so the user sees what they'll be able to ask ("What is the clinical
significance?") — an onboarding preview of value, not a greyed dead field. No chat
bubbles, no avatars, no purple — the real, deterministic summary above is the
substance; the chat is a clearly-labelled next step.

**Anti-slop guardrails honoured.** No centered message bubbles, no violet/indigo
gradient, no glassmorphism, no hero-metric block, no side-stripe accents, no em
dashes in UI copy. The surface is the warm reading-room: hairlines, the `--ink` ramp,
one teal sparkle accent. The "Ask Eamos" rail title may use Spectral to tie it to the
report's section-header voice.

## 11. Verification

- Browser visual review (proactive, screenshots) at **1440**, **~1280**, and
  **drawer (<1200)**: toggle affordance + active state; mode cross-fade; expand to
  ~half + output reflow + ribbon stays centered; foot hides in AI; coming-soon chat
  reads as guiding; collapsed-rail `✦` → AI.
- `prefers-reduced-motion` on → no rail motion.
- app/web `tsc` 0-err, `eslint` 0-err (≤3 pre-existing warns); zero console errors.
