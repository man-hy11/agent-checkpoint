# Migration Template

Use this workflow for **changing database schemas, persisted formats, object layouts, indexes, data ownership, or performing backfills/moves**.

Recommended work package:

```text
changes/MIGRATION-YYYY-NNN-<slug>/
```

Default lifecycle:

```text
M1 Data / Schema Baseline
-> M2 Migration & Recovery Design
-> M3 Forward Migration Implementation
-> M4 Validation / Backfill / Compatibility
-> M5 Restore / Rollback Drill
-> Migration Gate
```

## Hard Rules

- Data safety outranks convenience.
- Inventory current schema/format, volume, invariants, and consumers first.
- Define backup/restore, forward migration, validation, and rollback or compensating strategy before destructive changes.
- Migration must be restart-safe/idempotent where appropriate.
- Never equate successful SQL execution with successful data migration.
- Validate row counts, invariants, nullability, references, checksums/samples, and application compatibility as relevant.

All execution uses:

```text
one AI invocation = one Step or one Gate
```

PASS advances `CURRENT.md` to the next target and then STOPs.
FAIL does not advance.
