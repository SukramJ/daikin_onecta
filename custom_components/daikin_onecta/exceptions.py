"""Dedicated exception hierarchy for the Daikin Onecta integration.

Background: previously many code paths signaled errors via sentinel values
(``False``/``[]``) or plain ``Exception``. That makes it hard for the
coordinator to map correctly to ``UpdateFailed`` / ``ConfigEntryAuthFailed`` /
``ConfigEntryNotReady``.

With this hierarchy we can catch and translate errors precisely:

- ``DaikinError``              — root; everything the integration raises.
  - ``DaikinAuthError``        — token/OAuth problems → reauth.
  - ``DaikinRateLimitError``   — HTTP 429 or exhausted daily budget.
  - ``DaikinApiError``         — other HTTP errors (4xx/5xx).
  - ``DaikinDeviceError``      — cloud reports OK but the device refuses.
  - ``DaikinValidationError``  — cloud response does not match the schema.
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
    """Root of all integration-specific errors."""


class DaikinAuthError(DaikinError):
    """Token refresh failed or the cloud requires reauth (HTTP 401/400)."""


class DaikinRateLimitError(DaikinError):
    """Cloud rate limit reached (HTTP 429 or ``remaining_*`` == 0).

    ``retry_after`` (seconds) is taken from the corresponding header when
    present; otherwise ``None``.
    """

    def __init__(self, message: str, *, retry_after: int | None = None) -> None:
        super().__init__(message)
        self.retry_after = retry_after


class DaikinApiError(DaikinError):
    """HTTP or transport error that cannot be categorized more specifically."""

    def __init__(self, message: str, *, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status


class DaikinDeviceError(DaikinError):
    """Device-side error — e.g. a PATCH was acknowledged with a non-204 status."""


class DaikinValidationError(DaikinError):
    """Cloud response does not match the expected schema."""
