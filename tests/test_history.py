"""Tests for ventocontrol.history (DeviceHistory, HistoryEntry).

Covers persistence, ordering, capping, rename round-trip, and the critical
requirement that a user-set fan name is NOT wiped when the app reconnects
to the same device.

All tests use monkeypatch to redirect I/O to a tmp_path directory so they
never touch ~/.ventocontrol/.
"""
from __future__ import annotations

import json

import pytest

from ventocontrol.history import DeviceHistory, HistoryEntry, _MAX_ENTRIES


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def history(tmp_path, monkeypatch):
    """A DeviceHistory backed by a temp directory."""
    monkeypatch.setattr("ventocontrol.history._HISTORY_FILE",
                        tmp_path / "history.json")
    monkeypatch.setattr("ventocontrol.history._HISTORY_DIR", tmp_path)
    return DeviceHistory()


def _record(h: DeviceHistory, device_id="DEV1", ip="1.2.3.4",
            unit_type_name="Vento Expert W30", password="1111") -> None:
    h.record(device_id=device_id, ip=ip,
             unit_type_name=unit_type_name, password=password)


# ---------------------------------------------------------------------------
# TestHistoryEntry
# ---------------------------------------------------------------------------

class TestHistoryEntry:
    def test_defaults(self):
        e = HistoryEntry(device_id="X", ip="1.2.3.4",
                         unit_type_name="Vento", password="1111")
        assert e.name      == ""
        assert e.last_seen == ""

    def test_custom_name(self):
        e = HistoryEntry(device_id="X", ip="1.2.3.4",
                         unit_type_name="Vento", password="1111", name="Bedroom")
        assert e.name == "Bedroom"


# ---------------------------------------------------------------------------
# TestDeviceHistoryBasics
# ---------------------------------------------------------------------------

class TestDeviceHistoryBasics:
    def test_empty_on_new(self, history):
        assert history.entries   == []
        assert history.last_used is None

    def test_record_adds_entry(self, history):
        _record(history)
        assert len(history.entries) == 1
        e = history.entries[0]
        assert e.device_id      == "DEV1"
        assert e.ip             == "1.2.3.4"
        assert e.unit_type_name == "Vento Expert W30"
        assert e.password       == "1111"
        assert e.last_seen      != ""   # timestamp set

    def test_last_used_is_most_recent(self, history):
        _record(history, device_id="DEV1")
        _record(history, device_id="DEV2")
        assert history.last_used.device_id == "DEV2"

    def test_record_moves_existing_to_front(self, history):
        _record(history, device_id="DEV1")
        _record(history, device_id="DEV2")
        _record(history, device_id="DEV1")  # re-connect to DEV1
        assert history.entries[0].device_id == "DEV1"
        assert len(history.entries) == 2    # no duplicate

    def test_record_cap(self, history):
        for i in range(_MAX_ENTRIES + 3):
            _record(history, device_id=f"DEV{i}")
        assert len(history.entries) == _MAX_ENTRIES

    def test_clear(self, history):
        _record(history)
        history.clear()
        assert history.entries   == []
        assert history.last_used is None

    def test_missing_file(self, tmp_path, monkeypatch):
        monkeypatch.setattr("ventocontrol.history._HISTORY_FILE",
                            tmp_path / "no_file.json")
        monkeypatch.setattr("ventocontrol.history._HISTORY_DIR", tmp_path)
        h = DeviceHistory()
        assert h.entries == []

    def test_malformed_json(self, tmp_path, monkeypatch):
        f = tmp_path / "history.json"
        f.write_text("{{not valid")
        monkeypatch.setattr("ventocontrol.history._HISTORY_FILE", f)
        monkeypatch.setattr("ventocontrol.history._HISTORY_DIR", tmp_path)
        h = DeviceHistory()
        assert h.entries == []


# ---------------------------------------------------------------------------
# TestDeviceHistoryPersistence
# ---------------------------------------------------------------------------

class TestDeviceHistoryPersistence:
    def test_reload_restores_entries(self, tmp_path, monkeypatch):
        """Entries written by one instance are visible to a new instance."""
        f = tmp_path / "history.json"
        monkeypatch.setattr("ventocontrol.history._HISTORY_FILE", f)
        monkeypatch.setattr("ventocontrol.history._HISTORY_DIR", tmp_path)

        h1 = DeviceHistory()
        _record(h1, device_id="DEV1", ip="10.0.0.1")
        _record(h1, device_id="DEV2", ip="10.0.0.2")

        h2 = DeviceHistory()
        assert len(h2.entries) == 2
        assert h2.entries[0].device_id == "DEV2"
        assert h2.entries[1].device_id == "DEV1"

    def test_rename_persists_across_restart(self, tmp_path, monkeypatch):
        """
        Core requirement: a user-set fan name must survive app restart.
        Simulated by writing with h1, reloading into h2, verifying name.
        """
        f = tmp_path / "history.json"
        monkeypatch.setattr("ventocontrol.history._HISTORY_FILE", f)
        monkeypatch.setattr("ventocontrol.history._HISTORY_DIR", tmp_path)

        h1 = DeviceHistory()
        _record(h1, device_id="DEV1")
        h1.rename("DEV1", "Bedroom Fan")

        # Simulate app restart
        h2 = DeviceHistory()
        assert h2.entries[0].name == "Bedroom Fan"

    def test_unicode_name_persists(self, tmp_path, monkeypatch):
        """Unicode / emoji in the fan name must round-trip correctly."""
        f = tmp_path / "history.json"
        monkeypatch.setattr("ventocontrol.history._HISTORY_FILE", f)
        monkeypatch.setattr("ventocontrol.history._HISTORY_DIR", tmp_path)

        h1 = DeviceHistory()
        _record(h1, device_id="DEV1")
        h1.rename("DEV1", "🌡 Stue-vifte")

        h2 = DeviceHistory()
        assert h2.entries[0].name == "🌡 Stue-vifte"

    def test_clear_name_persists(self, tmp_path, monkeypatch):
        """Clearing a name (rename to '') also persists correctly."""
        f = tmp_path / "history.json"
        monkeypatch.setattr("ventocontrol.history._HISTORY_FILE", f)
        monkeypatch.setattr("ventocontrol.history._HISTORY_DIR", tmp_path)

        h1 = DeviceHistory()
        _record(h1, device_id="DEV1")
        h1.rename("DEV1", "Temp Name")
        h1.rename("DEV1", "")   # clear it

        h2 = DeviceHistory()
        assert h2.entries[0].name == ""


# ---------------------------------------------------------------------------
# TestRenameAfterReconnect   ← the critical bug-prevention tests
# ---------------------------------------------------------------------------

class TestRenameAfterReconnect:
    def test_name_preserved_on_reconnect(self, history):
        """
        When the app reconnects to a device, the user's custom name must
        NOT be wiped by record().  This was a bug in the original implementation.
        """
        _record(history, device_id="DEV1")
        history.rename("DEV1", "Living Room")

        # Simulate reconnect (e.g., user switches device, then switches back)
        _record(history, device_id="DEV1", ip="10.0.0.99")  # IP may change (DHCP)

        e = history.entries[0]
        assert e.device_id == "DEV1"
        assert e.ip        == "10.0.0.99"   # IP updated
        assert e.name      == "Living Room" # name preserved ← was "" before fix

    def test_name_preserved_on_reconnect_and_reload(self, tmp_path, monkeypatch):
        """
        Full end-to-end: rename → reconnect → restart.
        The name must survive both the reconnect and a reload from disk.
        """
        f = tmp_path / "history.json"
        monkeypatch.setattr("ventocontrol.history._HISTORY_FILE", f)
        monkeypatch.setattr("ventocontrol.history._HISTORY_DIR", tmp_path)

        h1 = DeviceHistory()
        _record(h1, device_id="DEV1")
        h1.rename("DEV1", "Kitchen Fan")
        _record(h1, device_id="DEV1")   # reconnect

        # Simulate restart
        h2 = DeviceHistory()
        assert h2.entries[0].name == "Kitchen Fan"

    def test_new_device_has_empty_name(self, history):
        """A freshly seen device starts with an empty name."""
        _record(history, device_id="BRAND_NEW")
        assert history.entries[0].name == ""

    def test_rename_unknown_device_is_noop(self, history):
        """Renaming a device_id not in history should not crash."""
        history.rename("GHOST", "Ghost Fan")   # should not raise
        assert history.entries == []
