# Chain contract v1

`next_skill` is a pure function of the state block, evaluated top to bottom.
The first matching row wins. It is computed on read and never stored.

| # | Condition | next_skill |
|---|---|---|
| 1 | no state block exists | checkpoint-select-workflow |
| 2 | brief_confirmed is false | checkpoint-brainstorm |
| 3 | units is empty | checkpoint-plan |
| 4 | every unit is passed or superseded, and at least one unit is passed | checkpoint-handoff |
| 5 | current_unit names no member of units | checkpoint-plan |
| 6 | current unit state is passed (and not every unit is passed) | checkpoint-plan |
| 7 | current unit state is superseded | checkpoint-plan |
| 8 | current unit state is blocked | checkpoint-recover |
| 9 | current unit state is failed and the current attempt has no root_cause_fingerprint | checkpoint-diagnose |
| 10 | current unit state is failed | checkpoint-recover |
| 11 | current unit state is pending or ready | checkpoint-claim |
| 12 | current unit state is running and kind is gate | checkpoint-verify-gate |
| 13 | current unit state is running and kind is step | checkpoint-execute |

Row 4 precedes every current-unit row, so completed work terminates at a handoff
regardless of what current_unit still names. `superseded` marks a unit whose
work was folded into a later unit during re-planning — a resolved, terminal
outcome, not an unfinished one — so row 4 does not require every unit to be
literally `passed`; it only requires no unit left in an unresolved state, and
at least one unit actually `passed` (a package that superseded all of its own
units without ever passing one has not finished any work and does not
qualify). Row 6 covers a stale tracker: a
unit can be `passed` while current_unit still names it if nothing has yet
advanced current_unit to the next pending unit — checkpoint-plan is the
routing target that picks the next unit, not a request to re-plan the whole
package. Row 11 admits `pending` because a tracker may point at a unit whose
dependency has just passed; checkpoint-claim verifies the dependency before
claiming.

checkpoint-evidence is never returned. While a unit is running the table
returns checkpoint-execute or checkpoint-verify-gate; those skills hand results
to checkpoint-evidence, which alone may complete the transition. Calling
`work pass` or `work fail` without validated evidence is refused with exit 2 and
a message naming checkpoint-evidence.

checkpoint-inspect is never returned. It is user-invoked only and never writes.

## allowed_events

Derived from the transition table for the current unit's state, minus events
refused by the no-progress guard.

## No-progress guard

retry is refused when either holds:

- the unit has recorded attempts equal to or beyond `attempt_override or max_attempts`;
- the last two attempts for the unit carry an identical non-null root_cause_fingerprint.

When retry is refused, allowed_events retains replan, supersede, and block.
