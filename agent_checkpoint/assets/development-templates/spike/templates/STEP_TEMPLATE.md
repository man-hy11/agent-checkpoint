# Spike / Research / POC Step <ID> — <TITLE>

## Target
- Step: <ID>
- Scope: **Only this Step**

## Goal

<Precise research goal — one or two sentences, not a restated title. A
Spike Step produces evidence and narrows a decision; it does not ship
production behavior.>

## Preconditions

<Which earlier Step(s)/Gate must already be verified complete — e.g. the
question and decision criteria (S1) must be recorded before experiments
(S3) begin.>

## Required Reading / Existing System Inspection

Before experimenting, read:
- repository agent instructions (`AGENTS.md` / `CLAUDE.md`);
- this work package's `WORK.md`;
- `CURRENT.md`;
- `DECISION_RECORD.md` (this Step must extend, not contradict, the
  recorded Question and Decision Criteria — if the question needs to
  change, update `DECISION_RECORD.md` first and note why);
- any existing prior art in the repository relevant to the question (prior
  spikes, existing partial implementations, related ADRs) — do not
  re-investigate what is already answered;
- relevant external documentation for each alternative under
  consideration.

## Working Rule

Investigate only this Step's bounded question. If a further question is
relevant, leave a short TODO or note only — do not chase it. Time/scope-box
this Step's experiments per the work package's plan.

## Scope

### In Scope
- ...

### Out of Scope
- ...

## Investigate

<High-level shape of what this Step tries to learn — the "what," before the
Task-by-Task "how" below. E.g. "prototype approach A against the
representative workload and measure latency," "compare library X and
library Y against the defined decision criteria.">

## Granular Experiment Tasks

> Execute each Task (experiment) in order and collect evidence before
> proceeding. Spike Tasks adapt `shared/TASK_DECOMPOSITION_STANDARD.md`'s
> structure to bounded experiments — "Detailed Experiment Steps" replaces
> "Detailed Implementation Steps," and "Evidence Required" demands
> documented findings and uncertainty, not passing tests. Per
> `WORK_TYPE_HARD_RULES.md` (SPIKE): the goal is evidence and a decision,
> not production implementation — prototype code is disposable unless
> separately promoted through a normal implementation plan.

### Task 1 — <imperative, specific experiment>

#### Objective
One sentence: what question this experiment alone must answer (e.g.
"measure whether approach A meets the p95 latency requirement under a
representative load").

#### Inspect Before Editing
- exact scratch/prototype location this experiment writes to — keep
  prototype code physically separated from production paths (e.g. a
  `spikes/` or `experiments/` directory, or an isolated branch/worktree),
  never mixed into application modules;
- confirm this experiment is not duplicating a prior spike's already-answered
  question — check `DECISION_RECORD.md` and any earlier Steps first.

#### Experiment Contract
- exact question this experiment answers;
- inputs/setup (representative workload, dataset, environment) used to make
  the result meaningful, not a toy case that cannot generalize;
- the metric(s)/observable(s) that will be captured as the result;
- the decision criteria (from `DECISION_RECORD.md`) this experiment's
  result feeds into;
- explicit time/scope box for this experiment (e.g. "no more than N hours,"
  "prototype only the critical path, not full feature parity").

#### Detailed Experiment Steps
Numbered, concrete steps — not restatement of the Objective. Include, where
applicable:
1. confirm the Experiment Contract above, including the time/scope box,
   before starting;
2. build the minimum prototype/harness needed to produce the target
   metric/observable — do not build more than the bounded question
   requires;
3. keep prototype code isolated from production code paths so it cannot be
   silently promoted or accidentally wired into real behavior;
4. run the experiment against a representative case, not only the easiest
   case;
5. capture the result with enough detail to be independently checked later
   (raw output, not just a verbal conclusion);
6. record what did **not** work and why, with the same rigor as what did —
   a negative result is evidence, not a wasted experiment;
7. record uncertainty explicitly: what this experiment does not tell you,
   what would need to be tested further to be confident;
8. if the experiment reveals the original question needs to change, note
   that in `DECISION_RECORD.md` rather than silently pivoting;
9. stop at the time/scope box even if the result is inconclusive — record
   it as inconclusive rather than open-endedly continuing.

#### Failure / Recovery Cases
For a spike, "failure" typically means the experiment could not produce a
usable result, not a production error. List each realistic way this
experiment could fail to answer its question:
- failure mode (e.g. environment could not be set up, representative data
  unavailable, approach fundamentally infeasible, time-boxed out before
  conclusive);
- what was learned from the failure anyway (a blocked approach is itself a
  finding — record it in `DECISION_RECORD.md`'s Findings or Alternatives
  Considered, not discarded silently);
- whether the failure is fatal to the alternative being tested or merely
  means this experiment's method needs revision;
- cleanup: prototype artifacts/scratch resources are removed or clearly
  marked disposable, not left in a state that could be mistaken for
  production-ready.

#### Task-Level Evidence Captured
- the experiment's actual output/measurement (not a summary written from
  memory);
- comparison against the decision criteria this experiment targets;
- explicit uncertainty/limitations of this result;
- whether the result was reproduced more than once if variance is a
  concern.

#### Evidence Required Before Checking This Task
- exact command(s)/setup used to run the experiment;
- raw result/output captured (log, benchmark numbers, screenshot, sample
  output — whatever makes the finding independently checkable);
- findings written into `DECISION_RECORD.md`'s Experiments table and
  Findings/Uncertainty sections;
- any deviation from this experiment's contract or time-box and why it was
  necessary.

#### Task Done Condition
The bounded question is answered with captured, independently-checkable
evidence (or explicitly recorded as inconclusive within the time-box), the
finding — positive or negative — is recorded in `DECISION_RECORD.md`, and
any prototype code is clearly isolated and marked disposable. A vague
verbal conclusion without captured evidence does not satisfy this
condition, and neither does silently leaving prototype code positioned as
if it were production-ready.

<!-- Repeat Task N for every additional experiment this Step requires. -->

## Task Execution Tracking

| Experiment | Run | Findings Recorded | Evidence | Verified |
|---|---|---|---|---|
| 1. <name> | [ ] | [ ] | [ ] | [ ] |

## Cross-Cutting Contracts

> Most `shared/CROSS_CUTTING_CONTRACTS.md` sections do not apply to spike
> work — there is normally no production API/data model/worker contract
> being introduced. Keep this section minimal. Focus on documenting what
> was tried and what was learned rather than production contracts.

### What Was Tried
- approaches/alternatives actually attempted in this Step, referencing the
  Experiment Tasks above;
- any approach considered but not attempted, and why (out of scope,
  ruled out by an earlier finding, time-boxed out).

### What Was Learned
- concrete findings this Step produced, mapped to the decision criteria in
  `DECISION_RECORD.md`;
- uncertainty/unknowns that remain after this Step.

### Productionization Boundary
- explicit statement that prototype code from this Step is `DISPOSABLE` or
  `CANDIDATE_FOR_REIMPLEMENTATION` (per `DECISION_RECORD_TEMPLATE.md`) —
  never silently treated as production-ready;
- if any prototype artifact must persist temporarily for later reference,
  name its location and that it is excluded from production build/deploy
  paths.

(Include Configuration/Environment only if this Step's experiment required
a real credential/environment setup — e.g. a sandbox account to test
feasibility — and note any secret handling the same way an integration Step
would.)

## Required Test Matrix

Not applicable in the usual sense — a spike does not ship tested production
code. Instead, list here how this Step's findings could be independently
re-verified later (e.g. "re-run `experiments/approach-a/benchmark.py`
against the same dataset to reproduce the latency numbers").

## Manual Verification

<Anything not captured by an automated measurement — a manual
walkthrough of a prototype UI, a subjective assessment of developer
ergonomics, a manual read of an unfamiliar library's source.>

## Acceptance Criteria

- [ ] ...
- [ ] ...

## Implementation Review Checklist

> This Step's Definition of Done differs from a typical code Step per
> `shared/STEP_EXECUTION_PROTOCOL.md` — the deliverable is evidence and a
> narrowed decision, not passing production tests. Baseline items below are
> adapted for spike work; spike-specific items are added under the line.

- [ ] Existing prior art/repository context was inspected before starting
      new experiments.
- [ ] Only this Step's declared bounded question was investigated.
- [ ] Any new scratch/prototype code is physically isolated from
      production paths.
- [ ] Experiments ran against a representative case, not only a toy case.
- [ ] Time/scope boxes were respected; an inconclusive result was recorded
      as such rather than extended indefinitely.
- [ ] Findings — positive and negative — are captured with independently
      checkable evidence, not verbal summaries alone.
- [ ] Documentation (`DECISION_RECORD.md`) was updated where this Step
      changed the question, criteria, or known alternatives.
- [ ] Every Acceptance Criterion for this Step is independently verified.
- [ ] `CURRENT.md` was updated only after verification, not before.
- [ ] No Task or experiment belonging to a later Step/Gate was started.
---
- [ ] Prototype code is explicitly marked `DISPOSABLE` or
      `CANDIDATE_FOR_REIMPLEMENTATION` — it was not silently left in a
      state that could be mistaken for production-ready.
- [ ] Uncertainty/unknowns are explicitly recorded, not implied away by an
      optimistic summary.
- [ ] Findings are traceable back to the decision criteria in
      `DECISION_RECORD.md`, not disconnected observations.

## Step Execution Protocol

> See `shared/STEP_EXECUTION_PROTOCOL.md` for the full A–E protocol. For a
> spike, "Task Loop" means running each bounded experiment and recording
> its evidence, not implementing and unit-testing code; "Definition of Done"
> means the question is answered (or explicitly inconclusive) with
> evidence, not that tests pass. This Step's Definition of Done additionally
> requires:

- every Task Execution Tracking row fully checked;
- this Step's own Acceptance Criteria and Implementation Review Checklist
  items verified, not assumed;
- `DECISION_RECORD.md` updated with this Step's findings and any
  uncertainty before completion;
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
3. report exact remediation needed (e.g. experiment needs a different
   setup, question needs revision);
4. STOP.

Do not start the next Step or Gate in this invocation.
