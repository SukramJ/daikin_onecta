# Architecture

This document gives a one-page picture of how `daikin_onecta` is wired
together. For day-to-day commands and conventions, see
[`CONTRIBUTING.md`](../CONTRIBUTING.md). For the rationale behind
specific decisions, see [`adr/`](adr/).

## Layer diagram

```
┌──────────────────────────────────────────────────────────────────┐
│                     Home Assistant Core                          │
│  (Coordinator scheduler, Entity registry, Config-Entry storage)  │
└──────────────────────────────────────────────────────────────────┘
                ▲                                ▲
                │ async_setup_entry              │ runtime_data
                │                                │
┌───────────────┴────────────────────────────────┴─────────────────┐
│                      __init__.py                                 │
│  - DaikinApi factory   - OnectaRuntimeData   - migrate_entry     │
└──────────────────────────────────────────────────────────────────┘
                │                                │
                ▼                                ▼
┌────────────────────────────┐   ┌─────────────────────────────────┐
│   coordinator.py           │   │  Platforms (HA glue)            │
│   OnectaDataUpdateCoord.   │◄──┤  climate / sensor / select /    │
│   - update_interval        │   │  switch / button / binary /     │
│   - exception translation  │   │  water_heater                   │
│   - rate-limit pacing      │   │  + diagnostics, system_health   │
└────────────────────────────┘   └─────────────────────────────────┘
                │                                ▲
                ▼                                │ device.json_data walks
┌────────────────────────────┐   ┌─────────────────────────────────┐
│   daikin_api.py            │──►│  device.py                      │
│   - OAuth2Session          │   │  DaikinOnectaDevice (per-device │
│   - doBearerRequest        │   │  wrapper, get/set walks)        │
│   - _cloud_lock            │   └─────────────────────────────────┘
│   - rate_limits            │
│   - CircuitBreaker hook    │
│   - retry on getCloud…     │
└────────────────────────────┘
                │
                ▼
┌────────────────────────────┐
│   support/                 │
│   retry · circuit_breaker  │
│   · throttle               │
└────────────────────────────┘
                │
                ▼
        Daikin Onecta Cloud
        (idp.onecta.daikineurope.com,
         api.onecta.daikineurope.com)
```

## Data flow

1. **Setup** (`__init__.py::async_setup_entry`)
   1. Build `DaikinApi` from the OAuth2 implementation.
   2. Stash it on `config_entry.runtime_data` together with the
      coordinator and per-device wrappers.
   3. `coordinator.async_config_entry_first_refresh()` does the first
      poll.
   4. Forward to the seven platforms (climate, sensor, water_heater,
      switch, select, binary_sensor, button).

2. **Polling** (`coordinator._async_update_data`)
   1. `determine_update_interval()` chooses high vs. low scan interval
      by time of day.
   2. After a write, the coordinator skips GETs for `scan_ignore`
      seconds (cloud returns stale data otherwise — see
      [§ Stale-read protection](#stale-read-protection)).
   3. `daikin_api.getCloudDeviceDetails()` runs the GET. Transient
      errors are retried with backoff. Persistent errors open the
      circuit breaker.
   4. Daikin\* exceptions are translated into
      `ConfigEntryAuthFailed` / `UpdateFailed`.

3. **Write** (entity `async_set_*`)
   1. The platform calls `device.patch(path, options)`.
   2. `daikin_api.doBearerRequest("PATCH", …)` acquires `_cloud_lock`,
      sends the PATCH, records `_last_patch_call`, releases the lock.
   3. The next coordinator tick honors the `scan_ignore` window.

## Key invariants

### Stale-read protection

The Daikin cloud frequently returns stale device state if a `GET` runs
immediately after a `PATCH`. Two mechanisms guard against this:

- **`_cloud_lock`** (`daikin_api.DaikinApi`) — an `asyncio.Lock` that
  serializes every HTTP call against the cloud. No PATCH/GET overlap is
  possible.
- **`scan_ignore`** (`coordinator.OnectaDataUpdateCoordinator`) — after
  a successful PATCH, GETs are skipped for N seconds (default 30,
  configurable via options flow).

### Rate limits

The cloud surfaces remaining quota in
`X-RateLimit-Remaining-{minute,day}`. We:

- update `daikin_api.rate_limits` on every response;
- expose them via `system_health` and a sensor;
- when `remaining_day == 0`, force `update_interval = retry_after + 60s`.

The proactive `RateLimitThrottle` in `support/throttle.py` is wired and
testable but **not yet** consumed by the coordinator — that hook-up is
deferred to the phase-7 domain model (see ADR 0003).

### Circuit breaker

A `CircuitBreaker(failure_threshold=5, recovery_timeout=60s)` wraps
`doBearerRequest`. Five consecutive `ClientError`s open it; further
calls fail fast with `CircuitBreakerOpenError` until the recovery
timeout elapses. 429 responses do **not** count as failures (expected
state). See ADR 0002.

## Module map

| Module                               | Responsibility                                          |
| ------------------------------------ | ------------------------------------------------------- |
| `__init__.py`                        | HA setup, unload, config-entry migration                |
| `application_credentials.py`         | OAuth2 client registration                              |
| `config_flow.py`                     | OAuth2 flow + reauth + JWT-`sub` unique-id              |
| `coordinator.py`                     | Polling cadence, exception translation                  |
| `daikin_api.py`                      | HTTP transport, OAuth, rate-limit telemetry, cloud lock |
| `device.py`                          | Per-device JSON wrapper, get/set helpers                |
| `exceptions.py`                      | `DaikinError` hierarchy                                 |
| `const.py`                           | Constants and the central `VALUE_SENSOR_MAPPING`        |
| `support/`                           | Retry, circuit breaker, throttle (no HA deps)           |
| `climate.py` etc.                    | HA platform glue                                        |
| `diagnostics.py`, `system_health.py` | HA diagnostic surfaces                                  |

## See also

- ADR [0001 — Record architecture decisions](adr/0001-record-architecture-decisions.md)
- ADR [0002 — Resilience patterns](adr/0002-resilience-patterns.md)
- ADR [0003 — Domain-model package layout](adr/0003-domain-model-package-layout.md) (Proposed)
- ADR [0004 — Cloud lock & scan_ignore](adr/0004-cloud-lock-and-scan-ignore.md)
- ADR [0005 — Polling strategy](adr/0005-polling-strategy.md)
