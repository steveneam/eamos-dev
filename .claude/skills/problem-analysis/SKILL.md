<!-- Source: https://github.com/solatis/claude-config — integrated into Eamos project -->
---
name: problem-analysis
description: Invoke IMMEDIATELY via python script when user requests problem analysis or root cause investigation. Do NOT explore first - the script orchestrates the investigation.
---

# Problem Analysis

Identifies WHY a problem occurs, NOT how to fix it.

When this skill activates, IMMEDIATELY invoke the script. The script IS the workflow.

## Invocation

```
python3 -m skills.problem_analysis.analyze --step 1
```

Working directory: `.claude/skills/scripts`

Do NOT explore or analyze first. Run the script and follow its output.
