"""Support for the Daikin HVAC."""

from __future__ import annotations

import logging
import re
from datetime import date
from datetime import timedelta
from typing import Any
from typing import Final

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate import PLATFORM_SCHEMA
from homeassistant.components.climate.const import ATTR_HVAC_MODE
from homeassistant.components.climate.const import ClimateEntityFeature
from homeassistant.components.climate.const import HVACMode
from homeassistant.components.climate.const import PRESET_AWAY
from homeassistant.components.climate.const import PRESET_BOOST
from homeassistant.components.climate.const import PRESET_COMFORT
from homeassistant.components.climate.const import PRESET_ECO
from homeassistant.components.climate.const import PRESET_NONE
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE
from homeassistant.const import CONF_HOST
from homeassistant.const import CONF_NAME
from homeassistant.const import UnitOfTemperature
from homeassistant.core import callback
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .const import FANMODE_FIXED
from .const import TRANSLATION_KEY
from .const import VALUE_SENSOR_MAPPING
from .coordinator import OnectaDataUpdateCoordinator
from .coordinator import OnectaRuntimeData
from .device import DaikinOnectaDevice

__all__: Final = ("DaikinClimate", "async_setup_entry")

_LOGGER = logging.getLogger(__name__)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({vol.Required(CONF_HOST): cv.string, vol.Optional(CONF_NAME): cv.string})

PRESET_MODES = {PRESET_COMFORT, PRESET_ECO, PRESET_AWAY, PRESET_BOOST}

HA_HVAC_TO_DAIKIN = {
    HVACMode.FAN_ONLY: "fanOnly",
    HVACMode.DRY: "dry",
    HVACMode.COOL: "cooling",
    HVACMode.HEAT: "heating",
    HVACMode.HEAT_COOL: "auto",
    HVACMode.OFF: "off",
}

DAIKIN_HVAC_TO_HA = {
    "fanOnly": HVACMode.FAN_ONLY,
    "dry": HVACMode.DRY,
    "cooling": HVACMode.COOL,
    "heating": HVACMode.HEAT,
    "heatingDay": HVACMode.HEAT,
    "heatingNight": HVACMode.HEAT,
    "auto": HVACMode.HEAT_COOL,
    "off": HVACMode.OFF,
    "humidification": HVACMode.DRY,
}

HA_PRESET_TO_DAIKIN = {
    PRESET_AWAY: "holidayMode",
    PRESET_NONE: "off",
    PRESET_BOOST: "powerfulMode",
    PRESET_COMFORT: "comfortMode",
    PRESET_ECO: "econoMode",
}


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Daikin climate based on config_entry."""
    onecta_data: OnectaRuntimeData = config_entry.runtime_data
    coordinator = onecta_data.coordinator
    for dev_id, device in onecta_data.devices.items():
        modes = []
        device_model = device.daikin_data["deviceModel"]
        supported_management_point_types = {"climateControl"}
        embedded_id = ""
        for mp in device.iter_management_points():
            management_point = mp.raw
            management_point_type = mp.management_point_type
            if management_point_type in supported_management_point_types:
                embedded_id = mp.embedded_id or ""
                # Check if we have a temperatureControl
                temperatureControl = management_point.get("temperatureControl")
                if temperatureControl is not None:
                    for operationmode in temperatureControl["value"]["operationModes"]:
                        # for modes in operationmode["setpoints"]:
                        for c in temperatureControl["value"]["operationModes"][operationmode]["setpoints"]:
                            modes.append(c)
        # Remove duplicates
        modes = list(dict.fromkeys(modes))
        _LOGGER.info("Climate: Device '%s' has modes %s", device_model, modes)
        for mode in modes:
            async_add_entities(
                [DaikinClimate(device, mode, coordinator, embedded_id)],
                update_before_add=False,
            )


class DaikinClimate(CoordinatorEntity[OnectaDataUpdateCoordinator], ClimateEntity):
    """Representation of a Daikin HVAC."""

    _enable_turn_on_off_backwards_compatibility = False  # Remove with HA 2025.1

    # Setpoint is the setpoint string under
    # temperatureControl/value/operationsModes/mode/setpoints, for example roomTemperature/leavingWaterOffset
    def __init__(
        self,
        device: DaikinOnectaDevice,
        setpoint: str,
        coordinator: OnectaDataUpdateCoordinator,
        embedded_id: str,
    ) -> None:
        """Initialize the climate device."""
        super().__init__(coordinator)
        _LOGGER.info(
            "Device '%s' initializing Daikin Climate for controlling %s...",
            device.name,
            setpoint,
        )
        self._device = device
        self._embedded_id = embedded_id
        self._setpoint = setpoint
        self._attr_temperature_unit = UnitOfTemperature.CELSIUS
        self._attr_unique_id = f"{self._device.id}_{self._setpoint}"
        self._attr_device_info = {"identifiers": {(DOMAIN, self._device.id)}, "name": self._device.name}
        self._attr_has_entity_name = True
        self._device.fill_device_info(self._attr_device_info, "gateway")
        sensor_settings = VALUE_SENSOR_MAPPING[setpoint]
        self._attr_translation_key = sensor_settings[TRANSLATION_KEY]
        self.update_state()

    def update_state(self) -> None:
        self._attr_supported_features = self.get_supported_features()
        self._attr_current_temperature = self.get_current_temperature()
        self._attr_max_temp = self.get_max_temp()
        self._attr_min_temp = self.get_min_temp()
        self._attr_target_temperature_step = self.get_target_temperature_step()
        self._attr_target_temperature = self.get_target_temperature()
        self._attr_hvac_modes = self.get_hvac_modes()
        self._attr_swing_modes = self.get_swing_modes()
        self._attr_swing_horizontal_modes = self.get_swing_horizontal_modes()
        self._attr_preset_modes = self.get_preset_modes()
        self._attr_fan_modes = self.get_fan_modes()
        self._attr_hvac_mode = self.get_hvac_mode()
        self._attr_swing_mode = self.get_swing_mode()
        self._attr_swing_horizontal_mode = self.get_swing_horizontal_mode()
        self._attr_preset_mode = self.get_preset_mode()
        self._attr_fan_mode = self.get_fan_mode()

    async def async_added_to_hass(self) -> None:
        """Subscribe to the climate control management point.

        Climate entities depend on many fields (``onOffMode``,
        ``operationMode``, ``temperatureControl``, fan, swing, preset),
        so listening at management-point granularity is cheaper than one
        subscription per field.
        """
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
    def available(self) -> bool:
        return bool(self._device.available)

    def climate_control(self) -> dict[str, Any] | None:
        cc: dict[str, Any] | None = None
        for mp in self._device.iter_management_points():
            if mp.management_point_type == "climateControl":
                cc = mp.raw
        return cc

    def operation_mode(self) -> dict[str, Any] | None:
        om: dict[str, Any] | None = None
        cc = self.climate_control()
        if cc is not None:
            om = cc.get("operationMode")
        return om

    def setpoint(self) -> dict[str, Any] | None:
        setpoint: dict[str, Any] | None = None
        cc = self.climate_control()
        if cc is not None:
            # Check if we have a temperatureControl
            temperature_control = cc.get("temperatureControl")
            if temperature_control is not None:
                operation_mode_data = cc.get("operationMode")
                if operation_mode_data is not None:
                    operation_mode = operation_mode_data.get("value")
                    # For not all operationModes there is a temperatureControl setpoint available
                    oo = temperature_control["value"]["operationModes"].get(operation_mode)
                    if oo is not None:
                        setpoint = oo["setpoints"].get(self._setpoint)
                    _LOGGER.info(
                        "Device '%s' %s operation mode %s has setpoint %s",
                        self._device.name,
                        self._setpoint,
                        operation_mode,
                        setpoint,
                    )
        return setpoint

    def sensory_data(self, setpoint: str) -> dict[str, Any] | None:
        sensoryData: dict[str, Any] | None = None
        for mp in self._device.iter_management_points():
            if mp.management_point_type == "climateControl":
                # Check if we have a sensoryData
                sensoryData = mp.raw.get("sensoryData")
                _LOGGER.info("Climate: Device sensoryData %s", sensoryData)
                if sensoryData is not None:
                    value = sensoryData.get("value")
                    if value is not None:
                        sensoryData = value.get(setpoint)
                        _LOGGER.info(
                            "Device '%s' %s sensoryData %s",
                            self._device.name,
                            setpoint,
                            sensoryData,
                        )
        return sensoryData

    def get_supported_features(self) -> ClimateEntityFeature:
        supported_features = ClimateEntityFeature(0)
        if hasattr(ClimateEntityFeature, "TURN_OFF"):
            supported_features = ClimateEntityFeature.TURN_OFF | ClimateEntityFeature.TURN_ON
        setpointdict = self.setpoint()
        if setpointdict is not None and setpointdict["settable"] is True:
            supported_features |= ClimateEntityFeature.TARGET_TEMPERATURE
        if len(self.get_preset_modes()) > 1:
            supported_features |= ClimateEntityFeature.PRESET_MODE
        cc = self.climate_control()
        if cc is not None:
            fanControl = cc.get("fanControl")
            if fanControl is not None:
                operation_mode_data = cc.get("operationMode")
                if operation_mode_data is not None:
                    operationmode = operation_mode_data.get("value")
                    operationmodedict = fanControl["value"]["operationModes"].get(operationmode)
                    if operationmodedict is not None:
                        if operationmodedict.get("fanSpeed") is not None:
                            supported_features |= ClimateEntityFeature.FAN_MODE
                        fan_direction = operationmodedict.get("fanDirection")
                        if fan_direction is not None:
                            if fan_direction.get("vertical") is not None:
                                supported_features |= ClimateEntityFeature.SWING_MODE
                            if fan_direction.get("horizontal") is not None:
                                supported_features |= ClimateEntityFeature.SWING_HORIZONTAL_MODE

            _LOGGER.info("Device '%s' supports features %s", self._device.name, supported_features)

        return supported_features

    @property
    def name(self) -> str:
        myname = self._setpoint[0].upper() + self._setpoint[1:]
        readable = re.findall("[A-Z][^A-Z]*", myname)
        return f"{' '.join(readable)}"

    def get_current_temperature(self) -> float | None:
        current_temp: float | None = None
        sensory_data = self.sensory_data(self._setpoint)
        # Check if there is a sensoryData which is for the same setpoint, if so, return that
        if sensory_data is not None:
            current_temp = sensory_data["value"]
        else:
            # There is no sensoryData with the same name as the setpoint we are using, see
            # if we are using leavingWaterOffset, at that moment see if we have a
            # leavingWaterTemperature temperature
            lwsensor = self.sensory_data("leavingWaterTemperature")
            if self._setpoint == "leavingWaterOffset" and lwsensor is not None:
                current_temp = lwsensor["value"]
        _LOGGER.info(
            "Device '%s' %s current temperature '%s'",
            self._device.name,
            self._setpoint,
            current_temp,
        )
        return current_temp

    def get_max_temp(self) -> float:
        max_temp: float
        setpointdict = self.setpoint()
        if setpointdict is not None:
            max_temp = setpointdict["maxValue"]
        else:
            max_temp = super().max_temp
        _LOGGER.info(
            "Device '%s' %s max temperature '%s'",
            self._device.name,
            self._setpoint,
            max_temp,
        )
        return max_temp

    def get_min_temp(self) -> float:
        min_temp: float
        setpointdict = self.setpoint()
        if setpointdict is not None:
            min_temp = setpointdict["minValue"]
        else:
            min_temp = super().min_temp
        _LOGGER.info(
            "Device '%s' %s min temperature '%s'",
            self._device.name,
            self._setpoint,
            min_temp,
        )
        return min_temp

    def get_target_temperature(self) -> float | None:
        value: float | None = None
        setpointdict = self.setpoint()
        if setpointdict is not None:
            value = setpointdict["value"]
        _LOGGER.info(
            "Device '%s' %s target temperature '%s'",
            self._device.name,
            self._setpoint,
            value,
        )
        return value

    def get_target_temperature_step(self) -> float | None:
        step_value: float | None = None
        setpointdict = self.setpoint()
        if setpointdict is not None:
            step = setpointdict.get("stepValue")
            if step is not None:
                step_value = setpointdict["stepValue"]
            else:
                step_value = super().target_temperature_step
        _LOGGER.info(
            "Device '%s' %s target temperature step '%s'",
            self._device.name,
            self._setpoint,
            step_value,
        )
        return step_value

    async def async_set_temperature(self, **kwargs: Any) -> None:
        # """Set new target temperature."""
        if ATTR_HVAC_MODE in kwargs:
            await self.async_set_hvac_mode(kwargs[ATTR_HVAC_MODE])

        if ATTR_TEMPERATURE in kwargs:
            value = kwargs[ATTR_TEMPERATURE]
            _LOGGER.debug(
                "Device '%s' request to set temperature to '%s'",
                self._device.name,
                value,
            )
            if self._attr_target_temperature != value:
                operationmode = self.operation_mode()
                if operationmode is not None:
                    omv = operationmode["value"]
                    res = await self._device.patch(
                        self._device.id,
                        self._embedded_id,
                        "temperatureControl",
                        f"/operationModes/{omv}/setpoints/{self._setpoint}",
                        value,
                    )
                    # When updating the value to the daikin cloud worked update our local cached version
                    if res:
                        setpointdict = self.setpoint()
                        if setpointdict is not None:
                            self._attr_target_temperature = value
                            self.async_write_ha_state()
                    else:
                        _LOGGER.warning(
                            "Device '%s' problem setting temperature to '%s'",
                            self._device.name,
                            value,
                        )

    def get_hvac_mode(self) -> HVACMode:
        """Return current HVAC mode."""
        mode: str | HVACMode = HVACMode.OFF
        operationmode = self.operation_mode()
        cc = self.climate_control()
        if cc is not None:
            onoff = cc.get("onOffMode")
            if onoff is not None:
                if onoff["value"] != "off" and operationmode is not None:
                    mode = operationmode["value"]
            _LOGGER.info(
                "Device '%s' %s hvac mode '%s'",
                self._device.name,
                self._setpoint,
                mode,
            )
        return DAIKIN_HVAC_TO_HA.get(mode, HVACMode.HEAT_COOL)

    def get_hvac_modes(self) -> list[HVACMode]:
        """Return the list of available HVAC modes."""
        modes: list[HVACMode] = [HVACMode.OFF]
        operationmode = self.operation_mode()
        if operationmode is not None:
            if operationmode["settable"] is True:
                for mode in operationmode["values"]:
                    ha_mode = DAIKIN_HVAC_TO_HA[mode]
                    if ha_mode not in modes:
                        modes.append(ha_mode)
            currentmode = operationmode["value"]
            ha_currentmode = DAIKIN_HVAC_TO_HA[currentmode]
            if ha_currentmode not in modes:
                modes.append(ha_currentmode)
        return modes

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set HVAC mode."""
        _LOGGER.debug(
            "Device '%s' request to set hvac_mode to '%s'",
            self._device.name,
            hvac_mode,
        )

        result = True

        # First determine the new settings for onOffMode/operationMode
        on_off_mode = None
        operation_mode = None
        if hvac_mode == HVACMode.OFF:
            if self.hvac_mode != HVACMode.OFF:
                on_off_mode = "off"
        else:
            if self.hvac_mode == HVACMode.OFF:
                on_off_mode = "on"
            operation_mode = HA_HVAC_TO_DAIKIN[hvac_mode]

        cc = self.climate_control()
        if cc is None:
            return

        # Only set the on/off to Daikin when we need to change it
        if on_off_mode is not None:
            result &= bool(await self._device.patch(self._device.id, self._embedded_id, "onOffMode", "", on_off_mode))
            if result is False:
                _LOGGER.warning(
                    "Device '%s' problem setting onOffMode to '%s'",
                    self._device.name,
                    on_off_mode,
                )
            else:
                cc["onOffMode"]["value"] = on_off_mode

        if operation_mode is not None:
            # Only set the operationMode when it has changed, also prevents setting it when
            # it is readOnly
            if operation_mode != cc["operationMode"]["value"]:
                result &= bool(
                    await self._device.patch(
                        self._device.id,
                        self._embedded_id,
                        "operationMode",
                        "",
                        operation_mode,
                    )
                )
                if result is False:
                    _LOGGER.warning(
                        "Device '%s' problem setting operationMode to '%s'",
                        self._device.name,
                        operation_mode,
                    )
                else:
                    cc["operationMode"]["value"] = operation_mode

        if result is True:
            # When switching hvac mode it could be that we can set min/max/target/etc
            # which we couldn't set with a previous hvac mode
            self.update_state()
            self.async_write_ha_state()

    def get_fan_mode(self) -> str | None:
        fan_mode: str | None = None
        cc = self.climate_control()
        if cc is None:
            return fan_mode
        # Check if we have a fanControl
        fanControl = cc.get("fanControl")
        if fanControl is not None:
            operation_mode = cc["operationMode"]["value"]
            operationmodedict = fanControl["value"]["operationModes"].get(operation_mode)
            if operationmodedict is not None:
                fan_speed = operationmodedict.get("fanSpeed")
                if fan_speed is not None:
                    mode = fan_speed["currentMode"]["value"]
                    if mode == FANMODE_FIXED:
                        fsm = fan_speed.get("modes")
                        if fsm is not None:
                            fixedModes = fsm[mode]
                            fan_mode = str(fixedModes["value"])
                    else:
                        fan_mode = mode

        _LOGGER.info(
            "Device '%s' has fan mode '%s'",
            self._device.name,
            fan_mode,
        )

        return fan_mode

    def get_fan_modes(self) -> list[str]:
        fan_modes: list[str] = []
        cc = self.climate_control()
        if cc is None:
            return fan_modes
        # Check if we have a fanControl
        fan_control = cc.get("fanControl")
        if fan_control is not None:
            operation_mode = cc["operationMode"]["value"]
            operationmodedict = fan_control["value"]["operationModes"].get(operation_mode)
            if operationmodedict is not None:
                fan_speed = operationmodedict.get("fanSpeed")
                if fan_speed is not None:
                    _LOGGER.info("Device '%s' has fanspeed %s", self._device.name, fan_speed)
                    for c in fan_speed["currentMode"]["values"]:
                        if c == FANMODE_FIXED:
                            fsm = fan_speed.get("modes")
                            if fsm is not None:
                                fixedModes = fsm[c]
                                min_val = int(fixedModes["minValue"])
                                max_val = int(fixedModes["maxValue"])
                                step_value = int(fixedModes["stepValue"])
                                for val in range(min_val, max_val + 1, step_value):
                                    fan_modes.append(str(val))
                        else:
                            fan_modes.append(c)

        _LOGGER.info(
            "Device '%s' has fan modes '%s'",
            self._device.name,
            fan_modes,
        )

        return fan_modes

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        """Set the fan mode."""
        _LOGGER.debug(
            "Device '%s' request to set fan_mode to '%s'",
            self._device.name,
            fan_mode,
        )

        res = True
        cc = self.climate_control()
        if cc is None:
            return
        operationmode = cc["operationMode"]["value"]
        if fan_mode.isnumeric():
            if self._attr_fan_mode is None or not self._attr_fan_mode.isnumeric():
                # Only set the currentMode to fixed when we currently don't have set
                # a numeric mode
                res = bool(
                    await self._device.patch(
                        self._device.id,
                        self._embedded_id,
                        "fanControl",
                        f"/operationModes/{operationmode}/fanSpeed/currentMode",
                        FANMODE_FIXED,
                    )
                )
                if res is False:
                    _LOGGER.warning(
                        "Device '%s' problem setting fan_mode to fixed",
                        self._device.name,
                    )

            new_fixed_mode = int(fan_mode)
            res &= bool(
                await self._device.patch(
                    self._device.id,
                    self._embedded_id,
                    "fanControl",
                    f"/operationModes/{operationmode}/fanSpeed/modes/fixed",
                    new_fixed_mode,
                )
            )
            if res is False:
                _LOGGER.warning(
                    "Device '%s' problem setting fan_mode fixed to '%s'",
                    self._device.name,
                    new_fixed_mode,
                )
        else:
            res = bool(
                await self._device.patch(
                    self._device.id,
                    self._embedded_id,
                    "fanControl",
                    f"/operationModes/{operationmode}/fanSpeed/currentMode",
                    fan_mode,
                )
            )
            if res is False:
                _LOGGER.warning(
                    "Device '%s' problem setting fan_mode to '%s'",
                    self._device.name,
                    fan_mode,
                )

        if res is True:
            self._attr_fan_mode = fan_mode
            self.async_write_ha_state()

    def __get_swing_mode(self, direction: str) -> str:
        swingMode = ""
        cc = self.climate_control()
        if cc is None:
            return swingMode
        fanControl = cc.get("fanControl")
        if fanControl is not None:
            operationmode = cc["operationMode"]["value"]
            operationmodedict = fanControl["value"]["operationModes"].get(operationmode)
            if operationmodedict is not None:
                fan_direction = operationmodedict.get("fanDirection")
                if fan_direction is not None:
                    fd = fan_direction.get(direction)
                    if fd is not None:
                        swingMode = fd["currentMode"]["value"].lower()

        _LOGGER.info(
            "Device '%s' has %s swing mode '%s'",
            self._device.name,
            direction,
            swingMode,
        )

        return swingMode

    def get_swing_mode(self) -> str:
        return self.__get_swing_mode("vertical")

    def get_swing_horizontal_mode(self) -> str:
        return self.__get_swing_mode("horizontal")

    def __get_swing_modes(self, direction: str) -> list[str]:
        swingModes: list[str] = []
        cc = self.climate_control()
        if cc is None:
            return swingModes
        fanControl = cc.get("fanControl")
        if fanControl is not None:
            swingModes = []
            operationmode = cc["operationMode"]["value"]
            operationmodedict = fanControl["value"]["operationModes"].get(operationmode)
            if operationmodedict is not None:
                fanDirection = operationmodedict.get("fanDirection")
                if fanDirection is not None:
                    vertical = fanDirection.get(direction)
                    if vertical is not None:
                        for mode in vertical["currentMode"]["values"]:
                            swingModes.append(mode.lower())
        _LOGGER.info("Device '%s' support %s swing modes %s", self._device.name, direction, swingModes)
        return swingModes

    def get_swing_modes(self) -> list[str]:
        return self.__get_swing_modes("vertical")

    def get_swing_horizontal_modes(self) -> list[str]:
        return self.__get_swing_modes("horizontal")

    async def __set_swing(self, direction: str, swing_mode: str) -> bool:
        _LOGGER.debug(
            "Device '%s' request to set swing %s mode to '%s'",
            self._device.name,
            direction,
            swing_mode,
        )
        res = True
        cc = self.climate_control()
        if cc is None:
            return res
        fan_control = cc.get("fanControl")
        operation_mode = cc["operationMode"]["value"]
        if fan_control is not None:
            operation_mode = cc["operationMode"]["value"]
            fan_direction = fan_control["value"]["operationModes"][operation_mode].get("fanDirection")
            if fan_direction is not None:
                fd = fan_direction.get(direction)
                if fd is not None:
                    new_mode = "stop"
                    # For translation the current mode is always lower case, but we need to send
                    # the daikin mixed case mode, so search that
                    for mode in fd["currentMode"]["values"]:
                        if swing_mode == mode.lower():
                            new_mode = mode
                    res = bool(
                        await self._device.patch(
                            self._device.id,
                            self._embedded_id,
                            "fanControl",
                            f"/operationModes/{operation_mode}/fanDirection/{direction}/currentMode",
                            new_mode,
                        )
                    )
                    if res is False:
                        _LOGGER.warning(
                            "Device '%s' problem setting %s swing mode to '%s'",
                            self._device.name,
                            direction,
                            new_mode,
                        )
        return res

    async def async_set_swing_mode(self, swing_mode: str) -> None:
        if self.swing_mode != swing_mode:
            res = await self.__set_swing("vertical", swing_mode)

            if res is True:
                self._attr_swing_mode = swing_mode
                self.async_write_ha_state()
        else:
            _LOGGER.debug(
                "Device '%s' request to set vertical swing mode '%s' ignored already set",
                self._device.name,
                swing_mode,
            )

    async def async_set_swing_horizontal_mode(self, swing_horizontal_mode: str) -> None:
        if self.swing_horizontal_mode != swing_horizontal_mode:
            res = await self.__set_swing("horizontal", swing_horizontal_mode)

            if res is True:
                self._attr_swing_horizontal_mode = swing_horizontal_mode
                self.async_write_ha_state()
        else:
            _LOGGER.debug(
                "Device '%s' request to set horizontal swing mode '%s' ignored already set",
                self._device.name,
                swing_horizontal_mode,
            )

    def get_preset_mode(self) -> str:
        cc = self.climate_control()
        current_preset_mode = PRESET_NONE
        if cc is None:
            return current_preset_mode
        for mode in self.preset_modes or []:
            daikin_mode = HA_PRESET_TO_DAIKIN[mode]
            preset = cc.get(daikin_mode)
            if preset is not None:
                preset_value = preset.get("value")
                if preset_value is not None:
                    # for example holidayMode value is a dict object with an enabled value
                    if isinstance(preset_value, dict):
                        enabled_value = preset_value.get("enabled")
                        if enabled_value is not None and enabled_value:
                            current_preset_mode = mode
                    if preset_value == "on":
                        current_preset_mode = mode
        return current_preset_mode

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        _LOGGER.debug("Device '%s' request set preset mode %s", self._device.name, preset_mode)
        result = True
        new_daikin_mode = HA_PRESET_TO_DAIKIN[preset_mode]

        if self.preset_mode is not None and self.preset_mode != PRESET_NONE:
            current_mode = HA_PRESET_TO_DAIKIN[self.preset_mode]
            if self.preset_mode == PRESET_AWAY:
                value: dict[str, Any] = {"enabled": False}
                result &= bool(await self._device.post(self._device.id, self._embedded_id, "holiday-mode", value))
                if result is False:
                    _LOGGER.warning(
                        "Device '%s' problem setting %s to off",
                        self._device.name,
                        current_mode,
                    )
            else:
                result &= bool(await self._device.patch(self._device.id, self._embedded_id, current_mode, "", "off"))
                if result is False:
                    _LOGGER.warning(
                        "Device '%s' problem setting %s to off",
                        self._device.name,
                        current_mode,
                    )

        if preset_mode != PRESET_NONE:
            if self.hvac_mode == HVACMode.OFF and preset_mode == PRESET_BOOST:
                result &= bool(await self.async_turn_on())

            if preset_mode == PRESET_AWAY:
                value = {"enabled": True, "startDate": date.today().isoformat(), "endDate": (date.today() + timedelta(days=60)).isoformat()}
                result &= bool(await self._device.post(self._device.id, self._embedded_id, "holiday-mode", value))
                if result is False:
                    _LOGGER.warning(
                        "Device '%s' problem setting %s to on",
                        self._device.name,
                        new_daikin_mode,
                    )
            else:
                result &= bool(await self._device.patch(self._device.id, self._embedded_id, new_daikin_mode, "", "on"))
                if result is False:
                    _LOGGER.warning(
                        "Device '%s' problem setting %s to on",
                        self._device.name,
                        new_daikin_mode,
                    )

        if result is True:
            self._attr_preset_mode = preset_mode
            self.async_write_ha_state()

    def get_preset_modes(self) -> list[str]:
        supported_preset_modes = [PRESET_NONE]
        cc = self.climate_control()
        if cc is None:
            return supported_preset_modes
        for mode in PRESET_MODES:
            daikin_mode = HA_PRESET_TO_DAIKIN[mode]
            preset = cc.get(daikin_mode)
            if preset is not None and preset.get("value") is not None:
                supported_preset_modes.append(mode)

        _LOGGER.info(
            "Device '%s' supports preset_modes %s",
            self._device.name,
            format(supported_preset_modes),
        )

        supported_preset_modes.sort()
        return supported_preset_modes

    # Override returns ``bool`` instead of ``None``: the internal caller in
    # ``async_set_preset_mode`` consumes the success flag via ``result &= ...``.
    async def async_turn_on(self) -> bool:  # type: ignore[override]
        """Turn device CLIMATE on."""
        _LOGGER.debug("Device '%s' request to turn on", self._device.name)
        cc = self.climate_control()
        result = True
        if cc is None:
            return result
        if cc["onOffMode"]["value"] == "off":
            result &= bool(await self._device.patch(self._device.id, self._embedded_id, "onOffMode", "", "on"))
            if result is False:
                _LOGGER.error("Device '%s' problem setting onOffMode to on", self._device.name)
            else:
                cc["onOffMode"]["value"] = "on"
                self._attr_hvac_mode = self.get_hvac_mode()
                self.async_write_ha_state()
        else:
            _LOGGER.debug(
                "Device '%s' request to turn on ignored because device is already on",
                self._device.name,
            )

        return result

    # Override returns ``bool`` statt ``None`` (siehe ``async_turn_on``).
    async def async_turn_off(self) -> bool:  # type: ignore[override]
        _LOGGER.debug("Device '%s' request to turn off", self._device.name)
        cc = self.climate_control()
        result = True
        if cc is None:
            return result
        if cc["onOffMode"]["value"] == "on":
            result &= bool(await self._device.patch(self._device.id, self._embedded_id, "onOffMode", "", "off"))
            if result is False:
                _LOGGER.error("Device '%s' problem setting onOffMode to off", self._device.name)
            else:
                cc["onOffMode"]["value"] = "off"
                self._attr_hvac_mode = self.get_hvac_mode()
                self.async_write_ha_state()
        else:
            _LOGGER.debug(
                "Device '%s' request to turn off ignored because device is already off",
                self._device.name,
            )

        return result
