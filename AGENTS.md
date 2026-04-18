# Notes for AI coding agents

This file is intended for AI assistants (Claude Code, Copilot, Cursor,
etc.) working in this repository. Human contributors should start with
[`CONTRIBUTING.md`](CONTRIBUTING.md) and [`CLAUDE.md`](CLAUDE.md).

## Ground rules

- **Read [`CLAUDE.md`](CLAUDE.md) first.** It contains the architecture
  overview and the canonical command list.
- **Never commit unless explicitly asked.** Treat commit creation as a
  destructive action — confirm first.
- **Never push.** Pushing to `master` requires a human in the loop.
- **Never bypass hooks.** No `--no-verify`. If a hook fails, fix the
  underlying issue.
- **Never log tokens.** See [`docs/security.md`](docs/security.md). The
  Daikin terms of service prohibit sharing access or refresh tokens.

## What changes need an ADR

Any of the following:

- New top-level package under `custom_components/daikin_onecta/`.
- New runtime dependency in `manifest.json`.
- New layer or boundary (e.g. extracting `client/` from `daikin_api.py`).
- Breaking change to an internal API consumed by tests or platforms.

The ADR template is the same Michael-Nygard format used by
`docs/adr/0001-record-architecture-decisions.md`. Number sequentially.

## Where the rails live

- **CI:** `.github/workflows/` — every workflow must stay green.
- **Coverage gate:** `fail_under = 80` in `pyproject.toml::[tool.coverage.report]`.
  Currently at 94.68 %.
- **Type gate:** `mypy --python-version 3.14` 0 errors in 21 files.
- **Lint gate:** `prek run --all-files` clean (`pre-commit` also works — same config).
- **Snapshot gate:** `pytest tests` — failures usually mean the
  snapshot needs `--snapshot-update`, but verify the diff first.

## Helpful starting points

- Big picture: [`docs/architecture.md`](docs/architecture.md).
- ROADMAP and progress: [`ROADMAP.md`](ROADMAP.md). The progress
  dashboard at the bottom and the per-phase summaries are the canonical
  status; the checkboxes in the per-phase tables are the day-to-day
  tracking.
- Existing decisions: [`docs/adr/`](docs/adr/).
- Test fixtures: `tests/fixtures/*.json` are real (scrubbed) Daikin
  cloud responses — reuse them rather than fabricating new mock data.

## When you are stuck

- Resilience question (retry, circuit breaker, throttle): check
  `docs/adr/0002-resilience-patterns.md`.
- Domain-model question (where should this code live?): check
  `docs/adr/0003-domain-model-package-layout.md` — the layout there is
  Proposed, not Accepted, so call it out if your change preempts that
  decision.
- Anything else: ask the human reviewer.
