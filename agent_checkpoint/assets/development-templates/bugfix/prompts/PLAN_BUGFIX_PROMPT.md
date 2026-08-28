Use the supplied **AI Development Templates / Bugfix Template** to plan this bug investigation and fix in the existing repository.

Do not implement the fix yet.

First inspect:

- existing repository agent instructions;
- affected architecture/modules;
- existing tests;
- relevant logs/errors;
- user-provided reproduction details;
- version/config/environment.

Create an independent package such as:

```text
changes/BUG-YYYY-NNN-<slug>/
```

Create:

- `BUG.md`
- `CURRENT.md`
- detailed bugfix Steps;
- `gate.md`
- `FIRST_RUN_PROMPT.md`
- `CONTINUE_PROMPT.md`

Default Step structure:

```text
B1 Reproduce & Capture Evidence
B2 Root Cause Analysis
B3 Minimal Fix
B4 Regression & Related Behavior
Bug Gate
```

Adjust the number of Steps only when complexity requires it.

Rules:

1. dependency-order the Steps: B1 must precede B2, B2 must precede B3, B3
   must precede B4, B4 must precede Bug Gate;
2. every B1 (Reproduce) Step must follow
   `templates/REPRODUCE_STEP_TEMPLATE.md` in full — do not emit a thin
   summary. It needs:
   - Required Reading and explicit In/Out of Scope;
   - Tasks broken out per `shared/TASK_DECOMPOSITION_STANDARD.md`, adapted
     to investigation/evidence-capture (Objective, Inspect Before Editing,
     Investigation Contract, numbered Detailed Investigation Steps,
     Failure/Recovery Cases, Task-Level Test/Verification Cases, Evidence
     Required, Task Done Condition) — the Task work is capturing evidence,
     never implementing a fix;
   - a Task Execution Tracking table (a genuinely single-Task reproduction
     effort may stay one Task — do not split artificially);
   - the Implementation Review Checklist adapted for an evidence-gathering
     Step;
3. every B2 (Root Cause) Step must follow
   `templates/ROOT_CAUSE_STEP_TEMPLATE.md` in full. It needs:
   - Tasks broken out per `shared/TASK_DECOMPOSITION_STANDARD.md`, adapted
     to causal investigation (trace the failure path, form and evaluate
     hypotheses, confirm the surviving hypothesis via a targeted, falsifiable
     experiment, define the minimal fix boundary);
   - Evidence Required for each Task must demonstrate the hypothesis was
     actually tested and could have been disproven, not merely plausible;
   - alternative hypotheses named and explicitly eliminated with evidence;
   - an explicit minimal fix boundary (files/modules, behavior changed,
     behavior preserved, regression risk) handed to B3;
4. the B3 (Fix) Step must follow `templates/FIX_STEP_TEMPLATE.md` in full —
   full Task decomposition per `shared/TASK_DECOMPOSITION_STANDARD.md`
   (regression test first, then implement, then focused verification, then
   inspect resulting state) plus the relevant sections of
   `shared/CROSS_CUTTING_CONTRACTS.md` (Data/Persistence, API Contract,
   Worker/Background Contract, Configuration, Error Handling Matrix,
   Logging/Observability) filled in for whatever the fix actually touches —
   omit sections the fix does not touch rather than padding them. Keep the
   fix itself minimal and aligned to B2's confirmed cause per
   `shared/WORK_TYPE_HARD_RULES.md`'s BUGFIX rule;
5. every B4 (Regression) Step must follow
   `templates/REGRESSION_STEP_TEMPLATE.md` in full. It needs:
   - Tasks broken out per `shared/TASK_DECOMPOSITION_STANDARD.md`, adapted
     to verification (independent re-run of the original reproduction,
     targeted regression suite, neighboring/adjacent behavior per B2's
     regression risk surface, operational/log check);
   - any defect found during verification reported as a FAIL with
     remediation pointing back to B3 or B2 — never patched silently inside
     B4;
6. the Bug Gate must follow `templates/BUG_GATE_TEMPLATE.md` in full, per
   `shared/GATE_STANDARD.md`: explicit verification subsections, a
   Representative End-to-End that repeats the original bug scenario and
   exercises at least one adjacent behavior, Required Evidence, explicit
   Gate Failure and Gate PASS procedures;
7. `CURRENT.md` is authoritative;
8. one invocation = one Bugfix Step or Bug Gate;
9. PASS -> advance CURRENT.md -> report -> STOP;
10. FAIL -> do not advance -> report remediation -> STOP;
11. when evidence is reasonably obtainable, do not enter Fix (B3) before
    Root Cause (B2) is evidence-backed by a falsifiable, actually-tested
    experiment — never a plausible-sounding hypothesis alone;
12. do not make broad unrelated refactors in any Step;
13. add/strengthen a regression test where practical, wired into the real
    test suite the project ordinarily runs, not a standalone script only;
14. do not implement the fix while creating this plan.

If reproduction is impossible due to missing environment/data, create an
explicit evidence-gathering/blocker path instead of guessing — document it
per `templates/REPRODUCE_STEP_TEMPLATE.md`'s Failure/Recovery Cases pattern
rather than fabricating a reproduction.

A Step that is thin because the underlying investigation/fix is genuinely
small (few Tasks, no persistence/API/worker surface for B3) is correct —
omit inapplicable Cross-Cutting Contracts sections rather than padding
them. A Step that omits detail because it involves real causal ambiguity,
persistence, API, worker, or failure-prone behavior is not acceptable.
