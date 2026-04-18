# Release process

Releases are cut by pushing a `vMAJOR.MINOR.PATCH` tag. The
[`release.yaml`](https://github.com/jwillemsen/daikin_onecta/blob/master/.github/workflows/release.yaml)
workflow validates that the tag matches `manifest.json::version`,
packages `custom_components/daikin_onecta/` into a zip, and publishes a
GitHub Release with auto-generated notes.

## Pre-release checklist

Run through this list **before** pushing the tag.

### 1. Decide the version number

- Use [`docs/versioning.md`](versioning.md) to pick MAJOR / MINOR /
  PATCH.
- If you're not sure, prefer the smaller bump and revisit on user
  feedback.

### 2. Update `manifest.json`

```bash
# Bump the version in custom_components/daikin_onecta/manifest.json::version
```

This is the source of truth. HACS reads it, the release workflow
checks it.

### 3. Update `changelog.md`

- Move the contents of `## [Unreleased]` into a new section
  `## [X.Y.Z] — YYYY-MM-DD`.
- Leave an empty `## [Unreleased]` block at the top for the next cycle.
- Group entries under **Added**, **Changed**, **Fixed**, **Removed**,
  **Deprecated**, **Security** as needed.

### 4. Migration notes (only if config-entry version changes)

- If you bumped `version` in `async_migrate_entry`, document the
  migration in the changelog entry under **Changed** with a one-line
  explanation of what users should expect.
- Confirm `tests/test_migrate.py` covers the new path.

### 5. Verify CI is green on `master`

- All workflows must be green on the commit you intend to tag.
- In particular: `tests`, `mypy`, `bandit`, `pylint`, `hassfest`,
  `HACS Validate`, `CodeQL`.

### 6. Tag and push

```bash
git tag -a vX.Y.Z -m "vX.Y.Z"
git push origin vX.Y.Z
```

The release workflow takes it from there.

### 7. After the release

- Verify the GitHub Release page shows the zip artifact.
- Verify HACS picks up the new version (may take a few minutes).
- Watch the issue tracker for early reports — if a regression appears
  within the first 24 hours, prefer a fast PATCH release over a
  revert.

## Hotfix releases

For urgent fixes against the latest release:

1. Branch from the release tag: `git checkout -b hotfix/X.Y.Z+1 vX.Y.Z`.
2. Apply the minimal fix and a test that pins it.
3. Bump `manifest.json` to the next PATCH.
4. Open a PR into `master`. After merge, tag from `master` as usual.

Do **not** force-push to `master` to inject a hotfix.
