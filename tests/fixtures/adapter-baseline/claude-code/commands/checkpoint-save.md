---
description: Save a concise, resumable checkpoint for the current project.
---

Compose a checkpoint entry from the current work using these exact headings:

- `## 2. Progress`
- `## 5. Decisions / Constraints / Notes`

When a work package's `CURRENT.md` exists, do not restate its Goal/Plan or
Current Focus in the checkpoint entry — `CURRENT.md` is that information's
only source. Record only what changed this session.

If no work package exists yet, this session did substantive work without
ever running `agent-checkpoint workflow`. Follow the checkpoint-save
skill's Case B: recommend a workflow type from the session's actual work
and wait for confirmation, run
`"${CLAUDE_PLUGIN_ROOT}/bin/agent-checkpoint" workflow --type TYPE --id
current`, backfill `.agent-checkpoint/work/current/BRIEF.md` and
`PROJECT_CONTEXT.md` from what already happened (do not invent unanswered
fields), set `brief_confirmed: true`, and — only if planning already
reads as done, confirmed with the user — hand off to checkpoint-plan
rather than drafting `PLAN.md` here.

Keep it brief, exclude credentials and diff content, and pass the entry on standard
input to `"${CLAUDE_PLUGIN_ROOT}/bin/agent-checkpoint" write --entry -`. Add each
concrete test/build result with a repeated `--verification TEXT` option. Confirm
the result briefly. If the command fails, report its diagnostic without claiming
that the checkpoint was saved.
