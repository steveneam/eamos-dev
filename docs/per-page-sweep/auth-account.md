# Per-page sweep — Auth + Account

UI/UX scout pass over the identity surfaces. Assessment only — no source
edits. Quality bar: Linear / Vercel / Stripe / Supabase, against the Eamos
"Reading Room" brand register (DESIGN.md "Brand surfaces" cheat-sheet).

Reviewed: 2026-06-08 · model: claude-opus-4-8
Skills consulted: `frontend-design` (precision/refinement lens), `ui-ux-pro-max`
(`--domain ux` / `style`).

---

## 1. Surface map

| File | Role |
| ---- | ---- |
| `app/web/app/auth/page.tsx` | Route shell — metadata only, renders `<AuthPageClient />`. |
| `app/web/components/auth/AuthPageClient.tsx` | Full-page `/auth` — split layout: editorial left panel (desktop) + form right panel; redirects signed-in users to `/account`; owns the loading skeleton. |
| `app/web/components/auth/AuthPanel.tsx` | The actual auth form (sign up / sign in / reset / success). OAuth row (Google / Microsoft / LinkedIn), email/password fields, ToS checkbox, all scoped styles + brand SVG icons. Shared by `/auth`, `/account` signed-out gate, and the `AuthMenu` popover. |
| `app/web/components/auth/AuthMenu.tsx` | Top-right nav control. Signed out: Sign in / Register → anchored popover hosting `<AuthPanel>`. Signed in: avatar button → account dropdown. |
| `app/web/components/auth/AuthProvider.tsx` | Auth context (Supabase); not a visual surface. |
| `app/web/app/account/page.tsx` | Route shell — metadata only, renders `<AccountClient />`. |
| `app/web/components/account/AccountClient.tsx` | Account dashboard ("Messenger"): plan-status header, Saved variants form+list, Evidence submissions form+list, empty/skeleton/notice states, all scoped styles. |
| `app/web/app/account/update-password/page.tsx` | Password-recovery landing — new-password + confirm form, link-expired / signed-out / done states. |
| `app/web/components/pricing/PageHeader.tsx` | Shared brand nav used by `/account` (logo left, centered links, `AuthMenu` right). |

**Three distinct field/button CSS systems** exist for the same visual idiom:
`.ap-*` (AuthPanel), `.ac-*` (AccountClient), `.upw-*` (update-password). They
are near-identical but drift in field background, font-size, and disabled
opacity — the root cause of most findings below.

---

## 2. Findings

Severity: **P0** = broken / accessibility-blocking / trust-damaging ·
**P1** = clear inconsistency or craft gap a senior reviewer flags ·
**P2** = polish / nicety.

### P0

1. **`AuthPanel.tsx:497-559` (the `Field` component) · no password visibility toggle on any password input.**
   Sign-up asks for password **twice** ("Create password" + "Confirm password")
   with no way to reveal either, and sign-in / update-password are also masked-only.
   ui-ux-pro-max Forms › *Password Visibility* ("Let users see password while
   typing… Toggle to show/hide", severity Medium) — but at the point where a
   user must type a password blind twice and a mismatch only surfaces on blur,
   the friction compounds to a real completion blocker. Affects `AuthPanel`
   (2 fields) and `update-password/page.tsx:186-231` (2 fields).
   **Severity: P0.**

2. **`AuthPanel.tsx:619-645` (`.ap-primary-btn`) · disabled primary button has no visual disabled affordance.**
   The disabled rule only sets `cursor: not-allowed`; opacity is driven inline
   by `style={{ opacity: busy ? 0.65 : 1 }}` (line 354) — so a button disabled
   for any *non-busy* reason renders at full teal and looks fully pressable.
   The success-state CTA (line 487) and the SuccessState reuse the same class.
   DESIGN.md mandate: "Disabled buttons always go to `opacity: .45-.55` and
   `cursor: not-allowed`." `.ac-add-btn` (`AccountClient.tsx:81`) and
   `.upw-submit` (`update-password:93`) get this right (`opacity .55`/`.65` in
   CSS); `.ap-primary-btn` is the outlier. **Severity: P0** (token-mandate
   violation + affordance lie per DESIGN.md principle 3 / ui-ux-pro-max
   *Disabled state*).

3. **`AuthPanel.tsx:341-360` · "Sign up" / "Sign in" submit button label does not match the validation it triggers, and `noValidate` (line 214) disables native validation while inline validation only runs `onBlur`.**
   Concretely: on sign-up, password-match and length errors are thrown from
   `onSubmit` (lines 98-99) as a single top-level `error` banner, while the
   per-field `onBlur` validators (lines 241-262) set *field* errors — so the
   same failure can surface in two different places with two different
   wordings ("Use at least 8 characters." top-level vs "Use at least 8
   characters." field-level — same text, different location/role). With
   `noValidate` on, a user who never blurs a field gets only the top banner.
   ui-ux-pro-max Forms › *Inline Validation* (validate on blur, severity
   Medium) + Feedback › *Error Recovery*. The duplicate-channel behaviour is
   the trust problem. **Severity: P0** (conflicting error presentation on the
   primary conversion path).

### P1

4. **OAuth buttons are icon-only with no text label — `AuthPanel.tsx:167-184`.**
   Three 42px-tall squares showing only a brand glyph. `aria-label`/`title`
   carry "Continue with Google" etc., so SR + hover are covered, but sighted
   users get no visible affordance text, and three same-shape squares read as a
   toolbar, not three distinct sign-in paths. Vercel/Supabase/Linear all label
   at least the primary provider. ui-ux-pro-max Forms › *Input Labels* spirit
   ("don't rely on a glyph alone"). On the full-page `/auth` (380px column)
   there is ample room for "Continue with Google" stacked full-width.
   **Severity: P1** (flag the stacked-label variant for `/auth` under §4 — it
   is a layout change).

5. **`AuthPanel.tsx:148-156` · the panel's Close (✕) button is wrong-to-confusing on the full-page `/auth` and `/account` gate.**
   In the `AuthMenu` popover the ✕ means "dismiss popover" — correct. But the
   same `AuthPanel` is embedded full-page in `AuthPageClient` (`onClose` →
   `router.push('/account')`) and in `AccountClient`'s `SignedOut` gate
   (`onClose` → `router.push('/')`). On a full-page form a top-right ✕ reads as
   "close this page" but actually *navigates*, and on `/auth` it pushes to
   `/account` which (signed-out) bounces straight back — a confusing no-op
   loop. The "Cancel" button (line 342) duplicates the same `onClose`.
   **Severity: P1** (the ✕ should be suppressed when the panel is full-page;
   see spec).

6. **Field background inconsistency across the three form systems.**
   - `.ap-field` (AuthPanel): `background` set *inline* per-call to `var(--bg)`
     light / `var(--hero-glass)` dark (`AuthPanel.tsx:548`); the class itself
     sets no background.
   - `.ac-field` (AccountClient `:31`): `background: var(--bg-soft)`.
   - `.upw-field` (update-password `:47`): `background: var(--bg-soft)`.
   So the AuthPanel inputs are near-white (`--bg`) while the Account and
   update-password inputs are one step grey (`--bg-soft`) — the same input,
   three surfaces, two fills. DESIGN.md brand-surface Input row implies one
   input idiom. **Severity: P1.**

7. **Field font-size drift.** `.ap-field` and `.upw-field` are `13.5px`;
   `.ac-field` is `13px` (`AccountClient.tsx:34`). Same control, three
   declarations, two sizes. **Severity: P1.**

8. **`AccountClient.tsx:449-469` (Saved variants) and `:622-643` (Evidence) · inputs have `aria-label` but no *visible* `<label>`; placeholder is the only visible field name.**
   ui-ux-pro-max Forms › *Input Labels*, severity **High**: "Every input needs
   a visible label… Don't: Placeholder as only label." Once the user types, the
   field name vanishes. The Evidence detail grid (`:676-732`) repeats this for
   ~8 fields. (The `<select>`s at `:690-710` use the first `<option>` as a
   pseudo-label, same anti-pattern.) **Severity: P1** (high-frequency,
   audit-grade data entry — the field names matter).

9. **Required-field marking is invisible — `AccountClient.tsx:629,639`.**
   The Evidence form marks HGVS + PMID `required` and enforces them in
   `submit` (`:592`), but nothing tells the user they are required until the
   submit error fires ("Variant HGVS and a supporting PMID are required.").
   Saved-variants HGVS is also effectively required (`:419` early-returns) with
   no marker. ui-ux-pro-max Forms › *Required Indicators* (severity Medium).
   **Severity: P1.**

10. **`.ac-remove-btn` tap target below 44px — `AccountClient.tsx:83-104`.**
    Padding `4px 6px` on a 12px font yields a ~20px-tall hit target; it sits at
    the right edge of each saved-variant row on mobile. ui-ux-pro-max Touch ›
    *Touch Target Size* (min 44×44, severity **High**). The OAuth buttons
    (42px) and the `.ap-icon-btn` close (28px, `AuthPanel.tsx:718-720`) are
    also under 44px but are desktop-popover-centric; the Remove button is the
    worst because it is a destructive action in the main mobile flow.
    **Severity: P1** (Remove); P2 (the two icon buttons).

11. **`AuthPanel.tsx:312-328` · "Forgot password?" link has weak hierarchy / contrast and sits before the error region.**
    It renders as `--ink-3` (light) 12px right-aligned with only an opacity
    hover (`.ap-link-btn` `:745`) — no teal accent, unlike every other
    brand-surface text affordance which uses the teal-underline signal
    (DESIGN.md "Text link" / "Toggle pill" rows). It reads as disabled-grey
    rather than actionable. **Severity: P1** (affordance clarity, DESIGN.md
    principle 3).

12. **`update-password/page.tsx` reimplements the panel from scratch (`.upw-*`) instead of composing shared primitives — and drifts.**
    It hard-codes its own field/submit styles that duplicate `.ap-*` with
    subtle differences (disabled opacity `.65` vs none; field bg `--bg-soft`
    vs inline `--bg`). It also has **no password visibility toggle** (see #1)
    and **no minimum-length hint shown up front** — the 8-char rule only
    appears as an error after a short password is submitted (`:29`).
    **Severity: P1** (consistency + the same blind-double-entry as #1).

13. **`AuthPanel.tsx:344-359` · Cancel + Submit button row: the secondary "Cancel" carries equal vertical weight and competes with the primary on the full-page form where there is nothing to cancel to.**
    On the popover this pairing is fine; full-page it is redundant with the ✕
    (#5) and dilutes the single-focal-point rule (DESIGN.md principle 2: "One —
    and only one — focal point per region"). **Severity: P1** (couples to #5).

### P2

14. **`AuthPanel.tsx:185-210` · the "or with email" divider uppercase label is exactly the editorial-template tracked-uppercase fingerprint DESIGN.md warns against** — though here it is a single functional divider, not section grammar, so it is borderline-acceptable. Consider sentence-case "or continue with email". **P2.**

15. **`AuthPanel.tsx:758-774` (`MiniSpinner`) injects a `<style>` with `@keyframes ap-spin` inside the SVG, rendered once per spinning OAuth button.** Works, but the keyframe should live in `AuthPanelStyles`, and the spin animation is not gated by `prefers-reduced-motion` (DESIGN.md mandates the global guard; verify the guard in `globals.css` covers it — `animation-iteration-count:1` would stop it, so likely fine, but the inline injection is sloppy). **P2.**

16. **`AuthPageClient.tsx:182` · the form column is `maxWidth: 380` centered inside a 480px right rail, but the right rail itself is `var(--bg-soft)` while the card is `var(--bg)` with `--elev-2`.** A floating near-white card on a one-step-darker rail on a desktop split where the *left* panel is also `--bg` creates a three-surface sandwich (bg / bg-soft / bg) that reads slightly muddy. Minor; the card elevation does the separating work. **P2.**

17. **`AccountClient.tsx:530` · evidence-code pills include `'Other'` in a mono pill row** — mono is for codes/scores (DESIGN.md typography), and "Other" is a word, not a code, so it sits oddly in `var(--mono)`. **P2.**

18. **`update-password/page.tsx:178` uses Tailwind utility classes (`flex flex-col gap-3`) mixed with inline styles**, while the rest of the file is pure inline — harmless but inconsistent with its own idiom. Same mixing in `AuthPanel` (`className="flex flex-col gap-2.5"`). This is the established app pattern, so **don't-touch** (see §5), noted only for completeness. **P2.**

19. **No `autoFocus` on the first field of any form.** On the full-page `/auth` and `/account/update-password`, focusing the email/password field on mount is the expected behavior for a dedicated auth page (Stripe/Linear do this). The popover correctly should NOT autofocus (it would scroll/steal focus on nav). **P2** (full-page routes only).

---

## 3. Implementation spec (P0 + P1)

All values use existing tokens. Changes are surgical; each traces to a finding.

### Spec A — Password visibility toggle (Finding #1, #12) · P0

Add a reveal toggle to every password field. Cleanest path: extend the shared
`Field` component in `AuthPanel.tsx` and reuse it in `update-password`.

In `AuthPanel.tsx` `Field` (line 497), when `type === 'password'`, render the
input with a trailing button inside a relative wrapper:

- Wrapper: `position: relative`.
- Input: add `paddingRight: 40` (so text clears the button).
- Toggle button (new): absolutely positioned right, `28px` square min,
  `top: 50%; transform: translateY(-50%)`, `right: 6px`, transparent bg, no
  border, `color: var(--ink-4)`, `cursor: pointer`, eye / eye-off SVG
  (stroke `currentColor`, 16px — matches existing icon weight). On click,
  toggle local `show` state → swap input `type` between `password`/`text`.
- `aria-label`: `Show password` / `Hide password`; `aria-pressed={show}`.
- `:focus-visible` → `box-shadow: 0 0 0 3px rgba(29,158,117,0.12)` (the panel's
  existing focus token), `border-radius: 6px`.
- `tabIndex={-1}` is acceptable so it does not interrupt the email→password→
  submit tab order (it is mouse/AT-reachable via the label).

Apply the same `Field` (or a shared toggle) to `update-password/page.tsx`'s two
inputs (lines 186, 210) — ideally by importing the shared `Field`, which also
resolves Finding #12's duplication.

### Spec B — Disabled primary button affordance (Finding #2) · P0

`AuthPanel.tsx` `.ap-primary-btn:disabled` (line 643), change:

```css
/* before */
.ap-primary-btn:disabled { cursor: not-allowed; }
/* after */
.ap-primary-btn:disabled { opacity: 0.55; cursor: not-allowed; }
```

Then remove the now-redundant inline opacity at line 354
(`style={{ flex: 1, opacity: busy ? 0.65 : 1 }}` → `style={{ flex: 1 }}`), so a
single source of truth governs the disabled look. (`.55` matches DESIGN.md's
`.45-.55` band and `.ac-add-btn`.)

### Spec C — Single error channel on sign-up (Finding #3) · P0

Make the per-field `onBlur` validators the single source for field-level rules
and stop re-throwing the same rules as top-level banners:

- In `onSubmit` (lines 97-100), keep `!agreed` as a top-level banner (it has no
  field), but route password-length + mismatch into `setFieldError` instead of
  `setError`:
  - `if (password.length < 8) { setFieldError('password', 'Use at least 8 characters.'); return }`
  - `if (password !== confirm) { setFieldError('confirm', 'Passwords do not match.'); return }`
- Keep `humaniseError`-based server errors on the top banner (correct — they
  are not field-scoped).
- Result: length/mismatch always surface under their field (one wording, one
  location), server/agreement errors surface in the banner. No behavior change
  to `noValidate` needed.

### Spec D — Suppress ✕ + redundant Cancel when full-page (Findings #5, #13) · P1

Add a `chromeless?: boolean` prop to `AuthPanel` (default `false`):

- When `chromeless`, do not render the header ✕ button (lines 148-156) — keep
  the `<h3>` title.
- When `chromeless`, do not render the "Cancel" button (lines 342-350); let the
  primary submit be the sole full-width focal action (`flex: 1` already).
- Pass `chromeless` from `AuthPageClient.tsx:191` and from `AccountClient.tsx`'s
  `SignedOut` (line 272). The popover (`AuthMenu.tsx:136`) keeps the default
  (chrome on) — there the ✕/Cancel are correct.
- The "Back to Eamos" link already exists below the card on `/auth`
  (`AuthPageClient.tsx:201`), so the escape hatch is preserved.

### Spec E — Unify the three field/button systems (Findings #6, #7) · P1

Pick `.ap-field` as canonical and align the other two:

- `.ac-field` (`AccountClient.tsx:34`): `font-size: 13px` → `13.5px`.
- `.ac-field` (`:33`) + `.upw-field` (`update-password:47`): keep
  `background: var(--bg-soft)` **or** move `.ap-field` to `--bg-soft` — choose
  one fill for "input on brand surface". Recommendation: **standardize on
  `var(--bg-soft)`** (the Account/update-password choice) because the field
  then reads as inset against the `var(--bg)` card, which is the stronger
  affordance. That means: in `AuthPanel.tsx:548`, drop the inline
  `background: dark ? 'var(--hero-glass)' : 'var(--bg)'` light value and set
  `.ap-field { background: var(--bg-soft); }` in the class, keeping the dark
  override inline. (Token-only; no new values.)

### Spec F — Teal-accent the "Forgot password?" link (Finding #11) · P1

`AuthPanel.tsx:312-328`, give the link the canonical brand text-link signal
instead of bare opacity. Reuse the `.ap-tos-link` pattern (already defined,
lines 590-606): apply `className="ap-tos-link"` style of teal-underline hover,
or add to `.ap-link-btn`:

```css
.ap-link-btn { color: var(--ink-3); }  /* keep */
/* add a teal hover for the forgot-password affordance specifically: */
.ap-forgot-btn:hover { color: var(--teal); }
```

Minimal version: change the inline `color` (line 323) from `--ink-3` to
`--teal` so it matches the other actionable text affordances and the disabled-
grey read disappears. Keep size 12px.

### Spec G — Visible labels + required markers on Account forms (Findings #8, #9) · P1

For the Saved-variants and Evidence forms (`AccountClient.tsx:449-469`,
`:622-732`), promote each `aria-label` to a visible `<label>` using the
existing `labelStyle` idiom from `update-password` (`fontSize: 11.5,
fontWeight: 600, color: var(--ink-2)`):

- Wrap each input in `<label className="flex flex-col gap-1.5">` with a
  `<span>` label above (matches the `update-password` and `AuthPanel.Field`
  pattern already in the codebase — reuse, don't invent).
- Append a required marker to HGVS and PMID labels: a `var(--err)` `*` or
  `(required)` in `--ink-4`. Use one convention site-wide; `*` is most compact.
- Selects (`:690-710`): keep the first option as hint but add the visible
  label above too.

This is the largest P1 by surface area; it can be staged (Saved variants +
top-level Evidence first, the collapsed ClinVar detail grid second).

### Spec H — Remove-button tap target (Finding #10) · P1

`AccountClient.tsx:83-104` `.ac-remove-btn`, raise the hit area without
changing visual size much:

```css
/* before */
.ac-remove-btn { ... padding: 4px 6px; ... }
/* after — meets 44px min height via padding, keeps 12px text */
.ac-remove-btn { ... padding: 10px 10px; min-height: 44px; ... }
```

Or, if 44px rows feel heavy, set `min-height: 36px` + `min-width: 44px` and
accept the documented compromise (note it under §5 if Steven prefers the
tighter row). The OAuth (42px) and `.ap-icon-btn` (28px) targets are P2 — only
raise if Steven wants strict 44px everywhere (flag, don't auto-apply, since the
popover ✕ at 44px would unbalance the 28px header).

---

## 4. Flagged — needs Steven approval (durable structural / major-visual)

- **OAuth buttons → labelled, stacked, full-width on `/auth` (Finding #4).**
  This changes the OAuth row from a 3-icon strip to three full-width
  "Continue with Google / Microsoft / LinkedIn" buttons (or one primary +
  two icon-secondary). It is a layout/visual change on the conversion path,
  not a token tweak — get explicit sign-off and decide the variant
  (full stack vs. primary-labelled + secondary-icons). The popover keeps the
  compact icon row regardless (width-constrained).
- **`/auth` chromeless mode (Spec D)** removes the in-form ✕ and Cancel on the
  full-page routes. It is the right call but it is a visible behavior change to
  a shipped auth surface — confirm before applying.
- **Password strength meter / live "8+ characters" affordance.** Beyond the
  toggle, a live requirement hint (greys → teal as satisfied) on sign-up and
  update-password would lift trust to the Stripe bar. New component — propose,
  don't build unprompted.
- **`/account/update-password` consuming the shared `Field` / `AuthPanel`
  primitives (Spec A + Finding #12).** Recommended, but it re-points a
  standalone route at shared components — a refactor with blast radius;
  confirm before collapsing the `.upw-*` system.

---

## 5. Don't-touch (intentional-but-odd)

- **Mixed Tailwind utility classes + inline styles** (e.g.
  `className="flex flex-col gap-2.5"` alongside `style={{…}}`). This is the
  established `app/web` idiom (utility for layout, inline/`<style>` for
  tokens) — Finding #18 is informational only; matching the idiom is correct.
- **Per-component `<style>` blocks with scoped class prefixes** (`.ap-*`,
  `.ac-*`, `.am-*`). DESIGN.md / the app pattern favors this over a global
  stylesheet; the fix is to *align values*, not to centralize.
- **The editorial left panel's specimen card** (`AuthPageClient.tsx:108-150`)
  using `--cls-lpath-*` classification tokens for the "Likely Pathogenic"
  badge — correct token reuse, reads as a real product artifact (good trust
  signal), keep.
- **"Demo mode" notice when `!configured`** (`AuthPanel.tsx:159-163`) — honest
  dev-state messaging, intentional.
- **`AuthMenu` popover ✕ + Cancel** — correct in the popover context; only the
  full-page embeds are wrong (Spec D scopes the fix to those).
- **Mono `--mono` on the specimen HGVS / email / tracking IDs** — correct per
  DESIGN.md (HGVS/coords/scores/identifiers only).
- **Skeleton loaders** (`AuthSkeleton`, `AccountSkeleton`, `RowSkeleton`) —
  honest pending states per DESIGN.md principle 4; opacity-stepped, no
  fabricated progress. Keep.

---

## Summary (top findings)

1. **Password fields are blind across all four forms** — no reveal toggle, and
   sign-up makes users type a password twice with mismatch surfacing only on
   blur. Highest-friction P0; add a shared eye-toggle to the `Field` primitive.
2. **`.ap-primary-btn` disabled state lies** — it stays full-teal/pressable
   when disabled for non-busy reasons, violating DESIGN.md's `.45-.55` opacity
   mandate. One-line CSS fix.
3. **Sign-up errors fire on two channels** (top banner *and* per-field) with
   duplicated wording — route length/mismatch to the field, keep server errors
   on the banner.
4. **Three near-identical field/button CSS systems** (`.ap-*` / `.ac-*` /
   `.upw-*`) have drifted in field background and font-size — unify on one
   idiom (Spec E).
5. **Account forms label fields only via placeholder** (High-severity
   anti-pattern) and never mark required fields — promote `aria-label`→visible
   `<label>` using the pattern already present in `update-password`/`Field`.

Most fixes are token/value-level and surgical; the only structural items
(labelled OAuth row, chromeless full-page panel, update-password refactor) are
isolated under §4 for approval.

File written: `D:\eamos\docs\per-page-sweep\auth-account.md`
