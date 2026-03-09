from __future__ import annotations
import struct
from .exceptions import VentoChecksumError, VentoProtocolError, VentoUnsupportedParamError
from .parameters import (CMD_NOT_SUP, CMD_PAGE, CMD_SIZE, CMD_FUNC, DEFAULT_DEVICE_ID,
    MAX_PACKET_SIZE, PACKET_START, PARAM_META, PROTOCOL_TYPE, Func, Param)

def _encode_id(device_id):
    raw = device_id.encode('ascii') if isinstance(device_id, str) else device_id
    if len(raw) != 16: raise VentoProtocolError(f"Device ID must be 16 chars, got {len(raw)}")
    return raw

def _encode_password(password):
    raw = password.encode('ascii')
    if len(raw) > 8: raise VentoProtocolError(f"Password max 8 chars")
    return raw

def _checksum(payload): return struct.pack('<H', sum(payload) & 0xFFFF)
def _param_high_low(p): v = int(p); return (v >> 8) & 0xFF, v & 0xFF

def build_packet(device_id, password, func, data):
    id_bytes = _encode_id(device_id); pwd_bytes = _encode_password(password)
    payload = (bytes([PROTOCOL_TYPE]) + bytes([len(id_bytes)]) + id_bytes
               + bytes([len(pwd_bytes)]) + pwd_bytes + bytes([int(func)]) + data)
    pkt = PACKET_START + payload + _checksum(payload)
    if len(pkt) > MAX_PACKET_SIZE: raise VentoProtocolError(f"Packet {len(pkt)} > {MAX_PACKET_SIZE}")
    return pkt

def _build_read_data(params):
    data = bytearray(); page = 0x00
    for p in params:
        high, low = _param_high_low(p)
        if high != page: data += bytes([CMD_PAGE, high]); page = high
        data.append(low)
    return bytes(data)

def _build_write_data(param_values):
    data = bytearray(); page = 0x00
    for p, val in param_values.items():
        high, low = _param_high_low(p); meta = PARAM_META[p]; esz = meta['size']
        if isinstance(val, int):
            if esz is None: raise VentoProtocolError(f"{p.name} needs bytes, not int")
            val_bytes = val.to_bytes(esz, 'little')
        else:
            val_bytes = bytes(val)
        asz = len(val_bytes)
        if high != page: data += bytes([CMD_PAGE, high]); page = high
        if asz != 1: data += bytes([CMD_SIZE, asz])
        data.append(low); data += val_bytes
    return bytes(data)

def build_read(device_id, password, params):
    return build_packet(device_id, password, Func.READ, _build_read_data(params))
def build_write(device_id, password, pv):
    return build_packet(device_id, password, Func.WRITE, _build_write_data(pv))
def build_write_resp(device_id, password, pv):
    return build_packet(device_id, password, Func.WRITE_RESP, _build_write_data(pv))
def build_increment(device_id, password, params):
    return build_packet(device_id, password, Func.INCREMENT, _build_read_data(params))
def build_decrement(device_id, password, params):
    return build_packet(device_id, password, Func.DECREMENT, _build_read_data(params))
def build_discovery():
    return build_read(DEFAULT_DEVICE_ID, '', [Param.DEVICE_SEARCH, Param.UNIT_TYPE])

def verify_checksum(raw):
    if len(raw) < 4: raise VentoChecksumError("Packet too short")
    exp = struct.unpack('<H', raw[-2:])[0]; act = sum(raw[2:-2]) & 0xFFFF
    if act != exp: raise VentoChecksumError(f"Checksum mismatch: {act:#06x} != {exp:#06x}")

def _find_data_start(raw):
    if len(raw) < 23: raise VentoProtocolError(f"Packet too short: {len(raw)}")
    if raw[0] != 0xFD or raw[1] != 0xFD: raise VentoProtocolError("Missing 0xFD 0xFD header")
    if raw[2] != PROTOCOL_TYPE: raise VentoProtocolError(f"Unknown type {raw[2]:#04x}")
    size_id = raw[3]; id_end = 4 + size_id
    size_pwd = raw[id_end]; pwd_end = id_end + 1 + size_pwd
    func_byte = raw[pwd_end]
    return pwd_end + 1, raw[4:id_end], raw[id_end+1:pwd_end], func_byte

def parse_response(raw):
    verify_checksum(raw)
    data_start, _id, _pwd, func_byte = _find_data_start(raw)
    if func_byte != int(Func.RESPONSE):
        raise VentoProtocolError(f"Expected FUNC=0x06, got {func_byte:#04x}")
    data = raw[data_start:-2]; result = {}; unsupported = []
    page = 0x00; i = 0; param_sz = 1
    while i < len(data):
        b = data[i]
        if b == CMD_PAGE:
            i += 1; page = data[i]; i += 1; param_sz = 1; continue
        if b == CMD_FUNC:
            i += 2; param_sz = 1; continue
        if b == CMD_SIZE:
            i += 1; param_sz = data[i]; i += 1; b = data[i]
        if b == CMD_NOT_SUP:
            i += 1
            if i < len(data): unsupported.append((page << 8) | data[i])
            i += 1; param_sz = 1; continue
        param_num = (page << 8) | b; i += 1
        val_end = i + param_sz
        if val_end > len(data): raise VentoProtocolError(f"Param {param_num:#06x} truncated")
        val_bytes = bytes(data[i:val_end]); i = val_end
        try: result[Param(param_num)] = val_bytes
        except ValueError: result[param_num] = val_bytes
        param_sz = 1
    if unsupported: raise VentoUnsupportedParamError(unsupported)
    return result

def decode_int(val): return int.from_bytes(val, 'little')
def decode_ip(val):
    if len(val) != 4: raise VentoProtocolError("IP must be 4 bytes")
    return '.'.join(str(b) for b in val)
def encode_ip(ip):
    parts = ip.split('.')
    if len(parts) != 4: raise VentoProtocolError(f"Invalid IP {ip!r}")
    return bytes(int(p) for p in parts)
def decode_text(val): return val.decode('ascii', errors='replace')
def decode_firmware(val):
    if len(val) != 6: raise VentoProtocolError("Firmware must be 6 bytes")
    return {'major':val[0],'minor':val[1],'day':val[2],'month':val[3],'year':int.from_bytes(val[4:6],'little')}
def decode_machine_hours(val):
    if len(val) != 4: raise VentoProtocolError("Machine hours must be 4 bytes")
    return {'minutes':val[0],'hours':val[1],'days':int.from_bytes(val[2:4],'little')}
def decode_rtc_time(val):
    if len(val) != 3: raise VentoProtocolError("RTC time must be 3 bytes")
    return {'seconds':val[0],'minutes':val[1],'hours':val[2]}
def decode_rtc_calendar(val):
    if len(val) != 4: raise VentoProtocolError("RTC calendar must be 4 bytes")
    return {'day':val[0],'day_of_week':val[1],'month':val[2],'year':2000+val[3]}
def decode_schedule(val):
    if len(val) != 6: raise VentoProtocolError("Schedule must be 6 bytes")
    return {'day_of_week':val[0],'period':val[1],'speed':val[2],'_reserved':val[3],'end_minutes':val[4],'end_hours':val[5]}
def decode_timer_countdown(val):
    if len(val) != 3: raise VentoProtocolError("Timer countdown must be 3 bytes")
    return {'seconds':val[0],'minutes':val[1],'hours':val[2]}
def decode_filter_countdown(val):
    if len(val) != 3: raise VentoProtocolError("Filter countdown must be 3 bytes")
    return {'minutes':val[0],'hours':val[1],'days':val[2]}
