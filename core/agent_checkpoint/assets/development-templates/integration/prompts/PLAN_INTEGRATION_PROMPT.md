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
6. do not start implementation while creating the plan;
7. every Step must follow `templates/STEP_TEMPLATE.md` in full — do not emit
   a thin summary. Each Step needs:
   - Required Reading / Existing System Inspection, including
     `PROVIDER_CONTRACT.md`, and explicit In/Out of Scope;
   - Tasks broken out per `shared/TASK_DECOMPOSITION_STANDARD.md`
     (Objective, Inspect Before Editing with concrete adapter paths,
     Implementation Contract using normalized error categories, numbered
     Detailed Implementation Steps, a Failure/Recovery table covering
     provider-specific failure modes — auth expiry, rate limit, timeout,
     outage, malformed response, version mismatch — each with error
     code/message/retryability/cleanup/final-state, Task-Level Test Cases,
     Evidence Required, Task Done Condition);
   - an explicit split between default fake/sandbox testing and any opt-in
     live-provider testing;
   - a Task Execution Tracking table;
   - the relevant sections of `shared/CROSS_CUTTING_CONTRACTS.md` adapted
     for integration work (Architecture Fit on the adapter boundary,
     Provider Contract in place of a generic API Contract, Configuration/
     Environment covering auth/token storage and least-privilege scopes,
     Error Handling Matrix, Logging/Observability with an explicit
     never-log-secrets reminder) — filled in, not left as placeholders, for
     every section that applies;
   - the Implementation Review Checklist from
     `shared/STEP_EXECUTION_PROTOCOL.md` plus the integration-specific
     items in `templates/STEP_TEMPLATE.md`;
8. every External Integration Gate must follow `templates/GATE_TEMPLATE.md`
   in full, per `shared/GATE_STANDARD.md` — Gate PASS requires provider
   contract compliance to be verified, failure/retry/idempotency behavior to
   be actually exercised (not only present in source), no leaked secrets,
   and an end-to-end pass through the real or realistically sandboxed
   provider, not merely a fully in-process fake.

A Step that is thin because the underlying integration surface is genuinely
small (few operations, no side effects) is correct — omit inapplicable
Cross-Cutting Contracts sections rather than padding them. A Step that omits
detail because it involves real auth, side-effecting calls, retries, or
failure-prone provider behavior is not acceptable.
