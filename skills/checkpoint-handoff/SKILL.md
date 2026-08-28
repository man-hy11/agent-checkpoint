---
name: checkpoint-handoff
description: Use when every unit is passed — generates the final handoff context for the completed work package.
---

# Checkpoint — Handoff

Every unit is `passed`. Generate the handoff.

## Generate the handoff

```bash
agent-checkpoint handoff --root .
```

The handoff renders a bounded summary of completed work, verification results, and decisions. Include any constraints or deferred items the next session must know.

The rendered output includes an "Open Handoff Reports" section listing any files under `.agent-checkpoint/handoff/` — these are deferred items a prior step wrote instead of folding into its own scope. Surface them explicitly to the next session; do not let them go unmentioned just because they rendered automatically.

If the project's `.agent-checkpoint.toml` sets `auto_commit_on_handoff = true`, the command also stages and commits the working tree after rendering the handoff -- this is opt-in and off by default. A commit failure (nothing to commit, no Git repository, a rejecting pre-commit hook) is reported to stderr and never blocks handoff from completing; check stderr if you need to know whether it happened.

## Check, then ask, about each open report

For every report in that section besides the one for this work package:

**First check whether it is already resolved.** A report is written when a step defers something; nothing marks it done when the work later happens, so an open report is not evidence that the work is outstanding. Read the report's "What was found" section and verify against the tree as it stands now — the named function, line, or behavior may already be fixed by a later unit or an unrelated commit. `git log --oneline -- PATH` on the file it names usually settles it. A report can also be voided rather than fixed: if what it describes no longer matters (the code path was deleted, the dependency dropped, the distribution channel retired), it is just as closed.

State the finding for each report — resolved by what, or still outstanding — then ask the user how to proceed:

- **Already resolved or voided**: say what closed it, then resolve the report with `agent-checkpoint handoff resolve --root . --name NAME`.
- **Act now**: start a new work package for it with `agent-checkpoint workflow --type TYPE --id ID`, then resolve the report the same way so it stops surfacing on every future handoff.
- **Leave open**: do nothing further — it renders again on the next handoff.

Resolving deletes the report file, and reports are untracked, so a resolved report leaves no trace behind — the reason it closed lives only in what you say here and in the commit that did the work. Say it explicitly rather than resolving silently.

Never resolve a report on the user's behalf without confirmation, and never leave one open merely because checking would take a moment. Reports that are silently carried forward accumulate: every future handoff re-renders them, and the next session cannot tell a live deferral from one that was fixed months ago.

## Finalize the work package

Run the final package renderer if applicable:

```bash
agent-checkpoint workflow --type TYPE --id WORK_ID
```

Record the handoff evidence in `EVIDENCE.md`.

## After handoff

Checkpoint and stop. The work is complete.
