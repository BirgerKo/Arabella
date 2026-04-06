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

class HumiditySensorRequest(BaseModel):
    # 0 = Off, 1 = On, 2 = Invert
    sensor: int = Field(..., ge=0, le=2)


class HumidityThresholdRequest(BaseModel):
    # Relative humidity percent: valid range 40–80
    threshold: int = Field(..., ge=40, le=80)


class EnableScheduleRequest(BaseModel):
    enabled: bool


class SchedulePeriodRequest(BaseModel):
    # Day group: 0=Weekdays, 1=Mon … 7=Sun
    day: int = Field(..., ge=0, le=7)
    # Period within the day (1–4)
    period: int = Field(..., ge=1, le=4)
    # Speed: 0=Standby, 1=Speed 1, 2=Speed 2, 3=Speed 3
    speed: int = Field(..., ge=0, le=3)
    end_h: int = Field(..., ge=0, le=23)
    end_m: int = Field(..., ge=0, le=59)


class SchedulePeriodData(BaseModel):
    speed: int
    end_h: int
    end_m: int


class ScheduleResponse(BaseModel):
    # Outer list: 8 day groups (0=Weekdays, 1=Mon … 7=Sun).
    # Inner list: 4 periods per day group.
    periods: list[list[SchedulePeriodData]]


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
    humidity_sensor: Optional[int] = None
    humidity_threshold: Optional[int] = None
    current_humidity: Optional[int] = None
    fan1_rpm: Optional[int]
    fan2_rpm: Optional[int]
    alarm_status: Optional[int]
    alarm_name: str
    weekly_schedule_enabled: Optional[bool] = None
    rtc_time: Optional[str] = None
    rtc_calendar: Optional[str] = None


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
