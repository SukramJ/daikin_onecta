# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Home Assistant custom integration (`domain: daikin_onecta`) for Daikin devices via the Daikin Onecta cloud API. `iot_class: cloud_polling`, OAuth2 via `application_credentials`. All integration code lives under `custom_components/daikin_onecta/`. Distributed via HACS.

## Common commands

Tests (Python 3.13 or 3.14 — CI matrix covers both; requires `pip install -r requirements_test.txt`):

```bash
pytest tests                               # full suite (coverage via pyproject.toml)
pytest tests/test_init.py::<test_name>     # single test
pytest -n auto --timeout=9 tests           # how CI runs it (.github/workflows/tests.yaml)
```

Linting / formatting is driven by prek (a drop-in Rust rewrite of pre-commit; reads the same `.pre-commit-config.yaml`). Hooks: ruff + ruff-format + `reorder-python-imports` + codespell + yamllint + prettier + bandit + mypy + pylint + custom `lint-all-exports` / `check-i18n`:

```bash
prek run --all-files          # or: pre-commit run --all-files
```

All tool config lives in `pyproject.toml` (`[tool.ruff]`, `[tool.mypy]`, `[tool.pylint]`, `[tool.bandit]`, `[tool.coverage]`, `[tool.pytest.ini_options]`, `[tool.codespell]`). `setup.cfg` was removed in phase 1. `mypy --strict --python-version 3.14` is clean; `coverage fail_under = 80` (current: ~94 %).

## Architecture

The integration is a thin Home Assistant wrapper around the Daikin Onecta REST API. The cloud returns one large JSON document per account containing all devices and their `managementPoints`; typed domain objects are derived from that structure.

**Package layout (ADR 0003)**

```
custom_components/daikin_onecta/
├── client/       # transport: HTTP, OAuth, retry, circuit breaker
│   └── api.py    # DaikinApi
├── model/        # domain: typed wrappers around cloud JSON
│   ├── device.py             # DaikinOnectaDevice
│   ├── management_point.py   # ManagementPoint + per-type subclasses
│   └── data_point.py         # DataPoint (value/settable/min/max/step)
├── support/      # resilience primitives
│   ├── retry.py              # @retry_with_backoff
│   ├── circuit_breaker.py    # CircuitBreaker (CLOSED/OPEN/HALF_OPEN)
│   └── throttle.py           # RateLimitThrottle
├── daikin_api.py  # re-export shim → client.api (internal imports keep working)
├── device.py      # re-export shim → model.device
└── climate.py, sensor.py, water_heater.py, switch.py, select.py,
    binary_sensor.py, button.py   # HA platforms
```

`daikin_api.py` and `device.py` are thin re-export shims; new code should import directly from `client/` and `model/`.

**Setup flow (`__init__.py`)**

1. `async_setup_entry` builds a `DaikinApi` from the OAuth2 implementation, stashes it on `config_entry.runtime_data` (an `OnectaRuntimeData` dataclass holding `daikin_api`, `coordinator`, `devices`).
2. `OnectaDataUpdateCoordinator.async_config_entry_first_refresh()` runs the first poll; only then are the seven platforms forwarded: climate, sensor, water_heater, switch, select, binary_sensor, button.
3. `async_migrate_entry` handles config-entry schema migrations (e.g. v1.1→v1.2 decodes the JWT `sub` to set `unique_id`).

**Transport layer (`client/api.py`)**

- `DaikinApi` owns an `asyncio.Lock` (`_cloud_lock`) that serializes every HTTP call to Daikin. This exists because the cloud returns stale data when a GET races a recent PATCH.
- `_last_patch_call` records the most recent write; the coordinator skips GETs for `scan_ignore` seconds (default 30) after a PATCH for the same reason.
- `rate_limits` is updated from response headers and consumed by both the coordinator (back-off) and the diagnostics/system_health platforms.
- A `CircuitBreaker` (5 failures → OPEN → 60 s → HALF_OPEN) wraps `doBearerRequest`; `getCloudDeviceDetails` is additionally retried with exponential backoff + jitter. Exceptions map to `DaikinAuthError` / `DaikinRateLimitError` / `DaikinApiError` from `exceptions.py`.

**Coordinator (`coordinator.py`)**

`determine_update_interval` picks between two configurable intervals based on time of day (`high_scan_start`/`low_scan_start`, in minutes). When transitioning high→low the first poll is randomized to spread load across users. When `rate_limits["remaining_day"] == 0`, the interval is forced to `retry_after + 60s`. Daikin exceptions are translated into `ConfigEntryAuthFailed` / `UpdateFailed` for HA.

**Domain model (`model/`)**

`DaikinOnectaDevice` wraps a single device's JSON and exposes two helpers that the platforms use instead of walking `daikin_data` directly:

- `device.iter_management_points()` → `Iterator[ManagementPoint]` — yields a typed wrapper per management-point, dispatched by `managementPointType` (`ClimateControlPoint`, `DomesticHotWaterTankPoint`, `GatewayPoint`, `IndoorUnitPoint`, `OutdoorUnitPoint`, `UserInterfacePoint`, …; unknown types fall back to the base class).
- `device.find_management_point(embedded_id)` → `ManagementPoint | None` — lookup by embedded id.
- `device.iter_data_points()` → `Iterator[DataPoint]` — flattens every `{value, settable, minValue, maxValue, stepValue}` field across all management points into frozen `DataPoint` records.

Each `ManagementPoint` keeps its raw dict on `.raw` for partially migrated callers. `const.py::VALUE_SENSOR_MAPPING` remains the central registry mapping Daikin JSON field names to HA `device_class` / `state_class` / `unit` / `icon` / translation key — most new sensors are added by extending that dict plus the matching key in `translations/`.

`climate.py` is the largest platform (~850 lines) and handles the variety of Daikin units (split AC, Altherma heat pumps, etc.); `water_heater.py` covers domestic-hot-water tanks. New device behaviors usually mean handling another `managementPointType` or operationMode value here rather than adding a new platform.

## Tests

- `tests/conftest.py` defines `MockConfigEntry` + `snapshot_platform_entities` helper. Test fixtures are saved Daikin cloud responses in `tests/fixtures/*.json` — to add coverage for a new device type, drop in its JSON and reference it via the existing snapshot helper.
- Snapshot baselines live in `tests/snapshots/*.ambr` (syrupy). Update with `pytest --snapshot-update`.
- `pytest_homeassistant_custom_component` provides the `hass` fixture and `AiohttpClientMocker` used to stub the `/v1/gateway-devices` endpoint.

## Versioning

Bump `custom_components/daikin_onecta/manifest.json::version` for releases (HACS reads it). `hacs.json` controls HACS metadata.
