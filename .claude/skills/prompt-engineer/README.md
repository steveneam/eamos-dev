<!-- Source: https://github.com/solatis/claude-config — integrated into Eamos project -->
# Prompt Engineer

Prompts are code. They have bugs, edge cases, and failure modes. This skill treats prompt optimization as a systematic discipline -- analyzing issues, applying documented patterns, and proposing changes with explicit rationale.

## When to Use

- A sub-agent definition that misbehaves
- A Python script with embedded prompts that underperform
- A multi-prompt workflow that produces inconsistent results
- Any prompt that does not do what you intended

## How It Works

1. Reads prompt engineering pattern references
2. Analyzes the target prompt for issues
3. Proposes changes with explicit pattern attribution
4. Waits for approval before applying changes
5. Presents optimized result with self-verification

Recitation and careful output ordering ground the skill in referenced patterns, preventing the model from inventing techniques.

## Example Usage

Optimize a sub-agent:

```
Use your prompt engineer skill to optimize the system prompt for
the following claude code sub-agent: agents/developer.md
```

Optimize a multi-prompt workflow:

```
Consider @skills/planner/scripts/planner.py. Identify all prompts,
understand how they interact, then use your prompt engineer skill
to optimize each.
```

## Output Format

Each proposed change includes: scope, problem, technique, before/after, and rationale.

## Caveat

When you tell an LLM "find problems and opportunities for optimization", it will find problems. Some may not be real issues. Invoke the skill multiple times on challenging prompts, but recognize when good enough and stop. Diminishing returns are real.
