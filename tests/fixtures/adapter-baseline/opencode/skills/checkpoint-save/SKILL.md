---
name: checkpoint-save
description: "Use to write down what happened this session \u2014 a resumable summary via write, or (when no work package exists yet) recommend a workflow type, backfill its brief from the session's actual work, and record progress."
---

# Checkpoint — Save

Record what happened this session so a future session (after compaction
or a fresh start) can pick up without reconstructing a compacted
conversation. This is distinct from the `checkpoint` skill: `checkpoint`
is a router that advances an existing work package's plan; this skill
writes a summary and, when needed, backfills a work package around
completed work rather than starting to plan new work.

## Case A — a work package already exists

Compose a concise entry using exactly these two headings, excluding
credentials and diff content:

```markdown
## 2. Progress
## 5. Decisions / Constraints / Notes
```

`CURRENT.md` already owns Goal/Plan and Current Focus — do not restate
them here. Record only what changed this session.

Pass the entry on standard input:

```bash
agent-checkpoint write --entry -
```

Add each concrete test/build result with a repeated `--verification TEXT`
option. Use `--root PATH` when the project root is not the current
directory. If the command fails, report its diagnostic without claiming
the checkpoint was saved.

If `agent-checkpoint` is unavailable, put its launcher on `PATH` and
retry:

```bash
ln -s /absolute/path/to/agent-checkpoint/bin/agent-checkpoint /usr/local/bin/agent-checkpoint
```

## Case B — no work package exists yet

This is the common case when a user does substantive work without ever
running `agent-checkpoint workflow`, then wants it recorded before a
compaction or a new session. Confirm this case first:

```bash
agent-checkpoint work status --root . --json
```

No state block means no work package — proceed with the steps below.
(Any other result means Case A applies instead.)

### 1. Recommend a workflow type

Look at what the session actually did — files touched, the nature of the
changes, what was discussed — and recommend one of the ten types:

```
project, feature, bugfix, refactor, upgrade,
migration, performance, integration, release, spike
```

Present the recommendation and the reasoning. Wait for the user to
confirm it or name a different type. Never apply the guess silently —
this is a proposal, not a decision, the same standard
`checkpoint-select-workflow` holds for an explicit ask.

### 2. Create the work package

```bash
agent-checkpoint workflow --type TYPE --id current
```

### 3. Backfill the brief

`agent-checkpoint workflow` does not create `BRIEF.md` or
`PROJECT_CONTEXT.md` — write them fresh in the new work package
directory, the same way `checkpoint-brainstorm` does for a package it
didn't create either, except drawing the answers from the session's
actual work instead of asking fresh:

- **Goal:** what outcome did the work achieve?
- **Scope:** what was actually in and out of scope?
- **Success criteria:** how do you know the work is done (or where it
  stands)?
- **Constraints:** time, people, technology, or policy limits that
  applied.
- **Affected area:** files, systems, teams, or surfaces touched.

Do not fabricate anything the session doesn't support — leave a field
open rather than inventing an answer. Once written, set
`brief_confirmed: true` in `CURRENT.md`'s state block.

### 4. Judge whether planning is already effectively done

Look at whether the remaining work reads as a clear, ordered set of
steps rather than an open question. Present that judgment and the
reasoning. Wait for the user to confirm or disagree.

- **Confirmed done**: invoke `checkpoint-plan` to write `PLAN.md`.
  `checkpoint-save` never drafts the plan itself — only `checkpoint-plan`
  edits `PLAN.md`.
- **Confirmed not done**: do not invoke `checkpoint-plan`. Leave the
  package as-is; the next `checkpoint` router call reads the empty unit
  list and routes to `checkpoint-plan` on its own — no extra step needed
  here.

### 5. Record the summary

Same as Case A: compose the two-heading entry and pipe it to
`agent-checkpoint write --entry -`.

### 6. Nothing else to do for CONTINUE_PROMPT.md

Step 2's `workflow` call already wrote the root `CONTINUE_PROMPT.md`
naming this package, and the package's own `CONTINUE_PROMPT.md`. No
separate action is needed — the next session's standard reading order
(root `CONTINUE_PROMPT.md` -> package `CURRENT.md` -> package
`CONTINUE_PROMPT.md`) already resolves correctly.

## Why this skill and not checkpoint?

`checkpoint` reads `work status` and hands off to whichever skill
advances the plan next — with no work package, that means asking which
of the ten types to plan *next*. `checkpoint-save` writes down what
*already happened*, creating a work package around it only when doing so
is what backfilling a summary requires.
