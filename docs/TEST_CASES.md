# Test Cases — Arabella / VentoControl

Human-readable catalogue of all 220+ pytest test cases. Each entry describes
**what** the test checks, **why** it exists, and **what result** confirms it passes.

Run the full suite:
```bash
cd /Users/birger/Python/Arabella && python3.11 -m pytest -q
```

---

## Overview

| Test file | Classes | Tests | Area covered |
|-----------|---------|-------|--------------|
| `tests/test_history.py` | 4 | 18 | Device connection history, fan renaming, persistence |
| `tests/test_protocol.py` | 5 | 28 | UDP packet building, parsing, decoders, input validation |
| `tests/test_scenarios.py` | 6 | 32 | Scenario store CRUD, quick-slots, v1→v2 migration |
| `tests/test_simulator.py` | 13 | 75 | Simulator ID generation, protocol helpers, SimDevice physics, VentoFanSim routing |
| `tests/webdashboard/test_hub.py` | — | 5 | WebSocket broadcast hub: connect, disconnect, broadcast, dead socket cleanup |
| `tests/webdashboard/test_device_manager.py` | — | 15 | DeviceManager connect/disconnect, power/speed/mode/boost commands, fan switching, broadcast callback, discovery |
| `tests/webdashboard/test_routers_commands.py` | — | 7 | Command HTTP endpoints (power/speed/mode/boost), 503 when disconnected, 422 validation |
| `tests/webdashboard/test_routers_devices.py` | — | 10 | Device state, connect, fan switching, disconnect, and discovery HTTP endpoints |
| `tests/webdashboard/test_routers_scenarios.py` | — | 8 | Scenario CRUD and quick-slot HTTP endpoints |
| `tests/webdashboard/e2e/test_dashboard.py` | — | 14 | Playwright E2E: connect dialog, power toggle, speed/mode controls, scenario save+list, fan switching |
| **Total** | **28+** | **220+** | |

---

## test_history.py

Tests for `ventocontrol.history` — the `DeviceHistory` and `HistoryEntry` classes that
record which fans the user has connected to, preserve custom fan names, and survive
app restarts. All tests use `monkeypatch` to redirect file I/O to a temp directory so
they never touch `~/.ventocontrol/`.

---

### TestHistoryEntry

Basic construction and field defaults for the `HistoryEntry` data class.

| Test | Purpose | Expected result |
|------|---------|----------------|
| `test_defaults` | A freshly created `HistoryEntry` has sensible zero-state defaults for optional fields | `name == ""` and `last_seen == ""` |
| `test_custom_name` | The optional `name` parameter is accepted and stored | `entry.name == "Bedroom"` |

---

### TestDeviceHistoryBasics

Core behaviour of `DeviceHistory` — adding, ordering, capping, and clearing entries.

| Test | Purpose | Expected result |
|------|---------|----------------|
| `test_empty_on_new` | A brand-new history file starts with no entries | `entries == []` and `last_used is None` |
| `test_record_adds_entry` | Calling `record()` creates an entry with all provided fields plus a non-empty timestamp | 1 entry; `device_id`, `ip`, `unit_type_name`, `password` all match; `last_seen != ""` |
| `test_last_used_is_most_recent` | `last_used` always reflects the device most recently passed to `record()` | After recording DEV1 then DEV2, `last_used.device_id == "DEV2"` |
| `test_record_moves_existing_to_front` | Re-recording a device that is already in history moves it to position 0 — no duplicate is created | After re-connecting DEV1, `entries[0].device_id == "DEV1"` and `len(entries) == 2` |
| `test_record_cap` | History is capped at `_MAX_ENTRIES`; recording more than the cap drops the oldest | `len(entries) == _MAX_ENTRIES` after adding `_MAX_ENTRIES + 3` devices |
| `test_clear` | `clear()` wipes all entries and resets `last_used` | `entries == []` and `last_used is None` |
| `test_missing_file` | If the JSON file does not exist, `DeviceHistory` starts empty without raising | `entries == []` |
| `test_malformed_json` | If the JSON file is corrupt, `DeviceHistory` starts empty without raising | `entries == []` |

---

### TestDeviceHistoryPersistence

Verifies that history survives being written and re-loaded (simulates app restart).

| Test | Purpose | Expected result |
|------|---------|----------------|
| `test_reload_restores_entries` | Entries recorded by one `DeviceHistory` instance are visible when a new instance is created from the same backing file | Second instance has 2 entries in the correct order (most-recent first) |
| `test_rename_persists_across_restart` | A custom fan name set via `rename()` is restored after re-loading from disk | Second instance shows `entries[0].name == "Bedroom Fan"` |
| `test_unicode_name_persists` | Emoji and non-ASCII characters in fan names survive a write → reload cycle | Second instance shows `entries[0].name == "🌡 Stue-vifte"` |
| `test_clear_name_persists` | Clearing a name (renaming to `""`) is also persisted; the blank name is not accidentally filled in by reload | Second instance shows `entries[0].name == ""` |

---

### TestRenameAfterReconnect

Bug-prevention tests: ensures that reconnecting to a known device does **not** wipe the
user's custom name. This was a real defect in the original implementation.

| Test | Purpose | Expected result |
|------|---------|----------------|
| `test_name_preserved_on_reconnect` | When `record()` is called again for a device that already has a custom name, the name must not be reset | After reconnect: `entry.name == "Living Room"` (IP may change; name must not) |
| `test_name_preserved_on_reconnect_and_reload` | Name survives both the reconnect call *and* a full file reload (full end-to-end path) | After restart: `entries[0].name == "Kitchen Fan"` |
| `test_new_device_has_empty_name` | A device never seen before starts with an empty name — there is nothing to accidentally preserve | `entries[0].name == ""` |
| `test_rename_unknown_device_is_noop` | Calling `rename()` for a `device_id` not present in history should be a silent no-op | No exception raised; `entries == []` |

---

## test_protocol.py

Tests for `blauberg_vento.protocol` — the low-level UDP binary protocol used to
communicate with Blauberg Vento fans. All packet formats are verified against the
official Blauberg specification.

---

### TestChecksum

Verifies the custom XOR-based packet checksum algorithm.

| Test | Purpose | Expected result |
|------|---------|----------------|
| `test_spec_rq` | The exact REQUEST example from the Blauberg spec passes checksum verification | `verify_checksum()` does not raise |
| `test_spec_rs` | The exact RESPONSE example from the Blauberg spec passes checksum verification | `verify_checksum()` does not raise |
| `test_bad_checksum` | A single corrupted byte in a valid packet triggers a checksum error | `VentoChecksumError` raised |

---

### TestBuilding

Ensures `build_read()`, `build_write_resp()`, and `build_discovery()` produce
correctly structured binary packets.

| Test | Purpose | Expected result |
|------|---------|----------------|
| `test_matches_spec` | `build_read()` with POWER + SPEED produces the exact byte sequence from the Blauberg spec | Output `== SPEC_RQ` |
| `test_starts_fd_fd` | All packets begin with the `0xFD 0xFD` magic header | First 2 bytes are `b'\xFD\xFD'` |
| `test_checksum_valid` | Packets built by `build_read()` always carry a valid checksum | `verify_checksum()` passes on the built packet |
| `test_discovery_default_id` | `build_discovery()` embeds the literal string `DEFAULT_DEVICEID` in the device-ID field | Bytes 4–20 equal `b'DEFAULT_DEVICEID'` |
| `test_night_timer_page_cmd` | `NIGHT_TIMER` is a page-3 parameter; its packet includes a `CMD_PAGE 0x03` prefix | Raw packet body contains `0xFF 0x03 0x02` |
| `test_bad_id_raises` | Passing a device ID shorter than 16 bytes raises an exception | Exception raised |
| `test_long_password_raises` | Passing a password longer than 4 characters raises an exception | Exception raised |

---

### TestParsing

Tests for `parse_response()` — converting raw response bytes back into a
`{Param → bytes}` dictionary.

| Test | Purpose | Expected result |
|------|---------|----------------|
| `test_spec_response` | The spec example response decodes to the expected POWER and SPEED values | `r[Param.POWER] == b'\x00'` and `r[Param.SPEED] == b'\x03'` |
| `test_unsupported_param` | A response containing an unknown parameter code raises `VentoUnsupportedParamError` with the offending code in the exception | Exception raised; `0x0001` in `exception.params` |
| `test_size_override` | A 2-byte value prefixed with `CMD_SIZE` is read as a multi-byte field | `BATTERY_VOLTAGE` decoded to 5000 (0x1388 little-endian) |
| `test_page_change` | A page-3 parameter wrapped in a `CMD_PAGE` prefix is decoded into the correct multi-byte value | `NIGHT_TIMER` decoded to `(30, 8)` |

---

### TestDecoders

Unit tests for each decode/encode helper function for complex fan parameters.

| Test | Purpose | Expected result |
|------|---------|----------------|
| `test_decode_ip` | Four raw bytes decode to a human-readable dotted-quad string | `"192.168.1.50"` |
| `test_encode_ip` | Dotted-quad string encodes back to four bytes | `bytes([192, 168, 1, 50])` |
| `test_firmware` | Firmware version bytes decode to a dict with major, minor, day, month, year | `{'major':1, 'minor':5, 'day':14, 'month':3, 'year':2024}` |
| `test_machine_hours` | Runtime counter bytes decode to minutes, hours, days | `{'minutes':30, 'hours':5, 'days':10}` |
| `test_rtc_time` | RTC time bytes decode to seconds, minutes, hours | `{'seconds':45, 'minutes':30, 'hours':14}` |
| `test_rtc_calendar` | RTC calendar bytes decode with correct year (adds 2000 offset) and month | `year == 2024`, `month == 6` |
| `test_schedule` | Schedule bytes decode with correct speed, end hour, and end minutes | `speed == 2`, `end_hours == 8`, `end_minutes == 30` |
| `test_filter_countdown` | Filter countdown bytes decode to minutes, hours, days | `{'minutes':0, 'hours':12, 'days':90}` |
| `test_bad_ip_size` | Passing fewer than 4 bytes to `decode_ip()` raises an exception | Exception raised |

---

### TestValidation

Ensures `VentoClient` rejects out-of-range values before sending any packets.

| Test | Purpose | Expected result |
|------|---------|----------------|
| `test_bad_speed` | `set_speed(5)` is rejected — valid fan speeds are 1–4 | `VentoValueError` raised |
| `test_bad_humidity_threshold` | `set_humidity_threshold(100)` is rejected — valid range is 0–95 % | `VentoValueError` raised |
| `test_bad_boost_delay` | `set_boost_delay(61)` is rejected — maximum boost delay is 60 minutes | `VentoValueError` raised |
| `test_long_password` | `change_password('TOOLONGPWD')` is rejected — maximum password length is 4 characters | `VentoValueError` raised |
| `test_manual_speed_boundaries` | `set_manual_speed(0)` and `set_manual_speed(255)` are both accepted — full 8-bit range is valid | No exception raised |

---

## test_scenarios.py

Tests for `ventocontrol.scenarios` — the `ScenarioStore` that lets users save named
fan configurations ("Night Mode", "Away", etc.) and assign up to 3 of them to
quick-access slots per device. Scenarios can cover multiple fans simultaneously.
All tests redirect file I/O to a temp directory.

---

### TestScenarioSettings

Validates the `ScenarioSettings` data class that holds one fan's target state.

| Test | Purpose | Expected result |
|------|---------|----------------|
| `test_all_none_default` | A `ScenarioSettings()` with no arguments has all 7 fields set to `None` | All 7 attributes are `None` |
| `test_partial_construction` | Providing only `power` and `speed` leaves other fields as `None` | `power == True`, `speed == 2`, `operation_mode is None` |
| `test_all_fields` | All 7 fields can be set and retrieved independently | Each field matches the value passed to the constructor |

---

### TestFanSettings

Validates `FanSettings` — the pairing of a `device_id` with a `ScenarioSettings`.

| Test | Purpose | Expected result |
|------|---------|----------------|
| `test_basic` | `FanSettings` stores both device ID and settings | `fs.device_id == "ABCD1234"` and `fs.settings.power is True` |
| `test_none_settings` | `FanSettings` with an all-None `ScenarioSettings` is valid | `fs.settings.speed is None` |

---

### TestScenarioEntry

Validates `ScenarioEntry` — a named scenario that covers one or more fans — and
the `get_settings_for_device()` lookup helper.

| Test | Purpose | Expected result |
|------|---------|----------------|
| `test_single_fan` | A single-fan entry stores its name and the fan's settings correctly | `entry.name == "Night"`, 1 fan, correct device_id and settings |
| `test_multi_fan` | A two-fan entry stores both fans with their respective device IDs | 2 fans; correct IDs and speed for each |
| `test_get_settings_for_device_found` | `get_settings_for_device()` returns the correct `ScenarioSettings` for a matching device ID | `settings.speed == 3` for DEV2 |
| `test_get_settings_for_device_first` | Works correctly for the first device in the list (not just non-first entries) | `settings.speed == 3` for DEV1 |
| `test_get_settings_for_device_not_found` | Returns `None` when the requested device ID is not in the scenario's fan list | `None` returned |
| `test_get_settings_for_device_empty_fans` | Returns `None` for a scenario with an empty fan list | `None` returned |

---

### TestScenarioStorePersistence

Core persistence, overwrite, eviction, deletion, and quick-slot tests for `ScenarioStore`.

| Test | Purpose | Expected result |
|------|---------|----------------|
| `test_save_and_reload` | A scenario saved by one `ScenarioStore` instance is fully restored by a new instance reading the same file | Loaded scenario has correct name, device_id, power, and speed |
| `test_overwrite_in_place` | Saving a scenario whose name already exists updates it **in place** (same list position, no duplicate) | 2 entries total; "A" stays at index 0 with the new speed value |
| `test_cap_eviction` | When the 11th scenario is added (cap = 10), the oldest (index 0) is evicted; any quick-slot pointing to the evicted scenario is automatically cleared | 10 entries remain; oldest is gone; `quick_slots[0] is None` |
| `test_delete` | `delete_scenario()` removes a named scenario and clears any quick-slot references to it | 1 entry remains ("Keep"); `quick_slots[0] is None` |
| `test_delete_nonexistent_is_noop` | Deleting a name that doesn't exist leaves the store unchanged | Still 1 entry; no exception |
| `test_quick_slots_set_and_get` | Quick slots assigned via `set_quick_slots()` are returned unchanged by `get_quick_slots()` | `["A", None, None]` |
| `test_quick_slots_normalise_missing_device` | `get_quick_slots()` for an unknown device always returns `[None, None, None]` (length = `_QUICK_SLOTS`) | 3 `None` values |
| `test_quick_slots_truncated_if_too_long` | A list longer than `_QUICK_SLOTS` is silently truncated on assignment | Returned list has exactly `_QUICK_SLOTS` items; "EXTRA" is absent |
| `test_malformed_json` | A corrupt JSON file results in an empty store — no crash | `get_scenarios() == []` |
| `test_missing_file` | A completely absent file starts as an empty store with default quick-slots | `get_scenarios() == []` and `get_quick_slots("DEV1") == [None, None, None]` |
| `test_migration_v1` | A v1-format file (per-device scenario lists) is auto-migrated to v2 on first load; name, settings, and quick-slot references are preserved | 1 entry; name "Night"; correct settings; `quick_slots[0] == "Night"` |
| `test_migration_v1_name_collision` | When two v1 devices share the same scenario name, migration disambiguates by appending a device suffix | 2 entries; one is "Night"; the other contains "Night" with a suffix |

---

### TestScenarioStoreMultiFan

Persistence and management of scenarios that control more than one fan.

| Test | Purpose | Expected result |
|------|---------|----------------|
| `test_multi_fan_save_load` | A 2-fan scenario survives a full save → reload cycle | 1 entry with 2 fans; correct device IDs and settings after reload |
| `test_get_settings_for_device` | After reload, `get_settings_for_device()` returns the correct per-device settings | DEV1 speed=1, DEV2 speed=3; DEV3 returns `None` |
| `test_delete_clears_all_device_slots` | Deleting a multi-fan scenario clears quick-slots for **all** devices it covered, not just the first | `get_quick_slots("DEV1") == [None, None, None]` and same for DEV2 |
| `test_overwrite_multi_fan_in_place` | Overwriting a scenario with a different number of fans preserves its position in the ordered list | "Multi" stays at index 1; updated to 2 fans; speed values are updated |

---

### TestScenarioStoreEdgeCases

Robustness tests for unusual but valid inputs and corrupt data.

| Test | Purpose | Expected result |
|------|---------|----------------|
| `test_empty_fans_list` | A scenario with zero fans saves and loads without error | 1 entry loaded; `fans == []` |
| `test_unicode_name` | Emoji and non-ASCII characters in a scenario name round-trip correctly through JSON | Second instance shows `name == "🌡 Natt-modus"` |
| `test_independent_quick_slots_per_device` | Each `device_id` has its own independent quick-slot array | DEV1 and DEV2 hold different slot assignments |
| `test_malformed_fan_entry_skipped` | A fan entry missing the `"settings"` key is skipped silently; valid entries are still loaded | 1 entry ("Good") loaded; "Bad" is absent |
| `test_save_writes_version_2` | The JSON file written by `_save()` always contains `"version": 2` and both `"scenarios"` and `"quick_slots"` keys | `on_disk["version"] == 2`; both keys present |

---

## test_simulator.py

Tests for `ventocontrol.simulator` — the software fan simulator used for development
and Docker-based testing without real hardware.

---

### TestMakeSimId

Tests for `_make_sim_id()` — generates consistent, fixed-length device IDs for simulated fans.

| Test | Purpose | Expected result |
|------|---------|----------------|
| `test_length_is_16` | IDs must always be exactly 16 characters (the Blauberg protocol field size) | `len(_make_sim_id(0)) == 16` |
| `test_first_device` | Index 0 produces a predictable, human-readable ID | `"SIMFAN0000000001"` |
| `test_second_device` | Index 1 produces the next sequential ID | `"SIMFAN0000000002"` |
| `test_uses_default_prefix` | Without an explicit prefix, the default `SIM_ID_PREFIX` is used | ID starts with `SIM_ID_PREFIX` |
| `test_custom_prefix` | A caller-supplied prefix replaces the default while still producing a 16-char result | `len(result) == 16` and starts with `"FAN"` |
| `test_large_index` | Index 99 maps to number 100; the ID is still exactly 16 chars | Ends with `"100"`; length = 16 |

---

### TestParseReadRequestData

Tests for `_parse_read_request_data()` — decodes the data field of a READ packet into a list of integer parameter codes.

| Test | Purpose | Expected result |
|------|---------|----------------|
| `test_empty_data` | Empty input returns an empty list | `[]` |
| `test_single_param_page_zero` | A single page-0 parameter byte is decoded to its full integer Param code | `[int(Param.POWER)]` |
| `test_multiple_params_same_page` | Multiple page-0 params in one data field are all decoded | Both `POWER` and `SPEED` codes present in result |
| `test_page_change_sets_high_byte` | `CMD_PAGE 0x03` opcode shifts subsequent parameter codes to page 3 (high byte = `0x03`) | `int(Param.NIGHT_TIMER)` present in result |
| `test_page_resets_between_params` | A page-0 param before and a page-3 param after a `CMD_PAGE` are both parsed correctly | Both `POWER` and `NIGHT_TIMER` codes present |

---

### TestParseWriteData

Tests for `_parse_write_data()` — decodes the data field of a WRITE packet into a `{param_code: bytes}` dict.

| Test | Purpose | Expected result |
|------|---------|----------------|
| `test_empty_data` | Empty input returns an empty dict | `{}` |
| `test_single_byte_param` | A single `param_code + value` byte pair is decoded correctly | `{int(Param.POWER): b"\x01"}` |
| `test_multi_byte_param_via_cmd_size` | `CMD_SIZE 2` prefix causes two bytes to be read as the value (e.g., FAN1_SPEED = 1000 RPM little-endian) | `{int(Param.FAN1_SPEED): bytes([0xE8, 0x03])}` |
| `test_multiple_params` | POWER and SPEED both present in one write data field | Both keys decoded correctly |

---

### TestBuildResponseData

Tests for `_build_response_data()` — constructs the data field of a response packet from a param list and the current device state.

| Test | Purpose | Expected result |
|------|---------|----------------|
| `test_empty_request_returns_empty` | No requested params → no response bytes | `b""` |
| `test_known_single_byte_param` | A param present in state appears as its value byte in the output | `b"\x01"` present in output |
| `test_unknown_param_gets_not_sup` | A param missing from state is encoded as `CMD_NOT_SUP` | `CMD_NOT_SUP` byte present in output |
| `test_page_prefix_inserted_for_page3_param` | Page-3 params (e.g., NIGHT_TIMER) are prefixed with `CMD_PAGE` so the client can decode them | `CMD_PAGE` byte present in output |
| `test_multi_byte_param_prefixed_with_cmd_size` | Multi-byte params (e.g., FAN1_SPEED = 2 bytes) are prefixed with `CMD_SIZE` | `CMD_SIZE` byte present in output |

---

### TestSimDeviceInit

Tests for `SimDevice.__init__()` — verifies that a simulated fan starts up with the
correct identity and state based on its index (variant).

| Test | Purpose | Expected result |
|------|---------|----------------|
| `test_device_id_is_16_chars` | Device ID field must be exactly 16 characters for protocol compatibility | `len(device_id) == 16` |
| `test_device_id_uses_prefix` | Default prefix `SIM_ID_PREFIX` is used | `device_id.startswith(SIM_ID_PREFIX)` |
| `test_password_is_default` | All simulated fans use the `SIM_PASSWORD` constant | `password == SIM_PASSWORD` |
| `test_index_stored` | Constructor index is accessible for later reference | `SimDevice(2).index == 2` |
| `test_id_bytes_matches_device_id` | `id_bytes` is the ASCII-encoded form of `device_id` (used for raw socket comparison) | `id_bytes == device_id.encode("ascii")` |
| `test_state_has_required_keys` | Initial state dict contains all mandatory parameters that the GUI reads | All of POWER, SPEED, FAN1_SPEED, FAN2_SPEED, CURRENT_HUMIDITY, OPERATION_MODE present |
| `test_variant0_power_off` | Index 0 (variant 0) initialises with the fan off — provides a useful "powered off" test device | `_state[Param.POWER] == b"\x00"` |
| `test_variant1_power_on` | Index 1 (variant 1) initialises with the fan running | `_state[Param.POWER] == b"\x01"` |
| `test_variant2_power_on` | Index 2 (variant 2) also initialises with the fan running (different speed preset) | `_state[Param.POWER] == b"\x01"` |
| `test_variants_wrap_at_index3` | Index 3 wraps back to variant 0 (power off) | `_state[Param.POWER] == b"\x00"` |
| `test_custom_prefix` | A custom `id_prefix` is supported for scenarios needing distinct ID namespaces | `device_id.startswith("MYFAN")` and `len(device_id) == 16` |
| `test_device_search_param_contains_own_id` | The `DEVICE_SEARCH` parameter in state is pre-populated with the device's own ID bytes (used for discovery responses) | `_state[Param.DEVICE_SEARCH] == id_bytes` |

---

### TestSimDeviceSetLanIp

Tests for `SimDevice.set_lan_ip()` — stores the device's own IP address in state
so it can be returned in discovery responses.

| Test | Purpose | Expected result |
|------|---------|----------------|
| `test_valid_ip_stored` | A valid IPv4 address is encoded to 4 bytes and stored in `WIFI_CURRENT_IP` | `_state[Param.WIFI_CURRENT_IP] == bytes([192, 168, 1, 42])` |
| `test_invalid_ip_does_not_raise` | An invalid IP string is silently ignored — the simulator must not crash during startup | No exception raised |
| `test_loopback_stored` | The loopback address `127.0.0.1` is stored correctly (used in test environments) | `_state[Param.WIFI_CURRENT_IP] == bytes([127, 0, 0, 1])` |

---

### TestSimDeviceTick

Tests for `SimDevice.tick(dt)` — the physics simulation step that updates fan RPM,
humidity drift, timestamps, and other time-varying state.

| Test | Purpose | Expected result |
|------|---------|----------------|
| `test_tick_does_not_raise` | A single tick with any `dt` must never raise an exception | No exception raised |
| `test_powered_off_fans_ramp_toward_zero` | When the fan is off, RPM ramps down at 80 RPM/s until it reaches near zero | After 120 ticks of 0.1 s, `_fan1_rpm < 10.0` |
| `test_powered_on_fans_ramp_up` | When the fan is on, RPM ramps up from zero toward the target speed | After 30 ticks of 0.1 s, `_fan1_rpm > 0.0` |
| `test_fan_speed_stored_in_state` | After ticking, the live `FAN1_SPEED` value in state is updated as a little-endian integer | `int.from_bytes(_state[Param.FAN1_SPEED], "little") >= 0` |
| `test_humidity_stays_in_bounds` | Humidity drifts randomly but is clamped to the valid sensor range 30–95 % | After 300 ticks, `30 <= CURRENT_HUMIDITY[0] <= 95` |
| `test_rtc_time_is_3_bytes` | After a tick, `RTC_TIME` is exactly 3 bytes (seconds, minutes, hours) | `len(_state[Param.RTC_TIME]) == 3` |
| `test_machine_hours_is_4_bytes` | After a tick, `MACHINE_HOURS` is exactly 4 bytes | `len(_state[Param.MACHINE_HOURS]) == 4` |
| `test_manual_speed_mode` | When speed is set to 255 (manual mode), the fan ramps toward the `MANUAL_SPEED` target | After 30 ticks, `_fan1_rpm > 0.0` |
| `test_humidity_status_set_when_above_threshold` | When humidity exceeds `HUMIDITY_THRESHOLD`, the `HUMIDITY_STATUS` flag is set to 1 | `_state[Param.HUMIDITY_STATUS] == b"\x01"` |
| `test_humidity_status_clear_when_below_threshold` | When humidity is below `HUMIDITY_THRESHOLD`, the `HUMIDITY_STATUS` flag is cleared | `_state[Param.HUMIDITY_STATUS] == b"\x00"` |

---

### TestSimDeviceApplyWrites

Tests for `SimDevice._apply_writes()` — processes a dict of `{param_code: bytes}` and
updates device state, including special-cased parameters like POWER toggle and FILTER_RESET.

| Test | Purpose | Expected result |
|------|---------|----------------|
| `test_normal_write_updates_state` | Writing a value to an ordinary param (SPEED) updates that param in state | `_state[Param.SPEED] == b"\x03"` |
| `test_power_toggle_off_to_on` | Writing `0x02` to POWER (toggle command) flips a powered-off fan ON | `_state[Param.POWER] == b"\x01"` |
| `test_power_toggle_on_to_off` | Writing `0x02` to POWER flips a powered-on fan OFF | `_state[Param.POWER] == b"\x00"` |
| `test_power_direct_set_on` | Writing `0x01` to POWER directly sets it ON (not toggle) | `_state[Param.POWER] == b"\x01"` |
| `test_filter_reset_restores_countdown` | Writing `0x01` to `FILTER_RESET` restores the filter countdown to 180 days and clears the filter indicator | `FILTER_COUNTDOWN == b"\x00\x00\xB4"` and `FILTER_INDICATOR == b"\x00"` |
| `test_reset_alarms_clears_status` | Writing `0x01` to `RESET_ALARMS` sets `ALARM_STATUS` to zero | `_state[Param.ALARM_STATUS] == b"\x00"` |
| `test_factory_reset_zeros_fans` | A factory reset immediately stops both fans (RPM → 0) | `_fan1_rpm == 0.0` and `_fan2_rpm == 0.0` |
| `test_factory_reset_restores_variant_defaults` | Factory reset reinstates the device's original variant state (not all zeros) | Variant-1 device recovers `POWER == b"\x01"` |
| `test_unknown_param_ignored` | Writing to an unrecognised parameter code is silently ignored — no crash | No exception raised |

---

### TestSimDeviceNudge

Tests for `SimDevice._nudge()` — increments or decrements a parameter by a given delta,
clamped to the parameter's valid range.

| Test | Purpose | Expected result |
|------|---------|----------------|
| `test_nudge_speed_up` | `_nudge(SPEED, +1)` increments speed by 1 | `_state[Param.SPEED] == b"\x02"` |
| `test_nudge_speed_down` | `_nudge(SPEED, -1)` decrements speed by 1 | `_state[Param.SPEED] == b"\x01"` |
| `test_nudge_clamps_to_max` | `_nudge(SPEED, +10)` with speed at maximum does not exceed the max | `value <= 3` |
| `test_nudge_clamps_to_min` | `_nudge(SPEED, -10)` with speed at minimum does not go below the min | `value >= 1` |
| `test_nudge_unknown_param_does_not_raise` | Nudging an unknown parameter code is a silent no-op | No exception raised |

---

### TestSimDeviceHandle

Tests for `SimDevice.handle()` — the top-level packet dispatcher that processes a
decoded function code, calls the appropriate action, and sends a UDP reply if needed.
A `MagicMock` socket is used so no real network traffic is generated.

| Test | Purpose | Expected result |
|------|---------|----------------|
| `test_read_triggers_sendto` | A `Func.READ` packet causes the device to send a response via `sock.sendto()` | `sock.sendto` was called |
| `test_write_updates_state_without_sending` | A `Func.WRITE` packet updates device state but does **not** send a reply (fire-and-forget protocol) | State updated; `sock.sendto` not called |
| `test_write_resp_updates_state_and_sends` | A `Func.WRITE_RESP` packet updates state **and** sends a confirmation reply | State updated; `sock.sendto` was called |
| `test_increment_nudges_param_and_sends` | `Func.INCREMENT` increments the parameter and sends a response | SPEED goes from 1 → 2; `sock.sendto` called |
| `test_decrement_nudges_param_and_sends` | `Func.DECREMENT` decrements the parameter and sends a response | SPEED goes from 2 → 1; `sock.sendto` called |

---

### TestVentoFanSimConstruction

Tests for `VentoFanSim.__init__()` — verifies that the multi-device simulator
creates the correct number of devices with consistent IDs.

| Test | Purpose | Expected result |
|------|---------|----------------|
| `test_default_single_device` | Default construction creates exactly 1 simulated device | `len(sim._devices) == 1` |
| `test_creates_n_devices` | `count=3` creates 3 devices | `len(sim._devices) == 3` |
| `test_id_map_has_n_entries` | The internal `_id_map` (used for routing) has one entry per device | `len(sim._id_map) == 2` for `count=2` |
| `test_start_index_offsets_device_id` | `start_index=5` generates the ID for index 5 — allows unique IDs across multiple simulator processes | `sim._devices[0].device_id == _make_sim_id(5)` |
| `test_id_map_keys_are_bytes` | `_id_map` is keyed by raw bytes (matching the protocol's device-ID field) | All keys are `bytes` instances |

---

### TestVentoFanSimDispatch

Tests for `VentoFanSim._dispatch()` — the UDP receive handler that routes incoming
packets to the correct `SimDevice`, or broadcasts to all devices for discovery.

| Test | Purpose | Expected result |
|------|---------|----------------|
| `test_discovery_gets_response_from_every_device` | A discovery packet (broadcast device ID) causes every simulated device to reply | `sock.sendto` called twice for a 2-device simulator |
| `test_directed_packet_routes_to_correct_device` | A READ packet addressed to device 1 is handled only by device 1 | `sock.sendto` called exactly once |
| `test_bad_checksum_packet_ignored` | A packet with a corrupted checksum is silently dropped — no reply is sent | `sock.sendto` not called |
| `test_unknown_device_id_ignored` | A packet addressed to a device ID not in the simulator is silently dropped | `sock.sendto` not called |

---

### TestGetLanIp

Tests for `_get_lan_ip()` — detects the machine's LAN IP address for embedding in
simulated discovery responses.

| Test | Purpose | Expected result |
|------|---------|----------------|
| `test_returns_string` | The function always returns a `str` (not bytes or None) | `isinstance(_get_lan_ip(), str)` |
| `test_returns_dotted_quad` | The returned string is a valid dotted-quad IPv4 address | 4 dot-separated numeric parts |

---

## tests/webdashboard/test_hub.py

Tests for `webdashboard.backend.hub.ConnectionHub` — the WebSocket broadcast hub that
distributes real-time fan state to all connected browser clients.

| Test | Purpose | Expected result |
|------|---------|----------------|
| `test_connect_accepts_websocket` | `connect()` calls `websocket.accept()` and increments the client count | `client_count == 1` |
| `test_disconnect_removes_client` | `disconnect()` removes the socket from the active set | `client_count == 0` |
| `test_broadcast_sends_json_to_all_clients` | `broadcast()` sends a JSON-serialised dict to every connected socket | Both mock sockets receive the expected JSON string |
| `test_broadcast_removes_dead_connections` | A socket that raises on `send_text` is silently removed; healthy sockets still receive the message | `client_count == 1`; healthy socket received message |
| `test_broadcast_to_empty_hub_is_noop` | Broadcasting with no connected clients raises no exception | No exception raised |

---

## tests/webdashboard/test_device_manager.py

Tests for `webdashboard.backend.device_manager.DeviceManager` — the async use-case layer
that wraps `AsyncVentoClient`. All UDP I/O is mocked.

| Test | Purpose | Expected result |
|------|---------|----------------|
| `test_state_to_dict_maps_fields` | `_state_to_dict()` maps all required DeviceState fields to the correct JSON-serialisable keys | All key fields match, `operation_mode_name == "Ventilation"` |
| `test_initially_not_connected` | A fresh `DeviceManager` is not connected and has no state | `is_connected == False`, `current_state is None` |
| `test_connect_sets_state_and_starts_polling` | `connect()` calls `get_state()` and starts the poll task | `is_connected == True`, `_poll_task` is not None |
| `test_disconnect_clears_state` | `disconnect()` resets `is_connected` and `current_state` | Both false/None after disconnect |
| `test_set_power_calls_turn_on` | `set_power(True)` calls `client.turn_on()` | `turn_on` awaited; `turn_off` not called |
| `test_set_power_calls_turn_off` | `set_power(False)` calls `client.turn_off()` | `turn_off` awaited |
| `test_set_speed_preset` | `set_speed(3)` calls `client.set_speed(3)` | `set_speed` awaited with 3 |
| `test_set_speed_manual` | `set_speed(180)` calls `client.set_manual_speed(180)` | `set_manual_speed` awaited with 180 |
| `test_set_mode` | `set_mode(1)` calls `client.set_mode(1)` | `set_mode` awaited with 1 |
| `test_require_connection_raises_when_disconnected` | Any command without a connection raises `RuntimeError` | `RuntimeError` raised |
| `test_discover_delegates_to_client` | `DeviceManager.discover()` delegates to `AsyncVentoClient.discover()` | Returns the mocked device list |
| `test_broadcast_callback_called_after_command` | After `set_power()`, the registered broadcast callback receives a `type: state` message | `type == "state"` in received messages |
| `test_connect_replaces_active_device` | Connecting to a second device cancels the first poller and makes the new device active | `current_state.device_id == "FAN-B"`; old poll task is done; new poll task is different |
| `test_switch_preserves_connection_to_new_device` | After switching, commands are sent to the second device, not the first | `client_b.turn_on` awaited; `client_a.turn_on` not called |
| `test_switch_active_state_reflects_new_device` | After switching, `current_state` carries the new device's IP, ID, speed, and RPM values | All fields reflect device B (ip, device_id, speed, fan1_rpm) |

---

## tests/webdashboard/test_routers_devices.py

Integration tests for the device state, connect, and discovery HTTP endpoints using
`httpx.AsyncClient` against the FastAPI app with `DeviceManager` dependency-overridden
by a mock. Fan-switching is covered end-to-end at the router level.

| Test | Purpose | Expected result |
|------|---------|----------------|
| `test_get_state_returns_200_when_connected` | `GET /api/state` returns device fields when connected | HTTP 200; `connected == True`; correct `ip` and `device_id` |
| `test_get_state_returns_503_when_disconnected` | `GET /api/state` returns 503 when no device is active | HTTP 503 |
| `test_connect_returns_device_state` | `POST /api/connect` returns the device's initial state | HTTP 200; `device_id` matches request; `manager.connect` awaited with correct args |
| `test_connect_uses_provided_password` | Password in the request body is forwarded to `manager.connect` | `manager.connect` awaited with the custom password |
| `test_connect_returns_502_on_connection_error` | A connection timeout or refused error returns HTTP 502 with the error message | HTTP 502; `"Timeout"` in response detail |
| `test_switch_fan_returns_new_device_state` | Two sequential `POST /api/connect` calls each return the state of the respective device | First response: `device_id == "FAN-A"`, `speed == 1`; second: `device_id == "FAN-B"`, `speed == 3` |
| `test_switch_fan_connect_called_with_correct_credentials` | Each switch call forwards the exact IP, device ID, and password to `manager.connect` | `connect` awaited twice with the correct distinct credentials |
| `test_disconnect_returns_204` | `DELETE /api/connect` calls `manager.disconnect()` and returns 204 | HTTP 204; `disconnect` called once |
| `test_list_devices_returns_discovered` | `GET /api/devices` triggers a scan and returns a list of discovered devices | HTTP 200; two entries with correct `device_id` and `ip` |
| `test_list_devices_returns_empty_list_when_none_found` | `GET /api/devices` returns an empty array when no devices are on the network | HTTP 200; `[] == body` |

---

## tests/webdashboard/test_routers_commands.py

Integration tests for the command HTTP endpoints using `httpx.AsyncClient` against the
FastAPI app with `DeviceManager` dependency-overridden by a mock.

| Test | Purpose | Expected result |
|------|---------|----------------|
| `test_set_power_on` | `POST /api/command/power {"on": true}` delegates to `manager.set_power(True)` | HTTP 204; `set_power` awaited with `True` |
| `test_set_power_off` | `POST /api/command/power {"on": false}` | HTTP 204; `set_power` awaited with `False` |
| `test_set_speed` | `POST /api/command/speed {"speed": 3}` | HTTP 204; `set_speed` awaited with `3` |
| `test_set_mode` | `POST /api/command/mode {"mode": 1}` | HTTP 204; `set_mode` awaited with `1` |
| `test_set_boost` | `POST /api/command/boost {"on": true}` | HTTP 204; `set_boost` awaited with `True` |
| `test_command_returns_503_when_disconnected` | Any command endpoint returns 503 when `is_connected == False` | HTTP 503 |
| `test_invalid_mode_returns_422` | `mode: 99` fails Pydantic validation | HTTP 422 |

---

## tests/webdashboard/test_routers_scenarios.py

Integration tests for scenario CRUD and quick-slot endpoints.

| Test | Purpose | Expected result |
|------|---------|----------------|
| `test_list_scenarios` | `GET /api/scenarios` returns the store's scenario list as JSON | HTTP 200; `data[0]["name"] == "Night"` |
| `test_save_scenario` | `POST /api/scenarios` saves current device state and returns the new entry | HTTP 201; `store.save_scenario` called |
| `test_delete_scenario` | `DELETE /api/scenarios/Night` calls `store.delete_scenario("Night")` | HTTP 204 |
| `test_delete_nonexistent_returns_404` | Deleting a name not in the store returns 404 | HTTP 404 |
| `test_apply_scenario` | `POST /api/scenarios/Night/apply` calls manager commands from the scenario settings | HTTP 204; `set_power` awaited |
| `test_apply_scenario_not_found` | Applying a missing scenario returns 404 | HTTP 404 |
| `test_get_quick_slots` | `GET /api/scenarios/quick-slots/VENT-01` returns the device's slot assignments | HTTP 200; `slots` has 3 elements |
| `test_set_quick_slots` | `PUT /api/scenarios/quick-slots/VENT-01` saves new slot assignments | HTTP 200; `store.set_quick_slots` called with new list |

---

## tests/webdashboard/e2e/test_dashboard.py

Playwright end-to-end tests that drive a real browser against the running web dashboard.
Requires the backend (`python -m webdashboard`) and a reachable device or simulator.

| Test | Purpose | Expected result |
|------|---------|----------------|
| `test_connect_dialog_shown_on_load` | On first load with no device connected, the connect dialog is visible | Dialog with `aria-label="Connect to device"` is visible |
| `test_connect_dialog_has_rescan_button` | The connect dialog has a Rescan button for UDP discovery | "Rescan" button visible |
| `test_power_button_visible_when_connected` | After connecting, the power button is rendered | Button with `aria-label` matching `/Turn (on\|off)/i` is visible |
| `test_power_button_toggle` | Clicking the power button changes its `aria-label` to the opposite state | `aria-label` flips between "Turn on" and "Turn off" |
| `test_speed_preset_buttons_visible` | Speed preset buttons 1/2/3 are visible after connecting | Three buttons found |
| `test_speed_preset_activates` | Clicking Speed 2 sets its `aria-pressed` to `"true"` | `aria-pressed == "true"` on the clicked button |
| `test_mode_buttons_present` | All three mode buttons (Ventilation, Heat Recovery, Supply) are visible | All three found |
| `test_save_scenario_modal` | Clicking "Save as Scenario" opens the save dialog | Dialog visible |
| `test_save_scenario_and_appears_in_list` | Saving a scenario with a name results in that name appearing in the scenario list | Text "E2E Test Scenario" visible in the page |
| `test_status_bar_shows_connected` | After connecting, the status bar shows "Connected" | Text "Connected" visible |
| `test_switch_button_visible_after_connect` | The "Switch…" button in the device header is visible once a fan is connected | "Switch" button visible |
| `test_switch_reopens_connect_dialog` | Clicking "Switch…" re-opens the connect dialog without a full page reload | Connect dialog visible again |
| `test_switch_between_fans` | After switching, the dashboard header shows the new device's ID and hides the old one | "VENT-SIM-2" visible; "VENT-SIM-1" not visible |
| `test_switch_connect_dialog_is_prefilled_with_current_device` | The connect dialog pre-populates the current device's IP and ID when opened via "Switch…" | IP and Device ID inputs contain the connected device's values |
