# PROVIDER_CONTRACT.md

## Provider

...

## Capabilities Needed

- ...

## Authentication

- auth type:
- scopes:
- token lifetime:
- refresh:
- secret storage:
- revocation:

## Endpoints / SDK Surface

| Operation | Provider API | Our Adapter Method | Side Effect |
|---|---|---|---|
| ... | ... | ... | yes/no |

## Normalized Errors

Map provider-specific failures into stable application categories:

- AUTH_REQUIRED
- RATE_LIMITED
- TIMEOUT
- UNAVAILABLE
- INVALID_REQUEST
- NOT_FOUND
- CONFLICT
- CAPACITY_EXHAUSTED
- UNKNOWN_PROVIDER_ERROR

Adapt to the project.

## Retry Policy

Define per operation:

- retryable?
- max attempts;
- backoff;
- jitter;
- Retry-After handling.

## Idempotency

For external side effects:

- idempotency key;
- local request record;
- ambiguous timeout reconciliation;
- duplicate detection.

## Rate Limits / Quotas

- known limits:
- headers/state:
- degradation behavior:

## Webhooks / Polling

- signature verification;
- replay protection;
- ordering/duplication;
- polling cadence when applicable.

## Version Compatibility

- API version:
- SDK version:
- deprecation monitoring:
- contract tests:
