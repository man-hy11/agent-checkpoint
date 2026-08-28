Use the supplied **AI Development Templates / New Project Template** as the planning and execution methodology for this new project.

Analyze the requirements I provide and create a complete project-specific implementation planning package.

Important:

- The template defines methodology, not product requirements.
- Do not copy product-specific features, technologies, integrations, policies, or assumptions from previous projects unless this project requires them.
- Do not begin implementation while generating the plan.
- Resolve dependencies before assigning Step numbers.
- Put cross-cutting architecture/security/state-machine decisions before dependent features.

Create, as relevant:

- `AGENTS.md`
- `CLAUDE.md`
- `PHASE.md`
- `FILE_MANIFEST.md`
- `docs/PROJECT_REQUIREMENTS.md`
- `docs/DEVELOPMENT_PLAN.md`
- `docs/ARCHITECTURE.md`
- `docs/DATA_CONTRACTS.md`
- `docs/TEST_STRATEGY.md`
- `docs/PRODUCT_UI_SPEC.md` when UI exists
- `docs/TASK_EXECUTION_STANDARD.md`
- architecture/security/operations/quality docs as relevant
- detailed `docs/prompts/phase-X/step-X-Y.md`
- one `gate.md` per Phase
- `prompts/FIRST_RUN_PROMPT.md`
- `prompts/CONTINUE_PROMPT.md`

Rules:

1. dependency-order the Phases;
2. split each Phase into granular independently verifiable Steps;
3. every Step must follow `templates/STEP_PROMPT_TEMPLATE.md` in full — do not
   emit a thin summary. Each Step needs:
   - Required Reading and explicit In/Out of Scope;
   - Tasks broken out per `shared/TASK_DECOMPOSITION_STANDARD.md` (Objective,
     Inspect Before Editing with concrete paths, Implementation Contract,
     numbered Detailed Implementation Steps, Failure/Recovery Cases with
     error code/message/retryability/cleanup/final-state, Task-Level Test
     Cases, Evidence Required, Task Done Condition);
   - a Task Execution Tracking table;
   - the relevant sections of `shared/CROSS_CUTTING_CONTRACTS.md` (Data/
     Persistence, API Contract, Worker/Background Contract, Configuration,
     Error Handling Matrix, Logging/Observability) — filled in, not left as
     placeholders, for every section that applies to this Step's behavior;
   - the Implementation Review Checklist from `shared/STEP_EXECUTION_PROTOCOL.md`;
4. every Phase Gate must follow `templates/PHASE_GATE_TEMPLATE.md` in full,
   per `shared/GATE_STANDARD.md`;
5. `PHASE.md` is authoritative;
6. one invocation = one Step or one Phase Gate;
7. PASS -> advance Current Target -> report -> STOP;
8. FAIL -> do not advance -> report -> STOP;
9. perform a final dependency/consistency audit;
10. validate Step IDs, file names, headers, preconditions, Gates, and source-of-truth documents.

A Step that is thin because the underlying work is genuinely small (few
Tasks, no persistence/API/worker surface) is correct — omit inapplicable
Cross-Cutting Contracts sections rather than padding them. A Step that omits
detail because it involves real persistence, API, worker, or failure-prone
behavior is not acceptable.

Do not start application implementation.
