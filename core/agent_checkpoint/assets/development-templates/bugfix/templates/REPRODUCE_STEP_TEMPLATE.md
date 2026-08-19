# Bugfix Step B1 — Reproduce & Capture Evidence

## Target
- Step: B1
- Scope: **Only this Step**

## Required Reading

Before investigating, read:
- existing repo agent instructions (`AGENTS.md`/`CLAUDE.md` equivalent);
- `BUG.md`;
- `CURRENT.md`;
- affected module docs and their current tests;
- relevant logs/issues/error reports if available;
- the project's source-of-truth architecture doc for the affected area, if one
  exists.

## Working Rule

This Step captures evidence — it does not implement a fix. Do not change
production behavior in this Step. If a fix seems obvious, note it in the
completion report and leave it for B3.

## Goal

Reproduce the reported bug, or establish the strongest available failure
evidence, with the environment/config/inputs required documented precisely
enough that B2 (Root Cause) and B4 (Regression) can re-run the same
reproduction.

## Preconditions

None — this is the first Step of the bugfix workflow.

## Scope

### In Scope
- confirming the environment/version/config needed to reproduce;
- reproducing the bug through the smallest reliable path;
- capturing failure evidence (stack trace, logs, API response, DB/UI state,
  artifact output) as relevant to the bug's surface;
- minimizing the reproduction to remove irrelevant variables;
- documenting an inability to reproduce, with concrete attempts, if that is
  the outcome.

### Out of Scope
- diagnosing *why* the failure happens (that is B2's job — this Step
  documents *what* happens and *when*);
- any production code change;
- any fix, workaround, or defensive patch, even a small one.

## Investigate

<Precise description of what evidence-gathering this Step performs — the
"what," before the Task-by-Task "how" below. State what is currently known
about the bug from `BUG.md` and what remains unconfirmed.>

## Granular Execution Tasks

> Execute each Task in order and collect evidence before proceeding. Apply
> `shared/TASK_DECOMPOSITION_STANDARD.md`'s structure, with "Implementation"
> reframed as "Investigation" — a Task here produces evidence, not shipped
> behavior. A Step that is genuinely one coherent reproduction effort may
> stay a single Task; do not split artificially.

### Task 1 — Confirm Reproduction Environment

#### Objective
Determine and record the exact version/commit, configuration, and
data/setup state required to attempt reproduction.

#### Inspect Before Editing
- `BUG.md`'s Environment and Known Reproduction Steps sections;
- current repo version/commit and any environment-specific config the
  affected module depends on;
- whether the reporting environment differs from the environment available
  for reproduction (e.g. production data shape vs. local/staging).

#### Investigation Contract
- accepted inputs: the reporter-supplied environment/config/data description;
- output: a recorded, concrete environment description sufficient for
  another invocation to repeat the same attempt;
- invariant: no production or shared environment is mutated destructively to
  chase reproduction.

#### Detailed Investigation Steps
1. read `BUG.md`'s Environment and Known Reproduction Steps fields;
2. identify the exact version/commit, runtime, OS/browser/device, and config
   flags relevant to the reported symptom;
3. identify what data/setup state is required (fixtures, account state, file
   inputs, feature flags);
4. if the required environment/data is unavailable, record exactly what is
   missing rather than approximating silently;
5. record the confirmed environment in the completion report / evidence
   artifact.

#### Failure / Recovery Cases
- **Required environment/data unavailable**: category
  `environment-unavailable`; internal log context: what was requested vs.
  what exists; not retryable without acquiring the missing environment;
  no cleanup needed; resulting state: this Task stops and the completion
  report names the exact blocker — do not proceed to guess at Task 2 with an
  unconfirmed environment.
- **Environment description in `BUG.md` is ambiguous/contradictory**:
  category `ambiguous-report`; log the discrepancy; not retryable
  automatically; resulting state: proceed with the best-supported reading
  and flag the ambiguity explicitly in evidence.

#### Task-Level Test/Verification Cases
- the confirmed environment matches at least one of: reporter-supplied
  version, currently checked-out commit, or an explicitly documented
  substitute;
- any gap between the ideal and the available environment is written down,
  not silently assumed away.

#### Evidence Required Before Checking This Task
- exact environment/version/config/data recorded;
- PASS/FAIL: environment confirmed or blocker documented;
- any deviation from the reporter's stated environment and why.

#### Task Done Condition
The environment needed for reproduction is either confirmed and recorded,
or its unavailability is documented as an explicit blocker — not silently
assumed.

### Task 2 — Reproduce via Smallest Reliable Path

#### Objective
Trigger the reported failure using the smallest reliable sequence of
actions/inputs.

#### Inspect Before Editing
- existing tests near the affected module that already exercise similar
  paths — reuse their setup/fixtures where possible instead of inventing
  new scaffolding;
- any existing repro script/harness in the repo before writing a new one.

#### Investigation Contract
- accepted inputs: the confirmed environment from Task 1, `BUG.md`'s Known
  Reproduction Steps;
- output: either an observed failure matching the reported symptom, or a
  documented set of attempts that did not reproduce it;
- invariant: reproduction attempts must not leave the working tree with
  uncommitted fix code.

#### Detailed Investigation Steps
1. follow `BUG.md`'s Known Reproduction Steps first, exactly as stated;
2. if that does not reproduce, vary one input/condition at a time and record
   each attempt and its outcome (do not vary several factors at once — that
   destroys the ability to isolate the cause later);
3. prefer an automated reproduction (failing test, script, API call) over a
   manual one when practical, since B2/B4 will need to re-run it;
4. if reproduction is flaky, run it enough times to characterize the
   flake rate rather than reporting a single run;
5. stop as soon as the failure is reliably triggered — do not over-explore.

#### Failure / Recovery Cases
- **Bug does not reproduce after documented, varied attempts**: category
  `repro-not-achieved`; log every attempt (input, expected, actual); not
  retryable without new information from the reporter; resulting state:
  Acceptance Criteria are satisfied via "inability to reproduce is
  documented with concrete attempts" — do not fabricate a reproduction.
- **Reproduction is intermittent/flaky**: category `repro-flaky`; log
  observed pass/fail ratio over N attempts and any correlating factor
  (timing, ordering, concurrency, cache state); retryable — flag for B2 to
  investigate the flake as part of root cause; resulting state: proceed to
  Task 3 using the failing runs as evidence, but explicitly label the
  flake rate.
- **Reproduction requires an environment/data set that is unavailable**
  (e.g. production-only data, a paid external provider, a specific
  third-party outage): category `repro-environment-blocked`; log what is
  missing and what was substituted, if anything; not retryable without
  access; resulting state: document the blocker in the completion report
  and propose the closest available substitute evidence (e.g. logs from
  the reporter, a synthetic approximation) rather than blocking indefinitely.

#### Task-Level Test/Verification Cases
- the reproduction path is reduced to the smallest set of steps/inputs that
  still triggers the symptom;
- if flaky, the flake rate is characterized (e.g. "3/10 runs failed");
- if not reproduced, every distinct attempt is listed with its outcome.

#### Evidence Required Before Checking This Task
- exact steps/commands/inputs used to attempt reproduction;
- PASS/FAIL/FLAKY result, with counts if flaky;
- any deviation from `BUG.md`'s reported steps and why.

#### Task Done Condition
The bug is reliably reproduced via the smallest known path, or a flaky/
partial reproduction is characterized with real run counts, or non-
reproduction is documented with concrete varied attempts — never a single
unexamined "could not repro."

### Task 3 — Capture Failure Evidence

#### Objective
Capture concrete, inspectable evidence of the failure as it actually
occurred during Task 2's reproduction.

#### Inspect Before Editing
- existing logging/observability conventions in the repo (correlation IDs,
  log format) so captured evidence is consistent with them;
- existing test output/artifact conventions for where evidence should live.

#### Investigation Contract
- accepted inputs: the triggered failure state from Task 2;
- output: a durable evidence artifact (failing test output, saved log
  excerpt, stack trace, API response body/status, DB row/state snapshot,
  UI/browser state or screenshot, artifact/file output) attached to this
  Step's evidence, not only described in prose;
- invariant: evidence capture must not itself alter the failure state
  before it is captured (e.g. do not "fix and re-run" before saving output).

#### Detailed Investigation Steps
1. capture the failing test output or exact command output verbatim;
2. capture the exception/stack trace in full, not a paraphrase;
3. capture the relevant API request/response (status code, body) if the bug
   is API-observable;
4. capture relevant log lines with their correlation identifiers (request/
   job/user id) if the bug is observable via logs;
5. capture DB/persisted state relevant to the failure (row values, not just
   "the record looked wrong");
6. capture browser/UI state (console errors, network tab, screenshot) if
   the bug is UI-observable;
7. capture artifact/file output (or its absence) if the bug is
   artifact-producing;
8. record expected vs. actual for each piece of captured evidence explicitly.

#### Failure / Recovery Cases
- **Evidence capture tooling itself fails** (e.g. logging disabled in this
  environment, screenshot tool unavailable): category `evidence-tooling-gap`;
  log what was attempted and what substitute was used instead; not
  retryable without tooling; resulting state: use the next-best available
  evidence and note the gap explicitly rather than leaving the Task with no
  evidence at all.
- **Captured evidence is inconsistent between runs** (e.g. different stack
  trace each time): category `evidence-inconsistent`; log each distinct
  variant observed; resulting state: hand all variants to B2 rather than
  picking one arbitrarily.

#### Task-Level Test/Verification Cases
- at least one piece of captured evidence directly demonstrates the
  reported symptom (not an adjacent or unrelated failure);
- expected vs. actual behavior is stated explicitly, not left implicit in
  a log dump;
- evidence is attached/saved, not only summarized in prose.

#### Evidence Required Before Checking This Task
- exact artifacts captured (paths, log excerpts, response bodies, etc.);
- PASS/FAIL: evidence obtained matches the reported symptom;
- any inconsistency observed across runs.

#### Task Done Condition
Concrete, inspectable evidence of the failure is captured and attached,
with expected vs. actual made explicit — not a prose restatement of the bug
report.

### Task 4 — Minimize and Finalize Reproduction Case

#### Objective
Reduce the reproduction to remove irrelevant variables and produce a final,
reusable reproduction case for B2 and B4.

#### Inspect Before Editing
- the reproduction path and evidence from Tasks 2-3.

#### Investigation Contract
- accepted inputs: the working reproduction and captured evidence;
- output: a minimal, named reproduction case (test name, script, or
  documented manual sequence) that B2 and B4 can re-run verbatim;
- invariant: minimizing must not change *what* fails, only remove
  unnecessary steps/inputs.

#### Detailed Investigation Steps
1. remove steps/inputs one at a time, re-confirming the failure still
   occurs after each removal;
2. stop removing as soon as removing further steps stops reproducing the
   bug or changes its character;
3. name/save the final minimized reproduction case so it is re-runnable
   (e.g. a specific failing test, a documented curl command, a specific UI
   sequence);
4. re-run the minimized case once more to confirm it still reproduces
   before finalizing.

#### Failure / Recovery Cases
- **Minimization changes the failure's character** (e.g. removing a step
  makes a different error appear): category `minimization-drift`; log the
  point at which the failure changed; resulting state: back up to the last
  step that reproduced the original symptom and stop there — do not report
  a minimized case that reproduces a different bug.

#### Task-Level Test/Verification Cases
- the final minimized case reproduces the same symptom captured in Task 3
  when re-run;
- the minimized case is concrete enough to hand to another invocation
  without re-deriving it.

#### Evidence Required Before Checking This Task
- the final minimized reproduction steps/command;
- PASS/FAIL on re-running the minimized case;
- what was removed during minimization.

#### Task Done Condition
A minimal, named, re-runnable reproduction case exists and was re-confirmed
to still trigger the original symptom.

## Task Execution Tracking

| Task | Investigated | Evidence Captured | Reviewed | Verified |
|---|---|---|---|---|
| 1. Confirm Reproduction Environment | [ ] | [ ] | [ ] | [ ] |
| 2. Reproduce via Smallest Reliable Path | [ ] | [ ] | [ ] | [ ] |
| 3. Capture Failure Evidence | [ ] | [ ] | [ ] | [ ] |
| 4. Minimize and Finalize Reproduction Case | [ ] | [ ] | [ ] | [ ] |

## Manual Verification

<Anything the automated capture above cannot fully cover — visual UI state,
timing-sensitive behavior, cross-device behavior.>

## Acceptance Criteria

- [ ] bug is reproduced OR inability to reproduce is documented with
      concrete, varied attempts;
- [ ] failure evidence is captured and attached (not only described);
- [ ] expected vs. actual behavior is explicit;
- [ ] the reproduction case is minimized and named/re-runnable;
- [ ] no production fix has been implemented in this Step.

## Implementation Review Checklist

> Adapted from `shared/STEP_EXECUTION_PROTOCOL.md`'s baseline for an
> evidence-gathering Step rather than an implementation Step.

- [ ] Existing repo docs, tests, and prior evidence were inspected before
      new reproduction attempts.
- [ ] Only reproduction/evidence-capture was performed — no fix or
      workaround was implemented.
- [ ] Every reproduction attempt (successful or not) is recorded, not just
      the final one.
- [ ] Flaky reproduction is characterized with real run counts, not
      asserted as reliable on a single run.
- [ ] Captured evidence is attached as artifacts, not only summarized.
- [ ] Expected vs. actual behavior is stated explicitly.
- [ ] `CURRENT.md` was updated only after verification, not before.
- [ ] No Task or file belonging to B2/B3/B4 was started.

---

## Step Execution Protocol

> See `shared/STEP_EXECUTION_PROTOCOL.md` for the full A-E protocol
> (Baseline -> Task Loop -> Step Integration -> Definition of Done -> Stop),
> read here as evidence-gathering rather than implementation. This Step's
> Definition of Done additionally requires:

- every Task Execution Tracking row fully checked;
- this Step's Acceptance Criteria and Implementation Review Checklist
  items verified, not assumed;
- `CURRENT.md` updated to reflect completion only after the above.

## Completion

PASS:
1. mark B1 complete in `CURRENT.md`;
2. advance Current Target to B2;
3. write the completion report (per `shared/EXECUTION_RULES.md`), including
   the final minimized reproduction case and captured evidence references;
4. STOP.

FAIL (bug could not be reproduced or blocked on missing environment/data):
1. leave B1 incomplete;
2. do not advance Current Target;
3. report the exact blocker and attempts made;
4. STOP.

Do not begin B2 Root Cause analysis work in this invocation beyond recording
observations needed for reproduction.
