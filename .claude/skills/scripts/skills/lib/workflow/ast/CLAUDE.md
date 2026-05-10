# ast/

AST-based prompt builder for structured prompt construction.

## Files

| File | What | When to read |
| ---- | ---- | ------------ |
| `nodes.py` | AST node types — blocks, sections, messages | Changing prompt structure types |
| `builder.py` | Fluent AST builder API | Changing how prompts are constructed |
| `renderer.py` | AST-to-string renderer | Changing how AST renders to text |
| `dispatch.py` | Dispatch prompt builder | Changing dispatch prompt construction |
| `dispatch_renderer.py` | Dispatch-specific rendering logic | Changing dispatch prompt rendering |
