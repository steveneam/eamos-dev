<!-- Source: https://github.com/solatis/claude-config — integrated into Eamos project -->
---
name: refactor
description: Invoke IMMEDIATELY via python script when user requests refactoring analysis, technical debt review, or code quality improvement. Do NOT explore first - the script orchestrates exploration.
---

# Refactor

When this skill activates, IMMEDIATELY invoke the script. The script IS the workflow.

## Invocation

```
python3 -m skills.refactor.refactor --step 1 [--n 10]
```

Working directory: `.claude/skills/scripts`

| Argument | Required | Description                                   |
| -------- | -------- | --------------------------------------------- |
| `--step` | Yes      | Current step (starts at 1)                    |
| `--n`    | No       | Number of smell categories to analyze (default: 10) |

## Scope Determination

Adjust `--n` based on request size:

- Small scope requests: `--n 5`
- Standard analysis: `--n 10` (default)
- Comprehensive reviews: `--n 25`

Do NOT explore or analyze first. Run the script and follow its output.
