# Security notes

This document records security-relevant defaults in `daikin_onecta` so
they don't drift unnoticed. The user-facing reporting policy lives in
[`SECURITY.md`](https://github.com/jwillemsen/daikin_onecta/blob/master/SECURITY.md).

## Transport / TLS

All cloud requests are sent through the shared
`homeassistant.helpers.aiohttp_client.async_get_clientsession()`
session, which uses `aiohttp.ClientSession` with its upstream defaults:

- TLS 1.2 minimum (Python `ssl.create_default_context()` defaults).
- Server certificate verification **on** (default `ssl.CERT_REQUIRED`).
- Hostname verification **on** (default `check_hostname=True`).
- Trusted CA bundle from `certifi` via `ssl.create_default_context()`.

`grep -rn 'ssl\|verify=' custom_components/daikin_onecta/` returns
nothing — there is **no** `ssl=False`, `verify_ssl=False`, or custom
`SSLContext` anywhere in the integration.

If you ever need to disable verification (e.g. for a local mock cloud
during testing), do it in test code only and add a comment referencing
this file.

## Logging hygiene

The following log lines have been intentionally placed at `DEBUG`
because their content can include cloud-side identifiers (gateway IDs,
MAC addresses) that should not appear in default `INFO` logs:

- `daikin_api.py` — `Request URL`, `Request <method> Options`,
  `Response status … Text … Limit`.

Tokens, refresh tokens, and `Authorization` headers are **never**
logged. The only place a token is even decoded is the JWT `sub` claim
for unique-id derivation in:

- `__init__.py::async_migrate_entry` (v1.1 → v1.2 migration)
- `config_flow.py::async_oauth_create_entry`

Both decode paths log only the exception class on failure, never the
token contents.

Diagnostics output redacts the entire `token` block — see
`diagnostics.py`.

## Static analysis suppressions

Two `# noqa: Sxxx # nosec Bxxx` markers exist with justifications:

- `const.py:OAUTH2_TOKEN` (B105) — the value is a public OIDC endpoint
  URL, not a secret.
- `coordinator.py` random jitter (B311) — non-cryptographic, purely for
  load spreading across users.

See [`bandit-baseline.txt`](https://github.com/jwillemsen/daikin_onecta/blob/master/bandit-baseline.txt)
for the complete review.
