# workflow/

Workflow engine for skill orchestration: step dispatch, AST-based prompt building, CLI runner.

## Files

| File | What | When to read |
| ---- | ---- | ------------ |
| `cli.py` | CLI entry point — `--step N` argument parsing and dispatch | Changing how skills are invoked from the command line |
| `core.py` | Core workflow runner — step sequencing, state management | Changing how steps execute or state is managed |
| `constants.py` | Shared constants across the workflow engine | Changing shared values |
| `discovery.py` | Codebase discovery helpers — file enumeration, structure detection | Changing how skills discover project files |
| `quality_docs.py` | Quality documentation helpers | Changing quality doc generation |
| `types.py` | Shared type definitions for the workflow engine | Changing data structures |

## Subdirectories

| Directory | What | When to read |
| --------- | ---- | ------------ |
| `ast/` | AST-based prompt builder — structured prompt construction | Modifying prompt building logic |
| `prompts/` | Prompt template helpers — file, step, and sub-agent prompts | Modifying prompt templates or rendering |
