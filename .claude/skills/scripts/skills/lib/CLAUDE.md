# lib/

Shared orchestration library used by all skill implementations.

## Files

| File | What | When to read |
| ---- | ---- | ------------ |
| `conventions.py` | Documentation convention helpers | Changing how skills read or apply conventions |
| `io.py` | File I/O utilities — state files, output writing | Changing state persistence or output handling |

## Subdirectories

| Directory | What | When to read |
| --------- | ---- | ------------ |
| `workflow/` | Workflow engine — step dispatch, AST building, prompt rendering | Modifying skill orchestration infrastructure |
