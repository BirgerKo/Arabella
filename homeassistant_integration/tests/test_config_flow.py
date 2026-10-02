"""Test the Blauberg Vento config flow."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from blauberg_vento import VentoTimeoutError
import pytest

from homeassistant import config_entries
from homeassistant.const import CONF_DEVICE_ID, CONF_HOST, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.blauberg_vento.const import DEFAULT_PASSWORD, DOMAIN

from .conftest import DEVICE_ID, HOST, make_state

USER_INPUT = {
    CONF_HOST: HOST,
    CONF_DEVICE_ID: DEVICE_ID,
    CONF_PASSWORD: DEFAULT_PASSWORD,
}


async def test_form(hass: HomeAssistant, mock_setup_entry: AsyncMock) -> None:
    """Test a successful config flow."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"

    with patch(
        "custom_components.blauberg_vento.config_flow.AsyncVentoClient",
        autospec=True,
    ) as client_cls:
        client = client_cls.return_value
        client.get_state = AsyncMock(return_value=make_state())
        client.__aexit__ = AsyncMock(return_value=None)
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], USER_INPUT
        )
        await hass.async_block_till_done()

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_HOST] == HOST
    assert result["data"][CONF_DEVICE_ID] == DEVICE_ID
    assert len(mock_setup_entry.mock_calls) == 1


async def test_form_cannot_connect(hass: HomeAssistant) -> None:
    """Test a failed connection shows an error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "custom_components.blauberg_vento.config_flow.AsyncVentoClient",
        autospec=True,
    ) as client_cls:
        client = client_cls.return_value
        client.get_state = AsyncMock(side_effect=VentoTimeoutError())
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], USER_INPUT
        )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}
