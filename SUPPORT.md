# Getting support

## Before you open an issue

1. **Check whether the Daikin cloud is up.**
   <https://daikincloudsolutions.statuspage.io/> — many "the integration
   is broken" reports are actually cloud outages.

2. **Update.** Make sure you're on the latest release from HACS or the
   latest tag on this repository. Old releases do not get fixes.

3. **Search existing issues.**
   <https://github.com/jwillemsen/daikin_onecta/issues?q=is%3Aissue> —
   there is a good chance someone already reported it.

4. **Enable debug logging** and reproduce the problem:

   ```yaml
   logger:
     logs:
       custom_components.daikin_onecta: debug
       homeassistant.helpers.config_entry_oauth2_flow: debug
   ```

   Restart Home Assistant, reproduce the issue, then collect the log
   excerpt.

## Reporting a bug

Open an issue using the bug-report template:
<https://github.com/jwillemsen/daikin_onecta/issues/new?template=issue_report.md>.

Please include:

- **Integration version** (`Settings → Devices & Services → Daikin
Onecta → ⋮ → System Information`, or `manifest.json::version`).
- **Home Assistant Core version**.
- **Daikin device model**.
- **Diagnostics download** (`Settings → Devices & Services → Daikin
Onecta → Download diagnostics`). The diagnostics output already
  redacts tokens.
- **Debug log excerpt** for the time window where the problem occurs.
  Please scrub any access or refresh tokens — see the warning in
  [`SECURITY.md`](SECURITY.md).

## Reporting a security issue

Do **not** open a public issue. Follow the process in
[`SECURITY.md`](SECURITY.md).

## Feature requests

Open an issue and describe the use case. Pull requests are welcome —
see [`CONTRIBUTING.md`](CONTRIBUTING.md).

## Issue triage

Maintainers triage issues with these labels:

- **`needs-info`** — the report is missing diagnostics, version, or a
  debug log. Stale `needs-info` issues are closed after 30 days.
- **`upstream`** — the root cause is in Daikin's cloud or the upstream
  Home Assistant Core. We track it but cannot fix it here.
- **`good-first-issue`** — small, well-scoped tasks for new
  contributors.

## Not supported

- Account or device migration to a different region.
- Integration with the legacy Daikin BRP/OpenAPI cloud (see
  `daikin_residential` for that).
- Custom firmware or modified Onecta apps.
