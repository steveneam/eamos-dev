<!-- Source: https://github.com/solatis/claude-config — integrated into Eamos project -->
# Planner Skill

Planning and execution skill with quality review gates.

## Overview

The planner skill transforms user requests into executable plans through a structured multi-phase workflow. It separates concerns: the orchestrator routes and coordinates; sub-agents (architect, developer, technical-writer, quality-reviewer) do specialized work; Python scripts emit prompts and manage state.

## Philosophy

Three principles govern this design:

**RESOLVE AMBIGUITY EARLY**: Business decisions happen in planning phase, BEFORE code is written. Execution is mechanical. Questions about requirements, architecture, or approach get answered during planning, not discovered during implementation.

**CAPTURE INVISIBLE KNOWLEDGE**: Decisions, rationale, and context are captured in state files so any agent can understand WHY, not just WHAT. When a sub-agent picks up work, it reads state files and has full context. No information lives only in conversation history.

**QUALITY OVER SPEED**: LLMs make mistakes. Multiple QR gates with iteration loops catch errors before they propagate. This skill explicitly trades execution time for correctness.

## Architecture

Two interconnected workflows:

### Planning Workflow (14 steps)

Transforms user request into executable plan (the IR):

```
Step 1: plan-init
Step 2: context-verify
Step 3: plan-design-work (architect)
Steps 4-6: plan-design QR block
Step 7: plan-code-work (developer)
Steps 8-10: plan-code QR block
Step 11: plan-docs-work (technical-writer)
Steps 12-14: plan-docs QR block
```

### Execution Workflow (10 steps)

Implements the approved plan:

```
Step 1: exec-init
Steps 2-5: impl-code block (developer + QR)
Steps 6-9: impl-docs block (technical-writer + QR)
Step 10: wave-next
```

## State Files

All state mutation happens via Python scripts. Three primary state files:

- `context.json` -- user-provided planning context, created at step 2
- `plan.json` -- primary state, overview + milestones + code changes
- `qr-{phase}.json` -- ephemeral QR state, created and deleted per phase

## Key Invariants

- Sub-agents cannot launch sub-agents
- Orchestrator LLM never reads/writes state files directly
- Sub-agents self-validate written state before returning
- User authority is absolute -- user decisions override agent findings
- Maximum 5 QR iterations per phase
