Implement the planned feature change.

First read:

- existing repository `AGENTS.md` / equivalent;
- relevant existing project architecture/docs;
- this feature change's `CHANGE.md`;
- `IMPACT.md`;
- `CURRENT.md`;
- the current Feature Step/Gate prompt.

Execute ONLY the Current Target from `CURRENT.md`.

One invocation = one Feature Step or Feature Gate.

For a Step:

```text
inspect existing behavior
-> implement only current Step
-> focused tests
-> regression tests
-> inspect actual result
-> evidence
-> acceptance
```

For a Gate, verify only; do not begin unrelated enhancement work.

On PASS:
- update `CURRENT.md`;
- report;
- STOP.

On FAIL:
- do not advance;
- report exact remediation;
- STOP.
