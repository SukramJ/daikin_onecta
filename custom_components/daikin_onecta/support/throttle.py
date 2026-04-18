"""Proactive rate-limit pacing.

Complements the reactive logic in ``DaikinApi`` (which only reacts when
``remaining_day == 0``) by deriving the next wait time from the remaining
per-minute and daily quotas.
"""

from __future__ import annotations

import logging
from typing import Final

from ..daikin_api import RateLimits

__all__: Final = ("RateLimitThrottle",)

_LOGGER = logging.getLogger(__name__)


class RateLimitThrottle:
    """Computes a recommended wait time (in seconds) until the next call."""

    def __init__(self, *, safety_margin: int = 2, min_remaining_pct: float = 0.1) -> None:
        if safety_margin < 0:
            raise ValueError("safety_margin must be >= 0")
        if not 0.0 < min_remaining_pct < 1.0:
            raise ValueError("min_remaining_pct must be in (0, 1)")
        self._safety_margin = safety_margin
        self._min_remaining_pct = min_remaining_pct

    def recommended_delay(self, limits: RateLimits) -> float:
        """Recommended wait time in seconds until the next call.

        If the daily quota is exhausted, ``retry_after`` plus the safety
        margin is returned. Otherwise the next call frequency is chosen such
        that ``remaining_minutes`` does not drop below
        ``min_remaining_pct * minute``.
        """
        if limits.get("remaining_day", 1) <= 0:
            return float(limits.get("retry_after", 0)) + self._safety_margin

        per_minute = int(limits.get("minute", 0))
        remaining = int(limits.get("remaining_minutes", per_minute))
        if per_minute <= 0:
            return 0.0

        if remaining <= int(per_minute * self._min_remaining_pct):
            reset = int(limits.get("ratelimit_reset", 60))
            return float(max(reset, 1)) + self._safety_margin
        return 0.0
