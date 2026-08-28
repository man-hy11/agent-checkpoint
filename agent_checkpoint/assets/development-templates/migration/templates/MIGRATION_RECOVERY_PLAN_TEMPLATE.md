# MIGRATION_RECOVERY_PLAN.md

## Source State

- schema/version:
- data volume:
- key invariants:
- consumers:
- write traffic:
- retention:

## Target State

...

## Forward Migration

1. ...
2. ...

## Backfill

- batching:
- ordering:
- checkpoints:
- idempotency:
- retry:
- concurrency:
- throttling:

## Validation

Verify as relevant:

- row/object counts;
- required fields;
- referential integrity;
- uniqueness;
- aggregate totals;
- checksums;
- representative samples;
- application reads/writes;
- old/new compatibility window.

## Backup / Restore

- backup mechanism:
- restore mechanism:
- restore test environment:
- expected restoration point:
- evidence required:

## Rollback / Compensation

Describe what is actually possible.

Do not claim rollback if the migration is irreversible.

Possible strategies:

- transactional rollback;
- restore from backup;
- dual-write cutback;
- compensating migration;
- forward-only recovery.

## Cutover

- write freeze if needed:
- dual read/write if needed:
- switching condition:
- rollback trigger:
- observability:
