# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Home Assistant custom integration (`domain: daikin_onecta`) for Daikin devices via the Daikin Onecta cloud API. `iot_class: cloud_polling`, OAuth2 via `application_credentials`. All integration code lives under `custom_components/daikin_onecta/`. Distributed via HACS.

## Common commands

Tests (Python 3.13, requires `pip install -r requirements_test.txt`):

```bash
pytest tests                               # full suite (config in setup.cfg uses --cov)
pytest tests/test_init.py::<test_name>     # single test
pytest -n auto --timeout=9 tests           # how CI runs it (.github/workflows/tests.yaml)
```

Linting / formatting is driven by pre-commit (ruff + ruff-format + `reorder-python-imports`):

```bash
pre-commit run --all-files
```

`pyproject.toml` is intentionally near-empty — tool config lives in `setup.cfg` (flake8, isort, pytest, coverage). Note `setup.cfg` declares `max-line-length = 88` and `force_single_line = true` for imports.

## Architecture

The integration is a thin Home Assistant wrapper around the Daikin Onecta REST API. The cloud returns one large JSON document per account containing all devices and their `managementPoints`; entities are derived by walking that structure.

**Setup flow (`__init__.py`)**

1. `async_setup_entry` builds a `DaikinApi` from the OAuth2 implementation, stashes it on `config_entry.runtime_data` (an `OnectaRuntimeData` dataclass holding `daikin_api`, `coordinator`, `devices`).
2. `OnectaDataUpdateCoordinator.async_config_entry_first_refresh()` runs the first poll; only then are the seven platforms forwarded: climate, sensor, water_heater, switch, select, binary_sensor, button.
3. `async_migrate_entry` handles config-entry schema migrations (e.g. v1.1→v1.2 decodes the JWT `sub` to set `unique_id`).

**API layer (`daikin_api.py`)**

- `DaikinApi` owns an `asyncio.Lock` (`_cloud_lock`) that serializes every HTTP call to Daikin. This exists because the cloud returns stale data when a GET races a recent PATCH.
- `_last_patch_call` records the most recent write; the coordinator skips GETs for `scan_ignore` seconds (default 30) after a PATCH for the same reason.
- `rate_limits` is updated from response headers and consumed by both the coordinator (back-off) and the diagnostics/system_health platforms.

**Coordinator (`coordinator.py`)**

`determine_update_interval` picks between two configurable intervals based on time of day (`high_scan_start`/`low_scan_start`, in minutes). When transitioning high→low the first poll is randomized to spread load across users. When `rate_limits["remaining_day"] == 0`, the interval is forced to `retry_after + 60s`.

**Devices and entities (`device.py` + platform files)**

`DaikinOnectaDevice` wraps a single device's JSON. Each platform (e.g. `climate.py`, `sensor.py`) iterates `daikin_api.json_data` → `managementPoints` and creates entities for the data points it understands. `const.py::VALUE_SENSOR_MAPPING` is the central registry mapping Daikin JSON field names to HA `device_class`/`state_class`/`unit`/`icon`/translation key — most new sensors are added by extending that dict plus the matching key in `translations/`.

`climate.py` is the largest module (~850 lines) and handles the variety of Daikin units (split AC, Altherma heat pumps, etc.); `water_heater.py` covers domestic-hot-water tanks. New device behaviors usually mean handling another `managementPointType` or operationMode value here rather than adding a new platform.

## Tests

- `tests/conftest.py` defines `MockConfigEntry` + `snapshot_platform_entities` helper. Test fixtures are saved Daikin cloud responses in `tests/fixtures/*.json` — to add coverage for a new device type, drop in its JSON and reference it via the existing snapshot helper.
- Snapshot baselines live in `tests/snapshots/*.ambr` (syrupy). Update with `pytest --snapshot-update`.
- `pytest_homeassistant_custom_component` provides the `hass` fixture and `AiohttpClientMocker` used to stub the `/v1/gateway-devices` endpoint.

## Versioning

Bump `custom_components/daikin_onecta/manifest.json::version` for releases (HACS reads it). `hacs.json` controls HACS metadata.
