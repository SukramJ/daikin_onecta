# Docstring standards

This document defines the docstring style used across `daikin_onecta`.
It exists so that newcomers do not have to reverse-engineer the
convention from existing code, and so that `ruff`'s `D` rules can
enforce the minimum consistently in CI.

The style deliberately stays close to **PEP 257** plus a small set of
project-specific rules, and intentionally avoids the heavier NumPy /
Google / reST conventions — the codebase favors type annotations over
prose parameter descriptions.

## When to write a docstring

- **Always** for public modules, public classes, and every public
  function or method.
- **Optional** for tiny private helpers whose purpose is obvious from
  name + signature. When in doubt, add one.
- **Never** as a substitute for a meaningful name — rename first, then
  decide whether a docstring is still necessary.

## Style rules

1. Triple double quotes, no blank line before the closing `"""`.
2. Imperative mood for the one-line summary: "Return the ...", not
   "Returns the ..." or "Gets the ...".
3. One-line summary fits on a single line ≤ 88 characters. A period at
   the end.
4. When more context is needed, follow the summary with one blank line
   and the body paragraphs (same rule as PEP 257).
5. **Do not** repeat the signature or the type annotations in prose.
   Type info lives in annotations; the docstring adds _intent_,
   _invariants_, _side effects_, or _failure modes_.
6. Document exceptions only when the caller has to branch on them.
   `Raises:` sections are not mandatory, but if a function raises a
   `Daikin*Error` that callers catch explicitly, list it.
7. Reference constants, config keys, and HA symbols with `double
backticks`.
8. Prefer short `Why:` / `How to apply:` notes over long narratives
   when encoding non-obvious design decisions — mirrors the memory
   convention and keeps docstrings scannable.
9. Keep async/await semantics visible — mention if a coroutine does
   I/O, acquires a lock, or is meant to be fire-and-forget.

## Examples

Minimal public function — summary only:

```python
def scan_ignore(self) -> int:
    """Number of seconds to skip GETs for after a PATCH."""
    return int(self.options.get("scan_ignore", 30))
```

Function with non-obvious invariants and failure modes:

```python
async def doBearerRequest(
    self, method: str, resource_url: str, options: str | None = None
) -> RequestResult:
    """HTTP request against the Daikin cloud (serialized via ``_cloud_lock``).

    Return values:
    - GET 200            → ``JsonResponse``
    - PATCH/POST/PUT 204 → ``True``
    - GET 429            → ``[]`` (rate limit; an issue is registered)
    - Write 429          → ``False``

    Raises:
    - ``DaikinAuthError``      — token refresh failed or HTTP 401.
    - ``DaikinRateLimitError`` — only via the explicit wrapper API.
    - ``DaikinApiError``       — transport error or HTTP 5xx.
    """
```

Class docstring — intent first, contracts after:

```python
class CircuitBreaker:
    """Simple circuit breaker.

    - After ``failure_threshold`` consecutive failures, the state
      transitions to ``OPEN``; calls raise ``CircuitBreakerOpenError``
      without contacting the protected endpoint.
    - After ``recovery_timeout`` seconds the breaker moves to
      ``HALF_OPEN``: the next call is allowed through. If it succeeds
      the breaker closes; otherwise it trips back to ``OPEN``.
    """
```

## What **not** to do

- Do **not** describe parameters that have self-explanatory names
  (`hass`, `config_entry`, `device`). Annotations already cover the
  types.
- Do **not** copy the function body into prose. The docstring is a
  summary, not a narration.
- Do **not** write `TODO` docstrings. Either the function is ready and
  documented, or the work isn't finished and the TODO belongs in an
  issue.
- Avoid decorative separators (`# -----`) and emojis.

## Tooling

Ruff's `D` rule family enforces a minimum. The selection below is the
subset the project cares about; everything else is intentionally left
off to avoid noise on historical code:

| Code | Meaning                                             |
| ---- | --------------------------------------------------- |
| D200 | One-line docstring should fit on one line           |
| D201 | No blank lines allowed before docstring             |
| D202 | No blank lines allowed after docstring              |
| D205 | Blank line required between summary and description |
| D209 | Closing quotes on separate line for multiline       |
| D210 | No whitespace surrounding docstring text            |
| D300 | Use triple double quotes                            |
| D400 | First line should end with a period                 |
| D401 | First line should be in imperative mood             |
| D419 | Docstring is empty                                  |

The full ruff `D` ruleset is **not** enabled, because the existing
codebase legitimately omits docstrings on obvious helpers and on
internal platform glue. If you hit a warning that seems spurious, err
on the side of adding a short summary rather than suppressing the
rule.
