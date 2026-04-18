# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html)
(see [`docs/versioning.md`](docs/versioning.md) for the project-specific policy).

For releases prior to the introduction of this file, see the
[GitHub Releases page](https://github.com/jwillemsen/daikin_onecta/releases) —
release notes there are auto-generated from PR titles and remain the
authoritative record.

## [Unreleased]

## [4.5.0] — 2026-04-18

Large engineering release — no breaking changes to HA entities or
config, but the internal architecture was substantially reworked.

### Added

- **Domain-model package** (`model/`) — typed wrappers around the cloud
  JSON: `DaikinOnectaDevice`, `ManagementPoint` with per-type subclasses
  (`ClimateControlPoint`, `DomesticHotWaterTankPoint`, `GatewayPoint`, …),
  and a frozen `DataPoint` view over every `{value, settable, minValue,
  maxValue, stepValue}` field. Platforms now use
  `device.iter_management_points()` / `device.find_management_point()`
  instead of walking raw `daikin_data["managementPoints"]`. See ADR
  [`docs/adr/0003-domain-model-package-layout.md`](docs/adr/0003-domain-model-package-layout.md).
- **Transport-layer split** (`client/`) — `DaikinApi` moved to
  `client/api.py`; top-level `daikin_api.py` / `device.py` are thin
  re-export shims so external imports keep working.
- **Model-level event listeners** — `DaikinOnectaDevice` exposes
  `add_listener`, `add_management_point_listener`, and
  `add_data_point_listener`. `setJsonData()` diffs the payload and only
  fires listeners for fields whose value actually changed; all seven
  platforms moved from `CoordinatorEntity._handle_coordinator_update`
  to scoped model subscriptions. See ADR
  [`docs/adr/0006-model-event-listeners.md`](docs/adr/0006-model-event-listeners.md).
- **Resilience layer** (`support/`) — `@retry_with_backoff` decorator,
  `CircuitBreaker` (CLOSED / OPEN / HALF_OPEN), `RateLimitThrottle` for
  proactive pacing. Wired into `daikin_api.doBearerRequest` and
  `getCloudDeviceDetails`. See ADR
  [`docs/adr/0002-resilience-patterns.md`](docs/adr/0002-resilience-patterns.md).
- **Custom exception hierarchy** (`exceptions.py`): `DaikinError` with
  subclasses `DaikinAuthError`, `DaikinRateLimitError`, `DaikinApiError`,
  `DaikinDeviceError`, `DaikinValidationError`. The coordinator
  translates them into `ConfigEntryAuthFailed` / `UpdateFailed`.
- **Tooling baseline**: central `pyproject.toml` (ruff, mypy, pylint,
  bandit, coverage, pytest, codespell), prek hook suite, CI jobs for
  mypy / bandit / pylint / CodeQL / dependency review, `codecov.yml`
  with component tracking.
- **Test suite**: new `test_support.py`, `test_daikin_api.py`,
  `test_migrate.py`, `test_device_listeners.py`,
  `test_management_point.py`, `test_data_point.py`,
  `test_fixture_contract.py` — 28 → 151 tests, line coverage
  ≈ 94 %, verified under `pytest-xdist`.
- **Documentation**: `SECURITY.md`, `CONTRIBUTING.md`, `AGENTS.md`,
  `SUPPORT.md`, `docs/architecture.md`, `docs/security.md`,
  `docs/versioning.md`, `docs/release.md`, `mkdocs.yml`. ADRs 0001–0006
  cover recording architecture decisions, resilience patterns, the
  domain-model layout, cloud-lock / scan-ignore, the polling strategy,
  and the new event-listener system.

### Changed

- **Entity refresh model**: entities no longer rely on the coordinator
  broadcast (`_handle_coordinator_update`). Each entity subscribes at
  the granularity it needs — DataPoint for single-field sensors /
  switches / selects, management-point for climate and water heater,
  device-wide for the refresh button and the rate-limit sensor.
  Identical polls now produce zero redundant `async_write_ha_state`
  calls.
- **Logging hygiene**: request / response bodies in the cloud client
  moved from `INFO` to `DEBUG` to keep cloud identifiers out of default
  logs.
- **Type safety**: all modules typed; `mypy --strict
  --python-version 3.14` reports 0 errors (baseline was 49). `__all__`
  declared on every public module.
- **Hook runner**: migrated from `pre-commit` to
  [`prek`](https://github.com/j178/prek), a drop-in Rust rewrite. The
  `.pre-commit-config.yaml` is unchanged; CI uses
  `j178/prek-action@v2`; `pre-commit` itself still works locally.

### Security

- Bandit baseline reviewed; the two low-severity false positives
  (`OAUTH2_TOKEN` URL constant, `random.randint` jitter) are annotated
  with `# nosec` plus justification.
- `.gitleaks.toml` added with an allowlist for the documented test JWT
  and fixture paths.

## [4.4.10] — 2026-04-15

- See <https://github.com/jwillemsen/daikin_onecta/releases/tag/v4.4.10>.

## [4.4.0] – [4.4.9]

- See <https://github.com/jwillemsen/daikin_onecta/releases>.
- Highlights: water-heater fixes, additional translations, manifest
  bumps for newer Home Assistant Core minimums, redaction of token data
  in diagnostics.

## [4.3.0] – [4.3.3]

- See <https://github.com/jwillemsen/daikin_onecta/releases>.
- Highlights: Finnish, German, Norwegian translations; rate-limit
  remaining-day sensor; broader test coverage.

## [4.2.0] – [4.2.13]

- See <https://github.com/jwillemsen/daikin_onecta/releases>.
- Highlights: sub-device grouping, software/hardware version moved into
  the device registry, system-health entries renamed and translated.

## [4.1.0] – [4.1.x]

- See <https://github.com/jwillemsen/daikin_onecta/releases>.
- Highlights: Python 3.13 support, swing-mode fix, schedule rate-limit
  test coverage.

## [4.0.0] – [4.0.x]

- See <https://github.com/jwillemsen/daikin_onecta/releases>.
- Highlights: `turn_on`/`turn_off` on water_heater, dry/humidification
  mapping, dry-mode without fanspeed control.

## Older

For changes before 4.0, please refer to
<https://github.com/jwillemsen/daikin_onecta/releases>.
