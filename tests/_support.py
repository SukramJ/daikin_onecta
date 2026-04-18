"""Shared test utilities for the daikin_onecta integration test suite.

Pure helpers and constants that don't need pytest discovery live here so
``conftest.py`` stays focused on actual fixtures. Anything imported via
``from .conftest import ...`` historically belongs in this module instead.
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock
from unittest.mock import patch

import homeassistant.helpers.entity_registry as er
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.syrupy import HomeAssistantSnapshotExtension
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker
from syrupy import SnapshotAssertion
from syrupy.filters import props
from syrupy.location import PyTestLocation
from syrupy.types import SnapshotIndex

from custom_components.daikin_onecta.const import DAIKIN_API_URL
from custom_components.daikin_onecta.coordinator import OnectaRuntimeData

FAKE_REFRESH_TOKEN = "some-refresh-token"
FAKE_ACCESS_TOKEN = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
    ".eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ"
    ".SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
)
FAKE_AUTH_IMPL = "conftest-imported-cred"


def load_fixture_json(name: str) -> Any:
    """Load a Daikin Onecta cloud-response fixture from ``tests/fixtures/``."""
    with open(f"tests/fixtures/{name}.json") as json_file:
        return json.load(json_file)


class PerTestSnapshotExtension(HomeAssistantSnapshotExtension):
    """Write one ``.ambr`` file per test function instead of per test module.

    The default HA extension bundles every snapshot from a test file into a
    single ``<module>.ambr``. ``test_init.py`` grew to ~80k lines that way,
    making review and bisecting individual device regressions painful. This
    subclass includes the test's ``methodname`` (e.g. ``test_homehub``) in the
    file basename so each device-specific test ends up in its own, reviewable
    file under ``tests/snapshots/``.
    """

    @classmethod
    def get_file_basename(cls, *, test_location: PyTestLocation, index: SnapshotIndex) -> str:
        return f"{test_location.basename}__{test_location.methodname}"


async def snapshot_platform_entities(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    config_entry: MockConfigEntry,
    platform: Platform,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
    fixture_device_json: str,
) -> None:
    """Set up the integration from a fixture and snapshot all resulting entities."""
    config_entry.runtime_data = OnectaRuntimeData(daikin_api=MagicMock(), coordinator=MagicMock(), devices={})
    with (
        patch(
            "homeassistant.helpers.config_entry_oauth2_flow.async_get_config_entry_implementation",
        ),
        patch(
            "homeassistant.helpers.config_entry_oauth2_flow.OAuth2Session.valid_token",
            False,
        ),
        patch(
            "homeassistant.helpers.config_entry_oauth2_flow.OAuth2Session.async_ensure_token_valid",
        ),
        patch(
            "homeassistant.helpers.config_entry_oauth2_flow.OAuth2Session.token",
            {"access_token": FAKE_ACCESS_TOKEN},
        ),
    ):
        aioclient_mock.get(DAIKIN_API_URL + "/v1/gateway-devices", status=200, json=load_fixture_json(fixture_device_json))
        assert await hass.config_entries.async_setup(config_entry.entry_id)

        await hass.async_block_till_done()

    entity_entries = er.async_entries_for_config_entry(entity_registry, config_entry.entry_id)

    assert entity_entries
    # ``friendly_name`` is excluded from state snapshots because Home Assistant
    # composes it from the device name plus the entity's translated name. The
    # translation cache is shared process-wide and warmed lazily, so the same
    # state can render either ``"<device>"`` or ``"<device> <ManagementPoint>"``
    # depending on which test ran first. The information is fully covered by
    # ``original_name`` and ``translation_key`` in the entry snapshot.
    state_excludes = props("friendly_name")
    for entity_entry in entity_entries:
        assert entity_entry == snapshot(name=f"{entity_entry.entity_id}-entry")
        assert hass.states.get(entity_entry.entity_id) == snapshot(name=f"{entity_entry.entity_id}-state", exclude=state_excludes)
