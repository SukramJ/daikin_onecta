"""Tests for the HTTP / auth behavior of ``DaikinApi``."""

from __future__ import annotations

import asyncio
import json
from http import HTTPStatus
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest
from aiohttp import ClientError
from aiohttp import ClientResponseError
from homeassistant.exceptions import ConfigEntryAuthFailed

from custom_components.daikin_onecta.daikin_api import DaikinApi
from custom_components.daikin_onecta.exceptions import DaikinApiError
from custom_components.daikin_onecta.exceptions import DaikinAuthError
from custom_components.daikin_onecta.support import CircuitState


def _make_api(hass) -> DaikinApi:
    entry = MagicMock()
    impl = MagicMock()
    with (
        patch("custom_components.daikin_onecta.daikin_api.config_entry_oauth2_flow.OAuth2Session"),
        patch("custom_components.daikin_onecta.daikin_api.async_get_clientsession"),
    ):
        api = DaikinApi(hass, entry, impl)
    api.session = MagicMock()
    api.session.token = {"access_token": "ACCESS"}
    api.session.valid_token = True
    return api


def _resp(status: int, body: str = "", headers: dict | None = None):
    """Build an async-context-manager mock for aiohttp's response."""
    response = MagicMock()
    response.status = status
    response.headers = headers or {}
    response.text = AsyncMock(return_value=body)

    async def _aenter():
        return response

    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=response)
    cm.__aexit__ = AsyncMock(return_value=None)
    return cm


@pytest.fixture
def api(hass):
    return _make_api(hass)


class TestAccessToken:
    """async_get_access_token & reauth mapping."""

    async def test_returns_token_when_valid(self, api):
        api.session.valid_token = True
        api.session.token = {"access_token": "tok"}
        assert await api.async_get_access_token() == "tok"

    async def test_refreshes_when_invalid(self, api):
        api.session.valid_token = False
        api.session.async_ensure_token_valid = AsyncMock()
        api.session.token = {"access_token": "fresh"}
        assert await api.async_get_access_token() == "fresh"
        api.session.async_ensure_token_valid.assert_awaited_once()

    async def test_400_during_refresh_raises_config_entry_auth_failed(self, api):
        api.session.valid_token = False
        err = ClientResponseError(MagicMock(), (), status=HTTPStatus.BAD_REQUEST)
        api.session.async_ensure_token_valid = AsyncMock(side_effect=err)
        with pytest.raises(ConfigEntryAuthFailed):
            await api.async_get_access_token()

    async def test_other_status_during_refresh_propagates(self, api):
        api.session.valid_token = False
        err = ClientResponseError(MagicMock(), (), status=HTTPStatus.INTERNAL_SERVER_ERROR)
        api.session.async_ensure_token_valid = AsyncMock(side_effect=err)
        with pytest.raises(ClientResponseError):
            await api.async_get_access_token()


class TestDoBearerRequest:
    """doBearerRequest: status codes, headers, exceptions."""

    async def test_get_200_returns_parsed_json(self, api):
        api._daikin_session.request = MagicMock(
            return_value=_resp(
                HTTPStatus.OK,
                body=json.dumps([{"id": "x"}]),
                headers={
                    "X-RateLimit-Limit-minute": "100",
                    "X-RateLimit-Limit-day": "10000",
                    "X-RateLimit-Remaining-minute": "99",
                    "X-RateLimit-Remaining-day": "9999",
                },
            )
        )
        result = await api.doBearerRequest("GET", "/v1/gateway-devices")
        assert result == [{"id": "x"}]
        # Rate limits adopted from headers
        assert api.rate_limits["remaining_minutes"] == 99
        assert api.rate_limits["remaining_day"] == 9999

    async def test_get_200_with_invalid_json_returns_empty_list(self, api):
        api._daikin_session.request = MagicMock(return_value=_resp(HTTPStatus.OK, body="not json"))
        assert await api.doBearerRequest("GET", "/v1/gateway-devices") == []

    async def test_patch_204_returns_true_and_records_patch_time(self, api):
        api._last_patch_call = MagicMock()
        api._daikin_session.request = MagicMock(return_value=_resp(HTTPStatus.NO_CONTENT))
        result = await api.doBearerRequest("PATCH", "/v1/.../characteristics/onOffMode", '{"value": "on"}')
        assert result is True
        # _last_patch_call should be updated
        assert api._last_patch_call is not None

    async def test_get_429_returns_empty_list(self, api):
        api._daikin_session.request = MagicMock(return_value=_resp(HTTPStatus.TOO_MANY_REQUESTS, headers={"retry-after": "60"}))
        result = await api.doBearerRequest("GET", "/v1/gateway-devices")
        assert result == []

    async def test_patch_429_returns_false(self, api):
        api._daikin_session.request = MagicMock(return_value=_resp(HTTPStatus.TOO_MANY_REQUESTS, headers={"retry-after": "60"}))
        result = await api.doBearerRequest("PATCH", "/v1/.../onOffMode", '{"value": "on"}')
        assert result is False

    async def test_client_error_raises_daikin_api_error(self, api):
        api._daikin_session.request = MagicMock(side_effect=ClientError("network down"))
        with pytest.raises(DaikinApiError, match="network down"):
            await api.doBearerRequest("GET", "/v1/gateway-devices")

    async def test_token_refresh_failure_raises_daikin_auth_error(self, api):
        api.session.valid_token = False
        api.session.async_ensure_token_valid = AsyncMock(side_effect=ClientResponseError(MagicMock(), (), status=HTTPStatus.BAD_REQUEST))
        with pytest.raises(DaikinAuthError):
            await api.doBearerRequest("GET", "/v1/gateway-devices")

    async def test_mid_request_401_raises_daikin_auth_error_and_keeps_breaker_closed(self, api):
        api._daikin_session.request = MagicMock(return_value=_resp(HTTPStatus.UNAUTHORIZED, body="expired"))
        with pytest.raises(DaikinAuthError):
            await api.doBearerRequest("GET", "/v1/gateway-devices")
        # Auth error is not a cloud outage → breaker must not trip.
        assert api._breaker.state is CircuitState.CLOSED

    async def test_500_raises_daikin_api_error_and_records_breaker_failure(self, api):
        api._daikin_session.request = MagicMock(return_value=_resp(HTTPStatus.INTERNAL_SERVER_ERROR))
        with pytest.raises(DaikinApiError) as exc:
            await api.doBearerRequest("GET", "/v1/gateway-devices")
        assert exc.value.status == HTTPStatus.INTERNAL_SERVER_ERROR
        # 5xx counts as a breaker failure.
        assert api._breaker._failures == 1

    async def test_503_raises_daikin_api_error(self, api):
        api._daikin_session.request = MagicMock(return_value=_resp(HTTPStatus.SERVICE_UNAVAILABLE))
        with pytest.raises(DaikinApiError) as exc:
            await api.doBearerRequest("GET", "/v1/gateway-devices")
        assert exc.value.status == HTTPStatus.SERVICE_UNAVAILABLE

    async def test_unexpected_4xx_returns_false_without_breaker_failure(self, api):
        # 3xx / unexpected 4xx (except 401/429) are intentionally not surfaced
        # as exceptions — that would push the coordinator into UpdateFailed on
        # every network hiccup. The return stays return-compatible.
        api._daikin_session.request = MagicMock(return_value=_resp(HTTPStatus.BAD_REQUEST, body="bad"))
        result = await api.doBearerRequest("PATCH", "/v1/.../onOffMode", '{"value": "on"}')
        assert result is False
        assert api._breaker._failures == 0

    async def test_unexpected_3xx_returns_empty_list_without_breaker_failure(self, api):
        api._daikin_session.request = MagicMock(return_value=_resp(HTTPStatus.MULTIPLE_CHOICES, body="redirect"))
        result = await api.doBearerRequest("GET", "/v1/gateway-devices")
        assert result == []
        assert api._breaker._failures == 0


class TestCloudLockSerialization:
    """Phase 8.7 — race condition: two parallel calls are serialized."""

    async def test_parallel_calls_are_serialized(self, api):
        order: list[str] = []

        def make_request(method, url, headers, data):
            response = MagicMock()
            response.status = HTTPStatus.NO_CONTENT
            response.headers = {}
            response.text = AsyncMock(return_value="")

            async def _aenter():
                order.append(f"start-{data}")
                await asyncio.sleep(0.05)
                order.append(f"end-{data}")
                return response

            cm = MagicMock()
            cm.__aenter__ = AsyncMock(side_effect=_aenter)
            cm.__aexit__ = AsyncMock(return_value=None)
            return cm

        api._daikin_session.request = MagicMock(side_effect=make_request)

        await asyncio.gather(
            api.doBearerRequest("PATCH", "/a", "first"),
            api.doBearerRequest("PATCH", "/b", "second"),
        )
        # If the lock works, the calls must never overlap,
        # i.e. every "start-X" must be followed by its "end-X" before the next "start".
        assert order in (
            ["start-first", "end-first", "start-second", "end-second"],
            ["start-second", "end-second", "start-first", "end-first"],
        )


class TestCircuitBreakerIntegration:
    """Phase 6.4 — circuit breaker engages in doBearerRequest."""

    async def test_consecutive_client_errors_open_breaker(self, api):
        api._daikin_session.request = MagicMock(side_effect=ClientError("boom"))
        # threshold=5: 5 failures are enough
        for _ in range(5):
            with pytest.raises(DaikinApiError):
                await api.doBearerRequest("GET", "/v1/gateway-devices")
        assert api._breaker.state is CircuitState.OPEN

    async def test_open_breaker_short_circuits_calls(self, api):
        # Manipulate the breaker directly
        for _ in range(api._breaker._failure_threshold):
            await api._breaker.record_failure()
        assert api._breaker.state is CircuitState.OPEN

        # Network call must no longer happen
        api._daikin_session.request = MagicMock()
        from custom_components.daikin_onecta.support import CircuitBreakerOpenError

        with pytest.raises(CircuitBreakerOpenError):
            await api.doBearerRequest("GET", "/v1/gateway-devices")
        api._daikin_session.request.assert_not_called()


class TestRetryIntegration:
    """getCloudDeviceDetails retries on DaikinApiError."""

    async def test_retries_on_transient_failure(self, api, monkeypatch):
        async def _no_sleep(*_args, **_kwargs):
            return None

        monkeypatch.setattr(asyncio, "sleep", _no_sleep)

        calls = {"n": 0}

        async def fake_do_bearer_request(method, url, options=None):
            calls["n"] += 1
            if calls["n"] < 3:
                raise DaikinApiError("transient")
            return [{"id": "device-1"}]

        api.doBearerRequest = fake_do_bearer_request
        result = await api.getCloudDeviceDetails()
        assert result == [{"id": "device-1"}]
        assert calls["n"] == 3

    async def test_auth_error_not_retried(self, api, monkeypatch):
        async def _no_sleep(*_args, **_kwargs):
            return None

        monkeypatch.setattr(asyncio, "sleep", _no_sleep)
        calls = {"n": 0}

        async def fake_do_bearer_request(method, url, options=None):
            calls["n"] += 1
            raise DaikinAuthError("expired")

        api.doBearerRequest = fake_do_bearer_request
        with pytest.raises(DaikinAuthError):
            await api.getCloudDeviceDetails()
        assert calls["n"] == 1
