# Release / Deployment Gate — <TITLE>

## Preconditions

All planned Release / Deployment Steps are verified complete in
`CURRENT.md`, and `RELEASE_PLAN.md` reflects what was actually executed.

## Gate Focus

Verify the deployment actually succeeded in the target environment — not
merely that deployment commands returned zero — including exact
artifact/version running, smoke tests passed against the live environment,
observability is live and showing healthy signal, and the rollback path is
proven, not just documented. Per `WORK_TYPE_HARD_RULES.md` (RELEASE): "A
successful build is not a successful release."

## Verify

> See `shared/GATE_STANDARD.md`. Include only sections relevant to what this
> release actually shipped; do not leave a relevant section as `...`.

### Functional — Deployment Actually Succeeded
- every Step's Acceptance Criteria still hold when the full deploy sequence
  is reviewed end-to-end, not only individually;
- the exact artifact/version/commit recorded in `RELEASE_PLAN.md` is what
  is actually running in the target environment — verify via a live
  version/health endpoint or deployment API, not by re-reading the deploy
  script;
- no unplanned/out-of-scope change reached the target environment alongside
  this release.

### Smoke Tests — Executed, Not Just Planned
- each smoke test listed in `RELEASE_PLAN.md` was actually run against the
  live target environment after deploy, with its actual result recorded
  (health, critical API, login/auth, core user path, background jobs,
  external integrations, as applicable);
- a failing or skipped smoke test blocks Gate PASS — it is not sufficient
  that the smoke test exists.

### Rollback Path — Proven, Not Just Documented
- the rollback procedure in `RELEASE_PLAN.md` was rehearsed (dry run,
  staging rehearsal, or canary rollback) at some point in this release's
  Steps, and that evidence is available — not merely a written procedure
  that was never exercised;
- rollback trigger thresholds are concrete and observable (specific
  metric/threshold), not vague ("if something looks wrong");
- if this release included a migration, confirm the migration's rollback
  or restore path was actually validated against a non-production copy.

### Data / State
- schema/migrations for this release are applied and consistent in the
  target environment — verify the actual migration table/version, not the
  migration file list;
- existing data is confirmed intact post-migration (spot-check or count
  comparison, as appropriate);
- ...

### Security / Permissions
- secrets/config used for this deploy are the intended environment's
  values, not leaked from another environment;
- no credentials appear in deployment logs or CI output;
- ...

### Failure / Recovery
- each Step's rollback trigger/procedure still holds when reviewed against
  the fully deployed system, not only in isolation per-Step;
- ...

### Cross-Step Regression
- pre-existing critical paths unrelated to this release still function
  post-deploy (representative smoke coverage, not a full regression suite
  unless the release plan calls for it);
- ...

### Backward Compatibility
- clients/consumers on the previous version (if a rolling/staged deploy)
  continue to function during and after the transition;
- ...

### Observability — Live, Not Assumed
- error rate, latency, saturation, job failures, DB health, and
  external-provider failure signals are checked in the real
  monitoring/dashboard tool post-deploy, with the actual observed values
  recorded — not assumed healthy because no alert fired;
- correlation/deploy-run identifiers are visible in logs/traces for this
  release's actual traffic;
- on-call/ownership is confirmed aware the release shipped, if the
  project's process requires it.

## Representative End-to-End

```text
deploy trigger (CI run / deploy command, with run ID)
-> artifact/version confirmed live in target environment
-> smoke tests executed against live environment
-> observability signals checked (error rate, latency, health)
-> rollback readiness confirmed (rehearsed, not just documented)
-> surrounding/earlier functionality still works
```

## Required Evidence

- exact tests/commands/pipeline runs executed, with run IDs/links;
- actual state/artifacts inspected (live version endpoint response, smoke
  test output, dashboard values, migration table state) — not just process
  exit codes;
- PASS/FAIL per verification area above;
- rollback rehearsal evidence (when/how it was exercised);
- unresolved issues, explicitly named.

## Gate Failure

If the Gate reveals a defect:

1. do not mark the Gate complete;
2. do not patch large unrelated code inside the Gate — only tiny
   verification-only corrections are permitted, and only if this Gate
   explicitly allows them;
3. if the deployed state is unsafe, trigger the rollback procedure and
   record its result before anything else;
4. identify the required remediation as a new/reopened Step;
5. record evidence;
6. STOP.

## Gate PASS

1. mark the Release / Deployment Gate complete in `CURRENT.md`;
2. write the final work summary (per `shared/EXECUTION_RULES.md`), including
   the exact shipped version/artifact and observability baseline recorded
   at Gate time;
3. STOP.

Do not start unrelated follow-on work in this invocation.
