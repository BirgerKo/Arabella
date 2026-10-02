"""Data update coordinator for Blauberg Vento."""

from __future__ import annotations

import asyncio
from datetime import timedelta
from typing import Any

from blauberg_vento import AsyncVentoClient, DeviceState, VentoError

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_DEVICE_ID, CONF_HOST, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DEFAULT_NAME, DEFAULT_PASSWORD, DOMAIN

UPDATE_INTERVAL = timedelta(seconds=30)
REQUEST_TIMEOUT = 10


class VentoCoordinator(DataUpdateCoordinator[DeviceState]):
    """Coordinate state updates for a single Vento device."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            logger=None,
            name=DOMAIN,
            update_interval=UPDATE_INTERVAL,
        )
        self.entry = entry
        self.client = AsyncVentoClient(
            host=entry.data[CONF_HOST],
            device_id=entry.data[CONF_DEVICE_ID],
            password=entry.data.get(CONF_PASSWORD, DEFAULT_PASSWORD),
        )

    async def _async_update_data(self) -> DeviceState:
        """Fetch the latest device state."""
        try:
            async with asyncio.timeout(REQUEST_TIMEOUT):
                return await self.client.get_state()
        except VentoError as err:
            raise UpdateFailed(f"Error fetching Vento state: {err}") from err

    async def async_shutdown(self) -> None:
        """Close the client connection."""
        await self.client.__aexit__(None, None, None)

    @property
    def device_id(self) -> str:
        """Return the device id of the managed device."""
        return str(self.entry.data[CONF_DEVICE_ID])

    @property
    def device_info_data(self) -> dict[str, Any]:
        """Return device info attributes."""
        state = self.current_state
        firmware = str(state.firmware) if state and state.firmware else None
        model = state.unit_type_name if state else None
        return {
            "identifiers": {(DOMAIN, self.device_id)},
            "name": self.entry.data.get("name", DEFAULT_NAME),
            "model": model,
            "sw_version": firmware,
        }
