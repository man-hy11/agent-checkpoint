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
6. do not start implementation while creating the plan.
