Use the supplied **AI Development Templates / Upgrade Template** to plan this work.

Do not execute the change yet.

First inspect the existing repository and gather the context needed to plan safely.

Create an independent work package such as:

```text
changes/UPGRADE-YYYY-NNN-<slug>/
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
U1 Version / Dependency Inventory
U2 Breaking-Change & Compatibility Analysis
U3 Bounded Upgrade
U4 Migration / Adaptation
U5 Regression / Rollback Check
Upgrade Gate
```

Adjust Step count to the actual complexity.

Planning focus:

upgrading runtimes, frameworks, libraries, build tools, database engines, containers, or platform versions

Hard rules:

- Record current and target versions before changing anything.
- Read official migration/release notes when available.
- Identify breaking changes, removed APIs, runtime/toolchain constraints, and transitive dependency risks.
- Prefer bounded increments over a giant upgrade when practical.
- Do not hide incompatibilities by disabling tests or pinning unsafe workarounds without documentation.
- Preserve a rollback/downgrade path where the environment permits it.

Execution rules:

1. one invocation = one Upgrade Step or one Upgrade Gate;
2. PASS -> advance `CURRENT.md` -> completion report -> STOP;
3. FAIL -> do not advance -> remediation report -> STOP;
4. do not perform unrelated refactors or product changes;
5. include evidence and regression requirements in every Step;
6. do not start implementation while creating the plan;
7. every Step must follow `templates/STEP_TEMPLATE.md` in full — do not emit
   a thin summary. Each Step needs:
   - Required Reading / Existing System Inspection, including
     `COMPATIBILITY_MATRIX.md` for its component(s) and the relevant
     official migration/release notes, and explicit In/Out of Scope;
   - Tasks broken out per `shared/TASK_DECOMPOSITION_STANDARD.md`
     (Objective naming the exact `COMPATIBILITY_MATRIX.md` row(s) resolved,
     Inspect Before Editing with concrete paths and exact current/target
     versions, Implementation Contract, numbered Detailed Implementation
     Steps that capture a pre-upgrade baseline run and a post-upgrade
     comparison run, Failure/Recovery Cases with error
     code/message/retryability/cleanup/final-state including rollback,
     Task-Level Test Cases covering the Verification Matrix, Evidence
     Required, Task Done Condition);
   - a Task Execution Tracking table;
   - the relevant sections of `shared/CROSS_CUTTING_CONTRACTS.md` (Data/
     Persistence, API Contract, Worker/Background Contract, Configuration/
     Environment including Runtime/Toolchain Requirements, Error Handling
     Matrix, Logging/Observability) — filled in, not left as placeholders,
     for every section that applies to this Step's version/compatibility
     change;
   - the Regression/Compatibility Surface naming the exact
     `COMPATIBILITY_MATRIX.md` rows this Step resolves and the rollback
     path;
   - the Implementation Review Checklist from `templates/STEP_TEMPLATE.md`
     (baseline items plus the upgrade-specific items: current/target
     versions recorded before change, every Breaking Changes row has
     remediation evidence, the increment stayed bounded, rollback path
     verified or explicitly documented as unavailable, no unrelated
     feature/refactor work folded in);
8. the Upgrade Gate must follow `templates/GATE_TEMPLATE.md` in full, per
   `shared/GATE_STANDARD.md` — Version/Compatibility Verification,
   Breaking-Change Closure, Existing Behavior/Compatibility, Failure/
   Recovery, Security/Data/Operations, Rollback Verification, Cross-Step
   Regression, Observability, Representative End-to-End, and Required
   Evidence, all filled in rather than left as placeholders.

A Step that is thin because the underlying version bump is genuinely small
(few Tasks, no persistence/API/worker surface touched, no breaking changes
in range) is correct — omit inapplicable Cross-Cutting Contracts sections
rather than padding them. A Step that omits detail because it involves real
breaking changes, persistence, API, worker, or failure-prone behavior is not
acceptable.
