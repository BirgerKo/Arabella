"""
VentoFanSim — UDP Blauberg Vento Expert Wi-Fi fan simulator.

Simulates one or more real devices on the LAN so the GUI can be demoed
without hardware.  Multiple virtual devices share a single UDP socket on
port 4000 — exactly as multiple real fans on the same LAN would behave.

Usage:
    python3.11 -m ventocontrol.simulator              # 1 device (default)
    python3.11 -m ventocontrol.simulator --count 3    # 3 virtual fans
    python3.11 -m ventocontrol.simulator --start-index 1  # SIMFAN0000000002 …
    python3.11 -m ventocontrol.simulator --help

Container usage (one container per fan):
    FAN_INDEX=0  python3.11 -m ventocontrol.simulator  # → SIMFAN0000000001
    FAN_INDEX=1  python3.11 -m ventocontrol.simulator  # → SIMFAN0000000002
"""
from __future__ import annotations

import argparse
import os
import random
import select
import socket
import struct
import time
from datetime import datetime
from typing import Optional

from blauberg_vento.exceptions import VentoChecksumError, VentoProtocolError
from blauberg_vento.parameters import (
    CMD_FUNC, CMD_NOT_SUP, CMD_PAGE, CMD_SIZE,
    DEFAULT_DEVICE_ID, PARAM_META, Func, Param,
)
from blauberg_vento.protocol import (
    _find_data_start,   # noqa: PLC2701 — intentional use of internal helper
    build_packet,
    verify_checksum,
)

# ---------------------------------------------------------------------------
# Shared constants
# ---------------------------------------------------------------------------

SIM_PASSWORD  = '1111'
SIM_UNIT_TYPE = 3          # Vento Expert A50-1/A85-1/A100-1 W V.2
SIM_ID_PREFIX = 'SIMFAN'   # 6-char prefix; total device ID is always 16 chars

# Fan RPM targets for preset speeds: (fan1, fan2)
_RPM_TARGETS = {1: (640, 560), 2: (1260, 1100), 3: (1860, 1640)}
_RAMP_RATE             = 80.0   # RPM/s
_MANUAL_RPM_MAX_FAN1   = 2000   # RPM at manual speed 255 for fan 1
_MANUAL_RPM_MAX_FAN2   = 1800   # RPM at manual speed 255 for fan 2
_RPM_NOISE_STDDEV      = 2.5    # Gaussian jitter added when fans are spinning
_HUMIDITY_NOISE_STDDEV = 0.06   # Gaussian humidity drift per second
_STATUS_INTERVAL       = 5.0    # Seconds between periodic console status lines
_SELECT_TIMEOUT        = 0.05   # Seconds to wait in select() per main-loop tick

def _make_sim_id(index: int, prefix: str = SIM_ID_PREFIX) -> str:
    """Return a unique 16-char device ID for the n-th virtual device (0-based)."""
    num_digits = 16 - len(prefix)
    return f'{prefix}{index + 1:0{num_digits}d}'


# ---------------------------------------------------------------------------
# Packet helpers  (simulator-side parsing / building)
# ---------------------------------------------------------------------------

def _parse_read_request_data(data: bytes) -> list[int]:
    """Extract ordered list of param codes from a READ request DATA section."""
    params: list[int] = []
    page = 0x00
    i = 0
    while i < len(data):
        b = data[i]
        if b == CMD_PAGE:
            i += 1
            if i < len(data):
                page = data[i]; i += 1
            continue
        if b == CMD_FUNC:
            i += 2
            continue
        params.append((page << 8) | b)
        i += 1
    return params


def _parse_write_data(data: bytes) -> dict[int, bytes]:
    """Extract {param_code: value_bytes} from a WRITE / WRITE_RESP DATA section."""
    result: dict[int, bytes] = {}
    page = 0x00
    param_sz = 1
    i = 0
    while i < len(data):
        b = data[i]
        if b == CMD_PAGE:
            i += 1
            if i < len(data):
                page = data[i]; i += 1
            param_sz = 1; continue
        if b == CMD_FUNC:
            i += 2; param_sz = 1; continue
        if b == CMD_SIZE:
            i += 1
            param_sz = data[i] if i < len(data) else 1
            i += 1
            if i < len(data):
                b = data[i]
            else:
                break
        param_num = (page << 8) | b; i += 1
        val_end = i + param_sz
        if val_end > len(data):
            break
        result[param_num] = bytes(data[i:val_end])
        i = val_end; param_sz = 1
    return result


def _build_response_data(requested: list[int], state: dict[int, bytes]) -> bytes:
    """
    Build the DATA section for a FUNC=0x06 response.

    Supported params are encoded with their current byte values;
    unknown params are marked CMD_NOT_SUP.
    """
    data = bytearray(); page = 0x00
    for p in requested:
        high, low = (p >> 8) & 0xFF, p & 0xFF
        if high != page:
            data += bytes([CMD_PAGE, high]); page = high
        val = state.get(p)
        if val is None:
            data += bytes([CMD_NOT_SUP, low])
        else:
            sz = len(val)
            if sz != 1:
                data += bytes([CMD_SIZE, sz])
            data.append(low); data += val
    return bytes(data)


# ---------------------------------------------------------------------------
# Console helpers
# ---------------------------------------------------------------------------

def _log(tag: str, addr: tuple, params: Optional[dict] = None,
         prefix: str = '') -> None:
    ts = datetime.now().strftime('%H:%M:%S')
    prefix_str = f'{prefix} ' if prefix else ''
    if params:
        parts = []
        for k, v in list(params.items())[:6]:
            try:
                name = Param(k).name
            except ValueError:
                name = f'0x{k:04X}'
            if v is None:
                value_str = '—'
            elif len(v) == 0:
                value_str = '(empty)'
            elif len(v) <= 2:
                value_str = str(int.from_bytes(v, 'little'))
            else:
                value_str = v.hex()
            parts.append(f'{name}={value_str}')
        extra = f'  +{len(params) - 6} more' if len(params) > 6 else ''
        params_str = ', '.join(parts) + extra
    else:
        params_str = ''
    print(f'  [{ts}] {prefix_str}{tag:<5} {addr[0]}:{addr[1]}  {params_str}')


def _banner(lan_ip: str, devices: list['SimDevice'], port: int) -> None:
    box_width = 66
    def row(text=''):
        pad = box_width - len(text) - 2
        return f'║ {text}{" " * pad} ║'

    n = len(devices)
    title = f'VentoFanSim — {n} virtual Vento Expert{"s" if n > 1 else ""}'
    print('╔' + '═' * box_width + '╗')
    print(row(title))
    print('╠' + '═' * box_width + '╣')
    for d in devices:
        print(row(f'Device #{d.index + 1}  │  ID: {d.device_id}   Pwd: {d.password}'))
    print('╠' + '═' * box_width + '╣')
    print(row(f'LAN IP : {lan_ip}   Port : {port}'))
    print(row('Use auto-discovery  OR  enter ID + IP manually'))
    print('╚' + '═' * box_width + '╝')
    print()
    print('  Listening … (Ctrl+C to stop)\n')


# ---------------------------------------------------------------------------
# Per-device simulated unit
# ---------------------------------------------------------------------------

class SimDevice:
    """
    One virtual Blauberg Vento Expert fan.

    Maintains its own state dict, physics (RPM ramp, humidity drift) and
    handles packets addressed to its device ID.  Devices at different
    indices start with different speeds / modes / humidity levels so the
    demo looks more realistic.
    """

    _MODE_NAMES  = {0: 'Ventilation', 1: 'HeatRecovery', 2: 'Supply'}
    _SPEED_NAMES = {1: 'Spd1', 2: 'Spd2', 3: 'Spd3', 255: 'Man'}
    _ALARM_NAMES = {0: 'OK', 1: 'ALARM', 2: 'Warn'}

    # Initial variety per index slot (wraps around for index >= 3)
    _VARIANTS = [
        dict(speed=1, mode=0, humidity=48.0, power=False),   # #1 — off, slow
        dict(speed=2, mode=1, humidity=63.0, power=True),    # #2 — running, recovery
        dict(speed=3, mode=2, humidity=72.0, power=True),    # #3 — running fast, supply
    ]


    def __init__(self, index: int, password: str = SIM_PASSWORD,
                 unit_type: int = SIM_UNIT_TYPE,
                 id_prefix: str = SIM_ID_PREFIX) -> None:
        self.index      = index
        self.device_id  = _make_sim_id(index, id_prefix)
        self.id_bytes   = self.device_id.encode('ascii')
        self.password   = password
        self._unit_type = unit_type
        self._start     = time.monotonic()

        v = self._VARIANTS[index % len(self._VARIANTS)]
        self._fan1_rpm = 0.0
        self._fan2_rpm = 0.0
        self._humidity = v['humidity']
        self._state: dict[int, bytes] = self._make_initial_state(v)

    # ------------------------------------------------------------------
    # Initial state
    # ------------------------------------------------------------------

    def _make_initial_state(self, v: dict) -> dict[int, bytes]:
        now = datetime.now()
        return {
            # ── Group 1 ─────────────────────────────────────────────
            Param.POWER:              bytes([int(v['power'])]),
            Param.SPEED:              bytes([v['speed']]),
            Param.BOOST_STATUS:       b'\x00',
            Param.TIMER_MODE:         b'\x00',
            Param.TIMER_COUNTDOWN:    b'\x00\x00\x00',
            Param.HUMIDITY_SENSOR:    b'\x01',
            Param.RELAY_SENSOR:       b'\x00',
            Param.VOLTAGE_SENSOR:     b'\x00',
            Param.HUMIDITY_THRESHOLD: b'\x3C',                         # 60 %RH
            Param.VOLTAGE_THRESHOLD:  b'\x32',
            Param.BATTERY_VOLTAGE:    struct.pack('<H', 4800),
            Param.CURRENT_HUMIDITY:   bytes([int(v['humidity'])]),
            Param.VOLTAGE_SENSOR_VAL: b'\x00',
            Param.RELAY_STATE:        b'\x00',
            Param.HUMIDITY_STATUS:    b'\x00',
            Param.MANUAL_SPEED:       b'\x80',                         # 128
            Param.FAN1_SPEED:         struct.pack('<H', 0),
            Param.FAN2_SPEED:         struct.pack('<H', 0),
            # ── Group 2 ─────────────────────────────────────────────
            Param.FILTER_COUNTDOWN:   b'\x00\x00\xB4',                 # 180 days
            Param.FILTER_INDICATOR:   b'\x00',
            Param.BOOST_DELAY:        b'\x00',
            Param.RTC_TIME:           bytes([now.second, now.minute, now.hour]),
            Param.RTC_CALENDAR:       bytes([now.day, now.weekday() + 1,
                                             now.month, now.year % 100]),
            Param.WEEKLY_SCHEDULE_EN: b'\x00',
            Param.DEVICE_SEARCH:      self.id_bytes,                   # 16 bytes
            Param.MACHINE_HOURS:      b'\x00\x00\x00\x00',
            Param.ALARM_STATUS:       b'\x00',
            Param.CLOUD_PERMISSION:   b'\x00',
            Param.FIRMWARE_VERSION:   bytes([1, 2, 6, 3, 0xE8, 0x07]), # v1.2 Mar 6 2024
            Param.OPERATION_MODE:     bytes([v['mode']]),
            Param.UNIT_TYPE:          struct.pack('<H', self._unit_type),
            # ── Group 3 (Wi-Fi) ─────────────────────────────────────
            Param.WIFI_MODE:          b'\x01',
            Param.WIFI_SSID:          b'SimNetwork',
            Param.WIFI_ENCRYPTION:    b'\x34',                         # WPA/WPA2
            Param.WIFI_CHANNEL:       b'\x06',
            Param.WIFI_DHCP:          b'\x01',
            Param.WIFI_IP:            bytes([192, 168, 1, 100]),
            Param.WIFI_SUBNET:        bytes([255, 255, 255, 0]),
            Param.WIFI_GATEWAY:       bytes([192, 168, 1, 1]),
            Param.WIFI_CURRENT_IP:    bytes([127, 0, 0, 1]),
            # ── Group 4 ─────────────────────────────────────────────
            Param.VOLTAGE_STATUS:     b'\x00',
            Param.NIGHT_TIMER:        b'\x00\x08',
            Param.PARTY_TIMER:        b'\x00\x04',
        }

    def get_state_snapshot(self, params: list[int]) -> dict[int, Optional[bytes]]:
        """Return a {param_code: value} mapping for the given param codes."""
        return {p: self._state.get(p) for p in params}

    def set_lan_ip(self, ip: str) -> None:
        try:
            parts = [int(x) for x in ip.split('.')]
            self._state[Param.WIFI_CURRENT_IP] = bytes(parts)
        except (ValueError, struct.error):
            pass  # malformed IP — leave current value unchanged

    # ------------------------------------------------------------------
    # Physics / dynamics
    # ------------------------------------------------------------------

    def tick(self, dt: float) -> None:
        self._tick_fans(dt)
        self._tick_humidity(dt)
        self._tick_rtc()
        self._tick_uptime()

    def _tick_fans(self, dt: float) -> None:
        power  = self._state[Param.POWER][0]
        speed  = self._state[Param.SPEED][0]
        manual = self._state[Param.MANUAL_SPEED][0]

        if not power:
            target_rpm_fan1 = target_rpm_fan2 = 0
        elif speed == 255:
            target_rpm_fan1 = int(manual / 255.0 * _MANUAL_RPM_MAX_FAN1)
            target_rpm_fan2 = int(manual / 255.0 * _MANUAL_RPM_MAX_FAN2)
        else:
            target_rpm_fan1, target_rpm_fan2 = _RPM_TARGETS.get(speed, _RPM_TARGETS[2])

        self._fan1_rpm = self._apply_rpm_ramp(self._fan1_rpm, target_rpm_fan1, dt, bool(power))
        self._fan2_rpm = self._apply_rpm_ramp(self._fan2_rpm, target_rpm_fan2, dt, bool(power))
        self._state[Param.FAN1_SPEED] = struct.pack('<H', int(self._fan1_rpm))
        self._state[Param.FAN2_SPEED] = struct.pack('<H', int(self._fan2_rpm))

    @staticmethod
    def _apply_rpm_ramp(current: float, target: float, dt: float, spinning: bool) -> float:
        """Step current RPM toward target at _RAMP_RATE, adding jitter when spinning."""
        diff = target - current
        step = min(abs(diff), _RAMP_RATE * dt)
        updated = current + (step if diff > 0 else (-step if diff < 0 else 0))
        if spinning and target > 0:
            updated += random.gauss(0, _RPM_NOISE_STDDEV)
        return max(0.0, updated)

    def _tick_humidity(self, dt: float) -> None:
        self._humidity += random.gauss(0, _HUMIDITY_NOISE_STDDEV) * dt
        self._humidity  = max(30.0, min(95.0, self._humidity))
        rh = int(self._humidity)
        self._state[Param.CURRENT_HUMIDITY] = bytes([rh])
        threshold = self._state[Param.HUMIDITY_THRESHOLD][0]
        self._state[Param.HUMIDITY_STATUS] = bytes([1 if rh >= threshold else 0])

    def _tick_rtc(self) -> None:
        now = datetime.now()
        self._state[Param.RTC_TIME]     = bytes([now.second, now.minute, now.hour])
        self._state[Param.RTC_CALENDAR] = bytes([now.day, now.weekday() + 1,
                                                  now.month, now.year % 100])

    def _tick_uptime(self) -> None:
        uptime_seconds = int(time.monotonic() - self._start)
        minutes = (uptime_seconds // 60) % 60
        hours   = (uptime_seconds // 3600) % 24
        days    = uptime_seconds // 86400
        self._state[Param.MACHINE_HOURS] = bytes([minutes, hours]) + struct.pack('<H', days)

    # ------------------------------------------------------------------
    # Packet dispatch
    # ------------------------------------------------------------------

    def handle(self, func_byte: int, data: bytes, addr: tuple,
               sock: socket.socket, tag_prefix: str = '') -> None:
        """Handle a verified packet that is addressed to this device."""
        handler = self._FUNC_HANDLERS.get(func_byte)
        if handler:
            handler(self, func_byte, data, addr, sock, tag_prefix)

    def _handle_read(self, _func: int, data: bytes, addr: tuple,
                     sock: socket.socket, tag_prefix: str) -> None:
        requested = _parse_read_request_data(data)
        _log('READ ', addr, {p: self._state.get(p) for p in requested}, tag_prefix)
        self._send_response(requested, addr, sock)

    def _handle_write(self, _func: int, data: bytes, addr: tuple,
                      sock: socket.socket, tag_prefix: str) -> None:
        updates = _parse_write_data(data)
        self._apply_writes(updates)
        _log('WRITE', addr, updates, tag_prefix)

    def _handle_write_resp(self, _func: int, data: bytes, addr: tuple,
                           sock: socket.socket, tag_prefix: str) -> None:
        updates = _parse_write_data(data)
        self._apply_writes(updates)
        _log('WRSP ', addr, updates, tag_prefix)
        self._send_response(list(updates.keys()), addr, sock)

    def _handle_increment(self, _func: int, data: bytes, addr: tuple,
                          sock: socket.socket, tag_prefix: str) -> None:
        params = _parse_read_request_data(data)
        for p in params:
            self._nudge(p, +1)
        _log('INC  ', addr, {p: self._state.get(p) for p in params}, tag_prefix)
        self._send_response(params, addr, sock)

    def _handle_decrement(self, _func: int, data: bytes, addr: tuple,
                          sock: socket.socket, tag_prefix: str) -> None:
        params = _parse_read_request_data(data)
        for p in params:
            self._nudge(p, -1)
        _log('DEC  ', addr, {p: self._state.get(p) for p in params}, tag_prefix)
        self._send_response(params, addr, sock)

    # Wire up the dispatch table once all handler methods are defined
    _FUNC_HANDLERS = {
        int(Func.READ):       _handle_read,
        int(Func.WRITE):      _handle_write,
        int(Func.WRITE_RESP): _handle_write_resp,
        int(Func.INCREMENT):  _handle_increment,
        int(Func.DECREMENT):  _handle_decrement,
    }

    def respond_to_discovery(self, requested: list[int], addr: tuple,
                             sock: socket.socket) -> None:
        """Send a discovery response for the given params (called by the server)."""
        self._send_response(requested, addr, sock)

    def _send_response(self, requested: list[int], addr: tuple,
                       sock: socket.socket) -> None:
        resp_data = _build_response_data(requested, self._state)
        pkt = build_packet(self.device_id, self.password, Func.RESPONSE, resp_data)
        sock.sendto(pkt, addr)

    # ------------------------------------------------------------------
    # State mutation
    # ------------------------------------------------------------------

    def _apply_writes(self, updates: dict[int, bytes]) -> None:
        # Factory reset wipes state entirely — process it first and stop.
        factory_reset_value = updates.get(int(Param.FACTORY_RESET))
        if factory_reset_value is not None:
            self._write_factory_reset(factory_reset_value)
            return

        for param_int, value_bytes in updates.items():
            special = self._WRITE_HANDLERS.get(param_int)
            if special:
                special(self, value_bytes)
            else:
                try:
                    self._state[Param(param_int)] = value_bytes
                except ValueError:
                    pass

    def _write_power(self, value_bytes: bytes) -> None:
        if value_bytes == b'\x02':                      # toggle
            cur = self._state.get(Param.POWER, b'\x00')[0]
            self._state[Param.POWER] = bytes([0 if cur else 1])
        else:
            self._state[Param.POWER] = value_bytes

    def _write_filter_reset(self, _value: bytes) -> None:
        self._state[Param.FILTER_COUNTDOWN] = b'\x00\x00\xB4'
        self._state[Param.FILTER_INDICATOR] = b'\x00'

    def _write_reset_alarms(self, _value: bytes) -> None:
        self._state[Param.ALARM_STATUS] = b'\x00'

    def _write_factory_reset(self, _value: bytes) -> None:
        print(f'  [#{self.index + 1}] Factory reset — restoring defaults')
        self._fan1_rpm = self._fan2_rpm = 0.0
        variant = self._VARIANTS[self.index % len(self._VARIANTS)]
        self._humidity = variant['humidity']
        self._state = self._make_initial_state(variant)

    _WRITE_HANDLERS = {
        int(Param.POWER):         _write_power,
        int(Param.FILTER_RESET):  _write_filter_reset,
        int(Param.RESET_ALARMS):  _write_reset_alarms,
        int(Param.FACTORY_RESET): _write_factory_reset,
    }

    def _nudge(self, param_int: int, delta: int) -> None:
        try:
            p    = Param(param_int)
            meta = PARAM_META.get(p)
            cur  = self._state.get(p)
            if meta is None or cur is None:
                return
            val = int.from_bytes(cur, 'little') + delta
            value_range = meta.get('range')
            if value_range:
                val = max(value_range[0], min(value_range[1], val))
            choices = meta.get('values')
            if choices:
                keys = sorted(k for k in choices if k != 255)
                val  = max(keys[0], min(keys[-1], val))
            byte_size = meta.get('size') or 1
            if byte_size:
                self._state[p] = val.to_bytes(byte_size, 'little')
        except (ValueError, struct.error):
            pass  # unknown param or encoding error — skip silently

    # ------------------------------------------------------------------
    # Console status
    # ------------------------------------------------------------------

    def print_status(self) -> None:
        pwr  = self._state[Param.POWER][0]
        spd  = self._state[Param.SPEED][0]
        mode = self._state[Param.OPERATION_MODE][0]
        rpm1 = int.from_bytes(self._state[Param.FAN1_SPEED], 'little')
        rpm2 = int.from_bytes(self._state[Param.FAN2_SPEED], 'little')
        rh   = self._state[Param.CURRENT_HUMIDITY][0]
        al   = self._state[Param.ALARM_STATUS][0]

        pwr_s = '\033[32mON \033[0m' if pwr else '\033[31mOFF\033[0m'
        ts    = datetime.now().strftime('%H:%M:%S')
        print(f'  [{ts}] #{self.index + 1} Power:{pwr_s} '
              f'{self._SPEED_NAMES.get(spd, str(spd)):<4}  '
              f'{self._MODE_NAMES.get(mode, "?"):<12}  '
              f'Fan1:{rpm1:>5} RPM  Fan2:{rpm2:>5} RPM  '
              f'RH:{rh:>3}%  {self._ALARM_NAMES.get(al, "?")}')


# ---------------------------------------------------------------------------
# Multi-device server
# ---------------------------------------------------------------------------

class VentoFanSim:
    """
    Runs N simulated Vento fans on a single UDP socket bound to port 4000.

    Discovery broadcasts get a response from every virtual device, just
    as real hardware on the same LAN would behave.  Directed packets are
    routed to the device whose ID matches the packet's target field.
    """

    def __init__(self, count: int = 1, host: str = '0.0.0.0',
                 port: int = 4000, start_index: int = 0,
                 unit_type: int = SIM_UNIT_TYPE,
                 id_prefix: str = SIM_ID_PREFIX) -> None:
        self._port    = port
        self._devices = [
            SimDevice(start_index + i, unit_type=unit_type, id_prefix=id_prefix)
            for i in range(count)
        ]
        self._id_map  = {d.id_bytes: d for d in self._devices}

        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        try:
            self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        except AttributeError:
            pass
        self._sock.bind((host, port))
        self._sock.setblocking(False)

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    def run(self) -> None:
        lan_ip = _get_lan_ip()
        _banner(lan_ip, self._devices, self._port)
        for d in self._devices:
            d.set_lan_ip(lan_ip)

        last_tick   = time.monotonic()
        last_status = time.monotonic()

        while True:
            now = time.monotonic()
            dt  = now - last_tick
            last_tick = now
            for dev in self._devices:
                dev.tick(dt)

            if now - last_status >= _STATUS_INTERVAL:
                last_status = now
                for dev in self._devices:
                    dev.print_status()

            r, _, _ = select.select([self._sock], [], [], _SELECT_TIMEOUT)
            if r:
                try:
                    raw, addr = self._sock.recvfrom(1024)
                    self._dispatch(raw, addr)
                except Exception as exc:
                    print(f'  [!] Socket error: {exc}')

    # ------------------------------------------------------------------
    # Packet routing
    # ------------------------------------------------------------------

    def _dispatch(self, raw: bytes, addr: tuple) -> None:
        try:
            verify_checksum(raw)
        except (VentoChecksumError, VentoProtocolError):
            return

        try:
            data_start, target_id, pwd, func_byte = _find_data_start(raw)
        except VentoProtocolError:
            return

        target_id_bytes = bytes(target_id)
        data = bytes(raw[data_start:-2])

        if target_id_bytes == DEFAULT_DEVICE_ID:
            # ── Discovery broadcast: every device responds ──────────
            requested = _parse_read_request_data(data)
            _log('DISC ', addr, self._devices[0].get_state_snapshot(requested[:4]))
            for dev in self._devices:
                dev.respond_to_discovery(requested, addr, self._sock)

        else:
            # ── Directed packet: route to the matching device ───────
            dev = self._id_map.get(target_id_bytes)
            if dev:
                dev.handle(func_byte, data, addr, self._sock,
                           tag_prefix=f'#{dev.index + 1}')

    def close(self) -> None:
        self._sock.close()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_lan_ip() -> str:
    """Best-effort: return the machine's primary LAN IP address."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(('8.8.8.8', 80))
            return s.getsockname()[0]
    except OSError:
        return '127.0.0.1'


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description='VentoFanSim — Blauberg Vento Expert UDP simulator',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        '--count', type=int, default=1, metavar='N',
        help='Number of virtual fan devices to simulate (1–9)',
    )
    parser.add_argument('--host', default='0.0.0.0', help='Bind address')
    parser.add_argument('--port', type=int, default=4000, help='UDP port')
    parser.add_argument(
        '--start-index', type=int,
        default=int(os.environ.get('FAN_INDEX', '0')),
        metavar='N',
        help='Device index of the first simulated fan — sets device ID offset. '
             'Defaults to the FAN_INDEX environment variable or 0. '
             'Index 0 → SIMFAN0000000001, index 1 → SIMFAN0000000002, etc.',
    )
    parser.add_argument(
        '--id-prefix',
        default=os.environ.get('DEVICE_PREFIX', SIM_ID_PREFIX),
        metavar='PREFIX',
        help='Device ID prefix (default: DEVICE_PREFIX env var or SIMFAN). '
             'Total device ID is always 16 chars: prefix + zero-padded index.',
    )
    parser.add_argument(
        '--unit-type', type=int,
        default=int(os.environ.get('UNIT_TYPE', str(SIM_UNIT_TYPE))),
        metavar='N',
        help='Vento unit type integer (3=A50/A85/A100 W V.2, '
             '4=Duo A30 W V.2, 5=A30 W V.2). '
             'Default: UNIT_TYPE env var or 3.',
    )
    args = parser.parse_args()

    if not 1 <= args.count <= 9:
        parser.error('--count must be between 1 and 9')
    if args.start_index < 0:
        parser.error('--start-index must be >= 0')
    if len(args.id_prefix) > 15:
        parser.error('--id-prefix must be 15 characters or fewer')

    sim = VentoFanSim(count=args.count, host=args.host,
                      port=args.port, start_index=args.start_index,
                      unit_type=args.unit_type, id_prefix=args.id_prefix)
    try:
        sim.run()
    except KeyboardInterrupt:
        print('\n  Simulator stopped.')
    finally:
        sim.close()


if __name__ == '__main__':
    main()
