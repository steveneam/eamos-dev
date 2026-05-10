<!-- Source: https://github.com/solatis/claude-config — integrated into Eamos project -->
# Skills Architecture

Script-based agent workflows with shared orchestration framework.

## Overview

Skills are structured agent workflows that orchestrate LLM sub-agents through Python scripts. The Python script IS the workflow -- it emits prompts, the LLM performs work, and state is managed in JSON files.

## Core Patterns

### The "Book" Pattern

Skill files organize content so readers understand dependencies without scrolling backward. Section ordering follows:

1. Shared Prompts
2. Configuration
3. System Prompts
4. Message Templates
5. Parsing Functions
6. Message Builders
7. Domain Logic
8. Step Definitions
9. Output Formatting
10. Entry Point

### Step-Delimited Templates

Within MESSAGE TEMPLATES, step dividers organize content chronologically:

```python
# --- STEP N: PHASE_NAME -----------------------------------------------------------
```

### Dispatch Separation

Static template fragments stay in MESSAGE TEMPLATES as constants. Composition logic lives in MESSAGE BUILDERS functions. This ensures prompt text is visible at the constant definition.

### Naming Convention

Pattern: `[PHASE]_[TYPE]`

Where PHASE is workflow stage (SCOPE, SURVEY, DEEPEN, SYNTHESIZE) and TYPE indicates role (INSTRUCTIONS, DISPATCH_CONTEXT, etc.).

## Anti-patterns to Avoid

- Action factories that return conditional fragments
- Forward references (using a constant before it is defined)
- Composition logic embedded in MESSAGE TEMPLATES

Instead: compose constants directly using string concatenation in MESSAGE BUILDERS.

## Shared Library

`lib/workflow/prompts/` contains three reusable modules:
- `subagent.py` -- dispatch templates
- `step.py` -- step formatting
- `file_content.py` -- file embedding

## Implementation Patterns

Five patterns emerge across skills:

1. Static steps with separate title/instruction dicts
2. Parameterized steps with templates + builders
3. Dispatch steps spawning sub-agents
4. File injection for reference material
5. Hybrid static/dynamic steps

The fundamental abstraction is the step itself: **body + invoke_after**.
