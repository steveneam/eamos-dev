<!-- Source: https://github.com/solatis/claude-config — integrated into Eamos project -->
---
name: deepthink
description: Invoke IMMEDIATELY via python script when user requests structured reasoning for open-ended analytical questions. Do NOT explore first - the script orchestrates the thinking workflow.
---

# DeepThink

Structured reasoning skill for open-ended analytical questions where the answer structure itself is unknown.

When this skill activates, IMMEDIATELY invoke the script. The script IS the workflow.

## Invocation

```
python3 -m skills.deepthink.think --step 1
```

Working directory: `.claude/skills/scripts`

Do NOT analyze or explore first. Run the script and follow its output.
