"""Circuit-Breaker (CLOSED → OPEN → HALF_OPEN → CLOSED)."""

from __future__ import annotations

import asyncio
import enum
import logging
import time
from typing import Final

from ..exceptions import DaikinError

__all__: Final = ("CircuitBreaker", "CircuitBreakerOpenError", "CircuitState")

_LOGGER = logging.getLogger(__name__)


class CircuitState(enum.Enum):
    """Zustände des Circuit-Breakers."""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreakerOpenError(DaikinError):
    """Wird geworfen, wenn der Circuit-Breaker offen ist und Calls blockiert."""


class CircuitBreaker:
    """Einfacher Circuit-Breaker.

    - Nach ``failure_threshold`` aufeinanderfolgenden Fehlern wechselt der Zustand
      auf ``OPEN``; Calls werfen ``CircuitBreakerOpenError`` ohne den geschützten
      Endpunkt anzusprechen.
    - Nach ``recovery_timeout`` Sekunden geht der Breaker in ``HALF_OPEN``: der
      nächste Call darf passieren. Erfolgt dieser ohne Fehler, schließt der
      Breaker; ansonsten geht er sofort wieder auf ``OPEN``.
    """

    def __init__(self, *, failure_threshold: int = 5, recovery_timeout: float = 60.0) -> None:
        if failure_threshold < 1:
            raise ValueError("failure_threshold must be >= 1")
        if recovery_timeout <= 0:
            raise ValueError("recovery_timeout must be > 0")
        self._failure_threshold = failure_threshold
        self._recovery_timeout = recovery_timeout
        self._state: CircuitState = CircuitState.CLOSED
        self._failures: int = 0
        self._opened_at: float = 0.0
        self._lock = asyncio.Lock()

    @property
    def state(self) -> CircuitState:
        return self._state

    async def before_call(self) -> None:
        """Prüft den State vor einem Call. Hebt ``CircuitBreakerOpenError`` wenn blockiert."""
        async with self._lock:
            if self._state is CircuitState.OPEN:
                if time.monotonic() - self._opened_at >= self._recovery_timeout:
                    _LOGGER.info("CircuitBreaker -> HALF_OPEN (probing)")
                    self._state = CircuitState.HALF_OPEN
                else:
                    raise CircuitBreakerOpenError("circuit breaker is open")

    async def record_success(self) -> None:
        async with self._lock:
            if self._state is not CircuitState.CLOSED:
                _LOGGER.info("CircuitBreaker -> CLOSED (recovered)")
            self._state = CircuitState.CLOSED
            self._failures = 0

    async def record_failure(self) -> None:
        async with self._lock:
            if self._state is CircuitState.HALF_OPEN:
                _LOGGER.warning("CircuitBreaker -> OPEN (probe failed)")
                self._state = CircuitState.OPEN
                self._opened_at = time.monotonic()
                return
            self._failures += 1
            if self._failures >= self._failure_threshold:
                _LOGGER.warning(
                    "CircuitBreaker -> OPEN (threshold %d reached)",
                    self._failure_threshold,
                )
                self._state = CircuitState.OPEN
                self._opened_at = time.monotonic()
