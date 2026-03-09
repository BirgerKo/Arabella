from __future__ import annotations
from dataclasses import dataclass, field

@dataclass
class FirmwareVersion:
    major: int; minor: int; day: int; month: int; year: int
    def __str__(self): return f"{self.major}.{self.minor} ({self.year}-{self.month:02d}-{self.day:02d})"

@dataclass
class RtcTime:
    hours: int; minutes: int; seconds: int
    def __str__(self): return f"{self.hours:02d}:{self.minutes:02d}:{self.seconds:02d}"

@dataclass
class RtcCalendar:
    year: int; month: int; day: int; day_of_week: int
    def __str__(self):
        days = ['Mon','Tue','Wed','Thu','Fri','Sat','Sun']
        dow = days[self.day_of_week-1] if 1 <= self.day_of_week <= 7 else '?'
        return f"{self.year}-{self.month:02d}-{self.day:02d} ({dow})"

@dataclass
class TimerCountdown:
    hours: int; minutes: int; seconds: int
    def total_seconds(self): return self.hours*3600+self.minutes*60+self.seconds
    def __str__(self): return f"{self.hours:02d}:{self.minutes:02d}:{self.seconds:02d}"

@dataclass
class FilterCountdown:
    days: int; hours: int; minutes: int
    def __str__(self): return f"{self.days}d {self.hours:02d}h {self.minutes:02d}m"

@dataclass
class MachineHours:
    days: int; hours: int; minutes: int
    def total_hours(self): return self.days*24+self.hours+self.minutes/60
    def __str__(self): return f"{self.days}d {self.hours:02d}h {self.minutes:02d}m"

@dataclass
class SchedulePeriod:
    period_number: int; end_hours: int; end_minutes: int; speed: int
    def __str__(self):
        spd = ['Standby','Speed 1','Speed 2','Speed 3']
        s = spd[self.speed] if 0 <= self.speed <= 3 else str(self.speed)
        return f"Period {self.period_number}: -> {self.end_hours:02d}:{self.end_minutes:02d} @ {s}"

@dataclass
class WifiConfig:
    mode: int; ssid: str; encryption: int; channel: int
    dhcp: bool; ip: str; subnet: str; gateway: str; current_ip: str
    @property
    def mode_name(self): return {1:'Client',2:'Access Point'}.get(self.mode,'Unknown')
    @property
    def encryption_name(self): return {48:'OPEN',50:'WPA_PSK',51:'WPA2_PSK',52:'WPA_WPA2_PSK'}.get(self.encryption,'Unknown')

UNIT_TYPE_NAMES = {3:'Vento Expert A50-1/A85-1/A100-1 W V.2', 4:'Vento Expert Duo A30-1 W V.2', 5:'Vento Expert A30 W V.2'}
UNIT_TYPE_IS_A30 = {3:False, 4:False, 5:True}

@dataclass
class DeviceState:
    ip: str = ''; device_id: str = ''; unit_type: int = 0
    power: bool|None = None; speed: int|None = None
    manual_speed: int|None = None; operation_mode: int|None = None
    boost_active: bool|None = None; boost_delay_minutes: int|None = None
    timer_mode: int|None = None; timer_countdown: object = None
    night_timer: tuple|None = None; party_timer: tuple|None = None
    humidity_sensor: int|None = None; humidity_threshold: int|None = None
    current_humidity: int|None = None; humidity_status: bool|None = None
    relay_sensor: int|None = None; relay_state: bool|None = None
    voltage_sensor: int|None = None; voltage_threshold: int|None = None
    voltage_sensor_value: int|None = None; voltage_status: bool|None = None
    fan1_rpm: int|None = None; fan2_rpm: int|None = None
    filter_countdown: object = None; filter_needs_replacement: bool|None = None
    alarm_status: int|None = None; machine_hours: object = None
    battery_voltage_mv: int|None = None; firmware: object = None
    rtc_time: object = None; rtc_calendar: object = None
    weekly_schedule_enabled: bool|None = None
    schedule: dict = field(default_factory=dict)
    wifi: object = None; cloud_permitted: bool|None = None

    @property
    def unit_type_name(self): return UNIT_TYPE_NAMES.get(self.unit_type, f'Unknown ({self.unit_type})')
    @property
    def is_a30(self): return UNIT_TYPE_IS_A30.get(self.unit_type, False)
    @property
    def operation_mode_name(self): return {0:'Ventilation',1:'Heat Recovery',2:'Supply'}.get(self.operation_mode,'Unknown')
    @property
    def speed_name(self):
        if self.speed == 255: return f'Manual ({self.manual_speed})'
        return {1:'Speed 1',2:'Speed 2',3:'Speed 3'}.get(self.speed,'Unknown')
    @property
    def alarm_name(self): return {0:'OK',1:'Alarm',2:'Warning'}.get(self.alarm_status,'Unknown')
    def __repr__(self):
        return (f"<DeviceState ip={self.ip!r} id={self.device_id!r} type={self.unit_type_name!r} "
                f"power={'ON' if self.power else 'OFF'} speed={self.speed_name} mode={self.operation_mode_name}>")

@dataclass
class DiscoveredDevice:
    ip: str; device_id: str; unit_type: int; unit_type_name: str = ''
    def __post_init__(self):
        if not self.unit_type_name:
            self.unit_type_name = UNIT_TYPE_NAMES.get(self.unit_type, f'Unknown ({self.unit_type})')
    def __repr__(self):
        return f"<DiscoveredDevice ip={self.ip!r} id={self.device_id!r} type={self.unit_type_name!r}>"
