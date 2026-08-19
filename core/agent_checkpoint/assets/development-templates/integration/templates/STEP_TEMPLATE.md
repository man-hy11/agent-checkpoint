# External Integration Step <ID> — <TITLE>

## Target
- Step: <ID>
- Scope: **Only this Step**

## Goal

<Precise integration goal — one or two sentences, not a restated title.>

## Preconditions

<Which earlier Step(s)/Gate must already be verified complete — e.g. Provider
Contract analysis (I1) must be verified before adapter implementation.>

## Required Reading / Existing System Inspection

Before implementing, read:
- repository agent instructions (`AGENTS.md` / `CLAUDE.md`);
- this work package's `WORK.md`;
- `CURRENT.md`;
- `PROVIDER_CONTRACT.md` (this Step must not contradict the recorded
  contract — if reality differs from what was recorded, update
  `PROVIDER_CONTRACT.md` first and note the change in this Step's evidence);
- relevant source-of-truth architecture/adapter-boundary docs;
- the existing provider adapter module(s), if any already exist for this or
  a similar provider — extend rather than duplicate;
- affected tests/contracts, including any existing fake/sandbox test harness.

## Working Rule

Implement only this Step. If future work is relevant, leave a short TODO or
note only — do not implement it.

## Scope

### In Scope
- ...

### Out of Scope
- ...

## Implement

<High-level shape of the integration behavior this Step adds — the "what,"
before the Task-by-Task "how" below.>

## Granular Execution Tasks

> Execute each Task in order and collect evidence before proceeding. See
> `shared/TASK_DECOMPOSITION_STANDARD.md` for the required structure of each
> Task below. Integration Tasks additionally require the provider-specific
> failure enumeration described here.

### Task 1 — <imperative, specific action>

#### Objective
One sentence: what this Task alone must accomplish.

#### Inspect Before Editing
- exact adapter/client files this Task is expected to touch or extend;
- confirm no parallel adapter for the same provider already exists under a
  different path — if it does, extend it and record the mapping in the
  completion report;
- the current auth/token storage mechanism, if this Task touches
  credentials.

#### Implementation Contract
- accepted inputs (including which are attacker/provider-controlled and
  must be treated as untrusted);
- returned outputs / persisted state;
- invariants that must hold before and after (e.g. no vendor SDK object
  leaks past the adapter boundary into domain logic);
- error categories this Task owns, expressed as the normalized categories
  from `PROVIDER_CONTRACT.md` (e.g. `AUTH_REQUIRED`, `RATE_LIMITED`,
  `TIMEOUT`, `UNAVAILABLE`, `INVALID_REQUEST`, `NOT_FOUND`, `CONFLICT`,
  `CAPACITY_EXHAUSTED`, `UNKNOWN_PROVIDER_ERROR`), not raw provider
  exception types.

#### Testing Strategy: Fake/Sandbox vs Live Provider
- default implementation and Task-Level Test Cases must run against a
  fake/sandbox/contract-test double — never require a live paid provider to
  pass;
- if this Task requires verification against the real provider (e.g. to
  confirm an auth flow or a response-shape assumption), mark that check as
  an explicit **opt-in live-provider test**, name the sandbox/test account
  used, and report separately whether it was actually executed;
- never use a destructive real-provider call as casual/default verification
  (see `shared/EVIDENCE_STANDARD.md`).

#### Detailed Implementation Steps
1. inspect current ownership (adapter boundary, credential storage, existing
   callers, tests) before adding new modules;
2. confirm the Implementation Contract above, including the normalized
   error categories, before writing code;
3. implement only this Task's behavior — do not pull forward-Step scope in
   (e.g. do not implement retry/idempotency in a Step scoped to auth);
4. keep the provider adapter separate from domain/business logic so core
   logic is unit-testable without live network calls;
5. validate all provider responses at the adapter boundary before trusting
   them downstream — treat provider data as untrusted input;
6. make partial-failure behavior explicit — the system must end in a state
   that can be inspected and safely retried or corrected;
7. add stable structured log context (correlation id, provider, operation,
   normalized error category) — never log secrets, tokens, or full raw
   provider payloads that may contain sensitive data;
8. add focused automated tests for success, boundary conditions, and each
   provider-specific failure mode below;
9. verify through the real owning adapter code path (fake/sandbox provider),
   not only in isolation.

#### Failure / Recovery Cases

Per `WORK_TYPE_HARD_RULES.md` (INTEGRATION): provider auth, timeout, retry,
rate limits, idempotency, outages, and API versioning are first-class
concerns, not afterthoughts. Enumerate each realistic provider failure mode
for this Task. At minimum, cover the applicable rows below (omit only the
ones this Task's operations genuinely cannot hit):

| Failure Mode | Error Category | Safe User-Facing Message | Internal Log Context | Retryable? | Cleanup/Compensation | Final State |
|---|---|---|---|---|---|---|
| Auth token expired/invalid | `AUTH_REQUIRED` | ... | ... | no (requires re-auth) | ... | ... |
| Rate limit exceeded | `RATE_LIMITED` | ... | ... | yes (backoff per Retry-After) | ... | ... |
| Request timeout | `TIMEOUT` | ... | ... | yes (bounded) | ... | ... |
| Provider outage / 5xx | `UNAVAILABLE` | ... | ... | yes (backoff) | ... | ... |
| Malformed/unexpected response shape | `INVALID_REQUEST` or `UNKNOWN_PROVIDER_ERROR` | ... | ... | no | ... | ... |
| API version mismatch / deprecated field | `UNKNOWN_PROVIDER_ERROR` | ... | ... | no (requires code change) | ... | ... |
| Ambiguous timeout after side-effecting call (idempotency) | n/a — reconciliation | ... | ... | reconcile via idempotency key | ... | ... |

For each row actually included, specify: error category/code, safe
user-facing message (if user-facing), internal log context, retryability,
cleanup/compensation action, and final resulting state — a bare failure
name without these attributes is insufficient.

#### Task-Level Test Cases
- the success path against the fake/sandbox provider;
- each boundary condition relevant to this Task (e.g. empty response, max
  page size, near-rate-limit);
- each failure case in the table above, simulated via the fake/sandbox
  double;
- assert normalized error category and resulting persisted/local state, not
  only that an exception was thrown;
- unit tests must not require live paid external providers unless
  explicitly marked as opt-in integration tests.

#### Evidence Required Before Checking This Task
- exact test/build command(s) executed;
- PASS/FAIL result;
- key artifact/state inspected (adapter response, normalized error object,
  local DB row, log line showing correlation id — with secrets redacted);
- whether any opt-in live-provider test was executed, and its result;
- any deviation from this Task's contract and why it was necessary.

#### Task Done Condition
Implemented through the normal adapter code path, its provider-specific
failure modes are explicit and tested against a fake/sandbox double, and its
focused tests pass. Placeholder code, mocks left in a production path, or
unresolved TODOs do not satisfy this condition.

<!-- Repeat Task N for every additional Task this Step requires. -->

## Task Execution Tracking

| Task | Code | Focused Tests | Integration Evidence | Verified |
|---|---|---|---|---|
| 1. <name> | [ ] | [ ] | [ ] | [ ] |

## Cross-Cutting Contracts

> See `shared/CROSS_CUTTING_CONTRACTS.md`. Include only sections relevant to
> this Step's actual behavior; do not leave an irrelevant section as `...`.

### Architecture Fit
- name the adapter/provider abstraction boundary this Step must respect
  (e.g. `PROVIDER_CONTRACT.md`, any documented ports-and-adapters or
  gateway pattern already in the codebase);
- vendor SDK types/objects must not leak past the adapter into domain code;
- state that listed file paths are recommended targets, not a command to
  restructure a working adapter — if an equivalent adapter already exists,
  extend it and record the mapping in the completion report.

### Expected Files / Modules
...

### Provider Contract

> Replaces a generic "API Contract" section for integration work — see
> `templates/PROVIDER_CONTRACT_TEMPLATE.md`, which this Step must stay
> consistent with (update it if reality diverges).

- provider operation(s) this Step implements or changes, and the adapter
  method(s) that expose them;
- request/response shape at the adapter boundary (our normalized shape, not
  the raw vendor shape);
- authentication/authorization applied to each call;
- normalized, stable error codes returned to callers (not raw
  provider/library exception types);
- idempotency key/strategy for any side-effecting call;
- retry policy (retryable categories, max attempts, backoff, jitter,
  Retry-After handling) per operation;
- rate-limit/quota handling and degradation behavior;
- API/SDK version this Step targets and how a version mismatch is detected.

### Worker / Background Processing Contract
(Include only if this Step's provider calls run outside the request path —
e.g. webhook processing, polling, or async job dispatch to the provider.)
...

### Configuration / Environment
- exact new environment variables/secrets this Step introduces (name,
  purpose, required/optional);
- secret storage mechanism (never plaintext in the repo or in logs);
- least-privilege scope requested from the provider for each credential —
  name the exact scopes and why each is required;
- token lifetime and refresh strategy;
- revocation path if a credential is compromised;
- safe default only where a safe default genuinely exists.

### Error Handling Matrix
- restate (or reference) the Failure/Recovery table from each Task above at
  the Step level if this Step introduces provider-facing failure paths not
  fully captured per-Task (e.g. a Step-level circuit breaker or fallback
  behavior spanning multiple Tasks' operations).

### Logging / Observability
- what gets logged at which point (call attempted, retried, succeeded,
  failed — with latency and normalized error category);
- correlation identifiers used (request/job/user id, plus any
  provider-side request id returned) so this Step's activity is traceable
  across logs and, where available, in the provider's own dashboard;
- **explicit reminder: never log credentials, tokens, API keys, or full raw
  provider payloads that may contain PII or secrets — log redacted/summary
  fields only.**

## Required Test Matrix

In addition to each Task's own tests, list Step-level tests that exercise
more than one Task together (e.g. full request -> normalized response ->
persisted-state path; provider-failure simulation spanning multiple
operations; regression fixtures from earlier Steps).

Use the project's test strategy doc if one exists. Unit tests should not
require live paid external APIs. If a live-provider check is required, make
it an explicit opt-in integration test and report whether it was actually
executed.

## Manual Verification

<Anything automated assertions cannot fully cover — provider dashboard
state, webhook delivery confirmation, manual sandbox walkthrough.>

## Acceptance Criteria

- [ ] ...
- [ ] ...

## Implementation Review Checklist

> Baseline list from `shared/STEP_EXECUTION_PROTOCOL.md`; integration-specific
> items are added below the line.

- [ ] Existing repository architecture/behavior was inspected before changes.
- [ ] Only this Step's declared scope was implemented.
- [ ] New schemas/types are validated and versioned where necessary.
- [ ] Long-running provider work runs outside request/response handlers.
- [ ] External commands/inputs are validated, not string-concatenated.
- [ ] Timeouts and failure paths are explicit for every external call.
- [ ] Retry behavior cannot silently duplicate or corrupt state/artifacts.
- [ ] Tests cover the core success path and each meaningful failure.
- [ ] Documentation/config examples were updated where relevant.
- [ ] Every Acceptance Criterion for this Step is independently verified.
- [ ] `CURRENT.md` was updated only after verification, not before.
- [ ] No Task or file belonging to a later Step/Gate was started.
---
- [ ] Vendor SDK objects do not leak past the adapter boundary into domain
      logic.
- [ ] Every provider failure mode in the Error Handling Matrix has a
      handled path, exercised by a fake/sandbox test, not only coded.
- [ ] Auth/token storage uses least-privilege scopes, and secrets are never
      logged or committed.
- [ ] Idempotency is implemented for every side-effecting provider call.
- [ ] `PROVIDER_CONTRACT.md` matches the implemented behavior (updated if
      reality diverged during implementation).
- [ ] Any opt-in live-provider test is clearly marked and its execution
      status is reported (run or explicitly skipped, with why).

## Step Execution Protocol

> See `shared/STEP_EXECUTION_PROTOCOL.md` for the full A–E protocol
> (Baseline -> Task Loop -> Step Integration -> Definition of Done -> Stop).
> This Step's Definition of Done additionally requires:

- every Task Execution Tracking row fully checked;
- this Step's own Acceptance Criteria and Implementation Review Checklist
  items verified, not assumed;
- `PROVIDER_CONTRACT.md` consistent with what was actually implemented;
- `CURRENT.md` updated to reflect completion only after the above.

## Completion

PASS:
1. mark this Step complete in `CURRENT.md`;
2. advance Current Target;
3. write the completion report (per `shared/EXECUTION_RULES.md`);
4. STOP.

FAIL:
1. leave this Step incomplete;
2. do not advance Current Target;
3. report exact remediation needed;
4. STOP.

Do not start the next Step or Gate in this invocation.
