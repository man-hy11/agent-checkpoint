Execute the planned bugfix.

First read:

- existing repository agent instructions;
- bugfix `BUG.md`;
- bugfix `CURRENT.md`;
- current Bugfix Step/Gate prompt;
- affected project docs/tests.

Execute ONLY the Current Target.

Hard rules:

- one invocation = one Bugfix Step or Bug Gate;
- do not skip Reproduce/Root Cause requirements;
- do not implement the fix before the plan reaches the Fix Step;
- do not advance without verified PASS;
- do not perform unrelated refactors;
- record concrete evidence;
- after the completion report, STOP.

Do not begin the next target automatically.
