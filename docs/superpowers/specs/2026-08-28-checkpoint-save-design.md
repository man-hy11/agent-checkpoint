# checkpoint-save: a session-summary skill/command distinct from the checkpoint router

## Problem

`checkpoint` names two different things that happen to share a name:

- The **skill** `skills/checkpoint/SKILL.md` is a pure router. It runs
  `agent-checkpoint work status --root . --json`, reads `next_skill`, and
  invokes exactly that skill. It never writes anything itself.
- The **command** `/checkpoint` (`commands/checkpoint/*`) composes a session
  summary from two headings (`## 2. Progress`, `## 5. Decisions / Constraints
  / Notes`) and pipes it to `agent-checkpoint write --entry -`.

Asking an agent to "use the checkpoint skill to save progress" invokes the
router, not the summary writer. With no work package yet (the common case
when a user works for a while before ever running `agent-checkpoint
workflow`), the router's first hop is `checkpoint-select-workflow`, which asks
which of the ten workflow types the user wants — not what actually happened.
The user's intent ("write down what I just did") and the router's behavior
("start planning a new unit of work") diverge, and the shared name hides
that divergence until it bites.

Two names for two jobs removes the ambiguity:

- `checkpoint` keeps its current meaning and behavior everywhere unchanged:
  the routing skill and the routing command.
- `checkpoint-save`, new, is the session-summary skill and command: what
  `/checkpoint` does today, plus the orchestration needed to make it work
  sensibly when no work package exists yet.

## Scope

In scope: a new `checkpoint-save` skill, a new `checkpoint-save` command per
host, the orchestration logic for the no-work-package case, deleting the old
`checkpoint` command in favor of it, and the packaging/doc changes that
follow (hosts.toml, build_adapter projection, tests, baseline fixtures,
README additions in both languages).

Out of scope: any change to the `checkpoint` skill, the `checkpoint` command,
or chain-v1.md's routing table. Out of scope: automatic PLAN.md drafting —
when a plan exists, `checkpoint-save` hands off to the existing
`checkpoint-plan` skill rather than writing the plan itself. Out of scope:
fixing `checkpoint-brainstorm` or `initialize_workflow`'s behavior — both
are correct as they stand; `checkpoint-save` follows the same pattern
`checkpoint-brainstorm` already uses (write `BRIEF.md`/`PROJECT_CONTEXT.md`
fresh, since `workflow` doesn't create them).

Also in scope, found while planning and unrelated to the naming problem:
`hosts.toml`'s `npm_hint`, `npm_package`, `doctor_adapter`, and
`doctor_adapter_name` keys are dead — `_project_commands`
(`build_adapter.py:222-238`) copies each host's command file verbatim and
never reads them. They're a residue of the npm-retirement cleanup
(073a94b fixed the command bodies' text but missed these declared-but-unused
keys). Removing them is small and touches the same file this work already
edits.

## Behavior

### Case A — a work package already exists

Unchanged from today's `/checkpoint` command: compose a delta-only entry
(`## 2. Progress`, `## 5. Decisions / Constraints / Notes`) describing only
what changed this session — `CURRENT.md` remains the sole source for
Goal/Plan and Current Focus — and pipe it to
`agent-checkpoint write --entry -`. Accept repeated
`--verification TEXT` for concrete results. If the CLI is unavailable,
recover the same way the other opencode commands now do (symlink the
launcher onto `PATH`; see 073a94b), not via a since-retired npm install.

### Case B — no work package exists (the new orchestration)

This is the case that matters: the user has already done substantive work
without ever running `agent-checkpoint workflow`, and now wants it recorded
before a compaction or a new session.

1. Confirm there is no state block (`work status --json` returns none).
2. **Recommend a workflow type** from the ten (`project`, `feature`,
   `bugfix`, `refactor`, `upgrade`, `migration`, `performance`,
   `integration`, `release`, `spike`), inferred from the session's actual
   work — files touched, the nature of the changes, what was discussed.
   Present the recommendation and reasoning; wait for the user to confirm or
   pick a different type. Never silently apply the guess — this preserves
   `checkpoint-select-workflow`'s existing hard rule ("do not infer or
   default the type silently") in spirit: inference produces a proposal, not
   a decision.
3. Run `agent-checkpoint workflow --type TYPE --id current` to create the
   package.
4. Write `BRIEF.md` and `PROJECT_CONTEXT.md` (Goal / Scope / Success
   Criteria / Constraints / Affected Area) from the session's actual work,
   then set `brief_confirmed: true` in `CURRENT.md`'s state block before
   moving on — the same two actions `checkpoint-brainstorm` already
   performs (SKILL.md:19-24), just with facts drawn from completed work
   instead of asked fresh. Verified empirically that `agent-checkpoint
   workflow` does not create these files itself (a package it materializes
   holds only `CURRENT.md`, `CONTINUE_PROMPT.md`, and the template/prompt
   copies — confirmed by running it and listing the tree), so
   `checkpoint-save` creates them fresh, same as checkpoint-brainstorm does
   for a package it didn't create either. There is no CLI flag for
   `brief_confirmed`; the CLI never lets state be set by fiat, only parsed
   from the file (`work_state.py`), so writing the block is the skill's
   job, as it already is for checkpoint-brainstorm.
5. **Judge whether planning is already effectively done** — the remaining
   work reads as a clear, ordered set of steps rather than an open
   question. Present that judgment and the reasoning; wait for the user to
   confirm or disagree.
   - **Confirmed done**: invoke `checkpoint-plan` to write `PLAN.md`.
     `checkpoint-save` does not draft the plan itself — this keeps "only
     `checkpoint-plan` edits `PLAN.md`" (checkpoint-plan/SKILL.md) true
     without an exception.
   - **Confirmed not done**: do not invoke `checkpoint-plan`. Leave the
     package at that state; the next session's `checkpoint` router call
     reads it as Row 3 (`units is empty` -> `checkpoint-plan`) and lands
     there on its own — no special-casing needed on the read side.
6. Record the session summary via `agent-checkpoint write --entry -`, as in
   Case A.
7. `CONTINUE_PROMPT.md` requires no separate step: step 3's `workflow` call
   already wrote the root and package-level files
   (`work_renderer.py`/`workflows.py`), naming this package. Nothing
   `checkpoint-save`-specific needs to run here — the general rule already
   holds: run `checkpoint-save` (or the plain `/checkpoint-save` command),
   and afterward the root `CONTINUE_PROMPT.md` always points somewhere
   useful, whether or not a package existed beforehand.

### Reading order for the next session

Unchanged from the documented flow (README "How a work item flows", step 4):
root `CONTINUE_PROMPT.md` -> package `CURRENT.md` -> package
`CONTINUE_PROMPT.md`, executing only the Current Target. `checkpoint-save`
does not introduce a second reading order; it only guarantees a work package
(and therefore a valid `CONTINUE_PROMPT.md`) exists by the time it finishes,
even when the session started without one.

## Naming and file layout

| Old | New |
|---|---|
| `skills/checkpoint/SKILL.md` (router) | unchanged |
| `commands/checkpoint/{claude-code.md,opencode.md,gemini-cli.toml}` (summary) | deleted |
| — | `skills/checkpoint-save/SKILL.md` (new) |
| — | `commands/checkpoint-save/{claude-code.md,opencode.md,gemini-cli.toml}` (new) |

No backward-compatible alias for the old `/checkpoint` command — full
migration, per the approved direction. Anyone with the old habit gets a
"command not found"-style miss rather than a silently different behavior
under the same name, which is preferable to reintroducing the exact
ambiguity this change removes.

## Downstream changes

- `hosts.toml`: three `names = ["checkpoint", "resume", "handoff"]` arrays
  (lines 32, 96, 118 — `claude-code`, `opencode`, `gemini-cli`) each need
  `"checkpoint"` replaced with `"checkpoint-save"`. `codex` ships no
  commands at all (`hosts.toml:81`, "Deliberately absent") and needs no
  change.
- `tools/build_adapter.py`: confirmed no code change needed.
  `_project_commands` (build_adapter.py:222-238) reads `commands["names"]`
  directly from the profile and projects `commands/{name}.{extension}` for
  each — the `hosts.toml` edit above is sufficient on its own.
- `tests/`: extend adapter/skill tests to cover the new skill and command
  (existence, projection to every host that ships commands, frontmatter
  validity) and to confirm the old `checkpoint` command name is gone from
  every host output. `tests/fixtures/adapter-baseline/`: regenerate the
  affected per-host files and their checksums in
  `adapter-baseline.sha256`, per the existing "fix the generator, not the
  fixture" rule (`tools/AGENTS.md`) — this is a deliberate source change,
  not generator drift, so regenerating the fixture is correct here (same
  reasoning already applied in 073a94b and 461b9a1).
- `README.md` / `README.ko.md`: extend "The twelve skills" to thirteen,
  adding `checkpoint-save` with an explicit note distinguishing it from
  `checkpoint` (the two-table split — what each is, not just what it does
  — is what a reader needs to avoid the ambiguity that motivated this
  change). Both files must stay in lockstep as usual.

## Risks / open questions carried into implementation

- Step 2 and step 5's recommendations are inference over conversation
  content, which the implementation plan should treat as unverifiable by
  automated tests — cover the mechanism (recommendation presented, wait for
  confirmation, never silently applied) rather than the quality of any
  particular guess.
- `agent-checkpoint workflow` materializes a package meant to be filled
  going forward, not backfilled from completed work — using it this way is
  within its existing contract (it just writes the scaffold; nothing
  prevents filling `CURRENT.md` from hindsight) but is a new *pattern* of
  use worth calling out explicitly in the skill body so a future reader
  doesn't mistake the backfill for the command's primary purpose.
