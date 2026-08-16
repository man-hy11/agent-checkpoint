---
name: checkpoint-claim
description: Use when the current unit is pending or ready — verifies its dependency, then starts it with work start.
---

# Checkpoint — Claim

The current unit is `pending` or `ready`. Claim it before starting execution.

## Verify the dependency

A `pending` unit may have a predecessor that is not yet `passed`. Confirm the dependency is satisfied before claiming.

## Start the unit

```bash
agent-checkpoint work start \
  --unit UNIT_ID \
  --plan-revision PLAN_REVISION \
  --root .
```

This transitions the unit to `running`. Do not begin implementation before this command succeeds.

## After claiming

After a successful `work start`, run `agent-checkpoint work status --root . --json` to confirm the unit is now `running` and `next_skill` has advanced to `checkpoint-execute` or `checkpoint-verify-gate`.
