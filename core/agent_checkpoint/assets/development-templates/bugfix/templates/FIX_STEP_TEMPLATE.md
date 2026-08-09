# Bugfix Step B3 — Minimal Fix

## Goal

Implement the smallest correct fix for the evidence-backed root cause.

## Preconditions

B1 and B2 verified complete.

## Tasks

### Task 1 — Add/Prepare Regression Test
Where practical, create a test that fails before the fix and protects the bug.

### Task 2 — Implement Fix
Change only the required behavior.

### Task 3 — Focused Verification
Run the direct reproduction/regression test.

### Task 4 — Inspect State
Verify actual result, not only test process exit code.

## Constraints

Do not:
- redesign unrelated architecture;
- change unrelated APIs;
- upgrade dependencies without need;
- weaken validation;
- hide the symptom without addressing the confirmed cause.

## Acceptance Criteria

- [ ] original reproduction now passes;
- [ ] regression test passes;
- [ ] fix matches root cause;
- [ ] change surface remains minimal;
- [ ] no known new failure introduced.

## Completion

PASS -> advance to B4 -> report -> STOP.
