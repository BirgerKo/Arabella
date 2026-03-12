"""Device discovery and connection endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from webdashboard.backend.dependencies import get_device_manager
from webdashboard.backend.device_manager import DeviceManager
from webdashboard.backend.models import (
    ConnectRequest,
    DeviceStateResponse,
    DiscoveredDeviceResponse,
)

router = APIRouter(prefix="/api", tags=["devices"])


@router.get("/state", response_model=DeviceStateResponse)
async def get_state(manager: DeviceManager = Depends(get_device_manager)):
    """Return the current cached device state."""
    if not manager.is_connected:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                            detail="Not connected to any device")
    state = manager.current_state
    return DeviceStateResponse(
        connected=True,
        ip=state.ip,
        device_id=state.device_id,
        power=state.power,
        speed=state.speed,
        manual_speed=state.manual_speed,
        operation_mode=state.operation_mode,
        operation_mode_name=state.operation_mode_name,
        boost_active=state.boost_active,
        fan1_rpm=state.fan1_rpm,
        fan2_rpm=state.fan2_rpm,
        alarm_status=state.alarm_status,
        alarm_name=state.alarm_name,
    )


@router.get("/devices", response_model=list[DiscoveredDeviceResponse])
async def list_devices(manager: DeviceManager = Depends(get_device_manager)):
    """Trigger a UDP broadcast scan and return discovered devices."""
    devices = await manager.discover()
    return [
        DiscoveredDeviceResponse(
            ip=d.ip,
            device_id=d.device_id,
            unit_type=d.unit_type,
            unit_type_name=d.unit_type_name,
        )
        for d in devices
    ]


@router.post("/connect", response_model=DeviceStateResponse, status_code=status.HTTP_200_OK)
async def connect_device(
    body: ConnectRequest,
    manager: DeviceManager = Depends(get_device_manager),
):
    """Connect to a Vento device and return the initial state."""
    try:
        state = await manager.connect(body.ip, body.device_id, body.password)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY,
                            detail=str(exc)) from exc
    return DeviceStateResponse(
        connected=True,
        ip=state.ip,
        device_id=state.device_id,
        power=state.power,
        speed=state.speed,
        manual_speed=state.manual_speed,
        operation_mode=state.operation_mode,
        operation_mode_name=state.operation_mode_name,
        boost_active=state.boost_active,
        fan1_rpm=state.fan1_rpm,
        fan2_rpm=state.fan2_rpm,
        alarm_status=state.alarm_status,
        alarm_name=state.alarm_name,
    )


@router.delete("/connect", status_code=status.HTTP_204_NO_CONTENT)
async def disconnect_device(manager: DeviceManager = Depends(get_device_manager)):
    """Disconnect the current device."""
    manager.disconnect()
