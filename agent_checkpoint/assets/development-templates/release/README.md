# Release / Deployment Template

Use this workflow for **shipping already-planned/implemented work to dev, staging, production, devices, clusters, or distributable packages**.

Recommended work package:

```text
changes/REL-YYYY-NNN-<slug>/
```

Default lifecycle:

```text
D1 Release Scope / Artifact Inventory
-> D2 Environment Preflight / Backup / Rollback Readiness
-> D3 Build / Package / Migration Dry Run
-> D4 Deploy
-> D5 Smoke / Observability / Rollback Decision
-> Release Gate
```

## Hard Rules

- A successful build is not a successful deployment.
- Freeze the exact release scope/version/artifacts.
- Verify environment/config/secrets/dependencies before deploy.
- Identify database/config migrations and rollback constraints.
- Define rollback trigger and procedure before changing production.
- Use health checks, smoke tests, logs/metrics/traces after deploy.
- Do not declare PASS merely because deployment commands returned zero.

All execution uses:

```text
one AI invocation = one Step or one Gate
```

PASS advances `CURRENT.md` to the next target and then STOPs.
FAIL does not advance.
