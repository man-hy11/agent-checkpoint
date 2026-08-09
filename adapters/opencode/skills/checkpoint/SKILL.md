---
name: checkpoint
description: Use to manually save resumable project progress, read resume context, create a handoff, or diagnose the checkpoint CLI.
---

# Checkpoint

This adapter is manual-only: use the OpenCode checkpoint, resume, and handoff
commands when needed. It does not configure lifecycle hooks or automatic
context injection.

## Checkpoint

For a new work item, choose the matching bundled workflow type and run
`agent-checkpoint workflow --type TYPE --id current`. Read and fill
`.agent-checkpoint/work/current/CURRENT.md` and its `PLAN_*.md` prompt before
writing the checkpoint. Keep `PROGRESS.md` concise: point to the package,
Current Step/Gate, and `PROGRESS.md -> CURRENT.md -> CONTINUE_PROMPT.md`.
If no type was specified, ask the user to choose one; never infer it.
Before filling planning files, ask concise questions for missing goal, scope,
success criteria, constraints, or affected area. Do not invent details or
advance the tracker until answered.

Create a concise entry with these exact headings, excluding credentials and
diff content:

```markdown
## 1. Goal / Plan
## 2. Progress
## 3. Current Focus
## 4. Next Actions / TODO
## 5. Decisions / Constraints / Notes
```

Pass the completed entry on standard input to the installed CLI:

```bash
agent-checkpoint write --entry -
```

Add concrete test/build results with repeated `--verification TEXT` options.

Use `--root PATH` when the project root is not the current directory. Report
the CLI result briefly and do not say the checkpoint was saved when it fails.

## Resume

Render the current checkpoint context manually:

```bash
agent-checkpoint resume
```

Use `--root PATH` or `--max-chars NUMBER` when appropriate.
Follow the rendered `Language:` instruction.

## Handoff

Create a manual handoff summary for the next agent:

```bash
agent-checkpoint handoff
```

Use `--root PATH` or `--max-chars NUMBER` when appropriate.
Preserve the rendered verification section separately from recent decisions,
and follow the rendered `Language:` instruction.

## Doctor

Check the installed CLI when checkpoint behavior is unavailable or unexpected:

```bash
agent-checkpoint doctor --adapter opencode
```

If `agent-checkpoint` is not found, install it from this project's source
directory, then ensure the prefix's `bin` directory is on `PATH`:

```bash
python3 tools/install.py --prefix "$HOME/.local"
```
