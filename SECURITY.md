# Security Policy

## Supported versions

Only the most recent minor release receives security fixes. Older releases
are end-of-life as soon as the next minor is published.

| Version | Supported |
|---------|-----------|
| 4.4.x   | ✅ |
| 4.3.x   | ❌ |
| < 4.3   | ❌ |

The current release version is tracked in
[`custom_components/daikin_onecta/manifest.json`](custom_components/daikin_onecta/manifest.json).

## Reporting a vulnerability

Please **do not** open a public GitHub issue for security problems.

Use GitHub's private vulnerability reporting:
<https://github.com/jwillemsen/daikin_onecta/security/advisories/new>

If GitHub reporting is not available to you, email the maintainer at the
address listed in the GitHub profile of `@jwillemsen`. Include:

- A description of the issue and the impact you observed.
- Steps to reproduce (a redacted Daikin Onecta cloud response is usually
  enough — do **not** include access or refresh tokens).
- The integration version (`manifest.json::version`) and Home Assistant
  Core version.

You can expect an acknowledgement within **5 working days** and a
remediation plan or rejection within **30 days**.

## Scope

In scope:

- Code under `custom_components/daikin_onecta/`.
- Workflows under `.github/workflows/` that this repository owns.
- Secrets handling for the OAuth2 client credentials and access/refresh
  tokens (see also [§ Token handling](#token-handling)).

Out of scope:

- Vulnerabilities in the Daikin Onecta cloud API itself — please report
  these directly to Daikin via
  <https://developer.cloud.daikineurope.com/>.
- Vulnerabilities in upstream dependencies (Home Assistant, `aiohttp`,
  …) — please report these to the respective project; we will pick up
  the fix once a patched release is available.
- Anything that requires the attacker to already control the Home
  Assistant host.

## Token handling

The Daikin developer terms of service prohibit sharing access or refresh
tokens. The integration follows that rule:

- Tokens are stored only in the Home Assistant config entry, encrypted
  at rest by Home Assistant Core's storage layer.
- Tokens are **not** logged. Only the JWT `sub` claim is decoded for
  unique-id derivation; decode failures log the exception type, never
  the token contents (see `__init__.py:async_migrate_entry` and
  `config_flow.py:async_oauth_create_entry`).
- Diagnostics output redacts the entire `token` block — see
  `diagnostics.py`.

If you find a path where a token (or fragment of one) leaks into logs,
diagnostics, or error reports, treat it as a security issue and use the
process above.

## Transport security

All cloud calls go through `aiohttp.ClientSession` with the upstream
defaults: TLS 1.2+, certificate verification enabled, hostname
verification on. There are no `ssl=False` or `verify_ssl=False`
shortcuts in this codebase. Confirmation lives in
[`docs/security.md`](docs/security.md).

## Static analysis

Every push runs:

- `bandit` on `custom_components/daikin_onecta/` (workflow:
  `.github/workflows/bandit.yaml`, SARIF uploaded to the GitHub
  Security tab).
- CodeQL for Python (workflow: `.github/workflows/codeql.yaml`).
- `dependency-review-action` on pull requests (workflow:
  `.github/workflows/dependency-review.yaml`).

Known suppressed findings are documented in
[`bandit-baseline.txt`](bandit-baseline.txt).
