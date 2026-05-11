use std::collections::HashMap;

use crate::error::{Result, VentoError};
use crate::models::{
    FilterCountdown, FirmwareVersion, MachineHours, RtcCalendar, RtcTime, TimerCountdown,
};
use crate::param::{
    CMD_FUNC, CMD_NOT_SUP, CMD_PAGE, CMD_SIZE, DEFAULT_DEVICE_ID,
    Func, MAX_PACKET_SIZE, PACKET_START, PROTOCOL_TYPE, Param, WriteParam,
};

// ---------------------------------------------------------------------------
// Encoding helpers
// ---------------------------------------------------------------------------

fn encode_id(device_id: &[u8]) -> Result<[u8; 16]> {
    if device_id.len() != 16 {
        return Err(VentoError::Protocol(format!(
            "Device ID must be 16 bytes, got {}",
            device_id.len()
        )));
    }
    let mut out = [0u8; 16];
    out.copy_from_slice(device_id);
    Ok(out)
}

fn encode_password(password: &str) -> Result<Vec<u8>> {
    if !password.is_ascii() {
        return Err(VentoError::Protocol("Password must be ASCII".into()));
    }
    let raw = password.as_bytes();
    if raw.len() > 8 {
        return Err(VentoError::Protocol("Password max 8 chars".into()));
    }
    Ok(raw.to_vec())
}

fn checksum(payload: &[u8]) -> [u8; 2] {
    let sum: u32 = payload.iter().map(|&b| b as u32).sum();
    let cs = (sum & 0xFFFF) as u16;
    cs.to_le_bytes()
}

// ---------------------------------------------------------------------------
// Packet building
// ---------------------------------------------------------------------------

pub fn build_packet(device_id: &[u8], password: &str, func: Func, data: &[u8]) -> Result<Vec<u8>> {
    let id = encode_id(device_id)?;
    let pwd = encode_password(password)?;

    let mut payload = Vec::with_capacity(4 + id.len() + 1 + pwd.len() + 1 + data.len());
    payload.push(PROTOCOL_TYPE);
    payload.push(id.len() as u8);
    payload.extend_from_slice(&id);
    payload.push(pwd.len() as u8);
    payload.extend_from_slice(&pwd);
    payload.push(func as u8);
    payload.extend_from_slice(data);

    let cs = checksum(&payload);
    let mut pkt = Vec::with_capacity(2 + payload.len() + 2);
    pkt.extend_from_slice(&PACKET_START);
    pkt.extend_from_slice(&payload);
    pkt.extend_from_slice(&cs);

    if pkt.len() > MAX_PACKET_SIZE {
        return Err(VentoError::Protocol(format!(
            "Packet {} bytes > max {}",
            pkt.len(),
            MAX_PACKET_SIZE
        )));
    }
    Ok(pkt)
}

fn build_read_data(params: &[Param]) -> Vec<u8> {
    let mut data = Vec::new();
    let mut page = 0u8;
    for &p in params {
        let high = p.page();
        if high != page {
            data.push(CMD_PAGE);
            data.push(high);
            page = high;
        }
        data.push(p.addr());
    }
    data
}

fn build_write_data(params: &[WriteParam]) -> Vec<u8> {
    let mut data = Vec::new();
    let mut page = 0u8;
    for WriteParam(p, val_bytes) in params {
        let high = p.page();
        let size = val_bytes.len();
        if high != page {
            data.push(CMD_PAGE);
            data.push(high);
            page = high;
        }
        if size != 1 {
            data.push(CMD_SIZE);
            data.push(size as u8);
        }
        data.push(p.addr());
        data.extend_from_slice(val_bytes);
    }
    data
}

pub fn build_read(device_id: &[u8], password: &str, params: &[Param]) -> Result<Vec<u8>> {
    build_packet(device_id, password, Func::Read, &build_read_data(params))
}

pub fn build_write(device_id: &[u8], password: &str, params: &[WriteParam]) -> Result<Vec<u8>> {
    build_packet(device_id, password, Func::Write, &build_write_data(params))
}

pub fn build_write_resp(device_id: &[u8], password: &str, params: &[WriteParam]) -> Result<Vec<u8>> {
    build_packet(device_id, password, Func::WriteResp, &build_write_data(params))
}

pub fn build_increment(device_id: &[u8], password: &str, params: &[Param]) -> Result<Vec<u8>> {
    build_packet(device_id, password, Func::Increment, &build_read_data(params))
}

pub fn build_decrement(device_id: &[u8], password: &str, params: &[Param]) -> Result<Vec<u8>> {
    build_packet(device_id, password, Func::Decrement, &build_read_data(params))
}

pub fn build_discovery() -> Vec<u8> {
    build_read(DEFAULT_DEVICE_ID, "", &[Param::DeviceSearch, Param::UnitType])
        .expect("discovery packet is always valid")
}

// ---------------------------------------------------------------------------
// Checksum verification and response parsing
// ---------------------------------------------------------------------------

pub fn verify_checksum(raw: &[u8]) -> Result<()> {
    if raw.len() < 4 {
        return Err(VentoError::Checksum("Packet too short".into()));
    }
    let expected = u16::from_le_bytes([raw[raw.len() - 2], raw[raw.len() - 1]]);
    let actual = (raw[2..raw.len() - 2]
        .iter()
        .map(|&b| b as u32)
        .sum::<u32>()
        & 0xFFFF) as u16;
    if actual != expected {
        return Err(VentoError::Checksum(format!(
            "mismatch: {actual:#06x} != {expected:#06x}"
        )));
    }
    Ok(())
}

struct PacketHeader {
    data_start: usize,
}

fn parse_header(raw: &[u8]) -> Result<PacketHeader> {
    if raw.len() < 23 {
        return Err(VentoError::Protocol(format!("Packet too short: {}", raw.len())));
    }
    if raw[0] != 0xFD || raw[1] != 0xFD {
        return Err(VentoError::Protocol("Missing 0xFD 0xFD header".into()));
    }
    if raw[2] != PROTOCOL_TYPE {
        return Err(VentoError::Protocol(format!("Unknown type {:#04x}", raw[2])));
    }
    let id_size = raw[3] as usize;
    let id_end = 4 + id_size;
    let pwd_size = raw[id_end] as usize;
    let pwd_end = id_end + 1 + pwd_size;
    let func_byte = raw[pwd_end];
    if func_byte != Func::Response as u8 {
        return Err(VentoError::Protocol(format!(
            "Expected FUNC=0x06, got {func_byte:#04x}"
        )));
    }
    Ok(PacketHeader { data_start: pwd_end + 1 })
}

/// Parse a device response packet into a param→bytes map.
/// Unknown param numbers are stored with their raw u16 key.
/// Returns Err(UnsupportedParams) if the device reported unsupported params.
pub fn parse_response(raw: &[u8]) -> Result<HashMap<u16, Vec<u8>>> {
    verify_checksum(raw)?;
    let header = parse_header(raw)?;
    parse_data_bytes(&raw[header.data_start..raw.len() - 2])
}

fn parse_data_bytes(data: &[u8]) -> Result<HashMap<u16, Vec<u8>>> {
    let mut result: HashMap<u16, Vec<u8>> = HashMap::new();
    let mut unsupported: Vec<u16> = Vec::new();
    let mut page = 0u8;
    let mut param_size: usize = 1;
    let mut i = 0;

    while i < data.len() {
        let mut b = data[i];

        if b == CMD_PAGE {
            i += 1;
            page = data[i];
            i += 1;
            param_size = 1;
            continue;
        }

        if b == CMD_FUNC {
            i += 2;
            param_size = 1;
            continue;
        }

        if b == CMD_SIZE {
            i += 1;
            param_size = data[i] as usize;
            i += 1;
            b = data[i];
        }

        if b == CMD_NOT_SUP {
            i += 1;
            if i < data.len() {
                unsupported.push(((page as u16) << 8) | data[i] as u16);
            }
            i += 1;
            param_size = 1;
            continue;
        }

        let param_num = ((page as u16) << 8) | b as u16;
        i += 1;
        let value_end = i + param_size;
        if value_end > data.len() {
            return Err(VentoError::Protocol(format!(
                "Param {param_num:#06x} truncated"
            )));
        }
        result.insert(param_num, data[i..value_end].to_vec());
        i = value_end;
        param_size = 1;
    }

    if !unsupported.is_empty() {
        return Err(VentoError::UnsupportedParams(unsupported));
    }
    Ok(result)
}

// ---------------------------------------------------------------------------
// Decoder helpers
// ---------------------------------------------------------------------------

pub fn decode_int(val: &[u8]) -> u64 {
    val.iter()
        .enumerate()
        .fold(0u64, |acc, (i, &b)| acc | ((b as u64) << (i * 8)))
}

pub fn decode_ip(val: &[u8]) -> Result<String> {
    if val.len() != 4 {
        return Err(VentoError::Protocol(format!(
            "IP must be 4 bytes, got {}",
            val.len()
        )));
    }
    Ok(format!("{}.{}.{}.{}", val[0], val[1], val[2], val[3]))
}

pub fn encode_ip(ip: &str) -> Result<[u8; 4]> {
    let parts: Vec<&str> = ip.split('.').collect();
    if parts.len() != 4 {
        return Err(VentoError::Protocol(format!("Invalid IP {ip:?}")));
    }
    let mut out = [0u8; 4];
    for (i, part) in parts.iter().enumerate() {
        out[i] = part
            .parse::<u8>()
            .map_err(|_| VentoError::Protocol(format!("Invalid IP octet {part:?}")))?;
    }
    Ok(out)
}

pub fn decode_text(val: &[u8]) -> String {
    val.iter()
        .map(|&b| if b.is_ascii() { b as char } else { '?' })
        .collect()
}

pub fn decode_firmware(val: &[u8]) -> Result<FirmwareVersion> {
    if val.len() != 6 {
        return Err(VentoError::Protocol(format!(
            "Firmware must be 6 bytes, got {}",
            val.len()
        )));
    }
    Ok(FirmwareVersion {
        major: val[0],
        minor: val[1],
        day: val[2],
        month: val[3],
        year: u16::from_le_bytes([val[4], val[5]]),
    })
}

pub fn decode_machine_hours(val: &[u8]) -> Result<MachineHours> {
    if val.len() != 4 {
        return Err(VentoError::Protocol(format!(
            "Machine hours must be 4 bytes, got {}",
            val.len()
        )));
    }
    Ok(MachineHours {
        minutes: val[0],
        hours: val[1],
        days: u16::from_le_bytes([val[2], val[3]]),
    })
}

pub fn decode_rtc_time(val: &[u8]) -> Result<RtcTime> {
    if val.len() != 3 {
        return Err(VentoError::Protocol(format!(
            "RTC time must be 3 bytes, got {}",
            val.len()
        )));
    }
    Ok(RtcTime { seconds: val[0], minutes: val[1], hours: val[2] })
}

pub fn decode_rtc_calendar(val: &[u8]) -> Result<RtcCalendar> {
    if val.len() != 4 {
        return Err(VentoError::Protocol(format!(
            "RTC calendar must be 4 bytes, got {}",
            val.len()
        )));
    }
    Ok(RtcCalendar {
        day: val[0],
        day_of_week: val[1],
        month: val[2],
        year: 2000 + val[3] as u16,
    })
}

pub fn decode_timer_countdown(val: &[u8]) -> Result<TimerCountdown> {
    if val.len() != 3 {
        return Err(VentoError::Protocol(format!(
            "Timer countdown must be 3 bytes, got {}",
            val.len()
        )));
    }
    Ok(TimerCountdown { seconds: val[0], minutes: val[1], hours: val[2] })
}

pub fn decode_filter_countdown(val: &[u8]) -> Result<FilterCountdown> {
    if val.len() != 3 {
        return Err(VentoError::Protocol(format!(
            "Filter countdown must be 3 bytes, got {}",
            val.len()
        )));
    }
    Ok(FilterCountdown { minutes: val[0], hours: val[1], days: val[2] })
}

pub struct DecodedSchedule {
    pub day_of_week: u8,
    pub period: u8,
    pub speed: u8,
    pub end_minutes: u8,
    pub end_hours: u8,
}

pub fn decode_schedule(val: &[u8]) -> Result<DecodedSchedule> {
    if val.len() != 6 {
        return Err(VentoError::Protocol(format!(
            "Schedule must be 6 bytes, got {}",
            val.len()
        )));
    }
    Ok(DecodedSchedule {
        day_of_week: val[0],
        period: val[1],
        speed: val[2],
        // val[3] is reserved
        end_minutes: val[4],
        end_hours: val[5],
    })
}

// ---------------------------------------------------------------------------
// Tests — byte-for-byte parity with the Python test suite
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;
    use crate::param::Func;

    const NULL_ID: [u8; 16] = [0u8; 16];
    const NULL_PWD: &str = "1111";

    // Spec packets copied verbatim from tests/test_protocol.py
    const SPEC_RQ: &[u8] = &[
        0xFD, 0xFD, 0x02, 0x10,
        0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
        0x04, 0x31, 0x31, 0x31, 0x31,
        0x01, 0x01, 0x02, 0xDE, 0x00,
    ];

    const SPEC_RS: &[u8] = &[
        0xFD, 0xFD, 0x02, 0x10,
        0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
        0x04, 0x31, 0x31, 0x31, 0x31,
        0x06, 0x01, 0x00, 0x02, 0x03, 0xE6, 0x00,
    ];

    fn mkr(data: &[u8]) -> Vec<u8> {
        build_packet(&NULL_ID, NULL_PWD, Func::Response, data).unwrap()
    }

    // --- checksum ---
    #[test]
    fn checksum_spec_rq() { verify_checksum(SPEC_RQ).unwrap(); }
    #[test]
    fn checksum_spec_rs() { verify_checksum(SPEC_RS).unwrap(); }
    #[test]
    fn checksum_bad() {
        let mut bad = SPEC_RQ.to_vec();
        let last = bad.last_mut().unwrap();
        *last ^= 0xFF;
        assert!(verify_checksum(&bad).is_err());
    }

    // --- building ---
    #[test]
    fn build_matches_spec() {
        let pkt = build_read(&NULL_ID, NULL_PWD, &[Param::Power, Param::Speed]).unwrap();
        assert_eq!(pkt, SPEC_RQ);
    }
    #[test]
    fn build_starts_fd_fd() {
        let pkt = build_read(&NULL_ID, NULL_PWD, &[Param::Power]).unwrap();
        assert_eq!(&pkt[..2], &[0xFD, 0xFD]);
    }
    #[test]
    fn build_checksum_valid() {
        let pkt = build_read(&NULL_ID, NULL_PWD, &[Param::Power, Param::Speed]).unwrap();
        verify_checksum(&pkt).unwrap();
    }
    #[test]
    fn build_discovery_default_id() {
        let pkt = build_discovery();
        assert_eq!(&pkt[4..20], b"DEFAULT_DEVICEID");
    }
    #[test]
    fn build_night_timer_page_cmd() {
        let pkt = build_read(&NULL_ID, NULL_PWD, &[Param::NightTimer]).unwrap();
        // strip 0xFD 0xFD header and trailing checksum
        let payload = &pkt[2..pkt.len() - 2];
        let idx = payload.iter().position(|&b| b == CMD_PAGE).expect("CMD_PAGE not found");
        assert_eq!(payload[idx + 1], 0x03);
        assert_eq!(payload[idx + 2], 0x02);
    }
    #[test]
    fn build_bad_id_raises() {
        assert!(build_read(b"SHORT", NULL_PWD, &[Param::Power]).is_err());
    }
    #[test]
    fn build_long_password_raises() {
        assert!(build_read(&NULL_ID, "TOOLONGPWD", &[Param::Power]).is_err());
    }

    // --- parsing ---
    #[test]
    fn parse_spec_response() {
        let r = parse_response(SPEC_RS).unwrap();
        assert_eq!(r.get(&(Param::Power as u16)), Some(&vec![0x00]));
        assert_eq!(r.get(&(Param::Speed as u16)), Some(&vec![0x03]));
    }
    #[test]
    fn parse_unsupported_param() {
        let pkt = mkr(&[0xFD, 0x01, 0x02, 0x03]);
        let err = parse_response(&pkt).unwrap_err();
        match err {
            VentoError::UnsupportedParams(params) => assert!(params.contains(&0x0001)),
            other => panic!("unexpected error: {other}"),
        }
    }
    #[test]
    fn parse_size_override() {
        // CMD_SIZE=0xFE, size=2, param=0x24 (BatteryVoltage), value=0x88 0x13 = 5000 LE
        let pkt = mkr(&[0xFE, 0x02, 0x24, 0x88, 0x13]);
        let r = parse_response(&pkt).unwrap();
        let val = r.get(&(Param::BatteryVoltage as u16)).unwrap();
        assert_eq!(decode_int(val), 5000);
    }
    #[test]
    fn parse_page_change() {
        // CMD_PAGE=0xFF, page=0x03, CMD_SIZE=0xFE, size=2, addr=0x02 (NightTimer), value=[30, 8]
        let pkt = mkr(&[0xFF, 0x03, 0xFE, 0x02, 0x02, 0x1E, 0x08]);
        let r = parse_response(&pkt).unwrap();
        let v = r.get(&(Param::NightTimer as u16)).unwrap();
        assert_eq!(v[0], 30);
        assert_eq!(v[1], 8);
    }

    // --- decoders ---
    #[test]
    fn decode_ip_ok() {
        assert_eq!(decode_ip(&[192, 168, 1, 50]).unwrap(), "192.168.1.50");
    }
    #[test]
    fn encode_ip_ok() {
        assert_eq!(encode_ip("192.168.1.50").unwrap(), [192, 168, 1, 50]);
    }
    #[test]
    fn firmware_decoder() {
        let v = decode_firmware(&[1, 5, 14, 3, 0xE8, 0x07]).unwrap();
        assert_eq!(v.major, 1);
        assert_eq!(v.minor, 5);
        assert_eq!(v.day, 14);
        assert_eq!(v.month, 3);
        assert_eq!(v.year, 2024);
    }
    #[test]
    fn machine_hours_decoder() {
        let v = decode_machine_hours(&[30, 5, 10, 0]).unwrap();
        assert_eq!(v.minutes, 30);
        assert_eq!(v.hours, 5);
        assert_eq!(v.days, 10);
    }
    #[test]
    fn rtc_time_decoder() {
        let v = decode_rtc_time(&[45, 30, 14]).unwrap();
        assert_eq!(v.seconds, 45);
        assert_eq!(v.minutes, 30);
        assert_eq!(v.hours, 14);
    }
    #[test]
    fn rtc_calendar_decoder() {
        let v = decode_rtc_calendar(&[15, 3, 6, 24]).unwrap();
        assert_eq!(v.year, 2024);
        assert_eq!(v.month, 6);
        assert_eq!(v.day, 15);
    }
    #[test]
    fn schedule_decoder() {
        let v = decode_schedule(&[2, 1, 2, 0, 30, 8]).unwrap();
        assert_eq!(v.speed, 2);
        assert_eq!(v.end_hours, 8);
        assert_eq!(v.end_minutes, 30);
    }
    #[test]
    fn filter_countdown_decoder() {
        let v = decode_filter_countdown(&[0, 12, 90]).unwrap();
        assert_eq!(v.minutes, 0);
        assert_eq!(v.hours, 12);
        assert_eq!(v.days, 90);
    }
    #[test]
    fn decode_ip_bad_size() {
        assert!(decode_ip(&[192, 168]).is_err());
    }
}
