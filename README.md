# Agent Checkpoint

Agent Checkpoint is a portable skill and command-line tool for preserving the
small amount of project state that a new AI-agent session actually needs. It
keeps verified progress in `PROGRESS.md`, places detailed planning material in
a template-backed work package, and gives the next session a deterministic
reading order instead of asking it to reconstruct a compacted conversation.

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

4. After a handoff or compaction, start a new session and read
   `PROGRESS.md`. Follow its work-package pointer to `CURRENT.md` and then
   `CONTINUE_PROMPT.md`; execute only the documented Current Target.

This design makes `PROGRESS.md` a short routing document and keeps the
template package as the source of detailed execution state.

## Adapter behavior at a glance

| Target | Checkpoint behavior | New-session behavior |
|---|---|---|
| Claude Code | Automatic PreCompact bootstrap only when no checkpoint exists; manual commands remain available | The hook tells a fresh startup session to read `PROGRESS.md` and follow its work-package pointer |
| Codex | Manual skill and CLI workflow | Read the checkpoint/work package manually |
| OpenCode | Manual skill, commands, and CLI workflow | Read the checkpoint/work package manually |
| Gemini CLI | Advisory pre-compression message when checkpoint state is missing or stale | Read the checkpoint/work package manually |

Automatic behavior never fabricates a task summary. In particular, the Claude
bootstrap checkpoint clearly marks itself as a placeholder because lifecycle
hooks cannot inspect the preceding conversation. Replace it with a
task-specific manual checkpoint once the active work is known.

## Requirements

- Python 3.11 or newer on `PATH`
- Git for branch, worktree, ignore, and tracked-file diagnostics

## Install the CLI globally

### npm / npx

The npm package wraps the bundled Python 3.11+ core. After the package is
published to the npm registry, either install it globally or run it on demand:

```bash
npm install -g agent-checkpoint
agent-checkpoint --help

npx --yes agent-checkpoint --help
```

Publishing is deliberately separate from this repository change: use your
approved npm account and package name before relying on the registry form. To
test a checkout before publication, install that checkout directly:

```bash
npm install -g /absolute/path/to/agent-checkpoint
```

The wrapper uses `python3` by default. Set `AGENT_CHECKPOINT_PYTHON` to select
another Python 3.11+ executable.

### Python prefix installation

From this repository, install the shared CLI into an explicit prefix:

```bash
python3 tools/install.py --prefix "$HOME/.local"
```

The installer writes the package under
`$HOME/.local/share/agent-checkpoint` and the launcher at
`$HOME/.local/bin/agent-checkpoint`. It never edits shell startup files, so add
`$HOME/.local/bin` to `PATH` yourself if necessary. Running
`python3 tools/install.py` without `--prefix` prints the recommended locations
without changing anything. Installation refuses symlinks in the prefix or its
`share`/`bin` destination ancestors, including with `--force`.

## Install the generic skill globally

`skill-install` copies the canonical generic skill once to
`~/.agent/skills/checkpoint`, then creates symbolic links only for the agents
you select. It never overwrites an existing skill or link.

```bash
agent-checkpoint skill-install --global \
  --agent claude-code \
  --agent codex \
  --agent opencode
```

The selected link targets are `~/.claude/skills/checkpoint`,
`$CODEX_HOME/skills/checkpoint` (or `~/.codex/skills/checkpoint` when
`CODEX_HOME` is unset), and
`~/.config/opencode/skills/checkpoint`. Choose `--agent agent-compatible` to
also link `~/.agents/skills/checkpoint`, which OpenCode discovers as an
agent-compatible global skill location. You may instead choose exact paths:

```bash
agent-checkpoint skill-install --destination .agent/skills \
  --link .claude/skills \
  --link .codex/skills
```

Gemini CLI does not load generic `SKILL.md` directories, so it is intentionally
not a symbolic-link target. Install its native extension from the built adapter
instead:

```bash
gemini extensions install "$PWD/dist/gemini-cli"
```

## Initialize a project

Run this once from the consumer project's root:

```bash
agent-checkpoint init
```

Initialization adds a managed block for `PROGRESS.md` and
`PROGRESS_ARCHIVE.md` to that project's `.gitignore` without replacing its
existing rules. This package repository does not globally ignore those names;
initialization controls them in each consumer project.

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
a concise `PROGRESS.md` entry that points to
`.agent-checkpoint/work/current/`. Planning fills that package's `CURRENT.md`
and `PLAN_*.md` prompt; a new session reads `PROGRESS.md`, `CURRENT.md`, then
`CONTINUE_PROMPT.md` and executes only the Current Target.

## Runtime adapters

Each build is self-contained: it copies the canonical core, an executable
`bin/agent-checkpoint` launcher, and the selected runtime's native files into
the output directory.

```bash
python3 tools/build_adapter.py claude-code --output dist/claude-code
python3 tools/build_adapter.py codex --output dist/codex
python3 tools/build_adapter.py opencode --output dist/opencode
python3 tools/build_adapter.py gemini-cli --output dist/gemini-cli
```

Install the resulting directory with the runtime's native plugin, skill, or
extension workflow. The supported capability levels are:

| Target | Capability | Behavior |
|---|---|---|
| Claude Code | `automatic` | `/agent-checkpoint:checkpoint`, `/agent-checkpoint:resume`, and `/agent-checkpoint:handoff`, plus bootstrap checkpoint creation followed by a new-session handoff |
| Codex | `manual` | Native checkpoint skill with manual resume, handoff, and doctor workflows |
| OpenCode | `manual` | Native commands and skill; no lifecycle automation is promised |
| Gemini CLI | `advisory` | Native commands plus a pre-compression checkpoint advisory; resume and handoff remain manual |

All adapters retain a manual checkpoint path if lifecycle automation is absent
or unavailable.

### Install an adapter

Build the adapter you need first. The shared CLI can be installed once for all
runtimes, but each native adapter still needs its own installation step.

```bash
python3 tools/install.py --prefix "$HOME/.local"
export PATH="$HOME/.local/bin:$PATH"
```

#### Claude Code

For local development or a one-session test, load the built plugin directly:

```bash
claude --plugin-dir "$PWD/dist/claude-code"
```

For a persistent installation, publish or add the bundle through a Claude Code
marketplace and install it with Claude Code's plugin manager.

#### Codex

Install the checkpoint skill into Codex's user skill directory:

```bash
mkdir -p "${CODEX_HOME:-$HOME/.codex}/skills"
cp -a dist/codex/skills/checkpoint "${CODEX_HOME:-$HOME/.codex}/skills/"
```

Restart Codex after copying it. This adapter is manual-only.

#### OpenCode

Copy the built skill and commands into the current project's OpenCode folders:

```bash
mkdir -p .opencode/skills .opencode/commands
cp -a dist/opencode/skills/checkpoint .opencode/skills/
cp -a dist/opencode/commands/. .opencode/commands/
```

Restart OpenCode or reload its project configuration. This adapter is
manual-only.

#### Gemini CLI

Install the built extension from its local path, then restart Gemini CLI:

```bash
gemini extensions install "$PWD/dist/gemini-cli"
```

Gemini CLI copies local extensions on installation; run its extension update
command after rebuilding when you want to refresh that installed copy.

When Claude Code reaches compaction without an existing checkpoint, its hook
writes one valid bootstrap entry through the bundled CLI, stops the current
processing path, and asks the user to start a fresh Claude Code session. That
new `startup` session receives only the `PROGRESS.md -> CURRENT.md ->
CONTINUE_PROMPT.md` reading order, not a prior-history resume body. If the
bootstrap write fails, compaction is blocked rather than proceeding without a
checkpoint. Existing checkpoints are left unchanged.

To statically check a built bundle, run:

```bash
python3 tools/validate_adapters.py dist/claude-code
```

Validation checks both the shared launcher/core and the selected runtime's
native manifest, command, skill, and hook structure. Bundle builds are staged
before replacement; output paths that overlap the selected adapter template or
canonical core are refused, and a failed forced build preserves the prior
bundle.

## Project configuration

An optional `.agent-checkpoint.toml` in the consumer project's root overrides
the defaults. Progress and archive paths are resolved under the canonical
project root and must remain distinct. Absolute paths, `..`, control
characters, reserved project/system paths, and symlinked path components are
rejected.

```toml
progress_path = "PROGRESS.md"
archive_path = "PROGRESS_ARCHIVE.md"
language = "English"
max_live_chars = 12000
resume_max_chars = 6000
lock_timeout_seconds = 10.0
include_git_hints = true
```

`max_live_chars` controls live-file rotation, `resume_max_chars` bounds default
resume output, and `lock_timeout_seconds` controls concurrent-write lock
waiting. `language` is rendered as a resume/handoff instruction.
`include_git_hints` controls whether handoff output includes safe branch,
worktree, and changed-filename hints; `doctor` still inspects Git safety state
when hints are disabled. Checkpoint content and diagnostics reject probable
credentials and never store a Git diff.

## Development

Run the complete test suite and validate any generated bundles before release:

```bash
PYTHONPATH=core python3 -m unittest discover -s tests -v
python3 tools/validate_adapters.py dist/claude-code
```

## License

Distributed under the [MIT License](LICENSE).
