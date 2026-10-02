"""Sensor platform for the Blauberg Vento integration."""

from __future__ import annotations

from typing import Any

from blauberg_vento import DeviceState

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType

from .const import DOMAIN
from .coordinator import VentoCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensor entities."""
    coordinator: VentoCoordinator = hass.data[DOMAIN][entry.entry_id]
    state = coordinator.current_state
    entities: list[VentoSensor] = [
        VentoSensor(coordinator, "current_humidity", "Humidity",
                    SensorDeviceClass.HUMIDITY, PERCENTAGE,
                    SensorStateClass.MEASUREMENT),
        VentoSensor(coordinator, "fan1_rpm", "Fan 1 Speed", None, "rpm",
                    SensorStateClass.MEASUREMENT),
        VentoSensor(coordinator, "fan2_rpm", "Fan 2 Speed", None, "rpm",
                    SensorStateClass.MEASUREMENT),
    ]
    if state and state.unit_type and state.is_a30:
        entities.append(
            VentoSensor(coordinator, "battery_voltage_mv", "Battery Voltage",
                        SensorDeviceClass.VOLTAGE, "mV",
                        SensorStateClass.MEASUREMENT))
    async_add_entities(entities)


class VentoSensor(SensorEntity):
    """Representation of a Vento sensor."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: VentoCoordinator,
        attr: str,
        name: str,
        device_class: SensorDeviceClass | None,
        unit: str | None,
        state_class: SensorStateClass | None,
    ) -> None:
        """Initialize the sensor."""
        self.coordinator = coordinator
        self._attr_unique_id = f"{coordinator.device_id}_{attr}"
        self._attr_name = name
        self._attr_device_class = device_class
        self._attr_native_unit_of_measurement = unit
        self._attr_state_class = state_class
        self._attr = attr

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return DeviceInfo(**self.coordinator.device_info_data)

    @property
    def native_value(self) -> StateType:
        """Return the sensor value."""
        state = self.coordinator.current_state
        if not state:
            return None
        value: Any = getattr(state, self._attr, None)
        return value if isinstance(value, (int, float, str)) else None
