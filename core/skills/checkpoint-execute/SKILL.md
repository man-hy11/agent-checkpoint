---
name: checkpoint-execute
description: Use when the current unit is running and its kind is step — implements the step, then hands results to checkpoint-evidence.
---

# Checkpoint — Execute

The current unit is `running` and its kind is `step`. Implement it, then record evidence.

## Implement the step

Follow the plan for this unit exactly. Do not expand scope or start the next unit.

## Collect evidence

When the step is complete, document the result using the sections required by the manifest's `evidence_required.step` list. Typical required sections: `command`, `pass_fail`, `observed_output`.

## Hand to checkpoint-evidence

Do not call `work pass` or `work fail` yourself. Pass the evidence document to `checkpoint-evidence`, which validates it and completes the transition.

## Scope boundary

This skill covers `step` units only. Acceptance criteria and cross-cutting checks belong to a different skill. Do not reference those concepts here.
