"""Config flow for the Blauberg Vento integration."""

from __future__ import annotations

import logging
from typing import Any

from blauberg_vento import AsyncVentoClient, VentoError
import voluptuous as vol

from homeassistant.config_entries import (
    ConfigFlow,
    ConfigFlowResult,
)
from homeassistant.const import CONF_DEVICE_ID, CONF_HOST, CONF_PASSWORD
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from .const import CONF_DEVICE_ID as CUSTOM_DEVICE_ID, DEFAULT_PASSWORD, DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_DEVICE_ID): str,
        vol.Optional(CONF_PASSWORD, default=DEFAULT_PASSWORD): str,
    }
)


class BlaubergVentoConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the Blauberg Vento config flow."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST]
            device_id = user_input[CONF_DEVICE_ID]
            password = user_input.get(CONF_PASSWORD, DEFAULT_PASSWORD)

            client = AsyncVentoClient(host=host, device_id=device_id, password=password)
            try:
                state = await client.get_state()
            except VentoError:
                errors["base"] = "cannot_connect"
            else:
                await client.__aexit__(None, None, None)
                await self.async_set_unique_id(device_id)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=state.device_id or device_id,
                    data={
                        CONF_HOST: host,
                        CONF_DEVICE_ID: device_id,
                        CONF_PASSWORD: password,
                    },
                )

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_SCHEMA, errors=errors
        )
