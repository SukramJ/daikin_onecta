# 3. Package layout for the domain model

Date: 2026-04-17

## Status

Proposed (implementation in phase 7)

## Context

The HA platform modules (`climate.py` ≈ 850 lines, `water_heater.py`,
`sensor.py`) currently walk the large cloud JSON directly
(`daikin_data["managementPoints"][...]`). That has three consequences:

1. **Duplicate logic:** every platform implements the same `get/set`
   walks for setpoints, operationModes, onOff, etc.
2. **Hard to test:** tests have to bring up the whole HA pipeline
   because there is no layer between JSON and entity.
3. **Blocker for robustness:** throttle and circuit breaker live at the
   transport layer; the model is completely decoupled from resilience
   logic — nothing knows the semantics of individual data points.

## Decision

We split the package into four clearly separated layers (analogous to
`aiohomematic`):

```
custom_components/daikin_onecta/
├── client/         # Transport: HTTP, OAuth, retry, circuit breaker
│   ├── api.py            # formerly daikin_api.py
│   └── exceptions.py     # formerly exceptions.py (transport-level)
├── model/          # Domain: typed DataPoints, ManagementPoints, Devices
│   ├── data_point.py     # unified value/min/max/stepValue interface
│   ├── management_point.py   # classes per type (climateControl, gateway, …)
│   └── device.py         # formerly device.py, without JSON walks
├── support/        # Resilience (already in place: retry, circuit_breaker, throttle)
└── platforms/      # Thin HA glue (climate, water_heater, sensor, …)
    ├── climate.py
    └── …
```

**Migration path (one module per PR, not everything at once):**

1. `support/` is already introduced (phase 6).
2. Extract `client/api.py` from `daikin_api.py` — re-export from the
   old path as a transition.
3. Extract `model/device.py` from `device.py`, move the JSON walks
   into `model/management_point.py`.
4. Introduce `model/data_point.py` — a DataPoint wraps
   `{value, min, max, step, settable}` and knows its write path.
5. Migrate platforms one by one to `model.iter_data_points()`.
6. Remove the old paths once no imports point to them anymore.

**Re-exports during migration:** the old import paths keep working until
all internal and external consumers are migrated — this prevents
breaking tests and HACS updates within a single release phase.

## Consequences

- **Positive:** platform modules shrink drastically (estimate for
  `climate.py`: 850 → < 250 lines).
- **Positive:** tests can exercise DataPoints/ManagementPoints in
  isolation, without the HA pipeline.
- **Positive:** throttle and schema validation (phase 5.5) get a
  meaningful attachment point in the model.
- **Risk (🔴):** the largest planned refactor in the repo. Therefore
  start only after solid test coverage is in place.
- **Risk:** HA exposes various lifecycle hooks on the entity
  (`available`, `_handle_coordinator_update`) — these need clean hooks
  in the model, otherwise values will diverge.
- **Consequence:** ADR 0002 remains valid; `support/` already lives
  where it belongs.
