"""Tests for the model-level listener system on ``DaikinOnectaDevice`` (phase 7.9)."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from custom_components.daikin_onecta.model.device import DaikinOnectaDevice

FIXTURES = Path(__file__).parent / "fixtures"


def _load_first_device(name: str) -> dict:
    with (FIXTURES / name).open(encoding="utf-8") as handle:
        data = json.load(handle)
    return data[0] if isinstance(data, list) else data


def _mutate_field(device: DaikinOnectaDevice, embedded_id: str, field: str, value: Any) -> dict:
    """Return a deep-copied device payload with one field replaced."""
    payload = copy.deepcopy(device.daikin_data)
    for mp in payload["managementPoints"]:
        if mp["embeddedId"] == embedded_id:
            mp[field]["value"] = value
            break
    return payload


@pytest.fixture
def device() -> DaikinOnectaDevice:
    """Return a device populated from the altherma fixture with a fake API."""
    api = MagicMock()
    return DaikinOnectaDevice(_load_first_device("altherma.json"), api)


@pytest.fixture
def cc_embedded_id(device: DaikinOnectaDevice) -> str:
    """embedded_id of the climateControl management point in the fixture."""
    mp = next(m for m in device.daikin_data["managementPoints"] if m["managementPointType"] == "climateControl")
    return str(mp["embeddedId"])


class TestDeviceListener:
    """``add_listener`` fires on any DataPoint change or availability toggle."""

    def test_fires_on_value_change(self, device: DaikinOnectaDevice, cc_embedded_id: str) -> None:
        cb = MagicMock()
        device.add_listener(cb)

        current = next(mp["onOffMode"]["value"] for mp in device.daikin_data["managementPoints"] if mp["embeddedId"] == cc_embedded_id)
        flipped = "off" if current == "on" else "on"
        device.setJsonData(_mutate_field(device, cc_embedded_id, "onOffMode", flipped))

        cb.assert_called_once()

    def test_does_not_fire_when_nothing_changed(self, device: DaikinOnectaDevice) -> None:
        cb = MagicMock()
        device.add_listener(cb)

        # Re-send the exact same payload.
        device.setJsonData(copy.deepcopy(device.daikin_data))

        cb.assert_not_called()

    def test_fires_on_availability_change(self, device: DaikinOnectaDevice) -> None:
        cb = MagicMock()
        device.add_listener(cb)

        payload = copy.deepcopy(device.daikin_data)
        payload["isCloudConnectionUp"]["value"] = not device.available
        device.setJsonData(payload)

        cb.assert_called_once()

    def test_unsubscribe_stops_callbacks(self, device: DaikinOnectaDevice, cc_embedded_id: str) -> None:
        cb = MagicMock()
        unsub = device.add_listener(cb)
        unsub()

        current = next(mp["onOffMode"]["value"] for mp in device.daikin_data["managementPoints"] if mp["embeddedId"] == cc_embedded_id)
        flipped = "off" if current == "on" else "on"
        device.setJsonData(_mutate_field(device, cc_embedded_id, "onOffMode", flipped))

        cb.assert_not_called()


class TestManagementPointListener:
    """``add_management_point_listener`` fires only for its ``embedded_id``."""

    def test_fires_on_own_mp_change(self, device: DaikinOnectaDevice, cc_embedded_id: str) -> None:
        cb = MagicMock()
        device.add_management_point_listener(cc_embedded_id, cb)

        current = next(mp["onOffMode"]["value"] for mp in device.daikin_data["managementPoints"] if mp["embeddedId"] == cc_embedded_id)
        flipped = "off" if current == "on" else "on"
        device.setJsonData(_mutate_field(device, cc_embedded_id, "onOffMode", flipped))

        cb.assert_called_once()

    def test_does_not_fire_for_other_mp(self, device: DaikinOnectaDevice, cc_embedded_id: str) -> None:
        cb = MagicMock()
        device.add_management_point_listener(cc_embedded_id, cb)

        # Change something on the gateway management point instead.
        gateway = next(mp for mp in device.daikin_data["managementPoints"] if mp["managementPointType"] == "gateway")
        gateway_id = gateway["embeddedId"]
        # Find any string value-wrapper on gateway and flip it.
        changed_field = None
        changed_new_value: Any = None
        for field, wrapper in gateway.items():
            if isinstance(wrapper, dict) and isinstance(wrapper.get("value"), str):
                changed_field = field
                changed_new_value = wrapper["value"] + "_x"
                break
        assert changed_field is not None, "fixture must expose a string field on gateway"
        device.setJsonData(_mutate_field(device, gateway_id, changed_field, changed_new_value))

        cb.assert_not_called()


class TestDataPointListener:
    """``add_data_point_listener`` fires only for its ``(embedded_id, name)`` key."""

    def test_fires_on_own_field_change(self, device: DaikinOnectaDevice, cc_embedded_id: str) -> None:
        cb = MagicMock()
        device.add_data_point_listener(cc_embedded_id, "onOffMode", cb)

        current = next(mp["onOffMode"]["value"] for mp in device.daikin_data["managementPoints"] if mp["embeddedId"] == cc_embedded_id)
        flipped = "off" if current == "on" else "on"
        device.setJsonData(_mutate_field(device, cc_embedded_id, "onOffMode", flipped))

        cb.assert_called_once()

    def test_does_not_fire_on_sibling_field(self, device: DaikinOnectaDevice, cc_embedded_id: str) -> None:
        cb = MagicMock()
        device.add_data_point_listener(cc_embedded_id, "onOffMode", cb)

        cc_mp = next(mp for mp in device.daikin_data["managementPoints"] if mp["embeddedId"] == cc_embedded_id)
        op_mode_wrapper = cc_mp.get("operationMode")
        if op_mode_wrapper is None:
            pytest.skip("Fixture climateControl has no operationMode field")
        values = op_mode_wrapper.get("values", [])
        other = next((v for v in values if v != op_mode_wrapper["value"]), None)
        if other is None:
            pytest.skip("Fixture has no alternate operationMode value")
        device.setJsonData(_mutate_field(device, cc_embedded_id, "operationMode", other))

        cb.assert_not_called()

    def test_unsubscribe_only_removes_that_listener(self, device: DaikinOnectaDevice, cc_embedded_id: str) -> None:
        cb_a = MagicMock()
        cb_b = MagicMock()
        unsub_a = device.add_data_point_listener(cc_embedded_id, "onOffMode", cb_a)
        device.add_data_point_listener(cc_embedded_id, "onOffMode", cb_b)
        unsub_a()

        current = next(mp["onOffMode"]["value"] for mp in device.daikin_data["managementPoints"] if mp["embeddedId"] == cc_embedded_id)
        flipped = "off" if current == "on" else "on"
        device.setJsonData(_mutate_field(device, cc_embedded_id, "onOffMode", flipped))

        cb_a.assert_not_called()
        cb_b.assert_called_once()


class TestDiffingSemantics:
    """The diff is based on DataPoint ``value``, not wrapper identity."""

    def test_identical_value_does_not_fire(self, device: DaikinOnectaDevice) -> None:
        cb = MagicMock()
        device.add_listener(cb)

        # Resending the same payload should not trigger any listener.
        device.setJsonData(copy.deepcopy(device.daikin_data))

        cb.assert_not_called()
