"""Retry decorator with exponential backoff and jitter."""

from __future__ import annotations

import asyncio
import logging
import random
from collections.abc import Awaitable
from collections.abc import Callable
from functools import wraps
from typing import Any
from typing import Final
from typing import TypeVar

from ..exceptions import DaikinApiError
from ..exceptions import DaikinAuthError
from ..exceptions import DaikinRateLimitError

__all__: Final = ("retry_with_backoff",)

_LOGGER = logging.getLogger(__name__)

T = TypeVar("T")


def retry_with_backoff(
    *,
    tries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    jitter: float = 0.25,
    retry_on: tuple[type[BaseException], ...] = (DaikinApiError,),
) -> Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]:
    """Async decorator: run the function up to ``tries`` times with exponential backoff.

    - ``base_delay`` is multiplied by ``2 ** attempt`` and clamped to ``max_delay``.
    - ``jitter`` (relative, 0-1) spreads parallel callers apart.
    - ``DaikinAuthError`` and ``DaikinRateLimitError`` are never retried
      automatically: auth errors need a reauth flow, rate limit has its own
      ``retry_after``.
    """
    if tries < 1:
        raise ValueError("tries must be >= 1")
    if base_delay < 0 or max_delay < 0:
        raise ValueError("delays must be non-negative")

    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            last_exc: BaseException | None = None
            for attempt in range(tries):
                try:
                    return await func(*args, **kwargs)
                except DaikinAuthError, DaikinRateLimitError:
                    raise
                except retry_on as exc:
                    last_exc = exc
                    if attempt == tries - 1:
                        break
                    delay = min(base_delay * (2**attempt), max_delay)
                    delay *= 1 + random.uniform(-jitter, jitter)
                    delay = max(delay, 0.0)
                    _LOGGER.warning(
                        "Retry %d/%d for %s after %.2fs (cause: %s)",
                        attempt + 1,
                        tries,
                        func.__qualname__,
                        delay,
                        exc,
                    )
                    await asyncio.sleep(delay)
            # Invariant: the loop body always assigns ``last_exc`` before reaching this line.
            assert last_exc is not None  # nosec B101
            raise last_exc

        return wrapper

    return decorator
