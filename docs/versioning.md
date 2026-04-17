# Versioning policy

`daikin_onecta` follows [Semantic Versioning 2.0.0][semver].

[semver]: https://semver.org/spec/v2.0.0.html

## What the parts mean here

- **MAJOR** — a breaking change for end users. Examples:
  - dropping support for a Home Assistant Core minor that was
    previously declared compatible in `manifest.json`;
  - removing or renaming an entity in a way that breaks existing
    automations and dashboards;
  - changing the config-flow schema in a way that requires the user to
    re-add the integration (a `version` bump in
    `async_migrate_entry` that cannot migrate forward).
- **MINOR** — backwards-compatible feature work. Examples:
  - new entities, new sensors, new device types;
  - new options-flow settings with a sensible default;
  - new translation languages;
  - migrations between `minor_version`s of a config entry that the
    user does not have to act on.
- **PATCH** — backwards-compatible fixes only. Examples:
  - bug fix in an existing entity's value mapping;
  - correction of a translation string;
  - dependency or CI change with no runtime impact.

## What is *not* a public surface

The following are **internal** and may change without a major bump:

- Anything under `support/` — retry, circuit breaker, throttle.
- Internal helpers in `daikin_api.py`, `device.py`, `coordinator.py`
  that are not consumed by tests or by other Home Assistant
  integrations.
- Test fixtures, snapshot files, baselines.

If you depend on something internal, file an issue and we'll discuss
making it stable.

## Home Assistant Core minimum

The minimum supported HA Core version lives in
`custom_components/daikin_onecta/manifest.json::homeassistant`. Bumping
it is a **MINOR** change if the new minimum is a *previous* HA Core
release, and a **MAJOR** change if it forces users still on the old
release to stay on an old `daikin_onecta` version.

## Relationship to HACS

HACS reads the `version` from `manifest.json`. The release workflow
(`.github/workflows/release.yaml`) refuses to publish a tag whose
version does not match. Don't tag manually without bumping
`manifest.json` first.
