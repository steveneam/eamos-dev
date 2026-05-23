# On-Hold And Pause Register

This folder keeps dated, prioritized pause state that both Claude and Codex can
read without repeating long hold lists in every resume prompt.

Use `register.md` as the current sorted list. Keep permanent decisions in
`agent_handoff/DECISIONS.md`, risks in `agent_handoff/RISKS.md`, and detailed
implementation plans in `plans/*`; this folder is only the quick pickup map for
parked or gated work.

Entry shape:

- Priority bucket
- Item name and route/scope
- Added timestamp and last touched timestamp
- Owner or next reviewer
- Resume condition
- Source of truth

Priority buckets:

1. Cross-check attention: items one agent should notice while reviewing the
   other agent's work.
2. Active lane pauses: currently relevant work paused for approval, mirror, or
   sequencing.
3. Workbench and later build queue: planned but gated product/tool work.
4. Parked holds: explicitly on hold until the user reopens them.
