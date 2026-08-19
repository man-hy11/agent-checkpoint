# External Integration Gate — <TITLE>

## Preconditions

All planned External Integration Steps are verified complete in `CURRENT.md`.

## Gate Focus

Verify the provider contract as actually implemented — not merely coded —
including auth boundary, happy path, outages/errors, rate limits,
retry/idempotency, safe external side effects, and that no secrets leaked
anywhere in the process. Gate PASS means the integration behaves correctly
when exercised through the real (or realistically sandboxed) provider, not
that unit tests with a fully-controlled fake pass.

## Verify

> See `shared/GATE_STANDARD.md`. Include only sections relevant to what this
> integration actually built; do not leave a relevant section as `...`.

### Functional
- every Step's Acceptance Criteria still hold when exercised together, not
  only individually;
- the adapter's public surface matches `PROVIDER_CONTRACT.md` exactly
  (operations, request/response shapes, normalized error codes);
- no vendor SDK object/type leaks past the adapter boundary into domain
  code (spot-check call sites, not just the adapter module);
- ...

### Provider Contract Compliance
- every operation listed in `PROVIDER_CONTRACT.md`'s Endpoints/SDK Surface
  table is implemented and its normalized error mapping verified;
- authentication flow matches the documented auth type/scopes/token
  lifetime/refresh behavior — verify token refresh actually happens before
  expiry, not only that the code path exists;
- API/SDK version pinned matches what was recorded, and any deprecation
  warnings from the provider are captured, not ignored.

### Failure / Retry / Idempotency — Actually Exercised
- each failure mode in every Step's Error Handling Matrix is triggered
  through the real adapter (via fake/sandbox simulation or, where safe,
  live provider) and produces the documented normalized error, user
  message, and final state — not just present in source code;
- retry policy is verified to back off correctly and to stop at max
  attempts (simulate rate-limit / 5xx responses and observe actual retry
  timing/count, not just read the retry loop);
- idempotency is proven, not assumed: trigger an ambiguous-timeout or
  duplicate-call scenario and confirm the side effect is not duplicated
  (e.g. re-run a payment/webhook/create call with the same idempotency key
  and inspect the resulting record count);
- outage/unavailable handling is exercised (simulate a 5xx/connection
  failure) and confirmed to degrade safely rather than crash or corrupt
  state.

### Security / Secrets
- grep logs, error messages, and any captured request/response fixtures
  produced during this Gate's verification for tokens/API keys/secrets —
  confirm none are present;
- confirm credential storage uses the mechanism documented in
  `PROVIDER_CONTRACT.md` and that scopes requested are least-privilege, not
  broader than what the implemented operations require;
- confirm webhook signature verification (if applicable) actually rejects
  an unsigned/incorrectly-signed payload, not only that the code exists.

### Data / State
- local records created by side-effecting provider calls (e.g. request
  records used for idempotency/reconciliation) are consistent after retry
  and failure scenarios;
- ...

### Backward Compatibility
- existing callers/features that depended on any pre-existing integration
  behavior this Step touched still function;
- ...

### Observability
- structured log context (correlation id, provider, operation, normalized
  error category) is present in a real run's logs;
- no secret/credential/full raw payload appears in any log line produced
  during this Gate's verification;
- ...

## End-to-End / Representative Scenario — Real or Sandboxed Provider

```text
entry point (e.g. application action that triggers the provider call)
-> adapter call through the real or sandboxed provider (not a fully
   in-process fake, for at least the primary happy-path and one failure
   scenario)
-> normalized response/error observed
-> persisted/local state inspected
-> expected observable result confirmed
```

Note explicitly whether this scenario ran against a live sandbox/test
account or a fake double, and why that choice was sufficient evidence.

## Required Evidence

- exact commands/tests executed, including which failure modes were
  actively triggered (not merely read from source);
- actual state/output inspected (normalized error objects, local DB rows,
  log lines with secrets redacted, provider dashboard state where
  applicable);
- confirmation that no secrets/tokens appear in logs or captured
  evidence;
- regression evidence for any pre-existing behavior this work touched;
- remaining limitations, explicitly named (e.g. "live outage handling
  verified only via simulated 5xx, not an actual provider outage").

## Gate Failure

If the Gate reveals a defect:

1. do not mark the Gate complete;
2. do not patch large unrelated code inside the Gate — only tiny
   verification-only corrections are permitted, and only if this Gate
   explicitly allows them;
3. identify the required remediation as a new/reopened Step;
4. record evidence;
5. STOP.

## Gate PASS

1. mark the External Integration Gate complete in `CURRENT.md`;
2. write the final work summary (per `shared/EXECUTION_RULES.md`);
3. STOP.

Do not start unrelated follow-on work in this invocation.
