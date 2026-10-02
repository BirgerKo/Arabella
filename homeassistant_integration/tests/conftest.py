"""Fixtures for Blauberg Vento integration tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from blauberg_vento import DeviceState
import pytest

from homeassistant.const import CONF_DEVICE_ID, CONF_HOST, CONF_PASSWORD

from tests.common import MockConfigEntry

from custom_components.blauberg_vento.const import DEFAULT_PASSWORD, DOMAIN

HOST = "192.168.1.100"
DEVICE_ID = "AABBCCDDEEFF1122"


@pytest.fixture
def mock_setup_entry() -> AsyncMock:
    """Mock setting up a config entry."""
    with patch(
        "custom_components.blauberg_vento.async_setup_entry",
        return_value=True,
    ) as mock:
        yield mock


def make_state() -> DeviceState:
    """Create a plausible device state."""
    return DeviceState(
        ip=HOST,
        device_id=DEVICE_ID,
        power=True,
        speed=2,
        manual_speed=None,
        operation_mode=0,
        boost_active=False,
        current_humidity=55,
        fan1_rpm=1200,
        fan2_rpm=1180,
        humidity_status=False,
        voltage_status=False,
        relay_state=False,
        filter_needs_replacement=False,
    )


@pytest.fixture
def mock_vento_client() -> AsyncMock:
    """Mock the AsyncVentoClient."""
    with patch(
        "custom_components.blauberg_vento.coordinator.AsyncVentoClient",
        autospec=True,
    ) as client_cls:
        client = MagicMock()
        client.get_state = AsyncMock(return_value=make_state())
        client.turn_on = AsyncMock()
        client.turn_off = AsyncMock()
        client.set_speed = AsyncMock()
        client.set_mode = AsyncMock()
        client.set_manual_speed = AsyncMock()
        client.set_humidity_threshold = AsyncMock()
        client.__aexit__ = AsyncMock(return_value=None)
        client_cls.return_value = client
        yield client


@pytest.fixture
def config_entry() -> MockConfigEntry:
    """Create a mock config entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_HOST: HOST,
            CONF_DEVICE_ID: DEVICE_ID,
            CONF_PASSWORD: DEFAULT_PASSWORD,
        },
        entry_id="test",
        unique_id=DEVICE_ID,
    )
