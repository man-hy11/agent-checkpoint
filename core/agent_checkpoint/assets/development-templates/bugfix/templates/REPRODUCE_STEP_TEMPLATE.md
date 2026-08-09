# Bugfix Step B1 — Reproduce & Capture Evidence

## Goal

Reproduce the reported bug or establish the strongest available failure evidence.

## Required Reading

- existing repo agent instructions;
- BUG.md;
- affected module docs/tests;
- relevant logs/issues if available.

## Tasks

### Task 1 — Confirm Environment
Capture version/config/environment required for reproduction.

### Task 2 — Reproduce
Use the smallest reliable reproduction.

### Task 3 — Capture Evidence
Capture:
- failing test;
- exception/stack;
- API response;
- log correlation;
- DB state;
- browser/UI state;
- artifact output;
as relevant.

### Task 4 — Minimize Reproduction
Reduce variables where practical.

## Acceptance Criteria

- [ ] bug is reproduced OR inability to reproduce is documented with concrete attempts;
- [ ] failure evidence is captured;
- [ ] expected vs actual behavior is explicit;
- [ ] no production fix has been implemented yet.

## Completion

PASS -> advance to B2 -> report -> STOP.

Do not begin Root Cause analysis implementation work in this invocation beyond recording observations needed for reproduction.
