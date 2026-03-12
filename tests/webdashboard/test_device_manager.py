"""Unit tests for DeviceManager."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from blauberg_vento.models import DeviceState, DiscoveredDevice
from webdashboard.backend.device_manager import DeviceManager, _state_to_dict


def make_state(**kw):
    defaults = dict(
        ip="10.0.0.1",
        device_id="VENT-01",
        power=True,
        speed=2,
        manual_speed=None,
        operation_mode=0,
        boost_active=False,
        fan1_rpm=1200,
        fan2_rpm=1100,
        alarm_status=0,
    )
    return DeviceState(**{**defaults, **kw})


@pytest.fixture
def manager():
    return DeviceManager()


def test_state_to_dict_maps_fields():
    state = make_state()
    d = _state_to_dict(state)
    assert d["connected"] is True
    assert d["ip"] == "10.0.0.1"
    assert d["device_id"] == "VENT-01"
    assert d["power"] is True
    assert d["operation_mode_name"] == "Ventilation"
    assert d["alarm_name"] == "OK"


def test_initially_not_connected(manager):
    assert not manager.is_connected
    assert manager.current_state is None


@pytest.mark.asyncio
async def test_connect_sets_state_and_starts_polling(manager):
    mock_state = make_state()
    mock_client = MagicMock()
    mock_client.get_state = AsyncMock(return_value=mock_state)

    with patch("webdashboard.backend.device_manager.AsyncVentoClient", return_value=mock_client):
        result = await manager.connect("10.0.0.1", "VENT-01")

    assert manager.is_connected
    assert manager.current_state is mock_state
    assert result is mock_state
    assert manager._poll_task is not None
    # Cleanup
    manager.disconnect()


@pytest.mark.asyncio
async def test_disconnect_clears_state(manager):
    mock_state = make_state()
    mock_client = MagicMock()
    mock_client.get_state = AsyncMock(return_value=mock_state)

    with patch("webdashboard.backend.device_manager.AsyncVentoClient", return_value=mock_client):
        await manager.connect("10.0.0.1", "VENT-01")

    manager.disconnect()
    assert not manager.is_connected
    assert manager.current_state is None


@pytest.mark.asyncio
async def test_set_power_calls_turn_on(manager):
    mock_state = make_state(power=False)
    mock_client = MagicMock()
    mock_client.get_state = AsyncMock(return_value=mock_state)
    mock_client.turn_on   = AsyncMock()
    mock_client.turn_off  = AsyncMock()

    with patch("webdashboard.backend.device_manager.AsyncVentoClient", return_value=mock_client):
        await manager.connect("10.0.0.1", "VENT-01")
        await manager.set_power(True)

    mock_client.turn_on.assert_awaited_once()
    mock_client.turn_off.assert_not_awaited()
    manager.disconnect()


@pytest.mark.asyncio
async def test_set_power_calls_turn_off(manager):
    mock_state = make_state(power=True)
    mock_client = MagicMock()
    mock_client.get_state = AsyncMock(return_value=mock_state)
    mock_client.turn_off  = AsyncMock()

    with patch("webdashboard.backend.device_manager.AsyncVentoClient", return_value=mock_client):
        await manager.connect("10.0.0.1", "VENT-01")
        await manager.set_power(False)

    mock_client.turn_off.assert_awaited_once()
    manager.disconnect()


@pytest.mark.asyncio
async def test_set_speed_preset(manager):
    mock_state = make_state()
    mock_client = MagicMock()
    mock_client.get_state  = AsyncMock(return_value=mock_state)
    mock_client.set_speed  = AsyncMock()

    with patch("webdashboard.backend.device_manager.AsyncVentoClient", return_value=mock_client):
        await manager.connect("10.0.0.1", "VENT-01")
        await manager.set_speed(3)

    mock_client.set_speed.assert_awaited_once_with(3)
    manager.disconnect()


@pytest.mark.asyncio
async def test_set_speed_manual(manager):
    mock_state = make_state()
    mock_client = MagicMock()
    mock_client.get_state       = AsyncMock(return_value=mock_state)
    mock_client.set_manual_speed = AsyncMock()

    with patch("webdashboard.backend.device_manager.AsyncVentoClient", return_value=mock_client):
        await manager.connect("10.0.0.1", "VENT-01")
        await manager.set_speed(180)

    mock_client.set_manual_speed.assert_awaited_once_with(180)
    manager.disconnect()


@pytest.mark.asyncio
async def test_set_mode(manager):
    mock_state = make_state()
    mock_client = MagicMock()
    mock_client.get_state = AsyncMock(return_value=mock_state)
    mock_client.set_mode  = AsyncMock()

    with patch("webdashboard.backend.device_manager.AsyncVentoClient", return_value=mock_client):
        await manager.connect("10.0.0.1", "VENT-01")
        await manager.set_mode(1)

    mock_client.set_mode.assert_awaited_once_with(1)
    manager.disconnect()


@pytest.mark.asyncio
async def test_require_connection_raises_when_disconnected(manager):
    with pytest.raises(RuntimeError, match="Not connected"):
        await manager.set_power(True)


@pytest.mark.asyncio
async def test_discover_delegates_to_client():
    mock_devices = [DiscoveredDevice(ip="192.168.1.1", device_id="FAN", unit_type=3)]
    with patch(
        "webdashboard.backend.device_manager.AsyncVentoClient.discover",
        new=AsyncMock(return_value=mock_devices),
    ):
        result = await DeviceManager.discover()

    assert result == mock_devices


@pytest.mark.asyncio
async def test_broadcast_callback_called_after_command(manager):
    mock_state = make_state()
    mock_client = MagicMock()
    mock_client.get_state = AsyncMock(return_value=mock_state)
    mock_client.turn_on   = AsyncMock()

    received = []
    manager.set_broadcast_callback(lambda m: received.append(m) or AsyncMock()())

    with patch("webdashboard.backend.device_manager.AsyncVentoClient", return_value=mock_client):
        await manager.connect("10.0.0.1", "VENT-01")
        await manager.set_power(True)

    assert any(m.get("type") == "state" for m in received)
    manager.disconnect()
