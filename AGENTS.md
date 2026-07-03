## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

When the user types `/graphify`, invoke the `skill` tool with `skill: "graphify"` before doing anything else.

Rules:
- For codebase questions, first run `python -m graphify query "<question>"` when graphify-out/graph.json exists. Use `python -m graphify path "<A>" "<B>"` for relationships and `python -m graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- Dirty graphify-out/ files are expected after hooks or incremental updates; dirty graph files are not a reason to skip graphify. Only skip graphify if the task is about stale or incorrect graph output, or the user explicitly says not to use it.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `python -m graphify update .` to keep the graph current (AST-only, no API cost).
- `python -m graphify update .` routinely exceeds short/default command ceilings on
  this repo. Run it with a long timeout (at least 360 seconds) the first time;
  do not burn a short timeout before rerunning.
- For routine codebase searches, scope `rg` to the current handoff/docs/source
  files and avoid `agent_handoff/archive/` unless historical context is required.

Maintenance practice:
- Follow the Selom-style maintenance model: use cheap AST updates routinely, and run semantic extraction only when Steven explicitly asks or at deliberate release/handoff checkpoints.
- Before any semantic pass, resolve and pin the graphify Python interpreter in `graphify-out/.graphify_python`, then run corpus detection and sanity-check the file/word counts. Keep multi-GB references, fixtures, generated payloads, screenshots, archives, `.tools/`, and vendored/tooling docs out via `.graphifyignore`.
- Do not treat the semantic pass as covered by `graphify update .`; update is AST-only and free, while semantic extraction is LLM-backed and should be occasional.
- Eamos is above graphify's default 5,000-node HTML visualization threshold. Default `graphify export html` may produce an aggregated community view; when Steven wants the Selom-style full raw HTML, use `graphify export html --graph graphify-out/graph.json --node-limit 20000`.
- Full raw HTML can be large/heavy; verify it in Chrome after export when changing visualization output.

## Parallel-agent workflow

Eamos is parallel-ready (Forj protocol). Live board + Eamos adaptation: `COORDINATION.md`.
Protocol (read-only vault): `Forj/bones/parallel-agents.md` + `Forj/Wiki/reference/parallel-agent-workflow.md`.

Two standing rules:

1. **Propose & launch lanes.** When upcoming work has ≥2 dependency-independent buckets that
   meet at one freezable contract, proactively propose a parallel-worktree sprint — name the
   lanes, owned globs (one file → one owner), the frozen contract, and merge order — and hand
   Steven exact copy-paste launch commands. He approves the partition and runs them; he never
   designs the setup. 3–5 lanes max; run coupled work sequentially.
2. **Agent-run merges, human-approved.** Agents execute the serialized merge gate themselves
   (rebase onto latest `main` → CI green → review → merge), pausing for Steven's explicit
   approval before each merge to `main`. Never merge on red; one lane at a time.

End every session clear-safe — update `agent_handoff/CURRENT.md` + hand Steven a stamped
resume prompt (protocol: `agent_handoff/README.md`).

## backend predictor wiring

When Steven says "admin" for predictor work, interpret it as: Steven/backend gets all predictors wired now. Do not add account-role/auth plumbing for this. Do not postpone backend predictor integration because of commercial, launch, or licensing labels. Preserve license/provenance/launch-gate metadata on rows and health/preflight output so commercialization filtering can be decided later.
