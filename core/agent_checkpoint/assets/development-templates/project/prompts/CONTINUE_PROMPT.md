Continue implementing the project.

First read:

- `AGENTS.md`
- `CLAUDE.md` if applicable
- `PHASE.md`
- `docs/DEVELOPMENT_PLAN.md`
- `docs/TASK_EXECUTION_STANDARD.md`

Determine the Current Target from `PHASE.md`.

Read the corresponding Step/Gate prompt and every referenced cross-cutting document.

Execute ONLY that target.

Rules:

- one invocation = one Step or one Phase Gate;
- do not skip required Tasks/checks;
- do not begin the next target;
- preserve established project invariants;
- update `PHASE.md` only after all acceptance criteria pass;
- if verification fails, do not advance;
- produce the completion report and STOP.

Advancing Current Target does not authorize beginning it in this invocation.
