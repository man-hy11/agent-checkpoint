Continue the planned feature change.

Read:

- existing repository agent instructions;
- feature `CHANGE.md`;
- feature `IMPACT.md`;
- feature `CURRENT.md`;
- current Step/Gate prompt;
- affected existing project docs/tests.

Execute ONLY the Current Target from `CURRENT.md`.

Rules:

- one invocation = one Feature Step or one Feature Gate;
- preserve existing architecture and behavior unless explicitly changed;
- no unrelated refactor;
- run focused + relevant regression checks;
- update `CURRENT.md` only after verified PASS;
- after completion report, STOP;
- do not begin the next target automatically.
