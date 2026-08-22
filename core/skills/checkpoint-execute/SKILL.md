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

## Discovered work: fold in or defer

If you notice work beyond this unit's declared scope while implementing:

- **Small fix, same area, no scope creep** — fold it into this unit's evidence and mention it there. Do not open a new unit for it.
- **Large enough to need its own unit, or genuinely out of scope for this work package** — do not implement it here. Write a handoff report instead of silently dropping it or silently expanding scope: `.agent-checkpoint/handoff/<work_id>-<unit_id>-<slug>.md`, naming what was found, why it was deferred, and enough context for a future session to act on it without re-discovering it. The directory is created on first use.

The size judgment is yours to make in the moment; when in doubt, prefer a handoff report over expanding this unit's scope.

## Hand to checkpoint-evidence

Do not call `work pass` or `work fail` yourself. Pass the evidence document to `checkpoint-evidence`, which validates it and completes the transition.

## Scope boundary

This skill covers `step` units only. Acceptance criteria and cross-cutting checks belong to a different skill. Do not reference those concepts here.
