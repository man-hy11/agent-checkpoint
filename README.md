# Agent Checkpoint

**English** | [한국어](README.ko.md)

Agent Checkpoint is a portable skill and command-line tool for preserving the
small amount of project state that a new AI-agent session actually needs. It
keeps verified progress in a work-scoped `PROGRESS.md`, places detailed
planning material in a template-backed work package, and gives the next
session a deterministic reading order — starting from the repo-root
`CONTINUE_PROMPT.md` — instead of asking it to reconstruct a compacted
conversation.

It is deliberately not a chat transcript, memory database, or Git-diff store.
Each checkpoint records the current goal, verified progress, current focus,
next actions, and durable decisions; detailed plans, evidence, and gates stay
in `.agent-checkpoint/work/<id>/`.

## What the skill provides

- A dependency-free Python 3.11+ CLI for safe checkpoint writes, validation,
  rotation/archival, bounded resume and handoff context, and diagnostics.
- Ten development workflow templates: `project`, `feature`, `bugfix`,
  `refactor`, `upgrade`, `migration`, `performance`, `integration`, `release`,
  and `spike`.
- A generic `SKILL.md` that directs compatible agents to ask for missing
  planning inputs rather than inventing scope, success criteria, or
  constraints.
- Native adapters for Claude Code, Codex, OpenCode, and Gemini CLI, with each
  adapter exposing only the lifecycle behavior its host can actually support.
- Safety boundaries: atomic writes, locking, project-path containment,
  credential and diff-content rejection, and Git-aware diagnostic hints that
  do not read or persist Git file contents.

## How a work item flows

1. At the start of a work item, select a workflow type and materialize a work
   package. The command writes a concise pointer checkpoint rather than a large
   copy of the templates.

   ```bash
   agent-checkpoint workflow --type feature --id current
   ```

2. Before planning, the skill asks the user for any material information that
   is missing for the selected template: goal, scope, success criteria,
   constraints, or affected area. It records confirmed facts only.

3. During work, write a compact checkpoint using the five required headings
   and attach concrete verification results separately. Do not paste diffs,
   credentials, or speculative summaries.

4. After a handoff or compaction, start a new session and read the repo-root
   `CONTINUE_PROMPT.md`. It names the active work package; follow it to that
   package's `CURRENT.md` and then its own `CONTINUE_PROMPT.md`, and execute
   only the documented Current Target.

This design makes each work package's `PROGRESS.md` a short routing document
and keeps the template package as the source of detailed execution state.

## The twelve skills

`checkpoint` is a router: it runs `work status`, reads `next_skill`, and
invokes exactly that skill — it never edits state itself. The other eleven
each own one phase of a work package's lifecycle, selected by the unit's
current condition rather than by the agent's judgment. See
`skills/_checkpoint-shared/chain-v1.md` for the full ordered routing table.

| Skill | Fires when | Does |
|---|---|---|
| `checkpoint` | Always, first | Reads `work status --json`, dispatches to the skill named in `next_skill` |
| `checkpoint-select-workflow` | No state block exists yet | Asks which of the ten workflow types fits, then runs `agent-checkpoint workflow --type TYPE --id current` to create the package |
| `checkpoint-brainstorm` | A package exists but `brief_confirmed` is false | Asks for goal, scope, success criteria, constraints, and affected area; records only confirmed answers |
| `checkpoint-plan` | Brief confirmed, but the unit list is empty or the current unit is superseded | Writes `PLAN.md` with numbered steps tied to unit IDs; the only skill that edits the plan |
| `checkpoint-claim` | Current unit is `pending` or `ready` | Verifies the unit's dependency is satisfied, then runs `work start` to move it to `running` |
| `checkpoint-execute` | Current unit is `running` and its kind is `step` | Implements the step; folds small in-scope discoveries into its own evidence, defers larger ones to a handoff report |
| `checkpoint-verify-gate` | Current unit is `running` and its kind is `gate` | Checks cross-cutting acceptance criteria; any unmet criterion is a fail, not a partial pass |
| `checkpoint-evidence` | Execution or gate verification just finished | Validates the evidence document against the manifest's required sections, then runs `work pass` or `work fail` |
| `checkpoint-diagnose` | Current unit is `failed` with no `root_cause_fingerprint` | Analyzes the failure and records a fingerprint; never selects a recovery action itself |
| `checkpoint-recover` | Current unit is `failed` (fingerprint set) or `blocked` | Chooses one of `retry`, `replan`, `supersede`, `block`, `unblock` from `allowed_events` and applies it |
| `checkpoint-handoff` | Every unit is `passed` | Renders the final handoff context; checks each open handoff report against the tree before asking whether to resolve or act on it |
| `checkpoint-inspect` | Any time a read-only status view is needed | Reports state without writing — never calls a transition or recovery command |

## Adapter behavior at a glance

| Target | Checkpoint behavior | New-session behavior |
|---|---|---|
| Claude Code | Automatic PreCompact bootstrap only when no checkpoint exists; manual commands remain available | The hook tells a fresh startup session to read the root `CONTINUE_PROMPT.md` and follow its work-package pointer |
| Codex | Manual skill and CLI workflow | Read the checkpoint/work package manually |
| OpenCode | Manual skill, commands, and CLI workflow | Read the checkpoint/work package manually |
| Gemini CLI | Advisory pre-compression message when checkpoint state is missing or stale | Read the checkpoint/work package manually |

Automatic behavior never fabricates a task summary. In particular, the Claude
bootstrap checkpoint clearly marks itself as a placeholder because lifecycle
hooks cannot inspect the preceding conversation. Replace it with a
task-specific manual checkpoint once the active work is known.

When Claude Code reaches compaction without an existing checkpoint, its hook
writes one valid bootstrap entry, stops the current processing path, and asks
the user to start a fresh Claude Code session. That new `startup` session
receives only the root `CONTINUE_PROMPT.md -> CURRENT.md ->
CONTINUE_PROMPT.md` reading order, not a prior-history resume body. If the
bootstrap write fails, compaction is blocked rather than proceeding without a
checkpoint. Existing checkpoints are left unchanged.

## Requirements

- Python 3.11 or newer on `PATH`
- Git for branch, worktree, ignore, and tracked-file diagnostics

## Install the CLI

The CLI is a dependency-free Python 3.11+ program. From a checkout, either
add `bin/` to `PATH` or symlink the launcher onto an existing `PATH`
directory:

```bash
ln -s /absolute/path/to/agent-checkpoint/bin/agent-checkpoint /usr/local/bin/agent-checkpoint
agent-checkpoint --help

# or invoke it directly without installing anything
/absolute/path/to/agent-checkpoint/bin/agent-checkpoint --help
```

Set `AGENT_CHECKPOINT_PYTHON` to select a specific Python 3.11+ executable if
`python3` on `PATH` doesn't resolve to one.

## Install the skill

### Claude Code plugin (recommended for Claude Code)

Host bundles are built on demand rather than checked in. Build the Claude Code
bundle first; it is itself a Claude Code plugin marketplace
(`.claude-plugin/marketplace.json`), so Claude Code can install its skills,
commands, and hooks together in one step. Point the marketplace add at the
built bundle, not the repository root:

```bash
# Build the bundle from a local checkout
python3 tools/build_adapter.py claude-code --output /absolute/path/to/bundle

# Then, from a shell
claude plugin marketplace add /absolute/path/to/bundle
claude plugin install agent-checkpoint@agent-checkpoint

# Or from inside a Claude Code session
/plugin marketplace add /absolute/path/to/bundle
/plugin install agent-checkpoint@agent-checkpoint
```

This is the only install path that also gives you the Claude Code adapter's
`PreCompact`/`SessionStart` hooks and `/checkpoint`, `/resume`, `/handoff`
commands, not just the raw `SKILL.md` files. It still doesn't install the
`agent-checkpoint` CLI itself — put `bin/agent-checkpoint` on `PATH` as
described above so the commands the skills reference resolve.

### npx skills add (Claude Code, Codex, OpenCode, and other `skills`-CLI agents)

The skill package also installs with the community
[`skills`](https://www.npmjs.com/package/skills) CLI, which clones this
repository and links every `SKILL.md` it finds under `skills/` into your
agent's skill directory:

```bash
# Install every checkpoint skill
npx skills add https://github.com/man-hy11/agent-checkpoint --all

# Install a single skill (for example, the router)
npx skills add https://github.com/man-hy11/agent-checkpoint --skill checkpoint
```

This installs the skill definitions only (no hooks, no commands); it does not
install the `agent-checkpoint` CLI. Put `bin/agent-checkpoint` on `PATH`
as described above so the commands referenced by the skills resolve.

## Where things get installed

The CLI and the skill definitions are two separate deliverables that install
independently — there is no single command that installs both.

### The skill files (`SKILL.md`)

| Installer | Canonical (real files) | Naming |
|---|---|---|
| Claude Code plugin (`/plugin install`) | `~/.claude/plugins/cache/...` | managed entirely by Claude Code; not a bare `SKILL.md` directory |
| `npx skills add ... -g` (the community `skills` CLI) | `~/.agents/skills/` | plural `.agents` |

For the `skills`-CLI path, every supported coding agent gets a symlink
pointing back to the canonical copy — the agent itself never stores its own:

```
~/.claude/skills/checkpoint*              -> ~/.agents/skills/checkpoint*
~/.codex/skills/checkpoint*                (or $CODEX_HOME/skills)
~/.config/opencode/skills/checkpoint*
```

Gemini CLI does not read generic `SKILL.md` directories at all, so neither
installer links anything for it.

### Practical effect

Because the CLI and the skills install independently, running only one half
leaves the other missing. Installing the skill (via the Claude Code plugin or
`npx skills add`) without also putting `bin/agent-checkpoint` on `PATH`
means the skill's instructions reference a command that can't run.

## Initialize a project

Run this once from the consumer project's root:

```bash
agent-checkpoint init
```

Initialization adds a managed block ignoring every work package's
`PROGRESS.md` and `PROGRESS_ARCHIVE.md` (under
`.agent-checkpoint/work/*/`) to that project's `.gitignore` without replacing
its existing rules. This package repository does not globally ignore those
names; initialization controls them in each consumer project.

If either progress file is already tracked, an ignore rule does not remove it
from the Git index. Agent Checkpoint inspects tracking and ignore state for both
the live and archive files, reports an `already tracked` warning, and leaves the
manual Git migration to you; it never runs `git rm --cached`.

## Core commands

```bash
agent-checkpoint write --entry checkpoint-entry.md
agent-checkpoint validate --entry checkpoint-entry.md
agent-checkpoint status
agent-checkpoint resume
agent-checkpoint handoff
agent-checkpoint doctor --adapter codex
agent-checkpoint workflow --type feature --id current
```

Use `--root PATH` when the project root is not the current directory. `write`,
`validate`, and `dry-run` accept `--entry -` to read an entry from standard
input. `resume` and `handoff` accept `--max-chars NUMBER`; `status` and
`doctor` accept `--json`. `write`, `validate`, and `dry-run` reject Git or
unified-diff-shaped input. Writes also refuse unsafe diff-shaped content in an
existing live file or archive.

Repeated `write --verification TEXT` values are stored in the optional
`## 6. Verification` section. `handoff` renders those persisted results under
`Verification results`; they are not included in `Recent Decisions`.

`doctor` checks checkpoint state, Git tracking and worktree context, and reports
the selected adapter's capability. For example:

```bash
agent-checkpoint doctor --adapter claude-code
agent-checkpoint doctor --adapter codex --json
agent-checkpoint doctor --adapter opencode
agent-checkpoint doctor --adapter gemini-cli
```

## Template-backed work packages

The bundle includes the complete development-template asset package. For a new
work item, choose its workflow type and materialize only that type plus the
shared rules in the consumer project:

```bash
agent-checkpoint workflow --type feature --id current
```

Supported types are `project`, `feature`, `bugfix`, `refactor`, `upgrade`,
`migration`, `performance`, `integration`, `release`, and `spike`. This writes
a concise `PROGRESS.md` entry under `.agent-checkpoint/work/current/` and a
repo-root `CONTINUE_PROMPT.md` naming that package. Planning fills the
package's `CURRENT.md` and `PLAN_*.md` prompt; a new session reads the root
`CONTINUE_PROMPT.md`, then the package's `CURRENT.md`, then its own
`CONTINUE_PROMPT.md`, and executes only the Current Target.

## Project configuration

An optional `.agent-checkpoint.toml` in the consumer project's root overrides
the defaults. `progress_path`/`archive_path` name the checkpoint filenames
relative to the active work package (rebased under
`.agent-checkpoint/work/<id>/` at runtime) and must remain distinct. Absolute
paths, `..`, control characters, reserved project/system paths, and symlinked
path components are rejected.

```toml
progress_path = "PROGRESS.md"
archive_path = "PROGRESS_ARCHIVE.md"
language = "English"
max_live_chars = 12000
resume_max_chars = 6000
lock_timeout_seconds = 10.0
include_git_hints = true
auto_commit_on_handoff = false
```

`max_live_chars` controls live-file rotation, `resume_max_chars` bounds default
resume output, and `lock_timeout_seconds` controls concurrent-write lock
waiting. `language` is rendered as a resume/handoff instruction.
`include_git_hints` controls whether handoff output includes safe branch,
worktree, and changed-filename hints; `doctor` still inspects Git safety state
when hints are disabled. Checkpoint content and diagnostics reject probable
credentials and never store a Git diff.

`auto_commit_on_handoff` (default `false`) stages and commits the working
tree at the end of `agent-checkpoint handoff`, once every unit in the work
package has passed. It treats the tree's full dirty state at handoff time as
the package's footprint — there is no per-unit file scoping. It never raises:
no Git repository, a clean tree, or a failing `git commit` (e.g. a rejecting
pre-commit hook) all resolve to a skip reported on stderr, and handoff still
completes.

## Development

Run the complete test suite:

```bash
PYTHONPATH=. python3 -m unittest discover -s tests -v
```

## License

Distributed under the [MIT License](LICENSE).
