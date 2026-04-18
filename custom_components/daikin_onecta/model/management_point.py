"""Typed ManagementPoint classes.

A ManagementPoint is one element of the Daikin cloud's
``device["managementPoints"]`` list. The cloud uses the same wrapper
structure for everything: ``{"managementPointType": "...", "embeddedId":
"...", <fields>...}``. Most fields follow the ``{value, settable, ...}``
wrapper pattern.

This module provides a small class hierarchy that wraps a single raw
management-point dict and exposes typed accessors for the common and
per-type fields. Platforms will migrate from the raw JSON walks in steps
7.6 – 7.8; for now the classes live alongside the existing code.

The ``raw`` attribute is deliberately kept available so partially
migrated callers can reach into unmapped fields without duplicating the
wrapper logic.
"""

from __future__ import annotations

from collections.abc import Iterator
from collections.abc import Mapping
from typing import Any
from typing import Final
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .data_point import DataPoint

__all__: Final = (
    "ClimateControlPoint",
    "DomesticHotWaterFlowThroughPoint",
    "DomesticHotWaterTankPoint",
    "GatewayPoint",
    "HardwareInfoPoint",
    "IndoorUnitHydroPoint",
    "IndoorUnitPoint",
    "ManagementPoint",
    "OutdoorUnitPoint",
    "UserInterfacePoint",
    "management_point_from_json",
)


def _unwrap(field: Any) -> Any:
    """Return ``field["value"]`` if it is a value-wrapper dict, else ``None``."""
    if isinstance(field, Mapping) and "value" in field:
        return field["value"]
    return None


class ManagementPoint:
    """Generic wrapper around one ``managementPoints[*]`` entry.

    Subclasses specialise the accessors for a specific
    ``managementPointType``. Unknown types fall back to this base class,
    which still provides the common accessors.
    """

    def __init__(self, raw: dict[str, Any]) -> None:
        """Wrap a single raw management-point dict."""
        self.raw: dict[str, Any] = raw

    @property
    def embedded_id(self) -> str | None:
        """Stable identifier within its parent device, or ``None`` if absent."""
        value = self.raw.get("embeddedId")
        return value if isinstance(value, str) else None

    @property
    def management_point_type(self) -> str | None:
        """The ``managementPointType`` string, or ``None`` if absent."""
        value = self.raw.get("managementPointType")
        return value if isinstance(value, str) else None

    @property
    def management_point_category(self) -> str | None:
        """The ``managementPointCategory`` string, or ``None`` if absent."""
        value = self.raw.get("managementPointCategory")
        return value if isinstance(value, str) else None

    @property
    def name(self) -> str | None:
        """User-visible ``name.value``, or ``None`` if unset/empty."""
        value = _unwrap(self.raw.get("name"))
        return value if isinstance(value, str) and value else None

    @property
    def error_code(self) -> str | None:
        """Current ``errorCode.value``, or ``None`` if unset."""
        value = _unwrap(self.raw.get("errorCode"))
        return value if isinstance(value, str) else None

    @property
    def is_in_error_state(self) -> bool:
        """Whether the cloud flagged this management point as in error."""
        return bool(_unwrap(self.raw.get("isInErrorState")))

    @property
    def is_in_warning_state(self) -> bool:
        """Whether the cloud flagged this management point as in warning."""
        return bool(_unwrap(self.raw.get("isInWarningState")))

    def iter_data_points(self) -> Iterator[DataPoint]:
        """Yield every top-level value-field as a typed ``DataPoint``.

        Deferred import to keep the module import graph simple; the two
        classes form a cycle at the *type* level but not at import time.
        """
        from .data_point import iter_data_points  # pylint: disable=import-outside-toplevel

        yield from iter_data_points(self.raw, embedded_id=self.embedded_id)


class _OperatingPoint(ManagementPoint):
    """Shared base for operational management points (climate, hot water).

    These all expose ``onOffMode``, ``operationMode`` and
    ``temperatureControl``; subclasses add type-specific extras.
    """

    @property
    def on_off_mode(self) -> str | None:
        """Current ``onOffMode.value`` (``"on"``/``"off"``), or ``None``."""
        value = _unwrap(self.raw.get("onOffMode"))
        return value if isinstance(value, str) else None

    @property
    def operation_mode(self) -> str | None:
        """Current ``operationMode.value``, or ``None`` if unset."""
        value = _unwrap(self.raw.get("operationMode"))
        return value if isinstance(value, str) else None

    @property
    def temperature_control(self) -> Mapping[str, Any] | None:
        """Raw ``temperatureControl`` sub-tree, or ``None`` if absent."""
        value = self.raw.get("temperatureControl")
        return value if isinstance(value, Mapping) else None


class ClimateControlPoint(_OperatingPoint):
    """``managementPointType == "climateControl"``."""

    @property
    def setpoint_mode(self) -> str | None:
        """Current ``setpointMode.value`` (``"fixed"``/``"weatherDependent"``/…)."""
        value = _unwrap(self.raw.get("setpointMode"))
        return value if isinstance(value, str) else None

    @property
    def control_mode(self) -> str | None:
        """Current ``controlMode.value`` or ``None`` if unset."""
        value = _unwrap(self.raw.get("controlMode"))
        return value if isinstance(value, str) else None

    @property
    def is_holiday_mode_active(self) -> bool:
        """Whether the climate control is currently in holiday mode."""
        return bool(_unwrap(self.raw.get("isHolidayModeActive")))

    @property
    def is_powerful_mode_active(self) -> bool:
        """Whether the climate control is currently in powerful mode."""
        return bool(_unwrap(self.raw.get("isPowerfulModeActive")))


class DomesticHotWaterTankPoint(_OperatingPoint):
    """``managementPointType == "domesticHotWaterTank"``."""

    @property
    def setpoint_mode(self) -> str | None:
        """Current ``setpointMode.value`` (e.g. ``"fixed"``/``"weatherDependent"``)."""
        value = _unwrap(self.raw.get("setpointMode"))
        return value if isinstance(value, str) else None

    @property
    def powerful_mode(self) -> str | None:
        """Current ``powerfulMode.value`` (``"on"``/``"off"``), or ``None``."""
        value = _unwrap(self.raw.get("powerfulMode"))
        return value if isinstance(value, str) else None

    @property
    def is_powerful_mode_active(self) -> bool:
        """Whether the tank is currently in powerful mode."""
        return bool(_unwrap(self.raw.get("isPowerfulModeActive")))


class DomesticHotWaterFlowThroughPoint(_OperatingPoint):
    """``managementPointType == "domesticHotWaterFlowThrough"``.

    Flow-through hot water has no setpoint/powerful-mode concept — just
    the common on/off + operation-mode + temperatureControl.
    """


class GatewayPoint(ManagementPoint):
    """``managementPointType == "gateway"``."""

    @property
    def mac_address(self) -> str | None:
        """MAC address (``macAddress.value``), or ``None``."""
        value = _unwrap(self.raw.get("macAddress"))
        return value if isinstance(value, str) else None

    @property
    def ip_address(self) -> str | None:
        """IP address, or ``None``."""
        value = _unwrap(self.raw.get("ipAddress"))
        return value if isinstance(value, str) else None

    @property
    def model_info(self) -> str | None:
        """Gateway model identifier, or ``None``."""
        value = _unwrap(self.raw.get("modelInfo"))
        return value if isinstance(value, str) else None

    @property
    def firmware_version(self) -> str | None:
        """Gateway firmware version string, or ``None``."""
        value = _unwrap(self.raw.get("firmwareVersion"))
        return value if isinstance(value, str) else None

    @property
    def software_version(self) -> str | None:
        """Gateway software version string, or ``None``."""
        value = _unwrap(self.raw.get("softwareVersion"))
        return value if isinstance(value, str) else None

    @property
    def serial_number(self) -> str | None:
        """Gateway serial number, or ``None``."""
        value = _unwrap(self.raw.get("serialNumber"))
        return value if isinstance(value, str) else None


class HardwareInfoPoint(ManagementPoint):
    """Base for pure hardware descriptors (no control surface).

    Covers ``indoorUnit``, ``indoorUnitHydro``, ``outdoorUnit`` and
    ``userInterface``. They share model/software identifiers but differ
    in which subset of them the cloud actually populates.
    """

    @property
    def model_info(self) -> str | None:
        """Hardware model identifier, or ``None``."""
        value = _unwrap(self.raw.get("modelInfo"))
        return value if isinstance(value, str) else None

    @property
    def software_version(self) -> str | None:
        """Software version string, or ``None``."""
        value = _unwrap(self.raw.get("softwareVersion"))
        return value if isinstance(value, str) else None

    @property
    def eeprom_version(self) -> str | None:
        """EEPROM version (indoor units only), or ``None``."""
        value = _unwrap(self.raw.get("eepromVersion"))
        return value if isinstance(value, str) else None

    @property
    def firmware_version(self) -> str | None:
        """Firmware version (userInterface exposes this), or ``None``."""
        value = _unwrap(self.raw.get("firmwareVersion"))
        return value if isinstance(value, str) else None


class IndoorUnitPoint(HardwareInfoPoint):
    """``managementPointType == "indoorUnit"``."""


class IndoorUnitHydroPoint(HardwareInfoPoint):
    """``managementPointType == "indoorUnitHydro"``."""


class OutdoorUnitPoint(HardwareInfoPoint):
    """``managementPointType == "outdoorUnit"``."""


class UserInterfacePoint(HardwareInfoPoint):
    """``managementPointType == "userInterface"``."""


_REGISTRY: Final[Mapping[str, type[ManagementPoint]]] = {
    "climateControl": ClimateControlPoint,
    "domesticHotWaterFlowThrough": DomesticHotWaterFlowThroughPoint,
    "domesticHotWaterTank": DomesticHotWaterTankPoint,
    "gateway": GatewayPoint,
    "indoorUnit": IndoorUnitPoint,
    "indoorUnitHydro": IndoorUnitHydroPoint,
    "outdoorUnit": OutdoorUnitPoint,
    "userInterface": UserInterfacePoint,
}


def management_point_from_json(raw: dict[str, Any]) -> ManagementPoint:
    """Build the correct ``ManagementPoint`` subclass for a raw entry.

    Unknown ``managementPointType`` values fall back to the generic
    ``ManagementPoint`` base class — no exception. The cloud adds fields
    more often than entirely new types, and the base class is still
    useful (common accessors plus ``raw`` passthrough).
    """
    mp_type = raw.get("managementPointType")
    cls: type[ManagementPoint] = _REGISTRY.get(mp_type, ManagementPoint) if isinstance(mp_type, str) else ManagementPoint
    return cls(raw)
