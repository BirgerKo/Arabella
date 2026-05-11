"""Unit tests for DeviceManager."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from blauberg_vento.models import DeviceState, DiscoveredDevice
from webdashboard.backend.device_manager import DeviceManager, _state_to_dict


def _make_state(**kw):
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
    state = _make_state()
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
    mock_state = _make_state()
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
    mock_state = _make_state()
    mock_client = MagicMock()
    mock_client.get_state = AsyncMock(return_value=mock_state)

    with patch("webdashboard.backend.device_manager.AsyncVentoClient", return_value=mock_client):
        await manager.connect("10.0.0.1", "VENT-01")

    manager.disconnect()
    assert not manager.is_connected
    assert manager.current_state is None


@pytest.mark.asyncio
async def test_set_power_calls_turn_on(manager):
    mock_state = _make_state(power=False)
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
    mock_state = _make_state(power=True)
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
    mock_state = _make_state()
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
    mock_state = _make_state()
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
    mock_state = _make_state()
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
async def test_enable_schedule(manager):
    mock_state = _make_state()
    mock_client = MagicMock()
    mock_client.get_state             = AsyncMock(return_value=mock_state)
    mock_client.enable_weekly_schedule = AsyncMock()

    with patch("webdashboard.backend.device_manager.AsyncVentoClient", return_value=mock_client):
        await manager.connect("10.0.0.1", "VENT-01")
        await manager.enable_schedule(True)

    mock_client.enable_weekly_schedule.assert_awaited_once_with(True)
    manager.disconnect()


@pytest.mark.asyncio
async def test_set_schedule_period(manager):
    mock_state = _make_state()
    mock_client = MagicMock()
    mock_client.get_state          = AsyncMock(return_value=mock_state)
    mock_client.set_schedule_period = AsyncMock()

    with patch("webdashboard.backend.device_manager.AsyncVentoClient", return_value=mock_client):
        await manager.connect("10.0.0.1", "VENT-01")
        await manager.set_schedule_period(0, 1, 2, 8, 30)

    mock_client.set_schedule_period.assert_awaited_once_with(0, 1, 2, 8, 30)
    manager.disconnect()


@pytest.mark.asyncio
async def test_sync_rtc(manager):
    mock_state = _make_state()
    mock_client = MagicMock()
    mock_client.get_state = AsyncMock(return_value=mock_state)
    mock_client.sync_rtc  = AsyncMock()

    with patch("webdashboard.backend.device_manager.AsyncVentoClient", return_value=mock_client):
        await manager.connect("10.0.0.1", "VENT-01")
        await manager.sync_rtc()

    mock_client.sync_rtc.assert_awaited_once()
    manager.disconnect()


def test_state_to_dict_includes_schedule_fields():
    from blauberg_vento.models import RtcTime, RtcCalendar
    state = _make_state(
        weekly_schedule_enabled=True,
        rtc_time=RtcTime(hours=14, minutes=30, seconds=0),
        rtc_calendar=RtcCalendar(year=2026, month=3, day=22, day_of_week=7),
    )
    d = _state_to_dict(state)
    assert d["weekly_schedule_enabled"] is True
    assert d["rtc_time"] == "14:30:00"
    assert d["rtc_calendar"] is not None


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
    mock_state = _make_state()
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


# ── Fan switching ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_connect_replaces_active_device(manager):
    """Connecting to a second device stops the first poller and activates the new state."""
    state_a = _make_state(ip="10.0.0.1", device_id="FAN-A")
    state_b = _make_state(ip="10.0.0.2", device_id="FAN-B", speed=3)

    client_a = MagicMock()
    client_a.get_state = AsyncMock(return_value=state_a)
    client_b = MagicMock()
    client_b.get_state = AsyncMock(return_value=state_b)

    clients = iter([client_a, client_b])

    with patch(
        "webdashboard.backend.device_manager.AsyncVentoClient",
        side_effect=lambda *a, **kw: next(clients),
    ):
        await manager.connect("10.0.0.1", "FAN-A")
        poll_task_a = manager._poll_task

        await manager.connect("10.0.0.2", "FAN-B")

    assert manager.current_state is state_b, "Active state must be the new device"
    assert manager.current_state.device_id == "FAN-B"
    assert poll_task_a.done(), "Poller for device A must be cancelled after switching"
    assert manager._poll_task is not poll_task_a, "A new poll task must be created for device B"

    manager.disconnect()


@pytest.mark.asyncio
async def test_switch_preserves_connection_to_new_device(manager):
    """After switching, commands go to the new device, not the old one."""
    state_a = _make_state(ip="10.0.0.1", device_id="FAN-A")
    state_b = _make_state(ip="10.0.0.2", device_id="FAN-B")

    client_a = MagicMock()
    client_a.get_state = AsyncMock(return_value=state_a)
    client_a.turn_on   = AsyncMock()
    client_b = MagicMock()
    client_b.get_state = AsyncMock(return_value=state_b)
    client_b.turn_on   = AsyncMock()

    clients = iter([client_a, client_b])

    with patch(
        "webdashboard.backend.device_manager.AsyncVentoClient",
        side_effect=lambda *a, **kw: next(clients),
    ):
        await manager.connect("10.0.0.1", "FAN-A")
        await manager.connect("10.0.0.2", "FAN-B")
        await manager.set_power(True)

    client_b.turn_on.assert_awaited_once()
    client_a.turn_on.assert_not_awaited()

    manager.disconnect()


@pytest.mark.asyncio
async def test_switch_active_state_reflects_new_device(manager):
    """After switching, current_state contains the new device's fields, not the old ones."""
    state_a = _make_state(ip="10.0.0.1", device_id="FAN-A", speed=1, fan1_rpm=800)
    state_b = _make_state(ip="10.0.0.2", device_id="FAN-B", speed=3, fan1_rpm=2400)

    client_a = MagicMock()
    client_a.get_state = AsyncMock(return_value=state_a)
    client_b = MagicMock()
    client_b.get_state = AsyncMock(return_value=state_b)

    clients = iter([client_a, client_b])

    with patch(
        "webdashboard.backend.device_manager.AsyncVentoClient",
        side_effect=lambda *a, **kw: next(clients),
    ):
        await manager.connect("10.0.0.1", "FAN-A")
        assert manager.current_state.fan1_rpm == 800

        await manager.connect("10.0.0.2", "FAN-B")

    assert manager.current_state.ip == "10.0.0.2"
    assert manager.current_state.device_id == "FAN-B"
    assert manager.current_state.speed == 3
    assert manager.current_state.fan1_rpm == 2400

    manager.disconnect()
