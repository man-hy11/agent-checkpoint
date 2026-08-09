Use the supplied **AI Development Templates / External Integration Template** to plan this work.

Do not execute the change yet.

First inspect the existing repository and gather the context needed to plan safely.

Create an independent work package such as:

```text
changes/INT-YYYY-NNN-<slug>/
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
I1 Provider Contract / Capability Analysis
I2 Auth / Security / Adapter Design
I3 Fake / Sandbox Integration
I4 Production Integration Logic
I5 Failure / Retry / Idempotency / Compatibility
External Integration Gate
```

Adjust Step count to the actual complexity.

Planning focus:

adding an external API, OAuth provider, payment service, publishing platform, messaging service, cloud service, or vendor SDK

Hard rules:

- Treat external provider responses/data as untrusted input.
- Define auth/token storage and least-privilege scopes.
- Define timeout, bounded retry, rate-limit handling, provider outages, idempotency, duplicate-side-effect protection, and API-version compatibility.
- Prefer adapter/provider abstractions instead of leaking vendor objects into domain logic.
- Use fake/sandbox/contract tests before destructive real calls.
- Never log secrets/tokens.

Execution rules:

1. one invocation = one External Integration Step or one External Integration Gate;
2. PASS -> advance `CURRENT.md` -> completion report -> STOP;
3. FAIL -> do not advance -> remediation report -> STOP;
4. do not perform unrelated refactors or product changes;
5. include evidence and regression requirements in every Step;
6. do not start implementation while creating the plan.
