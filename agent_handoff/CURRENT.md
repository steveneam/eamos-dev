# Current Agent State

> ## ▶ BOOT: Steven types **`gogogo`** — that IS the whole resume prompt.
>
> **Agent, on `gogogo` (or any greeting with no task): do this, unprompted.**
> He cannot copy text out of the terminal, and he may be sending it from a
> Telegram topic on his phone. Read, in order, then act:
> 1. this whole file (Resume Prompt → Pointer → Delta → Next Action)
> 2. `CLAUDE.md` + `agent_handoff/README.md` (protocol) and your memory
> 3. `git log --oneline -8` and `git status` — trust the repo, not the stamp
>
> Then state the Next Action in one sentence, say what you are starting, and
> start it. Do not ask “shall I?” — the Next Action is the standing approval.
> Stop only at a founder gate (spend, irreversible action, or anything the
> protocol names a founder decision).
>
> _Boot block added 2026-07-13 at the founder's direction. Keep it at the top
> when overwriting this file._

> **Live state only — overwrite the whole file each wrap.** History belongs in
> Git, `PROGRESS.md`, and the agents' rolling logs. Protocol →
> `agent_handoff/README.md`; risks → `docs/operations/risks-and-guardrails.md`;
> worktree truth → `git status --short --branch`.

## Active Status

- **Claude:** STOPPED @ 2026-07-15 10:55 UTC — no active lane.
- **Codex:** STOPPED @ 2026-07-15 16:06 UTC — repository cleanup slice merged
  through PR #13 after Steven's explicit approval and all local/remote gates.

## Log Edit-Lock

RELEASED: 2026-07-15 16:06 +0000 · Codex (repo cleanup merged and clear-safe)

## Shared File Locks

- None.

## Resume Prompt

```text
# Resume prompt · 2026-07-15 16:06 +0000 · post-cleanup continuation
Read CURRENT.md, agent_handoff/README.md, then docs/repo-structure/audit-2026-07-15.md.
PR #13 consolidated the product on app/web, retired app/frontend, moved 13 useful tests,
removed seven dead active-web components, split the Workbench CSS and population age chart,
and split the variant-report orchestrator plus data-source registry behind stable facades.
The root npm gate now covers guard/lint/typecheck/test/build; dependency audit is separate.
Local npm run verify and audit passed; CI run 29430745226 and Vercel preview were green.
Start the next local-only responsibility fold from ReportGeneViewer.tsx behind its current API.
Use the impeccable skill, preserve behavior and visual output, add line-budget ratchets, and verify.
Do not mutate Supabase, Render, VPS, provider state, migrations, or deploy hooks without their gates.
Safe to clear: yes — PR #13 is merged, shared locks are released, and the next slice is local-only.
```

## Pointer

- Merged target: PR #13 (`codex/repo-cleanup-optimization`).
- Cleanup commits: `b90e33d` and protected-check alignment `929b002`.
- Final pre-merge CI: run `29430745226`; all jobs and Vercel preview green.
- Personal security skill: `~/.codex/skills/evidence-security/` (validated,
  secret-safe scanner included; intentionally not repository-tracked).

## Delta

- The duplicate Vite application is gone. `app/web` is the sole frontend and
  owns all 13 retained pure tests (135 passing Vitest assertions).
- Seven no-importer active-web components and 380 lines of their orphaned CSS
  were removed. Workbench CSS is now five responsibility-owned sheets with the
  original rule order preserved.
- `PopulationFrequencySection.tsx` now delegates its age visualization/export;
  variant-report helpers/signals and registry models/records are focused modules
  behind their original public imports.
- The verified diff changed 188 files: 7,911 insertions and 42,084 deletions.
- Backend constraints no longer install unused LangChain/community or async-test
  packages. Local and CI `pip-audit` report no known backend vulnerabilities.
- The frontend high/critical advisory gate passes. Three moderate advisories
  remain in Next's nested PostCSS; npm only offers an unsafe Next 9 downgrade.
- The evidence-security scanner inspected 896 tracked text files. Its six high
  leads were triaged as loopback developer tooling, verified JWT decoding, or
  tests that prohibit public service-role variables; none was a confirmed flaw.
- No Supabase/database, provider, Render/VPS, deployment, or other cloud mutation
  occurred. No frontend redesign or generated image was needed for this slice.

## Next Action

- Start a fresh branch from current `main` and split
  `app/web/components/report/ReportGeneViewer.tsx` by controller/adapter/rendering
  responsibility behind the unchanged exported component contract.
- Preserve visual output, use focused tests plus the full root verification gate,
  and lower the structure budget only after the responsibility split lands.
- Keep all cloud/provider/schema/deploy actions founder-gated.
