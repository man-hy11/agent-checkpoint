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
6. do not start implementation while creating the plan.
