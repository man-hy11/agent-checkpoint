# checkpoint-save Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `checkpoint-save` as a session-summary skill and per-host command, distinct from the existing `checkpoint` router, and remove the old `/checkpoint` command in favor of it.

**Architecture:** `checkpoint-save` is authored once as `skills/checkpoint-save/SKILL.md` (the same file every host's command delegates to, following how `commands/checkpoint/*` already point at CLI invocations rather than duplicating logic per host) and projected as a command body per host under `commands/checkpoint-save/`. `hosts.toml` gains the new command name and loses the old one in three `names` arrays; `tools/build_adapter.py` needs no code change, since `_project_commands` already reads `commands["names"]` and copies each host's file by name. The frozen baseline fixture and its checksums are regenerated for every file whose *projected content* changes as a result — this is a deliberate source edit, not generator drift, so regenerating is the documented-correct move (`tools/AGENTS.md`), same reasoning already applied in 073a94b and 461b9a1.

**Tech Stack:** Markdown skill/command bodies (Claude Code, OpenCode), TOML command body (Gemini CLI), Python 3.11 stdlib (`unittest`, `tomllib`), TOML config (`hosts.toml`).

**Spec:** `docs/superpowers/specs/2026-08-28-checkpoint-save-design.md`

## Global Constraints

- `checkpoint` (skill and command) stays byte-for-byte unchanged. Nothing in this plan touches `skills/checkpoint/SKILL.md`, `commands/checkpoint/*` content before deletion, or `skills/_checkpoint-shared/chain-v1.md`.
- No backward-compatible alias for the deleted `/checkpoint` command — full migration, per the spec's approved direction.
- `checkpoint-save` never writes `PLAN.md` itself; when planning is already done it invokes `checkpoint-plan`, never duplicating "only checkpoint-plan edits PLAN.md" (an existing rule in `skills/checkpoint-plan/SKILL.md`).
- Every workflow-type or plan-completeness judgment is presented to the user for confirmation before acting — never applied silently. This mirrors `checkpoint-select-workflow`'s existing rule ("do not infer or default the type silently").
- codex ships no commands at all (`hosts.toml:81`, "Deliberately absent") — it never needs a `checkpoint-save` command entry.
- Recovery guidance for a missing CLI must use the symlink instruction (`ln -s .../bin/agent-checkpoint /usr/local/bin/agent-checkpoint`), matching what 073a94b already fixed elsewhere — never reintroduce an `npm install -g` fallback.

---

## Task 1: Delete the dead npm-projection keys from hosts.toml

Unrelated to the naming work but touches the same file and is small enough to land first, out of the way.

**Files:**
- Modify: `hosts.toml:33-36` (claude-code), `hosts.toml:97-101` (opencode), `hosts.toml:119-120` (gemini-cli)
- Test: `tests/test_hosts_toml.py` (create if no such file exists — check first)

**Interfaces:**
- Consumes: nothing new.
- Produces: nothing new — this task only removes dead declarations. Confirms (for later tasks) that `_project_commands` in `tools/build_adapter.py` is unaffected by anything in the `[hosts.*.commands]` tables besides `format` and `names`.

- [ ] **Step 1: Confirm no code reads the four dead keys**

Run: `grep -rn "npm_hint\|npm_package\|doctor_adapter" tools/ agent_checkpoint/`
Expected: no output (already verified during planning; re-verify here before editing so the deletion is evidence-based, not assumed).

- [ ] **Step 2: Remove the dead keys from all three hosts**

In `hosts.toml`, within `[hosts.claude-code.commands]` remove these two lines (keep `format` and `names`):
```toml
npm_hint = false
doctor_adapter = false
```
Also remove the comment line directly above them:
```toml
# claude-code commands carry no recovery guidance: no npm reinstall hint and
# no `doctor --adapter` block. Both are opencode-only.
```

Within `[hosts.opencode.commands]` remove:
```toml
npm_hint = true
npm_package = "agent-checkpoint"
doctor_adapter = true
doctor_adapter_name = "opencode"
```
and the comment above them:
```toml
# opencode is the only host whose commands carry recovery guidance.
```

Within `[hosts.gemini-cli.commands]` remove:
```toml
npm_hint = false
doctor_adapter = false
```

- [ ] **Step 3: Verify hosts.toml still parses and every host still builds**

Run:
```bash
python3 -c "import tomllib; tomllib.load(open('hosts.toml', 'rb'))" && echo "PARSE OK"
for host in claude-code codex gemini-cli opencode; do
  python3 tools/build_adapter.py "$host" --output "/tmp/checkpoint-save-plan-t1-$host" && echo "$host: OK"
done
rm -rf /tmp/checkpoint-save-plan-t1-*
```
Expected: `PARSE OK`, then `OK` for all four hosts.

- [ ] **Step 4: Run the full suite to confirm nothing depended on the removed keys**

Run: `PYTHONPATH=. python3 -m unittest discover -s tests -v 2>&1 | tail -15`
Expected: same pass count as before this task (437 passed, 1 skipped, 159 subtests — confirm this is still the baseline by running the suite once before Step 2 if in doubt).

- [ ] **Step 5: Commit**

```bash
git add hosts.toml
git commit -m "chore: remove dead npm_hint/doctor_adapter keys from hosts.toml

_project_commands (build_adapter.py:222-238) copies each host's command
file by name and never reads these fields — they're leftover
declarations from before command bodies were de-duplicated per host,
made fully dead by 073a94b's npm retirement (which fixed the command
text but missed these keys).

Verified: grep confirms no code reads them. All four hosts still build.
Full suite unchanged."
```

---

## Task 2: Write the checkpoint-save skill body

**Files:**
- Create: `skills/checkpoint-save/SKILL.md`
- Test: `tests/test_skills.py` if it exists (check for an existing skill-count or skill-list assertion to extend); otherwise rely on `tools/validate_skills.py` in Step 3 below.

**Interfaces:**
- Consumes: `agent-checkpoint work status --root . --json` (existing CLI, unchanged), `agent-checkpoint workflow --type TYPE --id current` (existing CLI, unchanged), `agent-checkpoint write --entry -` with optional repeated `--verification TEXT` (existing CLI, unchanged).
- Produces: the `checkpoint-save` skill name, invokable by name or by description-based auto-trigger, same mechanism as every other skill in `skills/`.

- [ ] **Step 1: Check the skill-count baseline before adding a new skill**

Run: `python3 tools/validate_skills.py skills`
Expected: `OK — 12 skills valid, _checkpoint-shared present` (confirms the starting count before this task changes it).

- [ ] **Step 2: Write skills/checkpoint-save/SKILL.md**

```markdown
---
name: checkpoint-save
description: Use to write down what happened this session — a resumable summary via write, or (when no work package exists yet) recommend a workflow type, backfill its brief from the session's actual work, and record progress.
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
```

- [ ] **Step 3: Validate the new skill**

Run: `python3 tools/validate_skills.py skills`
Expected: `OK — 13 skills valid, _checkpoint-shared present`

- [ ] **Step 4: Commit**

```bash
git add skills/checkpoint-save/SKILL.md
git commit -m "feat: add checkpoint-save skill, distinct from the checkpoint router

checkpoint (skill and command) is a router: with no work package, its
first hop asks which of ten workflow types to plan next, not what
already happened. checkpoint-save is the session-summary counterpart —
same delta-entry write when a package exists, and when one doesn't, an
orchestration that recommends-and-confirms a workflow type, creates the
package, backfills its BRIEF.md/PROJECT_CONTEXT.md from the session's
actual work (agent-checkpoint workflow does not create these itself,
confirmed empirically), judges-and-confirms whether planning is already
done (handing off to checkpoint-plan rather than drafting PLAN.md
itself), then records the summary.

Verified: tools/validate_skills.py reports 13 skills valid, up from 12."
```

---

## Task 3: Register checkpoint-save in every SKILL_NAMES list and agents/openai.yaml

`tools/validate_skills.py` (used in Task 2) checks the `skills/` directory
against itself — it does not check whether the *bundle-installer* and
*test* copies of the skill roster know about the new skill. Three more
places declare the twelve skill names as their own source of truth and
must be updated by hand, or downstream tests fail and the OpenAI-agents
function catalog silently omits the new skill:

- `agent_checkpoint/skill_install.py` — the canonical `SKILL_NAMES` tuple.
  `tools/validate_adapters.py` extracts this exact tuple from a *built
  bundle* via regex (`_SKILL_NAMES_RE`,
  `tools/validate_adapters.py:42-43`) to decide which skills a bundle
  must ship — so this is not just an installer's internal list, it is
  the manifest validator's source of truth too.
- `tests/test_adapters.py:757` — a second, independently-typed
  `SKILL_NAMES` tuple used by four tests in `TwelveSkillCoverageTests`
  (`tests/test_adapters.py:773-889`) that assert bundle skill coverage
  and check `agents/openai.yaml`'s function catalog against it.
- `agents/openai.yaml` — one `functions` entry per skill, name
  underscored (`checkpoint-save` -> `checkpoint_save`), description
  copied verbatim from the skill's frontmatter `description:` field.

`tests/test_cli.py` and `tests/test_skill_install.py` both `import
SKILL_NAMES from agent_checkpoint.skill_install` rather than declaring
their own copy, so updating that one file's tuple is sufficient for both
— confirmed by reading their imports; no edit needed in either file.

**Files:**
- Modify: `agent_checkpoint/skill_install.py:18-30` (the `SKILL_NAMES` tuple)
- Modify: `tests/test_adapters.py:757-768` (the second `SKILL_NAMES` tuple)
- Modify: `agents/openai.yaml` (add one `functions` entry)

**Interfaces:**
- Consumes: the skill's frontmatter `description:` field, written verbatim
  in Task 2 Step 2 — copy it exactly into `agents/openai.yaml` so the two
  never drift (`SkillContentParityTests`, further down the same test
  file, exists precisely to catch that kind of drift for the existing
  twelve).
- Produces: `checkpoint-save` becomes a member of `SKILL_NAMES` everywhere
  it's declared, and `agents/openai.yaml` gains the matching
  `checkpoint_save` function entry.

- [ ] **Step 1: Confirm the coverage tests fail first, proving they're load-bearing**

Run: `PYTHONPATH=. python3 -m unittest tests.test_adapters.TwelveSkillCoverageTests -v 2>&1 | tail -30`
Expected: at least `test_codex_bundle_exposes_all_twelve_skills`,
`test_opencode_bundle_exposes_all_twelve_skills`,
`test_claude_bundle_skill_suite_directory_contains_all_twelve` FAIL —
each of these iterates `SKILL_NAMES` and asserts the file exists in the
built bundle; they currently pass only because `SKILL_NAMES` doesn't yet
include `checkpoint-save`, so they're testing eleven-of-twelve, not
coverage of the new skill. This step establishes that baseline before
editing so the later green run is evidence, not assumption.

- [ ] **Step 2: Add checkpoint-save to agent_checkpoint/skill_install.py's SKILL_NAMES**

In `agent_checkpoint/skill_install.py`, insert `"checkpoint-save",`
into the `SKILL_NAMES` tuple, alphabetically ordered following the
existing convention (immediately after `"checkpoint",` since
`checkpoint-save` sorts right after `checkpoint` and before
`checkpoint-brainstorm`):

```python
SKILL_NAMES: tuple[str, ...] = (
    "checkpoint",
    "checkpoint-save",
    "checkpoint-brainstorm",
    "checkpoint-claim",
    "checkpoint-diagnose",
    "checkpoint-evidence",
    "checkpoint-execute",
    "checkpoint-handoff",
    "checkpoint-inspect",
    "checkpoint-plan",
    "checkpoint-recover",
    "checkpoint-select-workflow",
    "checkpoint-verify-gate",
)
```

- [ ] **Step 3: Apply the identical addition to tests/test_adapters.py's SKILL_NAMES**

Same insertion, same position, in the second tuple at
`tests/test_adapters.py:757`:

```python
SKILL_NAMES = (
    "checkpoint",
    "checkpoint-save",
    "checkpoint-brainstorm",
    "checkpoint-claim",
    "checkpoint-diagnose",
    "checkpoint-evidence",
    "checkpoint-execute",
    "checkpoint-handoff",
    "checkpoint-inspect",
    "checkpoint-plan",
    "checkpoint-recover",
    "checkpoint-select-workflow",
    "checkpoint-verify-gate",
)
```

- [ ] **Step 4: Add the matching entry to agents/openai.yaml**

In `agents/openai.yaml`, insert a new entry immediately after the
`checkpoint` entry (matching the `SKILL_NAMES` position from Steps 2-3)
and before `checkpoint_brainstorm`. Use the exact `description:` string
from `skills/checkpoint-save/SKILL.md`'s frontmatter (written in Task 2
Step 2) — copy it verbatim, do not paraphrase:

```yaml
- name: checkpoint
  description: "Routes to the correct phase skill by running work status — determines which of the twelve checkpoint skills acts next and dispatches accordingly."
- name: checkpoint_save
  description: "Use to write down what happened this session — a resumable summary via write, or (when no work package exists yet) recommend a workflow type, backfill its brief from the session's actual work, and record progress."
- name: checkpoint_brainstorm
  description: "Use when a work package exists but brief_confirmed is false — gathers the goal, scope, success criteria, constraints, and affected area before any planning step."
```

(Only the `checkpoint` and `checkpoint_brainstorm` lines above are shown
for placement context — they already exist; add only the
`checkpoint_save` entry between them.)

- [ ] **Step 5: Run the coverage tests again, expect them to pass**

Run: `PYTHONPATH=. python3 -m unittest tests.test_adapters.TwelveSkillCoverageTests -v 2>&1 | tail -30`
Expected: all pass, including `test_openai_agents_yaml_covers_all_twelve_skills`
(which will now be covering thirteen, despite its name — renaming that
test method is out of scope for this plan; it asserts by content, not by
its own name).

- [ ] **Step 6: Run the full suite**

Run: `PYTHONPATH=. python3 -m unittest discover -s tests -v 2>&1 | tail -15`
Expected: all green, 1 pre-existing skip. `tests/test_cli.py` and
`tests/test_skill_install.py` should pass unchanged, confirming the
import-based sharing assumption from this task's intro held.

- [ ] **Step 7: Commit**

```bash
git add agent_checkpoint/skill_install.py tests/test_adapters.py agents/openai.yaml
git commit -m "feat: register checkpoint-save in every skill-roster source

Three separate places declare the twelve skill names as their own
source of truth, none of them agent_checkpoint's skills/ directory
tools/validate_skills.py already checked in the prior commit:
agent_checkpoint/skill_install.py's SKILL_NAMES (the tuple
tools/validate_adapters.py extracts from a built bundle via regex to
decide what a bundle must ship), tests/test_adapters.py's independent
SKILL_NAMES copy (used by TwelveSkillCoverageTests), and
agents/openai.yaml's function catalog (checked against that same tuple
by test_openai_agents_yaml_covers_all_twelve_skills). All three now
list checkpoint-save.

tests/test_cli.py and tests/test_skill_install.py both import
SKILL_NAMES from agent_checkpoint.skill_install rather than declaring
their own copy, so no edit was needed in either — verified by reading
their imports before concluding this.

Verified: TwelveSkillCoverageTests failed first (proving it was
testing eleven-of-twelve, not full coverage), passes after this
change. Full suite green."
```

---

## Task 4: Delete the old checkpoint command, add checkpoint-save commands, wire hosts.toml

**Files:**
- Delete: `commands/checkpoint/claude-code.md`, `commands/checkpoint/opencode.md`, `commands/checkpoint/gemini-cli.toml`
- Create: `commands/checkpoint-save/claude-code.md`, `commands/checkpoint-save/opencode.md`, `commands/checkpoint-save/gemini-cli.toml`
- Modify: `hosts.toml:32` (claude-code `names`), `hosts.toml:96` (opencode `names`), `hosts.toml:118` (gemini-cli `names`)

**Interfaces:**
- Consumes: `_project_commands` in `tools/build_adapter.py:222-238`, unchanged — reads `commands["names"]` from the profile and copies `commands/{name}.{extension}` verbatim per host.
- Produces: a `checkpoint-save.{md,toml}` file in every projected bundle that ships commands (claude-code, opencode, gemini-cli); no `checkpoint.{md,toml}` anywhere; codex bundles remain command-free.

The three new command bodies restate Case A of the skill (the delta-entry
write) in each host's existing command style — commands are short,
host-specific prose pointing at the CLI, not a copy of the full skill.
Content is adapted from the deleted `commands/checkpoint/*` files with the
Case-B orchestration folded in as a short pointer to the skill (commands
stay thin; the skill carries the orchestration detail), and the recovery
hint already fixed to the symlink form in 073a94b.

- [ ] **Step 1: Delete the old checkpoint command directory**

```bash
git rm commands/checkpoint/claude-code.md commands/checkpoint/opencode.md commands/checkpoint/gemini-cli.toml
```

- [ ] **Step 2: Create commands/checkpoint-save/claude-code.md**

```markdown
---
description: Save a concise, resumable checkpoint for the current project.
---

Compose a checkpoint entry from the current work using these exact headings:

- `## 2. Progress`
- `## 5. Decisions / Constraints / Notes`

When a work package's `CURRENT.md` exists, do not restate its Goal/Plan or
Current Focus in the checkpoint entry — `CURRENT.md` is that information's
only source. Record only what changed this session.

If no work package exists yet, this session did substantive work without
ever running `agent-checkpoint workflow`. Follow the checkpoint-save
skill's Case B: recommend a workflow type from the session's actual work
and wait for confirmation, run
`"${CLAUDE_PLUGIN_ROOT}/bin/agent-checkpoint" workflow --type TYPE --id
current`, backfill `.agent-checkpoint/work/current/BRIEF.md` and
`PROJECT_CONTEXT.md` from what already happened (do not invent unanswered
fields), set `brief_confirmed: true`, and — only if planning already
reads as done, confirmed with the user — hand off to checkpoint-plan
rather than drafting `PLAN.md` here.

Keep it brief, exclude credentials and diff content, and pass the entry on standard
input to `"${CLAUDE_PLUGIN_ROOT}/bin/agent-checkpoint" write --entry -`. Add each
concrete test/build result with a repeated `--verification TEXT` option. Confirm
the result briefly. If the command fails, report its diagnostic without claiming
that the checkpoint was saved.
```

- [ ] **Step 3: Create commands/checkpoint-save/opencode.md**

```markdown
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
```

- [ ] **Step 4: Create commands/checkpoint-save/gemini-cli.toml**

```toml
description = "Save a concise, resumable checkpoint for the current project."
prompt = """
Create a concise checkpoint entry from the current work using these exact headings:

## 2. Progress
## 5. Decisions / Constraints / Notes

When a work package's `CURRENT.md` exists, do not restate its Goal/Plan or
Current Focus in the checkpoint entry — `CURRENT.md` is that information's
only source. Record only what changed this session.

If no work package exists yet, this session did substantive work without
ever running `agent-checkpoint workflow`. Recommend a workflow type from
the session's actual work and wait for confirmation, then run:

agent-checkpoint workflow --type TYPE --id current

Backfill `.agent-checkpoint/work/current/BRIEF.md` and
`PROJECT_CONTEXT.md` from what already happened (do not invent unanswered
fields), set `brief_confirmed: true`, and only draft a plan by handing
off to the checkpoint-plan skill if planning already reads as done,
confirmed with the user.

Exclude credentials and diff content. Pass the completed entry on standard input to:

agent-checkpoint write --entry -

Add each concrete test/build result with a repeated `--verification TEXT`
option. Use `--root PATH` when the project root is not the current directory.
Report the result briefly, and do not claim the checkpoint was saved if the
command fails.
"""
```

- [ ] **Step 5: Update hosts.toml's three commands.names arrays**

In `hosts.toml`, change each of these three lines from:
```toml
names = ["checkpoint", "resume", "handoff"]
```
to:
```toml
names = ["checkpoint-save", "resume", "handoff"]
```
This applies at line 32 (`[hosts.claude-code.commands]`), line 96
(`[hosts.opencode.commands]`), and line 118 (`[hosts.gemini-cli.commands]`)
— line numbers as of before Task 1's edits; re-locate by the `names =`
pattern if Task 1 shifted them.

- [ ] **Step 6: Build every host and confirm checkpoint-save projects, checkpoint does not**

```bash
for host in claude-code codex gemini-cli opencode; do
  python3 tools/build_adapter.py "$host" --output "/tmp/checkpoint-save-plan-t3-$host" || echo "$host: BUILD FAILED"
done
echo "--- claude-code commands ---"
ls /tmp/checkpoint-save-plan-t3-claude-code/commands/
echo "--- opencode commands ---"
ls /tmp/checkpoint-save-plan-t3-opencode/commands/
echo "--- gemini-cli commands ---"
ls /tmp/checkpoint-save-plan-t3-gemini-cli/commands/
echo "--- codex (must have no commands/ dir at all) ---"
ls /tmp/checkpoint-save-plan-t3-codex/ | grep -x commands || echo "no commands/ dir, as expected"
rm -rf /tmp/checkpoint-save-plan-t3-*
```
Expected: `checkpoint-save.md` (claude-code, opencode) and
`checkpoint-save.toml` (gemini-cli) present; no `checkpoint.md` or
`checkpoint.toml` anywhere; codex has no `commands/` directory.

- [ ] **Step 7: Commit**

```bash
git add commands/checkpoint commands/checkpoint-save hosts.toml
git commit -m "feat: replace the checkpoint command with checkpoint-save

Full migration, no alias: the old /checkpoint command shared a name
with the checkpoint router skill while doing an unrelated job (session
summary vs. plan routing). /checkpoint-save is the unambiguous name for
the summary job; the new bodies fold in Case B (recommend a workflow
type, backfill BRIEF.md/PROJECT_CONTEXT.md, hand off to checkpoint-plan
only if planning already reads as done) as a pointer to the
checkpoint-save skill rather than duplicating its full detail in three
host-specific files.

hosts.toml: swapped \"checkpoint\" for \"checkpoint-save\" in all three
commands.names arrays that carry it (claude-code, opencode,
gemini-cli); codex ships no commands and needed no change.
_project_commands (build_adapter.py:222-238) required no code change —
it already copies by name from these arrays.

Verified: all four hosts build. checkpoint-save.{md,toml} present in
every host that ships commands; checkpoint.{md,toml} present nowhere;
codex still has no commands/ directory at all."
```

---

## Task 5: Update tests/test_adapters.py for the rename

The existing opencode CLI-fallback test and the claude-code manifest test
both reference `commands/checkpoint.md` by name. Update them to
`checkpoint-save.md` and extend coverage so a regression that reintroduces
`checkpoint.md` (or drops `checkpoint-save.md`) fails loudly.

**Files:**
- Modify: `tests/test_adapters.py:100-115` (claude-code bundle test), `tests/test_adapters.py:353-363` (opencode CLI-fallback test)
- Test: this task modifies test files directly; verification is running them.

**Interfaces:**
- Consumes: `build_bundle(adapter, directory)` (existing helper, `tests/test_adapters.py:116` area) — unchanged signature.
- Produces: nothing new — no new public interface, only corrected assertions.

- [ ] **Step 1: Read the current claude-code test to find every commands/checkpoint.md reference**

Run: `grep -n "commands.*checkpoint\|checkpoint\.md\|checkpoint\.toml" tests/test_adapters.py`

Expected output includes at least these two spots:
```
command = (bundle / "commands" / "checkpoint.md").read_text(
    encoding="utf-8"
)
```
in `ClaudeAdapterTests.test_claude_bundle_exposes_manifest_command_and_native_hook_paths`, and the same pattern in
`CodexOpenCodeAdapterTests.test_opencode_command_has_cli_install_fallback`
(confirmed by reading the file directly — the opencode fallback test
lives in a class named `CodexOpenCodeAdapterTests`, not
`OpencodeAdapterTests`; that class also holds
`test_codex_bundle_exposes_checkpoint_skill`, unrelated to this task and
untouched).

- [ ] **Step 2: Update both references from checkpoint.md to checkpoint-save.md**

In `test_claude_bundle_exposes_manifest_command_and_native_hook_paths`:
```python
command = (bundle / "commands" / "checkpoint-save.md").read_text(
    encoding="utf-8"
)
```

In `test_opencode_command_has_cli_install_fallback`:
```python
command = (bundle / "commands" / "checkpoint-save.md").read_text(
    encoding="utf-8"
)
```
(Keep the rest of each test body — including the existing
`self.assertIn("agent-checkpoint write --entry -", command)` and
`self.assertIn("bin/agent-checkpoint /usr/local/bin/agent-checkpoint", command)`
assertions in the opencode test — unchanged; only the filename read
changes.)

- [ ] **Step 3: Write a new regression test asserting the old command name is gone from every host**

Confirmed by reading the file (`grep -n "^class\|^def test_"
tests/test_adapters.py`) that every test in `test_adapters.py` is a
class method — there are no bare top-level `def test_...` functions.
Add a new class, `CrossHostCommandTests`, directly above
`ClaudeAdapterTests` (currently at line 99) so it reads as a
cross-cutting check rather than belonging to one host's test class:

```python
class CrossHostCommandTests(unittest.TestCase):
    def test_checkpoint_command_is_fully_retired(self):
        """Catches the old /checkpoint command name coming back under any
        host, or checkpoint-save failing to replace it somewhere."""
        with tempfile.TemporaryDirectory() as directory:
            for host, extension in (
                ("claude-code", "md"),
                ("opencode", "md"),
                ("gemini-cli", "toml"),
            ):
                bundle = build_bundle(host, Path(directory) / host)
                command_dir = bundle / "commands"
                self.assertFalse(
                    (command_dir / f"checkpoint.{extension}").exists(),
                    f"{host}: old checkpoint command must not be projected",
                )
                self.assertTrue(
                    (command_dir / f"checkpoint-save.{extension}").is_file(),
                    f"{host}: checkpoint-save command must be projected",
                )
            codex_bundle = build_bundle("codex", Path(directory) / "codex")
            self.assertFalse(
                (codex_bundle / "commands").exists(),
                "codex must still ship no commands directory at all",
            )
```

- [ ] **Step 4: Run the modified and new tests**

Run: `PYTHONPATH=. python3 -m unittest tests.test_adapters -v 2>&1 | tail -30`
Expected: all tests in the file pass, including the two modified ones
and the new `test_checkpoint_command_is_fully_retired`.

- [ ] **Step 5: Commit**

```bash
git add tests/test_adapters.py
git commit -m "test: cover checkpoint -> checkpoint-save rename in adapter bundles

Two existing tests referenced commands/checkpoint.md by name and would
have kept passing against a stale bundle; updated both to
checkpoint-save.md. Added a cross-host regression test asserting the
old command name is absent from every host that ships commands and
checkpoint-save is present, plus that codex still ships no commands
directory — catches either name reappearing or the other going
missing, for any single host, in one assertion pass.

Verified: PYTHONPATH=. python3 -m unittest tests.test_adapters -v
passes in full."
```

---

## Task 6: Regenerate the frozen baseline fixture and its checksums

The three hosts whose command names changed (claude-code, opencode,
gemini-cli) need their baseline copies regenerated, per the documented
rule: this is a deliberate source change, not generator drift, so
regenerating the fixture is correct (`tools/AGENTS.md`; same reasoning as
073a94b and 461b9a1).

**Files:**
- Delete: `tests/fixtures/adapter-baseline/claude-code/commands/checkpoint.md`, `tests/fixtures/adapter-baseline/opencode/commands/checkpoint.md`, `tests/fixtures/adapter-baseline/gemini-cli/commands/checkpoint.toml`
- Create: `tests/fixtures/adapter-baseline/claude-code/commands/checkpoint-save.md`, `tests/fixtures/adapter-baseline/opencode/commands/checkpoint-save.md`, `tests/fixtures/adapter-baseline/gemini-cli/commands/checkpoint-save.toml`
- Modify: `tests/fixtures/adapter-baseline.sha256`

**Interfaces:**
- Consumes: `tools/build_adapter.py` (Task 4's output), unchanged interface.
- Produces: nothing new — fixture content only.

- [ ] **Step 1: Confirm the baseline test fails first, proving it's load-bearing**

Run: `PYTHONPATH=. python3 -m unittest tests.test_build_adapter.ProjectionBaselineTests.test_projection_matches_frozen_baseline -v 2>&1 | tail -20`
Expected: FAIL, naming `checkpoint.md`/`checkpoint.toml` missing from the
freshly built output (or the reverse — `checkpoint-save` absent from the
old baseline) for at least claude-code, opencode, and gemini-cli.

- [ ] **Step 2: Remove the stale baseline command files and copy the fresh ones**

```bash
git rm tests/fixtures/adapter-baseline/claude-code/commands/checkpoint.md
git rm tests/fixtures/adapter-baseline/opencode/commands/checkpoint.md
git rm tests/fixtures/adapter-baseline/gemini-cli/commands/checkpoint.toml

tmp=$(mktemp -d)
for host in claude-code opencode gemini-cli; do
  python3 tools/build_adapter.py "$host" --output "$tmp/$host" >/dev/null 2>&1
done
cp "$tmp/claude-code/commands/checkpoint-save.md" tests/fixtures/adapter-baseline/claude-code/commands/checkpoint-save.md
cp "$tmp/opencode/commands/checkpoint-save.md" tests/fixtures/adapter-baseline/opencode/commands/checkpoint-save.md
cp "$tmp/gemini-cli/commands/checkpoint-save.toml" tests/fixtures/adapter-baseline/gemini-cli/commands/checkpoint-save.toml
rm -rf "$tmp"
```

- [ ] **Step 3: Update adapter-baseline.sha256 — remove the three stale lines, add three new ones**

```bash
cd tests/fixtures/adapter-baseline
for old in "claude-code/commands/checkpoint.md" "opencode/commands/checkpoint.md" "gemini-cli/commands/checkpoint.toml"; do
  python3 - "$old" <<'EOF'
import sys, pathlib
target = sys.argv[1]
p = pathlib.Path("../adapter-baseline.sha256")
lines = [ln for ln in p.read_text().splitlines() if not ln.endswith("  " + target)]
p.write_text("\n".join(lines) + "\n")
EOF
done
for new in "claude-code/commands/checkpoint-save.md" "opencode/commands/checkpoint-save.md" "gemini-cli/commands/checkpoint-save.toml"; do
  sum=$(sha256sum "$new" | cut -d' ' -f1)
  echo "$sum  $new" >> ../adapter-baseline.sha256
done
sort -k2 ../adapter-baseline.sha256 -o ../adapter-baseline.sha256
cd ../../..
```

- [ ] **Step 4: Verify checksums are internally consistent**

Run:
```bash
cd tests/fixtures/adapter-baseline
sha256sum -c ../adapter-baseline.sha256 2>&1 | grep -v ": OK$"
cd ../../..
```
Expected: no output (every line reports OK).

- [ ] **Step 5: Run the baseline test again, expect it to pass**

Run: `PYTHONPATH=. python3 -m unittest tests.test_build_adapter.ProjectionBaselineTests.test_projection_matches_frozen_baseline -v 2>&1 | tail -10`
Expected: PASS.

- [ ] **Step 6: Run the full suite**

Run: `PYTHONPATH=. python3 -m unittest discover -s tests -v 2>&1 | tail -15`
Expected: all pass, 1 skipped (the pre-existing chain-v1.md skip). Count should be Task 1's baseline plus this plan's new tests (Task 5 added one new test method — confirm the exact delta by comparing to the count recorded in Task 1 Step 4).

- [ ] **Step 7: Commit**

```bash
git add tests/fixtures/adapter-baseline tests/fixtures/adapter-baseline.sha256
git commit -m "test: regenerate frozen baseline for the checkpoint-save rename

claude-code, opencode, and gemini-cli each had a stale
commands/checkpoint.{md,toml} baseline file; replaced with
checkpoint-save.{md,toml} generated fresh from the corrected sources,
per tools/AGENTS.md's rule that a deliberate source change gets a
regenerated fixture, not a patched generator (same reasoning as
073a94b, 461b9a1).

Verified: test_projection_matches_frozen_baseline failed first against
the stale fixture (confirming it's load-bearing), passes after
regeneration. sha256 -c reports clean across every fixture file. Full
suite green."
```

---

## Task 7: Update README.md and README.ko.md

Add `checkpoint-save` to the skill catalog with an explicit distinction
from `checkpoint` — the two-table split (what each *is*, not just what it
*does*) is what a reader needs to avoid the exact ambiguity that motivated
this whole change.

**Files:**
- Modify: `README.md` (the "The twelve skills" section and its heading)
- Modify: `README.ko.md` (the "열두 개의 스킬" section and its heading, kept in lockstep)

**Interfaces:**
- Consumes: nothing — documentation only.
- Produces: nothing — documentation only.

- [ ] **Step 1: Update README.md's section heading and intro**

Change:
```markdown
## The twelve skills

`checkpoint` is a router: it runs `work status`, reads `next_skill`, and
invokes exactly that skill — it never edits state itself. The other eleven
each own one phase of a work package's lifecycle, selected by the unit's
current condition rather than by the agent's judgment. See
`skills/_checkpoint-shared/chain-v1.md` for the full ordered routing table.
```
to:
```markdown
## The thirteen skills

`checkpoint` and `checkpoint-save` share a name prefix but do different
jobs, and confusing them is easy — `checkpoint` is a pure router: it runs
`work status`, reads `next_skill`, and invokes exactly that skill, never
writing a summary itself. `checkpoint-save` is the session-summary
counterpart: it writes down what happened this session, creating a work
package around already-completed work when none exists yet, rather than
starting to plan new work. The other eleven each own one phase of a work
package's lifecycle, selected by the unit's current condition rather than
by the agent's judgment. See `skills/_checkpoint-shared/chain-v1.md` for
the full ordered routing table.
```

- [ ] **Step 2: Add a checkpoint-save row to README.md's skill table**

In the table (immediately after the `checkpoint` row, before
`checkpoint-select-workflow`), insert:
```markdown
| `checkpoint-save` | Any time you want to record what happened — mid-session, or before compaction/a new session | Writes a delta summary via `write` when a work package exists; when none exists, recommends a workflow type (confirmed by the user), creates the package, backfills its brief from the session's actual work, and — only if planning already reads as done, confirmed by the user — hands off to `checkpoint-plan` |
```

- [ ] **Step 3: Apply the equivalent changes to README.ko.md**

Change the Korean section heading and intro (currently "## 열두 개의
스킬") to "## 열세 개의 스킬" with translated prose covering the same
distinction as Step 1's English version — `checkpoint`과
`checkpoint-save`가 이름은 비슷하지만 하는 일이 다르다는 점, `checkpoint`는
순수 라우터이고 `checkpoint-save`는 세션 요약을 기록하며 필요하면 이미
끝난 작업을 근거로 work package를 소급 생성한다는 점을 명시. Add the
matching table row for `checkpoint-save` in Korean, in the same table
position (right after `checkpoint`, before `checkpoint-select-workflow`).

Keep every skill name, command, and file path untranslated (matching the
existing pattern verified in the earlier README.ko.md commit — only prose
and comments differ from README.md).

- [ ] **Step 4: Diff-check both files stay in lockstep**

Run:
```bash
diff <(grep -oP '`checkpoint[a-z-]*`' README.md | sort -u) <(grep -oP '`checkpoint[a-z-]*`' README.ko.md | sort -u)
```
Expected: no output (identical sorted skill-name sets in both files,
now 13 each).

- [ ] **Step 5: Commit**

```bash
git add README.md README.ko.md
git commit -m "docs: document checkpoint-save and the checkpoint/checkpoint-save split

Extends both READMEs' skill catalog from twelve to thirteen entries and
makes the checkpoint vs. checkpoint-save distinction explicit in the
section intro, not just implicit in two separate table rows — a reader
skimming only the table could still conflate them by name alone.

Verified: sorted checkpoint* skill-name sets extracted from each file's
table match exactly (13 entries each)."
```

---

## Task 8: Update the design spec's status and cross-link the plan

Small closing task: mark the spec as implemented and point back at this
plan, so a future reader of the spec knows it shipped and where the
implementation record lives.

**Files:**
- Modify: `docs/superpowers/specs/2026-08-28-checkpoint-save-design.md`

**Interfaces:** none — documentation only.

- [ ] **Step 1: Add an implementation-status line near the top of the spec**

Immediately after the spec's title (`# checkpoint-save: a session-summary
skill/command distinct from the checkpoint router`), insert:
```markdown
**Status:** Implemented. See `docs/superpowers/plans/2026-08-28-checkpoint-save.md`.
```

- [ ] **Step 2: Commit**

```bash
git add docs/superpowers/specs/2026-08-28-checkpoint-save-design.md
git commit -m "docs: mark checkpoint-save spec as implemented"
```

---

## Final Verification

- [ ] Run the complete suite one more time end to end: `PYTHONPATH=. python3 -m unittest discover -s tests -v 2>&1 | tail -20`. Expected: all green, 1 pre-existing skip.
- [ ] Run `python3 tools/validate_skills.py skills`. Expected: `OK — 13 skills valid, _checkpoint-shared present`.
- [ ] Build all four hosts once more and manually inspect: `checkpoint-save` present (as `.md` or `.toml`) in claude-code, opencode, gemini-cli; absent from codex (no `commands/` dir at all); `checkpoint` command absent everywhere; `checkpoint` *skill* still present and unchanged in every host that ships skills (claude-code, codex, opencode).
- [ ] Confirm `git log --oneline` shows one commit per task (8 commits) with no leftover unstaged changes: `git status --short`.
