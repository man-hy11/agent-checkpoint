---
name: checkpoint-evidence
description: "Use after execute or verify-gate to validate the evidence document and transition the unit to passed or failed via work pass or work fail."
---

# Checkpoint — Evidence

Execution or gate verification is complete. Validate the evidence document and record the result.

## Validate the evidence

The evidence document must satisfy all sections in `evidence_required` for the unit's kind. Check the manifest or run `agent-checkpoint work status --json` to see the required sections.

No credential-shaped text, no diff content, at most 8000 characters.

## Transition the unit

On success:

```bash
agent-checkpoint work pass \
  --unit UNIT_ID \
  --plan-revision PLAN_REVISION \
  --evidence-file EVIDENCE_FILE \
  --root .
```

On failure:

```bash
agent-checkpoint work fail \
  --unit UNIT_ID \
  --plan-revision PLAN_REVISION \
  --evidence-file EVIDENCE_FILE \
  --root .
```

The CLI validates the evidence before writing. If it exits 2, fix the evidence and retry.

## After the transition

Checkpoint and stop. Do not start the next unit in the same session.
