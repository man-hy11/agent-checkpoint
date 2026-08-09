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
6. do not start implementation while creating the plan.
