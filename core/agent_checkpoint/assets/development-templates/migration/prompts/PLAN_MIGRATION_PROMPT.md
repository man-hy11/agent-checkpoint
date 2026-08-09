Use the supplied **AI Development Templates / Migration Template** to plan this work.

Do not execute the change yet.

First inspect the existing repository and gather the context needed to plan safely.

Create an independent work package such as:

```text
changes/MIGRATION-YYYY-NNN-<slug>/
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
M1 Data / Schema Baseline
M2 Migration & Recovery Design
M3 Forward Migration Implementation
M4 Validation / Backfill / Compatibility
M5 Restore / Rollback Drill
Migration Gate
```

Adjust Step count to the actual complexity.

Planning focus:

changing database schemas, persisted formats, object layouts, indexes, data ownership, or performing backfills/moves

Hard rules:

- Data safety outranks convenience.
- Inventory current schema/format, volume, invariants, and consumers first.
- Define backup/restore, forward migration, validation, and rollback or compensating strategy before destructive changes.
- Migration must be restart-safe/idempotent where appropriate.
- Never equate successful SQL execution with successful data migration.
- Validate row counts, invariants, nullability, references, checksums/samples, and application compatibility as relevant.

Execution rules:

1. one invocation = one Migration Step or one Migration Gate;
2. PASS -> advance `CURRENT.md` -> completion report -> STOP;
3. FAIL -> do not advance -> remediation report -> STOP;
4. do not perform unrelated refactors or product changes;
5. include evidence and regression requirements in every Step;
6. do not start implementation while creating the plan.
