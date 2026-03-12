"""Pydantic request and response schemas for the web API."""
from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field


# ── Request bodies ────────────────────────────────────────────────────────────

class ConnectRequest(BaseModel):
    ip: str
    device_id: str
    password: str = "1111"


class PowerRequest(BaseModel):
    on: bool


class SpeedRequest(BaseModel):
    # 1/2/3 for presets; 0-255 for manual (speed=255 activates manual_speed)
    speed: int = Field(..., ge=0, le=255)


class ModeRequest(BaseModel):
    # 0 = Ventilation, 1 = Heat Recovery, 2 = Supply
    mode: int = Field(..., ge=0, le=2)


class BoostRequest(BaseModel):
    on: bool


class SaveScenarioRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=30)
    # device_id and current state are captured server-side


class UpdateScenarioRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=30)


class QuickSlotsRequest(BaseModel):
    # 3-element list; each element is a scenario name or null
    slots: list[Optional[str]] = Field(..., min_length=3, max_length=3)


# ── Response models ───────────────────────────────────────────────────────────

class DeviceStateResponse(BaseModel):
    connected: bool
    ip: str
    device_id: str
    power: Optional[bool]
    speed: Optional[int]
    manual_speed: Optional[int]
    operation_mode: Optional[int]
    operation_mode_name: str
    boost_active: Optional[bool]
    fan1_rpm: Optional[int]
    fan2_rpm: Optional[int]
    alarm_status: Optional[int]
    alarm_name: str


class DiscoveredDeviceResponse(BaseModel):
    ip: str
    device_id: str
    unit_type: int
    unit_type_name: str


class ScenarioSettingsModel(BaseModel):
    power: Optional[bool] = None
    speed: Optional[int] = None
    manual_speed: Optional[int] = None
    operation_mode: Optional[int] = None
    boost_active: Optional[bool] = None
    humidity_sensor: Optional[int] = None
    humidity_threshold: Optional[int] = None


class FanSettingsModel(BaseModel):
    device_id: str
    settings: ScenarioSettingsModel


class ScenarioResponse(BaseModel):
    name: str
    fans: list[FanSettingsModel]


class QuickSlotsResponse(BaseModel):
    device_id: str
    slots: list[Optional[str]]


class ErrorResponse(BaseModel):
    detail: str
