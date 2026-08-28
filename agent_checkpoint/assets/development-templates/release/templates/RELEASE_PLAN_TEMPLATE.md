# RELEASE_PLAN.md

## Release Identity

- release/version:
- commit/tag:
- artifacts/images:
- environment:
- planned scope:

## Included Changes

- ...

## Explicitly Excluded

- ...

## Preflight

- CI PASS;
- exact artifact exists;
- config/secrets validated;
- capacity/disk checked;
- dependent services healthy;
- migration compatibility checked;
- backup/restore readiness checked when needed.

## Deployment Procedure

1. ...
2. ...

## Migration Procedure

If applicable:

...

## Smoke Tests

- health;
- critical API;
- login/auth;
- core user path;
- background jobs;
- external integrations.

## Observability

Watch:

- error rate;
- latency;
- saturation;
- job failures;
- DB health;
- external-provider failures;
- business-critical signal.

## Rollback Trigger

Examples:

- error rate > threshold;
- critical path unavailable;
- data corruption risk;
- migration incompatibility.

## Rollback Procedure

1. ...
2. ...

## Post-Release Evidence

- deployed version;
- deployment command/run ID;
- smoke result;
- metrics/log review;
- migration state;
- rollback readiness/status.
