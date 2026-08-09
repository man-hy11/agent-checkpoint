# COMPATIBILITY_MATRIX.md

## Current -> Target

| Component | Current | Target | Upgrade Path |
|---|---|---|---|
| runtime | ... | ... | ... |
| framework | ... | ... | ... |
| library | ... | ... | ... |

## Breaking Changes

| Change | Affected Code | Required Adaptation | Evidence Source | Risk |
|---|---|---|---|---|
| ... | ... | ... | ... | ... |

## Runtime / Toolchain Requirements

- OS/base image:
- compiler/build tool:
- Node/Python/JDK/etc:
- DB/client:
- CI:
- deployment:

## Removed / Deprecated APIs

- ...

## Transitive Dependency Concerns

- ...

## Rollback Compatibility

- Can old application run against upgraded environment?
- Can new application run against old environment?
- Is DB/data format backward compatible?
- Is downgrade supported?

## Verification Matrix

- clean install;
- lockfile/install;
- build;
- tests;
- startup;
- migrations;
- production-like smoke.
