"""Tests for ventocontrol.simulator.

Covers:
- _make_sim_id         — ID generation
- _parse_read_request_data / _parse_write_data / _build_response_data — protocol helpers
- _get_lan_ip          — network helper
- SimDevice            — init, tick physics, apply_writes, nudge, handle dispatch
- VentoFanSim          — construction, _dispatch routing
"""
from __future__ import annotations

import socket
from unittest.mock import MagicMock

import pytest

from blauberg_vento.parameters import (
    CMD_NOT_SUP, CMD_PAGE, CMD_SIZE,
    DEFAULT_DEVICE_ID, Func, Param,
)
from blauberg_vento.protocol import build_discovery, build_read
from ventocontrol.simulator import (
    SIM_ID_PREFIX,
    SIM_PASSWORD,
    SimDevice,
    VentoFanSim,
    _build_response_data,
    _get_lan_ip,
    _make_sim_id,
    _parse_read_request_data,
    _parse_write_data,
)


# ---------------------------------------------------------------------------
# _make_sim_id
# ---------------------------------------------------------------------------

class TestMakeSimId:
    def test_length_is_16(self):
        assert len(_make_sim_id(0)) == 16

    def test_first_device(self):
        assert _make_sim_id(0) == "SIMFAN0000000001"

    def test_second_device(self):
        assert _make_sim_id(1) == "SIMFAN0000000002"

    def test_uses_default_prefix(self):
        assert _make_sim_id(0).startswith(SIM_ID_PREFIX)

    def test_custom_prefix(self):
        result = _make_sim_id(0, "FAN")
        assert len(result) == 16
        assert result.startswith("FAN")

    def test_large_index(self):
        result = _make_sim_id(99)
        assert len(result) == 16
        assert result.endswith("100")


# ---------------------------------------------------------------------------
# _parse_read_request_data
# ---------------------------------------------------------------------------

class TestParseReadRequestData:
    def test_empty_data(self):
        assert _parse_read_request_data(b"") == []

    def test_single_param_page_zero(self):
        data = bytes([int(Param.POWER) & 0xFF])
        result = _parse_read_request_data(data)
        assert result == [int(Param.POWER)]

    def test_multiple_params_same_page(self):
        data = bytes([int(Param.POWER) & 0xFF, int(Param.SPEED) & 0xFF])
        result = _parse_read_request_data(data)
        assert int(Param.POWER) in result
        assert int(Param.SPEED) in result

    def test_page_change_sets_high_byte(self):
        # CMD_PAGE, 0x03, param_low → param code = 0x0302 (NIGHT_TIMER low byte = 0x02)
        data = bytes([CMD_PAGE, 0x03, int(Param.NIGHT_TIMER) & 0xFF])
        result = _parse_read_request_data(data)
        assert int(Param.NIGHT_TIMER) in result

    def test_page_resets_between_params(self):
        # Two params on different pages
        data = bytes([
            int(Param.POWER) & 0xFF,           # page 0
            CMD_PAGE, 0x03,
            int(Param.NIGHT_TIMER) & 0xFF,     # page 3
        ])
        result = _parse_read_request_data(data)
        assert int(Param.POWER) in result
        assert int(Param.NIGHT_TIMER) in result


# ---------------------------------------------------------------------------
# _parse_write_data
# ---------------------------------------------------------------------------

class TestParseWriteData:
    def test_empty_data(self):
        assert _parse_write_data(b"") == {}

    def test_single_byte_param(self):
        # POWER (page 0, low byte 0x01) = value 0x01
        data = bytes([int(Param.POWER) & 0xFF, 0x01])
        result = _parse_write_data(data)
        assert result[int(Param.POWER)] == b"\x01"

    def test_multi_byte_param_via_cmd_size(self):
        # CMD_SIZE=2, FAN1_SPEED_low, val_lo, val_hi (1000 RPM LE)
        param_low = int(Param.FAN1_SPEED) & 0xFF
        data = bytes([CMD_SIZE, 2, param_low, 0xE8, 0x03])
        result = _parse_write_data(data)
        assert result[int(Param.FAN1_SPEED)] == bytes([0xE8, 0x03])

    def test_multiple_params(self):
        data = bytes([
            int(Param.POWER) & 0xFF, 0x01,
            int(Param.SPEED) & 0xFF, 0x02,
        ])
        result = _parse_write_data(data)
        assert result[int(Param.POWER)] == b"\x01"
        assert result[int(Param.SPEED)] == b"\x02"


# ---------------------------------------------------------------------------
# _build_response_data
# ---------------------------------------------------------------------------

class TestBuildResponseData:
    def test_empty_request_returns_empty(self):
        assert _build_response_data([], {}) == b""

    def test_known_single_byte_param(self):
        state = {int(Param.POWER): b"\x01"}
        data = _build_response_data([int(Param.POWER)], state)
        # Should contain the value byte 0x01
        assert b"\x01" in data

    def test_unknown_param_gets_not_sup(self):
        state = {}
        data = _build_response_data([int(Param.POWER)], state)
        assert CMD_NOT_SUP in data

    def test_page_prefix_inserted_for_page3_param(self):
        state = {int(Param.NIGHT_TIMER): b"\x00\x08"}
        data = _build_response_data([int(Param.NIGHT_TIMER)], state)
        assert CMD_PAGE in data

    def test_multi_byte_param_prefixed_with_cmd_size(self):
        # FAN1_SPEED is 2 bytes
        state = {int(Param.FAN1_SPEED): bytes([0xE8, 0x03])}
        data = _build_response_data([int(Param.FAN1_SPEED)], state)
        assert CMD_SIZE in data


# ---------------------------------------------------------------------------
# SimDevice — initialisation
# ---------------------------------------------------------------------------

class TestSimDeviceInit:
    def test_device_id_is_16_chars(self):
        assert len(SimDevice(0).device_id) == 16

    def test_device_id_uses_prefix(self):
        assert SimDevice(0).device_id.startswith(SIM_ID_PREFIX)

    def test_password_is_default(self):
        assert SimDevice(0).password == SIM_PASSWORD

    def test_index_stored(self):
        assert SimDevice(2).index == 2

    def test_id_bytes_matches_device_id(self):
        d = SimDevice(0)
        assert d.id_bytes == d.device_id.encode("ascii")

    def test_state_has_required_keys(self):
        d = SimDevice(0)
        for key in (Param.POWER, Param.SPEED, Param.FAN1_SPEED, Param.FAN2_SPEED,
                    Param.CURRENT_HUMIDITY, Param.OPERATION_MODE):
            assert key in d._state

    def test_variant0_power_off(self):
        assert SimDevice(0)._state[Param.POWER] == b"\x00"

    def test_variant1_power_on(self):
        assert SimDevice(1)._state[Param.POWER] == b"\x01"

    def test_variant2_power_on(self):
        assert SimDevice(2)._state[Param.POWER] == b"\x01"

    def test_variants_wrap_at_index3(self):
        # Index 3 wraps to variant 0 — power off
        assert SimDevice(3)._state[Param.POWER] == b"\x00"

    def test_custom_prefix(self):
        d = SimDevice(0, id_prefix="MYFAN")
        assert d.device_id.startswith("MYFAN")
        assert len(d.device_id) == 16

    def test_device_search_param_contains_own_id(self):
        d = SimDevice(0)
        assert d._state[Param.DEVICE_SEARCH] == d.id_bytes


# ---------------------------------------------------------------------------
# SimDevice — set_lan_ip
# ---------------------------------------------------------------------------

class TestSimDeviceSetLanIp:
    def test_valid_ip_stored(self):
        d = SimDevice(0)
        d.set_lan_ip("192.168.1.42")
        assert d._state[Param.WIFI_CURRENT_IP] == bytes([192, 168, 1, 42])

    def test_invalid_ip_does_not_raise(self):
        d = SimDevice(0)
        d.set_lan_ip("not-an-ip")  # must not raise

    def test_loopback_stored(self):
        d = SimDevice(0)
        d.set_lan_ip("127.0.0.1")
        assert d._state[Param.WIFI_CURRENT_IP] == bytes([127, 0, 0, 1])


# ---------------------------------------------------------------------------
# SimDevice — tick (physics)
# ---------------------------------------------------------------------------

class TestSimDeviceTick:
    def test_tick_does_not_raise(self):
        SimDevice(0).tick(0.1)

    def test_powered_off_fans_ramp_toward_zero(self):
        d = SimDevice(0)           # variant 0: power=OFF
        d._fan1_rpm = 800.0
        d._fan2_rpm = 800.0
        # RAMP_RATE=80 RPM/s → 800 RPM needs 10 s = 120 ticks at dt=0.1
        for _ in range(120):
            d.tick(0.1)
        assert d._fan1_rpm < 10.0

    def test_powered_on_fans_ramp_up(self):
        d = SimDevice(1)           # variant 1: power=ON, speed=2
        d._fan1_rpm = 0.0
        for _ in range(30):
            d.tick(0.1)
        assert d._fan1_rpm > 0.0

    def test_fan_speed_stored_in_state(self):
        d = SimDevice(1)
        for _ in range(20):
            d.tick(0.1)
        rpm1 = int.from_bytes(d._state[Param.FAN1_SPEED], "little")
        assert rpm1 >= 0

    def test_humidity_stays_in_bounds(self):
        d = SimDevice(0)
        for _ in range(300):
            d.tick(0.1)
        rh = d._state[Param.CURRENT_HUMIDITY][0]
        assert 30 <= rh <= 95

    def test_rtc_time_is_3_bytes(self):
        d = SimDevice(0)
        d.tick(0.1)
        assert len(d._state[Param.RTC_TIME]) == 3

    def test_machine_hours_is_4_bytes(self):
        d = SimDevice(0)
        d.tick(0.1)
        assert len(d._state[Param.MACHINE_HOURS]) == 4

    def test_manual_speed_mode(self):
        d = SimDevice(0)
        d._state[Param.POWER] = b"\x01"
        d._state[Param.SPEED] = bytes([255])        # manual mode
        d._state[Param.MANUAL_SPEED] = bytes([128])
        d._fan1_rpm = 0.0
        for _ in range(30):
            d.tick(0.1)
        assert d._fan1_rpm > 0.0

    def test_humidity_status_set_when_above_threshold(self):
        d = SimDevice(0)
        d._humidity = 90.0
        d._state[Param.HUMIDITY_THRESHOLD] = bytes([60])
        d.tick(0.0)
        assert d._state[Param.HUMIDITY_STATUS] == b"\x01"

    def test_humidity_status_clear_when_below_threshold(self):
        d = SimDevice(0)
        d._humidity = 40.0
        d._state[Param.HUMIDITY_THRESHOLD] = bytes([60])
        d.tick(0.0)
        assert d._state[Param.HUMIDITY_STATUS] == b"\x00"


# ---------------------------------------------------------------------------
# SimDevice — _apply_writes
# ---------------------------------------------------------------------------

class TestSimDeviceApplyWrites:
    def test_normal_write_updates_state(self):
        d = SimDevice(0)
        d._apply_writes({int(Param.SPEED): b"\x03"})
        assert d._state[Param.SPEED] == b"\x03"

    def test_power_toggle_off_to_on(self):
        d = SimDevice(0)                   # power=OFF
        d._apply_writes({int(Param.POWER): b"\x02"})
        assert d._state[Param.POWER] == b"\x01"

    def test_power_toggle_on_to_off(self):
        d = SimDevice(1)                   # power=ON
        d._apply_writes({int(Param.POWER): b"\x02"})
        assert d._state[Param.POWER] == b"\x00"

    def test_power_direct_set_on(self):
        d = SimDevice(0)
        d._apply_writes({int(Param.POWER): b"\x01"})
        assert d._state[Param.POWER] == b"\x01"

    def test_filter_reset_restores_countdown(self):
        d = SimDevice(0)
        d._state[Param.FILTER_COUNTDOWN] = b"\x00\x00\x00"
        d._state[Param.FILTER_INDICATOR] = b"\x01"
        d._apply_writes({int(Param.FILTER_RESET): b"\x01"})
        assert d._state[Param.FILTER_COUNTDOWN] == b"\x00\x00\xB4"
        assert d._state[Param.FILTER_INDICATOR] == b"\x00"

    def test_reset_alarms_clears_status(self):
        d = SimDevice(0)
        d._state[Param.ALARM_STATUS] = b"\x01"
        d._apply_writes({int(Param.RESET_ALARMS): b"\x01"})
        assert d._state[Param.ALARM_STATUS] == b"\x00"

    def test_factory_reset_zeros_fans(self):
        d = SimDevice(1)
        d._fan1_rpm = 1500.0
        d._fan2_rpm = 1400.0
        d._apply_writes({int(Param.FACTORY_RESET): b"\x01"})
        assert d._fan1_rpm == 0.0
        assert d._fan2_rpm == 0.0

    def test_factory_reset_restores_variant_defaults(self):
        d = SimDevice(1)              # variant 1: power=ON
        d._state[Param.SPEED] = b"\x01"
        d._apply_writes({int(Param.FACTORY_RESET): b"\x01"})
        assert d._state[Param.POWER] == b"\x01"

    def test_unknown_param_ignored(self):
        d = SimDevice(0)
        d._apply_writes({0x9999: b"\x01"})  # must not raise


# ---------------------------------------------------------------------------
# SimDevice — _nudge
# ---------------------------------------------------------------------------

class TestSimDeviceNudge:
    def test_nudge_speed_up(self):
        d = SimDevice(0)
        d._state[Param.SPEED] = b"\x01"
        d._nudge(int(Param.SPEED), +1)
        assert d._state[Param.SPEED] == b"\x02"

    def test_nudge_speed_down(self):
        d = SimDevice(0)
        d._state[Param.SPEED] = b"\x02"
        d._nudge(int(Param.SPEED), -1)
        assert d._state[Param.SPEED] == b"\x01"

    def test_nudge_clamps_to_max(self):
        d = SimDevice(0)
        d._state[Param.SPEED] = b"\x03"
        d._nudge(int(Param.SPEED), +10)
        val = d._state[Param.SPEED][0]
        assert val <= 3

    def test_nudge_clamps_to_min(self):
        d = SimDevice(0)
        d._state[Param.SPEED] = b"\x01"
        d._nudge(int(Param.SPEED), -10)
        val = d._state[Param.SPEED][0]
        assert val >= 1

    def test_nudge_unknown_param_does_not_raise(self):
        SimDevice(0)._nudge(0x9999, +1)


# ---------------------------------------------------------------------------
# SimDevice — handle (mock socket)
# ---------------------------------------------------------------------------

class TestSimDeviceHandle:
    """Tests for handle() — use a MagicMock socket to avoid real networking."""

    def _device_and_sock(self) -> tuple[SimDevice, MagicMock]:
        return SimDevice(0), MagicMock(spec=socket.socket)

    def test_read_triggers_sendto(self):
        d, sock = self._device_and_sock()
        data = bytes([int(Param.POWER) & 0xFF])
        d.handle(int(Func.READ), data, ("127.0.0.1", 4000), sock)
        assert sock.sendto.called

    def test_write_updates_state_without_sending(self):
        d, sock = self._device_and_sock()
        data = bytes([int(Param.SPEED) & 0xFF, 0x03])
        d.handle(int(Func.WRITE), data, ("127.0.0.1", 4000), sock)
        assert d._state[Param.SPEED] == b"\x03"
        assert not sock.sendto.called

    def test_write_resp_updates_state_and_sends(self):
        d, sock = self._device_and_sock()
        data = bytes([int(Param.SPEED) & 0xFF, 0x03])
        d.handle(int(Func.WRITE_RESP), data, ("127.0.0.1", 4000), sock)
        assert d._state[Param.SPEED] == b"\x03"
        assert sock.sendto.called

    def test_increment_nudges_param_and_sends(self):
        d, sock = self._device_and_sock()
        d._state[Param.SPEED] = b"\x01"
        data = bytes([int(Param.SPEED) & 0xFF])
        d.handle(int(Func.INCREMENT), data, ("127.0.0.1", 4000), sock)
        assert d._state[Param.SPEED] == b"\x02"
        assert sock.sendto.called

    def test_decrement_nudges_param_and_sends(self):
        d, sock = self._device_and_sock()
        d._state[Param.SPEED] = b"\x02"
        data = bytes([int(Param.SPEED) & 0xFF])
        d.handle(int(Func.DECREMENT), data, ("127.0.0.1", 4000), sock)
        assert d._state[Param.SPEED] == b"\x01"
        assert sock.sendto.called


# ---------------------------------------------------------------------------
# VentoFanSim — construction
# ---------------------------------------------------------------------------

class TestVentoFanSimConstruction:
    def test_default_single_device(self):
        sim = VentoFanSim(port=0)
        assert len(sim._devices) == 1
        sim.close()

    def test_creates_n_devices(self):
        sim = VentoFanSim(count=3, port=0)
        assert len(sim._devices) == 3
        sim.close()

    def test_id_map_has_n_entries(self):
        sim = VentoFanSim(count=2, port=0)
        assert len(sim._id_map) == 2
        sim.close()

    def test_start_index_offsets_device_id(self):
        sim = VentoFanSim(count=1, port=0, start_index=5)
        assert sim._devices[0].device_id == _make_sim_id(5)
        sim.close()

    def test_id_map_keys_are_bytes(self):
        sim = VentoFanSim(count=1, port=0)
        for key in sim._id_map:
            assert isinstance(key, bytes)
        sim.close()


# ---------------------------------------------------------------------------
# VentoFanSim — _dispatch routing
# ---------------------------------------------------------------------------

class TestVentoFanSimDispatch:
    """Uses a real socket for construction but replaces it with a mock for dispatch."""

    @pytest.fixture()
    def sim(self):
        s = VentoFanSim(count=2, port=0)
        s._sock = MagicMock(spec=socket.socket)
        yield s
        s.close()

    def test_discovery_gets_response_from_every_device(self, sim):
        pkt = build_discovery()
        sim._dispatch(pkt, ("127.0.0.1", 12345))
        assert sim._sock.sendto.call_count == 2

    def test_directed_packet_routes_to_correct_device(self, sim):
        target = sim._devices[1]
        pkt = build_read(
            target.device_id.encode("ascii"),
            target.password,
            [Param.POWER],
        )
        sim._dispatch(pkt, ("127.0.0.1", 12345))
        assert sim._sock.sendto.call_count == 1

    def test_bad_checksum_packet_ignored(self, sim):
        bad = bytearray(build_discovery())
        bad[-1] ^= 0xFF
        sim._dispatch(bytes(bad), ("127.0.0.1", 12345))
        assert sim._sock.sendto.call_count == 0

    def test_unknown_device_id_ignored(self, sim):
        pkt = build_read(b"UNKNOWNDEVICEID!", "1111", [Param.POWER])
        sim._dispatch(pkt, ("127.0.0.1", 12345))
        assert sim._sock.sendto.call_count == 0


# ---------------------------------------------------------------------------
# _get_lan_ip
# ---------------------------------------------------------------------------

class TestGetLanIp:
    def test_returns_string(self):
        assert isinstance(_get_lan_ip(), str)

    def test_returns_dotted_quad(self):
        parts = _get_lan_ip().split(".")
        assert len(parts) == 4
        assert all(p.isdigit() for p in parts)
