use std::collections::HashMap;

use crate::error::{Result, VentoError};
use crate::models::{
    DeviceState, DiscoveredDevice, FilterCountdown, FirmwareVersion, MachineHours,
    RtcCalendar, RtcTime, SchedulePeriod, SetRtcTime, TimerCountdown, WifiConfig,
};
use crate::packet::{
    build_decrement, build_discovery, build_increment, build_read, build_write,
    build_write_resp, decode_filter_countdown, decode_firmware, decode_int, decode_ip,
    decode_machine_hours, decode_rtc_calendar, decode_rtc_time, decode_schedule, decode_text,
    decode_timer_countdown, encode_ip, parse_response,
};
use crate::param::{DEFAULT_PORT, Param, WriteParam};
use crate::transport::VentoTransport;

// ---------------------------------------------------------------------------
// Validation helpers
// ---------------------------------------------------------------------------

fn check_range(name: &str, value: i64, low: i64, high: i64) -> Result<()> {
    if !(low..=high).contains(&value) {
        return Err(VentoError::Value(format!(
            "{name} must be in [{low},{high}], got {value}"
        )));
    }
    Ok(())
}

fn check_choices(name: &str, value: u8, choices: &[u8]) -> Result<()> {
    if !choices.contains(&value) {
        return Err(VentoError::Value(format!(
            "{name} must be one of {choices:?}, got {value}"
        )));
    }
    Ok(())
}

// ---------------------------------------------------------------------------
// Polling parameter groups (mirrors client.py)
// ---------------------------------------------------------------------------

const BASIC_STATUS: &[Param] = &[
    Param::Power, Param::Speed, Param::BoostStatus, Param::TimerMode,
    Param::TimerCountdown, Param::HumiditySensor, Param::RelaySensor,
    Param::VoltageSensor, Param::HumidityThreshold, Param::VoltageThreshold,
    Param::BatteryVoltage, Param::CurrentHumidity, Param::VoltageSensorVal,
    Param::RelayState, Param::ManualSpeed, Param::Fan1Speed, Param::Fan2Speed,
];
const EXTENDED_CONFIG: &[Param] = &[
    Param::FilterCountdown, Param::FilterIndicator, Param::BoostDelay,
    Param::RtcTime, Param::RtcCalendar, Param::WeeklyScheduleEn,
    Param::DeviceSearch, Param::MachineHours, Param::AlarmStatus,
    Param::CloudPermission, Param::FirmwareVersion, Param::OperationMode, Param::UnitType,
];
const WIFI_PARAMS: &[Param] = &[
    Param::WifiMode, Param::WifiSsid, Param::WifiEncryption, Param::WifiChannel,
    Param::WifiDhcp, Param::WifiIp, Param::WifiSubnet, Param::WifiGateway, Param::WifiCurrentIp,
];
const SENSOR_STATUS: &[Param] = &[
    Param::HumidityStatus, Param::VoltageStatus, Param::NightTimer, Param::PartyTimer,
];

const ALL_PARAM_GROUPS: &[&[Param]] = &[BASIC_STATUS, EXTENDED_CONFIG, WIFI_PARAMS, SENSOR_STATUS];

// ---------------------------------------------------------------------------
// DeviceState builder
// ---------------------------------------------------------------------------

struct DeviceStateBuilder<'a> {
    raw: &'a HashMap<u16, Vec<u8>>,
    host: &'a str,
}

impl<'a> DeviceStateBuilder<'a> {
    fn int_field(&self, param: Param) -> Option<u64> {
        self.raw.get(&param.as_u16()).map(|v| decode_int(v))
    }

    fn bool_field(&self, param: Param) -> Option<bool> {
        self.int_field(param).map(|v| v != 0)
    }

    fn text_field(&self, param: Param) -> Option<String> {
        self.raw.get(&param.as_u16()).map(|v| decode_text(v))
    }

    fn ip_field(&self, param: Param) -> Option<String> {
        self.raw
            .get(&param.as_u16())
            .and_then(|v| decode_ip(v).ok())
    }

    fn bytes_field(&self, param: Param) -> Option<&[u8]> {
        self.raw.get(&param.as_u16()).map(|v| v.as_slice())
    }

    fn build(self) -> DeviceState {
        let mut state = DeviceState {
            ip: self.host.to_string(),
            ..Default::default()
        };
        self.populate_identity(&mut state);
        self.populate_power_and_speed(&mut state);
        self.populate_timers(&mut state);
        self.populate_sensors(&mut state);
        self.populate_fan_and_filter(&mut state);
        self.populate_maintenance(&mut state);
        self.populate_wifi(&mut state);
        state
    }

    fn populate_identity(&self, s: &mut DeviceState) {
        s.device_id = self.text_field(Param::DeviceSearch).unwrap_or_default();
        s.unit_type = self.int_field(Param::UnitType).unwrap_or(0) as u16;
    }

    fn populate_power_and_speed(&self, s: &mut DeviceState) {
        s.power = self.bool_field(Param::Power);
        s.speed = self.int_field(Param::Speed).map(|v| v as u8);
        s.manual_speed = self.int_field(Param::ManualSpeed).map(|v| v as u8);
        s.operation_mode = self.int_field(Param::OperationMode).map(|v| v as u8);
        s.boost_active = self.bool_field(Param::BoostStatus);
        s.boost_delay_minutes = self.int_field(Param::BoostDelay).map(|v| v as u8);
    }

    fn populate_timers(&self, s: &mut DeviceState) {
        s.timer_mode = self.int_field(Param::TimerMode).map(|v| v as u8);
        if let Some(v) = self.bytes_field(Param::TimerCountdown) {
            s.timer_countdown = decode_timer_countdown(v).ok();
        }
        if let Some(v) = self.bytes_field(Param::NightTimer) {
            if v.len() >= 2 {
                s.night_timer = Some((v[1], v[0]));
            }
        }
        if let Some(v) = self.bytes_field(Param::PartyTimer) {
            if v.len() >= 2 {
                s.party_timer = Some((v[1], v[0]));
            }
        }
    }

    fn populate_sensors(&self, s: &mut DeviceState) {
        s.humidity_sensor    = self.int_field(Param::HumiditySensor).map(|v| v as u8);
        s.humidity_threshold = self.int_field(Param::HumidityThreshold).map(|v| v as u8);
        s.current_humidity   = self.int_field(Param::CurrentHumidity).map(|v| v as u8);
        s.humidity_status    = self.bool_field(Param::HumidityStatus);
        s.relay_sensor       = self.int_field(Param::RelaySensor).map(|v| v as u8);
        s.relay_state        = self.bool_field(Param::RelayState);
        s.voltage_sensor     = self.int_field(Param::VoltageSensor).map(|v| v as u8);
        s.voltage_threshold  = self.int_field(Param::VoltageThreshold).map(|v| v as u8);
        s.voltage_sensor_value = self.int_field(Param::VoltageSensorVal).map(|v| v as u8);
        s.voltage_status     = self.bool_field(Param::VoltageStatus);
    }

    fn populate_fan_and_filter(&self, s: &mut DeviceState) {
        s.fan1_rpm = self.int_field(Param::Fan1Speed).map(|v| v as u16);
        s.fan2_rpm = self.int_field(Param::Fan2Speed).map(|v| v as u16);
        if let Some(v) = self.bytes_field(Param::FilterCountdown) {
            s.filter_countdown = decode_filter_countdown(v).ok();
        }
        s.filter_needs_replacement = self.bool_field(Param::FilterIndicator);
        s.alarm_status = self.int_field(Param::AlarmStatus).map(|v| v as u8);
        if let Some(v) = self.bytes_field(Param::MachineHours) {
            s.machine_hours = decode_machine_hours(v).ok();
        }
        s.battery_voltage_mv = self.int_field(Param::BatteryVoltage).map(|v| v as u16);
    }

    fn populate_maintenance(&self, s: &mut DeviceState) {
        if let Some(v) = self.bytes_field(Param::FirmwareVersion) {
            s.firmware = decode_firmware(v).ok();
        }
        if let Some(v) = self.bytes_field(Param::RtcTime) {
            s.rtc_time = decode_rtc_time(v).ok();
        }
        if let Some(v) = self.bytes_field(Param::RtcCalendar) {
            s.rtc_calendar = decode_rtc_calendar(v).ok();
        }
        s.weekly_schedule_enabled = self.bool_field(Param::WeeklyScheduleEn);
        s.cloud_permitted = self.bool_field(Param::CloudPermission);
    }

    fn populate_wifi(&self, s: &mut DeviceState) {
        let has_wifi = [Param::WifiMode, Param::WifiSsid, Param::WifiIp]
            .iter()
            .any(|p| self.raw.contains_key(&p.as_u16()));
        if !has_wifi {
            return;
        }
        s.wifi = Some(WifiConfig {
            mode:       self.int_field(Param::WifiMode).unwrap_or(0) as u8,
            ssid:       self.text_field(Param::WifiSsid).unwrap_or_default(),
            encryption: self.int_field(Param::WifiEncryption).unwrap_or(52) as u8,
            channel:    self.int_field(Param::WifiChannel).unwrap_or(1) as u8,
            dhcp:       self.bool_field(Param::WifiDhcp).unwrap_or(true),
            ip:         self.ip_field(Param::WifiIp).unwrap_or_default(),
            subnet:     self.ip_field(Param::WifiSubnet).unwrap_or_default(),
            gateway:    self.ip_field(Param::WifiGateway).unwrap_or_default(),
            current_ip: self.ip_field(Param::WifiCurrentIp).unwrap_or_default(),
        });
    }
}

// ---------------------------------------------------------------------------
// VentoClient
// ---------------------------------------------------------------------------

pub struct VentoClient {
    pub host: String,
    pub device_id: String,
    pub password: String,
    pub port: u16,
    transport: VentoTransport,
}

impl VentoClient {
    pub fn new(host: &str, device_id: &str, password: &str) -> Self {
        VentoClient::with_port(host, device_id, password, DEFAULT_PORT)
    }

    pub fn with_port(host: &str, device_id: &str, password: &str, port: u16) -> Self {
        VentoClient {
            host: host.to_string(),
            device_id: device_id.to_string(),
            password: password.to_string(),
            port,
            transport: VentoTransport::default(),
        }
    }

    pub fn with_timeout(mut self, secs: f64) -> Self {
        self.transport = VentoTransport::new(secs);
        self
    }

    fn device_id_bytes(&self) -> Vec<u8> {
        self.device_id.as_bytes().to_vec()
    }

    fn send_recv(&self, packet: &[u8]) -> Result<HashMap<u16, Vec<u8>>> {
        let raw = self.transport.send_recv(&self.host, packet, self.port)?;
        parse_response(&raw)
    }

    fn send_only(&self, packet: &[u8]) -> Result<()> {
        self.transport.send_only(&self.host, packet, self.port)
    }

    pub fn read_params(&self, params: &[Param]) -> Result<HashMap<u16, Vec<u8>>> {
        self.send_recv(&build_read(&self.device_id_bytes(), &self.password, params)?)
    }

    pub fn write_params(&self, params: &[WriteParam]) -> Result<()> {
        self.send_only(&build_write(&self.device_id_bytes(), &self.password, params)?)
    }

    pub fn write_params_with_response(
        &self,
        params: &[WriteParam],
    ) -> Result<HashMap<u16, Vec<u8>>> {
        self.send_recv(&build_write_resp(
            &self.device_id_bytes(),
            &self.password,
            params,
        )?)
    }

    pub fn increment_params(&self, params: &[Param]) -> Result<HashMap<u16, Vec<u8>>> {
        self.send_recv(&build_increment(&self.device_id_bytes(), &self.password, params)?)
    }

    pub fn decrement_params(&self, params: &[Param]) -> Result<HashMap<u16, Vec<u8>>> {
        self.send_recv(&build_decrement(&self.device_id_bytes(), &self.password, params)?)
    }

    // --- Full state poll ---

    pub fn get_state(&self) -> Result<DeviceState> {
        let mut combined: HashMap<u16, Vec<u8>> = HashMap::new();
        for &group in ALL_PARAM_GROUPS {
            match self.read_params(group) {
                Ok(map) => combined.extend(map),
                Err(VentoError::UnsupportedParams(_)) => {}
                Err(e) => return Err(e),
            }
        }
        Ok(DeviceStateBuilder { raw: &combined, host: &self.host }.build())
    }

    // --- Power ---

    pub fn turn_on(&self) -> Result<()> {
        self.write_params(&[WriteParam::from_int(Param::Power, 1)?])
    }

    pub fn turn_off(&self) -> Result<()> {
        self.write_params(&[WriteParam::from_int(Param::Power, 0)?])
    }

    pub fn toggle_power(&self) -> Result<()> {
        self.write_params(&[WriteParam::from_int(Param::Power, 2)?])
    }

    // --- Speed ---

    pub fn set_speed(&self, speed: u8) -> Result<()> {
        check_choices("speed", speed, &[1, 2, 3])?;
        self.write_params(&[WriteParam::from_int(Param::Speed, speed as u64)?])
    }

    pub fn set_manual_speed(&self, value: u8) -> Result<()> {
        check_range("manual_speed", value as i64, 0, 255)?;
        self.write_params(&[
            WriteParam::from_int(Param::Speed, 255)?,
            WriteParam::from_int(Param::ManualSpeed, value as u64)?,
        ])
    }

    pub fn speed_up(&self) -> Result<HashMap<u16, Vec<u8>>> {
        self.increment_params(&[Param::Speed])
    }

    pub fn speed_down(&self) -> Result<HashMap<u16, Vec<u8>>> {
        self.decrement_params(&[Param::Speed])
    }

    // --- Mode ---

    pub fn set_mode(&self, mode: u8) -> Result<()> {
        check_choices("mode", mode, &[0, 1, 2])?;
        self.write_params(&[WriteParam::from_int(Param::OperationMode, mode as u64)?])
    }

    pub fn set_ventilation(&self)  -> Result<()> { self.set_mode(0) }
    pub fn set_heat_recovery(&self) -> Result<()> { self.set_mode(1) }
    pub fn set_supply(&self)        -> Result<()> { self.set_mode(2) }

    // --- Boost ---

    pub fn set_boost_delay(&self, minutes: u8) -> Result<()> {
        check_range("boost_delay", minutes as i64, 0, 60)?;
        self.write_params(&[WriteParam::from_int(Param::BoostDelay, minutes as u64)?])
    }

    // --- Timer ---

    pub fn set_timer_mode(&self, mode: u8) -> Result<()> {
        check_choices("timer_mode", mode, &[0, 1, 2])?;
        self.write_params(&[WriteParam::from_int(Param::TimerMode, mode as u64)?])
    }

    pub fn set_night_timer(&self, hours: u8, minutes: u8) -> Result<()> {
        check_range("hours", hours as i64, 0, 23)?;
        check_range("minutes", minutes as i64, 0, 59)?;
        self.write_params(&[WriteParam::from_bytes(Param::NightTimer, [minutes, hours])])
    }

    pub fn set_party_timer(&self, hours: u8, minutes: u8) -> Result<()> {
        check_range("hours", hours as i64, 0, 23)?;
        check_range("minutes", minutes as i64, 0, 59)?;
        self.write_params(&[WriteParam::from_bytes(Param::PartyTimer, [minutes, hours])])
    }

    pub fn get_timer_countdown(&self) -> Result<TimerCountdown> {
        let raw = self.read_params(&[Param::TimerCountdown])?;
        let bytes = raw
            .get(&Param::TimerCountdown.as_u16())
            .ok_or_else(|| VentoError::Protocol("TimerCountdown not in response".into()))?;
        decode_timer_countdown(bytes)
    }

    // --- Humidity ---

    pub fn set_humidity_sensor(&self, sensor: u8) -> Result<()> {
        check_choices("humidity_sensor", sensor, &[0, 1, 2])?;
        self.write_params(&[WriteParam::from_int(Param::HumiditySensor, sensor as u64)?])
    }

    pub fn set_humidity_threshold(&self, rh: u8) -> Result<()> {
        check_range("humidity_threshold", rh as i64, 40, 80)?;
        self.write_params(&[WriteParam::from_int(Param::HumidityThreshold, rh as u64)?])
    }

    pub fn get_current_humidity(&self) -> Result<u8> {
        let raw = self.read_params(&[Param::CurrentHumidity])?;
        Ok(raw
            .get(&Param::CurrentHumidity.as_u16())
            .map(|v| decode_int(v) as u8)
            .unwrap_or(0))
    }

    // --- Relay / voltage sensors ---

    pub fn set_relay_sensor(&self, sensor: u8) -> Result<()> {
        check_choices("relay_sensor", sensor, &[0, 1, 2])?;
        self.write_params(&[WriteParam::from_int(Param::RelaySensor, sensor as u64)?])
    }

    pub fn set_voltage_sensor(&self, sensor: u8) -> Result<()> {
        check_choices("voltage_sensor", sensor, &[0, 1, 2])?;
        self.write_params(&[WriteParam::from_int(Param::VoltageSensor, sensor as u64)?])
    }

    pub fn set_voltage_threshold(&self, percent: u8) -> Result<()> {
        check_range("voltage_threshold", percent as i64, 5, 100)?;
        self.write_params(&[WriteParam::from_int(Param::VoltageThreshold, percent as u64)?])
    }

    // --- Schedule ---

    pub fn enable_weekly_schedule(&self, enabled: bool) -> Result<()> {
        self.write_params(&[WriteParam::from_int(Param::WeeklyScheduleEn, enabled as u64)?])
    }

    pub fn set_schedule_period(
        &self,
        day: u8,
        period: u8,
        speed: u8,
        end_h: u8,
        end_m: u8,
    ) -> Result<()> {
        check_range("day", day as i64, 0, 9)?;
        check_range("period", period as i64, 1, 4)?;
        check_range("speed", speed as i64, 0, 3)?;
        check_range("end_h", end_h as i64, 0, 23)?;
        check_range("end_m", end_m as i64, 0, 59)?;
        self.write_params(&[WriteParam::from_bytes(
            Param::ScheduleSetup,
            [day, period, speed, 0, end_m, end_h],
        )])
    }

    pub fn get_schedule_period(&self, day: u8, period: u8) -> Result<SchedulePeriod> {
        check_range("day", day as i64, 0, 9)?;
        check_range("period", period as i64, 1, 4)?;
        let raw = self.write_params_with_response(&[WriteParam::from_bytes(
            Param::ScheduleSetup,
            [day, period, 0, 0, 0, 0],
        )])?;
        let bytes = raw
            .get(&Param::ScheduleSetup.as_u16())
            .ok_or_else(|| VentoError::Protocol("ScheduleSetup not in response".into()))?;
        let decoded = decode_schedule(bytes)?;
        Ok(SchedulePeriod {
            period_number: decoded.period,
            end_hours: decoded.end_hours,
            end_minutes: decoded.end_minutes,
            speed: decoded.speed,
        })
    }

    // --- RTC ---

    pub fn set_rtc(&self, dt: &SetRtcTime) -> Result<()> {
        self.write_params(&[
            WriteParam::from_bytes(Param::RtcTime, [dt.second, dt.minute, dt.hour]),
            WriteParam::from_bytes(
                Param::RtcCalendar,
                [dt.day, dt.day_of_week, dt.month, (dt.year % 100) as u8],
            ),
        ])
    }

    pub fn get_rtc(&self) -> Result<(RtcTime, RtcCalendar)> {
        let raw = self.read_params(&[Param::RtcTime, Param::RtcCalendar])?;
        let time = decode_rtc_time(
            raw.get(&Param::RtcTime.as_u16())
                .ok_or_else(|| VentoError::Protocol("RtcTime not in response".into()))?,
        )?;
        let cal = decode_rtc_calendar(
            raw.get(&Param::RtcCalendar.as_u16())
                .ok_or_else(|| VentoError::Protocol("RtcCalendar not in response".into()))?,
        )?;
        Ok((time, cal))
    }

    // --- Filter ---

    pub fn get_filter_status(&self) -> Result<(FilterCountdown, bool)> {
        let raw = self.read_params(&[Param::FilterCountdown, Param::FilterIndicator])?;
        let countdown = decode_filter_countdown(
            raw.get(&Param::FilterCountdown.as_u16())
                .ok_or_else(|| VentoError::Protocol("FilterCountdown not in response".into()))?,
        )?;
        let needs_replacement = raw
            .get(&Param::FilterIndicator.as_u16())
            .map(|v| decode_int(v) != 0)
            .unwrap_or(false);
        Ok((countdown, needs_replacement))
    }

    pub fn reset_filter_timer(&self) -> Result<()> {
        self.write_params(&[WriteParam::from_int(Param::FilterReset, 1)?])
    }

    // --- Machine hours ---

    pub fn get_machine_hours(&self) -> Result<MachineHours> {
        let raw = self.read_params(&[Param::MachineHours])?;
        decode_machine_hours(
            raw.get(&Param::MachineHours.as_u16())
                .ok_or_else(|| VentoError::Protocol("MachineHours not in response".into()))?,
        )
    }

    // --- Alarms ---

    pub fn reset_alarms(&self) -> Result<()> {
        self.write_params(&[WriteParam::from_int(Param::ResetAlarms, 1)?])
    }

    pub fn get_alarm_status(&self) -> Result<u8> {
        let raw = self.read_params(&[Param::AlarmStatus])?;
        Ok(raw
            .get(&Param::AlarmStatus.as_u16())
            .map(|v| decode_int(v) as u8)
            .unwrap_or(0))
    }

    // --- Firmware ---

    pub fn get_firmware_version(&self) -> Result<FirmwareVersion> {
        let raw = self.read_params(&[Param::FirmwareVersion])?;
        decode_firmware(
            raw.get(&Param::FirmwareVersion.as_u16())
                .ok_or_else(|| VentoError::Protocol("FirmwareVersion not in response".into()))?,
        )
    }

    pub fn get_unit_type(&self) -> Result<u16> {
        let raw = self.read_params(&[Param::UnitType])?;
        Ok(raw
            .get(&Param::UnitType.as_u16())
            .map(|v| decode_int(v) as u16)
            .unwrap_or(0))
    }

    pub fn get_device_id(&self) -> Result<String> {
        let raw = self.read_params(&[Param::DeviceSearch])?;
        Ok(raw
            .get(&Param::DeviceSearch.as_u16())
            .map(|v| decode_text(v))
            .unwrap_or_default())
    }

    // --- WiFi ---

    pub fn get_wifi_config(&self) -> Result<WifiConfig> {
        let raw = self.read_params(&[
            Param::WifiMode, Param::WifiSsid, Param::WifiEncryption, Param::WifiChannel,
            Param::WifiDhcp, Param::WifiIp, Param::WifiSubnet, Param::WifiGateway,
            Param::WifiCurrentIp,
        ])?;
        let get_int = |p: Param, default: u64| {
            raw.get(&p.as_u16()).map(|v| decode_int(v)).unwrap_or(default)
        };
        Ok(WifiConfig {
            mode: get_int(Param::WifiMode, 1) as u8,
            ssid: raw.get(&Param::WifiSsid.as_u16()).map(|v| decode_text(v)).unwrap_or_default(),
            encryption: get_int(Param::WifiEncryption, 52) as u8,
            channel: get_int(Param::WifiChannel, 6) as u8,
            dhcp: get_int(Param::WifiDhcp, 1) != 0,
            ip: raw.get(&Param::WifiIp.as_u16()).and_then(|v| decode_ip(v).ok()).unwrap_or_default(),
            subnet: raw.get(&Param::WifiSubnet.as_u16()).and_then(|v| decode_ip(v).ok()).unwrap_or_default(),
            gateway: raw.get(&Param::WifiGateway.as_u16()).and_then(|v| decode_ip(v).ok()).unwrap_or_default(),
            current_ip: raw.get(&Param::WifiCurrentIp.as_u16()).and_then(|v| decode_ip(v).ok()).unwrap_or_default(),
        })
    }

    pub fn set_wifi_client(
        &self,
        ssid: &str,
        wifi_password: &str,
        dhcp: bool,
        encryption: u8,
        static_ip: Option<&str>,
        subnet: Option<&str>,
        gateway: Option<&str>,
    ) -> Result<()> {
        let mut params = vec![
            WriteParam::from_int(Param::WifiMode, 1)?,
            WriteParam::from_bytes(Param::WifiSsid, ssid.as_bytes().to_vec()),
            WriteParam::from_bytes(Param::WifiPassword, wifi_password.as_bytes().to_vec()),
            WriteParam::from_int(Param::WifiEncryption, encryption as u64)?,
            WriteParam::from_int(Param::WifiDhcp, if dhcp { 1 } else { 0 })?,
        ];
        if !dhcp {
            let ip = static_ip
                .ok_or_else(|| VentoError::Value("static_ip required when dhcp=false".into()))?;
            params.push(WriteParam::from_bytes(Param::WifiIp, encode_ip(ip)?));
            params.push(WriteParam::from_bytes(
                Param::WifiSubnet,
                encode_ip(subnet.unwrap_or("255.255.255.0"))?,
            ));
            params.push(WriteParam::from_bytes(
                Param::WifiGateway,
                encode_ip(gateway.unwrap_or(ip))?,
            ));
        }
        self.write_params(&params)
    }

    pub fn set_wifi_ap(&self, channel: u8) -> Result<()> {
        check_range("channel", channel as i64, 1, 13)?;
        self.write_params(&[
            WriteParam::from_int(Param::WifiMode, 2)?,
            WriteParam::from_int(Param::WifiChannel, channel as u64)?,
        ])
    }

    pub fn apply_wifi_config(&self) -> Result<()> {
        self.write_params(&[WriteParam::from_int(Param::WifiApply, 1)?])
    }

    pub fn discard_wifi_config(&self) -> Result<()> {
        self.write_params(&[WriteParam::from_int(Param::WifiDiscard, 1)?])
    }

    // --- Misc ---

    pub fn change_password(&mut self, password: &str) -> Result<()> {
        if password.len() > 8 {
            return Err(VentoError::Value("Password max 8 characters".into()));
        }
        self.write_params(&[WriteParam::from_bytes(
            Param::DevicePassword,
            password.as_bytes().to_vec(),
        )])?;
        self.password = password.to_string();
        Ok(())
    }

    pub fn set_cloud_permission(&self, allowed: bool) -> Result<()> {
        self.write_params(&[WriteParam::from_int(Param::CloudPermission, allowed as u64)?])
    }

    pub fn factory_reset(&self) -> Result<()> {
        self.write_params(&[WriteParam::from_int(Param::FactoryReset, 1)?])
    }

    // --- Discovery ---

    pub fn discover(
        broadcast: &str,
        port: u16,
        timeout_secs: f64,
        max_devices: usize,
    ) -> Result<Vec<DiscoveredDevice>> {
        let transport = VentoTransport::new(timeout_secs);
        let pkt = build_discovery();
        let raw_items = transport.discover(&pkt, broadcast, port, max_devices)?;
        let mut devices = Vec::new();
        for (ip, raw) in raw_items {
            if let Ok(resp) = parse_response(&raw) {
                let device_id = resp
                    .get(&Param::DeviceSearch.as_u16())
                    .map(|v| decode_text(v))
                    .unwrap_or_default();
                let unit_type = resp
                    .get(&Param::UnitType.as_u16())
                    .map(|v| decode_int(v) as u16)
                    .unwrap_or(0);
                devices.push(DiscoveredDevice::new(ip, device_id, unit_type));
            }
        }
        Ok(devices)
    }
}

// ---------------------------------------------------------------------------
// Tests — validation mirrors test_protocol.py TestValidation
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    fn client() -> VentoClient {
        VentoClient::new("127.0.0.1", "\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00", "1111")
    }

    #[test]
    fn bad_speed_rejected() {
        assert!(client().set_speed(5).is_err());
    }

    #[test]
    fn bad_humidity_threshold_rejected() {
        assert!(client().set_humidity_threshold(100).is_err());
    }

    #[test]
    fn bad_boost_delay_rejected() {
        assert!(client().set_boost_delay(61).is_err());
    }

    #[test]
    fn long_password_rejected() {
        let mut c = client();
        assert!(c.change_password("TOOLONGPWD").is_err());
    }

    #[test]
    fn manual_speed_boundaries_accepted() {
        // These should not fail at the validation stage (they'll fail at network I/O)
        let c = client();
        // Validation passes — only the network send will fail
        let r0 = c.set_manual_speed(0);
        let r255 = c.set_manual_speed(255);
        // Both should fail only with a Connection error, not a Value error
        for r in [r0, r255] {
            match r {
                Err(VentoError::Value(_)) => panic!("validation wrongly rejected boundary value"),
                _ => {}
            }
        }
    }
}
