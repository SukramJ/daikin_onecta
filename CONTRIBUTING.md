# Contributing to daikin_onecta

Thanks for taking the time to contribute. This document explains how to
set up a development environment, the conventions the project follows,
and what to expect during review.

## Dev setup

This is a Home Assistant custom integration written for Python 3.13+.

```bash
git clone https://github.com/jwillemsen/daikin_onecta.git
cd daikin_onecta

python3.13 -m venv venv
source venv/bin/activate

pip install -r requirements_test.txt
pip install -r requirements_test_pre_commit.txt
pre-commit install
```

Run the test suite the same way CI does:

```bash
pytest -n auto --timeout=9 tests
```

Run a single test:

```bash
pytest tests/test_init.py::test_setup_with_fixture
```

Update snapshot baselines after intentional output changes:

```bash
pytest --snapshot-update
```

Run all linters and formatters:

```bash
pre-commit run --all-files
```

## Coding conventions

- **Line length:** 88 (configured in `pyproject.toml`).
- **Imports:** one per line (`force_single_line = true`).
- **Type annotations:** required on every new public function and class.
  `mypy --python-version 3.14` must stay at 0 errors.
- **`__all__`:** every public module declares its exports; the
  `lint-all-exports` pre-commit hook enforces this.
- **Translations:** every translated string key must exist in the
  English fallback (`translations/en.json`); the `check-i18n`
  pre-commit hook enforces this.
- **Comments:** explain the *why*, never the *what*. Multi-paragraph
  docstrings are not used; keep doc lines short.

## Tests

- Add unit tests for new behavior under `tests/`.
- For new device types, drop the captured cloud response into
  `tests/fixtures/` and use the existing snapshot helper.
- Snapshot tests live in `tests/snapshots/*.ambr` (syrupy). Run
  `pytest --snapshot-update` after intentional output changes.
- Coverage gate is `fail_under = 80` (currently 94.68 %). New code
  should not regress that number.

## Pull requests

- Branch from `master`.
- Keep PRs focused — one feature or one fix per PR. If you find
  unrelated cleanup along the way, open a separate PR for it.
- Reference the issue you are addressing in the PR description.
- The PR title becomes the changelog entry, so make it concise and
  descriptive.
- CI must be green (tests, mypy, ruff, bandit, pylint, hassfest, HACS
  validate, CodeQL).

## Architectural changes

For any structural change — new package, new dependency, new layer,
breaking change to the internal API — open an
**Architecture Decision Record** under `docs/adr/` using the format of
the existing entries. Code review will not approve a structural change
without an accompanying ADR.

## Versioning and releases

The project follows Semantic Versioning. The exact policy lives in
[`docs/versioning.md`](docs/versioning.md). The release process and
pre-release checklist live in [`docs/release.md`](docs/release.md).

## Reporting security issues

Do **not** open a public issue. See [`SECURITY.md`](SECURITY.md).
