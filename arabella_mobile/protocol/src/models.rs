use std::collections::HashMap;

#[derive(Debug, Default, Clone)]
pub struct FirmwareVersion {
    pub major: u8,
    pub minor: u8,
    pub day: u8,
    pub month: u8,
    pub year: u16,
}

#[derive(Debug, Default, Clone)]
pub struct RtcTime {
    pub hours: u8,
    pub minutes: u8,
    pub seconds: u8,
}

#[derive(Debug, Default, Clone)]
pub struct RtcCalendar {
    pub year: u16,
    pub month: u8,
    pub day: u8,
    pub day_of_week: u8,
}

#[derive(Debug, Default, Clone)]
pub struct TimerCountdown {
    pub hours: u8,
    pub minutes: u8,
    pub seconds: u8,
}

impl TimerCountdown {
    pub fn total_seconds(&self) -> u32 {
        self.hours as u32 * 3600 + self.minutes as u32 * 60 + self.seconds as u32
    }
}

#[derive(Debug, Default, Clone)]
pub struct FilterCountdown {
    pub days: u8,
    pub hours: u8,
    pub minutes: u8,
}

#[derive(Debug, Default, Clone)]
pub struct MachineHours {
    pub days: u16,
    pub hours: u8,
    pub minutes: u8,
}

impl MachineHours {
    pub fn total_hours(&self) -> f64 {
        self.days as f64 * 24.0 + self.hours as f64 + self.minutes as f64 / 60.0
    }
}

#[derive(Debug, Default, Clone)]
pub struct SchedulePeriod {
    pub period_number: u8,
    pub end_hours: u8,
    pub end_minutes: u8,
    pub speed: u8,
}

#[derive(Debug, Default, Clone)]
pub struct WifiConfig {
    pub mode: u8,
    pub ssid: String,
    pub encryption: u8,
    pub channel: u8,
    pub dhcp: bool,
    pub ip: String,
    pub subnet: String,
    pub gateway: String,
    pub current_ip: String,
}

/// Datetime value passed to set_rtc — caller provides current local time.
#[derive(Debug, Clone)]
pub struct SetRtcTime {
    pub year: u16,
    pub month: u8,
    pub day: u8,
    /// 1 = Monday, 7 = Sunday (ISO weekday)
    pub day_of_week: u8,
    pub hour: u8,
    pub minute: u8,
    pub second: u8,
}

#[derive(Debug, Default, Clone)]
pub struct DeviceState {
    pub ip: String,
    pub device_id: String,
    pub unit_type: u16,
    pub power: Option<bool>,
    pub speed: Option<u8>,
    pub manual_speed: Option<u8>,
    pub operation_mode: Option<u8>,
    pub boost_active: Option<bool>,
    pub boost_delay_minutes: Option<u8>,
    pub timer_mode: Option<u8>,
    pub timer_countdown: Option<TimerCountdown>,
    pub night_timer: Option<(u8, u8)>,
    pub party_timer: Option<(u8, u8)>,
    pub humidity_sensor: Option<u8>,
    pub humidity_threshold: Option<u8>,
    pub current_humidity: Option<u8>,
    pub humidity_status: Option<bool>,
    pub relay_sensor: Option<u8>,
    pub relay_state: Option<bool>,
    pub voltage_sensor: Option<u8>,
    pub voltage_threshold: Option<u8>,
    pub voltage_sensor_value: Option<u8>,
    pub voltage_status: Option<bool>,
    pub fan1_rpm: Option<u16>,
    pub fan2_rpm: Option<u16>,
    pub filter_countdown: Option<FilterCountdown>,
    pub filter_needs_replacement: Option<bool>,
    pub alarm_status: Option<u8>,
    pub machine_hours: Option<MachineHours>,
    pub battery_voltage_mv: Option<u16>,
    pub firmware: Option<FirmwareVersion>,
    pub rtc_time: Option<RtcTime>,
    pub rtc_calendar: Option<RtcCalendar>,
    pub weekly_schedule_enabled: Option<bool>,
    pub schedule: HashMap<(u8, u8), SchedulePeriod>,
    pub wifi: Option<WifiConfig>,
    pub cloud_permitted: Option<bool>,
}

impl DeviceState {
    pub fn unit_type_name(&self) -> &'static str {
        match self.unit_type {
            3 => "Vento Expert A50-1/A85-1/A100-1 W V.2",
            4 => "Vento Expert Duo A30-1 W V.2",
            5 => "Vento Expert A30 W V.2",
            _ => "Unknown",
        }
    }

    pub fn is_a30(&self) -> bool {
        self.unit_type == 5
    }

    pub fn operation_mode_name(&self) -> &'static str {
        match self.operation_mode {
            Some(0) => "Ventilation",
            Some(1) => "Heat Recovery",
            Some(2) => "Supply",
            _ => "Unknown",
        }
    }
}

#[derive(Debug, Clone)]
pub struct DiscoveredDevice {
    pub ip: String,
    pub device_id: String,
    pub unit_type: u16,
    pub unit_type_name: String,
}

impl DiscoveredDevice {
    pub fn new(ip: String, device_id: String, unit_type: u16) -> Self {
        let unit_type_name = match unit_type {
            3 => "Vento Expert A50-1/A85-1/A100-1 W V.2".to_string(),
            4 => "Vento Expert Duo A30-1 W V.2".to_string(),
            5 => "Vento Expert A30 W V.2".to_string(),
            n => format!("Unknown ({n})"),
        };
        DiscoveredDevice { ip, device_id, unit_type, unit_type_name }
    }
}
