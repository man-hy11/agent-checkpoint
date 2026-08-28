# Release / Deployment Step <ID> — <TITLE>

## Target
- Step: <ID>
- Scope: **Only this Step**

## Goal

<Precise deployment-action goal — one or two sentences, not a restated
title. Release Steps ship already-built work; they do not implement new
application behavior.>

## Preconditions

<Which earlier Step(s)/Gate must already be verified complete — e.g. the
release scope must be frozen (D1) before packaging (D3), and preflight (D2)
must pass before Deploy (D4).>

## Required Reading / Existing System Inspection

Before executing, read:
- repository agent instructions (`AGENTS.md` / `CLAUDE.md`);
- this work package's `WORK.md`;
- `CURRENT.md`;
- `RELEASE_PLAN.md` (this Step must not contradict the frozen release
  scope/version/artifact — if reality requires a change, update
  `RELEASE_PLAN.md` first and note the change in this Step's evidence);
- the target environment's current deployed version/config, inspected
  live, not assumed from documentation;
- any existing deployment runbook/CI pipeline definition already in the
  repository — extend/follow it rather than inventing a parallel process;
- migration files and current schema version, if this Step touches
  migrations.

## Working Rule

Execute only this Step. If a later Step's action is relevant, leave a short
TODO or note only — do not perform it. Do not change production state
beyond what this Step's scope defines.

## Scope

### In Scope
- ...

### Out of Scope
- ...

## Execute

<High-level shape of the deployment action this Step performs — the "what,"
before the Task-by-Task "how" below. E.g. "build and tag the release
artifact," "run the preflight checklist against staging," "deploy the
frozen artifact to production and verify smoke tests.">

## Granular Execution Tasks

> Execute each Task in order and collect evidence before proceeding. Release
> Tasks adapt `shared/TASK_DECOMPOSITION_STANDARD.md`'s structure to
> deployment actions rather than application coding — "Detailed Execution
> Steps" replaces "Detailed Implementation Steps," and every Task must
> define its own rollback trigger/procedure per `WORK_TYPE_HARD_RULES.md`
> (RELEASE: "Define rollback trigger and procedure before changing
> production.").

### Task 1 — <imperative, specific deployment action>

#### Objective
One sentence: what this Task alone must accomplish (e.g. "freeze and tag
the release artifact," "apply the database migration to production with a
verified rollback path").

#### Inspect Before Editing
- exact environment(s)/pipeline config/manifest files this Task touches;
- current live state of the target environment (deployed version, active
  migrations, health status) captured before this Task begins, so any
  change is provably attributable to this Task;
- confirm no equivalent deployment mechanism already exists that this Task
  would duplicate — extend the existing pipeline/runbook and record the
  mapping in the completion report.

#### Implementation Contract
- exact artifact/version/commit/tag this Task acts on;
- accepted inputs (config, secrets, environment target);
- resulting environment state (what "done" looks like, observably);
- invariants that must hold before and after (e.g. zero-downtime
  constraint, data-loss constraint, backward-compatible schema during
  rolling deploy);
- failure categories this Task owns (e.g. build failure, preflight check
  failure, migration failure, deploy failure, smoke-test failure).

#### Detailed Execution Steps
Numbered, concrete steps — not restatement of the Objective. Include, where
applicable:
1. capture current environment state (deployed version, health, active
   migrations) as the before-baseline;
2. confirm the Implementation Contract above, including the exact
   artifact/version this Task acts on, before executing;
3. execute only this Task's action — do not pull forward-Step scope in
   (e.g. do not deploy while still in a preflight-only Task);
4. run the action through the real deployment mechanism (CI pipeline,
   deploy script, infra tool) — not a manual approximation of it, unless no
   automated mechanism exists yet;
5. validate any external/boundary input (config values, secrets, artifact
   checksum) before an irreversible action;
6. make partial-failure behavior explicit — if this Task fails partway, the
   environment must end in a state that can be inspected and either rolled
   back or safely retried;
7. add stable structured log/audit context for this action (who/what
   triggered it, target environment, artifact version, timestamp) — no
   secrets in logs;
8. define this Task's rollback trigger (the observable condition that means
   "undo this Task") and rollback procedure, even if this Task is expected
   to succeed;
9. verify the resulting environment state directly (health check, deployed
   version endpoint, migration table, smoke request) — not only that the
   deployment command exited zero.

#### Failure / Recovery Cases
List each realistic failure for this Task, **including its rollback
trigger and rollback procedure** — per `WORK_TYPE_HARD_RULES.md` (RELEASE):
"Define rollback trigger and procedure before changing production." For
each failure:
- failure category/code (e.g. `BUILD_FAILED`, `PREFLIGHT_FAILED`,
  `MIGRATION_FAILED`, `DEPLOY_FAILED`, `SMOKE_TEST_FAILED`,
  `HEALTH_CHECK_FAILED`);
- observable signal that triggers this failure classification (specific
  metric/log/exit code/health endpoint response);
- rollback trigger — the exact threshold/condition that means "stop and
  roll back" (e.g. error rate > X% for Y minutes, critical smoke test
  fails, migration leaves schema in an inconsistent state);
- rollback procedure — the exact steps to revert (previous artifact/version
  to redeploy, migration-down command if reversible, config revert,
  traffic-shift-back for canary/blue-green);
- cleanup/compensation action (e.g. drain in-flight requests, invalidate
  cache, notify on-call);
- final resulting state after rollback (confirmed previous-good state, not
  merely "rollback command was run").

#### Task-Level Test Cases / Checks
- the success path, verified against real environment state;
- each boundary condition relevant to this Task (e.g. migration against a
  production-sized dataset copy, deploy under expected traffic);
- each failure case above, exercised via a dry run or staging rehearsal
  where the action is destructive/irreversible in production;
- assert actual environment/artifact state (deployed version, migration
  status, health endpoint), not only a command's return code;
- destructive production actions must not be exercised casually as a test —
  use staging/dry-run/canary evidence per `shared/EVIDENCE_STANDARD.md`.

#### Evidence Required Before Checking This Task
- exact command(s)/pipeline run executed, including run ID/link if CI-based;
- PASS/FAIL result;
- key artifact/state inspected (deployed version endpoint response,
  migration table state, health check output, smoke test result);
- rollback rehearsal evidence if this Task is irreversible or
  high-risk (dry run or staging rollback actually performed, not only
  documented);
- any deviation from this Task's contract and why it was necessary.

#### Task Done Condition
Executed through the real deployment mechanism, its rollback trigger and
procedure are explicit and — for high-risk actions — rehearsed, and its
checks confirm actual environment state. A green pipeline run alone does
not satisfy this condition; the resulting state must be independently
verified.

<!-- Repeat Task N for every additional Task this Step requires. -->

## Task Execution Tracking

| Task | Executed | Verification Checks | Rollback Readiness | Verified |
|---|---|---|---|---|
| 1. <name> | [ ] | [ ] | [ ] | [ ] |

## Cross-Cutting Contracts

> Most `shared/CROSS_CUTTING_CONTRACTS.md` sections do not apply to release
> work in their usual sense — there is normally no new API/data model being
> introduced. Use the release-adapted sections below instead. Include only
> what is relevant to this Step; do not leave a relevant section as `...`.

### Environment / Config Preflight
- exact environment variables/secrets required for this Step's target
  environment, and confirmation each is present/valid before proceeding;
- dependent services' health confirmed before this Step begins;
- capacity/disk/resource checks relevant to this Step's action;
- config drift check: target environment's current config compared against
  what this Step expects.

### Migration / Rollback Readiness
(Include if this Step applies a database/schema/data migration.)
- exact migration(s) this Step applies, forward-only unless rollback is
  explicitly planned;
- backward compatibility of the migration with the currently-deployed code
  during a rolling/staged deploy;
- backup/restore point captured before an irreversible migration;
- rollback procedure for the migration specifically (down-migration
  command, or restore-from-backup if not cleanly reversible), verified via
  a dry run against a non-production copy where feasible.

### Observability (Health Checks, Smoke Tests, Logs/Metrics/Traces Post-Deploy)
- health check endpoint(s)/command(s) this Step verifies, and the expected
  healthy response;
- smoke tests this Step runs post-action (critical API, auth/login, core
  user path, background jobs, external integrations, as applicable) and
  their expected result;
- metrics/logs/traces this Step's action must be visible in (error rate,
  latency, saturation, job failures, DB health, external-provider
  failures) — name the exact dashboard/query used to check them, not just
  "monitor";
- correlation identifier (deploy/run id) used to trace this Step's action
  across logs/metrics.

## Required Test Matrix

In addition to each Task's own checks, list Step-level checks that exercise
more than one Task together (e.g. full deploy -> smoke test -> rollback
rehearsal path; migration dry run against a staging copy before the
production Task runs).

Destructive or production-affecting checks must be dry-run/staging-rehearsed
first; report explicitly which checks were run against production versus a
non-production environment.

## Manual Verification

<Anything automated checks cannot fully cover — visual dashboard review,
manual smoke-test click-through, on-call handoff confirmation.>

## Acceptance Criteria

- [ ] ...
- [ ] ...

## Implementation Review Checklist

> This Step's Definition of Done differs from a typical code Step per
> `shared/STEP_EXECUTION_PROTOCOL.md` — "implementation" here means the
> deployment action was executed and independently verified, not that code
> was written. Baseline items below are adapted for release; release-specific
> items are added under the line.

- [ ] Existing environment/pipeline state was inspected before this Step's
      action.
- [ ] Only this Step's declared scope was executed (no unplanned production
      change).
- [ ] Environment/config was validated before the action, not assumed
      correct.
- [ ] Database/schema migrations (if any) are forward-compatible and tested
      via dry run before being applied to production.
- [ ] This Step's action does not block on unrelated long-running work.
- [ ] External commands/inputs (deploy scripts, config values) are
      validated, not string-concatenated.
- [ ] Timeouts and failure paths are explicit for every external call this
      Step makes (registry pull, deploy API, health check).
- [ ] Retry behavior (if this Step retries a deploy/migration step) cannot
      silently duplicate or corrupt state.
- [ ] Checks cover the success path and each meaningful failure, verified
      against real state, not only exit codes.
- [ ] Documentation/runbook was updated where this Step changed the
      deployment process.
- [ ] Every Acceptance Criterion for this Step is independently verified.
- [ ] `CURRENT.md` was updated only after verification, not before.
- [ ] No Task or action belonging to a later Step/Gate was started.
---
- [ ] A successful command/pipeline exit code was not treated as sufficient
      evidence — actual environment state was inspected.
- [ ] Rollback trigger and rollback procedure are defined and, for
      high-risk/irreversible actions, rehearsed before this Step is marked
      done.
- [ ] Smoke tests and health checks were actually run post-action, not
      only documented as a plan.
- [ ] `RELEASE_PLAN.md` matches what was actually executed (updated if
      reality diverged during execution).
- [ ] Observability signals (logs/metrics/traces) were checked live for
      this Step's action, not assumed healthy.

## Step Execution Protocol

> See `shared/STEP_EXECUTION_PROTOCOL.md` for the full A–E protocol. This
> Step's Definition of Done differs from a typical code Step: "Task Loop"
> means executing each deployment action and verifying resulting
> environment state, not writing and unit-testing code. This Step's
> Definition of Done additionally requires:

- every Task Execution Tracking row fully checked;
- this Step's own Acceptance Criteria and Implementation Review Checklist
  items verified against real environment state, not assumed;
- `RELEASE_PLAN.md` consistent with what was actually executed;
- `CURRENT.md` updated to reflect completion only after the above.

## Completion

PASS:
1. mark this Step complete in `CURRENT.md`;
2. advance Current Target;
3. write the completion report (per `shared/EXECUTION_RULES.md`);
4. STOP.

FAIL:
1. leave this Step incomplete;
2. do not advance Current Target;
3. report exact remediation needed — including whether a rollback was
   triggered and its result;
4. STOP.

Do not start the next Step or Gate in this invocation.
