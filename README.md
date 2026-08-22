# Agent Checkpoint

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

Installing the package also runs a `postinstall` step that places the generic
skill at `~/.agent/skills/checkpoint` and links it into any global skill
directories it can detect, unless a skill is already installed there.

Publishing is deliberately separate from this repository change: use your
approved npm account and package name before relying on the registry form. To
test a checkout before publication, install that checkout directly:

```bash
npm install -g /absolute/path/to/agent-checkpoint
```

The wrapper uses `python3` by default. Set `AGENT_CHECKPOINT_PYTHON` to select
another Python 3.11+ executable.

### npx skills add

The skill package also installs with the community
[`skills`](https://www.npmjs.com/package/skills) CLI, which clones this
repository and links the `SKILL.md` files it finds under `core/skills/` into
your agent's skill directory. Pass `--full-depth` so it looks past the
repository root:

```bash
# Install every checkpoint skill
npx skills add https://github.com/man-hy11/agent-checkpoint --full-depth --all

# Install a single skill (for example, the router)
npx skills add https://github.com/man-hy11/agent-checkpoint --full-depth --skill checkpoint
```

This installs the skill definitions only; it does not install the
`agent-checkpoint` CLI. Install the CLI with npm as described above so the
commands referenced by the skills are on `PATH`.

## Where things get installed

The CLI and the skill definitions are two separate deliverables, and each
install path puts them in different places. There is no single directory that
holds everything.

### The CLI

`npm install -g agent-checkpoint` puts the `agent-checkpoint` executable
wherever your npm global prefix resolves to (for example
`/usr/local/lib/node_modules` or your `nvm`/`npm config get prefix` location).
This is ordinary npm global-install behavior, not something this package
controls.

### The skill files (`SKILL.md`)

Two different tools manage skill files, and they use two different canonical
directories:

| Installer | Canonical (real files) | Naming |
|---|---|---|
| `agent-checkpoint skill-install` (also run by npm's `postinstall`) | `~/.agent/skills/` | singular `.agent` |
| `npx skills add ... -g` (the community `skills` CLI) | `~/.agents/skills/` | plural `.agents` |

Only one of these two directories holds the actual files for a given install;
the other tool never writes to it. Whichever one is canonical, every
supported coding agent gets a symlink pointing back to it — the agent itself
never stores its own copy:

```
~/.claude/skills/checkpoint*              -> canonical directory above
~/.codex/skills/checkpoint*                (or $CODEX_HOME/skills)
~/.config/opencode/skills/checkpoint*
```

`agent-checkpoint skill-install --agent agent-compatible` additionally links
`~/.agents/skills/checkpoint*` even when `~/.agent/skills/` is the canonical
copy — that one flag is the only place the two naming conventions overlap.

Gemini CLI does not read generic `SKILL.md` directories at all, so neither
installer links anything for it; it needs the native extension built by
`tools/build_adapter.py gemini-cli` instead.

### Practical effect

Because the CLI and the skills install independently, running only one half
leaves the other missing. Installing the CLI without also running
`skill-install` (or `npx skills add`) means no coding agent can discover the
skill; installing the skill without the CLI means the skill's `SKILL.md`
instructions reference an `agent-checkpoint` command that is not on `PATH`.
`npm install -g agent-checkpoint` handles both automatically via its
`postinstall` step; the other install paths require running each step
yourself.

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
npm install -g agent-checkpoint
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
new `startup` session receives only the root `CONTINUE_PROMPT.md -> CURRENT.md
-> CONTINUE_PROMPT.md` reading order, not a prior-history resume body. If the
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
