# Bugfix Step B2 — Root Cause Analysis

## Target
- Step: B2
- Scope: **Only this Step**

## Required Reading

Before investigating, read:
- existing repo agent instructions;
- `BUG.md`;
- `CURRENT.md`;
- B1's completion report and captured evidence (failing test, logs, stack
  trace, DB/UI state, minimized reproduction case);
- the affected module's source and its current tests;
- the project's source-of-truth architecture/data-contract docs for the
  affected area, if any exist.

## Working Rule

This Step investigates causality — it does not implement a fix. Do not
change production behavior in this Step beyond a disposable, clearly
labeled diagnostic probe (e.g. a temporary log line or a scratch test) that
is removed or converted to a real regression test before this Step ends.

## Hard Rule

Do not proceed to B3 merely because a hypothesis sounds plausible.

The root cause must be a **falsifiable claim that was actually tested**, not
just argued for. It must be supported by evidence such as:

- a traced code path from trigger to failure;
- a controlled experiment with both a failing and a passing run;
- a state-transition proof;
- a log sequence that isolates the causal step;
- a minimal test that demonstrates causality (fails when the cause is
  present, passes when it is removed/mocked out);
- a configuration/data comparison between working and broken cases.

A hypothesis that merely "explains the symptom" without a test that could
have disproven it is not a confirmed root cause.

## Goal

Identify the actual root cause of the bug reproduced in B1, evidence-backed
and falsifiable, and define the minimal fix boundary B3 must operate within.

## Preconditions

B1 verified complete, with a reproduced (or documented-blocked) failure and
captured evidence available.

## Scope

### In Scope
- tracing the exact code path from trigger to failure;
- enumerating plausible hypotheses and eliminating unsupported ones with
  evidence;
- running a targeted experiment/test that confirms the surviving hypothesis;
- defining the minimal fix boundary (files/modules, behavior changed,
  behavior preserved, regression risk) for B3.

### Out of Scope
- implementing the fix (that is B3's job);
- any change to production behavior beyond a disposable diagnostic probe;
- broad refactors "while I'm in here."

## Investigate

<Precise description of the causal investigation this Step performs — the
"what," before the Task-by-Task "how" below. State the leading hypothesis
(if any) coming out of B1's evidence, and what remains unconfirmed.>

## Granular Execution Tasks

> Execute each Task in order and collect evidence before proceeding. Apply
> `shared/TASK_DECOMPOSITION_STANDARD.md`'s structure, with "Implementation"
> reframed as "Investigation" — a Task here produces a tested, falsifiable
> causal claim, not shipped behavior.

### Task 1 — Trace the Failure Path

#### Objective
Identify the exact code path from the triggering input/action to the
observed failure, using B1's evidence as the starting point.

#### Inspect Before Editing
- the exact module(s)/function(s) implicated by B1's stack trace, log
  sequence, or failing test;
- callers/call sites of the implicated code, so the trace does not stop at
  the first frame that merely surfaces the symptom rather than causes it;
- existing tests around the implicated path, to understand intended
  behavior before assuming it is wrong.

#### Investigation Contract
- accepted inputs: B1's reproduction case and captured evidence;
- output: a concrete, named sequence of code locations (file:function/line)
  from trigger to failure;
- invariant: the trace must reach the point where behavior first diverges
  from what is expected — not stop at the point where the divergence
  becomes visible (those are often different places).

#### Detailed Investigation Steps
1. re-run B1's minimized reproduction case to confirm it still fails
   identically before tracing;
2. starting from the stack trace/error, walk backward through the call
   chain to find each decision point (branch, external call, state
   mutation) the failing execution passed through;
3. at each decision point, record the actual value/state observed versus
   what was expected;
4. identify the specific point where actual first diverges from expected —
   this is the candidate causal site, not necessarily the same as where
   the exception was thrown or the symptom was observed;
5. note any external dependency (DB state, config, timing, concurrency,
   third-party response) involved at the divergence point.

#### Failure / Recovery Cases
- **Trace does not converge on a single divergence point** (multiple
  plausible sites): category `trace-ambiguous`; log every candidate site
  with its evidence; not retryable without more targeted experiments;
  resulting state: carry all candidates into Task 2 rather than picking one
  arbitrarily.
- **Reproduction from B1 no longer reproduces when re-run**: category
  `repro-drift`; log what changed (environment, data, timing); resulting
  state: re-stabilize the reproduction before continuing, or fall back to
  B1's captured evidence artifacts if live re-reproduction is not possible.

#### Task-Level Test/Verification Cases
- the traced path is expressed as concrete file:function references, not a
  narrative description;
- the divergence point (actual vs. expected) is stated explicitly at each
  decision point recorded.

#### Evidence Required Before Checking This Task
- the concrete traced path (file:function/line sequence);
- the actual-vs-expected value/state at each decision point;
- PASS/FAIL: reproduction re-confirmed before tracing.

#### Task Done Condition
A concrete code-level trace from trigger to the candidate divergence
point(s) is recorded, backed by actual-vs-expected values at each step —
not a plausible-sounding narrative.

### Task 2 — Form and Evaluate Hypotheses

#### Objective
Enumerate plausible causes for the divergence point(s) found in Task 1, and
eliminate every hypothesis not supported by evidence.

#### Inspect Before Editing
- the divergence point(s) and their surrounding code/state from Task 1;
- any related historical bugs/commits touching the same code, if easily
  discoverable (e.g. `git log` / `git blame` on the implicated lines).

#### Investigation Contract
- accepted inputs: Task 1's candidate divergence point(s);
- output: a list of hypotheses, each marked eliminated (with the evidence
  that eliminated it) or surviving;
- invariant: each hypothesis must be stated as a falsifiable claim ("X
  causes Y because Z") — not a vague suspicion.

#### Detailed Investigation Steps
1. for each candidate divergence point, state the specific mechanism by
   which it could produce the observed symptom;
2. for each hypothesis, identify what evidence would confirm it and what
   evidence would rule it out — before running anything;
3. check existing evidence (from B1, from Task 1's trace) against each
   hypothesis first, before designing new experiments;
4. where existing evidence is insufficient, design the smallest targeted
   check (log addition, debugger inspection, scratch test) that
   discriminates between remaining hypotheses;
5. eliminate every hypothesis whose predicted evidence does not match what
   is actually observed; record why.

#### Failure / Recovery Cases
- **Two or more hypotheses remain equally supported**: category
  `hypotheses-tied`; log the evidence for each; not resolvable without
  Task 3's targeted experiment discriminating between them explicitly;
  resulting state: Task 3 must be designed to distinguish the tied
  hypotheses, not just confirm one of them in isolation.
- **No hypothesis survives initial evaluation**: category
  `no-surviving-hypothesis`; log every eliminated hypothesis and why;
  resulting state: return to Task 1 and re-trace with wider scope (e.g.
  include timing/concurrency/external state not previously considered)
  before declaring the cause unknown.

#### Task-Level Test/Verification Cases
- every hypothesis considered is listed, not only the winning one;
- each eliminated hypothesis has a stated reason tied to actual evidence,
  not intuition;
- the surviving hypothesis is stated as a specific, falsifiable claim.

#### Evidence Required Before Checking This Task
- the full hypothesis list with eliminated/surviving status and reasons;
- the specific evidence used to eliminate each ruled-out hypothesis.

#### Task Done Condition
A falsifiable, specific hypothesis survives explicit evaluation against
real evidence, with alternatives named and eliminated for stated reasons —
not merely the first plausible explanation found.

### Task 3 — Confirm Root Cause via Targeted Experiment

#### Objective
Run a targeted experiment/test that could have disproven the surviving
hypothesis, and did not.

#### Inspect Before Editing
- the surviving hypothesis and its predicted evidence from Task 2;
- existing test infrastructure/fixtures usable to construct the experiment
  without inventing unnecessary new scaffolding.

#### Investigation Contract
- accepted inputs: the surviving hypothesis from Task 2;
- output: a concrete experiment (test, script, controlled manual check)
  with both a failing run (cause present) and a passing/differing run
  (cause removed, mocked, or reverted) demonstrating the causal link;
- invariant: the experiment must be capable of failing — a check that
  would pass regardless of whether the hypothesis is true provides no
  evidence.

#### Detailed Investigation Steps
1. design the experiment so it isolates the candidate cause from other
   variables (change one thing at a time);
2. run the experiment with the candidate cause present — confirm it
   reproduces the failure;
3. run the same experiment with the candidate cause removed/altered/mocked
   — confirm the failure no longer occurs (or occurs differently in a way
   consistent with the hypothesis);
4. if either run does not match the predicted outcome, the hypothesis is
   not confirmed — return to Task 2;
5. record both runs' exact commands/output as evidence;
6. remove or convert any disposable diagnostic probe added during this
   investigation (temporary logs, scratch scripts) — keep only what
   becomes a real regression test candidate for B4.

#### Failure / Recovery Cases
- **Experiment result does not match the hypothesis's prediction**:
  category `hypothesis-disproven`; log both runs' actual output; not the
  root cause — return to Task 2 with this hypothesis marked eliminated and
  this evidence attached; resulting state: B2 remains incomplete until a
  new hypothesis is confirmed.
- **Experiment is only reproducible in one environment** (e.g. requires
  production data/timing not available locally): category
  `experiment-environment-limited`; log what was and wasn't reproducible
  where; resulting state: document the environment dependency explicitly as
  part of the confirmed cause, since B3's fix and B4's regression test must
  account for it too.

#### Task-Level Test/Verification Cases
- both the "cause present -> fails" and "cause absent -> passes/differs"
  runs are executed and recorded;
- the experiment is minimal — it isolates the candidate cause, not several
  changes at once.

#### Evidence Required Before Checking This Task
- exact experiment command(s)/script for both runs;
- PASS/FAIL for each run and whether the outcome matched the prediction;
- confirmation that disposable diagnostic probes were cleaned up.

#### Task Done Condition
A targeted experiment produced both a failing and a passing/differing run
consistent with the hypothesis's prediction — the root cause is confirmed
by a test that could have disproven it and did not.

### Task 4 — Define Minimal Fix Boundary

#### Objective
Translate the confirmed root cause into an explicit, minimal boundary that
B3's fix must stay within.

#### Inspect Before Editing
- the confirmed causal site's owning module and its direct callers/callees;
- any adjacent behavior sharing the same code path that must be preserved.

#### Investigation Contract
- accepted inputs: the confirmed root cause from Task 3;
- output: an explicit statement of files/modules the fix is expected to
  touch, the behavior that must change, the behavior that must be
  preserved, and the regression risk surface;
- invariant: the boundary must be the smallest one that actually addresses
  the confirmed causal site — not the smallest one that merely hides the
  symptom.

#### Detailed Investigation Steps
1. name the exact file(s)/function(s) the fix is expected to touch, based
   on the confirmed causal site (not the symptom's surface location, unless
   they are the same);
2. state precisely what behavior must change to eliminate the cause;
3. state precisely what behavior must NOT change (existing correct
   behavior sharing the same code path);
4. identify the regression risk surface — what else calls this code, what
   tests currently cover it, what could plausibly break;
5. confirm the boundary does not require an unrelated broad refactor; if it
   does, flag that explicitly rather than silently expanding scope in B3.

#### Failure / Recovery Cases
- **Minimal fix boundary would require touching unrelated broad
  architecture**: category `fix-boundary-too-wide`; log why a narrower fix
  is not possible; resulting state: document this explicitly in the
  completion report so it is a visible decision, not scope creep discovered
  mid-B3.

#### Task-Level Test/Verification Cases
- the boundary names concrete files/modules, not a vague area;
- "behavior preserved" is stated concretely enough that B3/B4 can verify it.

#### Evidence Required Before Checking This Task
- the written minimal fix boundary (files/modules, behavior changed,
  behavior preserved, regression risk).

#### Task Done Condition
An explicit, concrete minimal fix boundary is recorded and traceable to the
confirmed root cause, not to the symptom alone.

## Task Execution Tracking

| Task | Investigated | Evidence Captured | Reviewed | Verified |
|---|---|---|---|---|
| 1. Trace the Failure Path | [ ] | [ ] | [ ] | [ ] |
| 2. Form and Evaluate Hypotheses | [ ] | [ ] | [ ] | [ ] |
| 3. Confirm Root Cause via Targeted Experiment | [ ] | [ ] | [ ] | [ ] |
| 4. Define Minimal Fix Boundary | [ ] | [ ] | [ ] | [ ] |

## Manual Verification

<Anything the automated experiment above cannot fully cover — e.g. manual
confirmation of a UI/timing-dependent causal step.>

## Acceptance Criteria

- [ ] root cause is evidence-backed by a falsifiable experiment that was
      actually run, not just argued for;
- [ ] alternative major hypotheses are named and explicitly eliminated with
      evidence;
- [ ] minimal fix boundary is explicit (files/modules, behavior changed,
      behavior preserved, regression risk);
- [ ] no broad unrelated refactor is required without explicit
      justification;
- [ ] any disposable diagnostic probes were removed or converted into real
      regression test candidates for B4.

## Implementation Review Checklist

> Adapted from `shared/STEP_EXECUTION_PROTOCOL.md`'s baseline for a causal
> investigation Step rather than an implementation Step.

- [ ] B1's reproduction was re-confirmed before tracing began.
- [ ] The trace reached the point of actual divergence, not just the
      point where the symptom became visible.
- [ ] Every hypothesis considered is recorded, with eliminated ones showing
      why.
- [ ] The confirmed hypothesis was tested with a run that could have
      disproven it, and both outcomes are recorded.
- [ ] No production behavior was changed in this Step beyond disposable,
      removed diagnostic probes.
- [ ] The minimal fix boundary is concrete enough for B3 to implement
      without re-deriving the investigation.
- [ ] `CURRENT.md` was updated only after verification, not before.
- [ ] No Task or file belonging to B3/B4 was started.

---

## Step Execution Protocol

> See `shared/STEP_EXECUTION_PROTOCOL.md` for the full A-E protocol,
> read here as causal investigation rather than implementation. This Step's
> Definition of Done additionally requires:

- every Task Execution Tracking row fully checked;
- this Step's Acceptance Criteria and Implementation Review Checklist
  items verified, not assumed;
- `CURRENT.md` updated to reflect completion only after the above.

## Completion

PASS:
1. mark B2 complete in `CURRENT.md`;
2. advance Current Target to B3;
3. write the completion report (per `shared/EXECUTION_RULES.md`), including
   the confirmed root cause, the experiment evidence, and the minimal fix
   boundary;
4. STOP.

FAIL (root cause remains uncertain, or evidence does not support a single
surviving hypothesis):
1. leave B2 incomplete;
2. do not advance Current Target;
3. report the eliminated hypotheses, the remaining uncertainty, and what
   additional evidence/experiment is needed;
4. STOP.

If root cause remains uncertain, do not advance to B3.
