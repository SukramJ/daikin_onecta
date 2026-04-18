"""A Daikin Onecta device instance, populated from the cloud JSON.

Canonical home of ``DaikinOnectaDevice`` — moved from the top-level
``device.py`` as step 7.3 of the domain-model refactor (see
``docs/adr/0003-domain-model-package-layout.md``). JSON walks currently
live here; they move to ``management_point.py`` in step 7.4.
"""

from __future__ import annotations

import contextlib
import json
import logging
from collections.abc import Callable
from collections.abc import Iterator
from typing import Any
from typing import Final

from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC
from homeassistant.helpers.device_registry import DeviceInfo

from ..client.api import DaikinApi
from ..client.api import RequestResult
from ..const import DOMAIN
from ..exceptions import DaikinApiError
from .data_point import DataPoint
from .management_point import ManagementPoint
from .management_point import management_point_from_json

__all__: Final = ("DaikinOnectaDevice", "DataPointKey", "Listener")

_LOGGER = logging.getLogger(__name__)

# Listener callable — invoked with no args; subscribers capture whatever
# state they need via closure. Async/sync both acceptable at the call
# site since we only call synchronously (HA entities use @callback).
Listener = Callable[[], None]

# Identifies a single DataPoint within a device: (embedded_id, field name).
DataPointKey = tuple[str, str]


class DaikinOnectaDevice:
    """Class to represent and control one Daikin Onecta Device."""

    def __init__(self, jsonData: dict[str, Any], apiInstance: DaikinApi) -> None:
        """Initialize a new Daikin Onecta Device."""
        self.api = apiInstance
        # get name from climateControl
        self.daikin_data: dict[str, Any] = jsonData
        self.id: str = self.daikin_data["id"]
        self.name: str = self.daikin_data["deviceModel"]

        management_points = self.daikin_data.get("managementPoints", [])
        for management_point in management_points:
            if management_point["managementPointType"] == "climateControl":
                name = management_point["name"]["value"]
                if name:
                    self.name = name

        # Listener registry — populated by platforms in async_added_to_hass.
        # Cleared listeners are not an error, so removal uses contextlib.suppress.
        self._device_listeners: list[Listener] = []
        self._mp_listeners: dict[str, list[Listener]] = {}
        self._dp_listeners: dict[DataPointKey, list[Listener]] = {}

        _LOGGER.info("Initialized Daikin Onecta Device '%s' (id %s)", self.name, self.id)

    @property
    def available(self) -> bool:
        result = False
        icu = self.daikin_data.get("isCloudConnectionUp")
        if icu is not None:
            result = icu["value"]
        return result

    def fill_device_info(self, device_info: Any, management_point_type: str) -> None:
        manufacturer = {"manufacturer": "Daikin"}
        device_info.update(**manufacturer)
        management_points = self.daikin_data.get("managementPoints", [])
        for management_point in management_points:
            if management_point_type == management_point["managementPointType"]:
                mp = management_point.get("eepromVersion")
                if mp is not None:
                    device_info["sw_version"] = mp["value"]
                mp = management_point.get("modelInfo")
                if mp is not None:
                    device_info["model"] = mp["value"]
                mp = management_point.get("firmwareVersion")
                if mp is not None:
                    device_info["sw_version"] = mp["value"]
                mp = management_point.get("serialNumber")
                if mp is not None:
                    device_info["serial_number"] = mp["value"]
                mp = management_point.get("softwareVersion")
                if mp is not None:
                    device_info["sw_version"] = mp["value"]

    def device_info(self) -> DeviceInfo:
        """Return a device description for device registry."""
        mac_add = ""
        devicemodel = self.daikin_data.get("deviceModel")
        supported_management_point_types = {"gateway"}
        management_points = self.daikin_data.get("managementPoints", [])
        for management_point in management_points:
            management_point_type = management_point["managementPointType"]
            if management_point_type in supported_management_point_types:
                mp = management_point.get("macAddress")
                if mp is not None:
                    mac_add = mp["value"]

        info = DeviceInfo(
            identifiers={
                # Serial numbers are unique identifiers within a specific domain
                (DOMAIN, self.id)
            },
            connections={(CONNECTION_NETWORK_MAC, mac_add)},
            name=self.name,
            model_id=devicemodel,
        )

        self.fill_device_info(info, "gateway")

        return info

    def merge_json(self, a: dict[str, Any], b: dict[str, Any], path: list[str] | None = None) -> dict[str, Any]:
        """Merge ``b`` into ``a`` in place; safe against readers of ``daikin_data``."""
        if path is None:
            path = []
        for key in b:
            if key in a:
                if isinstance(a[key], dict) and isinstance(b[key], dict):
                    self.merge_json(a[key], b[key], [*path, str(key)])
                else:
                    a[key] = b[key]
            else:
                a[key] = b[key]
        return a

    def setJsonData(self, desc: dict[str, Any]) -> None:
        """Merge a device description and fire listeners for changed fields.

        The method takes a value-level snapshot before and after the merge
        and emits listeners only for DataPoints whose ``value`` actually
        changed. Device-level listeners also fire when ``available``
        toggles (``isCloudConnectionUp`` lives outside the management
        points, so the value-snapshot alone would not catch it).
        """
        before_values = self._snapshot_data_point_values()
        before_available = self.available

        self.merge_json(self.daikin_data, desc)

        after_values = self._snapshot_data_point_values()
        after_available = self.available

        changed_keys: set[DataPointKey] = set()
        for key in before_values.keys() | after_values.keys():
            if before_values.get(key) != after_values.get(key):
                changed_keys.add(key)

        _LOGGER.info(
            "Device '%s' received new data from the Daikin cloud, isCloudConnectionUp '%s', %d data point(s) changed",
            self.name,
            after_available,
            len(changed_keys),
        )

        self._emit_changes(changed_keys, available_changed=before_available != after_available)

    def _snapshot_data_point_values(self) -> dict[DataPointKey, Any]:
        """Flatten current DataPoint values keyed by ``(embedded_id, name)``."""
        snapshot: dict[DataPointKey, Any] = {}
        for mp in self.iter_management_points():
            if mp.embedded_id is None:
                continue
            for dp in mp.iter_data_points():
                snapshot[(mp.embedded_id, dp.name)] = dp.value
        return snapshot

    def _emit_changes(self, changed_keys: set[DataPointKey], *, available_changed: bool) -> None:
        """Dispatch listeners for the given changed DataPoints.

        Called from ``setJsonData``. Listeners run synchronously in the
        registration order; exceptions propagate so entity bugs surface
        loudly rather than silently corrupting state.
        """
        changed_mps: set[str] = {eid for eid, _ in changed_keys}

        for key in changed_keys:
            for callback in list(self._dp_listeners.get(key, ())):
                callback()

        for embedded_id in changed_mps:
            for callback in list(self._mp_listeners.get(embedded_id, ())):
                callback()

        if changed_keys or available_changed:
            for callback in list(self._device_listeners):
                callback()

    def add_listener(self, callback: Listener) -> Callable[[], None]:
        """Register a device-wide listener; returns an unsubscribe callable.

        Fires once per ``setJsonData`` call whenever *any* DataPoint
        changed or ``available`` toggled.
        """
        self._device_listeners.append(callback)

        def _unsubscribe() -> None:
            with contextlib.suppress(ValueError):
                self._device_listeners.remove(callback)

        return _unsubscribe

    def add_management_point_listener(self, embedded_id: str, callback: Listener) -> Callable[[], None]:
        """Register a listener scoped to one management point."""
        self._mp_listeners.setdefault(embedded_id, []).append(callback)

        def _unsubscribe() -> None:
            listeners = self._mp_listeners.get(embedded_id)
            if listeners is None:
                return
            with contextlib.suppress(ValueError):
                listeners.remove(callback)

        return _unsubscribe

    def add_data_point_listener(self, embedded_id: str, name: str, callback: Listener) -> Callable[[], None]:
        """Register a listener scoped to one DataPoint (embedded_id + field name)."""
        key: DataPointKey = (embedded_id, name)
        self._dp_listeners.setdefault(key, []).append(callback)

        def _unsubscribe() -> None:
            listeners = self._dp_listeners.get(key)
            if listeners is None:
                return
            with contextlib.suppress(ValueError):
                listeners.remove(callback)

        return _unsubscribe

    def iter_management_points(self) -> Iterator[ManagementPoint]:
        """Yield each ``managementPoints[*]`` as a typed wrapper.

        Platform code should prefer this over walking ``daikin_data``
        directly — the wrappers hide the ``{value, settable, …}`` plumbing
        and dispatch to per-type subclasses.
        """
        for raw in self.daikin_data.get("managementPoints", []):
            if isinstance(raw, dict):
                yield management_point_from_json(raw)

    def find_management_point(self, embedded_id: str) -> ManagementPoint | None:
        """Return the management point with ``embedded_id``, or ``None``."""
        for mp in self.iter_management_points():
            if mp.embedded_id == embedded_id:
                return mp
        return None

    def iter_data_points(self) -> Iterator[DataPoint]:
        """Yield every ``DataPoint`` across all management points on this device."""
        for mp in self.iter_management_points():
            yield from mp.iter_data_points()

    async def patch(self, id: str, embeddedId: str, dataPoint: str, dataPointPath: str, value: Any) -> RequestResult:
        setPath = "/v1/gateway-devices/" + id + "/management-points/" + embeddedId + "/characteristics/" + dataPoint
        setBody: dict[str, Any] = {"value": value}
        if dataPointPath:
            setBody["path"] = dataPointPath
        setOptions = json.dumps(setBody)

        _LOGGER.info("Path: %s , options: %s", setPath, setOptions)

        # Write path: 5xx and unexpected 4xx surface here as DaikinApiError.
        # For the platform these mean "write failed"; we catch, log, and return
        # False so the entity keeps its current state.
        try:
            res = await self.api.doBearerRequest("PATCH", setPath, setOptions)
        except DaikinApiError as err:
            _LOGGER.warning("PATCH %s failed: %s", setPath, err)
            return False

        _LOGGER.info("Result: %s", res)

        return res

    async def post(self, id: str, embeddedId: str, dataPoint: str, value: Any) -> RequestResult:
        setPath = "/v1/gateway-devices/" + id + "/management-points/" + embeddedId + "/" + dataPoint
        setOptions = json.dumps(value)

        _LOGGER.info("Path: %s , options: %s", setPath, setOptions)

        try:
            res = await self.api.doBearerRequest("POST", setPath, setOptions)
        except DaikinApiError as err:
            _LOGGER.warning("POST %s failed: %s", setPath, err)
            return False

        _LOGGER.info("Result: %s", res)

        return res

    async def put(self, id: str, embeddedId: str, dataPoint: str, value: Any) -> RequestResult:
        setPath = "/v1/gateway-devices/" + id + "/management-points/" + embeddedId + "/" + dataPoint
        setOptions = json.dumps(value)

        _LOGGER.info("Path: %s , options: %s", setPath, setOptions)

        try:
            res = await self.api.doBearerRequest("PUT", setPath, setOptions)
        except DaikinApiError as err:
            _LOGGER.warning("PUT %s failed: %s", setPath, err)
            return False

        _LOGGER.info("Result: %s", res)

        return res
