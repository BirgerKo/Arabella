"""Scenario CRUD and apply endpoints.

Reuses ventocontrol.scenarios.ScenarioStore which has no Qt dependencies.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from ventocontrol.scenarios import (
    FanSettings,
    ScenarioEntry,
    ScenarioSettings,
    ScenarioStore,
    get_settings_for_device,
)
from webdashboard.backend.dependencies import get_device_manager, get_scenario_store
from webdashboard.backend.device_manager import DeviceManager
from webdashboard.backend.models import (
    FanSettingsModel,
    QuickSlotsRequest,
    QuickSlotsResponse,
    SaveScenarioRequest,
    ScenarioResponse,
    ScenarioSettingsModel,
    UpdateScenarioRequest,
)

router = APIRouter(prefix="/api/scenarios", tags=["scenarios"])


def _entry_to_response(entry: ScenarioEntry) -> ScenarioResponse:
    fans = [
        FanSettingsModel(
            device_id=f.device_id,
            settings=ScenarioSettingsModel(
                power=f.settings.power,
                speed=f.settings.speed,
                manual_speed=f.settings.manual_speed,
                operation_mode=f.settings.operation_mode,
                boost_active=f.settings.boost_active,
                humidity_sensor=f.settings.humidity_sensor,
                humidity_threshold=f.settings.humidity_threshold,
            ),
        )
        for f in entry.fans
    ]
    return ScenarioResponse(name=entry.name, fans=fans)


@router.get("", response_model=list[ScenarioResponse])
def list_scenarios(store: ScenarioStore = Depends(get_scenario_store)):
    return [_entry_to_response(e) for e in store.get_scenarios()]


@router.post("", response_model=ScenarioResponse, status_code=status.HTTP_201_CREATED)
async def save_scenario(
    body: SaveScenarioRequest,
    manager: DeviceManager = Depends(get_device_manager),
    store: ScenarioStore = Depends(get_scenario_store),
):
    """Save the current device state as a new scenario."""
    if not manager.is_connected:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                            detail="Not connected to any device")
    state = manager.current_state
    settings = ScenarioSettings(
        power=state.power,
        speed=state.speed,
        manual_speed=state.manual_speed,
        operation_mode=state.operation_mode,
        boost_active=state.boost_active,
        humidity_sensor=state.humidity_sensor,
        humidity_threshold=state.humidity_threshold,
    )
    entry = ScenarioEntry(
        name=body.name,
        fans=[FanSettings(device_id=state.device_id, settings=settings)],
    )
    store.save_scenario(entry)
    return _entry_to_response(entry)


@router.put("/{name}", response_model=ScenarioResponse)
def update_scenario(
    name: str,
    body: UpdateScenarioRequest,
    store: ScenarioStore = Depends(get_scenario_store),
):
    """Rename a scenario."""
    scenarios = store.get_scenarios()
    entry = next((s for s in scenarios if s.name == name), None)
    if entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scenario not found")
    if body.name and body.name != name:
        store.delete_scenario(name)
        entry.name = body.name
        store.save_scenario(entry)
    return _entry_to_response(entry)


@router.delete("/{name}", status_code=status.HTTP_204_NO_CONTENT)
def delete_scenario(name: str, store: ScenarioStore = Depends(get_scenario_store)):
    scenarios = store.get_scenarios()
    if not any(s.name == name for s in scenarios):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scenario not found")
    store.delete_scenario(name)


@router.post("/{name}/apply", status_code=status.HTTP_204_NO_CONTENT)
async def apply_scenario(
    name: str,
    manager: DeviceManager = Depends(get_device_manager),
    store: ScenarioStore = Depends(get_scenario_store),
):
    """Apply a saved scenario to the connected device."""
    if not manager.is_connected:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                            detail="Not connected to any device")
    scenarios = store.get_scenarios()
    entry = next((s for s in scenarios if s.name == name), None)
    if entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scenario not found")

    device_id = manager.current_state.device_id
    settings = get_settings_for_device(entry, device_id)
    if settings is None:
        # No per-device settings; apply first fan's settings
        if not entry.fans:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                                detail="Scenario has no fan settings")
        settings = entry.fans[0].settings

    try:
        if settings.power is not None:
            await manager.set_power(settings.power)
        if settings.speed is not None:
            speed_val = settings.manual_speed if settings.speed == 255 else settings.speed
            if speed_val is not None:
                await manager.set_speed(speed_val)
        if settings.operation_mode is not None:
            await manager.set_mode(settings.operation_mode)
        if settings.boost_active is not None:
            await manager.set_boost(settings.boost_active)
        if settings.humidity_sensor is not None:
            await manager.set_humidity_sensor(settings.humidity_sensor)
        if settings.humidity_threshold is not None:
            await manager.set_humidity_threshold(settings.humidity_threshold)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc


@router.post("/{name}/add-fan", status_code=status.HTTP_204_NO_CONTENT)
async def add_fan_to_scenario(
    name: str,
    manager: DeviceManager = Depends(get_device_manager),
    store: ScenarioStore = Depends(get_scenario_store),
):
    """Merge the current fan's state into an existing scenario (adds or replaces)."""
    if not manager.is_connected:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                            detail="Not connected to any device")
    scenarios = store.get_scenarios()
    entry = next((s for s in scenarios if s.name == name), None)
    if entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scenario not found")
    state = manager.current_state
    new_fan = FanSettings(
        device_id=state.device_id,
        settings=ScenarioSettings(
            power=state.power,
            speed=state.speed,
            manual_speed=state.manual_speed,
            operation_mode=state.operation_mode,
            boost_active=state.boost_active,
            humidity_sensor=state.humidity_sensor,
            humidity_threshold=state.humidity_threshold,
        ),
    )
    updated_fans = [f for f in entry.fans if f.device_id != state.device_id]
    updated_fans.append(new_fan)
    store.save_scenario(ScenarioEntry(name=entry.name, fans=updated_fans))


@router.get("/quick-slots/{device_id}", response_model=QuickSlotsResponse)
def get_quick_slots(device_id: str, store: ScenarioStore = Depends(get_scenario_store)):
    return QuickSlotsResponse(device_id=device_id, slots=store.get_quick_slots(device_id))


@router.put("/quick-slots/{device_id}", response_model=QuickSlotsResponse)
def set_quick_slots(
    device_id: str,
    body: QuickSlotsRequest,
    store: ScenarioStore = Depends(get_scenario_store),
):
    store.set_quick_slots(device_id, body.slots)
    return QuickSlotsResponse(device_id=device_id, slots=store.get_quick_slots(device_id))
