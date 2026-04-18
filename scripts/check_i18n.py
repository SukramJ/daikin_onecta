#!/usr/bin/env python3
"""Pre-commit hook: cross-check translation files against ``en.json``.

Default mode (no flag): only ``extra`` keys — i.e. keys that exist in a
non-English file but were removed from ``en.json`` — are treated as
failures. These usually indicate stale translations after a refactor.

Strict mode (``--strict``): also fails on ``missing`` keys (untranslated
strings). Use this in CI once the backlog has been worked through.

Exit code 0 if all gates pass, non-zero otherwise.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Iterator
from pathlib import Path

TRANSLATIONS_DIR = Path("custom_components/daikin_onecta/translations")
REFERENCE = "en.json"


def _walk(prefix: str, node: object) -> Iterator[str]:
    if isinstance(node, dict):
        for key, value in node.items():
            yield from _walk(f"{prefix}.{key}" if prefix else key, value)
    else:
        yield prefix


def _key_set(path: Path) -> set[str]:
    with path.open(encoding="utf-8") as fh:
        data = json.load(fh)
    return set(_walk("", data))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--strict", action="store_true", help="also fail on missing keys")
    args = parser.parse_args()

    ref_path = TRANSLATIONS_DIR / REFERENCE
    if not ref_path.is_file():
        print(f"ERROR: reference translation '{ref_path}' missing", file=sys.stderr)
        return 1

    reference = _key_set(ref_path)
    hard_failures = 0
    soft_failures = 0

    for lang_path in sorted(TRANSLATIONS_DIR.glob("*.json")):
        if lang_path.name == REFERENCE:
            continue
        keys = _key_set(lang_path)
        missing = reference - keys
        extra = keys - reference
        if missing or extra:
            print(f"\n{lang_path}:")
            for key in sorted(extra):
                print(f"  extra (FAIL):    {key}")
                hard_failures += 1
            for key in sorted(missing):
                tag = "FAIL" if args.strict else "warn"
                print(f"  missing ({tag}): {key}")
                if args.strict:
                    hard_failures += 1
                else:
                    soft_failures += 1

    if hard_failures:
        print(f"\n{hard_failures} hard failure(s) — translations diverge from {REFERENCE}", file=sys.stderr)
        return 1
    if soft_failures:
        print(f"\n{soft_failures} missing translation(s) — non-blocking, run with --strict to enforce", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
