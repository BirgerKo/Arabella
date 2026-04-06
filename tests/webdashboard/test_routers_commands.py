"""Integration tests for command endpoints via the FastAPI test client."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from webdashboard.backend.main import app
from webdashboard.backend import dependencies


def _make_schedule_period(speed, end_hours, end_minutes):
    from blauberg_vento.models import SchedulePeriod
    return SchedulePeriod(period_number=1, speed=speed, end_hours=end_hours, end_minutes=end_minutes)


def _make_full_schedule():
    """Return a mock full schedule: 8 day groups × 4 periods, all zeroed."""
    return [[_make_schedule_period(0, 0, 0) for _ in range(4)] for _ in range(8)]


def make_connected_manager(state_overrides=None):
    from blauberg_vento.models import DeviceState
    state = DeviceState(
        ip="10.0.0.1",
        device_id="VENT-01",
        power=True,
        speed=2,
        operation_mode=0,
        boost_active=False,
        alarm_status=0,
    )
    mgr = MagicMock()
    mgr.is_connected = True
    mgr.current_state = state
    mgr.set_power              = AsyncMock()
    mgr.set_speed              = AsyncMock()
    mgr.set_mode               = AsyncMock()
    mgr.set_boost              = AsyncMock()
    mgr.set_humidity_sensor    = AsyncMock()
    mgr.set_humidity_threshold = AsyncMock()
    mgr.enable_schedule        = AsyncMock()
    mgr.set_schedule_period    = AsyncMock()
    mgr.get_full_schedule      = AsyncMock(return_value=_make_full_schedule())
    mgr.sync_rtc               = AsyncMock()
    return mgr


@pytest.fixture
def client_and_mgr():
    mgr = make_connected_manager()
    app.dependency_overrides[dependencies.get_device_manager] = lambda: mgr
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test"), mgr


@pytest.mark.asyncio
async def test_set_power_on(client_and_mgr):
    client, mgr = client_and_mgr
    async with client as c:
        resp = await c.post("/api/command/power", json={"on": True})
    assert resp.status_code == 204
    mgr.set_power.assert_awaited_once_with(True)


@pytest.mark.asyncio
async def test_set_power_off(client_and_mgr):
    client, mgr = client_and_mgr
    async with client as c:
        resp = await c.post("/api/command/power", json={"on": False})
    assert resp.status_code == 204
    mgr.set_power.assert_awaited_once_with(False)


@pytest.mark.asyncio
async def test_set_speed(client_and_mgr):
    client, mgr = client_and_mgr
    async with client as c:
        resp = await c.post("/api/command/speed", json={"speed": 3})
    assert resp.status_code == 204
    mgr.set_speed.assert_awaited_once_with(3)


@pytest.mark.asyncio
async def test_set_mode(client_and_mgr):
    client, mgr = client_and_mgr
    async with client as c:
        resp = await c.post("/api/command/mode", json={"mode": 1})
    assert resp.status_code == 204
    mgr.set_mode.assert_awaited_once_with(1)


@pytest.mark.asyncio
async def test_set_boost(client_and_mgr):
    client, mgr = client_and_mgr
    async with client as c:
        resp = await c.post("/api/command/boost", json={"on": True})
    assert resp.status_code == 204
    mgr.set_boost.assert_awaited_once_with(True)


@pytest.mark.asyncio
async def test_command_returns_503_when_disconnected():
    mgr = MagicMock()
    mgr.is_connected = False
    app.dependency_overrides[dependencies.get_device_manager] = lambda: mgr

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        resp = await c.post("/api/command/power", json={"on": True})
    assert resp.status_code == 503
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_invalid_mode_returns_422(client_and_mgr):
    client, _ = client_and_mgr
    async with client as c:
        resp = await c.post("/api/command/mode", json={"mode": 99})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_set_humidity_sensor(client_and_mgr):
    client, mgr = client_and_mgr
    async with client as c:
        resp = await c.post("/api/command/humidity_sensor", json={"sensor": 1})
    assert resp.status_code == 204
    mgr.set_humidity_sensor.assert_awaited_once_with(1)


@pytest.mark.asyncio
async def test_set_humidity_threshold(client_and_mgr):
    client, mgr = client_and_mgr
    async with client as c:
        resp = await c.post("/api/command/humidity_threshold", json={"threshold": 65})
    assert resp.status_code == 204
    mgr.set_humidity_threshold.assert_awaited_once_with(65)


@pytest.mark.asyncio
async def test_humidity_sensor_out_of_range_returns_422(client_and_mgr):
    client, _ = client_and_mgr
    async with client as c:
        resp = await c.post("/api/command/humidity_sensor", json={"sensor": 5})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_humidity_threshold_out_of_range_returns_422(client_and_mgr):
    client, _ = client_and_mgr
    async with client as c:
        resp = await c.post("/api/command/humidity_threshold", json={"threshold": 20})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_schedule_enable_on(client_and_mgr):
    client, mgr = client_and_mgr
    async with client as c:
        resp = await c.post("/api/command/schedule_enable", json={"enabled": True})
    assert resp.status_code == 204
    mgr.enable_schedule.assert_awaited_once_with(True)


@pytest.mark.asyncio
async def test_schedule_enable_off(client_and_mgr):
    client, mgr = client_and_mgr
    async with client as c:
        resp = await c.post("/api/command/schedule_enable", json={"enabled": False})
    assert resp.status_code == 204
    mgr.enable_schedule.assert_awaited_once_with(False)


@pytest.mark.asyncio
async def test_schedule_period_valid(client_and_mgr):
    client, mgr = client_and_mgr
    payload = {"day": 0, "period": 1, "speed": 2, "end_h": 8, "end_m": 30}
    async with client as c:
        resp = await c.post("/api/command/schedule_period", json=payload)
    assert resp.status_code == 204
    mgr.set_schedule_period.assert_awaited_once_with(0, 1, 2, 8, 30)


@pytest.mark.asyncio
async def test_schedule_period_invalid_day_returns_422(client_and_mgr):
    client, _ = client_and_mgr
    payload = {"day": 10, "period": 1, "speed": 1, "end_h": 0, "end_m": 0}
    async with client as c:
        resp = await c.post("/api/command/schedule_period", json=payload)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_schedule_period_invalid_speed_returns_422(client_and_mgr):
    client, _ = client_and_mgr
    payload = {"day": 0, "period": 1, "speed": 5, "end_h": 0, "end_m": 0}
    async with client as c:
        resp = await c.post("/api/command/schedule_period", json=payload)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_sync_rtc(client_and_mgr):
    client, mgr = client_and_mgr
    async with client as c:
        resp = await c.post("/api/command/sync_rtc")
    assert resp.status_code == 204
    mgr.sync_rtc.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_schedule_returns_8_days_4_periods(client_and_mgr):
    client, mgr = client_and_mgr
    async with client as c:
        resp = await c.get("/api/command/schedule")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["periods"]) == 8
    assert all(len(day) == 4 for day in body["periods"])
    assert body["periods"][0][0] == {"speed": 0, "end_h": 0, "end_m": 0}
    mgr.get_full_schedule.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_schedule_returns_503_when_disconnected():
    mgr = MagicMock()
    mgr.is_connected = False
    app.dependency_overrides[dependencies.get_device_manager] = lambda: mgr

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        resp = await c.get("/api/command/schedule")
    assert resp.status_code == 503
    app.dependency_overrides.clear()
