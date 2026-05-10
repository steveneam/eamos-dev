<!-- Source: https://github.com/solatis/claude-config — integrated into Eamos project -->
# Planner Skill Design Intent

Authoritative design specification for the planner skill. This document governs WHY the system works the way it does. Implementation MUST conform to this spec.

## Philosophy

Three principles govern this design:

**RESOLVE AMBIGUITY EARLY**: Business decisions happen in planning phase, BEFORE code is written. Execution is mechanical. Questions about requirements, architecture, or approach get answered during planning, not discovered during implementation.

**CAPTURE INVISIBLE KNOWLEDGE**: Decisions, rationale, and context are captured in state files so any agent can understand WHY, not just WHAT. When a sub-agent picks up work, it reads state files and has full context. No information lives only in conversation history.

**QUALITY OVER SPEED**: LLMs make mistakes. Multiple QR gates with iteration loops catch errors before they propagate. This skill explicitly trades execution time for correctness.

## State Files

All state mutation (except initial context capture) happens via Python scripts. The orchestrator dispatches sub-agents; sub-agents invoke scripts; scripts emit prompts; LLM performs work and writes state.

### context.json

Created by orchestrator in step 2 (context-verify). Persists user-provided planning context for sub-agent handover.

```json
{
  "task_spec": ["goal sentence", "scope: dir/module", "out-of-scope: X"],
  "constraints": ["MUST: X", "SHOULD: Y"],
  "entry_points": ["file:function - why relevant"],
  "rejected_alternatives": ["alternative - why dismissed"],
  "current_understanding": ["how system works", "bug: symptom + repro"],
  "assumptions": ["inference (H/M/L confidence)"],
  "invisible_knowledge": ["design rationale", "invariants", "tradeoffs"],
  "user_quotes": ["verbatim quote with context"],
  "reference_docs": ["doc/spec.md - what it specifies"]
}
```

All fields are string arrays. Empty arrays are acceptable; omitting fields is not.

### plan.json

Primary state file. Created in step 1 (plan-init) as skeleton. Mutated through planning phases.

Key schema elements:

```
Plan
  overview
    problem: string
    approach: string

  planning_context
    decisions: Decision[]
      id: "DL-001"
      decision: string
      reasoning: string  -- logical chain using -> notation

    rejected_alternatives: RejectedAlternative[]
    constraints: string[]
    risks: Risk[]

  invisible_knowledge
    system: string
    invariants: string[]
    tradeoffs: string[]

  diagram_graphs: DiagramGraph[]
  milestones: Milestone[]
  waves: Wave[]
```

Waves execute in array order. All milestones in W-001 complete before W-002 begins. Milestones within a wave may execute in parallel.

### qr-{phase}.json

Ephemeral QR state. Created during QR decomposition. Deleted after phase passes. Five phases: plan-design, plan-code, plan-docs, impl-code, impl-docs.

## Invariants

**Sub-agents cannot launch sub-agents.** Only orchestrator dispatches. Maintains audit trail, prevents hidden dependencies.

**Sub-agents cannot invoke AskUserQuestion.** Sub-agents that need user input yield with `<needs_user_input>` XML. Orchestrator relays question, then reinvokes sub-agent fresh with answer.

**Orchestrator LLM never reads/writes state files.** Context flows through dispatch prompts. State files are sub-agent territory.

**Orchestrator is a dumb dispatcher.** Routes based on status flags and step numbers. Never makes quality judgments or skips steps.

**Sub-agent self-validation.** Every sub-agent that writes to state files must validate the written file before returning to orchestrator.

**User authority is absolute.** Agent findings may be wrong. User decisions override everything.

**Always run scripts.** Every step invokes a Python script. No free-form execution.

**State detection over flags.** Work scripts detect their mode from state file presence, not from CLI flags.

**QR iteration limit.** Maximum 5 iterations per QR phase.
