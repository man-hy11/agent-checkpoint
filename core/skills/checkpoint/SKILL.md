---
name: checkpoint
description: Use when saving resumable project progress, recording current work and next actions, or preparing context for a later session or context window.
---

# Checkpoint

Create a concise, durable project checkpoint. Capture current facts and decisions,
not a transcript, and never include credentials or diff content.

## Template-backed planning

Before the first checkpoint for a work item, choose the workflow type from the
bundled selector (`project`, `feature`, `bugfix`, `refactor`, `upgrade`,
`migration`, `performance`, `integration`, `release`, or `spike`) and create
its work package:

```bash
agent-checkpoint workflow --type TYPE --id current
```

If no workflow type has been specified yet, ask the user to choose one before
running the command. Do not infer or silently default the type. The work id may
remain `current` unless the user wants multiple concurrent work packages.

Read `.agent-checkpoint/work/current/prompts/PLAN_*.md` and populate the
materialized package's `CURRENT.md` and planning files. Then make each
checkpoint entry a short pointer to that package: work type, current Step/Gate,
and the next-session read order `PROGRESS.md -> CURRENT.md ->
CONTINUE_PROMPT.md`. Keep detailed plans and evidence in the work package.

Before filling a planning template, check whether the user has supplied the
goal, scope, success criteria, constraints, and affected area needed by that
workflow. If any material planning field is unknown, ask concise questions and
wait for the answers; do not fabricate details or advance `CURRENT.md` to an
implementation Step. Record only confirmed answers in the package.

Compose an entry with these exact headings:

```markdown
## 1. Goal / Plan
- State the goal and the current high-level plan.

## 2. Progress
- List completed work and why it matters.

## 3. Current Focus
- Record the active work and its status.

## 4. Next Actions / TODO
- List small next steps in priority order.

## 5. Decisions / Constraints / Notes
- Preserve decisions, constraints, risks, and essential context.
```

Keep bullets brief and write only what a later agent needs to resume. Pass the
completed entry on standard input to:

```bash
agent-checkpoint write --entry -
```

Add each concrete test/build result with a repeated `--verification TEXT`
option. The CLI persists those results separately from decisions and renders
them in handoff output. Follow the `Language:` instruction produced by resume
and handoff.

Use `--root PATH` when the project root is not the current directory. Report the
CLI result briefly; do not claim the checkpoint was saved if the command failed.
