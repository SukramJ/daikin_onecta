#!/usr/bin/env python3
"""Pre-commit hook: ensure ``__all__`` (when present) is a sorted tuple/list of strings.

We do not require every module to expose ``__all__`` yet — Phase 4 will add
explicit exports module by module. But where one already exists, it must be
sorted to keep diffs stable.

Exit code 0 if all checked modules pass, non-zero otherwise.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path


def _check(path: Path) -> list[str]:
    errors: list[str] = []
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError as ex:
        return [f"{path}: syntax error: {ex}"]

    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        targets = [t for t in node.targets if isinstance(t, ast.Name) and t.id == "__all__"]
        if not targets:
            continue
        if not isinstance(node.value, ast.Tuple | ast.List):
            errors.append(f"{path}:{node.lineno}: __all__ must be a tuple or list literal")
            continue
        names: list[str] = []
        for elt in node.value.elts:
            if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                names.append(elt.value)
            else:
                errors.append(f"{path}:{node.lineno}: __all__ entries must be string literals")
                break
        if names and names != sorted(names):
            errors.append(f"{path}:{node.lineno}: __all__ is not sorted (expected {sorted(names)!r})")

    return errors


def main(argv: list[str]) -> int:
    failures: list[str] = []
    for filename in argv:
        path = Path(filename)
        if not path.is_file() or path.suffix != ".py":
            continue
        failures.extend(_check(path))

    for line in failures:
        print(line, file=sys.stderr)

    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
