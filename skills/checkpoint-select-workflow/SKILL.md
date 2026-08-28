---
name: checkpoint-select-workflow
description: Use when no workflow type has been chosen yet — routes the agent to pick a workflow family and initialize its work package before any planning begins.
---

# Checkpoint — Select Workflow

No work package exists yet. Select a workflow type and initialize one.

## Choose a workflow type

Ask the user which of the ten workflow types fits their work:

```
project, feature, bugfix, refactor, upgrade,
migration, performance, integration, release, spike
```

Do not infer or default the type silently. Wait for an explicit answer.

## Initialize the work package

Once the type is chosen, run:

```bash
agent-checkpoint workflow --type TYPE --id current
```

After initialization, read the root `CONTINUE_PROMPT.md`, then `.agent-checkpoint/work/current/CURRENT.md`, then `.agent-checkpoint/work/current/CONTINUE_PROMPT.md`. Do not proceed to planning until the package exists.

## Why this skill and not checkpoint-brainstorm?

`checkpoint-select-workflow` fires when no state block exists at all — before any work package is initialized. `checkpoint-brainstorm` fires after a work package exists and its planning brief needs confirmation.
