---
type: project
date: 2026-06-18
---

# Graphify Generated Output Hygiene

Graphify's AST update and semantic passes are useful as local navigation tools, but `graphify-out/` is generated state. Keep the whole output tree ignored in Git and in `.graphifyignore`; commit source, handoff, and memory changes, not regenerated graph JSON, reports, manifests, or dated snapshots.

Related: [[graphify-generated-output-hygiene]], [[graphify]], [[handoff-hygiene]]

Files:
- `.gitignore`
- `.graphifyignore`
- `graphify-out/`

Lesson: when a project tool can rebuild an artifact from source, treat the artifact directory as local cache unless there is an explicit review reason to version a specific exported file.

What's easier now: future graphify AST updates and dated snapshots can run after code changes without making `git add -A` dangerous or burying real source diffs in generated graph churn.
