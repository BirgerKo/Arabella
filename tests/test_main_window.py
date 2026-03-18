"""Tests for MainWindow UI behaviour — requires an offscreen Qt display."""
from __future__ import annotations

import os
import sys
import tempfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

from blauberg_vento.models import DeviceState
from ventocontrol.history import DeviceHistory
from ventocontrol.scenarios import (
    FanSettings, ScenarioEntry, ScenarioSettings, ScenarioStore,
)
from ventocontrol.ui.main_window import MainWindow


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance() or QApplication(sys.argv)
    yield app


@pytest.fixture
def tmp_history(tmp_path):
    """DeviceHistory backed by a temp directory."""
    import ventocontrol.history as _h
    original = _h._HISTORY_FILE
    _h._HISTORY_FILE = tmp_path / "history.json"
    yield DeviceHistory()
    _h._HISTORY_FILE = original


@pytest.fixture
def window(qapp, tmp_history):
    win = MainWindow(history=tmp_history)
    yield win
    win.close()


def _make_state(ip="192.168.1.10", device_id="TESTDEVICE000001",
                unit_type=5, power=True, speed=2) -> DeviceState:
    return DeviceState(
        ip=ip,
        device_id=device_id,
        unit_type=unit_type,
        power=power,
        speed=speed,
        manual_speed=128,
        operation_mode=0,
        boost_active=False,
        humidity_sensor=0,
        humidity_threshold=60,
    )


# ── Requirement 1: IP address on hover ───────────────────────────────────────

class TestDeviceLabelIpOnHover:

    def test_label_shows_name_only(self, window):
        state = _make_state(ip="10.0.0.1")
        window._apply_state(state)
        assert "10.0.0.1" not in window._device_lbl.text()

    def test_label_tooltip_shows_ip(self, window):
        state = _make_state(ip="10.0.0.1")
        window._apply_state(state)
        assert window._device_lbl.toolTip() == "10.0.0.1"

    def test_label_text_is_fan_name(self, window):
        state = _make_state(ip="10.0.0.1", unit_type=5)
        window._apply_state(state)
        assert window._device_lbl.text() != ""
        assert "·" not in window._device_lbl.text()


# ── Requirement 2: Scenario button ───────────────────────────────────────────

class TestScenarioButton:

    def test_button_label_is_scenario(self, window):
        assert window._save_scenario_btn.text() == "Scenario"

    def test_add_to_scenario_adds_fan(self, window, tmp_path, monkeypatch):
        """_add_to_scenario merges current fan into an existing scenario."""
        import ventocontrol.scenarios as _s
        original = _s._SCENARIOS_FILE
        _s._SCENARIOS_FILE = tmp_path / "scenarios.json"

        state = _make_state(device_id="FANDEVICE000001")
        window._apply_state(state)
        window._current_device_id = "FANDEVICE000001"
        window._last_state = state

        # Create an existing scenario with a different fan
        other_fan = FanSettings(
            device_id="OTHERFAN0000001",
            settings=ScenarioSettings(power=True, speed=1),
        )
        existing = ScenarioEntry(name="Night Mode", fans=[other_fan])
        window._scenarios.save_scenario(existing)

        window._add_to_scenario("Night Mode")

        updated = next(
            s for s in window._scenarios.get_scenarios() if s.name == "Night Mode"
        )
        device_ids = [f.device_id for f in updated.fans]
        assert "FANDEVICE000001" in device_ids
        assert "OTHERFAN0000001" in device_ids
        _s._SCENARIOS_FILE = original

    def test_add_to_scenario_updates_existing_fan(self, window, tmp_path):
        """_add_to_scenario replaces an existing fan entry rather than duplicating it."""
        import ventocontrol.scenarios as _s
        original = _s._SCENARIOS_FILE
        _s._SCENARIOS_FILE = tmp_path / "scenarios2.json"

        state = _make_state(device_id="FANDEVICE000001", speed=1)
        window._apply_state(state)
        window._current_device_id = "FANDEVICE000001"
        window._last_state = state

        existing = ScenarioEntry(name="Day Mode", fans=[
            FanSettings(device_id="FANDEVICE000001",
                        settings=ScenarioSettings(power=True, speed=3)),
        ])
        window._scenarios.save_scenario(existing)

        window._add_to_scenario("Day Mode")

        updated = next(s for s in window._scenarios.get_scenarios() if s.name == "Day Mode")
        assert len([f for f in updated.fans if f.device_id == "FANDEVICE000001"]) == 1
        _s._SCENARIOS_FILE = original

    def test_add_to_nonexistent_scenario_is_noop(self, window):
        """_add_to_scenario does nothing if the scenario name does not exist."""
        state = _make_state()
        window._apply_state(state)
        window._current_device_id = state.device_id
        window._last_state = state
        before = len(window._scenarios.get_scenarios())
        window._add_to_scenario("Nonexistent Scenario")
        assert len(window._scenarios.get_scenarios()) == before
