"""Integration tests for scenario endpoints."""
import pytest
from unittest.mock import MagicMock, AsyncMock
from httpx import ASGITransport, AsyncClient

from ventocontrol.scenarios import ScenarioEntry, FanSettings, ScenarioSettings, ScenarioStore
from webdashboard.backend.main import app
from webdashboard.backend import dependencies
from blauberg_vento.models import DeviceState


def make_store_with(scenarios):
    store = MagicMock(spec=ScenarioStore)
    store.get_scenarios.return_value = scenarios
    store.save_scenario = MagicMock()
    store.delete_scenario = MagicMock()
    store.get_quick_slots.return_value = [None, None, None]
    store.set_quick_slots = MagicMock()
    return store


def make_connected_manager(device_id="VENT-01"):
    state = DeviceState(ip="10.0.0.1", device_id=device_id, power=True, speed=2, operation_mode=0,
                        boost_active=False, alarm_status=0)
    mgr = MagicMock()
    mgr.is_connected = True
    mgr.current_state = state
    mgr.set_power  = AsyncMock()
    mgr.set_speed  = AsyncMock()
    mgr.set_mode   = AsyncMock()
    mgr.set_boost  = AsyncMock()
    return mgr


@pytest.fixture
def setup(tmp_path):
    """Returns (AsyncClient, store, manager) with overrides applied."""
    entry = ScenarioEntry(
        name="Night",
        fans=[FanSettings(device_id="VENT-01",
                          settings=ScenarioSettings(power=True, speed=1, operation_mode=0))]
    )
    store = make_store_with([entry])
    mgr   = make_connected_manager()

    app.dependency_overrides[dependencies.get_scenario_store] = lambda: store
    app.dependency_overrides[dependencies.get_device_manager] = lambda: mgr

    transport = ASGITransport(app=app)
    client = AsyncClient(transport=transport, base_url="http://test")
    yield client, store, mgr
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_list_scenarios(setup):
    client, store, _ = setup
    async with client as c:
        resp = await c.get("/api/scenarios")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["name"] == "Night"


@pytest.mark.asyncio
async def test_save_scenario(setup):
    client, store, _ = setup
    async with client as c:
        resp = await c.post("/api/scenarios", json={"name": "Morning"})
    assert resp.status_code == 201
    store.save_scenario.assert_called_once()


@pytest.mark.asyncio
async def test_delete_scenario(setup):
    client, store, _ = setup
    async with client as c:
        resp = await c.delete("/api/scenarios/Night")
    assert resp.status_code == 204
    store.delete_scenario.assert_called_once_with("Night")


@pytest.mark.asyncio
async def test_delete_nonexistent_returns_404(setup):
    client, store, _ = setup
    store.get_scenarios.return_value = []
    async with client as c:
        resp = await c.delete("/api/scenarios/Missing")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_apply_scenario(setup):
    client, store, mgr = setup
    async with client as c:
        resp = await c.post("/api/scenarios/Night/apply")
    assert resp.status_code == 204
    # At least power and mode should have been called
    mgr.set_power.assert_awaited()


@pytest.mark.asyncio
async def test_apply_scenario_not_found(setup):
    client, store, _ = setup
    store.get_scenarios.return_value = []
    async with client as c:
        resp = await c.post("/api/scenarios/Missing/apply")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_quick_slots(setup):
    client, store, mgr = setup
    async with client as c:
        resp = await c.get("/api/scenarios/quick-slots/VENT-01")
    assert resp.status_code == 200
    data = resp.json()
    assert data["device_id"] == "VENT-01"
    assert len(data["slots"]) == 3


@pytest.mark.asyncio
async def test_set_quick_slots(setup):
    client, store, mgr = setup
    async with client as c:
        resp = await c.put("/api/scenarios/quick-slots/VENT-01",
                           json={"slots": ["Night", None, None]})
    assert resp.status_code == 200
    store.set_quick_slots.assert_called_once_with("VENT-01", ["Night", None, None])
