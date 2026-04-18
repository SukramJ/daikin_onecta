"""Daikin Onecta cloud API client (transport layer).

This module is the canonical home of the HTTP/OAuth transport that talks
to the Daikin cloud. It knows nothing about Home Assistant platforms or
entity shapes — that belongs to ``model/`` and ``platforms/`` (phase 7).

The historic import path ``custom_components.daikin_onecta.daikin_api``
still works via a re-export shim and will be removed once all consumers
are migrated.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime
from http import HTTPStatus
from typing import Any
from typing import Final
from typing import TypedDict

from aiohttp import ClientError
from aiohttp import ClientResponseError
from homeassistant import config_entries
from homeassistant import core
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers import config_entry_oauth2_flow
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from ..const import DAIKIN_API_URL
from ..const import DOMAIN
from ..exceptions import DaikinApiError
from ..exceptions import DaikinAuthError

__all__: Final = ("DaikinApi", "JsonResponse", "RateLimits", "RequestResult")

# Defaults for the optional resilience building blocks. Values picked
# conservatively so the existing polling rhythm is not disturbed.
_RETRY_TRIES: Final = 3
_RETRY_BASE_DELAY: Final = 1.0
_RETRY_MAX_DELAY: Final = 5.0
_BREAKER_FAILURE_THRESHOLD: Final = 5
_BREAKER_RECOVERY_TIMEOUT: Final = 60.0

_LOGGER = logging.getLogger(__name__)

# JSON response shapes the Daikin cloud returns to us.
JsonResponse = dict[str, Any] | list[Any]

# What ``doBearerRequest`` returns to callers:
# - ``JsonResponse`` for GET (200)
# - ``True`` for PATCH/POST/PUT (204)
# - ``False`` when the cloud rejects a write (rate limit on the write path)
# - ``[]`` when a GET could not deliver data
RequestResult = JsonResponse | bool


class RateLimits(TypedDict):
    """HTTP-header-based rate-limit telemetry from the Daikin cloud."""

    minute: int
    day: int
    remaining_minutes: int
    remaining_day: int
    retry_after: int
    ratelimit_reset: int


class DaikinApi:
    """Daikin Onecta API."""

    def __init__(
        self,
        hass: core.HomeAssistant,
        entry: config_entries.ConfigEntry,
        implementation: config_entry_oauth2_flow.AbstractOAuth2Implementation,
    ) -> None:
        """Initialize a new Daikin Onecta API."""
        _LOGGER.debug("Initialing Daikin Onecta API...")
        self.hass = hass
        self._config_entry = entry
        self.session = config_entry_oauth2_flow.OAuth2Session(hass, entry, implementation)
        self._daikin_session = async_get_clientsession(hass)

        # The Daikin cloud returns old settings if queried with a GET
        # immediately after a PATCH request. Se we use this attribute
        # to check when we had the last patch command, if it is less then
        # 10 seconds ago we skip the get
        self._last_patch_call: datetime = datetime.min

        # Store the limits as member so that we can add these to the diagnostics
        self.rate_limits: RateLimits = {
            "minute": 0,
            "day": 0,
            "remaining_minutes": 0,
            "remaining_day": 0,
            "retry_after": 0,
            "ratelimit_reset": 0,
        }

        # Last successful cloud response — populated by the coordinator and
        # read by the diagnostics module.
        self.json_data: list[dict[str, Any]] | None = None

        # The following lock is used to serialize http requests to Daikin cloud
        # to prevent receiving old settings while a PATCH is ongoing.
        self._cloud_lock: asyncio.Lock = asyncio.Lock()

        # Resilience building blocks: the local import avoids a circular
        # import with ``support.throttle``.
        from ..support.circuit_breaker import CircuitBreaker  # pylint: disable=import-outside-toplevel

        self._breaker = CircuitBreaker(
            failure_threshold=_BREAKER_FAILURE_THRESHOLD,
            recovery_timeout=_BREAKER_RECOVERY_TIMEOUT,
        )

        _LOGGER.info("Daikin Onecta API initialized.")

    async def async_get_access_token(self) -> str:
        """Return a valid access token."""
        if not self.session.valid_token:
            try:
                await self.session.async_ensure_token_valid()
            except ClientResponseError as ex:
                # https://developers.home-assistant.io/docs/integration_setup_failures/#handling-expired-credentials
                if ex.status == HTTPStatus.BAD_REQUEST:
                    raise ConfigEntryAuthFailed(f"Problem refreshing token: {ex}") from ex
                raise

        return str(self.session.token["access_token"])

    def _update_rate_limits(self, headers: Any) -> None:
        """Copy header values into the ``rate_limits`` state."""
        self.rate_limits["minute"] = int(headers.get("X-RateLimit-Limit-minute", 0))
        self.rate_limits["day"] = int(headers.get("X-RateLimit-Limit-day", 0))
        self.rate_limits["remaining_minutes"] = int(headers.get("X-RateLimit-Remaining-minute", 0))
        self.rate_limits["remaining_day"] = int(headers.get("X-RateLimit-Remaining-day", 0))
        self.rate_limits["retry_after"] = int(headers.get("retry-after", 0))
        self.rate_limits["ratelimit_reset"] = int(headers.get("ratelimit-reset", 0))

        if self.rate_limits["remaining_minutes"] > 0:
            ir.async_delete_issue(self.hass, DOMAIN, "minute_rate_limit")

        if self.rate_limits["remaining_day"] > 0:
            ir.async_delete_issue(self.hass, DOMAIN, "day_rate_limit")

    def _raise_rate_limit_issues(self) -> None:
        """Surface exhausted rate-limit counters as persistent HA issues."""
        if self.rate_limits["remaining_minutes"] == 0:
            ir.async_create_issue(
                self.hass,
                DOMAIN,
                "minute_rate_limit",
                is_fixable=False,
                is_persistent=True,
                severity=ir.IssueSeverity.ERROR,
                learn_more_url="https://developer.cloud.daikineurope.com/docs/b0dffcaa-7b51-428a-bdff-a7c8a64195c0/general_api_guidelines#doc-heading-rate-limitation",
                translation_key="minute_rate_limit",
            )

        if self.rate_limits["remaining_day"] == 0:
            ir.async_create_issue(
                self.hass,
                DOMAIN,
                "day_rate_limit",
                is_fixable=False,
                is_persistent=True,
                severity=ir.IssueSeverity.ERROR,
                learn_more_url="https://developer.cloud.daikineurope.com/docs/b0dffcaa-7b51-428a-bdff-a7c8a64195c0/general_api_guidelines#doc-heading-rate-limitation",
                translation_key="day_rate_limit",
            )

    async def doBearerRequest(
        self,
        method: str,
        resource_url: str,
        options: str | None = None,
    ) -> RequestResult:
        """HTTP request against the Daikin cloud (serialized via ``_cloud_lock``).

        Return values:
        - GET 200      → ``JsonResponse``
        - PATCH/POST/PUT 204 → ``True``
        - GET 429      → ``[]`` (rate limit; an issue is registered)
        - Write 429    → ``False`` (rate limit on the write path)

        Raises:
        - ``DaikinAuthError``       — the token refresh failed, or the cloud
          answers the current request with HTTP 401.
        - ``DaikinRateLimitError``  — only when the caller opts in via the
          explicit wrapper API; ``doBearerRequest`` itself stays
          return-compatible on 429 so platform code stays unchanged.
        - ``DaikinApiError``        — transport error or HTTP 5xx (cloud
          outage). 3xx and other unexpected 4xx responses (except 401 / 429)
          are only logged and fall back to the default return value, to
          preserve the previous behaviour.
        """
        # Pre-check: circuit breaker. In the OPEN state we raise immediately
        # without reaching out to the cloud.
        await self._breaker.before_call()

        async with self._cloud_lock:
            try:
                token = await self.async_get_access_token()
            except ConfigEntryAuthFailed as ex:
                raise DaikinAuthError(str(ex)) from ex

            headers = {"Accept-Encoding": "gzip", "Authorization": "Bearer " + token, "Content-Type": "application/json"}

            _LOGGER.debug("Request URL: %s", resource_url)
            _LOGGER.debug("Request %s Options: %s", method, options)

            try:
                async with self._daikin_session.request(method=method, url=DAIKIN_API_URL + resource_url, headers=headers, data=options) as resp:
                    response_data = await resp.text()
                    # Body intentionally only at DEBUG: cloud responses may contain identifiers
                    # (gateway IDs, MAC addresses) that should not appear in default INFO logs.
                    _LOGGER.debug("Response status: %s Text: %s Limit: %s", resp.status, response_data, self.rate_limits)

                    self._update_rate_limits(resp.headers)

                    if method == "GET" and resp.status == HTTPStatus.OK:
                        await self._breaker.record_success()
                        try:
                            parsed: JsonResponse = json.loads(response_data)
                            return parsed
                        except json.JSONDecodeError:
                            _LOGGER.exception("Retrieve JSON failed: %s", response_data)
                            return []

                    if resp.status == HTTPStatus.TOO_MANY_REQUESTS:
                        self._raise_rate_limit_issues()
                        # Rate limit does not count as a breaker failure (expected state).
                        if method == "GET":
                            return []
                        return False

                    if resp.status == HTTPStatus.NO_CONTENT:
                        await self._breaker.record_success()
                        self._last_patch_call = datetime.now()
                        return True

                    # 401 mid-request: token was accepted, but the cloud still
                    # rejects the call. Not a breaker failure (auth issue, not
                    # a cloud outage).
                    if resp.status == HTTPStatus.UNAUTHORIZED:
                        raise DaikinAuthError(f"Daikin cloud rejected bearer token for {method} {resp.url}")

                    # 5xx: cloud outage → breaker should trip.
                    if resp.status >= HTTPStatus.INTERNAL_SERVER_ERROR:
                        await self._breaker.record_failure()
                        raise DaikinApiError(
                            f"Daikin cloud returned server error {resp.status}",
                            status=resp.status,
                        )

                    # All other status codes (3xx, unexpected 4xx): intentionally
                    # return-compatible with the previous behavior (empty list /
                    # False). No exception — otherwise the integration would hit
                    # ``UpdateFailed`` on every network hiccup. Log a warning
                    # instead.
                    _LOGGER.warning(
                        "Daikin cloud returned unexpected status %s for %s %s",
                        resp.status,
                        method,
                        resource_url,
                    )

            except ClientError as e:
                _LOGGER.error("REQUEST TYPE %s FAILED: %s", method, e)
                await self._breaker.record_failure()
                raise DaikinApiError(f"Daikin cloud request failed: {e}") from e

        # Unreachable: every status-code branch ends with either ``return`` or
        # ``raise``. This path only exists so mypy sees a definitive return.
        if method == "GET":
            return []
        return False

    async def getCloudDeviceDetails(self) -> list[dict[str, Any]]:
        """Get pure Device Data from the Daikin cloud devices.

        GETs are idempotent and are retried up to ``_RETRY_TRIES`` times with
        exponential backoff on ``DaikinApiError`` (transport errors, open
        circuit breaker, etc.). Auth and rate-limit errors are not retried.
        """
        # Local import avoids a circular dependency with support.throttle,
        # which imports RateLimits.
        from ..support.retry import retry_with_backoff  # pylint: disable=import-outside-toplevel

        @retry_with_backoff(
            tries=_RETRY_TRIES,
            base_delay=_RETRY_BASE_DELAY,
            max_delay=_RETRY_MAX_DELAY,
        )
        async def _do_get() -> RequestResult:
            return await self.doBearerRequest("GET", "/v1/gateway-devices")

        result = await _do_get()
        if isinstance(result, list):
            return result
        # GET should never yield ``True``/``False`` — fall back to empty.
        return []
