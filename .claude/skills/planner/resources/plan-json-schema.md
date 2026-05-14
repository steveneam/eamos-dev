# plan.json Schema Reference

`plan.json` is the authoritative intermediate representation (JSON-IR) that
the planner skill builds during the plan-design phase. The Technical Writer
later renders it to Markdown; until then, plan.json is the single source of
truth. Build it exclusively via the `skills.planner.cli.plan` CLI — never
hand-edit the JSON.

Authoritative dataclasses live in
`skills/planner/shared/schema.py`. This document is a flat reference so the
architect agent can plan field-by-field without reading Python.

---

## Top-level shape

```jsonc
{
  "plan_id":           "<uuid>",                // auto-set on init
  "created_at":        "<iso-8601>",            // auto-set on init
  "frozen_at":         null,                    // set when executor begins

  "overview":          { "problem": "...", "approach": "..." },
  "planning_context":  { ... },                 // see § planning_context
  "invisible_knowledge": { ... },               // see § invisible_knowledge
  "milestones":        [ ... ],                 // see § milestones
  "waves":             [ { "id": "W-001", "milestones": ["M-001","M-002"] } ],
  "diagram_graphs":    [ ... ],                 // see § diagrams
  "readme_entries":    []                       // deprecated, leave empty
}
```

**Required at validation time (phase=plan-design):**
- `overview.problem` — non-empty
- `milestones` — at least one
- every milestone has at least one `code_intent`

---

## § overview

```jsonc
{
  "problem":  "One-sentence statement of the underlying problem.",
  "approach": "High-level summary of how this plan solves it."
}
```

Avoid orchestration boilerplate (no "we will write a plan that…"). State the
substantive goal.

---

## § planning_context

```jsonc
{
  "decision_log":           [ Decision, ... ],
  "rejected_alternatives":  [ RejectedAlternative, ... ],
  "constraints":            [ "MUST: X", "SHOULD: Y" ],
  "known_risks":            [ Risk, ... ]
}
```

### Decision  (id format `DL-NNN`)

```jsonc
{
  "id":               "DL-001",
  "version":          1,
  "decision":         "What we chose.",
  "reasoning_chain":  "premise -> implication -> conclusion"
}
```

The `reasoning_chain` must be a multi-step chain, not a one-line dismissal.

| BAD  | `Polling \| Webhooks unreliable` |
| GOOD | `Polling \| 30% webhook failure -> need fallback anyway -> just use polling` |

### RejectedAlternative

```jsonc
{
  "id":               "RA-001",
  "alternative":      "What was considered.",
  "rejection_reason": "Why it was dismissed.",
  "decision_ref":     "DL-001"               // must exist in decision_log
}
```

### Risk

```jsonc
{
  "id":           "R-001",
  "risk":         "What could go wrong.",
  "mitigation":   "Concrete mitigation step.",
  "anchor":       "path/to/file.py:L42-L58",  // optional
  "decision_ref": "DL-001"                    // optional
}
```

---

## § invisible_knowledge

Knowledge for future sessions — design rationale, accepted tradeoffs,
invariants that aren't obvious from the code.

```jsonc
{
  "system":     "Short paragraph describing the system as it stands.",
  "invariants": [ "Invariant 1.", "Invariant 2." ],
  "tradeoffs":  [ "We accept X to gain Y." ]
}
```

---

## § milestones

Each milestone is an independently deployable increment.

```jsonc
{
  "id":             "M-001",
  "version":        1,
  "number":         1,
  "name":           "Auth stack",
  "files":          [ "src/auth.py", "tests/test_auth.py" ],
  "flags":          [],
  "requirements":   [ "Add JWT validation." ],
  "acceptance_criteria": [
    "POST /login with valid creds returns 200 and a JWT.",
    "POST /login with bad creds returns 401."
  ],
  "tests":          [ "test_login_success", "test_login_failure" ],
  "code_intents":   [ CodeIntent, ... ],
  "code_changes":   [ CodeChange, ... ],     // populated in plan-code phase
  "documentation":  Documentation,           // deprecated; use doc_diff
  "is_documentation_only": false,
  "delegated_to":   null
}
```

**File-uniqueness invariant**: every file path appears in exactly one
milestone. If two milestones need the same file, either consolidate them or
extract the shared edit into an upstream M-000 foundation milestone.

**Parallelization**: prefer vertical slices (M1=auth, M2=users, M3=posts)
over horizontal layers (M1=models, M2=services, M3=controllers). Layer
slicing forces sequential execution.

### CodeIntent  (id format `CI-NNN`)

Behavioral description the Developer turns into a CodeChange in a later
phase. The architect produces intents only.

```jsonc
{
  "id":            "CI-001",
  "version":       1,
  "file":          "src/auth.py",
  "function":      "validate_token",          // optional
  "behavior":      "Validate JWT signature against settings.JWT_SECRET; "
                   "raise HTTPException(401) on mismatch.",
  "decision_refs": [ "DL-001" ]               // must exist in decision_log
}
```

### CodeChange  (id format `CC-M-NNN-NNN`)

Filled by the Developer in plan-code phase. Not the architect's concern in
plan-design.

```jsonc
{
  "id":         "CC-M-001-001",
  "version":    1,
  "intent_ref": "CI-001",       // null only for doc-only changes
  "file":       "src/auth.py",
  "diff":       "...unified diff...",
  "doc_diff":   "",             // populated by Technical Writer
  "comments":   "WHY this change is needed (not what)."
}
```

---

## § diagrams

```jsonc
{
  "id":     "DIAG-001",
  "type":   "architecture" | "state" | "sequence" | "dataflow",
  "scope":  "overview" | "invisible_knowledge" | "milestone:M-001",
  "title":  "System overview",
  "nodes":  [ { "id": "client", "label": "Client", "type": "service" }, ... ],
  "edges":  [ { "source": "client", "target": "server", "label": "POST /login", "protocol": "HTTPS" }, ... ],
  "ascii_render": null   // populated by Technical Writer, not Architect
}
```

**Skip a diagram if:** pure refactor, single-file change, or
documentation-only milestone. Adding a diagram to such a plan adds noise
without insight.

**Add a diagram when:** multiple services interact, data flows through
pipeline stages, a protocol has state transitions, or an SDK/API boundary
needs surfacing.

---

## Reference invariants

- **CAS versioning**: every `version` field starts at 1 and increments on
  every CLI mutation. The CLI uses this to detect concurrent edits.
- **ID prefixes**: `DL-` decisions, `RA-` rejected alternatives, `R-` risks,
  `M-` milestones, `CI-` intents, `CC-` changes, `DIAG-` diagrams,
  `W-` waves.
- **Cross-reference integrity** is checked by `Plan.validate_refs()`. If
  `decision_refs` or `intent_ref` points at a missing ID, validation fails
  and the architect must fix the reference before proceeding.
- **`is_documentation_only`** trades requirements for doc edits: when true,
  acceptance criteria describe doc state, not code state.

---

## Building plan.json — invocation cheatsheet

Single command:

```
python3 -m skills.planner.cli.plan --state-dir $STATE_DIR \
    set-decision --decision '...' --reasoning '...'
```

Batch (preferred — one process per planning step, not per field):

```
python3 -m skills.planner.cli.plan --state-dir $STATE_DIR batch '[
  {"method": "set-decision",  "params": {"decision": "X", "reasoning": "Y"},   "id": 1},
  {"method": "set-milestone", "params": {"name": "Auth", "files": "src/a.py"}, "id": 2},
  {"method": "set-intent",    "params": {"milestone": "M-001", "file": "src/a.py", "behavior": "...", "decision_refs": "DL-001"}, "id": 3}
]'
```

Each batch element returns `{ "id": N, "result": {...} }` on success or
`{ "id": N, "error": {"code": -32000, "message": "..."} }` on failure.

Final validation:

```
python3 -m skills.planner.cli.plan validate --phase plan-design
```

Output `PASS` only after the validate call succeeds.
