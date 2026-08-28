---
name: checkpoint
description: Routes to the correct phase skill by running work status — determines which of the thirteen checkpoint skills acts next and dispatches accordingly.
---

# Checkpoint — Router

Determine which skill acts next by reading the current work state:

```bash
agent-checkpoint work status --root . --json
```

The `next_skill` field names the skill to invoke. Invoke it now. Do not perform any other action in this skill.

## Routing table (summary)

See `_checkpoint-shared/chain-v1.md` for the full ordered routing table. Representative cases:

| Condition | next_skill |
|---|---|
| No state block | checkpoint-select-workflow |
| `brief_confirmed` false | checkpoint-brainstorm |
| Units empty or current superseded | checkpoint-plan |
| All units completed | checkpoint-plan |
| Current unit blocked | checkpoint-recover |
| Current unit failed, no fingerprint | checkpoint-diagnose |
| Current unit failed, fingerprint set | checkpoint-recover |
| Current unit pending or ready | checkpoint-claim |
| Current unit running, kind gate | checkpoint-verify-gate |
| Current unit running, kind step | checkpoint-execute |

## Initializing a new work package

If no work package exists yet, run:

```bash
agent-checkpoint workflow --type TYPE --id current
```

Then re-run `work status` to confirm `next_skill` and proceed.

## This skill never acts directly

It reads state and dispatches. All execution, verification, evidence recording, and recovery are performed by the named skill, not here.
