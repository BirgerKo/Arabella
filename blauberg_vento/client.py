from __future__ import annotations
import logging
from datetime import datetime
from typing import Sequence
from .exceptions import VentoValueError, VentoUnsupportedParamError
from .models import (DeviceState, DiscoveredDevice, FilterCountdown, FirmwareVersion,
    MachineHours, RtcCalendar, RtcTime, SchedulePeriod, TimerCountdown, WifiConfig)
from .parameters import DEFAULT_PORT, Func, Param
from .protocol import (build_discovery, build_read, build_write, build_write_resp,
    build_increment, build_decrement, decode_filter_countdown, decode_firmware,
    decode_int, decode_ip, decode_machine_hours, decode_rtc_calendar, decode_rtc_time,
    decode_schedule, decode_text, decode_timer_countdown, encode_ip, parse_response)
from .transport import AsyncVentoTransport, VentoTransport
log = logging.getLogger(__name__)

def _check_range(name, val, lo, hi):
    if not lo <= val <= hi: raise VentoValueError(f"{name} must be in [{lo},{hi}], got {val}")
def _check_choices(name, val, choices):
    if val not in choices: raise VentoValueError(f"{name} must be one of {sorted(choices)}, got {val}")

_G1 = [Param.POWER,Param.SPEED,Param.BOOST_STATUS,Param.TIMER_MODE,Param.TIMER_COUNTDOWN,
       Param.HUMIDITY_SENSOR,Param.RELAY_SENSOR,Param.VOLTAGE_SENSOR,Param.HUMIDITY_THRESHOLD,
       Param.VOLTAGE_THRESHOLD,Param.BATTERY_VOLTAGE,Param.CURRENT_HUMIDITY,Param.VOLTAGE_SENSOR_VAL,
       Param.RELAY_STATE,Param.MANUAL_SPEED,Param.FAN1_SPEED,Param.FAN2_SPEED]
_G2 = [Param.FILTER_COUNTDOWN,Param.FILTER_INDICATOR,Param.BOOST_DELAY,Param.RTC_TIME,
       Param.RTC_CALENDAR,Param.WEEKLY_SCHEDULE_EN,Param.DEVICE_SEARCH,Param.MACHINE_HOURS,
       Param.ALARM_STATUS,Param.CLOUD_PERMISSION,Param.FIRMWARE_VERSION,Param.OPERATION_MODE,Param.UNIT_TYPE]
_G3 = [Param.WIFI_MODE,Param.WIFI_SSID,Param.WIFI_ENCRYPTION,Param.WIFI_CHANNEL,
       Param.WIFI_DHCP,Param.WIFI_IP,Param.WIFI_SUBNET,Param.WIFI_GATEWAY,Param.WIFI_CURRENT_IP]
_G4 = [Param.HUMIDITY_STATUS,Param.VOLTAGE_STATUS,Param.NIGHT_TIMER,Param.PARTY_TIMER]

class _SB:
    def __init__(self, r, ip): self._r = r; self._host = ip
    def _i(self, p, d=None): v = self._r.get(p); return decode_int(v) if v is not None else d
    def _t(self, p, d=''): v = self._r.get(p); return decode_text(v) if v is not None else d
    def _ip(self, p, d=''): v = self._r.get(p); return decode_ip(v) if v is not None else d
    def build(self):
        r = self._r; s = DeviceState(ip=self._host)
        s.device_id = self._t(Param.DEVICE_SEARCH)
        s.unit_type = self._i(Param.UNIT_TYPE) or 0
        pwr = self._i(Param.POWER); s.power = bool(pwr) if pwr is not None else None
        s.speed = self._i(Param.SPEED); s.manual_speed = self._i(Param.MANUAL_SPEED)
        s.operation_mode = self._i(Param.OPERATION_MODE)
        b = self._i(Param.BOOST_STATUS); s.boost_active = bool(b) if b is not None else None
        s.boost_delay_minutes = self._i(Param.BOOST_DELAY)
        s.timer_mode = self._i(Param.TIMER_MODE)
        if Param.TIMER_COUNTDOWN in r: s.timer_countdown = TimerCountdown(**decode_timer_countdown(r[Param.TIMER_COUNTDOWN]))
        if Param.NIGHT_TIMER in r: v = r[Param.NIGHT_TIMER]; s.night_timer = (v[1], v[0])
        if Param.PARTY_TIMER in r: v = r[Param.PARTY_TIMER]; s.party_timer = (v[1], v[0])
        s.humidity_sensor = self._i(Param.HUMIDITY_SENSOR)
        s.humidity_threshold = self._i(Param.HUMIDITY_THRESHOLD)
        s.current_humidity = self._i(Param.CURRENT_HUMIDITY)
        hs = self._i(Param.HUMIDITY_STATUS); s.humidity_status = bool(hs) if hs is not None else None
        s.relay_sensor = self._i(Param.RELAY_SENSOR)
        rs = self._i(Param.RELAY_STATE); s.relay_state = bool(rs) if rs is not None else None
        s.voltage_sensor = self._i(Param.VOLTAGE_SENSOR)
        s.voltage_threshold = self._i(Param.VOLTAGE_THRESHOLD)
        s.voltage_sensor_value = self._i(Param.VOLTAGE_SENSOR_VAL)
        vs = self._i(Param.VOLTAGE_STATUS); s.voltage_status = bool(vs) if vs is not None else None
        s.fan1_rpm = self._i(Param.FAN1_SPEED); s.fan2_rpm = self._i(Param.FAN2_SPEED)
        if Param.FILTER_COUNTDOWN in r: s.filter_countdown = FilterCountdown(**decode_filter_countdown(r[Param.FILTER_COUNTDOWN]))
        fi = self._i(Param.FILTER_INDICATOR); s.filter_needs_replacement = bool(fi) if fi is not None else None
        s.alarm_status = self._i(Param.ALARM_STATUS)
        if Param.MACHINE_HOURS in r: s.machine_hours = MachineHours(**decode_machine_hours(r[Param.MACHINE_HOURS]))
        s.battery_voltage_mv = self._i(Param.BATTERY_VOLTAGE)
        if Param.FIRMWARE_VERSION in r: s.firmware = FirmwareVersion(**decode_firmware(r[Param.FIRMWARE_VERSION]))
        if Param.RTC_TIME in r: s.rtc_time = RtcTime(**decode_rtc_time(r[Param.RTC_TIME]))
        if Param.RTC_CALENDAR in r: s.rtc_calendar = RtcCalendar(**decode_rtc_calendar(r[Param.RTC_CALENDAR]))
        se = self._i(Param.WEEKLY_SCHEDULE_EN); s.weekly_schedule_enabled = bool(se) if se is not None else None
        if any(p in r for p in (Param.WIFI_MODE, Param.WIFI_SSID, Param.WIFI_IP)):
            s.wifi = WifiConfig(mode=self._i(Param.WIFI_MODE,0), ssid=self._t(Param.WIFI_SSID),
                encryption=self._i(Param.WIFI_ENCRYPTION,52), channel=self._i(Param.WIFI_CHANNEL,1),
                dhcp=bool(self._i(Param.WIFI_DHCP,1)), ip=self._ip(Param.WIFI_IP),
                subnet=self._ip(Param.WIFI_SUBNET), gateway=self._ip(Param.WIFI_GATEWAY),
                current_ip=self._ip(Param.WIFI_CURRENT_IP))
        cl = self._i(Param.CLOUD_PERMISSION); s.cloud_permitted = bool(cl) if cl is not None else None
        return s

class VentoClient:
    def __init__(self, host, device_id, password='1111', port=DEFAULT_PORT, timeout=3.0):
        self.host=host; self.device_id=device_id; self.password=password; self.port=port
        self._transport = VentoTransport(timeout=timeout)
    def _sr(self, pkt): return parse_response(self._transport.send_recv(self.host, pkt, self.port))
    def _so(self, pkt): self._transport.send_only(self.host, pkt, self.port)
    def read_params(self, params): return self._sr(build_read(self.device_id, self.password, list(params)))
    def write_params(self, pv): self._so(build_write(self.device_id, self.password, pv))
    def write_params_with_response(self, pv): return self._sr(build_write_resp(self.device_id, self.password, pv))
    def increment_params(self, params): return self._sr(build_increment(self.device_id, self.password, list(params)))
    def decrement_params(self, params): return self._sr(build_decrement(self.device_id, self.password, list(params)))
    def get_state(self):
        combined = {}
        for g in (_G1, _G2, _G3, _G4):
            try: combined.update(self.read_params(g))
            except VentoUnsupportedParamError as e: log.debug("Unsupported: %s", e.params)
        return _SB(combined, self.host).build()
    def turn_on(self): self.write_params({Param.POWER: 1})
    def turn_off(self): self.write_params({Param.POWER: 0})
    def toggle_power(self): self.write_params({Param.POWER: 2})
    def set_speed(self, s): _check_choices('speed',s,{1,2,3}); self.write_params({Param.SPEED: s})
    def set_manual_speed(self, v):
        _check_range('manual_speed',v,0,255); self.write_params({Param.SPEED:255, Param.MANUAL_SPEED:v})
    def speed_up(self): return self.increment_params([Param.SPEED])
    def speed_down(self): return self.decrement_params([Param.SPEED])
    def set_mode(self, m): _check_choices('mode',m,{0,1,2}); self.write_params({Param.OPERATION_MODE: m})
    def set_ventilation(self): self.set_mode(0)
    def set_heat_recovery(self): self.set_mode(1)
    def set_supply(self): self.set_mode(2)
    def get_boost_status(self): return bool(decode_int(self.read_params([Param.BOOST_STATUS])[Param.BOOST_STATUS]))
    def set_boost_delay(self, m): _check_range('boost_delay',m,0,60); self.write_params({Param.BOOST_DELAY: m})
    def set_timer_mode(self, m): _check_choices('timer_mode',m,{0,1,2}); self.write_params({Param.TIMER_MODE: m})
    def set_night_timer(self, h, m):
        _check_range('hours',h,0,23); _check_range('min',m,0,59)
        self.write_params({Param.NIGHT_TIMER: bytes([m,h])})
    def set_party_timer(self, h, m):
        _check_range('hours',h,0,23); _check_range('min',m,0,59)
        self.write_params({Param.PARTY_TIMER: bytes([m,h])})
    def get_timer_countdown(self):
        return TimerCountdown(**decode_timer_countdown(self.read_params([Param.TIMER_COUNTDOWN])[Param.TIMER_COUNTDOWN]))
    def set_humidity_sensor(self, s): _check_choices('humidity_sensor',s,{0,1,2}); self.write_params({Param.HUMIDITY_SENSOR: s})
    def set_humidity_threshold(self, rh): _check_range('humidity_threshold',rh,40,80); self.write_params({Param.HUMIDITY_THRESHOLD: rh})
    def get_current_humidity(self): return decode_int(self.read_params([Param.CURRENT_HUMIDITY])[Param.CURRENT_HUMIDITY])
    def set_relay_sensor(self, s): _check_choices('relay_sensor',s,{0,1,2}); self.write_params({Param.RELAY_SENSOR: s})
    def set_voltage_sensor(self, s): _check_choices('voltage_sensor',s,{0,1,2}); self.write_params({Param.VOLTAGE_SENSOR: s})
    def set_voltage_threshold(self, p): _check_range('voltage_threshold',p,5,100); self.write_params({Param.VOLTAGE_THRESHOLD: p})
    def enable_weekly_schedule(self, en): self.write_params({Param.WEEKLY_SCHEDULE_EN: 1 if en else 0})
    def set_schedule_period(self, day, period, speed, end_h, end_m):
        _check_range('day',day,0,9); _check_range('period',period,1,4)
        _check_range('speed',speed,0,3); _check_range('end_h',end_h,0,23); _check_range('end_m',end_m,0,59)
        self.write_params({Param.SCHEDULE_SETUP: bytes([day,period,speed,0,end_m,end_h])})
    def sync_rtc(self): self.set_rtc(datetime.now())
    def set_rtc(self, dt):
        dow = dt.weekday() + 1
        self.write_params({Param.RTC_TIME: bytes([dt.second,dt.minute,dt.hour]),
                           Param.RTC_CALENDAR: bytes([dt.day,dow,dt.month,dt.year%100])})
    def get_rtc(self):
        raw = self.read_params([Param.RTC_TIME, Param.RTC_CALENDAR])
        return RtcTime(**decode_rtc_time(raw[Param.RTC_TIME])), RtcCalendar(**decode_rtc_calendar(raw[Param.RTC_CALENDAR]))
    def get_filter_status(self):
        raw = self.read_params([Param.FILTER_COUNTDOWN, Param.FILTER_INDICATOR])
        return FilterCountdown(**decode_filter_countdown(raw[Param.FILTER_COUNTDOWN])), bool(decode_int(raw[Param.FILTER_INDICATOR]))
    def reset_filter_timer(self): self.write_params({Param.FILTER_RESET: 1})
    def get_machine_hours(self):
        return MachineHours(**decode_machine_hours(self.read_params([Param.MACHINE_HOURS])[Param.MACHINE_HOURS]))
    def reset_alarms(self): self.write_params({Param.RESET_ALARMS: 1})
    def get_alarm_status(self): return decode_int(self.read_params([Param.ALARM_STATUS])[Param.ALARM_STATUS])
    def get_firmware_version(self):
        return FirmwareVersion(**decode_firmware(self.read_params([Param.FIRMWARE_VERSION])[Param.FIRMWARE_VERSION]))
    def get_unit_type(self): return decode_int(self.read_params([Param.UNIT_TYPE])[Param.UNIT_TYPE])
    def get_device_id(self): return decode_text(self.read_params([Param.DEVICE_SEARCH])[Param.DEVICE_SEARCH])
    def get_wifi_config(self):
        raw = self.read_params([Param.WIFI_MODE,Param.WIFI_SSID,Param.WIFI_ENCRYPTION,Param.WIFI_CHANNEL,
            Param.WIFI_DHCP,Param.WIFI_IP,Param.WIFI_SUBNET,Param.WIFI_GATEWAY,Param.WIFI_CURRENT_IP])
        return WifiConfig(mode=decode_int(raw.get(Param.WIFI_MODE,b'\x01')),
            ssid=decode_text(raw.get(Param.WIFI_SSID,b'')),
            encryption=decode_int(raw.get(Param.WIFI_ENCRYPTION,b'4')),
            channel=decode_int(raw.get(Param.WIFI_CHANNEL,b'\x06')),
            dhcp=bool(decode_int(raw.get(Param.WIFI_DHCP,b'\x01'))),
            ip=decode_ip(raw.get(Param.WIFI_IP,bytes(4))),
            subnet=decode_ip(raw.get(Param.WIFI_SUBNET,bytes(4))),
            gateway=decode_ip(raw.get(Param.WIFI_GATEWAY,bytes(4))),
            current_ip=decode_ip(raw.get(Param.WIFI_CURRENT_IP,bytes(4))))
    def set_wifi_client(self, ssid, wifi_password, dhcp=True, encryption=52, static_ip='', subnet='', gateway=''):
        params = {Param.WIFI_MODE:1, Param.WIFI_SSID:ssid.encode('ascii'),
                  Param.WIFI_PASSWORD:wifi_password.encode('ascii'),
                  Param.WIFI_ENCRYPTION:encryption, Param.WIFI_DHCP:1 if dhcp else 0}
        if not dhcp:
            if not static_ip: raise VentoValueError("static_ip required when dhcp=False")
            params[Param.WIFI_IP] = encode_ip(static_ip)
            params[Param.WIFI_SUBNET] = encode_ip(subnet or '255.255.255.0')
            params[Param.WIFI_GATEWAY] = encode_ip(gateway or static_ip)
        self.write_params(params)
    def set_wifi_ap(self, channel=6):
        _check_range('channel',channel,1,13); self.write_params({Param.WIFI_MODE:2, Param.WIFI_CHANNEL:channel})
    def apply_wifi_config(self): self.write_params({Param.WIFI_APPLY: 1})
    def discard_wifi_config(self): self.write_params({Param.WIFI_DISCARD: 1})
    def change_password(self, pw):
        if len(pw) > 8: raise VentoValueError("Password max 8 characters")
        self.write_params({Param.DEVICE_PASSWORD: pw.encode('ascii')}); self.password = pw
    def set_cloud_permission(self, allowed): self.write_params({Param.CLOUD_PERMISSION: 1 if allowed else 0})
    def factory_reset(self): self.write_params({Param.FACTORY_RESET: 1})
    @staticmethod
    def discover(broadcast='255.255.255.255', port=DEFAULT_PORT, timeout=3.0):
        pkt = build_discovery(); t = VentoTransport(timeout=timeout); devices = []
        for item in t.discover(pkt, broadcast, port, timeout):
            try:
                resp = parse_response(item['raw'])
                devices.append(DiscoveredDevice(ip=item['ip'],
                    device_id=decode_text(resp.get(Param.DEVICE_SEARCH, b'')),
                    unit_type=decode_int(resp.get(Param.UNIT_TYPE, b'\x00\x00'))))
            except Exception as e: log.warning("Discovery parse error %s: %s", item['ip'], e)
        return devices
    def __repr__(self): return f"<VentoClient host={self.host!r} id={self.device_id!r}>"

class AsyncVentoClient:
    def __init__(self, host, device_id, password='1111', port=DEFAULT_PORT, timeout=3.0):
        self.host=host; self.device_id=device_id; self.password=password; self.port=port
        self._transport = AsyncVentoTransport(timeout=timeout)
    async def __aenter__(self): return self
    async def __aexit__(self, *_): pass
    async def _sr(self, pkt): return parse_response(await self._transport.send_recv(self.host, pkt, self.port))
    async def _so(self, pkt): await self._transport.send_only(self.host, pkt, self.port)
    async def read_params(self, params): return await self._sr(build_read(self.device_id, self.password, list(params)))
    async def write_params(self, pv): await self._so(build_write(self.device_id, self.password, pv))
    async def write_params_with_response(self, pv): return await self._sr(build_write_resp(self.device_id, self.password, pv))
    async def get_state(self):
        combined = {}
        for g in (_G1, _G2, _G3, _G4):
            try: combined.update(await self.read_params(g))
            except VentoUnsupportedParamError as e: log.debug("Unsupported: %s", e.params)
        return _SB(combined, self.host).build()
    async def turn_on(self): await self.write_params({Param.POWER: 1})
    async def turn_off(self): await self.write_params({Param.POWER: 0})
    async def toggle_power(self): await self.write_params({Param.POWER: 2})
    async def set_speed(self, s): _check_choices('speed',s,{1,2,3}); await self.write_params({Param.SPEED: s})
    async def set_manual_speed(self, v):
        _check_range('manual_speed',v,0,255); await self.write_params({Param.SPEED:255, Param.MANUAL_SPEED:v})
    async def set_mode(self, m): _check_choices('mode',m,{0,1,2}); await self.write_params({Param.OPERATION_MODE: m})
    async def set_timer_mode(self, m): _check_choices('timer_mode',m,{0,1,2}); await self.write_params({Param.TIMER_MODE: m})
    async def set_night_timer(self, h, m): await self.write_params({Param.NIGHT_TIMER: bytes([m,h])})
    async def set_party_timer(self, h, m): await self.write_params({Param.PARTY_TIMER: bytes([m,h])})
    async def set_humidity_sensor(self, s):
        _check_choices('humidity_sensor',s,{0,1,2}); await self.write_params({Param.HUMIDITY_SENSOR: s})
    async def set_humidity_threshold(self, rh):
        _check_range('humidity_threshold',rh,40,80); await self.write_params({Param.HUMIDITY_THRESHOLD: rh})
    async def reset_filter_timer(self): await self.write_params({Param.FILTER_RESET: 1})
    async def reset_alarms(self): await self.write_params({Param.RESET_ALARMS: 1})
    async def sync_rtc(self): await self.set_rtc(datetime.now())
    async def set_rtc(self, dt):
        dow = dt.weekday() + 1
        await self.write_params({Param.RTC_TIME: bytes([dt.second,dt.minute,dt.hour]),
                                  Param.RTC_CALENDAR: bytes([dt.day,dow,dt.month,dt.year%100])})
    async def factory_reset(self): await self.write_params({Param.FACTORY_RESET: 1})
    async def change_password(self, pw):
        if len(pw) > 8: raise VentoValueError("Password max 8 characters")
        await self.write_params({Param.DEVICE_PASSWORD: pw.encode('ascii')}); self.password = pw
    @staticmethod
    async def discover(broadcast='255.255.255.255', port=DEFAULT_PORT, timeout=3.0):
        pkt = build_discovery(); t = AsyncVentoTransport(timeout=timeout); devices = []
        for item in await t.discover(pkt, broadcast, port, timeout):
            try:
                resp = parse_response(item['raw'])
                devices.append(DiscoveredDevice(ip=item['ip'],
                    device_id=decode_text(resp.get(Param.DEVICE_SEARCH, b'')),
                    unit_type=decode_int(resp.get(Param.UNIT_TYPE, b'\x00\x00'))))
            except Exception as e: log.warning("Discovery parse error %s: %s", item['ip'], e)
        return devices
    def __repr__(self): return f"<AsyncVentoClient host={self.host!r} id={self.device_id!r}>"
