"""Support for the Daikin BRP069A62."""

from __future__ import annotations

import logging
from typing import Any
from typing import Final

from homeassistant.components.water_heater import STATE_HEAT_PUMP
from homeassistant.components.water_heater import STATE_PERFORMANCE
from homeassistant.components.water_heater import WaterHeaterEntity
from homeassistant.components.water_heater import WaterHeaterEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE
from homeassistant.const import STATE_OFF
from homeassistant.const import UnitOfTemperature
from homeassistant.core import callback
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import OnectaDataUpdateCoordinator
from .coordinator import OnectaRuntimeData
from .device import DaikinOnectaDevice

__all__: Final = ("DaikinWaterTank", "async_setup_entry")

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Daikin water tank entities."""
    onecta_data: OnectaRuntimeData = config_entry.runtime_data
    coordinator = onecta_data.coordinator
    for dev_id, device in onecta_data.devices.items():
        supported_management_point_types = {
            "domesticHotWaterTank",
            "domesticHotWaterFlowThrough",
        }
        for mp in device.iter_management_points():
            management_point = mp.raw
            management_point_type = management_point["managementPointType"]
            if management_point_type in supported_management_point_types:
                async_add_entities([DaikinWaterTank(device, coordinator, management_point_type, management_point["embeddedId"])])
            else:
                _LOGGER.info(
                    "Device '%s' '%s' is not a tank management point, ignoring as water heater",
                    device.name,
                    management_point_type,
                )


class DaikinWaterTank(CoordinatorEntity[OnectaDataUpdateCoordinator], WaterHeaterEntity):
    """Representation of a Daikin Water Tank."""

    def __init__(
        self,
        device: DaikinOnectaDevice,
        coordinator: OnectaDataUpdateCoordinator,
        management_point_type: str,
        embedded_id: str,
    ) -> None:
        """Initialize the Water device."""
        _LOGGER.info("Initializing Daiking Altherma HotWaterTank...")
        super().__init__(coordinator)
        self._device = device
        self._embedded_id = embedded_id
        self._attr_temperature_unit = UnitOfTemperature.CELSIUS
        self._attr_unique_id = f"{self._device.id}"
        self._management_point_type = management_point_type
        self._attr_device_info = {
            "identifiers": {(DOMAIN, self._device.id + self._management_point_type)},
            "name": self._device.name,
            "via_device": (DOMAIN, self._device.id),
        }
        self._attr_has_entity_name = True
        self._device.fill_device_info(self._attr_device_info, management_point_type)
        self.update_state()
        if self.supported_features & WaterHeaterEntityFeature.TARGET_TEMPERATURE:
            _LOGGER.debug("Device '%s' tank temperature is settable", device.name)

    def update_state(self) -> None:
        self._attr_supported_features = self.get_supported_features()
        self._attr_current_temperature = self.get_current_temperature()
        self._attr_target_temperature = self.get_target_temperature()
        min_temp = self.get_min_temp()
        if min_temp is not None:
            self._attr_min_temp = min_temp
        max_temp = self.get_max_temp()
        if max_temp is not None:
            self._attr_max_temp = max_temp
        self._attr_operation_list = self.get_operation_list()
        self._attr_current_operation = self.get_current_operation()

    @property
    def available(self) -> bool:
        return self._device.available

    async def async_added_to_hass(self) -> None:
        """Subscribe to the tank's management point so any DataPoint change refreshes us."""
        await super().async_added_to_hass()
        self.async_on_remove(self._device.add_management_point_listener(self._embedded_id, self._handle_model_update))
        self.async_on_remove(self._device.add_listener(self._handle_availability_update))

    @callback
    def _handle_model_update(self) -> None:
        self.update_state()
        self.async_write_ha_state()

    @callback
    def _handle_availability_update(self) -> None:
        self.async_write_ha_state()

    @property
    def hotwatertank_data(self) -> Any:
        # Find the management point for the hot water tank.
        # Runtime invariant: the water-heater entity is only created for
        # devices with a matching management point, so the search here cannot
        # return ``None``.
        hwd: dict[str, Any] | None = None
        for mp in self._device.iter_management_points():
            if mp.management_point_type == self._management_point_type:
                hwd = mp.raw
        return hwd

    @property
    def domestic_hotwater_temperature(self) -> Any:
        # Find the json dictionary for controlling the hot water temperature
        dht: dict[str, Any] | None = None
        tc = self.hotwatertank_data.get("temperatureControl")
        if tc is not None:
            temp_control = tc["value"]
            if temp_control:
                heating_mode = temp_control["operationModes"]["heating"]
                if heating_mode is not None:
                    dht = heating_mode["setpoints"]["domesticHotWaterTemperature"]
        return dht

    def get_supported_features(self) -> WaterHeaterEntityFeature:
        sf = WaterHeaterEntityFeature.OPERATION_MODE | WaterHeaterEntityFeature.ON_OFF
        # Only when we have a fixed setpointMode we can control the target
        # temperature of the tank
        dht = self.domestic_hotwater_temperature
        if dht:
            if dht["settable"] is True:
                sf |= WaterHeaterEntityFeature.TARGET_TEMPERATURE
        return sf

    def get_current_temperature(self) -> float | None:
        """Return tank temperature."""
        ret: float | None = None
        hwtd = self.hotwatertank_data
        # Some Altherma versions don't provide a current temperature, there is no sensoryData
        sensoryData = hwtd.get("sensoryData")
        if sensoryData is not None:
            ret = float(sensoryData["value"]["tankTemperature"]["value"])
            _LOGGER.debug(
                "Device '%s' hot water tank current_temperature '%s'",
                self._device.name,
                ret,
            )
        else:
            _LOGGER.debug("Device '%s' doesn't provide a current temperature", self._device.name)

        return ret

    def get_target_temperature(self) -> float | None:
        """Return the temperature we try to reach."""
        ret: float | None = None
        dht = self.domestic_hotwater_temperature
        if dht is not None:
            ret = float(dht["value"])
        _LOGGER.debug("Device '%s' hot water tank target_temperature '%s'", self._device.name, ret)
        return ret

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the optional device state attributes."""
        data: dict[str, Any] = {}
        dht = self.domestic_hotwater_temperature
        if dht is not None:
            data = {"target_temp_step": float(dht["stepValue"])}
        return data

    def get_min_temp(self) -> float | None:
        """Return the supported minimum value target temperature."""
        ret: float | None = None
        dht = self.domestic_hotwater_temperature
        if dht is not None:
            ret = float(dht["minValue"])
        _LOGGER.debug(
            "Device '%s' hot water tank minimum_temperature '%s'",
            self._device.name,
            ret,
        )
        return ret

    def get_max_temp(self) -> float | None:
        """Return the supported maximum value of target temperature."""
        ret: float | None = None
        dht = self.domestic_hotwater_temperature
        if dht is not None:
            ret = float(dht["maxValue"])
        _LOGGER.debug(
            "Device '%s' hot water tank maximum temperature '%s'",
            self._device.name,
            ret,
        )
        return ret

    async def async_set_tank_temperature(self, value: float) -> None:
        """Set new target temperature."""
        _LOGGER.debug("Device '%s' set tank temperature: %s", self._device.name, value)
        if self.current_operation == STATE_OFF:
            _LOGGER.debug(
                "Device '%s' set tank temperature ignored because device is off",
                self._device.name,
            )
            return None
        dht = self.domestic_hotwater_temperature
        if dht is not None:
            if dht["settable"] is False:
                _LOGGER.debug(
                    "Device '%s' set tank temperature ignored because tank temperature can't be set",
                    self._device.name,
                )
                return None

        int_value = int(value)
        if int_value != self._attr_target_temperature:
            res = await self._device.patch(
                self._device.id,
                self._embedded_id,
                "temperatureControl",
                "/operationModes/heating/setpoints/domesticHotWaterTemperature",
                int_value,
            )
            # When updating the value to the daikin cloud worked update our local cached version
            if res:
                self._attr_target_temperature = int_value
                self.async_write_ha_state()

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature."""
        # The service climate.set_temperature can set the hvac_mode too, see
        # https://www.home-assistant.io/integrations/climate/#service-climateset_temperature
        # se we first set the hvac_mode, if provided, then the temperature.
        await self.async_set_tank_temperature(kwargs[ATTR_TEMPERATURE])

    def get_current_operation(self) -> str:
        """Return current operation ie. heat, cool, idle."""
        state = STATE_OFF
        hwtd = self.hotwatertank_data
        onoff = hwtd.get("onOffMode")
        if onoff is not None and onoff["value"] == "on":
            state = STATE_HEAT_PUMP
            pwf = hwtd.get("powerfulMode")
            if pwf is not None and pwf["value"] == "on":
                state = STATE_PERFORMANCE
        _LOGGER.debug("Device '%s' hot water tank current mode '%s'", self._device.name, state)
        return state

    def get_operation_list(self) -> list[str]:
        """Return the list of available operation modes."""
        states = [STATE_OFF, STATE_HEAT_PUMP]
        hwtd = self.hotwatertank_data
        pwf = hwtd.get("powerfulMode")
        if pwf is not None:
            if pwf["settable"] is True:
                states += [STATE_PERFORMANCE]
        _LOGGER.debug("Device '%s' hot water tank supports modes %s", self._device.name, states)
        return states

    async def async_set_operation_mode(self, operation_mode: str) -> None:
        """Set new tank state."""
        _LOGGER.debug("Set tank operation mode: %s", operation_mode)
        result = True

        # First determine the new settings for onOffMode/powerfulMode, we need these to set them to Daikin
        # and update our local cached version when succeeded
        on_off_mode = ""
        powerful_mode = ""
        if operation_mode == STATE_OFF:
            on_off_mode = "off"
        if operation_mode == STATE_PERFORMANCE:
            powerful_mode = "on"
            if self.current_operation == STATE_OFF:
                on_off_mode = "on"
        if operation_mode == STATE_HEAT_PUMP:
            if self.current_operation == STATE_PERFORMANCE:
                powerful_mode = "off"
            if self.current_operation == STATE_OFF:
                on_off_mode = "on"

        # Only set the on/off to Daikin when we need to change it
        if on_off_mode != "":
            result &= bool(await self._device.patch(self._device.id, self._embedded_id, "onOffMode", "", on_off_mode))
            if result is True:
                hwtd = self.hotwatertank_data
                hwtd["onOffMode"]["value"] = on_off_mode

        # Only set powerfulMode when it is set and supported by the device
        operation_list = self.operation_list or []
        if (powerful_mode != "") and (STATE_PERFORMANCE in operation_list):
            result &= bool(
                await self._device.patch(
                    self._device.id,
                    self._embedded_id,
                    "powerfulMode",
                    "",
                    powerful_mode,
                )
            )
            if result is True:
                hwtd = self.hotwatertank_data
                pwf = hwtd.get("powerfulMode")
                if pwf is not None:
                    if pwf["settable"] is True:
                        pwf["value"] = powerful_mode

        if result is False:
            _LOGGER.warning("Device '%s' invalid tank state: %s", self._device.name, operation_mode)
        else:
            # Update local cached version
            self._attr_current_operation = operation_mode
            self._attr_operation_list = self.get_operation_list()
            self.async_write_ha_state()

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn water heater on."""
        _LOGGER.debug("Device '%s' request to turn on", self._device.name)
        if self.current_operation == STATE_OFF:
            result = bool(await self._device.patch(self._device.id, self._embedded_id, "onOffMode", "", "on"))
            if result is False:
                _LOGGER.error("Device '%s' problem setting onOffMode to on", self._device.name)
            else:
                hwtd = self.hotwatertank_data
                hwtd["onOffMode"]["value"] = "on"
                self._attr_current_operation = self.get_current_operation()
                self._attr_operation_list = self.get_operation_list()
                self.async_write_ha_state()
        else:
            _LOGGER.debug(
                "Device '%s' request to turn on ignored because device is already on",
                self._device.name,
            )

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn water heater off."""
        _LOGGER.debug("Device '%s' request to turn off", self._device.name)
        if self.current_operation != STATE_OFF:
            result = bool(await self._device.patch(self._device.id, self._embedded_id, "onOffMode", "", "off"))
            if result is False:
                _LOGGER.error("Device '%s' problem setting onOffMode to off", self._device.name)
            else:
                hwtd = self.hotwatertank_data
                hwtd["onOffMode"]["value"] = "off"
                self._attr_current_operation = self.get_current_operation()
                self._attr_operation_list = self.get_operation_list()
                self.async_write_ha_state()
        else:
            _LOGGER.debug(
                "Device '%s' request to turn off ignored because device is already off",
                self._device.name,
            )
