# CROSS_CUTTING_CONTRACTS.md

## Purpose

Most real defects live in the seams between Tasks, not inside a single
function. Every Step whose Tasks touch persistence, an external interface,
background work, or configuration must resolve these seams explicitly before
the Step is considered planned — not discover them during implementation.

Include only the sections relevant to the Step's actual behavior. Omitting an
irrelevant section is correct; leaving a relevant one as `...` is not.

## Architecture Fit

- name the source-of-truth architecture/data-contract docs this Step must
  follow;
- state that the listed file paths are recommended targets, not a command to
  restructure working code — if an equivalent module already exists, extend
  it and record the mapping in the completion report.

## Expected Files / Modules

Concrete paths this Step is expected to create or extend.

## Data / Persistence Changes

- exact fields/tables/columns added or changed, with types;
- migration required for every relational/schema change, forward-only unless
  the workflow type explicitly plans rollback;
- existing data must be preserved across the change;
- version any JSON/contract whose future reinterpretation could silently
  break older records.

## API Contract

For every new or changed endpoint/interface:

- request/response shape;
- authorization/ownership check, when auth exists in the current scope;
- stable machine-readable error codes (not parsed human-readable strings);
- the HTTP/RPC boundary must not block on long-running work — hand off to a
  background job instead.

## Worker / Background Processing Contract

For any long-running or asynchronous task:

- a running/in-progress state is set only when execution actually begins;
- progress/stage is updated at meaningful points, not only at start/end;
- external process/API calls are bounded by an explicit timeout;
- errors are classified retryable vs non-retryable;
- temporary resources are cleaned up on every exit path, including failure;
- retries are idempotent where practical — a retry must not duplicate or
  corrupt the artifact/state it produces.

## Configuration / Environment

Every new setting must be:

- typed and validated at startup/first use, not assumed correct;
- documented (e.g. in `.env.example` or the project's config reference) when
  user-configurable;
- given a safe default only when a safe default genuinely exists;
- excluded from logs and error messages when secret.

## Error Handling Matrix

List each realistic failure mode this Step introduces or touches. For each:

- user-visible error code/message (if user-facing);
- internal log context;
- resulting job/record final state;
- retryability;
- cleanup/compensation behavior.

A bare bullet list of failure names without these five attributes is
insufficient.

## Logging / Observability

- what gets logged at which point (e.g. latency, counts, decisions made);
- correlation identifiers used (project/job/user/request id, whichever
  exist) so this Step's activity is traceable across logs;
- explicit reminder: never log credentials or full sensitive provider
  payloads.
