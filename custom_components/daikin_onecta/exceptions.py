"""Eigene Exception-Hierarchie für die Daikin-Onecta-Integration.

Hintergrund: Vorher signalisierten viele Code-Pfade Fehler über Sonderwerte
(``False``/``[]``) oder allgemeine ``Exception``. Das macht es im Coordinator
schwierig, korrekt auf ``UpdateFailed`` / ``ConfigEntryAuthFailed`` /
``ConfigEntryNotReady`` zu mappen.

Mit dieser Hierarchie können wir gezielt fangen und übersetzen:

- ``DaikinError``              — Wurzel; alles, was die Integration wirft.
  - ``DaikinAuthError``        — Token/OAuth-Probleme → reauth.
  - ``DaikinRateLimitError``   — HTTP 429 oder erschöpftes Tagesbudget.
  - ``DaikinApiError``         — sonstige HTTP-Fehler (4xx/5xx).
  - ``DaikinDeviceError``      — Cloud meldet OK, aber Gerät weigert sich.
  - ``DaikinValidationError``  — Cloud-Antwort hält das Schema nicht ein.
"""

from __future__ import annotations

from typing import Final

__all__: Final = (
    "DaikinApiError",
    "DaikinAuthError",
    "DaikinDeviceError",
    "DaikinError",
    "DaikinRateLimitError",
    "DaikinValidationError",
)


class DaikinError(Exception):
    """Wurzel aller integrationsspezifischen Fehler."""


class DaikinAuthError(DaikinError):
    """Token-Refresh fehlgeschlagen oder Cloud verlangt Reauth (HTTP 401/400)."""


class DaikinRateLimitError(DaikinError):
    """Cloud-Rate-Limit erreicht (HTTP 429 oder ``remaining_*`` == 0).

    ``retry_after`` (Sekunden) wird aus dem entsprechenden Header übernommen,
    falls vorhanden; sonst ``None``.
    """

    def __init__(self, message: str, *, retry_after: int | None = None) -> None:
        super().__init__(message)
        self.retry_after = retry_after


class DaikinApiError(DaikinError):
    """HTTP- oder Transport-Fehler, der nicht spezifischer kategorisierbar ist."""

    def __init__(self, message: str, *, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status


class DaikinDeviceError(DaikinError):
    """Geräteseitiger Fehler — z. B. Patch wurde mit Non-204 quittiert."""


class DaikinValidationError(DaikinError):
    """Cloud-Antwort entspricht nicht dem erwarteten Schema."""
