"""Pytest fixtures for the daikin_onecta integration test suite.

Pure helpers (constants, snapshot extension, ``snapshot_platform_entities``)
live in ``tests/_support.py`` so this module stays focused on actual fixtures.
"""

from __future__ import annotations

import time
from typing import Any
from unittest.mock import AsyncMock
from unittest.mock import patch

import pytest
from _pytest.assertion import truncate
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry
from syrupy import SnapshotAssertion

from custom_components.daikin_onecta.const import DOMAIN
from tests._support import FAKE_ACCESS_TOKEN
from tests._support import FAKE_AUTH_IMPL
from tests._support import FAKE_REFRESH_TOKEN
from tests._support import PerTestSnapshotExtension

truncate.DEFAULT_MAX_LINES = 9999
truncate.DEFAULT_MAX_CHARS = 9999


@pytest.fixture
def snapshot(snapshot: SnapshotAssertion) -> SnapshotAssertion:
    """Wrap syrupy's snapshot fixture with our per-test HA extension.

    pytest_homeassistant_custom_component ships a comparable override, but its
    discovery is unreliable when other plugins (e.g. syrupy itself) provide a
    fixture under the same name. Redeclaring it here pins the resolution so
    snapshots are written under tests/snapshots/ in the HA-aware format, split
    per test function.
    """
    return snapshot.use_extension(PerTestSnapshotExtension)


@pytest.fixture(name="auto_enable_custom_integrations", autouse=True)
def auto_enable_custom_integrations(hass: Any, enable_custom_integrations: Any) -> None:
    """Enable custom integrations defined in the test dir."""


@pytest.fixture(name="config_entry")
def mock_config_entry_fixture(hass: HomeAssistant) -> MockConfigEntry:
    """Mock a config entry."""
    mock_entry = MockConfigEntry(
        domain="daikin_onecta",
        data={
            "auth_implementation": "cloud",
            "token": {
                "refresh_token": "mock-refresh-token",
                "access_token": FAKE_ACCESS_TOKEN,
                "type": "Bearer",
                "expires_in": 60,
                "expires_at": 1000,
                "scope": 1,
            },
        },
    )
    mock_entry.add_to_hass(hass)

    return mock_entry


@pytest.fixture(name="onecta_auth")
def onecta_auth() -> AsyncMock:
    """Restrict loaded platforms to list given."""
    return


@pytest.fixture(name="access_token")
def async_get_access_token() -> AsyncMock:
    """Restrict loaded platforms to list given."""

    with patch(
        "custom_components.daikin_onecta.DaikinApi.async_get_access_token",
        return_value=FAKE_ACCESS_TOKEN,
    ):
        yield


@pytest.fixture(name="token_expiration_time")
def mock_token_expiration_time() -> float:
    """Fixture for expiration time of the config entry auth token."""
    return time.time() + 86400


@pytest.fixture(name="token_entry")
def mock_token_entry(token_expiration_time: float) -> dict[str, Any]:
    """Fixture for OAuth 'token' data for a ConfigEntry."""
    return {
        "refresh_token": FAKE_REFRESH_TOKEN,
        "access_token": FAKE_ACCESS_TOKEN,
        "type": "Bearer",
        "expires_at": token_expiration_time,
    }


@pytest.fixture(name="config_entry_v1_1")
def mock_config_entry_v1_1(token_entry: dict[str, Any]) -> MockConfigEntry:
    """Fixture for a config entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        data={
            "auth_implementation": FAKE_AUTH_IMPL,
            "token": token_entry,
        },
        minor_version=1,
    )
