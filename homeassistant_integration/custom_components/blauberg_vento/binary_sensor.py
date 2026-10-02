"""Binary sensor platform for the Blauberg Vento integration."""

from __future__ import annotations

from blauberg_vento import DeviceState
import voluptuous as vol

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import VentoCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up binary sensor entities."""
    coordinator: VentoCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            VentoBinarySensor(coordinator, "humidity_status", "Humidity Over Threshold",
                              BinarySensorDeviceClass.MOISTURE),
            VentoBinarySensor(coordinator, "voltage_status", "Voltage Over Threshold",
                              BinarySensorDeviceClass.VOLTAGE),
            VentoBinarySensor(coordinator, "relay_state", "Relay State",
                              BinarySensorDeviceClass.PLUG),
            VentoBinarySensor(coordinator, "filter_needs_replacement", "Filter Needs Replacement",
                              None),
        ]
    )


class VentoBinarySensor(BinarySensorEntity):
    """Representation of a Vento binary sensor."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: VentoCoordinator,
        attr: str,
        name: str,
        device_class: BinarySensorDeviceClass | None,
    ) -> None:
        """Initialize the binary sensor."""
        self.coordinator = coordinator
        self._attr_unique_id = f"{coordinator.device_id}_{attr}"
        self._attr_name = name
        self._attr_device_class = device_class
        self._attr = attr

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return DeviceInfo(**self.coordinator.device_info_data)

    @property
    def is_on(self) -> bool | None:
        """Return true if the binary sensor is on."""
        state = self.coordinator.current_state
        if not state:
            return None
        return getattr(state, self._attr, None)
