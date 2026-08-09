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
3. each Step needs detailed Tasks, tests, evidence, failure cases, acceptance criteria, and out-of-scope boundaries;
4. `PHASE.md` is authoritative;
5. one invocation = one Step or one Phase Gate;
6. PASS -> advance Current Target -> report -> STOP;
7. FAIL -> do not advance -> report -> STOP;
8. perform a final dependency/consistency audit;
9. validate Step IDs, file names, headers, preconditions, Gates, and source-of-truth documents.

Do not start application implementation.
