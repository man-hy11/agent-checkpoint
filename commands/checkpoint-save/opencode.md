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

If no work package exists yet, this session did substantive work without
ever running `agent-checkpoint workflow`. Follow the checkpoint-save
skill's Case B: recommend a workflow type from the session's actual work
and wait for confirmation, then run:

```bash
agent-checkpoint workflow --type TYPE --id current
```

Backfill `.agent-checkpoint/work/current/BRIEF.md` and
`PROJECT_CONTEXT.md` from what already happened (do not invent unanswered
fields), set `brief_confirmed: true`, and — only if planning already
reads as done, confirmed with the user — hand off to checkpoint-plan
rather than drafting `PLAN.md` here.

Pass the entry on standard input to the installed CLI:

```bash
agent-checkpoint write --entry -
```

Add each concrete test/build result with a repeated `--verification TEXT`
option.

Use `--root PATH` when needed. If `agent-checkpoint` is unavailable, put its
launcher on `PATH` and retry:

```bash
ln -s /absolute/path/to/agent-checkpoint/bin/agent-checkpoint /usr/local/bin/agent-checkpoint
```

If the CLI is present but the checkpoint operation fails, diagnose it with:

```bash
agent-checkpoint doctor --adapter opencode
```
