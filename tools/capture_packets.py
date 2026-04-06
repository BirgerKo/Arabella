#!/usr/bin/env python3
"""
Capture and decode Blauberg Vento UDP packets on port 4000.

Uses tshark to sniff traffic, then decodes each packet using the
blauberg_vento protocol module to give a human-readable trace.

Usage:
    python tools/capture_packets.py [--iface <interface>] [--count <n>]

    --iface   Network interface to sniff (default: any)
    --count   Stop after N packets (default: run until Ctrl-C)

Requires root / capture permissions:
    sudo python tools/capture_packets.py
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

# Make sure the project root is on sys.path so we can import blauberg_vento
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from blauberg_vento.parameters import Func, Param
from blauberg_vento.protocol import (
    decode_schedule, decode_rtc_time, decode_rtc_calendar,
    parse_response, verify_checksum,
)
from blauberg_vento.exceptions import VentoError


# ── Human-readable labels ────────────────────────────────────────────────────

_FUNC_NAMES = {
    0x01: "READ",
    0x02: "WRITE",
    0x03: "WRITE+RESP",
    0x04: "INCREMENT",
    0x05: "DECREMENT",
    0x06: "RESPONSE",
}

_SCHEDULE_DAYS = {
    0: "Mon", 1: "Tue", 2: "Wed", 3: "Thu",
    4: "Fri", 5: "Sat", 6: "Sun", 7: "All",
}


# ── Packet decoder ───────────────────────────────────────────────────────────

def _hex(data: bytes) -> str:
    return data.hex(' ').upper()


def _decode_packet(raw: bytes, src: str, dst: str) -> str:
    lines = [f"  {src} → {dst}  ({len(raw)} bytes)"]
    lines.append(f"  RAW: {_hex(raw)}")

    if len(raw) < 4 or raw[0] != 0xFD or raw[1] != 0xFD:
        lines.append("  [not a Vento packet — skipped]")
        return "\n".join(lines)

    try:
        verify_checksum(raw)
    except VentoError as e:
        lines.append(f"  [checksum error: {e}]")
        return "\n".join(lines)

    # Parse header manually (mirrors protocol._parse_packet_header)
    proto_type = raw[2]
    id_size    = raw[3]
    id_end     = 4 + id_size
    device_id  = raw[4:id_end].decode('ascii', errors='replace')
    pwd_size   = raw[id_end]
    pwd_end    = id_end + 1 + pwd_size
    password   = raw[id_end + 1:pwd_end].decode('ascii', errors='replace')
    func_byte  = raw[pwd_end]
    func_name  = _FUNC_NAMES.get(func_byte, f"UNKNOWN(0x{func_byte:02X})")

    lines.append(f"  Device-ID: {device_id!r}  Password: {password!r}")
    lines.append(f"  Function:  {func_name} (0x{func_byte:02X})")

    data_bytes = raw[pwd_end + 1:-2]
    lines.append(f"  DATA({len(data_bytes)}B): {_hex(data_bytes)}")

    # Decode the data section into param → value pairs
    params = _decode_data_section(data_bytes)
    for param_str, value_str in params:
        lines.append(f"    {param_str}: {value_str}")

    return "\n".join(lines)


def _decode_data_section(data: bytes) -> list[tuple[str, str]]:
    """Walk the TLV data section and return (param_name, decoded_value) pairs."""
    result = []
    page = 0x00
    param_size = 1
    i = 0

    CMD_PAGE    = 0xFF
    CMD_FUNC    = 0xFC
    CMD_SIZE    = 0xFE
    CMD_NOT_SUP = 0xFD

    while i < len(data):
        b = data[i]

        if b == CMD_PAGE:
            i += 1
            page = data[i]
            i += 1
            param_size = 1
            continue

        if b == CMD_FUNC:
            i += 2
            param_size = 1
            continue

        if b == CMD_SIZE:
            i += 1
            param_size = data[i]
            i += 1
            b = data[i]

        if b == CMD_NOT_SUP:
            i += 1
            if i < len(data):
                result.append((f"PARAM(0x{(page << 8) | data[i]:04X})", "NOT SUPPORTED"))
            i += 1
            param_size = 1
            continue

        param_num = (page << 8) | b
        i += 1
        val = bytes(data[i:i + param_size])
        i += param_size

        try:
            p = Param(param_num)
            name = p.name
        except ValueError:
            name = f"0x{param_num:04X}"

        decoded = _decode_value(param_num, val)
        result.append((name, decoded))
        param_size = 1

    return result


def _decode_value(param_num: int, val: bytes) -> str:
    hex_str = _hex(val)
    try:
        p = Param(param_num)
    except ValueError:
        return hex_str

    if p == Param.SCHEDULE_SETUP and len(val) == 6:
        d = decode_schedule(val)
        day_name = _SCHEDULE_DAYS.get(d['day_of_week'], str(d['day_of_week']))
        return (
            f"{hex_str}  →  day={day_name}({d['day_of_week']}) "
            f"period={d['period']} speed={d['speed']} "
            f"end={d['end_hours']:02d}:{d['end_minutes']:02d}"
        )

    if p == Param.RTC_TIME and len(val) == 3:
        t = decode_rtc_time(val)
        return f"{hex_str}  →  {t['hours']:02d}:{t['minutes']:02d}:{t['seconds']:02d}"

    if p == Param.RTC_CALENDAR and len(val) == 4:
        c = decode_rtc_calendar(val)
        day_name = _SCHEDULE_DAYS.get(c['day_of_week'] - 1, str(c['day_of_week']))
        return f"{hex_str}  →  {c['year']}-{c['month']:02d}-{c['day']:02d} ({day_name})"

    if len(val) <= 2:
        return f"{hex_str}  →  {int.from_bytes(val, 'little')}"

    return hex_str


# ── tshark runner ────────────────────────────────────────────────────────────

def run_capture(iface: str, count: int | None) -> None:
    """Launch tshark, read tab-separated output line-by-line, decode each packet."""
    cmd = [
        "tshark",
        "-i", iface,
        "-f", "udp port 4000",
        "-T", "fields",
        "-e", "ip.src",
        "-e", "ip.dst",
        "-e", "udp.payload",
        "-E", "separator=|",
        "-l",                   # flush after each packet
    ]
    if count:
        cmd += ["-c", str(count)]

    print(cmd)
    print(f"Capturing on interface '{iface}', UDP port 4000")
    print("Press Ctrl-C to stop.\n")

    try:
        print("Try")
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except FileNotFoundError:
        sys.exit("tshark not found — install Wireshark/tshark first")

    pkt_num = 0
    try:
        for line in proc.stdout:
            line = line.rstrip("\n")
            if not line:
                continue
            parts = line.split("|")
            if len(parts) < 3:
                continue
            src, dst, payload_hex = parts[0], parts[1], parts[2]
            if not payload_hex:
                continue
            pkt_num += 1
            raw = bytes.fromhex(payload_hex.replace(":", ""))
            print(f"{'─'*60}")
            print(f"Packet #{pkt_num}")
            print(_decode_packet(raw, src, dst))
            print()
    except KeyboardInterrupt:
        pass
    finally:
        proc.terminate()
        proc.wait()


def _handle_packet(num: int, src: str, dst: str, raw: bytes) -> None:
    print(f"{'─'*60}")
    print(f"Packet #{num}")
    print(_decode_packet(raw, src, dst))

    print(f"{'─'*60}")
    print(f"Packet #{num}")
    print(_decode_packet(raw, src, dst))
    print()


# ── CLI entry point ──────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--iface", default="any", help="Network interface (default: any)")
    parser.add_argument("--count", type=int, default=None, help="Stop after N packets")
    args = parser.parse_args()

    run_capture(args.iface, args.count)


if __name__ == "__main__":
    main()
