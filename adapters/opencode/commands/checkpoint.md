---
description: Manually save a concise, resumable project checkpoint.
---

Create a concise checkpoint entry with these exact headings, excluding
credentials and diff content:

```markdown
## 2. Progress
## 5. Decisions / Constraints / Notes
```

When a work package's `CURRENT.md` exists, do not restate its Goal/Plan or
Current Focus in the checkpoint entry — `CURRENT.md` is that information's
only source. Record only what changed this session.

For a new work item, choose the matching workflow type and run:

```bash
agent-checkpoint workflow --type TYPE --id current
```

Fill `.agent-checkpoint/work/current/CURRENT.md` and its planning prompt first.
Keep `PROGRESS.md` as a concise pointer to the package, Current Step/Gate, and
the `PROGRESS.md -> CURRENT.md -> CONTINUE_PROMPT.md` read order.
If the user has not specified a type, ask them to choose one; do not infer it.
Before filling the planning files, ask concise questions for any missing goal,
scope, success criterion, constraint, or affected area. Do not invent details
or advance the tracker until the answers are available.

Pass the entry on standard input to the installed CLI:

```bash
agent-checkpoint write --entry -
```

Add each concrete test/build result with a repeated `--verification TEXT`
option.

Use `--root PATH` when needed. If `agent-checkpoint` is unavailable, reinstall
the CLI and retry:

```bash
npm install -g agent-checkpoint
```

If the CLI is present but the checkpoint operation fails, diagnose it with:

```bash
agent-checkpoint doctor --adapter opencode
```
