Continue the planned bugfix.

Read:

- existing repository agent instructions;
- bugfix `BUG.md`;
- bugfix `CURRENT.md`;
- current Bugfix Step/Gate prompt;
- relevant existing docs/tests.

Execute ONLY the Current Target from `CURRENT.md`.

Rules:

- one invocation = one Bugfix Step or one Bug Gate;
- preserve the evidence chain: reproduction -> root cause -> fix -> regression;
- do not guess past a failed/uncertain Root Cause Step;
- no unrelated refactor;
- update CURRENT.md only after PASS;
- produce completion report;
- STOP.

Advancing Current Target does not authorize beginning it in this invocation.
