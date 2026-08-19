Use the supplied **AI Development Templates / Spike / Research / POC Template** to plan this work.

Do not execute the change yet.

First inspect the existing repository and gather the context needed to plan safely.

Create an independent work package such as:

```text
changes/SPIKE-YYYY-NNN-<slug>/
```

Create:

- `WORK.md` or a more specific work-description file;
- `CURRENT.md`;
- detailed Step prompts;
- `gate.md`;
- `FIRST_RUN_PROMPT.md`;
- `CONTINUE_PROMPT.md`.

Default conceptual Steps:

```text
S1 Question / Decision Criteria
S2 Alternatives / Evidence Plan
S3 Bounded Experiments
S4 Findings / Tradeoffs
S5 Recommendation / Decision Record
Spike / Research / POC Gate
```

Adjust Step count to the actual complexity.

Planning focus:

answering technical feasibility questions, comparing architectures/libraries, or building bounded proof-of-concepts before committing

Hard rules:

- The output is evidence and a decision, not production code.
- Define the question and decision criteria before experimenting.
- Time/scope-box experiments.
- Compare realistic alternatives where feasible.
- Record failed experiments and uncertainty.
- Prototype code must not silently become production code.
- If a prototype is selected, create a normal PROJECT/FEATURE/REFACTOR/INTEGRATION plan to productionize it.

Execution rules:

1. one invocation = one Spike / Research / POC Step or one Spike / Research / POC Gate;
2. PASS -> advance `CURRENT.md` -> completion report -> STOP;
3. FAIL -> do not advance -> remediation report -> STOP;
4. do not perform unrelated refactors or product changes;
5. include evidence and regression requirements in every Step;
6. do not start implementation while creating the plan;
7. every Step must follow `templates/STEP_TEMPLATE.md` in full — do not emit
   a thin summary. Spike Steps are framed around bounded experiments, not
   production implementation. Each Step needs:
   - Required Reading / Existing System Inspection, including
     `DECISION_RECORD.md` and prior art already in the repository, and
     explicit In/Out of Scope;
   - Experiment Tasks broken out per `shared/TASK_DECOMPOSITION_STANDARD.md`,
     reframed as bounded experiments (Objective as the question being
     answered, Inspect Before Editing to isolate prototype code from
     production paths, an Experiment Contract with an explicit time/scope
     box, numbered Detailed Experiment Steps, Failure/Recovery Cases that
     record negative results as findings rather than discarding them,
     Task-Level Evidence Captured, Evidence Required demanding documented
     findings and uncertainty rather than passing tests, Task Done
     Condition);
   - a Task Execution Tracking table using Experiment / Run / Findings
     Recorded / Evidence / Verified columns;
   - the spike-adapted Cross-Cutting section from `templates/STEP_TEMPLATE.md`
     (What Was Tried, What Was Learned, Productionization Boundary) kept
     minimal — most `shared/CROSS_CUTTING_CONTRACTS.md` production-contract
     sections do not apply and should be omitted rather than padded;
   - the Implementation Review Checklist from
     `shared/STEP_EXECUTION_PROTOCOL.md` plus the spike-specific items in
     `templates/STEP_TEMPLATE.md`, including that prototype code is marked
     `DISPOSABLE` or `CANDIDATE_FOR_REIMPLEMENTATION` and never silently
     treated as production-ready;
8. every Spike / Research / POC Gate must follow `templates/GATE_TEMPLATE.md`
   in full, per `shared/GATE_STANDARD.md` — Gate PASS means the decision is
   well-supported (question answered with evidence, alternatives genuinely
   compared, uncertainty recorded, a recommendation/decision record exists),
   not that prototype code works.

A Step that is thin because the bounded question is genuinely narrow (one
quick check, no alternative comparison needed) is correct — omit
inapplicable Cross-Cutting sections rather than padding them. A Step that
omits detail because it involves comparing real alternatives or building a
prototype with disposability risk is not acceptable.
