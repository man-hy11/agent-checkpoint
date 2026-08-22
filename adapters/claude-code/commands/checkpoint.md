---
description: Save a concise, resumable checkpoint for the current project.
---

Compose a checkpoint entry from the current work using these exact headings:

- `## 2. Progress`
- `## 5. Decisions / Constraints / Notes`

When a work package's `CURRENT.md` exists, do not restate its Goal/Plan or
Current Focus in the checkpoint entry — `CURRENT.md` is that information's
only source. Record only what changed this session.

For a new work item, select the matching bundled development workflow and run
`"${CLAUDE_PLUGIN_ROOT}/bin/agent-checkpoint" workflow --type TYPE --id current`.
Read and fill `.agent-checkpoint/work/current/CURRENT.md` and its `PLAN_*.md`
prompt first. Keep `.agent-checkpoint/work/current/PROGRESS.md` concise:
point to the work package, Current Step/Gate, and the root `CONTINUE_PROMPT.md
-> CURRENT.md -> CONTINUE_PROMPT.md` read order (root `CONTINUE_PROMPT.md`
names the active package; the rest live under
`.agent-checkpoint/work/current/`).
If the user has not specified a type, ask them to choose one; do not infer it.
Before filling the planning files, ask concise questions for any missing goal,
scope, success criterion, constraint, or affected area. Do not invent details
or advance the tracker until the answers are available.

Keep it brief, exclude credentials and diff content, and pass the entry on standard
input to `"${CLAUDE_PLUGIN_ROOT}/bin/agent-checkpoint" write --entry -`. Add each
concrete test/build result with a repeated `--verification TEXT` option. Confirm
the result briefly. If the command fails, report its diagnostic without claiming
that the checkpoint was saved.
