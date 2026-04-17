"""Platform for the Daikin AC."""

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

from .const import DAIKIN_API_URL
from .const import DOMAIN
from .exceptions import DaikinApiError
from .exceptions import DaikinAuthError
from .exceptions import DaikinRateLimitError

__all__: Final = ("DaikinApi", "RateLimits")

# Defaults für die optionalen Resilienz-Bausteine. Werte konservativ gewählt,
# damit der bisherige Polling-Rhythmus nicht gestört wird.
_RETRY_TRIES: Final = 3
_RETRY_BASE_DELAY: Final = 1.0
_RETRY_MAX_DELAY: Final = 5.0
_BREAKER_FAILURE_THRESHOLD: Final = 5
_BREAKER_RECOVERY_TIMEOUT: Final = 60.0

_LOGGER = logging.getLogger(__name__)

# JSON-Antworttypen, die wir aus der Cloud zurückbekommen.
JsonResponse = dict[str, Any] | list[Any]

# Was ``doBearerRequest`` an die Aufrufer zurückgibt:
# - ``JsonResponse`` für GET (200)
# - ``True`` für PATCH/POST/PUT (204)
# - ``False`` wenn Cloud die Schreiboperation ablehnt (Rate-Limit auf Write-Pfad)
# - ``[]`` wenn ein GET keine Daten liefern konnte
RequestResult = JsonResponse | bool


class RateLimits(TypedDict):
    """HTTP-Header-basierte Rate-Limit-Telemetrie der Daikin-Cloud."""

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

        # Letzte erfolgreiche Cloud-Antwort — wird vom Coordinator gefüllt und
        # vom Diagnostics-Modul gelesen.
        self.json_data: list[dict[str, Any]] | None = None

        # The following lock is used to serialize http requests to Daikin cloud
        # to prevent receiving old settings while a PATCH is ongoing.
        self._cloud_lock: asyncio.Lock = asyncio.Lock()

        # Resilienz-Bausteine: lokale Imports vermeiden Zirkel mit support.throttle.
        from .support.circuit_breaker import CircuitBreaker

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
        """Header-Werte in den ``rate_limits``-State übernehmen."""
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
        """Fehlende Rate-Limit-Headerwerte als persistente HA-Issues anlegen."""
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

    async def doBearerRequest(  # noqa: N802 - öffentlicher Name historisch
        self,
        method: str,
        resource_url: str,
        options: str | None = None,
    ) -> RequestResult:
        """HTTP-Request gegen die Daikin-Cloud (serialisiert über ``_cloud_lock``).

        Rückgabewerte:
        - GET 200      → ``JsonResponse``
        - PATCH/POST/PUT 204 → ``True``
        - GET 429      → ``[]`` (Rate-Limit; Issue wird angelegt)
        - Write 429    → ``False`` (Rate-Limit auf Write-Pfad)

        Wirft:
        - ``DaikinAuthError``       — Token-Refresh schlug fehl (HTTP 401).
        - ``DaikinRateLimitError``  — wenn der Aufrufer Rate-Limits durchreichen will
          (aktuell nur über die explizite Wrapper-API; ``doBearerRequest`` selbst
          bleibt rückgabe-kompatibel, damit Plattform-Code unverändert bleibt).
        - ``DaikinApiError``        — Transport-Fehler oder 5xx.
        """
        # Pre-Check: Circuit-Breaker. Im OPEN-State wird sofort geworfen,
        # ohne die Cloud zu kontaktieren.
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
                        # Rate-Limit zählt nicht als Breaker-Failure (erwarteter Zustand).
                        if method == "GET":
                            return []
                        return False

                    if resp.status == HTTPStatus.NO_CONTENT:
                        await self._breaker.record_success()
                        self._last_patch_call = datetime.now()
                        return True

            except ClientError as e:
                _LOGGER.error("REQUEST TYPE %s FAILED: %s", method, e)
                await self._breaker.record_failure()
                raise DaikinApiError(f"Daikin cloud request failed: {e}") from e

        if method == "GET":
            return []
        return False

    async def getCloudDeviceDetails(self) -> list[dict[str, Any]]:  # noqa: N802 - öffentlicher Name historisch
        """Get pure Device Data from the Daikin cloud devices.

        GETs sind idempotent und werden bei ``DaikinApiError`` (Transport-Fehler,
        Circuit-Breaker offen, etc.) bis zu ``_RETRY_TRIES``-mal mit exponentiellem
        Backoff wiederholt. Auth- und Rate-Limit-Fehler werden nicht wiederholt.
        """
        # Lokaler Import vermeidet Zirkel mit support.throttle, das RateLimits importiert.
        from .support.retry import retry_with_backoff

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
        # GET sollte niemals ``True``/``False`` liefern — sicherheitshalber leer.
        return []
