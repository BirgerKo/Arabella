"""Number platform for the Blauberg Vento integration."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity
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
    """Set up number entities."""
    coordinator: VentoCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            VentoNumber(
                coordinator,
                "manual_speed",
                "Manual Speed",
                0,
                255,
                lambda value: coordinator.client.set_manual_speed(int(value)),
            ),
            VentoNumber(
                coordinator,
                "humidity_threshold",
                "Humidity Threshold",
                40,
                80,
                lambda value: coordinator.client.set_humidity_threshold(int(value)),
            ),
        ]
    )


class VentoNumber(NumberEntity):
    """Representation of a Vento number entity."""

    _attr_has_entity_name = True
    _attr_mode = "box"

    def __init__(
        self,
        coordinator: VentoCoordinator,
        attr: str,
        name: str,
        minimum: int,
        maximum: int,
        setter,
    ) -> None:
        """Initialize the number entity."""
        self.coordinator = coordinator
        self._attr_unique_id = f"{coordinator.device_id}_{attr}"
        self._attr_name = name
        self._attr_native_min_value = minimum
        self._attr_native_max_value = maximum
        self._attr = attr
        self._setter = setter

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return DeviceInfo(**self.coordinator.device_info_data)

    @property
    def native_value(self) -> float | None:
        """Return the current value."""
        state = self.coordinator.current_state
        if not state:
            return None
        value = getattr(state, self._attr, None)
        return float(value) if value is not None else None

    async def async_set_native_value(self, value: float) -> None:
        """Set the value."""
        await self._setter(value)
        await self.coordinator.async_request_refresh()
