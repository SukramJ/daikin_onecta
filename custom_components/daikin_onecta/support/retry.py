"""Retry-Decorator mit exponentiellem Backoff und Jitter."""

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
    """Async-Decorator: führt die Funktion bis ``tries``-mal aus, mit exponentiellem Backoff.

    - ``base_delay`` wird mit ``2 ** attempt`` multipliziert, geclampt auf ``max_delay``.
    - ``jitter`` (relativ, 0–1) verteilt parallele Aufrufer.
    - ``DaikinAuthError`` und ``DaikinRateLimitError`` werden nie automatisch wiederholt:
      Auth-Fehler brauchen einen Reauth-Flow, RateLimit kennt sein eigenes ``retry_after``.
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
                except (DaikinAuthError, DaikinRateLimitError):
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
            assert last_exc is not None
            raise last_exc

        return wrapper

    return decorator
