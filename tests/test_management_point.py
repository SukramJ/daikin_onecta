"""Tests for the typed ``ManagementPoint`` wrappers (phase 7.4)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from custom_components.daikin_onecta.model.management_point import ClimateControlPoint
from custom_components.daikin_onecta.model.management_point import (
    DomesticHotWaterFlowThroughPoint,
)
from custom_components.daikin_onecta.model.management_point import (
    DomesticHotWaterTankPoint,
)
from custom_components.daikin_onecta.model.management_point import GatewayPoint
from custom_components.daikin_onecta.model.management_point import HardwareInfoPoint
from custom_components.daikin_onecta.model.management_point import ManagementPoint
from custom_components.daikin_onecta.model.management_point import (
    management_point_from_json,
)

FIXTURES = Path(__file__).parent / "fixtures"


def _load(name: str) -> list[dict]:
    with (FIXTURES / name).open(encoding="utf-8") as handle:
        data = json.load(handle)
    return data if isinstance(data, list) else [data]


def _management_points(fixture_name: str) -> list[dict]:
    devices = _load(fixture_name)
    return [mp for dev in devices for mp in dev.get("managementPoints", [])]


class TestFactoryDispatch:
    """``management_point_from_json`` returns the right subclass per type."""

    @pytest.mark.parametrize(
        ("mp_type", "expected"),
        [
            ("climateControl", ClimateControlPoint),
            ("domesticHotWaterTank", DomesticHotWaterTankPoint),
            ("domesticHotWaterFlowThrough", DomesticHotWaterFlowThroughPoint),
            ("gateway", GatewayPoint),
            ("indoorUnit", HardwareInfoPoint),
            ("indoorUnitHydro", HardwareInfoPoint),
            ("outdoorUnit", HardwareInfoPoint),
            ("userInterface", HardwareInfoPoint),
        ],
    )
    def test_dispatch_by_type(self, mp_type: str, expected: type[ManagementPoint]) -> None:
        mp = management_point_from_json({"managementPointType": mp_type, "embeddedId": "x"})
        assert isinstance(mp, expected)
        assert mp.embedded_id == "x"
        assert mp.management_point_type == mp_type

    def test_unknown_type_falls_back_to_base(self) -> None:
        mp = management_point_from_json({"managementPointType": "future-type", "embeddedId": "x"})
        assert type(mp) is ManagementPoint
        assert mp.management_point_type == "future-type"

    def test_missing_type_falls_back_to_base(self) -> None:
        mp = management_point_from_json({"embeddedId": "x"})
        assert type(mp) is ManagementPoint
        assert mp.management_point_type is None


class TestValueUnwrap:
    """Value-wrapper fields (``{value, settable, …}``) unwrap cleanly."""

    def test_name_returns_value_string(self) -> None:
        mp = management_point_from_json({"managementPointType": "gateway", "name": {"value": "Gateway"}})
        assert mp.name == "Gateway"

    def test_empty_name_returns_none(self) -> None:
        mp = management_point_from_json({"managementPointType": "gateway", "name": {"value": ""}})
        assert mp.name is None

    def test_missing_name_returns_none(self) -> None:
        mp = management_point_from_json({"managementPointType": "gateway"})
        assert mp.name is None

    def test_error_and_warning_flags(self) -> None:
        mp = management_point_from_json(
            {
                "managementPointType": "climateControl",
                "isInErrorState": {"value": True},
                "isInWarningState": {"value": False},
            }
        )
        assert mp.is_in_error_state is True
        assert mp.is_in_warning_state is False


class TestClimateControlPoint:
    """Accessors specific to ``climateControl``."""

    def test_real_fixture(self) -> None:
        mps = [mp for mp in _management_points("altherma.json") if mp["managementPointType"] == "climateControl"]
        assert mps, "altherma fixture must expose a climateControl point"
        point = management_point_from_json(mps[0])
        assert isinstance(point, ClimateControlPoint)
        assert point.on_off_mode in {"on", "off"}
        assert point.operation_mode is not None


class TestGatewayPoint:
    """Accessors specific to ``gateway``."""

    def test_real_fixture_exposes_model_and_mac(self) -> None:
        mps = [mp for mp in _management_points("altherma.json") if mp["managementPointType"] == "gateway"]
        assert mps, "altherma fixture must expose a gateway point"
        point = management_point_from_json(mps[0])
        assert isinstance(point, GatewayPoint)
        # Real Daikin fixtures always carry these on gateway points.
        assert point.model_info is not None
        assert point.mac_address is not None


class TestAllFixturesDispatch:
    """Every management point in every fixture survives the factory."""

    def test_every_mp_in_every_fixture(self) -> None:
        for fixture in FIXTURES.glob("*.json"):
            for mp in _management_points(fixture.name):
                wrapped = management_point_from_json(mp)
                # embedded_id and management_point_type must survive the wrap;
                # every real fixture has both.
                assert wrapped.embedded_id is not None, fixture.name
                assert wrapped.management_point_type is not None, fixture.name
                # The raw passthrough must stay identical.
                assert wrapped.raw is mp
