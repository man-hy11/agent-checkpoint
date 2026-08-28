# Upgrade Template

Use this workflow for **upgrading runtimes, frameworks, libraries, build tools, database engines, containers, or platform versions**.

Recommended work package:

```text
changes/UPGRADE-YYYY-NNN-<slug>/
```

Default lifecycle:

```text
U1 Version / Dependency Inventory
-> U2 Breaking-Change & Compatibility Analysis
-> U3 Bounded Upgrade
-> U4 Migration / Adaptation
-> U5 Regression / Rollback Check
-> Upgrade Gate
```

## Hard Rules

- Record current and target versions before changing anything.
- Read official migration/release notes when available.
- Identify breaking changes, removed APIs, runtime/toolchain constraints, and transitive dependency risks.
- Prefer bounded increments over a giant upgrade when practical.
- Do not hide incompatibilities by disabling tests or pinning unsafe workarounds without documentation.
- Preserve a rollback/downgrade path where the environment permits it.

All execution uses:

```text
one AI invocation = one Step or one Gate
```

PASS advances `CURRENT.md` to the next target and then STOPs.
FAIL does not advance.
