"""Fan command endpoints (power, speed, mode, boost)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from webdashboard.backend.dependencies import get_device_manager
from webdashboard.backend.device_manager import DeviceManager
from webdashboard.backend.models import (
    BoostRequest, EnableScheduleRequest, HumiditySensorRequest,
    HumidityThresholdRequest, ModeRequest, PowerRequest,
    SchedulePeriodData, SchedulePeriodRequest, ScheduleResponse, SpeedRequest,
)

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


@router.post("/humidity_sensor", status_code=status.HTTP_204_NO_CONTENT)
async def set_humidity_sensor(
    body: HumiditySensorRequest,
    manager: DeviceManager = Depends(get_device_manager),
):
    _require_connected(manager)
    try:
        await manager.set_humidity_sensor(body.sensor)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc


@router.post("/humidity_threshold", status_code=status.HTTP_204_NO_CONTENT)
async def set_humidity_threshold(
    body: HumidityThresholdRequest,
    manager: DeviceManager = Depends(get_device_manager),
):
    _require_connected(manager)
    try:
        await manager.set_humidity_threshold(body.threshold)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc


@router.post("/schedule_enable", status_code=status.HTTP_204_NO_CONTENT)
async def set_schedule_enable(
    body: EnableScheduleRequest,
    manager: DeviceManager = Depends(get_device_manager),
):
    _require_connected(manager)
    try:
        await manager.enable_schedule(body.enabled)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc


@router.post("/schedule_period", status_code=status.HTTP_204_NO_CONTENT)
async def set_schedule_period(
    body: SchedulePeriodRequest,
    manager: DeviceManager = Depends(get_device_manager),
):
    _require_connected(manager)
    try:
        await manager.set_schedule_period(body.day, body.period, body.speed, body.end_h, body.end_m)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc


@router.get("/schedule", response_model=ScheduleResponse)
async def get_schedule(
    manager: DeviceManager = Depends(get_device_manager),
):
    """Return all 32 schedule periods (8 day groups × 4 periods) from the device."""
    _require_connected(manager)
    try:
        full = await manager.get_full_schedule()
        return ScheduleResponse(periods=[
            [SchedulePeriodData(speed=sp.speed, end_h=sp.end_hours, end_m=sp.end_minutes)
             for sp in row]
            for row in full
        ])
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc


@router.post("/sync_rtc", status_code=status.HTTP_204_NO_CONTENT)
async def sync_rtc(
    manager: DeviceManager = Depends(get_device_manager),
):
    _require_connected(manager)
    try:
        await manager.sync_rtc()
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
