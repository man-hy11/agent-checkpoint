---
name: checkpoint-verify-gate
description: Use when the current unit is running and its kind is gate — verifies acceptance criteria, then hands results to checkpoint-evidence.
---

# Checkpoint — Verify Gate

The current unit is `running` and its kind is `gate`. Verify all acceptance criteria, then record evidence.

## Verify gate criteria

A gate unit checks cross-cutting quality: regression, compatibility, acceptance, sign-off. Typical evidence sections required by the manifest's `evidence_required.gate` list: `acceptance_criteria`, `regression_check`, `sign_off`.

Do not approve a gate if any criterion is unmet. A partial pass is a failure; use `checkpoint-evidence` with `pass_fail: failed`.

## Hand to checkpoint-evidence

Do not call `work pass` or `work fail` yourself. Pass the completed evidence document to `checkpoint-evidence`, which validates it and completes the transition.

## Why this skill and not checkpoint-execute?

`checkpoint-verify-gate` fires for `gate` units. `checkpoint-execute` fires for `step` units. Gate evidence requires `acceptance_criteria` and `sign_off`; step evidence requires `command` and `observed_output`.
