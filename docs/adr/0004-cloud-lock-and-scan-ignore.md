# 4. Cloud lock and scan_ignore

Date: 2026-04-17

## Status

Accepted (records existing behavior — predates the ADR process)

## Context

In practice the Daikin Onecta cloud has two timing properties that the
public documentation does not cover:

1. **Concurrent requests on the same account observe inconsistent
   state.** Two `GET`s issued in parallel against the same
   `gateway-devices` resource sometimes return one fresh and one stale
   document.
2. **A `GET` issued immediately after a `PATCH` returns the
   pre-PATCH state.** The window in which this happens is roughly
   10–30 seconds.

Without protection, the user experience is "I turned the AC off in the
HA UI and it bounces back to on for one tick." Worse, if the
coordinator polls inside that window it overwrites the entity state
with the stale value.

## Decision

We accept two coupled mechanisms in the integration:

### `_cloud_lock` (`daikin_api.DaikinApi`)

An `asyncio.Lock` is held across **every** HTTP call to the cloud,
including reads. This serializes calls per Home Assistant instance,
which empirically is enough to avoid the concurrent-read inconsistency.

The lock lives in the API layer, not in the coordinator, so writes
issued by entity callbacks are also covered.

### `scan_ignore` (`coordinator.OnectaDataUpdateCoordinator`)

After a successful `PATCH`, `daikin_api._last_patch_call` is set to
`datetime.now()`. The coordinator's `_async_update_data` skips its GET
if `now - _last_patch_call < scan_ignore` seconds. Default is 30 s,
exposed in the options flow.

This buys us time for the cloud to settle without losing the user's
write.

## Consequences

- **Positive:** entity state stays consistent with what the user last
  set, even under bursts of writes.
- **Positive:** parallel HA service calls do not race each other against
  the cloud.
- **Negative:** the lock turns the integration into a single-flight
  bottleneck — only one call to the Daikin cloud is in flight at any
  moment per HA instance. For a cloud-polling integration with a
  default cadence of minutes, this is acceptable.
- **Negative:** `scan_ignore` delays observability of _external_
  changes (someone using the Onecta phone app while HA is also
  managing the device). Default of 30 s is the empirical sweet spot —
  shorter values reintroduce the stale-read bug.

## Rejected alternatives

- **Per-device lock instead of global lock:** does not help, because the
  inconsistency is observed at the account level (the cloud serializes
  per account, not per device).
- **Optimistic write with re-read:** would generate two GETs per write
  and still hit the stale-read window.
- **Polling the cloud's "last-modified" header to detect freshness:**
  the header is not reliable for this resource (sometimes lags the
  actual change by minutes).
