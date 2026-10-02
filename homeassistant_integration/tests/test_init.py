"""Test setup and unloading of the integration."""

from __future__ import annotations

from homeassistant import config_entries
from homeassistant.core import HomeAssistant

from custom_components.blauberg_vento.const import DOMAIN

from .conftest import DEVICE_ID, HOST


async def test_setup_unload(
    hass: HomeAssistant, config_entry, mock_vento_client
) -> None:
    """Test setting up and unloading the integration."""
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    assert DOMAIN in hass.data
    assert config_entry.state is config_entries.ConfigEntryState.LOADED

    assert await hass.config_entries.async_unload(config_entry.entry_id)
    await hass.async_block_till_done()
    assert config_entry.state is config_entries.ConfigEntryState.NOT_LOADED
    assert config_entry.entry_id not in hass.data.get(DOMAIN, {})
