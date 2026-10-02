"""Fan platform for the Blauberg Vento integration."""

from __future__ import annotations

from typing import Any

from blauberg_vento import DeviceState

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util.percentage import (
    int_states_in_range,
    percentage_to_ranged_value_int,
    ranged_value_to_percentage,
)

from .const import DOMAIN
from .coordinator import VentoCoordinator

SPEED_RANGE = (1, 3)
OPERATION_MODES = {0: "ventilation", 1: "heat_recovery", 2: "supply"}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the fan platform."""
    coordinator: VentoCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([VentoFan(coordinator)])


class VentoFan(FanEntity):
    """Representation of a Blauberg Vento fan."""

    _attr_has_entity_name = True
    _attr_name = None

    def __init__(self, coordinator: VentoCoordinator) -> None:
        """Initialize the fan entity."""
        self.coordinator = coordinator
        self._attr_unique_id = coordinator.device_id
        self._attr_supported_features = (
            FanEntityFeature.SET_SPEED | FanEntityFeature.PRESET_MODE
        )
        self._attr_preset_modes = list(OPERATION_MODES.values())

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return DeviceInfo(**self.coordinator.device_info_data)

    @property
    def is_on(self) -> bool:
        """Return true if the fan is on."""
        state = self.coordinator.current_state
        return bool(state.power) if state else False

    @property
    def percentage(self) -> int | None:
        """Return the current speed as a percentage."""
        state = self.coordinator.current_state
        if not state or state.speed is None:
            return None
        if state.speed == 255:
            manual = state.manual_speed if state.manual_speed is not None else 0
            return ranged_value_to_percentage((0, 255), manual)
        return ranged_value_to_percentage(SPEED_RANGE, state.speed)

    @property
    def preset_mode(self) -> str | None:
        """Return the current operation mode preset."""
        state = self.coordinator.current_state
        if not state or state.operation_mode is None:
            return None
        return OPERATION_MODES.get(state.operation_mode)

    async def async_turn_on(
        self,
        percentage: int | None = None,
        preset_mode: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Turn on the fan."""
        if percentage is not None:
            await self.async_set_percentage(percentage)
            return
        await self.coordinator.client.turn_on()
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the fan."""
        await self.coordinator.client.turn_off()
        await self.coordinator.async_request_refresh()

    async def async_set_percentage(self, percentage: int) -> None:
        """Set the fan speed as a percentage."""
        if percentage == 0:
            await self.async_turn_off()
            return
        speed = percentage_to_ranged_value_int(SPEED_RANGE, percentage)
        await self.coordinator.client.set_speed(speed)
        await self.coordinator.async_request_refresh()

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set the operation mode."""
        for mode_value, name in OPERATION_MODES.items():
            if name == preset_mode:
                await self.coordinator.client.set_mode(mode_value)
                await self.coordinator.async_request_refresh()
                return

    @property
    def state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        state = self.coordinator.current_state
        attrs: dict[str, Any] = {
            "speed": state.speed,
            "boost_active": state.boost_active,
        }
        return attrs


def _speed_step_count() -> int:
    """Return the number of discrete speed steps."""
    return int_states_in_range(SPEED_RANGE)
