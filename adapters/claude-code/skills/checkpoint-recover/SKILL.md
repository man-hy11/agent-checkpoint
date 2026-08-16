---
name: checkpoint-recover
description: "Use when the current unit is failed (with a root_cause_fingerprint) or blocked \u2014 selects a recovery event (retry, replan, supersede, block, unblock) and applies it."
---

# Checkpoint — Recover

The current unit is `failed` (fingerprint recorded) or `blocked`. Select a recovery event and apply it.

## Check allowed events

```bash
agent-checkpoint work status --root . --json
```

Read `allowed_events`. Available recovery events: `retry`, `replan`, `supersede`, `block`, `unblock`.

`retry` may be refused when the attempt ceiling is reached or the last two fingerprints are identical. In that case, choose `replan`, `supersede`, or `block`.

## Apply the recovery event

```bash
agent-checkpoint work recover \
  --unit UNIT_ID \
  --plan-revision PLAN_REVISION \
  --event EVENT \
  --evidence-file EVIDENCE_FILE \
  --root .
```

Evidence must include a root cause analysis and the changed hypothesis for `retry`. For `replan`, include the new plan revision rationale.

## After recovery

Checkpoint and stop. A retry returns the unit to `ready`; the next session claims it again.
