# 2. Resilience: Retry, Circuit Breaker, Throttle

Date: 2026-04-17

## Status

Accepted

## Context

The Daikin Onecta cloud is sensitive in practice:

- transient 5xx and network outages tend to come in bursts,
- after a `PATCH`, an immediate `GET` frequently returns stale data
  (see `_cloud_lock` and `scan_ignore` in the coordinator),
- the rate-limit headers (`X-RateLimit-Remaining-{minute,day}`) are the only
  source for proactive pacing.

So far there were only reactive measures: `_cloud_lock`, `scan_ignore`, and a
hard pause as soon as `remaining_day == 0`. That does not cover three
classes of failure:

1. **Transient errors** on a GET produce an empty `UpdateFailed`, even though
   a retry would have absorbed the error without any user-visible impact.
2. **Cloud outages** that last several minutes still keep generating polling
   traffic that only produces errors — no protection, no graceful
   degradation.
3. **Slow rate-limit exhaustion**: `remaining_minute` slowly approaches 0
   without polling frequency reacting.

## Decision

Three building blocks live in the new package
`custom_components/daikin_onecta/support/`:

| Module               | Responsibility                                                                                                                                                                 | Wiring                                                                                          |
| -------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------- |
| `retry.py`           | `@retry_with_backoff` decorator: tries/base_delay/max_delay/jitter, retries only the configured exception classes, **lets auth and rate-limit errors through unconditionally** | `getCloudDeviceDetails()` (idempotent, GET)                                                     |
| `circuit_breaker.py` | `CircuitBreaker` with states `CLOSED → OPEN → HALF_OPEN`, asyncio-Lock guarded                                                                                                 | `doBearerRequest()` pre-hook (`before_call`) and path hooks (`record_success`/`record_failure`) |
| `throttle.py`        | `RateLimitThrottle.recommended_delay(limits)` — returns recommended wait time from current telemetry                                                                           | (prepared) coordinator can fold the wait time into the next `update_interval`                   |

**Important — what is _not_ retried:**

- `DaikinAuthError` → needs a reauth flow, not a retry.
- `DaikinRateLimitError` → the cloud explicitly says "wait X seconds";
  don't guess the same wait three times.

Defaults are conservative (`tries=3`, `failure_threshold=5`,
`recovery_timeout=60s`) so the existing polling rhythm is not disturbed.

## Consequences

- **Positive:** Cloud hiccups are transparently healed on the GET path; a
  longer cloud outage opens the breaker and suppresses follow-up calls
  until the next probe.
- **Positive:** The throttle module is testable in isolation and can later
  be consumed by the coordinator without rewriting it.
- **Risk:** Retry delays the visibility of real cloud problems in the UI.
  We log every retry attempt at `WARNING` with counter and cause so
  hangs remain traceable in the log.
- **Risk:** The circuit breaker can falsely open under very slow cloud
  drift. The threshold of 5 is therefore well above the typical polling
  burst rate.
- **Consequence:** A dedicated exception class
  `CircuitBreakerOpenError(DaikinError)` is translated by the coordinator
  to `UpdateFailed` analogously to `DaikinApiError` (no new HA path
  required).

## Rejected alternatives

- **`tenacity` library instead of an in-house decorator:** an extra
  dependency for a single function with clear behavior — unnecessary.
- **Circuit breaker at the coordinator level:** would leave the auth and
  write paths unprotected. The API layer is the only sensible bracket.
- **Active throttle in the coordinator (now):** deferred until phase 7,
  so the new domain model (DataPoints with individual write frequency)
  can supply input values.
