# Upgrade Step <ID> — <TITLE>

## Target
- Step: <ID>
- Scope: **Only this Step**

## Goal

<Precise version-bump / compatibility-fix goal — one or two sentences.
State the exact component(s) and version range this Step moves, not a
restated title.>

## Preconditions

<Which earlier Step(s)/Gate must already be verified complete, including
whether `COMPATIBILITY_MATRIX.md` covers this Step's component(s) with a
current Current -> Target row and a Breaking Changes entry for every
relevant change. A version bump must not start before its compatibility
entry exists.>

## Required Reading / Existing System Inspection

Before implementing, read:
- repository agent instructions (`AGENTS.md`/`CLAUDE.md` equivalent);
- this work package (`WORK.md`);
- `CURRENT.md`;
- `COMPATIBILITY_MATRIX.md` — the Current -> Target row, Breaking Changes,
  Runtime/Toolchain Requirements, and Rollback Compatibility entries for
  this Step's component(s);
- official migration/release notes for the exact version range this Step
  crosses (not just the final target version — read every intermediate
  major/minor release's notes when skipping versions);
- relevant source-of-truth architecture/docs;
- affected tests/contracts, lockfiles, and CI/build configuration.

Inspect, concretely, before making any change:
- exact current version(s) installed/pinned, verified from the lockfile or
  manifest, not assumed from documentation;
- every call site depending on an API/behavior that changes or is removed
  in the target version range;
- whether this Step's bump is bounded (per `WORK_TYPE_HARD_RULES.md`'s
  UPGRADE rule) — a single Step should not span an unbounded number of
  major versions when intermediate stops are feasible.

## Scope

### In Scope
- ...

### Out of Scope
- ...
- any unrelated feature work or refactor — route it to a separate work
  package instead of folding it into this upgrade.

## Implement

<High-level shape of the version bump and compatibility fixes this Step
makes — the "what" and "why," including the exact version range — before
the Task-by-Task "how" below.>

## Granular Execution Tasks

> Execute each Task in order and collect evidence before proceeding. See
> `shared/TASK_DECOMPOSITION_STANDARD.md` for the required structure of each
> Task below. Frame each Task around a version bump or a specific breaking-
> change remediation: the Task's Implementation Contract must name the
> exact `COMPATIBILITY_MATRIX.md` row(s) it resolves, and its Task-Level
> Test Cases must include the Verification Matrix items relevant to that
> component (build, tests, startup, migrations, smoke).

### Task 1 — <imperative, specific version/compatibility action>

#### Objective
One sentence: what this Task alone bumps or remediates, and which
`COMPATIBILITY_MATRIX.md` row(s) it resolves.

#### Inspect Before Editing
- exact files/modules/manifests/lockfiles this Task is expected to touch;
- exact current version and exact target version for this Task's
  component;
- note: if an equivalent module already exists under a different path,
  extend it and record the mapping in the completion report instead of
  creating a parallel implementation.

#### Implementation Contract
- accepted inputs (unchanged unless the breaking change requires an
  adaptation, in which case name the adaptation explicitly);
- returned outputs / persisted state (unchanged unless declared);
- invariants that must hold before and after — including the rollback path
  described in `COMPATIBILITY_MATRIX.md`;
- error categories this Task owns (e.g. version-mismatch, missing peer
  dependency, deprecated-API-still-in-use).

#### Detailed Implementation Steps
1. run the existing build/test suite and record it as the pre-upgrade
   baseline;
2. confirm the exact current -> target version pair against
   `COMPATIBILITY_MATRIX.md` and official release notes before editing any
   manifest/lockfile;
3. apply the version bump for this Task's bounded increment only — do not
   pull a later Task's or later Step's version range in;
4. apply the specific breaking-change remediation(s) this Task owns,
   referencing the exact `COMPATIBILITY_MATRIX.md` row;
5. update lockfiles/manifests and regenerate them through the real
   package/dependency manager, not by hand-editing pinned hashes;
6. re-run clean install, build, and the existing test suite;
7. make partial-failure behavior explicit — a failed upgrade attempt must
   leave the repository in a state that can be inspected and safely rolled
   back per `COMPATIBILITY_MATRIX.md`'s Rollback Compatibility section;
8. add stable structured log context for any new deprecation/compat shims
   (no secrets);
9. verify through the real owning code path (actual startup/runtime, not
   only static checks).

#### Failure / Recovery Cases
List each realistic failure for this Task (including "peer dependency
conflict," "removed API still referenced," and "lockfile drift" as
first-class cases). For each one, specify:
- error category/code;
- safe user-facing message (if user-facing);
- internal log context;
- retryability;
- cleanup/compensation action (including rollback to prior pinned
  version);
- final resulting state.

#### Task-Level Test Cases
- clean install succeeds at the new version;
- build succeeds;
- the existing test suite passes at the new version;
- startup/runtime smoke check succeeds;
- each breaking-change remediation this Task owns has a targeted test
  proving the old call site now behaves correctly under the new version;
- unit tests must not require live paid external providers unless
  explicitly marked as opt-in integration tests.

#### Evidence Required Before Checking This Task
- exact install/build/test command(s) executed, and their exact versions
  before and after;
- PASS/FAIL result;
- key artifact/state inspected (lockfile diff, build output, startup log,
  test report);
- any deviation from this Task's target version or contract and why it was
  necessary.

#### Task Done Condition
Implemented through the real package manager and build/startup path, every
breaking change this Task owns is remediated with evidence (not merely
silenced by pinning or disabling a test), and its focused tests pass.
Placeholder code, disabled tests, or unresolved TODOs do not satisfy this
condition.

<!-- Repeat Task N for every additional Task this Step requires. -->

## Task Execution Tracking

| Task | Code | Focused Tests | Integration Evidence | Verified |
|---|---|---|---|---|
| 1. <name> | [ ] | [ ] | [ ] | [ ] |

## Cross-Cutting Contracts

> See `shared/CROSS_CUTTING_CONTRACTS.md`. Include only sections relevant to
> this Step's actual version/compatibility change; do not leave an
> irrelevant section as `...`.

### Architecture Fit
- name the source-of-truth architecture doc and `COMPATIBILITY_MATRIX.md`
  this Step must align with;
- state that listed file paths are recommended targets, not a command to
  restructure working code beyond this Step's declared scope.

### Expected Files / Modules
- concrete manifest/lockfile/config paths this Step changes, plus any
  source files requiring breaking-change remediation.

### Data / Persistence Changes
- state explicitly if none;
- if the new version changes on-disk/DB format, a forward migration is
  required per `CROSS_CUTTING_CONTRACTS.md`, and existing data must be
  preserved across the change.

### API Contract
- state explicitly if no request/response shape changes;
- if the upgraded dependency changes a public request/response shape or
  error code, name the exact change and the compatibility decision made.

### Worker / Background Processing Contract
- state explicitly if not applicable;
- if the upgraded runtime/library affects background job execution
  (timeouts, retry semantics, serialization), confirm those are unchanged
  or explicitly adapted.

### Configuration / Environment
- every new/changed environment variable, config key, or toolchain
  requirement (OS/base image, compiler, runtime version) introduced by this
  Step, per `COMPATIBILITY_MATRIX.md`'s Runtime/Toolchain Requirements;
- typed/validated, documented in `.env.example` or equivalent, safe default
  only when genuinely safe, excluded from logs when secret.

### Error Handling Matrix
- list each failure mode introduced or touched by this version bump
  (deprecated API removed, changed error type/shape, new required config),
  with error code/message, retryability, and cleanup/rollback behavior.

### Logging / Observability
- what changes in log output/format due to the dependency bump vs. what
  stays the same in correlation identifiers;
- explicit reminder: never log credentials or full sensitive provider
  payloads.

## Regression / Compatibility Surface

- exact `COMPATIBILITY_MATRIX.md` rows (Breaking Changes, Removed/
  Deprecated APIs) this Step resolves;
- other existing tests/contracts that could be affected by this version
  bump even if not directly touched;
- rollback path: can this Step be reverted to the prior pinned version
  without data loss?

## Required Test Matrix

In addition to each Task's own tests, run `COMPATIBILITY_MATRIX.md`'s
Verification Matrix for this Step's component(s): clean install, lockfile/
install, build, tests, startup, migrations, production-like smoke.

## Manual Verification

<Anything automated assertions cannot fully cover for this version bump —
e.g. confirming no behavioral drift in a UI flow, CLI output formatting, or
a runtime warning that only appears interactively.>

## Acceptance Criteria

- [ ] ...
- [ ] Component(s) are at the exact target version recorded in
      `COMPATIBILITY_MATRIX.md`.
- [ ] Every Breaking Change row this Step claimed to resolve has passing
      evidence.
- [ ] Rollback path remains valid or is explicitly documented as no longer
      available (with justification).

## Implementation Review Checklist

> Baseline list from `shared/STEP_EXECUTION_PROTOCOL.md`; the items below
> the line are upgrade-specific and must also be verified.

- [ ] Existing repository architecture/behavior was inspected before changes.
- [ ] Only this Step's declared scope was implemented.
- [ ] New schemas/types are validated and versioned where necessary.
- [ ] Database migrations are present and tested when persistence changed.
- [ ] Long-running work runs outside request/response handlers.
- [ ] External commands/inputs are validated, not string-concatenated.
- [ ] Timeouts and failure paths are explicit for every external call.
- [ ] Retry behavior cannot silently duplicate or corrupt state/artifacts.
- [ ] Tests cover the core success path and each meaningful failure.
- [ ] Documentation/config examples were updated where relevant.
- [ ] Every Acceptance Criterion for this Step is independently verified.
- [ ] `CURRENT.md` was updated only after verification, not before.
- [ ] No Task or file belonging to a later Step/Gate was started.
---
- [ ] Current and target versions for this Step were recorded before any
      change was made.
- [ ] `COMPATIBILITY_MATRIX.md`'s Breaking Changes rows for this Step's
      component(s) each have explicit remediation evidence, not a silenced
      test or an unexplained pin.
- [ ] The upgrade was bounded to this Step's declared increment — it did
      not silently reach further than the declared target version.
- [ ] A rollback/downgrade path was verified or explicitly documented as
      unavailable, per `COMPATIBILITY_MATRIX.md`'s Rollback Compatibility
      section.
- [ ] No unrelated feature work or refactor was folded into this upgrade.

## Step Execution Protocol

> See `shared/STEP_EXECUTION_PROTOCOL.md` for the full A–E protocol
> (Baseline -> Task Loop -> Step Integration -> Definition of Done -> Stop).
> This Step's Definition of Done additionally requires:

- every Task Execution Tracking row fully checked;
- the pre-upgrade baseline build/test run was captured and the post-upgrade
  run is compared against it, not merely re-run in isolation;
- this Step's own Acceptance Criteria and Implementation Review Checklist
  items verified, not assumed;
- `CURRENT.md` and `COMPATIBILITY_MATRIX.md` updated to reflect completion
  only after the above.

## Completion

PASS:
1. mark this Step complete in `CURRENT.md`;
2. advance Current Target;
3. write the completion report (per `shared/EXECUTION_RULES.md`);
4. STOP.

FAIL:
1. leave this Step incomplete;
2. do not advance Current Target;
3. report exact remediation needed;
4. STOP.

Do not start the next Step or Gate in this invocation.
