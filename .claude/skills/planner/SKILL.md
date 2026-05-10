<!-- Source: https://github.com/solatis/claude-config — integrated into Eamos project -->
---
name: planner
description: Interactive planning and execution for complex tasks. IMMEDIATELY invoke when user asks to use planner.
---

# Planner

When this skill activates, IMMEDIATELY invoke the corresponding script. The script IS the workflow.

## Planning Mode

Activated when user requests "plan", "design", or "architect":

```
python3 -m skills.planner.orchestrator.planner --step 1
```

Working directory: `.claude/skills/scripts`

## Execution Mode

Activated when user asks to "execute", "implement", or "run plan":

```
python3 -m skills.planner.orchestrator.executor --step 1
```

Working directory: `.claude/skills/scripts`

When this skill activates, IMMEDIATELY invoke the corresponding script. The script IS the workflow.
