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
- No destructive Step may pass while `MIGRATION_RECOVERY_PLAN.md` is absent or does not yet cover that Step.
- Every migration Step names its rollback path before it runs.
- Data integrity is verified after every destructive Step, not only at the end.

Execution rules:

1. one invocation = one Migration Step or one Migration Gate;
2. every Step must follow `templates/STEP_TEMPLATE.md` in full — do not emit
   a thin summary. Each Step needs:
   - Required Reading / Existing System Inspection, including the relevant
     sections of `MIGRATION_RECOVERY_PLAN.md`;
   - Tasks broken out per `shared/TASK_DECOMPOSITION_STANDARD.md` (Objective,
     Inspect Before Editing with concrete paths, Implementation Contract
     including an idempotency/restart-safety statement, numbered Detailed
     Implementation Steps, Failure/Recovery Cases that explicitly cover
     partial-migration failure, rollback trigger conditions, and
     data-integrity violations, Task-Level Test Cases, Evidence Required,
     Task Done Condition);
   - a Task Execution Tracking table;
   - the relevant sections of `shared/CROSS_CUTTING_CONTRACTS.md`, with
     Data / Persistence Changes filled in at the depth `templates/
     STEP_TEMPLATE.md` requires (row-count/invariant/checksum validation,
     idempotency/restart-safety statement, explicit rollback procedure
     reference to `MIGRATION_RECOVERY_PLAN.md`) whenever this Step reads or
     writes persisted data — not left as a placeholder;
   - the Regression / Compatibility Surface section;
   - the Implementation Review Checklist, migration-specific items included;
3. every Migration Gate must follow `templates/GATE_TEMPLATE.md` in full,
   per `shared/GATE_STANDARD.md` — including Data Integrity Verification and
   Rollback-Drill Verification sections that record the drill as actually
   executed, and the Sign-Off checklist;
4. `CURRENT.md` is authoritative;
5. PASS -> advance `CURRENT.md` -> completion report -> STOP;
6. FAIL -> do not advance -> remediation report -> STOP;
7. do not perform unrelated refactors or product changes;
8. include evidence and regression requirements in every Step;
9. do not start implementation while creating the plan.

A Step that is thin because the underlying work is genuinely small (no
destructive change, small/simple backfill) is correct — omit inapplicable
Cross-Cutting Contracts sections rather than padding them. A Step that omits
detail because it involves destructive schema/data change, backfill, or
rollback-relevant behavior is not acceptable.
