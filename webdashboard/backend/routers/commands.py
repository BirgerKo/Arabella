"""Fan command endpoints (power, speed, mode, boost)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from webdashboard.backend.dependencies import get_device_manager
from webdashboard.backend.device_manager import DeviceManager
from webdashboard.backend.models import BoostRequest, ModeRequest, PowerRequest, SpeedRequest

router = APIRouter(prefix="/api/command", tags=["commands"])


def _require_connected(manager: DeviceManager) -> None:
    if not manager.is_connected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Not connected to any device",
        )


@router.post("/power", status_code=status.HTTP_204_NO_CONTENT)
async def set_power(
    body: PowerRequest,
    manager: DeviceManager = Depends(get_device_manager),
):
    _require_connected(manager)
    try:
        await manager.set_power(body.on)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc


@router.post("/speed", status_code=status.HTTP_204_NO_CONTENT)
async def set_speed(
    body: SpeedRequest,
    manager: DeviceManager = Depends(get_device_manager),
):
    _require_connected(manager)
    try:
        await manager.set_speed(body.speed)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc


@router.post("/mode", status_code=status.HTTP_204_NO_CONTENT)
async def set_mode(
    body: ModeRequest,
    manager: DeviceManager = Depends(get_device_manager),
):
    _require_connected(manager)
    try:
        await manager.set_mode(body.mode)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc


@router.post("/boost", status_code=status.HTTP_204_NO_CONTENT)
async def set_boost(
    body: BoostRequest,
    manager: DeviceManager = Depends(get_device_manager),
):
    _require_connected(manager)
    try:
        await manager.set_boost(body.on)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
