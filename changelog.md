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

### Added

- **Resilience layer (`support/`)** — `@retry_with_backoff` decorator,
  `CircuitBreaker` (CLOSED/OPEN/HALF_OPEN), `RateLimitThrottle` for
  proactive pacing. Wired into `daikin_api.doBearerRequest` and
  `getCloudDeviceDetails`. See ADR
  [`docs/adr/0002-resilience-patterns.md`](docs/adr/0002-resilience-patterns.md).
- **Custom exception hierarchy** (`exceptions.py`): `DaikinError` with
  subclasses `DaikinAuthError`, `DaikinRateLimitError`, `DaikinApiError`,
  `DaikinDeviceError`, `DaikinValidationError`. The coordinator
  translates them into `ConfigEntryAuthFailed` / `UpdateFailed`.
- **Tooling baseline**: central `pyproject.toml` (ruff, mypy, pylint,
  bandit, coverage, pytest, codespell), pre-commit suite, CI jobs for
  mypy / bandit / pylint / CodeQL / dependency review, `codecov.yml`
  with component tracking. See ROADMAP phases 0–3.
- **Test suite**: `test_support.py`, `test_daikin_api.py`,
  `test_migrate.py` — coverage from 28 → 75 tests, line coverage at
  94.68 %, pytest-xdist verified.
- **Documentation**: `SECURITY.md`, `CONTRIBUTING.md`, `AGENTS.md`,
  `SUPPORT.md`, `docs/architecture.md`, `docs/security.md`,
  `docs/versioning.md`, ADRs 0001–0003, `mkdocs.yml`.

### Changed

- **Logging hygiene**: request/response bodies in `daikin_api.py` moved
  from `INFO` to `DEBUG` to keep cloud identifiers out of default logs.
- **Type safety**: 17 modules typed (`mypy --python-version 3.14` 0
  errors, baseline was 49). `__all__` declared on every public module.

### Security

- Bandit baseline reviewed; the two low-severity false positives
  (`OAUTH2_TOKEN` URL constant, `random.randint` jitter) are now
  annotated with `# nosec` and a justification.
- `.gitleaks.toml` added with allowlist for the documented test JWT and
  fixture paths.

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
