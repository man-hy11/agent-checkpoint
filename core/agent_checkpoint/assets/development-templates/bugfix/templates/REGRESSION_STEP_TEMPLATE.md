# Bugfix Step B4 — Regression & Related Behavior

## Target
- Step: B4
- Scope: **Only this Step**

## Required Reading

Before verifying, read:
- existing repo agent instructions;
- `BUG.md`;
- `CURRENT.md`;
- B1's completion report (original reproduction, captured evidence);
- B2's completion report (confirmed root cause, minimal fix boundary);
- B3's completion report (fix implemented, regression test added, files
  changed);
- the project's `docs/TEST_STRATEGY.md` equivalent, if one exists.

## Working Rule

This Step verifies the fix holds and did not break neighboring behavior —
it does not change the fix. If verification uncovers a real defect, do not
patch it silently inside this Step; report it as a FAIL with the exact
remediation needed (typically: return to B3, or reopen B2 if the root cause
was mis-scoped).

## Goal

Confirm the B3 fix holds under the original reproduction, is protected by a
durable regression test, and did not break directly affected or adjacent
behavior.

## Preconditions

B3 verified complete: fix implemented, regression test passing, original
B1 reproduction passing.

## Scope

### In Scope
- re-running the original B1 reproduction one more time, independently;
- running the targeted regression suite for the directly affected
  module/interface;
- verifying important adjacent/neighboring behavior sharing the same code
  path (success path, error path, boundary values, backward compatibility,
  persistence/reload, as relevant to this bug);
- an operational check (logs/errors/state remain sane, no new unexplained
  warnings).

### Out of Scope
- modifying the fix itself;
- expanding the regression test's scope beyond what B3 already added,
  except to close a gap this Step's verification reveals — and if so, that
  gap must be reported, not silently patched past.

## Verify

<Precise description of what this Step confirms — the "what," before the
Task-by-Task "how" below. Name the directly affected module/interface and
the adjacent behaviors most at risk given B2's regression risk surface.>

## Granular Execution Tasks

> Execute each Task in order and collect evidence before proceeding. Apply
> `shared/TASK_DECOMPOSITION_STANDARD.md`'s structure, with "Implementation"
> reframed as "Verification" — a Task here confirms behavior, it does not
> change it.

### Task 1 — Re-run Original Reproduction

#### Objective
Independently re-confirm the original B1 reproduction no longer fails,
using the same minimized case B1 established.

#### Inspect Before Editing
- B1's final minimized reproduction case (test, script, or documented
  manual sequence).

#### Verification Contract
- accepted inputs: B1's minimized reproduction case;
- output: PASS/FAIL result plus the actual observed state, run
  independently of B3's own Task 3 verification;
- invariant: this must be a fresh run, not a reuse of B3's recorded output.

#### Detailed Verification Steps
1. locate B1's exact minimized reproduction case;
2. re-run it against the current (post-fix) code, fresh;
3. compare the result against `BUG.md`'s Expected Behavior;
4. if flaky reproduction was noted in B1, run enough times to confirm the
   flake is resolved, not just one lucky pass.

#### Failure / Recovery Cases
- **Original reproduction still fails**: category
  `fix-regression-verification-failed`; log the exact failure; not
  retryable by re-running — the fix is not actually complete; resulting
  state: this Step FAILs and reports that B3 must be revisited.
- **Reproduction was flaky and still shows the same flake rate**: category
  `fix-did-not-resolve-flake`; log the before/after flake rate; resulting
  state: FAIL — the fix did not address the confirmed cause if the cause
  was the source of the flake.

#### Task-Level Verification Cases
- fresh run of B1's minimized case: PASS, matching `BUG.md`'s Expected
  Behavior;
- if originally flaky: re-run count sufficient to show the flake rate
  dropped to zero (or to an explicitly accepted residual level).

#### Evidence Required Before Checking This Task
- exact command/steps re-run;
- PASS/FAIL and observed state;
- comparison against `BUG.md`'s Expected Behavior.

#### Task Done Condition
The original bug's reproduction case was independently re-run against the
current code and no longer exhibits the reported symptom.

### Task 2 — Targeted Regression Suite

#### Objective
Run the automated test suite for the directly affected module/interface,
including B3's new regression test, as a whole.

#### Inspect Before Editing
- the directly affected module's/interface's full test suite (not just the
  single new test).

#### Verification Contract
- accepted inputs: the current code including B3's fix and regression test;
- output: PASS/FAIL for the full targeted suite;
- invariant: this must exercise the suite as it is actually run in CI/build
  (the real command), not a hand-picked subset.

#### Detailed Verification Steps
1. identify the real test command used for the directly affected
   module/interface (per `docs/TEST_STRATEGY.md` or repo convention);
2. run it in full;
3. confirm B3's new/extended regression test is included and passes;
4. record any failure, including pre-existing ones — do not silently
   attribute a pre-existing failure to this fix, and do not silently
   dismiss a new one as pre-existing without checking.

#### Failure / Recovery Cases
- **A test outside B3's new one now fails**: category
  `regression-suite-broken`; log which test, its failure output, and
  whether it existed before B3's change (check git history/baseline if
  available); resulting state: if caused by the fix, FAIL and report back
  to B3; if genuinely pre-existing and unrelated, document explicitly with
  evidence it predates this fix.
- **Regression test suite itself cannot run** (broken tooling, missing
  dependency): category `suite-tooling-broken`; log the exact error;
  resulting state: FAIL — do not report Task 2 as passed without actually
  running the suite.

#### Task-Level Verification Cases
- full targeted suite run: PASS, or failures explicitly triaged as
  pre-existing and unrelated with supporting evidence.

#### Evidence Required Before Checking This Task
- exact suite command executed;
- PASS/FAIL with count of tests run/passed/failed;
- triage notes for any failure not caused by this fix.

#### Task Done Condition
The real targeted test suite (not a hand-picked subset) was run in full
and passes, or any failure is explicitly and evidentially triaged as
unrelated to this fix.

### Task 3 — Neighboring Behavior

#### Objective
Verify important adjacent behavior sharing the same code path as the fix,
per B2's regression risk surface.

#### Inspect Before Editing
- B2's stated regression risk surface (callers, shared code paths, related
  tests);
- B3's Cross-Cutting Contracts sections (Data/Persistence, API, Worker,
  Error Handling) to identify which adjacent behaviors are most exposed.

#### Verification Contract
- accepted inputs: B2's regression risk surface, B3's fix;
- output: explicit PASS/FAIL per relevant adjacent behavior checked;
- invariant: only behaviors actually sharing the fixed code path need
  checking — do not pad with unrelated areas of the app.

#### Detailed Verification Steps
1. from B2's regression risk surface, list the specific adjacent behaviors
   at risk (e.g. success path through the same function, error path
   through the same function, boundary values, backward compatibility with
   existing persisted data, persistence/reload behavior);
2. for each listed behavior, run or exercise it and record actual result;
3. prioritize behaviors that share code with the fixed path over unrelated
   areas — this is not a full regression sweep of the whole application;
4. if the fix touched persisted data/schema, verify existing (pre-fix)
   data still loads/behaves correctly.

#### Failure / Recovery Cases
- **An adjacent behavior on the same code path is now broken**: category
  `neighboring-behavior-regressed`; log which behavior, expected vs.
  actual; resulting state: FAIL — report back to B3, since the fix's
  boundary was evidently not as minimal/safe as intended.
- **Backward compatibility with existing persisted data is broken**:
  category `data-compat-regressed`; log the specific data shape that no
  longer works; resulting state: FAIL — this is treated as a new,
  potentially more severe defect than the original bug and must block Gate
  entry.

#### Task-Level Verification Cases
- each adjacent behavior identified from B2's regression risk surface: PASS;
- backward compatibility with pre-existing data (if applicable): PASS.

#### Evidence Required Before Checking This Task
- the list of adjacent behaviors checked and their individual results;
- any backward-compatibility check performed and its result.

#### Task Done Condition
Every adjacent behavior identified in B2's regression risk surface was
actually exercised (not assumed) and passes, including backward
compatibility with existing data where relevant.

### Task 4 — Operational Check

#### Objective
Confirm logs/errors/state remain sane after the fix — no new unexplained
warnings or error noise introduced.

#### Inspect Before Editing
- the logging/observability conventions already used near the fixed code
  (per B3's Logging/Observability notes, if present).

#### Verification Contract
- accepted inputs: a real run of the fixed path (from Task 1 or Task 3);
- output: confirmation that logs/errors emitted during a real run are
  expected, not new unexplained noise;
- invariant: this is inspected from an actual run's output, not assumed
  from reading the diff.

#### Detailed Verification Steps
1. capture logs/console/error output from one of the real runs already
   performed in Task 1 or Task 3;
2. compare against what was logged before the fix (if available) or against
   expected logging behavior for this path;
3. confirm no new unexplained error/warning appears;
4. confirm any correlation identifiers (request/job/user id) used by this
   path are still present and correct.

#### Failure / Recovery Cases
- **New unexplained warning/error appears in logs**: category
  `unexplained-log-noise`; log the exact new output; resulting state: FAIL
  if the cause is unclear or looks like a masked problem — investigate
  before Gate entry rather than dismissing it.

#### Task-Level Verification Cases
- logs/console output from a real run of the fixed path contain no new
  unexplained error/warning.

#### Evidence Required Before Checking This Task
- the captured log/console output inspected;
- confirmation of no new unexplained noise, or explanation if noise is
  expected and benign.

#### Task Done Condition
Logs/errors/state from a real run of the fixed path were actually
inspected and contain no new unexplained warning/error.

## Task Execution Tracking

| Task | Verified Behavior | Evidence Captured | Reviewed | Verified |
|---|---|---|---|---|
| 1. Re-run Original Reproduction | [ ] | [ ] | [ ] | [ ] |
| 2. Targeted Regression Suite | [ ] | [ ] | [ ] | [ ] |
| 3. Neighboring Behavior | [ ] | [ ] | [ ] | [ ] |
| 4. Operational Check | [ ] | [ ] | [ ] | [ ] |

## Required Test Matrix

In addition to each Task's own checks, use `docs/TEST_STRATEGY.md` (or
repo convention) to confirm the directly affected module/interface's full
suite and any integration/E2E fixtures relevant to the fixed path were
exercised — not only the single new regression test.

## Manual Verification

<Anything automated assertions cannot fully cover — visual state, UX
timing, cross-device behavior relevant to the fixed path or its neighbors.>

## Acceptance Criteria

- [ ] original bug remains fixed (fresh, independent re-run);
- [ ] regression test protects the case and runs as part of the real
      targeted suite;
- [ ] affected existing tests pass, or failures are explicitly triaged as
      pre-existing and unrelated;
- [ ] important adjacent behavior on the same code path passes;
- [ ] backward compatibility with existing data holds, where applicable;
- [ ] no unexplained new warning/error appears in a real run.

## Implementation Review Checklist

> Adapted from `shared/STEP_EXECUTION_PROTOCOL.md`'s baseline for a
> verification Step rather than an implementation Step.

- [ ] The original reproduction was independently re-run, not assumed from
      B3's own report.
- [ ] The real targeted test suite/command was run in full, not a
      hand-picked subset.
- [ ] Every adjacent behavior in B2's regression risk surface was actually
      exercised, not assumed safe.
- [ ] Backward compatibility with existing persisted data was checked when
      the fix touched persistence.
- [ ] Logs/errors from a real run were inspected, not assumed clean.
- [ ] No defect found during verification was silently patched inside this
      Step.
- [ ] `CURRENT.md` was updated only after verification, not before.
- [ ] No Task or file belonging to Bug Gate was started beyond what this
      Step's own verification required.

---

## Step Execution Protocol

> See `shared/STEP_EXECUTION_PROTOCOL.md` for the full A-E protocol, read
> here as verification rather than implementation. This Step's Definition
> of Done additionally requires:

- every Task Execution Tracking row fully checked;
- this Step's Acceptance Criteria and Implementation Review Checklist
  items verified, not assumed;
- `CURRENT.md` updated to reflect completion only after the above.

## Completion

PASS:
1. mark B4 complete in `CURRENT.md`;
2. advance Current Target to Bug Gate;
3. write the completion report (per `shared/EXECUTION_RULES.md`);
4. STOP.

FAIL:
1. leave B4 incomplete;
2. do not advance Current Target;
3. report exact remediation needed (return to B3, or reopen B2 if the root
   cause was mis-scoped);
4. STOP.

Do not start the Bug Gate in this invocation.
