"""Pydantic request and response schemas for the web API."""
from __future__ import annotations

from pydantic import BaseModel, Field

# ── Request bodies ────────────────────────────────────────────────────────────

class ConnectRequest(BaseModel):
    ip: str = Field(..., min_length=1, max_length=255)
    device_id: str = Field(..., min_length=16, max_length=16)
    password: str = Field("1111", min_length=1, max_length=8)


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
    name: str | None = Field(None, min_length=1, max_length=30)


class QuickSlotsRequest(BaseModel):
    # 3-element list; each element is a scenario name or null
    slots: list[str | None] = Field(..., min_length=3, max_length=3)


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
    power: bool | None
    speed: int | None
    manual_speed: int | None
    operation_mode: int | None
    operation_mode_name: str
    boost_active: bool | None
    humidity_sensor: int | None = None
    humidity_threshold: int | None = None
    current_humidity: int | None = None
    fan1_rpm: int | None
    fan2_rpm: int | None
    alarm_status: int | None
    alarm_name: str
    weekly_schedule_enabled: bool | None = None
    rtc_time: str | None = None
    rtc_calendar: str | None = None


class DiscoveredDeviceResponse(BaseModel):
    ip: str
    device_id: str
    unit_type: int
    unit_type_name: str


class ScenarioSettingsModel(BaseModel):
    power: bool | None = None
    speed: int | None = None
    manual_speed: int | None = None
    operation_mode: int | None = None
    boost_active: bool | None = None
    humidity_sensor: int | None = None
    humidity_threshold: int | None = None


class FanSettingsModel(BaseModel):
    device_id: str
    settings: ScenarioSettingsModel


class ScenarioResponse(BaseModel):
    name: str
    fans: list[FanSettingsModel]


class QuickSlotsResponse(BaseModel):
    device_id: str
    slots: list[str | None]


class ErrorResponse(BaseModel):
    detail: str
