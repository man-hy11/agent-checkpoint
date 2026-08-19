Use the supplied **AI Development Templates / Release / Deployment Template** to plan this work.

Do not execute the change yet.

First inspect the existing repository and gather the context needed to plan safely.

Create an independent work package such as:

```text
changes/REL-YYYY-NNN-<slug>/
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
D1 Release Scope / Artifact Inventory
D2 Environment Preflight / Backup / Rollback Readiness
D3 Build / Package / Migration Dry Run
D4 Deploy
D5 Smoke / Observability / Rollback Decision
Release / Deployment Gate
```

Adjust Step count to the actual complexity.

Planning focus:

shipping already-planned/implemented work to dev, staging, production, devices, clusters, or distributable packages

Hard rules:

- A successful build is not a successful deployment.
- Freeze the exact release scope/version/artifacts.
- Verify environment/config/secrets/dependencies before deploy.
- Identify database/config migrations and rollback constraints.
- Define rollback trigger and procedure before changing production.
- Use health checks, smoke tests, logs/metrics/traces after deploy.
- Do not declare PASS merely because deployment commands returned zero.

Execution rules:

1. one invocation = one Release / Deployment Step or one Release / Deployment Gate;
2. PASS -> advance `CURRENT.md` -> completion report -> STOP;
3. FAIL -> do not advance -> remediation report -> STOP;
4. do not perform unrelated refactors or product changes;
5. include evidence and regression requirements in every Step;
6. do not start implementation while creating the plan;
7. every Step must follow `templates/STEP_TEMPLATE.md` in full — do not emit
   a thin summary. Release Steps are framed around deployment actions
   (preflight check, artifact build, migration dry run, deploy, smoke test),
   not application coding. Each Step needs:
   - Required Reading / Existing System Inspection, including
     `RELEASE_PLAN.md`, live target-environment state, and explicit
     In/Out of Scope;
   - Tasks broken out per `shared/TASK_DECOMPOSITION_STANDARD.md`, reframed
     as deployment actions (Objective, Inspect Before Editing against live
     environment state, Implementation Contract naming the exact
     artifact/version acted on, numbered Detailed Execution Steps, a
     Failure/Recovery table where every failure names its rollback trigger
     and rollback procedure per the hard rule below, Task-Level Test Cases
     verified against real environment state, Evidence Required, Task Done
     Condition);
   - a Task Execution Tracking table;
   - the release-adapted Cross-Cutting sections from
     `templates/STEP_TEMPLATE.md` (Environment/Config Preflight,
     Migration/Rollback Readiness, Observability covering health checks,
     smoke tests, and logs/metrics/traces post-deploy) — filled in, not
     left as placeholders, for every section that applies; most generic
     `shared/CROSS_CUTTING_CONTRACTS.md` sections (new API/data model) do
     not apply to release work and should be omitted rather than padded;
   - the Implementation Review Checklist from
     `shared/STEP_EXECUTION_PROTOCOL.md` plus the release-specific items in
     `templates/STEP_TEMPLATE.md` — a green pipeline exit code is not
     sufficient evidence; actual environment state must be inspected;
8. every Release / Deployment Gate must follow `templates/GATE_TEMPLATE.md`
   in full, per `shared/GATE_STANDARD.md` — Gate PASS requires confirming
   the deployment actually succeeded (exact artifact/version live in the
   target environment), smoke tests were executed (not merely planned), the
   rollback path was rehearsed and proven rather than only documented, and
   observability is live and showing healthy signal.

A Step that is thin because the underlying deployment action is genuinely
small (no migration, no config change) is correct — omit inapplicable
Cross-Cutting sections rather than padding them. A Step that omits detail
because it changes production data, applies a migration, or is otherwise
high-risk/irreversible is not acceptable.
