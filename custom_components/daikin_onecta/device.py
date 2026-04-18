"""A Daikin Onecta device instance, populated from the cloud JSON."""

from __future__ import annotations

import json
import logging
from typing import Any
from typing import Final

from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC
from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN
from .daikin_api import DaikinApi
from .daikin_api import RequestResult
from .exceptions import DaikinApiError

__all__: Final = ("DaikinOnectaDevice",)

_LOGGER = logging.getLogger(__name__)


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
        """Set a device description and parse/traverse data structure."""
        self.merge_json(self.daikin_data, desc)
        _LOGGER.info("Device '%s' received new data from the Daikin cloud, isCloudConnectionUp '%s'", self.name, self.available)

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
