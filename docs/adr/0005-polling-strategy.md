# 5. Polling strategy

Date: 2026-04-17

## Status

Accepted (records existing behavior — predates the ADR process)

## Context

`daikin_onecta` is a `cloud_polling` integration. The Daikin cloud
imposes a per-minute and per-day rate limit (visible in
`X-RateLimit-Remaining-{minute,day}`); the per-day budget is the
binding one for a typical multi-device household.

A naive constant-interval poll either burns the daily budget by
mid-afternoon or undersamples device state to the point of being
unhelpful for automations.

## Decision

The coordinator picks one of two intervals based on time of day:

- **High-frequency window** — between `high_scan_start` and
  `low_scan_start`. Default 9 minutes.
- **Low-frequency window** — outside the high window (typically
  overnight). Default 30 minutes.

Both intervals and both window edges are user-configurable via the
options flow.

### Spreading load on the high→low edge

When the coordinator transitions from low into high (typically at
07:00–09:00 local time), all installations would otherwise hit the
cloud within the same one-second tick. To spread that thundering herd,
the **first** poll inside the high window is randomized between 60
seconds and `high_scan_interval`. Subsequent polls follow the
configured cadence.

### Rate-limit fallback

If `daikin_api.rate_limits["remaining_day"] == 0` we override the
chosen interval to `retry_after + 60s` (with `retry_after` taken from
the cloud's response). This pauses polling until the daily quota
resets, instead of generating a wave of `429`s.

## Consequences

- **Positive:** the daily budget is enough for a typical setup
  (1–4 devices) even with the high-frequency window covering waking
  hours.
- **Positive:** randomized first poll keeps the cloud (and other
  users) from being hammered at exactly 07:00:00.
- **Negative:** automations that need sub-minute reaction to *external*
  device state changes are not viable on this integration —
  `cloud_polling` plus the rate limit makes that a non-goal.
- **Future:** the `RateLimitThrottle` (see ADR 0002) is wired in
  `support/throttle.py` but not yet consumed by the coordinator. Once
  the phase-7 domain model exposes per-DataPoint write frequencies, we
  will fold its `recommended_delay()` into the interval choice instead
  of the binary "0 vs. retry_after" check.

## Rejected alternatives

- **Constant interval (e.g. 5 min):** burns the daily budget on a
  multi-gateway account, generates `429`s before sundown.
- **Adaptive interval based on detected change frequency:** would need
  per-DataPoint history; deferred until the domain model exists.
- **WebSockets / push:** the Onecta cloud does not offer a push
  channel that we could subscribe to.
