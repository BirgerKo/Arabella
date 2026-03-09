"""Tests for ventocontrol.scenarios.

Covers ScenarioSettings, FanSettings, ScenarioEntry, get_settings_for_device,
and all ScenarioStore methods (persistence, migration, edge cases).

All tests use a tmp_path-backed store so they never touch ~/.ventocontrol/.
"""
from __future__ import annotations

import json

import pytest

from ventocontrol.scenarios import (
    FanSettings,
    ScenarioEntry,
    ScenarioSettings,
    ScenarioStore,
    _QUICK_SLOTS,
    get_settings_for_device,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def store(tmp_path, monkeypatch):
    """A ScenarioStore wired to a temp directory instead of ~/.ventocontrol/."""
    monkeypatch.setattr("ventocontrol.scenarios._SCENARIOS_FILE",
                        tmp_path / "scenarios.json")
    monkeypatch.setattr("ventocontrol.scenarios._SCENARIOS_DIR", tmp_path)
    return ScenarioStore()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _settings(**kwargs) -> ScenarioSettings:
    return ScenarioSettings(**kwargs)


def _entry(name: str, device_ids: list[str] | None = None, **kwargs) -> ScenarioEntry:
    """Build a ScenarioEntry with one FanSettings per device_id."""
    if device_ids is None:
        device_ids = ["DEV1"]
    fans = [FanSettings(device_id=did, settings=_settings(**kwargs))
            for did in device_ids]
    return ScenarioEntry(name=name, fans=fans)


# ---------------------------------------------------------------------------
# TestScenarioSettings
# ---------------------------------------------------------------------------

class TestScenarioSettings:
    def test_all_none_default(self):
        s = ScenarioSettings()
        assert s.power             is None
        assert s.speed             is None
        assert s.manual_speed      is None
        assert s.operation_mode    is None
        assert s.boost_active      is None
        assert s.humidity_sensor   is None
        assert s.humidity_threshold is None

    def test_partial_construction(self):
        s = ScenarioSettings(power=True, speed=2)
        assert s.power == True   # noqa: E712
        assert s.speed == 2
        assert s.operation_mode is None

    def test_all_fields(self):
        s = ScenarioSettings(
            power=False, speed=255, manual_speed=128,
            operation_mode=1, boost_active=True,
            humidity_sensor=1, humidity_threshold=60,
        )
        assert s.power              is False
        assert s.speed              == 255
        assert s.manual_speed       == 128
        assert s.operation_mode     == 1
        assert s.boost_active       is True
        assert s.humidity_sensor    == 1
        assert s.humidity_threshold == 60


# ---------------------------------------------------------------------------
# TestFanSettings
# ---------------------------------------------------------------------------

class TestFanSettings:
    def test_basic(self):
        fs = FanSettings(device_id="ABCD1234", settings=ScenarioSettings(power=True))
        assert fs.device_id == "ABCD1234"
        assert fs.settings.power is True

    def test_none_settings(self):
        fs = FanSettings(device_id="X", settings=ScenarioSettings())
        assert fs.settings.speed is None


# ---------------------------------------------------------------------------
# TestScenarioEntry
# ---------------------------------------------------------------------------

class TestScenarioEntry:
    def test_single_fan(self):
        entry = _entry("Night", ["DEV1"], power=True, speed=1)
        assert entry.name == "Night"
        assert len(entry.fans) == 1
        assert entry.fans[0].device_id == "DEV1"
        assert entry.fans[0].settings.power is True
        assert entry.fans[0].settings.speed == 1

    def test_multi_fan(self):
        entry = _entry("Multi", ["DEV1", "DEV2"], speed=2)
        assert len(entry.fans) == 2
        assert entry.fans[0].device_id == "DEV1"
        assert entry.fans[1].device_id == "DEV2"
        assert entry.fans[1].settings.speed == 2

    def test_get_settings_for_device_found(self):
        entry = _entry("X", ["DEV1", "DEV2"], speed=3)
        s = get_settings_for_device(entry, "DEV2")
        assert s is not None
        assert s.speed == 3

    def test_get_settings_for_device_first(self):
        entry = _entry("X", ["DEV1", "DEV2"], speed=3)
        s = get_settings_for_device(entry, "DEV1")
        assert s is not None
        assert s.speed == 3

    def test_get_settings_for_device_not_found(self):
        entry = _entry("X", ["DEV1"])
        assert get_settings_for_device(entry, "MISSING") is None

    def test_get_settings_for_device_empty_fans(self):
        entry = ScenarioEntry(name="Empty", fans=[])
        assert get_settings_for_device(entry, "DEV1") is None


# ---------------------------------------------------------------------------
# TestScenarioStorePersistence
# ---------------------------------------------------------------------------

class TestScenarioStorePersistence:
    def test_save_and_reload(self, tmp_path, monkeypatch):
        f = tmp_path / "scenarios.json"
        monkeypatch.setattr("ventocontrol.scenarios._SCENARIOS_FILE", f)
        monkeypatch.setattr("ventocontrol.scenarios._SCENARIOS_DIR", tmp_path)

        s1 = ScenarioStore()
        s1.save_scenario(_entry("Night", ["DEV1"], power=True, speed=1))

        s2 = ScenarioStore()
        loaded = s2.get_scenarios()
        assert len(loaded) == 1
        assert loaded[0].name == "Night"
        assert loaded[0].fans[0].device_id == "DEV1"
        assert loaded[0].fans[0].settings.power is True
        assert loaded[0].fans[0].settings.speed == 1

    def test_overwrite_in_place(self, store):
        store.save_scenario(_entry("A", ["DEV1"], speed=1))
        store.save_scenario(_entry("B", ["DEV1"], speed=2))
        store.save_scenario(_entry("A", ["DEV1"], speed=3))  # overwrite

        entries = store.get_scenarios()
        assert len(entries) == 2
        # A is still at index 0 (preserved order), speed updated to 3
        assert entries[0].name == "A"
        assert entries[0].fans[0].settings.speed == 3
        assert entries[1].name == "B"

    def test_cap_eviction(self, store):
        # Fill up to the 10-entry cap
        for i in range(10):
            store.save_scenario(_entry(f"Scenario {i}", ["DEV1"], speed=1))
        # Assign slot 0 to "Scenario 0" so we can check it gets cleared
        store.set_quick_slots("DEV1", ["Scenario 0", None, None])

        # Adding one more triggers eviction of the oldest
        store.save_scenario(_entry("Scenario 10", ["DEV1"], speed=2))

        entries = store.get_scenarios()
        assert len(entries) == 10
        assert entries[0].name  == "Scenario 1"
        assert entries[-1].name == "Scenario 10"

        # Quick slot that pointed to the evicted entry is cleared
        slots = store.get_quick_slots("DEV1")
        assert slots[0] is None

    def test_delete(self, store):
        store.save_scenario(_entry("Keep", ["DEV1"], speed=1))
        store.save_scenario(_entry("Gone", ["DEV1"], speed=2))
        store.set_quick_slots("DEV1", ["Gone", None, None])

        store.delete_scenario("Gone")

        entries = store.get_scenarios()
        assert len(entries) == 1
        assert entries[0].name == "Keep"
        # Quick slot pointing to deleted scenario is cleared
        assert store.get_quick_slots("DEV1")[0] is None

    def test_delete_nonexistent_is_noop(self, store):
        store.save_scenario(_entry("Keep", ["DEV1"]))
        store.delete_scenario("DoesNotExist")
        assert len(store.get_scenarios()) == 1

    def test_quick_slots_set_and_get(self, store):
        store.save_scenario(_entry("A", ["DEV1"]))
        store.set_quick_slots("DEV1", ["A", None, None])
        assert store.get_quick_slots("DEV1") == ["A", None, None]

    def test_quick_slots_normalise_missing_device(self, store):
        """get_quick_slots for an unknown device returns [None, None, None]."""
        slots = store.get_quick_slots("UNKNOWN")
        assert slots == [None, None, None]
        assert len(slots) == _QUICK_SLOTS

    def test_quick_slots_truncated_if_too_long(self, store):
        """set_quick_slots silently truncates lists that are too long."""
        store.set_quick_slots("DEV1", ["A", "B", "C", "EXTRA"])
        slots = store.get_quick_slots("DEV1")
        assert len(slots) == _QUICK_SLOTS
        assert "EXTRA" not in slots

    def test_malformed_json(self, tmp_path, monkeypatch):
        f = tmp_path / "scenarios.json"
        f.write_text("not valid json{{}")
        monkeypatch.setattr("ventocontrol.scenarios._SCENARIOS_FILE", f)
        monkeypatch.setattr("ventocontrol.scenarios._SCENARIOS_DIR", tmp_path)

        s = ScenarioStore()
        assert s.get_scenarios() == []

    def test_missing_file(self, tmp_path, monkeypatch):
        """A completely missing file is treated as empty state."""
        f = tmp_path / "no_file.json"
        monkeypatch.setattr("ventocontrol.scenarios._SCENARIOS_FILE", f)
        monkeypatch.setattr("ventocontrol.scenarios._SCENARIOS_DIR", tmp_path)

        s = ScenarioStore()
        assert s.get_scenarios() == []
        assert s.get_quick_slots("DEV1") == [None, None, None]

    def test_migration_v1(self, tmp_path, monkeypatch):
        """A v1 JSON file is auto-migrated to v2 on load."""
        f   = tmp_path / "scenarios.json"
        v1  = {
            "devices": {
                "DEV_A": {
                    "scenarios": [
                        {
                            "name": "Night",
                            "settings": {
                                "power": True, "speed": 1, "manual_speed": None,
                                "operation_mode": 0, "boost_active": False,
                                "humidity_sensor": 0, "humidity_threshold": None,
                            },
                        }
                    ],
                    "quick_slots": ["Night", None, None],
                }
            }
        }
        f.write_text(json.dumps(v1))
        monkeypatch.setattr("ventocontrol.scenarios._SCENARIOS_FILE", f)
        monkeypatch.setattr("ventocontrol.scenarios._SCENARIOS_DIR", tmp_path)

        store   = ScenarioStore()
        entries = store.get_scenarios()

        assert len(entries) == 1
        assert entries[0].name == "Night"
        assert len(entries[0].fans) == 1
        assert entries[0].fans[0].device_id == "DEV_A"
        assert entries[0].fans[0].settings.power is True
        assert entries[0].fans[0].settings.speed == 1
        assert entries[0].fans[0].settings.boost_active is False

        # Quick-slot references are preserved
        slots = store.get_quick_slots("DEV_A")
        assert slots[0] == "Night"

    def test_migration_v1_name_collision(self, tmp_path, monkeypatch):
        """Two devices with a same-named scenario get disambiguated with a suffix."""
        f  = tmp_path / "scenarios.json"
        v1 = {
            "devices": {
                "DEVA": {
                    "scenarios": [
                        {"name": "Night", "settings": {"power": True, "speed": 1,
                         "manual_speed": None, "operation_mode": 0,
                         "boost_active": False, "humidity_sensor": 0,
                         "humidity_threshold": None}},
                    ],
                    "quick_slots": [None, None, None],
                },
                "DEVB": {
                    "scenarios": [
                        {"name": "Night", "settings": {"power": False, "speed": 2,
                         "manual_speed": None, "operation_mode": 0,
                         "boost_active": False, "humidity_sensor": 0,
                         "humidity_threshold": None}},
                    ],
                    "quick_slots": [None, None, None],
                },
            }
        }
        f.write_text(json.dumps(v1))
        monkeypatch.setattr("ventocontrol.scenarios._SCENARIOS_FILE", f)
        monkeypatch.setattr("ventocontrol.scenarios._SCENARIOS_DIR", tmp_path)

        store   = ScenarioStore()
        entries = store.get_scenarios()

        assert len(entries) == 2
        names = {e.name for e in entries}
        # One should be "Night", the other "Night (XXXX)" with a suffix
        assert "Night" in names
        assert any("Night" in n and n != "Night" for n in names)


# ---------------------------------------------------------------------------
# TestScenarioStoreMultiFan
# ---------------------------------------------------------------------------

class TestScenarioStoreMultiFan:
    def test_multi_fan_save_load(self, tmp_path, monkeypatch):
        f = tmp_path / "scenarios.json"
        monkeypatch.setattr("ventocontrol.scenarios._SCENARIOS_FILE", f)
        monkeypatch.setattr("ventocontrol.scenarios._SCENARIOS_DIR", tmp_path)

        s1 = ScenarioStore()
        entry = ScenarioEntry(
            name="Multi",
            fans=[
                FanSettings("DEV1", ScenarioSettings(power=True,  speed=1)),
                FanSettings("DEV2", ScenarioSettings(power=False, speed=2)),
            ],
        )
        s1.save_scenario(entry)

        s2     = ScenarioStore()
        loaded = s2.get_scenarios()
        assert len(loaded) == 1
        assert len(loaded[0].fans) == 2
        assert loaded[0].fans[0].device_id == "DEV1"
        assert loaded[0].fans[0].settings.power is True
        assert loaded[0].fans[1].device_id == "DEV2"
        assert loaded[0].fans[1].settings.speed == 2

    def test_get_settings_for_device(self, store):
        entry = ScenarioEntry(
            name="Multi",
            fans=[
                FanSettings("DEV1", ScenarioSettings(speed=1)),
                FanSettings("DEV2", ScenarioSettings(speed=3)),
            ],
        )
        store.save_scenario(entry)
        loaded = store.get_scenarios()[0]

        s1 = get_settings_for_device(loaded, "DEV1")
        s2 = get_settings_for_device(loaded, "DEV2")
        assert s1 is not None and s1.speed == 1
        assert s2 is not None and s2.speed == 3
        assert get_settings_for_device(loaded, "DEV3") is None

    def test_delete_clears_all_device_slots(self, store):
        """Deleting a multi-fan scenario clears quick-slots for all devices."""
        entry = ScenarioEntry(
            name="Multi",
            fans=[
                FanSettings("DEV1", ScenarioSettings(speed=1)),
                FanSettings("DEV2", ScenarioSettings(speed=2)),
            ],
        )
        store.save_scenario(entry)
        store.set_quick_slots("DEV1", ["Multi", None, None])
        store.set_quick_slots("DEV2", [None, "Multi", None])

        store.delete_scenario("Multi")

        assert store.get_quick_slots("DEV1") == [None, None, None]
        assert store.get_quick_slots("DEV2") == [None, None, None]

    def test_overwrite_multi_fan_in_place(self, store):
        """Overwriting a multi-fan scenario preserves list order."""
        store.save_scenario(_entry("First", ["DEV1"], speed=1))
        store.save_scenario(ScenarioEntry(
            name="Multi",
            fans=[FanSettings("DEV1", ScenarioSettings(speed=2))],
        ))
        store.save_scenario(_entry("Last", ["DEV1"], speed=3))

        # Overwrite "Multi" with a 2-fan version
        store.save_scenario(ScenarioEntry(
            name="Multi",
            fans=[
                FanSettings("DEV1", ScenarioSettings(speed=99)),
                FanSettings("DEV2", ScenarioSettings(speed=88)),
            ],
        ))

        entries = store.get_scenarios()
        assert len(entries) == 3
        # "Multi" is still at index 1
        assert entries[1].name == "Multi"
        assert len(entries[1].fans) == 2
        assert entries[1].fans[0].settings.speed == 99


# ---------------------------------------------------------------------------
# TestScenarioStoreEdgeCases
# ---------------------------------------------------------------------------

class TestScenarioStoreEdgeCases:
    def test_empty_fans_list(self, store):
        """A scenario with an empty fans list saves and loads cleanly."""
        entry = ScenarioEntry(name="Empty", fans=[])
        store.save_scenario(entry)
        loaded = store.get_scenarios()
        assert len(loaded) == 1
        assert loaded[0].fans == []

    def test_unicode_name(self, tmp_path, monkeypatch):
        """Emoji and non-ASCII in scenario names round-trip correctly."""
        f = tmp_path / "scenarios.json"
        monkeypatch.setattr("ventocontrol.scenarios._SCENARIOS_FILE", f)
        monkeypatch.setattr("ventocontrol.scenarios._SCENARIOS_DIR", tmp_path)

        s1 = ScenarioStore()
        s1.save_scenario(_entry("🌡 Natt-modus", ["DEV1"], speed=1))

        s2     = ScenarioStore()
        loaded = s2.get_scenarios()
        assert loaded[0].name == "🌡 Natt-modus"

    def test_independent_quick_slots_per_device(self, store):
        """Quick slots are independent per device_id."""
        store.save_scenario(_entry("Shared", ["DEV1"]))
        store.set_quick_slots("DEV1", ["Shared", None, None])
        store.set_quick_slots("DEV2", [None, "Shared", None])

        slots_a = store.get_quick_slots("DEV1")
        slots_b = store.get_quick_slots("DEV2")
        assert slots_a == ["Shared", None, None]
        assert slots_b == [None, "Shared", None]

    def test_malformed_fan_entry_skipped(self, tmp_path, monkeypatch):
        """Corrupt fan entries in the JSON file are skipped silently."""
        f = tmp_path / "scenarios.json"
        # Manually write a v2 file with one good and one bad scenario
        data = {
            "version": 2,
            "scenarios": [
                {
                    "name": "Good",
                    "fans": [
                        {"device_id": "DEV1",
                         "settings": {"power": True, "speed": 1,
                                      "manual_speed": None, "operation_mode": None,
                                      "boost_active": None, "humidity_sensor": None,
                                      "humidity_threshold": None}}
                    ],
                },
                {
                    "name": "Bad",
                    "fans": [{"device_id": "DEV2"}],  # missing "settings"
                },
            ],
            "quick_slots": {},
        }
        f.write_text(json.dumps(data))
        monkeypatch.setattr("ventocontrol.scenarios._SCENARIOS_FILE", f)
        monkeypatch.setattr("ventocontrol.scenarios._SCENARIOS_DIR", tmp_path)

        store   = ScenarioStore()
        entries = store.get_scenarios()
        assert len(entries) == 1
        assert entries[0].name == "Good"

    def test_save_writes_version_2(self, tmp_path, monkeypatch):
        """The file written by _save() always uses version=2."""
        f = tmp_path / "scenarios.json"
        monkeypatch.setattr("ventocontrol.scenarios._SCENARIOS_FILE", f)
        monkeypatch.setattr("ventocontrol.scenarios._SCENARIOS_DIR", tmp_path)

        store = ScenarioStore()
        store.save_scenario(_entry("A", ["DEV1"]))

        on_disk = json.loads(f.read_text())
        assert on_disk["version"] == 2
        assert "scenarios" in on_disk
        assert "quick_slots" in on_disk
