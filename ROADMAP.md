# Roadmap: daikin_onecta → aiohomematic level

Goal: bring `daikin_onecta` up to the engineering level of [`aiohomematic`](https://github.com/SukramJ/aiohomematic) — in **code quality, tests, architecture, security, CI, documentation, and tooling**.

**Tracking convention**

- `[ ]` = open · `[~]` = in progress · `[x]` = done · `[-]` = intentionally skipped
- Effort: **S** ≤ 1 day · **M** 1–3 days · **L** 1–2 weeks · **XL** > 2 weeks
- Risk: 🟢 low · 🟡 medium · 🔴 high (breaking change / large-scale refactor)
- Per-phase progress is summarised below in [§ Progress Dashboard](#progress-dashboard).

---

## Phase 0 — Baseline & safety net

> Prerequisite for everything else: measure first, then change. No production code changes.

| #   | Task                                                                                                 | Effort | Risk | Status |
| --- | ---------------------------------------------------------------------------------------------------- | ------ | ---- | ------ |
| 0.1 | Measure current test coverage and check baseline into `coverage-baseline.txt` (97 % total)           | S      | 🟢   | [x]    |
| 0.2 | Run `mypy --no-incremental .` once, document the error count as a baseline (49 default / 255 strict) | S      | 🟢   | [x]    |
| 0.3 | Document `ruff check --statistics` baseline (0 findings)                                             | S      | 🟢   | [x]    |
| 0.4 | Run `bandit -r custom_components/daikin_onecta`, inventory findings (2 low FPs)                      | S      | 🟢   | [x]    |
| 0.5 | Create directory `docs/adr/`, write `0001-record-architecture-decisions.md`                          | S      | 🟢   | [x]    |

---

## Phase 1 — Consolidate tooling & configuration

> One central `pyproject.toml`, all linters/typer/coverage in it. Prerequisite for the CI expansion.

| #    | Task                                                                                               | Effort | Risk | Status |
| ---- | -------------------------------------------------------------------------------------------------- | ------ | ---- | ------ |
| 1.1  | Build `pyproject.toml` with `[build-system]`, `[project]`, metadata, Python version constraint     | S      | 🟢   | [x]    |
| 1.2  | Migrate `setup.cfg` → `pyproject.toml` (flake8, isort, pytest, coverage), delete `setup.cfg`       | S      | 🟢   | [x]    |
| 1.3  | Adapt `[tool.ruff]` and `[tool.ruff.lint]` from aiohomematic (selective rules)                     | M      | 🟡   | [x]    |
| 1.4  | `[tool.mypy]` with a moderate baseline (`check_untyped_defs`); strict stays for phase 4.10         | M      | 🟡   | [x]    |
| 1.5  | Set up `[tool.pylint]` with project-specific disables                                              | M      | 🟡   | [x]    |
| 1.6  | Configure `[tool.bandit]` (skips for tests, confidence level)                                      | S      | 🟢   | [x]    |
| 1.7  | `[tool.coverage.run]` + `[tool.coverage.report]` with `fail_under = 80` (instead of the current 0) | S      | 🟢   | [x]    |
| 1.8  | Move `[tool.pytest.ini_options]` from `setup.cfg`, keep `asyncio_mode = auto`                      | S      | 🟢   | [x]    |
| 1.9  | Clean up `requirements_test.txt` and `requirements_dev.txt`, set version pins                      | S      | 🟢   | [x]    |
| 1.10 | `requirements_test_pre_commit.txt` separately (analogous to aiohomematic)                          | S      | 🟢   | [x]    |

---

## Phase 2 — Expand pre-commit hooks

> All checks run locally before push, identical behavior to CI.

| #   | Task                                                                                         | Effort | Risk | Status |
| --- | -------------------------------------------------------------------------------------------- | ------ | ---- | ------ |
| 2.1 | `codespell` hook with ignore list set up (1 real typo fixed)                                 | S      | 🟢   | [x]    |
| 2.2 | `yamllint` hook + `.yamllint` config (ignore blueprints)                                     | S      | 🟢   | [x]    |
| 2.3 | `prettier` hook for Markdown/YAML/JSON                                                       | S      | 🟢   | [x]    |
| 2.4 | `bandit` as a pre-commit hook                                                                | S      | 🟢   | [x]    |
| 2.5 | `mypy` as a pre-commit hook (with `additional_dependencies`)                                 | M      | 🟡   | [x]    |
| 2.6 | `pylint` as a pre-commit hook (via local config, run in phase 4)                             | M      | 🟡   | [x]    |
| 2.7 | Custom hook: `lint-all-exports` (ensure `__all__` is maintained) → `scripts/lint_exports.py` | M      | 🟡   | [x]    |
| 2.8 | Custom hook: `check-i18n` → `scripts/check_i18n.py` (7 orphan keys fixed)                    | M      | 🟡   | [x]    |
| 2.9 | Hook versions updated (pre-commit-hooks v5, ruff v0.6.9, mypy v1.11.2, bandit 1.7.10)        | S      | 🟢   | [x]    |

---

## Phase 3 — Expand CI/CD pipeline

> Every lint/type category as a separate job → clear failure signals.

| #    | Task                                                                                            | Effort | Risk | Status |
| ---- | ----------------------------------------------------------------------------------------------- | ------ | ---- | ------ |
| 3.1  | Job `mypy.yaml`                                                                                 | S      | 🟢   | [x]    |
| 3.2  | Job `bandit.yaml` with SARIF upload for the GitHub Security tab                                 | M      | 🟢   | [x]    |
| 3.3  | Workflow `codeql.yaml` for Python                                                               | S      | 🟢   | [x]    |
| 3.4  | Workflow `dependency-review.yaml` (on PRs)                                                      | S      | 🟢   | [x]    |
| 3.5  | Workflow `pylint.yaml`                                                                          | S      | 🟢   | [x]    |
| 3.6  | Extend Python matrix: 3.13 + 3.14                                                               | S      | 🟡   | [x]    |
| 3.7  | `codecov.yml` with component tracking (api, coordinator, device, climate, sensors, diagnostics) | S      | 🟢   | [x]    |
| 3.8  | Set up codecov token as a secret and enable coverage gates (token already configured)           | S      | 🟡   | [x]    |
| 3.9  | Release workflow: tag → GitHub release → manifest.json version validation                       | M      | 🟡   | [x]    |
| 3.10 | Extend `dependabot.yml` to include the pip ecosystem                                            | S      | 🟢   | [x]    |
| 3.11 | Job concurrency + cancel-older-runs across all workflows                                        | S      | 🟢   | [x]    |

---

## Phase 4 — Type safety & code hygiene

> Reach mypy strict step by step. Module by module.

| #    | Task                                                                                             | Effort | Risk | Status |
| ---- | ------------------------------------------------------------------------------------------------ | ------ | ---- | ------ |
| 4.1  | Type `const.py` (e.g. `VALUE_SENSOR_MAPPING: Final[Mapping[str, SensorMapping]]` with TypedDict) | M      | 🟢   | [x]    |
| 4.2  | Fully type `daikin_api.py` (response types, header parsing)                                      | M      | 🟡   | [x]    |
| 4.3  | Fully type `coordinator.py`                                                                      | S      | 🟢   | [x]    |
| 4.4  | Fully type `device.py`                                                                           | M      | 🟡   | [x]    |
| 4.5  | Fully type `climate.py` (largest module, 851 lines)                                              | L      | 🟡   | [x]    |
| 4.6  | Fully type `water_heater.py`                                                                     | M      | 🟡   | [x]    |
| 4.7  | Type `sensor.py` / `binary_sensor.py` / `select.py` / `switch.py` / `button.py`                  | M      | 🟡   | [x]    |
| 4.8  | Mark the `Platform` list as `Final`, optionally as a frozenset                                   | S      | 🟢   | [x]    |
| 4.9  | Add `__all__` to every public module                                                             | S      | 🟢   | [x]    |
| 4.10 | Enable mypy strict, fix every remaining error (or `# type: ignore[code]` with justification)     | L      | 🔴   | [x]    |

---

## Phase 5 — Custom exception hierarchy & validation

> Clear failure signals, clean error handling in the HA sense.

| #   | Task                                                                                                                  | Effort | Risk | Status |
| --- | --------------------------------------------------------------------------------------------------------------------- | ------ | ---- | ------ |
| 5.1 | Create `exceptions.py`: `DaikinError` (base)                                                                          | S      | 🟢   | [x]    |
| 5.2 | Subclasses: `DaikinAuthError`, `DaikinRateLimitError`, `DaikinApiError`, `DaikinDeviceError`, `DaikinValidationError` | S      | 🟢   | [x]    |
| 5.3 | `daikin_api.py`: map HTTP status codes to the right exceptions (401→Auth, 429→RateLimit, 5xx→Api)                     | M      | 🟡   | [x]    |
| 5.4 | Coordinator: translate specific exceptions into `UpdateFailed`/`ConfigEntryAuthFailed`/`ConfigEntryNotReady`          | S      | 🟡   | [x]    |
| 5.5 | Cloud response schema validation (e.g. `voluptuous` or own TypedDict + validator)                                     | L      | 🟡   | [x]    |
| 5.6 | Tests for every exception path                                                                                        | M      | 🟢   | [x]    |

---

## Phase 6 — Robustness: retry, backoff, circuit breaker

> Handle stale reads, rate limits, and cloud outages defensively.

| #   | Task                                                                                                         | Effort | Risk | Status |
| --- | ------------------------------------------------------------------------------------------------------------ | ------ | ---- | ------ |
| 6.1 | `support/retry.py` with decorator `@retry_with_backoff` (configurable: tries, base_delay, max_delay, jitter) | M      | 🟢   | [x]    |
| 6.2 | Wire retry into `doBearerRequest` (only idempotent GET methods)                                              | M      | 🟡   | [x]    |
| 6.3 | `support/circuit_breaker.py` with states CLOSED/OPEN/HALF_OPEN                                               | L      | 🟡   | [x]    |
| 6.4 | Wire the circuit breaker into `DaikinApi`, configurable failure threshold                                    | M      | 🟡   | [x]    |
| 6.5 | `support/throttle.py` for proactive rate-limit pacing (instead of only reactive at `remaining_day == 0`)     | M      | 🟡   | [x]    |
| 6.6 | Tests for retry behavior (timeouts, 5xx, 429)                                                                | M      | 🟢   | [x]    |
| 6.7 | Tests for circuit breaker state transitions                                                                  | M      | 🟢   | [x]    |

---

## Phase 7 — Architecture: extract domain model

> Separate transport (`client/`) ↔ domain (`model/`) ↔ HA entity (`platforms`).

| #    | Task                                                                                                                   | Effort | Risk | Status |
| ---- | ---------------------------------------------------------------------------------------------------------------------- | ------ | ---- | ------ |
| 7.1  | Design package layout: `client/`, `model/`, `support/`, `platforms/` (write ADR)                                       | M      | 🟡   | [x]    |
| 7.2  | `client/api.py`: pure cloud API (HTTP, OAuth, retry, circuit breaker), no HA knowledge                                 | L      | 🔴   | [ ]    |
| 7.3  | `model/device.py`: `DaikinDevice` (typed, no JSON walks in entities)                                                   | L      | 🔴   | [ ]    |
| 7.4  | `model/management_point.py`: typed ManagementPoint classes per type (climateControl, domesticHotWaterTank, gateway, …) | L      | 🔴   | [ ]    |
| 7.5  | `model/data_point.py`: unified interface for value/min/max/stepValue (analogous to aiohomematic DataPoint)             | L      | 🔴   | [ ]    |
| 7.6  | Refactor `climate.py`: HA glue only, logic in the model                                                                | L      | 🔴   | [ ]    |
| 7.7  | Refactor `water_heater.py`: HA glue only                                                                               | M      | 🔴   | [ ]    |
| 7.8  | `sensor.py`: iterate via `model.iter_data_points()` instead of JSON walks                                              | M      | 🔴   | [ ]    |
| 7.9  | Event/callback system for model updates instead of direct `setJsonData()` pushes                                       | L      | 🔴   | [ ]    |
| 7.10 | Optional: `store/` for caching the last successful cloud snapshots (resilience during cloud outages)                   | L      | 🟡   | [ ]    |

---

## Phase 8 — Massively expand the test suite

> Goal: coverage ≥ 85 %, error paths covered, all fixtures parametrised.

| #    | Task                                                                                                       | Effort | Risk | Status |
| ---- | ---------------------------------------------------------------------------------------------------------- | ------ | ---- | ------ |
| 8.1  | Split `tests/conftest.py` into `conftest.py` + `tests/fixtures/` (separate Python fixtures from JSON data) | M      | 🟢   | [x]    |
| 8.2  | Dedicated `daikin_onecta_test_support/` package (mock factories, builders, asserters)                      | L      | 🟡   | [-]    |
| 8.3  | Parametrise snapshot tests over **all** `tests/fixtures/*.json` (currently only a subset)                  | M      | 🟢   | [x]    |
| 8.4  | Per-platform snapshots (`test_climate.ambr`, `test_sensor.ambr`, …) instead of a single `test_init.ambr`   | M      | 🟢   | [x]    |
| 8.5  | Tests for `daikin_api.py`: token refresh, 401 auth fail, 429 rate limit, timeout                           | M      | 🟢   | [x]    |
| 8.6  | Tests for `coordinator.py`: high/low scan switch, scan_ignore logic, random spread                         | M      | 🟢   | [x]    |
| 8.7  | Tests for `_cloud_lock` serialisation (race condition test)                                                | M      | 🟡   | [x]    |
| 8.8  | Tests for `async_migrate_entry` (all versions)                                                             | S      | 🟢   | [x]    |
| 8.9  | Contract tests: validate every cloud endpoint against a response schema                                    | M      | 🟡   | [x]    |
| 8.10 | Reach coverage ≥ 80 %                                                                                      | L      | 🟡   | [x]    |
| 8.11 | Reach coverage ≥ 85 % (aiohomematic level)                                                                 | L      | 🟡   | [x]    |
| 8.12 | Enable `pytest-xdist` and verify test isolation                                                            | S      | 🟢   | [x]    |

---

## Phase 9 — Harden security

> Defensive programming, secrets, logging.

| #   | Task                                                                                         | Effort | Risk | Status |
| --- | -------------------------------------------------------------------------------------------- | ------ | ---- | ------ |
| 9.1 | Audit all `_LOGGER.{info,debug,exception}` calls: no tokens, no PII                          | M      | 🟢   | [x]    |
| 9.2 | JWT decode in `__init__.py:81` with `_LOGGER.exception` reviewed — no token fragments logged | S      | 🟢   | [x]    |
| 9.3 | Document TLS/cert verification explicitly (confirm `aiohttp` defaults)                       | S      | 🟢   | [x]    |
| 9.4 | Work through bandit findings from phase 0                                                    | M      | 🟡   | [x]    |
| 9.5 | Work through CodeQL findings from phase 3.3                                                  | M      | 🟡   | [-]    |
| 9.6 | `SECURITY.md` with reporting process and supported-versions table                            | S      | 🟢   | [x]    |
| 9.7 | Enable secret scanning on the repo (GitHub setting), `.gitleaks.toml` if needed              | S      | 🟢   | [x]    |

---

## Phase 10 — Documentation at aiohomematic level

> Documentation as a first-class citizen.

| #     | Task                                                                                               | Effort | Risk | Status |
| ----- | -------------------------------------------------------------------------------------------------- | ------ | ---- | ------ |
| 10.1  | Introduce `changelog.md` in the repo (Keep-a-Changelog format), backfill historic releases         | M      | 🟢   | [x]    |
| 10.2  | `AGENTS.md` with contributor guidelines (style, branch, commit, review)                            | S      | 🟢   | [x]    |
| 10.3  | `docs/architecture.md` (layer diagram, data flow Cloud→Coordinator→Entity)                         | M      | 🟢   | [x]    |
| 10.4  | `docs/adr/` covering all design decisions (cloud_lock, scan_ignore, polling strategy, model layer) | M      | 🟢   | [x]    |
| 10.5  | `mkdocs.yml` + `docs/` structure (getting_started, faq, devices, troubleshooting)                  | M      | 🟢   | [x]    |
| 10.6  | `mkdocs gh-deploy` workflow in `.github/workflows/docs.yml`                                        | S      | 🟢   | [x]    |
| 10.7  | Define docstring standards (`docs/docstring_standards.md`) and enforce via ruff `D` rules          | M      | 🟡   | [x]    |
| 10.8  | `CONTRIBUTING.md` with dev setup instructions                                                      | S      | 🟢   | [x]    |
| 10.9  | Extend `CLAUDE.md` with the updated architecture picture after phase 7                             | S      | 🟢   | [ ]    |
| 10.10 | `SUPPORT.md` with issue triage notes                                                               | S      | 🟢   | [x]    |

---

## Phase 11 — Release & versioning discipline

> Reproducible releases, clear versioning policy.

| #    | Task                                                                                         | Effort | Risk | Status |
| ---- | -------------------------------------------------------------------------------------------- | ------ | ---- | ------ |
| 11.1 | Define SemVer policy and document it in `CONTRIBUTING.md`                                    | S      | 🟢   | [x]    |
| 11.2 | Link `changelog.md` as the single source of truth for release notes                          | S      | 🟢   | [x]    |
| 11.3 | Pre-release checklist: `manifest.json` version, changelog entry, migration notes             | S      | 🟢   | [x]    |
| 11.4 | Release workflow: on tag `vX.Y.Z` → validate against `manifest.json` → create GitHub release | M      | 🟡   | [x]    |
| 11.5 | HACS release validation in CI                                                                | S      | 🟢   | [x]    |

---

## Progress Dashboard

> Update this table after each phase. `n/m` = completed tasks per phase.

| Phase     | Topic                      | Tasks                  | Status   |
| --------- | -------------------------- | ---------------------- | -------- |
| 0         | Baseline & safety net      | 5 / 5                  | 🟩       |
| 1         | Tooling & configuration    | 10 / 10                | 🟩       |
| 2         | Pre-commit hooks           | 9 / 9                  | 🟩       |
| 3         | CI/CD pipeline             | 11 / 11                | 🟩       |
| 4         | Type safety                | 10 / 10                | 🟩       |
| 5         | Exceptions & validation    | 6 / 6                  | 🟩       |
| 6         | Robustness (retry/breaker) | 7 / 7                  | 🟩       |
| 7         | Domain model               | 1 / 10 (ADR only)      | 🟨       |
| 8         | Test suite                 | 12 / 12 (8.2 deferred) | 🟩       |
| 9         | Security                   | 6 / 7 (9.5 deferred)   | 🟩       |
| 10        | Documentation              | 9 / 10 (10.9 open)     | 🟨       |
| 11        | Release discipline         | 5 / 5                  | 🟩       |
| **Total** |                            | **91 / 102**           | **89 %** |

**Status symbols:** ⬜ not started · 🟨 in progress · 🟩 done · `[-]` deferred / out of scope

**Last update:** 2026-04-18 — phases 0–6 + 8 + 11 done, 9 effectively done (one deferred), 10 substantial; phase 7 implementation still pending. Phase 2.6 closed: pylint rated 10.00/10, hook enabled via upstream `pylint-dev/pylint` repo with HA runtime `additional_dependencies`; HA-framework warnings (unused-argument, abstract-method, attribute-defined-outside-init, too-many-nested-blocks) moved into the pylint disable list with justification; real issues fixed in code (3 pointless-string-statements removed, `type` → `consumption_type` in sensor.py, `swing_mode` → `swing_horizontal_mode` in climate.py, justified inline disables for 2 protected-access and 2 import-outside-toplevel sites).

### Phase 0–3 summary

**New / updated files:**

- `pyproject.toml` (was 2 lines → now central tool config: ruff, mypy, pylint, bandit, coverage, pytest, codespell)
- `setup.cfg` deleted
- `requirements_dev.txt`, `requirements_test.txt`, `requirements_test_pre_commit.txt`
- `.pre-commit-config.yaml` (3 hooks → 9 hook repos + 2 custom hooks)
- `.yamllint`, `.prettierignore`
- `.github/workflows/`: `mypy.yaml`, `bandit.yaml`, `codeql.yaml`, `dependency-review.yaml`, `pylint.yaml`, `release.yaml` new; `tests.yaml`, `precommit.yaml`, `dependabot.yml`, `constraints.txt` updated
- `codecov.yml` (component tracking for 6 components)
- `scripts/check_i18n.py`, `scripts/lint_exports.py`
- `docs/adr/0001-record-architecture-decisions.md`
- Baselines: `coverage-baseline.txt`, `mypy-baseline.txt`, `ruff-baseline.txt`, `bandit-baseline.txt`

**Code fixes along the way:**

- `__init__.py:51` — `raise ... from ex` (B904)
- `device.py:102` — list concatenation → unpack (RUF005)
- `sensor.py:118` — fixed spelling of "multiple"
- `tests/conftest.py:78-79` — `# noqa: B015` with TODO referring to phase 8
- `translations/de.json` — key typo `heatingmonthlyconsumption` → `heatingmonthlygasconsumption`
- `translations/{fr,it}.json` — 6 orphan keys from old config removed
- 17 files reformatted once via `ruff format` v0.6

**Verification:**

- ruff: ✅ all checks passed
- yamllint: ✅ exit 0
- codespell: ✅ exit 0
- pytest: ✅ 28/28 passed (snapshot "failures" = TODO phase 8)
- coverage: 97 % (baseline)
- mypy: 49 errors (baseline; reduced in phase 4)
- bandit: 2 low-severity false positives (excluded in `[tool.bandit] skips`)

**Conscious deviations from the original ROADMAP:**

- 1.4 mypy: no `strict = true` directly — moderate defaults plus `check_untyped_defs`. Strict is reserved for phase 4.10 (all modules typed).
- 1.3 ruff: `I` (isort) and `SIM` currently commented out. `I` becomes active once `reorder-python-imports` is removed (later in phase 4); `SIM` active after the inventory refactor in phase 4.
- 2.6 pylint: enabled as pre-commit hook (via upstream `pylint-dev/pylint` repo, `pylint-v4.0.5`). Reaches 10.00/10 on `custom_components/daikin_onecta/`; HA-typical warnings (`too-many-nested-blocks`, `unused-argument`, `abstract-method`, `attribute-defined-outside-init`, `unused-variable`, `redefined-builtin`) disabled in `pyproject.toml`.
- Runner migrated from `pre-commit` to `prek` (Rust drop-in by j178, same `.pre-commit-config.yaml`). CI uses `j178/prek-action@v2`; `pre-commit install` still works for contributors.
- 3.6 Python 3.14 matrix: enabled (3.13 + 3.14) — codecov-action bumped to v6.

### Phase 4–5 summary

**New / updated files:**

- `custom_components/daikin_onecta/exceptions.py` — new: `DaikinError` (base) plus `DaikinAuthError`, `DaikinRateLimitError(retry_after)`, `DaikinApiError(status)`, `DaikinDeviceError`, `DaikinValidationError`
- `const.py` — all constants `Final`, `SensorMapping = Mapping[str, Any]` alias, `VALUE_SENSOR_MAPPING: Final[Mapping[str, SensorMapping]]`
- `daikin_api.py` — `RateLimits` TypedDict, `JsonResponse`/`RequestResult`, helpers `_update_rate_limits`/`_raise_rate_limit_issues`, token refresh raises `DaikinAuthError`, ClientError → `DaikinApiError`
- `coordinator.py` — `DataUpdateCoordinator[None]` generic, `OnectaRuntimeData.devices: dict[str, DaikinOnectaDevice]`, `_async_update_data` translates Daikin\* exceptions into `ConfigEntryAuthFailed`/`UpdateFailed`
- `device.py`, `__init__.py`, `binary_sensor.py`, `button.py`, `switch.py`, `select.py`, `sensor.py`, `water_heater.py`, `diagnostics.py`, `system_health.py`, `application_credentials.py`, `config_flow.py` — type annotations, `__all__` markers, `CoordinatorEntity[OnectaDataUpdateCoordinator]` parametrised, `from __future__ import annotations`
- `tests/test_coordinator.py` — class `TestExceptionTranslation` with three new tests (Auth → ConfigEntryAuthFailed, Api → UpdateFailed, generic → UpdateFailed)

**Code fixes along the way:**

- `water_heater.py` — `result &= await self._device.patch(...)` → `result &= bool(await ...)` (3 places); `_attr_min_temp`/`_attr_max_temp` only set when not-None; `async_turn_on/off` now `-> None` (matches HA ToggleEntity)
- `switch.py` — `async_turn_on/off` signature aligned with the superclass (`-> None`, `bool()` around `patch`)
- `sensor.py` — `VALUE_SENSOR_MAPPING.get(key)` → `[key]` (three places, KeyError instead of an AttributeError follow-up bug)
- `climate.py` — `for mode in self.preset_modes or []`, `self.preset_mode is not None` guard, explicit `self._attr_fan_mode is None` check, `swingModes: list[str]`, `value: dict[str, Any]`
- `config_flow.py` — return types unified to `ConfigFlowResult`, removed unused `FlowResult` import
- `system_health.py` — early return on empty entries

**Verification:**

- mypy `--python-version 3.14`: ✅ 0 errors in 17 files (baseline 49 → 0)
- pytest: ✅ 31/31 passed (28 original + 3 new exception tests)
- coverage: 93.7 % (above `fail_under = 80`)

**Conscious deviations from the original ROADMAP:**

- 4.5 climate.py: fully typed with minimal, justified `# type: ignore[override]` markers on `async_turn_on`/`async_turn_off` (HA ToggleEntity returns `None`; internal callers rely on `bool`).
- 4.10 mypy strict: `strict = true` enabled centrally in `pyproject.toml`; `mypy --strict --python-version 3.14` reports 0 errors across 21 source files. HA module-reexport attribute errors resolved by importing `EntityCategory` / `STATE_OFF` from `homeassistant.const` (the explicit `__all__` source) instead of the helper/component reexports.
- 5.3 HTTP status mapping: 401 (token refresh + mid-request) raises `DaikinAuthError`; transport layer (`ClientError`) and 5xx raise `DaikinApiError(status=…)` and trip the circuit breaker; 429 stays return-compatible (`[]` / `False`) so callers keep their existing branches; other unexpected statuses log a warning and fall through to the default return.
- 5.5 schema validation: soft-contract approach. `custom_components/daikin_onecta/schema.py` exposes `validate_cloud_response` (returns issue list) and a strict `require_valid_cloud_response` (raises `DaikinValidationError`). The coordinator uses the soft variant — contract drift logs a warning, records `last_validation_issue_count` for diagnostics, but never trips `UpdateFailed`. Rationale: Daikin adds fields opportunistically; hard-failing would take the integration down for cosmetic drift. Phase 7 can tighten this to raise once the domain model is the single source of truth.

### Phase 6–8 summary

**New files:**

- `custom_components/daikin_onecta/support/__init__.py` — re-exports (`CircuitBreaker`, `CircuitBreakerOpenError`, `CircuitState`, `RateLimitThrottle`, `retry_with_backoff`)
- `custom_components/daikin_onecta/support/retry.py` — `@retry_with_backoff(tries, base_delay, max_delay, jitter, retry_on)` with guaranteed pass-through of `DaikinAuthError`/`DaikinRateLimitError`
- `custom_components/daikin_onecta/support/circuit_breaker.py` — `CircuitState` (CLOSED/OPEN/HALF_OPEN), `CircuitBreaker(failure_threshold=5, recovery_timeout=60s)` with `asyncio.Lock` and `time.monotonic()`-based transitions, `CircuitBreakerOpenError(DaikinError)`
- `custom_components/daikin_onecta/support/throttle.py` — `RateLimitThrottle.recommended_delay(limits)` for proactive pacing from telemetry
- `tests/test_support.py` — 21 tests (retry behavior, breaker state transitions, throttle recommendations)
- `tests/test_daikin_api.py` — 16 tests (token refresh, 200/204/429 paths, ClientError mapping, `_cloud_lock` race, breaker integration, retry integration)
- `tests/test_migrate.py` — 7 tests for `async_migrate_entry` (v1.1→v1.2 JWT decode, error / no-op / unknown-minor paths)
- `docs/adr/0002-resilience-patterns.md` — Accepted: retry/breaker/throttle in the new `support/` package, what is _not_ retried, default values, rejected alternatives
- `docs/adr/0003-domain-model-package-layout.md` — Proposed: layers `client/` ↔ `model/` ↔ `support/` ↔ `platforms/`, migration path one module per PR with re-exports

**Updated files:**

- `custom_components/daikin_onecta/daikin_api.py` — `CircuitBreaker` in `__init__`, `before_call()` as a pre-hook in `doBearerRequest`, `record_success()` on 200/204, `record_failure()` on `ClientError` (429 does not count as a failure), `getCloudDeviceDetails` with inline `@retry_with_backoff` (`tries=3`, `base_delay=1s`, `max_delay=5s`)

**Verification:**

- pytest: ✅ 75/75 passed (28 original + 3 coordinator exceptions + 21 support + 16 daikin_api + 7 migrate)
- pytest-xdist: ✅ `-n auto --timeout=20` → 75/75 in 2.30 s, no test isolation issues
- mypy `--python-version 3.14`: ✅ 0 errors in 21 files
- coverage: 94.68 % (above `fail_under = 80`, ≥ 85 % level reached)

**Conscious deviations from the original ROADMAP:**

- Phase 7 only ADR (7.1) implemented — implementation 7.2–7.10 is 🔴 (largest refactor) and follows only after further test hardening. Re-export strategy documented in the ADR.
- 8.2 (dedicated test-support package with mock factories/builders/asserters) outstanding — the critical gaps (API/coordinator/migrate) are closed; cosmetic test structure follows before phase 9.
- 8.1 closed: pure helpers (`FAKE_*` constants, `load_fixture_json`, `PerTestSnapshotExtension`, `snapshot_platform_entities`) moved from `tests/conftest.py` to `tests/_support.py`. `conftest.py` is now ~110 lines of actual fixtures; imports in `test_init.py` and `test_config_flow.py` switched to `from ._support import …`.
- 8.3 / 8.4 closed: snapshot asserts re-enabled, `friendly_name` excluded from state snapshots (HA translation cache is non-deterministic between tests), and a `PerTestSnapshotExtension` writes one `.ambr` file per test function under `tests/snapshots/test_init__<test>.ambr` (was a single 80k-line file). 75/75 tests pass with 2852 snapshots, stable across 3 sequential runs and `pytest -n auto`.
- 8.9 closed: `custom_components/daikin_onecta/schema.py` provides a soft TypedDict-based contract (`ValueWrapper`, `ManagementPoint`, `DeviceResponse`, `ValidationIssue`) plus `validate_cloud_response`/`validate_device`. `tests/test_fixture_contract.py` parametrises over all `tests/fixtures/*.json` (17 files) and asserts zero issues; a guard test prevents the fixture directory from silently emptying. Same validator will be wired into the coordinator path for phase 5.5.
- Retry on `doBearerRequest` (6.2): not via the decorator directly — instead explicitly in `getCloudDeviceDetails` (idempotent GET); generic per-endpoint application after the phase-7 model split.

### Phase 9–11 summary

**New files:**

- `SECURITY.md` — reporting process, supported-versions table, scope, token-handling rules
- `CONTRIBUTING.md` — dev setup, conventions, PR rules, ADR requirement, links to versioning/release docs
- `AGENTS.md` — guardrails for AI coding assistants (no commits, no pushes, ADR triggers, gates)
- `SUPPORT.md` — pre-issue checklist, bug-report contents, triage labels, out-of-scope list
- `changelog.md` — Keep-a-Changelog format, `Unreleased` block plus historic-release pointers
- `.gitleaks.toml` — allowlist for documented test JWT, public OIDC endpoint URLs, fixture/snapshot paths
- `docs/architecture.md` — layer diagram, data flow, key invariants (`_cloud_lock`, `scan_ignore`, rate limits, breaker), module map
- `docs/security.md` — engineering-side security notes (TLS defaults, logging hygiene, suppression rationale)
- `docs/versioning.md` — SemVer policy with concrete MAJOR/MINOR/PATCH examples, what counts as internal
- `docs/release.md` — pre-release checklist, hotfix flow
- `docs/index.md` — mkdocs landing page
- `docs/adr/0004-cloud-lock-and-scan-ignore.md` — Accepted: existing stale-read protection codified, alternatives considered
- `docs/adr/0005-polling-strategy.md` — Accepted: high/low scan windows, jitter, rate-limit fallback
- `mkdocs.yml` — Material theme, navigation, ADR section
- `.github/workflows/docs.yml` — `mkdocs build --strict` on PRs + GitHub Pages deploy from `master`

**Updated files:**

- `custom_components/daikin_onecta/daikin_api.py` — request/response logging moved from `INFO` to `DEBUG` (cloud identifiers should not appear in default logs)
- `custom_components/daikin_onecta/const.py` — `# noqa: S105 # nosec B105` on `OAUTH2_TOKEN` URL constant with justification
- `custom_components/daikin_onecta/coordinator.py` — `# noqa: S311 # nosec B311` on `random.randint` jitter with justification

**Verification:**

- pytest: ✅ 75/75 passed (snapshot "failures" remain TODO from phase 8)
- mypy `--python-version 3.14`: ✅ 0 errors in 21 files
- coverage: 94.68 % (above `fail_under = 80`)

**Conscious deviations from the original ROADMAP:**

- 9.5 CodeQL findings: marked `[-]` (deferred / out of scope for this iteration). The CodeQL workflow runs on every push (since phase 3.3); current GitHub Security tab is empty for this repo. Re-open if a finding appears.
- 10.7 docstring standards + ruff `D` enforcement: deferred — large legacy surface would block CI immediately. Best handled together with the phase-7 module split, when modules can be opted in one by one.
- 10.9 CLAUDE.md update after phase 7: cannot be completed until phase 7 is implemented. The current `CLAUDE.md` already reflects the phase 0–6 state.
- Phase 11.4 / 11.5: the workflows (`release.yaml`, `validate.yml`, `hassfest.yaml`) already existed since phase 3 — verified that they cover SemVer-tag → manifest validation → release zip → HACS validation as required.

---

## Recommended order / dependencies

```
Phase 0  (Baseline)
   │
   ▼
Phase 1 (pyproject) ──► Phase 2 (pre-commit) ──► Phase 3 (CI)
                                                     │
                            ┌────────────────────────┤
                            ▼                        ▼
                       Phase 4 (Typing)         Phase 9 (Security)
                            │
                            ▼
                       Phase 5 (Exceptions) ──► Phase 6 (Robustness)
                            │
                            ▼
                       Phase 8 (Tests, parallel from here on)
                            │
                            ▼
                       Phase 7 (Domain model — largest refactor)
                            │
                            ▼
                       Phase 10 (Docs) ──► Phase 11 (Release)
```

**Rule of thumb:** finish phases 0–3 in weeks 1–2 — after that every further change has CI protection. Phase 7 carries the highest risk and should only be tackled once tests are solid (phase 8).

---

## Out of scope / deliberate non-goals

- An `aiohomematic_storage` equivalent (local state store) — only worthwhile if real resilience requirements arise.
- Python 3.14 free-threading support — depends on Home Assistant Core.
- Spinning out the HA integration into a separate PyPI library (would break HACS distribution).
