# AI Development Templates — Complete 10-Type Set

Reusable planning and execution frameworks for AI coding agents such as Codex CLI and Claude Code.

## Included Workflows

```text
01 project/       New project
02 feature/       Feature addition/change
03 bugfix/        Bug diagnosis/fix
04 refactor/      Internal structural improvement
05 upgrade/       Framework/runtime/dependency upgrade
06 migration/     Database/data/schema/format migration
07 performance/   Performance optimization
08 integration/   External API/service/provider integration
09 release/       Release/deployment
10 spike/         Research/POC/technical decision
```

## Universal Execution Rule

Every workflow follows:

```text
one AI invocation
=
one Step
or
one Gate
```

After verified PASS:

```text
mark current target complete
-> advance tracker to next target
-> completion report
-> STOP
```

FAIL does not advance the tracker.

## Template Selector

Read:

```text
shared/TEMPLATE_SELECTOR.md
```

Quick guide:

| What are you doing? | Use |
|---|---|
| Building a new system | PROJECT |
| Adding/changing functionality | FEATURE |
| Fixing wrong behavior | BUGFIX |
| Restructuring without intended behavior change | REFACTOR |
| Updating versions | UPGRADE |
| Changing persisted data/schema | MIGRATION |
| Making something faster/cheaper | PERFORMANCE |
| Connecting a provider/API | INTEGRATION |
| Shipping to an environment | RELEASE |
| Investigating before committing | SPIKE |

## Standard Usage

Each workflow has:

```text
prompts/PLAN_*_PROMPT.md
prompts/FIRST_RUN_PROMPT_TEMPLATE.md
prompts/CONTINUE_PROMPT.md
prompts/QUICK_REQUEST.txt
templates/
```

### 1. Plan

Ask the AI to read the workflow's `PLAN_*_PROMPT.md` and your requirements.

The planning invocation creates the actual project/change work package.

Do not implement during planning.

### 2. First execution

Tell the coding agent:

```text
Read the generated FIRST_RUN_PROMPT.md and proceed exactly as written.
```

### 3. Every later execution

Start a fresh agent session when practical and say:

```text
Read the generated CONTINUE_PROMPT.md and proceed exactly as written.
```

The Continue prompt reads the tracker and determines the current Step/Gate automatically.

## Shared Rules

- `shared/EXECUTION_RULES.md`
- `shared/EVIDENCE_STANDARD.md`
- `shared/GATE_STANDARD.md`
- `shared/CHANGE_SCOPE_RULES.md`
- `shared/TEMPLATE_SELECTOR.md`
- `shared/WORK_TYPE_HARD_RULES.md`

## Important Boundary

These templates define **how to plan and verify work**.

They do not define your product's:

- technology stack;
- business features;
- AI provider;
- deployment topology;
- security model;
- UI framework;
- database choice.

Those must be derived from the actual project requirements and existing repository.
