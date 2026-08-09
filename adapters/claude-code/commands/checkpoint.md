---
description: Save a concise, resumable checkpoint for the current project.
---

Compose a checkpoint entry from the current work using these exact headings:

- `## 1. Goal / Plan`
- `## 2. Progress`
- `## 3. Current Focus`
- `## 4. Next Actions / TODO`
- `## 5. Decisions / Constraints / Notes`

For a new work item, select the matching bundled development workflow and run
`"${CLAUDE_PLUGIN_ROOT}/bin/agent-checkpoint" workflow --type TYPE --id current`.
Read and fill `.agent-checkpoint/work/current/CURRENT.md` and its `PLAN_*.md`
prompt first. Keep `PROGRESS.md` concise: point to the work package, Current
Step/Gate, and `PROGRESS.md -> CURRENT.md -> CONTINUE_PROMPT.md` read order.
If the user has not specified a type, ask them to choose one; do not infer it.
Before filling the planning files, ask concise questions for any missing goal,
scope, success criterion, constraint, or affected area. Do not invent details
or advance the tracker until the answers are available.

Keep it brief, exclude credentials and diff content, and pass the entry on standard
input to `"${CLAUDE_PLUGIN_ROOT}/bin/agent-checkpoint" write --entry -`. Add each
concrete test/build result with a repeated `--verification TEXT` option. Confirm
the result briefly. If the command fails, report its diagnostic without claiming
that the checkpoint was saved.
