---
name: checkpoint-handoff
description: "Use when every unit is passed \u2014 generates the final handoff context for the completed work package."
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

## Ask about each open report

For every report in that section besides the one for this work package, ask the user whether to act on it now or leave it open:

- **Act now**: start a new work package for it with `agent-checkpoint workflow --type TYPE --id ID`, then resolve the report with `agent-checkpoint handoff resolve --root . --name NAME` so it stops surfacing on every future handoff.
- **Leave open**: do nothing further — it renders again on the next handoff.

Only resolve a report once the user has confirmed the described work is actually done or intentionally started elsewhere. Never resolve a report silently on its behalf.

## Finalize the work package

Run the final package renderer if applicable:

```bash
agent-checkpoint workflow --type TYPE --id WORK_ID
```

Record the handoff evidence in `EVIDENCE.md`.

## After handoff

Checkpoint and stop. The work is complete.
