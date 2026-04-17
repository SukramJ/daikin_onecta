"""Proaktives Rate-Limit-Pacing.

Ergänzt die reaktive Logik in ``DaikinApi`` (die nur bei
``remaining_day == 0`` reagiert), indem die nächste Wartezeit aus den
verbleibenden Minuten/Tag-Kontingenten abgeleitet wird.
"""

from __future__ import annotations

import logging
from typing import Final

from ..daikin_api import RateLimits

__all__: Final = ("RateLimitThrottle",)

_LOGGER = logging.getLogger(__name__)


class RateLimitThrottle:
    """Berechnet eine empfohlene Wartezeit (Sekunden) bis zum nächsten Call."""

    def __init__(self, *, safety_margin: int = 2, min_remaining_pct: float = 0.1) -> None:
        if safety_margin < 0:
            raise ValueError("safety_margin must be >= 0")
        if not 0.0 < min_remaining_pct < 1.0:
            raise ValueError("min_remaining_pct must be in (0, 1)")
        self._safety_margin = safety_margin
        self._min_remaining_pct = min_remaining_pct

    def recommended_delay(self, limits: RateLimits) -> float:
        """Empfohlene Wartezeit in Sekunden bis zum nächsten Call.

        Wenn das Tageskontingent erschöpft ist, wird ``retry_after`` plus Safety-Margin
        zurückgegeben. Andernfalls wird die nächste Aufruf-Frequenz so gewählt, dass
        ``remaining_minutes`` nicht unter ``min_remaining_pct * minute`` fällt.
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
