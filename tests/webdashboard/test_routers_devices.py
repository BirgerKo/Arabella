"""Integration tests for device discovery and connection endpoints."""
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from blauberg_vento.models import DeviceState, DiscoveredDevice
from webdashboard.backend import dependencies
from webdashboard.backend.main import app


def _make_state(ip: str = "10.0.0.1", device_id: str = "VENT-01", speed: int = 2) -> DeviceState:
    return DeviceState(
        ip=ip,
        device_id=device_id,
        power=True,
        speed=speed,
        manual_speed=None,
        operation_mode=0,
        boost_active=False,
        fan1_rpm=1200,
        fan2_rpm=1100,
        alarm_status=0,
    )


def _make_connected_manager(state: DeviceState) -> MagicMock:
    mgr = MagicMock()
    mgr.is_connected = True
    mgr.current_state = state
    mgr.connect = AsyncMock(return_value=state)
    mgr.disconnect = MagicMock()
    mgr.discover = AsyncMock(return_value=[])
    return mgr


def _make_disconnected_manager() -> MagicMock:
    mgr = MagicMock()
    mgr.is_connected = False
    mgr.current_state = None
    mgr.connect = AsyncMock()
    mgr.disconnect = MagicMock()
    mgr.discover = AsyncMock(return_value=[])
    return mgr


@pytest.fixture(autouse=True)
def clear_overrides():
    yield
    app.dependency_overrides.clear()


# ── GET /api/state ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_state_returns_200_when_connected():
    state = _make_state()
    mgr = _make_connected_manager(state)
    app.dependency_overrides[dependencies.get_device_manager] = lambda: mgr

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.get("/api/state")

    assert resp.status_code == 200
    body = resp.json()
    assert body["connected"] is True
    assert body["ip"] == "10.0.0.1"
    assert body["device_id"] == "VENT-01"


@pytest.mark.asyncio
async def test_get_state_returns_503_when_disconnected():
    mgr = _make_disconnected_manager()
    app.dependency_overrides[dependencies.get_device_manager] = lambda: mgr

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.get("/api/state")

    assert resp.status_code == 503


# ── POST /api/connect ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_connect_returns_device_state():
    state = _make_state()
    mgr = _make_disconnected_manager()
    mgr.connect = AsyncMock(return_value=state)
    app.dependency_overrides[dependencies.get_device_manager] = lambda: mgr

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.post("/api/connect", json={"ip": "10.0.0.1", "device_id": "VENT-01"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["connected"] is True
    assert body["device_id"] == "VENT-01"
    mgr.connect.assert_awaited_once_with("10.0.0.1", "VENT-01", "1111")


@pytest.mark.asyncio
async def test_connect_uses_provided_password():
    state = _make_state()
    mgr = _make_disconnected_manager()
    mgr.connect = AsyncMock(return_value=state)
    app.dependency_overrides[dependencies.get_device_manager] = lambda: mgr

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.post("/api/connect", json={"ip": "10.0.0.1", "device_id": "VENT-01", "password": "secret"})

    assert resp.status_code == 200
    mgr.connect.assert_awaited_once_with("10.0.0.1", "VENT-01", "secret")


@pytest.mark.asyncio
async def test_connect_returns_502_on_connection_error():
    mgr = _make_disconnected_manager()
    mgr.connect = AsyncMock(side_effect=Exception("Timeout"))
    app.dependency_overrides[dependencies.get_device_manager] = lambda: mgr

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.post("/api/connect", json={"ip": "10.0.0.99", "device_id": "DEAD"})

    assert resp.status_code == 502
    assert "Timeout" in resp.json()["detail"]


# ── Fan switching via POST /api/connect ────────────────────────────────────────

@pytest.mark.asyncio
async def test_switch_fan_returns_new_device_state():
    """POST /api/connect a second time must return the new device's state, not the old one."""
    state_a = _make_state(ip="10.0.0.1", device_id="FAN-A", speed=1)
    state_b = _make_state(ip="10.0.0.2", device_id="FAN-B", speed=3)

    connect_calls: list[tuple] = []

    async def fake_connect(ip: str, device_id: str, password: str = "1111") -> DeviceState:
        connect_calls.append((ip, device_id))
        return state_a if device_id == "FAN-A" else state_b

    mgr = MagicMock()
    mgr.is_connected = True
    mgr.connect = fake_connect
    app.dependency_overrides[dependencies.get_device_manager] = lambda: mgr

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp_a = await c.post("/api/connect", json={"ip": "10.0.0.1", "device_id": "FAN-A"})
        resp_b = await c.post("/api/connect", json={"ip": "10.0.0.2", "device_id": "FAN-B"})

    assert resp_a.status_code == 200
    assert resp_a.json()["device_id"] == "FAN-A"
    assert resp_a.json()["speed"] == 1

    assert resp_b.status_code == 200
    assert resp_b.json()["device_id"] == "FAN-B"
    assert resp_b.json()["speed"] == 3
    assert resp_b.json()["ip"] == "10.0.0.2"

    assert connect_calls == [("10.0.0.1", "FAN-A"), ("10.0.0.2", "FAN-B")]


@pytest.mark.asyncio
async def test_switch_fan_connect_called_with_correct_credentials():
    """Each call to POST /api/connect forwards the exact credentials to the manager."""
    state = _make_state()
    mgr = _make_disconnected_manager()
    mgr.connect = AsyncMock(return_value=state)
    app.dependency_overrides[dependencies.get_device_manager] = lambda: mgr

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        await c.post("/api/connect", json={"ip": "10.0.0.1", "device_id": "FAN-A", "password": "pw1"})
        await c.post("/api/connect", json={"ip": "10.0.0.2", "device_id": "FAN-B", "password": "pw2"})

    assert mgr.connect.await_count == 2
    mgr.connect.assert_any_await("10.0.0.1", "FAN-A", "pw1")
    mgr.connect.assert_any_await("10.0.0.2", "FAN-B", "pw2")


# ── DELETE /api/connect ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_disconnect_returns_204():
    mgr = _make_connected_manager(_make_state())
    app.dependency_overrides[dependencies.get_device_manager] = lambda: mgr

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.delete("/api/connect")

    assert resp.status_code == 204
    mgr.disconnect.assert_called_once()


# ── GET /api/devices ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_devices_returns_discovered():
    devices = [
        DiscoveredDevice(ip="192.168.1.10", device_id="FAN-01", unit_type=3),
        DiscoveredDevice(ip="192.168.1.11", device_id="FAN-02", unit_type=5),
    ]
    mgr = _make_disconnected_manager()
    mgr.discover = AsyncMock(return_value=devices)
    app.dependency_overrides[dependencies.get_device_manager] = lambda: mgr

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.get("/api/devices")

    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 2
    assert body[0]["device_id"] == "FAN-01"
    assert body[1]["ip"] == "192.168.1.11"


@pytest.mark.asyncio
async def test_list_devices_returns_empty_list_when_none_found():
    mgr = _make_disconnected_manager()
    mgr.discover = AsyncMock(return_value=[])
    app.dependency_overrides[dependencies.get_device_manager] = lambda: mgr

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.get("/api/devices")

    assert resp.status_code == 200
    assert resp.json() == []
