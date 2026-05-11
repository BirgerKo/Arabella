use std::cell::RefCell;
use std::ffi::{CStr, CString};
use std::os::raw::c_char;

use crate::client::VentoClient;
use crate::error::VentoError;
use crate::models::SetRtcTime;

// ── Error string (thread-local) ───────────────────────────────────────────────

thread_local! {
    static LAST_ERROR: RefCell<CString> =
        RefCell::new(CString::new("").unwrap());
}

fn set_last_error(e: &VentoError) {
    let s = CString::new(e.to_string())
        .unwrap_or_else(|_| CString::new("error").unwrap());
    LAST_ERROR.with(|le| *le.borrow_mut() = s);
}

/// Returns the last error message set by a failed FFI call on this thread.
/// The pointer is valid until the next FFI call. Do not free it.
#[no_mangle]
pub extern "C" fn vento_last_error() -> *const c_char {
    LAST_ERROR.with(|le| le.borrow().as_ptr())
}

// ── Status ────────────────────────────────────────────────────────────────────

/// Return status for all FFI functions. `Ok` (0) means success.
#[repr(C)]
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum VentoStatus {
    Ok = 0,
    ErrConnection = 1,
    ErrChecksum = 2,
    ErrProtocol = 3,
    ErrValue = 4,
    ErrDiscovery = 5,
    ErrUnsupported = 6,
}

fn to_status(e: &VentoError) -> VentoStatus {
    match e {
        VentoError::Connection(_) | VentoError::Io(_) => VentoStatus::ErrConnection,
        VentoError::Checksum(_)                       => VentoStatus::ErrChecksum,
        VentoError::Protocol(_)                       => VentoStatus::ErrProtocol,
        VentoError::Value(_)                          => VentoStatus::ErrValue,
        VentoError::Discovery(_)                      => VentoStatus::ErrDiscovery,
        VentoError::UnsupportedParams(_)              => VentoStatus::ErrUnsupported,
    }
}

fn map_result(r: crate::error::Result<()>) -> VentoStatus {
    match r {
        Ok(()) => VentoStatus::Ok,
        Err(e) => { set_last_error(&e); to_status(&e) }
    }
}

// ── String helpers ────────────────────────────────────────────────────────────

unsafe fn str_from_ptr<'a>(ptr: *const c_char) -> &'a str {
    if ptr.is_null() { return ""; }
    CStr::from_ptr(ptr).to_str().unwrap_or("")
}

fn copy_cstr(dst: &mut [c_char], src: &str) {
    let n = src.len().min(dst.len() - 1);
    for (i, b) in src.as_bytes()[..n].iter().enumerate() {
        dst[i] = *b as c_char;
    }
    dst[n] = 0;
}

// ── C-compatible structs ──────────────────────────────────────────────────────

/// Full device state snapshot filled by `vento_get_state`.
///
/// Every optional field is paired with a `_valid` byte.
/// When `_valid` is 0 the companion field is undefined.
/// String fields (`ip`, `device_id`) are null-terminated UTF-8.
#[repr(C)]
pub struct VentoDeviceState {
    /// Null-terminated device IP address.
    pub ip: [c_char; 64],
    /// Null-terminated device ID string.
    pub device_id: [c_char; 64],
    pub unit_type: u16,

    pub power_valid: u8,                    pub power: u8,
    pub speed_valid: u8,                    pub speed: u8,
    pub manual_speed_valid: u8,             pub manual_speed: u8,
    pub operation_mode_valid: u8,           pub operation_mode: u8,
    pub boost_active_valid: u8,             pub boost_active: u8,
    pub boost_delay_valid: u8,              pub boost_delay_minutes: u8,

    pub timer_mode_valid: u8,               pub timer_mode: u8,

    pub humidity_sensor_valid: u8,          pub humidity_sensor: u8,
    pub humidity_threshold_valid: u8,       pub humidity_threshold: u8,
    pub current_humidity_valid: u8,         pub current_humidity: u8,
    pub humidity_status_valid: u8,          pub humidity_status: u8,

    pub fan1_rpm_valid: u8,                 pub fan1_rpm: u16,
    pub fan2_rpm_valid: u8,                 pub fan2_rpm: u16,

    pub filter_needs_replacement_valid: u8, pub filter_needs_replacement: u8,
    pub alarm_status_valid: u8,             pub alarm_status: u8,

    pub firmware_valid: u8,
    pub firmware_major: u8,
    pub firmware_minor: u8,

    pub weekly_schedule_enabled_valid: u8,  pub weekly_schedule_enabled: u8,
    pub cloud_permitted_valid: u8,          pub cloud_permitted: u8,
}

/// Schedule period returned by `vento_get_schedule_period`.
#[repr(C)]
pub struct VentoSchedulePeriod {
    pub period_number: u8,
    pub end_hours: u8,
    pub end_minutes: u8,
    pub speed: u8,
}

/// Date/time input for `vento_set_rtc`. Caller supplies current local time.
#[repr(C)]
pub struct VentoRtcInput {
    pub year: u16,
    pub month: u8,
    pub day: u8,
    /// ISO weekday: 1 = Monday … 7 = Sunday.
    pub day_of_week: u8,
    pub hour: u8,
    pub minute: u8,
    pub second: u8,
}

/// A single fan device returned by `vento_discover`.
#[repr(C)]
pub struct VentoDiscoveredDevice {
    pub ip: [c_char; 64],
    pub device_id: [c_char; 64],
    pub unit_type: u16,
    pub unit_type_name: [c_char; 128],
}

/// List of discovered devices returned by `vento_discover`.
/// Free with `vento_device_list_free` when done.
#[repr(C)]
pub struct VentoDeviceList {
    pub devices: *mut VentoDiscoveredDevice,
    pub count: u32,
}

// ── VentoDeviceState population ───────────────────────────────────────────────

fn populate_state(c: &mut VentoDeviceState, s: &crate::models::DeviceState) {
    copy_cstr(&mut c.ip, &s.ip);
    copy_cstr(&mut c.device_id, &s.device_id);
    c.unit_type = s.unit_type;

    if let Some(v) = s.power               { c.power_valid = 1;                    c.power = v as u8; }
    if let Some(v) = s.speed               { c.speed_valid = 1;                    c.speed = v; }
    if let Some(v) = s.manual_speed        { c.manual_speed_valid = 1;             c.manual_speed = v; }
    if let Some(v) = s.operation_mode      { c.operation_mode_valid = 1;           c.operation_mode = v; }
    if let Some(v) = s.boost_active        { c.boost_active_valid = 1;             c.boost_active = v as u8; }
    if let Some(v) = s.boost_delay_minutes { c.boost_delay_valid = 1;              c.boost_delay_minutes = v; }
    if let Some(v) = s.timer_mode          { c.timer_mode_valid = 1;               c.timer_mode = v; }
    if let Some(v) = s.humidity_sensor     { c.humidity_sensor_valid = 1;          c.humidity_sensor = v; }
    if let Some(v) = s.humidity_threshold  { c.humidity_threshold_valid = 1;       c.humidity_threshold = v; }
    if let Some(v) = s.current_humidity    { c.current_humidity_valid = 1;         c.current_humidity = v; }
    if let Some(v) = s.humidity_status     { c.humidity_status_valid = 1;          c.humidity_status = v as u8; }
    if let Some(v) = s.fan1_rpm            { c.fan1_rpm_valid = 1;                 c.fan1_rpm = v; }
    if let Some(v) = s.fan2_rpm            { c.fan2_rpm_valid = 1;                 c.fan2_rpm = v; }
    if let Some(v) = s.filter_needs_replacement {
        c.filter_needs_replacement_valid = 1;
        c.filter_needs_replacement = v as u8;
    }
    if let Some(v) = s.alarm_status        { c.alarm_status_valid = 1;             c.alarm_status = v; }
    if let Some(ref fw) = s.firmware       { c.firmware_valid = 1; c.firmware_major = fw.major; c.firmware_minor = fw.minor; }
    if let Some(v) = s.weekly_schedule_enabled { c.weekly_schedule_enabled_valid = 1; c.weekly_schedule_enabled = v as u8; }
    if let Some(v) = s.cloud_permitted     { c.cloud_permitted_valid = 1;          c.cloud_permitted = v as u8; }
}

// ── Client lifecycle ──────────────────────────────────────────────────────────

/// Create a new VentoClient.
///
/// Returns a non-null opaque pointer on success. Free with `vento_client_free`.
/// Returns null if any argument is null.
#[no_mangle]
pub extern "C" fn vento_client_new(
    host: *const c_char,
    device_id: *const c_char,
    password: *const c_char,
) -> *mut VentoClient {
    if host.is_null() || device_id.is_null() || password.is_null() {
        return std::ptr::null_mut();
    }
    let client = unsafe {
        VentoClient::new(str_from_ptr(host), str_from_ptr(device_id), str_from_ptr(password))
    };
    Box::into_raw(Box::new(client))
}

/// Free a VentoClient returned by `vento_client_new`. Passing null is a no-op.
///
/// # Safety
/// `client` must be a pointer returned by `vento_client_new`, or null.
#[no_mangle]
pub unsafe extern "C" fn vento_client_free(client: *mut VentoClient) {
    if !client.is_null() {
        drop(Box::from_raw(client));
    }
}

// ── State ─────────────────────────────────────────────────────────────────────

/// Read the full device state into `*out`.
///
/// # Safety
/// `client` and `out` must be valid non-null pointers.
#[no_mangle]
pub unsafe extern "C" fn vento_get_state(
    client: *const VentoClient,
    out: *mut VentoDeviceState,
) -> VentoStatus {
    match (*client).get_state() {
        Ok(ref s) => {
            *out = std::mem::zeroed();
            populate_state(&mut *out, s);
            VentoStatus::Ok
        }
        Err(e) => { set_last_error(&e); to_status(&e) }
    }
}

// ── Power ─────────────────────────────────────────────────────────────────────

/// # Safety
/// `client` must be a valid non-null pointer.
#[no_mangle]
pub unsafe extern "C" fn vento_turn_on(client: *const VentoClient) -> VentoStatus {
    map_result((*client).turn_on())
}

/// # Safety
/// `client` must be a valid non-null pointer.
#[no_mangle]
pub unsafe extern "C" fn vento_turn_off(client: *const VentoClient) -> VentoStatus {
    map_result((*client).turn_off())
}

/// # Safety
/// `client` must be a valid non-null pointer.
#[no_mangle]
pub unsafe extern "C" fn vento_toggle_power(client: *const VentoClient) -> VentoStatus {
    map_result((*client).toggle_power())
}

// ── Speed ─────────────────────────────────────────────────────────────────────

/// Set fan speed (1, 2, or 3).
///
/// # Safety
/// `client` must be a valid non-null pointer.
#[no_mangle]
pub unsafe extern "C" fn vento_set_speed(client: *const VentoClient, speed: u8) -> VentoStatus {
    map_result((*client).set_speed(speed))
}

/// Set manual speed (0–255). Also sets speed mode to manual.
///
/// # Safety
/// `client` must be a valid non-null pointer.
#[no_mangle]
pub unsafe extern "C" fn vento_set_manual_speed(client: *const VentoClient, value: u8) -> VentoStatus {
    map_result((*client).set_manual_speed(value))
}

/// Increment speed by one step.
///
/// # Safety
/// `client` must be a valid non-null pointer.
#[no_mangle]
pub unsafe extern "C" fn vento_speed_up(client: *const VentoClient) -> VentoStatus {
    map_result((*client).speed_up().map(|_| ()))
}

/// Decrement speed by one step.
///
/// # Safety
/// `client` must be a valid non-null pointer.
#[no_mangle]
pub unsafe extern "C" fn vento_speed_down(client: *const VentoClient) -> VentoStatus {
    map_result((*client).speed_down().map(|_| ()))
}

// ── Mode ──────────────────────────────────────────────────────────────────────

/// Set operation mode: 0 = Ventilation, 1 = Heat Recovery, 2 = Supply.
///
/// # Safety
/// `client` must be a valid non-null pointer.
#[no_mangle]
pub unsafe extern "C" fn vento_set_mode(client: *const VentoClient, mode: u8) -> VentoStatus {
    map_result((*client).set_mode(mode))
}

// ── Boost ─────────────────────────────────────────────────────────────────────

/// Enable (on != 0) or disable (on == 0) boost mode.
///
/// # Safety
/// `client` must be a valid non-null pointer.
#[no_mangle]
pub unsafe extern "C" fn vento_set_boost_status(
    client: *const VentoClient,
    on: u8,
) -> VentoStatus {
    map_result((*client).set_boost_status(on != 0))
}

/// Set boost delay in minutes (0–60).
///
/// # Safety
/// `client` must be a valid non-null pointer.
#[no_mangle]
pub unsafe extern "C" fn vento_set_boost_delay(
    client: *const VentoClient,
    minutes: u8,
) -> VentoStatus {
    map_result((*client).set_boost_delay(minutes))
}

// ── Timer ─────────────────────────────────────────────────────────────────────

/// Set timer mode: 0 = off, 1 = night, 2 = party.
///
/// # Safety
/// `client` must be a valid non-null pointer.
#[no_mangle]
pub unsafe extern "C" fn vento_set_timer_mode(client: *const VentoClient, mode: u8) -> VentoStatus {
    map_result((*client).set_timer_mode(mode))
}

/// Set night timer duration.
///
/// # Safety
/// `client` must be a valid non-null pointer.
#[no_mangle]
pub unsafe extern "C" fn vento_set_night_timer(
    client: *const VentoClient,
    hours: u8,
    minutes: u8,
) -> VentoStatus {
    map_result((*client).set_night_timer(hours, minutes))
}

/// Set party timer duration.
///
/// # Safety
/// `client` must be a valid non-null pointer.
#[no_mangle]
pub unsafe extern "C" fn vento_set_party_timer(
    client: *const VentoClient,
    hours: u8,
    minutes: u8,
) -> VentoStatus {
    map_result((*client).set_party_timer(hours, minutes))
}

// ── Humidity ──────────────────────────────────────────────────────────────────

/// Set humidity sensor mode: 0 = off, 1 = internal, 2 = external.
///
/// # Safety
/// `client` must be a valid non-null pointer.
#[no_mangle]
pub unsafe extern "C" fn vento_set_humidity_sensor(
    client: *const VentoClient,
    sensor: u8,
) -> VentoStatus {
    map_result((*client).set_humidity_sensor(sensor))
}

/// Set humidity threshold (40–80 %RH).
///
/// # Safety
/// `client` must be a valid non-null pointer.
#[no_mangle]
pub unsafe extern "C" fn vento_set_humidity_threshold(
    client: *const VentoClient,
    rh: u8,
) -> VentoStatus {
    map_result((*client).set_humidity_threshold(rh))
}

// ── Schedule ──────────────────────────────────────────────────────────────────

/// Enable or disable the weekly schedule (enabled != 0 means enable).
///
/// # Safety
/// `client` must be a valid non-null pointer.
#[no_mangle]
pub unsafe extern "C" fn vento_enable_weekly_schedule(
    client: *const VentoClient,
    enabled: u8,
) -> VentoStatus {
    map_result((*client).enable_weekly_schedule(enabled != 0))
}

/// Write one schedule period.
///
/// - `day`: 0–9
/// - `period`: 1–4
/// - `speed`: 0–3
/// - `end_h`/`end_m`: end time of the period
///
/// # Safety
/// `client` must be a valid non-null pointer.
#[no_mangle]
pub unsafe extern "C" fn vento_set_schedule_period(
    client: *const VentoClient,
    day: u8,
    period: u8,
    speed: u8,
    end_h: u8,
    end_m: u8,
) -> VentoStatus {
    map_result((*client).set_schedule_period(day, period, speed, end_h, end_m))
}

/// Read one schedule period into `*out`.
///
/// # Safety
/// `client` and `out` must be valid non-null pointers.
#[no_mangle]
pub unsafe extern "C" fn vento_get_schedule_period(
    client: *const VentoClient,
    day: u8,
    period: u8,
    out: *mut VentoSchedulePeriod,
) -> VentoStatus {
    match (*client).get_schedule_period(day, period) {
        Ok(p) => {
            (*out).period_number = p.period_number;
            (*out).end_hours     = p.end_hours;
            (*out).end_minutes   = p.end_minutes;
            (*out).speed         = p.speed;
            VentoStatus::Ok
        }
        Err(e) => { set_last_error(&e); to_status(&e) }
    }
}

// ── RTC ───────────────────────────────────────────────────────────────────────

/// Synchronise the fan's real-time clock.
///
/// # Safety
/// `client` and `dt` must be valid non-null pointers.
#[no_mangle]
pub unsafe extern "C" fn vento_set_rtc(
    client: *const VentoClient,
    dt: *const VentoRtcInput,
) -> VentoStatus {
    let dt = &*dt;
    let rtc = SetRtcTime {
        year:        dt.year,
        month:       dt.month,
        day:         dt.day,
        day_of_week: dt.day_of_week,
        hour:        dt.hour,
        minute:      dt.minute,
        second:      dt.second,
    };
    map_result((*client).set_rtc(&rtc))
}

// ── Filter ────────────────────────────────────────────────────────────────────

/// Reset the filter replacement countdown.
///
/// # Safety
/// `client` must be a valid non-null pointer.
#[no_mangle]
pub unsafe extern "C" fn vento_reset_filter_timer(client: *const VentoClient) -> VentoStatus {
    map_result((*client).reset_filter_timer())
}

// ── Alarms ────────────────────────────────────────────────────────────────────

/// Clear all active alarms.
///
/// # Safety
/// `client` must be a valid non-null pointer.
#[no_mangle]
pub unsafe extern "C" fn vento_reset_alarms(client: *const VentoClient) -> VentoStatus {
    map_result((*client).reset_alarms())
}

// ── Misc ──────────────────────────────────────────────────────────────────────

/// Allow or deny cloud access.
///
/// # Safety
/// `client` must be a valid non-null pointer.
#[no_mangle]
pub unsafe extern "C" fn vento_set_cloud_permission(
    client: *const VentoClient,
    allowed: u8,
) -> VentoStatus {
    map_result((*client).set_cloud_permission(allowed != 0))
}

/// Restore factory defaults. Use with caution.
///
/// # Safety
/// `client` must be a valid non-null pointer.
#[no_mangle]
pub unsafe extern "C" fn vento_factory_reset(client: *const VentoClient) -> VentoStatus {
    map_result((*client).factory_reset())
}

// ── Discovery ─────────────────────────────────────────────────────────────────

/// Discover fans on the local network.
///
/// On `Ok`, `out->devices` points to a heap-allocated array of `out->count` entries.
/// Free with `vento_device_list_free` when done.
///
/// # Safety
/// `broadcast` must be a valid non-null C string. `out` must be a valid non-null pointer.
#[no_mangle]
pub unsafe extern "C" fn vento_discover(
    broadcast: *const c_char,
    port: u16,
    timeout_secs: f64,
    max_devices: u32,
    out: *mut VentoDeviceList,
) -> VentoStatus {
    match VentoClient::discover(str_from_ptr(broadcast), port, timeout_secs, max_devices as usize) {
        Ok(devices) => {
            let mut c_devices: Vec<VentoDiscoveredDevice> = devices
                .iter()
                .map(|d| {
                    let mut c = VentoDiscoveredDevice {
                        ip:             [0; 64],
                        device_id:      [0; 64],
                        unit_type:      d.unit_type,
                        unit_type_name: [0; 128],
                    };
                    copy_cstr(&mut c.ip, &d.ip);
                    copy_cstr(&mut c.device_id, &d.device_id);
                    copy_cstr(&mut c.unit_type_name, &d.unit_type_name);
                    c
                })
                .collect();
            let count = c_devices.len() as u32;
            let ptr = c_devices.as_mut_ptr();
            std::mem::forget(c_devices);
            (*out).devices = ptr;
            (*out).count = count;
            VentoStatus::Ok
        }
        Err(e) => { set_last_error(&e); to_status(&e) }
    }
}

/// Free a device list returned by `vento_discover`. Passing a null or empty list is a no-op.
///
/// # Safety
/// `list` must be a pointer to a `VentoDeviceList` previously filled by `vento_discover`, or null.
#[no_mangle]
pub unsafe extern "C" fn vento_device_list_free(list: *mut VentoDeviceList) {
    if list.is_null() || (*list).devices.is_null() {
        return;
    }
    let n = (*list).count as usize;
    drop(Vec::from_raw_parts((*list).devices, n, n));
    (*list).devices = std::ptr::null_mut();
    (*list).count = 0;
}

// ── Tests ─────────────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;
    use std::ffi::CString;

    fn make_client() -> *mut VentoClient {
        let host  = CString::new("127.0.0.1").unwrap();
        let id    = CString::new("SIMFAN0000000001").unwrap();
        let pwd   = CString::new("1111").unwrap();
        vento_client_new(host.as_ptr(), id.as_ptr(), pwd.as_ptr())
    }

    #[test]
    fn client_new_and_free() {
        let c = make_client();
        assert!(!c.is_null());
        unsafe { vento_client_free(c); }
    }

    #[test]
    fn null_args_return_null() {
        let c = vento_client_new(std::ptr::null(), std::ptr::null(), std::ptr::null());
        assert!(c.is_null());
    }

    #[test]
    fn bad_speed_sets_error() {
        let c = make_client();
        let status = unsafe { vento_set_speed(c, 5) };
        assert_eq!(status, VentoStatus::ErrValue);
        let msg = unsafe { std::ffi::CStr::from_ptr(vento_last_error()).to_str().unwrap() };
        assert!(msg.contains("speed"), "error message: {msg}");
        unsafe { vento_client_free(c); }
    }

    #[test]
    fn bad_humidity_threshold_sets_error() {
        let c = make_client();
        let status = unsafe { vento_set_humidity_threshold(c, 99) };
        assert_eq!(status, VentoStatus::ErrValue);
        unsafe { vento_client_free(c); }
    }

    #[test]
    fn device_list_free_null_is_noop() {
        unsafe { vento_device_list_free(std::ptr::null_mut()); }
    }

    #[test]
    fn device_list_free_empty_is_noop() {
        let mut list = VentoDeviceList { devices: std::ptr::null_mut(), count: 0 };
        unsafe { vento_device_list_free(&mut list); }
    }
}
