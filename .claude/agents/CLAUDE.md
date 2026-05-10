# agents/

Custom subagent role definitions. Each file is a system-prompt fragment that shapes an agent's persona, scope, and constraints when invoked via the Agent tool.

## Files

| File | What | When to read |
| ---- | ---- | ------------ |
| `architect.md` | Architect agent — system design, architecture decisions, trade-off analysis | Spawning or tuning the architect agent |
| `debugger.md` | Debugger agent — systematic root-cause analysis, evidence gathering | Spawning or tuning the debugger agent |
| `developer.md` | Developer agent — implementation, test writing, code changes | Spawning or tuning the developer agent |
| `quality-reviewer.md` | Quality-reviewer agent — production risk, spec conformance, code structure | Spawning or tuning the QR agent |
| `technical-writer.md` | Technical-writer agent — LLM-optimised documentation | Spawning or tuning the TW agent |
| `ui-ux-consultant.md` | UI/UX consultant agent — desktop accessibility, platform standards | Spawning or tuning the UI agent |
