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

## Finalize the work package

Run the final package renderer if applicable:

```bash
agent-checkpoint workflow --type TYPE --id WORK_ID
```

Record the handoff evidence in `EVIDENCE.md`.

## After handoff

Checkpoint and stop. The work is complete.
