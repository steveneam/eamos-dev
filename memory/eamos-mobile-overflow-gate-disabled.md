---
type: memory
topic: frontend-verification
date: 2026-06-25
---

# Eamos Mobile Overflow Gate Disabled

Steven disabled mobile/sub-desktop overflow and layout-stability gates
indefinitely until he explicitly says to activate them again.

Operational rule:

- Do not spend task time fixing mobile overflow unless Steven explicitly
  reactivates mobile layout work.
- Do not run sub-desktop widths as pass/fail report preflight evidence.
- Keep report section slot and hydration preflight proof desktop-only.
- If a command receives sub-desktop widths, tooling should skip them or report
  them as ignored, not fail on mobile overflow.
