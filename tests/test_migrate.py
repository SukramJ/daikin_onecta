"""Phase 8.8 — tests for ``async_migrate_entry`` (version migrations)."""

from __future__ import annotations

from typing import Any

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.daikin_onecta import async_migrate_entry
from custom_components.daikin_onecta.const import DOMAIN

# JWT with ``sub = 1234567890`` (see conftest.FAKE_ACCESS_TOKEN)
_VALID_JWT = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
    ".eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ"
    ".SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
)


def _entry(*, version: int, minor: int, token: dict[str, Any] | None = None) -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN,
        version=version,
        minor_version=minor,
        data={"auth_implementation": "cloud", "token": token or {"access_token": _VALID_JWT}},
    )


async def test_migrate_v1_1_decodes_jwt_and_sets_unique_id(hass: HomeAssistant):
    entry = _entry(version=1, minor=1)
    entry.add_to_hass(hass)
    assert await async_migrate_entry(hass, entry) is True
    assert entry.minor_version == 2
    assert entry.unique_id == "1234567890"


async def test_migrate_v1_1_with_invalid_jwt_returns_false(hass: HomeAssistant):
    entry = _entry(version=1, minor=1, token={"access_token": "not-a-jwt"})
    entry.add_to_hass(hass)
    assert await async_migrate_entry(hass, entry) is False
    # Kein Update bei Fehler
    assert entry.minor_version == 1
    assert entry.unique_id is None


async def test_migrate_v1_1_missing_sub_returns_false(hass: HomeAssistant):
    # JWT ohne ``sub``-Claim (selbst-konstruiert: Header.Payload.Signature)
    no_sub = "eyJhbGciOiJIUzI1NiJ9.eyJuYW1lIjoiSm9obiBEb2UifQ.dummy"
    entry = _entry(version=1, minor=1, token={"access_token": no_sub})
    entry.add_to_hass(hass)
    assert await async_migrate_entry(hass, entry) is False


async def test_migrate_v1_2_is_noop(hass: HomeAssistant):
    """Eintrag ist bereits aktuell — Migration tut nichts und bleibt erfolgreich."""
    entry = _entry(version=1, minor=2)
    entry.add_to_hass(hass)
    assert await async_migrate_entry(hass, entry) is True
    assert entry.minor_version == 2


@pytest.mark.parametrize("minor", [3, 4, 99])
async def test_migrate_unknown_minor_version_does_nothing(hass: HomeAssistant, minor: int):
    """Unbekannte minor-Versionen passieren stumm — Schutz gegen Downgrade-Loops."""
    entry = _entry(version=1, minor=minor)
    entry.add_to_hass(hass)
    assert await async_migrate_entry(hass, entry) is True
    assert entry.minor_version == minor
