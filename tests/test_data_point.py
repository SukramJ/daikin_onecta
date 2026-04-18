"""Tests for the ``DataPoint`` wrapper (phase 7.5)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from custom_components.daikin_onecta.model.data_point import DataPoint
from custom_components.daikin_onecta.model.data_point import iter_data_points
from custom_components.daikin_onecta.model.management_point import (
    management_point_from_json,
)

FIXTURES = Path(__file__).parent / "fixtures"


def _load(name: str) -> list[dict]:
    with (FIXTURES / name).open(encoding="utf-8") as handle:
        data = json.load(handle)
    return data if isinstance(data, list) else [data]


class TestFromField:
    """``DataPoint.from_field`` parses the cloud wrapper shape."""

    def test_full_numeric_field(self) -> None:
        dp = DataPoint.from_field(
            "targetTemperature",
            {
                "value": 20.0,
                "settable": True,
                "minValue": 5.0,
                "maxValue": 30.0,
                "stepValue": 0.5,
                "requiresReboot": False,
            },
            embedded_id="climateControlMainZone",
        )
        assert dp.name == "targetTemperature"
        assert dp.embedded_id == "climateControlMainZone"
        assert dp.value == 20.0
        assert dp.settable is True
        assert dp.min_value == 5.0
        assert dp.max_value == 30.0
        assert dp.step_value == 0.5
        assert dp.requires_reboot is False

    def test_string_field_has_no_bounds(self) -> None:
        dp = DataPoint.from_field("onOffMode", {"value": "on", "settable": True})
        assert dp.value == "on"
        assert dp.settable is True
        assert dp.min_value is None
        assert dp.max_value is None
        assert dp.step_value is None

    def test_non_mapping_field_yields_none(self) -> None:
        dp = DataPoint.from_field("weird", "not-a-dict")
        assert dp.value is None
        assert dp.settable is False

    def test_bool_is_not_min_value(self) -> None:
        """Booleans must not end up in the float bounds."""
        dp = DataPoint.from_field("onOffMode", {"value": "on", "minValue": True})
        assert dp.min_value is None


class TestIterDataPoints:
    """``iter_data_points`` skips metadata and non-wrapper keys."""

    def test_skips_meta_keys(self) -> None:
        raw = {
            "embeddedId": "x",
            "managementPointType": "gateway",
            "managementPointCategory": "secondary",
            "managementPointSubType": "foo",
            "name": {"value": "Gateway", "settable": False},
        }
        dps = list(iter_data_points(raw))
        names = [dp.name for dp in dps]
        assert names == ["name"]
        assert dps[0].embedded_id == "x"

    def test_skips_non_wrapper_fields(self) -> None:
        raw = {
            "embeddedId": "x",
            "managementPointType": "climateControl",
            # Not a value-wrapper (no "value" key at this level).
            "consumptionData": {"electrical": {}},
            "onOffMode": {"value": "on", "settable": True},
        }
        names = [dp.name for dp in iter_data_points(raw)]
        assert names == ["onOffMode"]


class TestManagementPointIntegration:
    """``ManagementPoint.iter_data_points`` bridges cleanly."""

    def test_altherma_climate_control_has_data_points(self) -> None:
        devices = _load("altherma.json")
        mps = [mp for dev in devices for mp in dev.get("managementPoints", []) if mp["managementPointType"] == "climateControl"]
        assert mps, "altherma fixture must expose a climateControl point"
        wrapper = management_point_from_json(mps[0])
        dps = list(wrapper.iter_data_points())
        names = {dp.name for dp in dps}
        # Known fields from altherma's climateControl payload.
        assert "onOffMode" in names
        assert "operationMode" in names
        # Every DataPoint on this MP should share the MP's embedded_id.
        assert all(dp.embedded_id == wrapper.embedded_id for dp in dps)


class TestAllFixturesIterate:
    """``iter_data_points`` survives every real fixture without raising."""

    @pytest.mark.parametrize("fixture_path", sorted(FIXTURES.glob("*.json")), ids=lambda p: p.name)
    def test_fixture(self, fixture_path: Path) -> None:
        devices = _load(fixture_path.name)
        for dev in devices:
            for mp_raw in dev.get("managementPoints", []):
                # No assertion on content — just that it walks cleanly.
                list(iter_data_points(mp_raw))
