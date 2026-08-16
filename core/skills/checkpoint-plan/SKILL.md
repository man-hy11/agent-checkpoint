---
name: checkpoint-plan
description: Use when the work package brief is confirmed but the unit list is empty or the current unit is superseded — creates or updates the implementation plan.
---

# Checkpoint — Plan

The brief is confirmed, but planning is incomplete. The unit list is empty, the current unit is superseded, or a plan revision is needed.

## Read the manifest

Check the work type in the state block, then read its planning template from the work package. For each plan unit, assign a unique ID (using the manifest's `unit_prefix`), set its `kind` (`step` or `gate`), and record it in the state block.

## Write the plan

Populate `PLAN.md` with numbered steps tied to unit IDs. No unit may start without an entry in the state block.

## Revise the plan

If an existing plan needs revision after a failed unit:

```bash
agent-checkpoint work revise --plan-revision N --evidence-file EVIDENCE_FILE
```

Only `checkpoint-plan` edits `PLAN.md`. The recovery skill decides to replan; this skill executes it.

## Why this skill and not checkpoint-claim?

`checkpoint-plan` fires when no executable unit exists. `checkpoint-claim` fires when a unit is `pending` or `ready` — meaning the plan is already present and a specific unit is next.
