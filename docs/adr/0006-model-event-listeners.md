# 6. Model-level event listeners replace the coordinator broadcast

Date: 2026-04-18

## Status

Accepted (implemented in phase 7.9)

## Context

Before this change every platform entity was a
`CoordinatorEntity[OnectaDataUpdateCoordinator]` and relied on
`_handle_coordinator_update`. After each successful poll the coordinator
pushed the cloud JSON into every `DaikinOnectaDevice` via
`setJsonData(...)` and then broadcast a single refresh signal to _all_
entities for _all_ devices — each entity recomputed its state even if
none of its own DataPoints had changed.

This had two drawbacks:

1. **No diffing.** Identical polls (the common case — most Daikin units
   don't change state between 10-minute GETs) still triggered a full
   fan-out of `update_state() + async_write_ha_state()` for every
   entity.
2. **No locality.** An entity that reflects a single field (e.g. the
   binary sensor for `installerState`) re-rendered whenever _any_ field
   on _any_ device changed. Platforms could not subscribe to just the
   data they actually read.

Phase 7 extracted the typed domain model (`model/device.py`,
`model/management_point.py`, `model/data_point.py`). With the value
wrappers in place, adding a change-detecting event system at the model
layer became feasible.

## Decision

`DaikinOnectaDevice` now owns a listener registry with three
granularities:

- `add_listener(callback)` — device-wide; fires when any DataPoint
  changes or when `available` (derived from `isCloudConnectionUp`)
  toggles.
- `add_management_point_listener(embedded_id, callback)` — fires when
  any DataPoint under a specific management point changes.
- `add_data_point_listener(embedded_id, name, callback)` — fires when
  exactly one `(embedded_id, field)` DataPoint's `value` changes.

Each `add_*` call returns an unsubscribe callable; platforms pass it to
`Entity.async_on_remove` in `async_added_to_hass`.

`setJsonData(...)` takes a value-level snapshot before and after the
merge (`_snapshot_data_point_values`), computes the set of changed keys,
and dispatches listeners in DataPoint → management-point → device order.
`available` changes are tracked separately since `isCloudConnectionUp`
lives outside the management points.

All seven platforms were migrated off `_handle_coordinator_update`:

| Platform                    | Subscription scope               | Rationale                                                                  |
| --------------------------- | -------------------------------- | -------------------------------------------------------------------------- |
| `binary_sensor.py`          | DataPoint (one field per entity) | Reads exactly one boolean field.                                           |
| `switch.py`                 | DataPoint                        | Reads one on/off field.                                                    |
| `select.py`                 | DataPoint                        | Reads one schedule field (nested dict, diff goes deep via value-compare).  |
| `sensor.DaikinEnergySensor` | DataPoint (`consumptionData`)    | All energy variants live under one DataPoint.                              |
| `sensor.DaikinValueSensor`  | DataPoint                        | Subscribes to either `value` or `sub_type` (the actual top-level key).     |
| `sensor.DaikinLimitSensor`  | device                           | Rate-limits live on the API, not the model — uses the coarse device event. |
| `water_heater.py`           | management point                 | Reads many fields on one MP — finer subscription would mean many handlers. |
| `climate.py`                | management point                 | Same reasoning — climate entities depend on ~10 fields on one MP.          |
| `button.py`                 | device                           | Refresh button only cares about availability.                              |

The coordinator still polls the cloud, still calls `setJsonData` on each
device, and is still created and wired on setup. It just no longer owns
the entity-refresh broadcast — the model does.

## Consequences

**Positive**

- Entities only repaint when their own data actually changed. Identical
  polls produce no `async_write_ha_state` calls.
- Platforms state their dependencies explicitly via the subscription
  scope — easier to reason about which field a handler needs.
- The model stays HA-independent: `Listener = Callable[[], None]`
  captures whatever the subscriber needs via closure; the model never
  imports `hass` or `dispatcher`.

**Negative**

- `DaikinLimitSensor` refreshes only when at least one DataPoint on the
  device changed. In practice every successful poll carries updated
  timestamps or rate-limit-sensitive fields, so the staleness window is
  bounded — but it's not zero. Acceptable because the limit sensor is
  diagnostic, not operational.
- `setJsonData` now takes two O(fields) snapshots per poll. The
  management-point / data-point iteration was already present through
  `iter_management_points()`; the added cost is a dict build and a set
  diff, both trivial relative to network I/O.

## Alternatives rejected

- **HA dispatcher (`async_dispatcher_send`).** Would couple the model to
  `hass` and spread signal-string conventions across the codebase. The
  model-internal API is both simpler and testable without HA.
- **Event on every poll, no diff.** Would keep the "all entities
  repaint" behaviour and defeat the point of the refactor.
- **Full removal of `CoordinatorEntity`.** Entities still benefit from
  the coordinator's lifecycle integration (first refresh, availability
  gating, config-entry teardown). The refactor swaps the update
  mechanism, not the parent class.
