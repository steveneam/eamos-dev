# NEEDS STEVEN - the founder action queue

> Agent-maintained. One line per OPEN founder action:
> `- [YYYY-MM-DD] text` (date = when it was raised; the dashboard shows age).
> Remove a line only when its source says done; this file records state and
> does not invent or retire decisions.

- [2026-07-10] Decide M-013 branch protection/CI hardening: approve the plan's single stable aggregate `ci` required check, or explicitly leave M-013 deferred. The separately approved tooling retirement must not wait on this decision.
- [2026-07-15] Restore GitHub Actions billing or raise the spending limit. PR #9 run `29416286779` marked all three CI jobs failed without starting them because account payments/spending limits blocked runners; never merge the PR while those required checks are red.
