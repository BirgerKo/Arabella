"""Test fan entity behavior."""

from __future__ import annotations

from homeassistant.components.fan import (
    ATTR_PERCENTAGE,
    ATTR_PRESET_MODE,
    DOMAIN as FAN_DOMAIN,
)
from homeassistant.const import STATE_ON
from homeassistant.core import HomeAssistant

from custom_components.blauberg_vento.const import DOMAIN

ENTITY_ID = "fan.vento_fan"


async def test_fan_state(
    hass: HomeAssistant, config_entry, mock_vento_client
) -> None:
    """Test the fan reports state from the coordinator."""
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get(ENTITY_ID)
    assert state is not None
    assert state.state == STATE_ON


async def test_fan_turn_off(
    hass: HomeAssistant, config_entry, mock_vento_client
) -> None:
    """Test turning the fan off calls the client."""
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    await hass.services.async_call(
        FAN_DOMAIN,
        "turn_off",
        {"entity_id": ENTITY_ID},
        blocking=True,
    )
    assert mock_vento_client.turn_off.await_count == 1


async def test_fan_set_percentage(
    hass: HomeAssistant, config_entry, mock_vento_client
) -> None:
    """Test setting fan speed percentage."""
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    await hass.services.async_call(
        FAN_DOMAIN,
        "set_percentage",
        {"entity_id": ENTITY_ID, ATTR_PERCENTAGE: 100},
        blocking=True,
    )
    assert mock_vento_client.set_speed.await_count == 1


async def test_fan_set_preset_mode(
    hass: HomeAssistant, config_entry, mock_vento_client
) -> None:
    """Test setting the preset mode."""
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    await hass.services.async_call(
        FAN_DOMAIN,
        "set_preset_mode",
        {"entity_id": ENTITY_ID, ATTR_PRESET_MODE: "heat_recovery"},
        blocking=True,
    )
    assert mock_vento_client.set_mode.await_count == 1
