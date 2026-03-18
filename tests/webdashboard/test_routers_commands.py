"""Integration tests for command endpoints via the FastAPI test client."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from webdashboard.backend.main import app
from webdashboard.backend import dependencies


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
