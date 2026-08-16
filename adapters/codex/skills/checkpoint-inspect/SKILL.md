---
name: checkpoint-inspect
description: "Use to read and report work package state without making any changes \u2014 read-only diagnostic view of the current unit, allowed events, and next skill."
---

# Checkpoint — Inspect

Read-only view of the current work package state. This skill never writes.

## Read the current state

```bash
agent-checkpoint work status --root . --json
```

Report the key fields: `work_id`, `work_type`, `current_unit`, `state`, `attempt`, `next_skill`, `allowed_events`, `evidence_required`, `hard_rules`.

## What this skill does not do

- Does not call any state-transition or recovery commands.
- Does not edit `CURRENT.md`, `EVIDENCE.md`, or `PLAN.md`.
- Does not advance state.

Use `checkpoint-inspect` when you need to report state to the user or diagnose a stuck package without making changes.
