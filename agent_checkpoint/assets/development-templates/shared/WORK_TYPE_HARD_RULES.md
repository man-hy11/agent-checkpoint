# WORK_TYPE_HARD_RULES.md

## PROJECT
Plan complete dependency order before implementation.

## FEATURE
Inspect existing behavior/architecture first. Preserve unrelated behavior.

## BUGFIX
When evidence is obtainable: reproduce -> prove root cause -> minimal fix -> regression.

## REFACTOR
Intended external behavior must remain unchanged. Characterization tests precede risky structural changes.

## UPGRADE
Inventory current versions and breaking changes first. Upgrade in bounded increments with rollback/compatibility evidence.

## MIGRATION
Protect data first. Define forward migration, validation, backup/restore or rollback strategy before destructive change.

## PERFORMANCE
Measure baseline before optimizing. Keep before/after measurements and correctness regression.

## INTEGRATION
Treat provider auth, timeout, retry, rate limits, idempotency, outages, and API versioning as first-class concerns.

## RELEASE
A successful build is not a successful release. Preflight, deploy, smoke, observability, and rollback readiness are distinct checks.

## SPIKE
The goal is evidence and a decision, not production implementation. Prototype code is disposable unless separately promoted through a normal implementation plan.
