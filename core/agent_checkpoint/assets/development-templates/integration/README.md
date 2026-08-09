# External Integration Template

Use this workflow for **adding an external API, OAuth provider, payment service, publishing platform, messaging service, cloud service, or vendor SDK**.

Recommended work package:

```text
changes/INT-YYYY-NNN-<slug>/
```

Default lifecycle:

```text
I1 Provider Contract / Capability Analysis
-> I2 Auth / Security / Adapter Design
-> I3 Fake or Sandbox Integration
-> I4 Production Integration Logic
-> I5 Failure / Retry / Idempotency / Compatibility
-> Integration Gate
```

## Hard Rules

- Treat external provider responses/data as untrusted input.
- Define auth/token storage and least-privilege scopes.
- Define timeout, bounded retry, rate-limit handling, provider outages, idempotency, duplicate-side-effect protection, and API-version compatibility.
- Prefer adapter/provider abstractions instead of leaking vendor objects into domain logic.
- Use fake/sandbox/contract tests before destructive real calls.
- Never log secrets/tokens.

All execution uses:

```text
one AI invocation = one Step or one Gate
```

PASS advances `CURRENT.md` to the next target and then STOPs.
FAIL does not advance.
