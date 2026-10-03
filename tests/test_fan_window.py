"""Tests for FanWindow UI behaviour — requires an offscreen Qt display."""

from __future__ import annotations

import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from blauberg_vento.models import DeviceState
from PySide6.QtWidgets import QApplication, QDialog
from ventocontrol.history import DeviceHistory
from ventocontrol.scenarios import (
    FanSettings,
    ScenarioEntry,
    ScenarioSettings,
    ScenarioStore,
)
from ventocontrol.ui.fan_details_window import FanDetailsWindow
from ventocontrol.ui.fan_window import FanWindow

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
    win = FanWindow(history=tmp_history)
    yield win
    win.close()


def _make_state(ip="192.168.1.10", device_id="TESTDEVICE000001", unit_type=5, power=True, speed=2) -> DeviceState:
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


# ── Requirement 2: Scenario operations ───────────────────────────────────────


class TestScenarioButton:
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

        updated = next(s for s in window._scenarios.get_scenarios() if s.name == "Night Mode")
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

        existing = ScenarioEntry(
            name="Day Mode",
            fans=[
                FanSettings(device_id="FANDEVICE000001", settings=ScenarioSettings(power=True, speed=3)),
            ],
        )
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


# ── Details button ────────────────────────────────────────────────────────────


class TestDetailsButton:
    def test_details_button_disabled_before_connect(self, window):
        """Details button is disabled until a device connects."""
        assert not window._details_btn.isEnabled()

    def test_details_button_enabled_after_connect(self, window):
        """Details button becomes enabled once connected."""
        state = _make_state()
        window._on_connected(state)
        assert window._details_btn.isEnabled()


# ── FanDetailsWindow ──────────────────────────────────────────────────────────


@pytest.fixture
def details_dialog(qapp, tmp_path):
    import ventocontrol.scenarios as _s

    original = _s._SCENARIOS_FILE
    _s._SCENARIOS_FILE = tmp_path / "scenarios.json"
    dlg = FanDetailsWindow(title="Test Fan", scenarios=ScenarioStore())
    yield dlg
    dlg.close()
    _s._SCENARIOS_FILE = original


class TestFanDetailsWindow:
    def test_schedule_buttons_present(self, details_dialog):
        """Schedule controls exist in the details dialog."""
        assert hasattr(details_dialog, "_sched_en_btn")
        assert hasattr(details_dialog, "_sched_edit_btn")
        assert hasattr(details_dialog, "_sync_rtc_btn")

    def test_schedule_enable_emits_signal(self, details_dialog, qapp):
        """Clicking the schedule enable button emits the schedule-enable signal."""
        received = []
        details_dialog.schedule_enable_changed.connect(lambda v: received.append(v))
        details_dialog._sched_en_btn.setChecked(True)
        details_dialog._on_schedule_enable_clicked()
        assert received == [True]

    def test_sync_rtc_emits_signal(self, details_dialog, qapp):
        """Clicking Sync RTC emits the sync_rtc signal."""
        emitted = []
        details_dialog.sync_rtc.connect(lambda: emitted.append(True))
        details_dialog._sync_rtc_btn.click()
        assert emitted == [True]

    def test_refresh_reflects_schedule_enabled(self, details_dialog):
        state = DeviceState(
            ip="192.168.1.1",
            device_id="TESTDEVICE000001",
            weekly_schedule_enabled=True,
        )
        details_dialog.refresh(state)
        assert details_dialog._sched_en_btn.isChecked()
        assert details_dialog._sched_en_btn.text() == "ON"

    def test_refresh_reflects_schedule_disabled(self, details_dialog):
        state = DeviceState(
            ip="192.168.1.1",
            device_id="TESTDEVICE000001",
            weekly_schedule_enabled=False,
        )
        details_dialog.refresh(state)
        assert not details_dialog._sched_en_btn.isChecked()
        assert details_dialog._sched_en_btn.text() == "OFF"

    def test_refresh_updates_boost(self, details_dialog):
        state = DeviceState(
            ip="192.168.1.1",
            device_id="TESTDEVICE000001",
            boost_active=True,
        )
        details_dialog.refresh(state)
        assert details_dialog._boost_btn.isChecked()
        assert details_dialog._boost_btn.text() == "ON"

    def test_boost_emits_signal(self, details_dialog, qapp):
        received = []
        details_dialog.boost_changed.connect(lambda v: received.append(v))
        details_dialog._boost_btn.setChecked(True)
        details_dialog._on_boost_clicked()
        assert received == [True]


# ── Requirement: power button health colours ─────────────────────────────────


class TestPowerButtonHealth:
    def test_button_green_after_connect(self, window):
        state = _make_state()
        window._apply_state(state)
        assert window._power_btn.is_available() is True
        assert window._power_btn.is_warning() is False

    def test_button_yellow_on_alarm(self, window):
        state = _make_state()
        state.alarm_status = 1
        window._apply_state(state)
        assert window._power_btn.is_warning() is True

    def test_button_yellow_on_expired_filter(self, window):
        from blauberg_vento.models import FilterCountdown

        state = _make_state()
        state.filter_countdown = FilterCountdown(0, 0, 0)
        window._apply_state(state)
        assert window._power_btn.is_warning() is True

    def test_button_grey_when_unconnected(self, window):
        state = _make_state()
        window._apply_state(state)
        window._go_to_unconnected()
        assert window._power_btn.is_available() is False
        assert window._power_btn.is_warning() is False

    def test_no_airflow_icon_in_fan_window(self, window):
        assert not hasattr(window, "_airflow_icon")


# ── Requirement: no status box, no Switch button ─────────────────────────────


class TestRemovedRedundancy:
    def test_no_status_group_box(self, window):
        assert not hasattr(window, "_conn_led")
        assert not hasattr(window, "_alarm_led")

    def test_no_switch_button_or_menu_action(self, window):
        assert not hasattr(window, "_switch_btn")
        assert not hasattr(window, "_switch_device")
        menu_titles = [a.text() for a in window.menuBar().actions()]
        assert "Device" in menu_titles

    def test_details_button_under_fan_name(self, window):
        # The header is the first sub-layout of the central widget's layout;
        # the power button comes first, then a column stacking the name over
        # the Details button.
        central = window.centralWidget()
        assert central is not None
        root = central.layout()
        assert root is not None
        header = root.itemAt(0).layout()
        assert header is not None
        assert header.itemAt(0).widget() is window._power_btn
        name_col = header.itemAt(1).layout()
        assert name_col is not None
        widgets = [name_col.itemAt(i).widget() for i in range(name_col.count())]
        widgets = [w for w in widgets if w is not None]
        assert window._device_lbl in widgets
        assert window._details_btn in widgets
        assert widgets.index(window._device_lbl) < widgets.index(window._details_btn)


# ── Requirement: cancelling the initial connect dialog closes the window ─────


class TestInitialConnectDialog:
    def test_cancel_closes_window_without_connecting(self, window, tmp_history, monkeypatch):
        """Cancelling "Connect New Fan…" must not silently open the last fan."""
        tmp_history.record(device_id="LASTFAN0000001", ip="10.0.0.1", unit_type_name="Vento Expert", password="1111")

        class FakeConnectDialog:
            DialogCode = QDialog.DialogCode

            def __init__(self, parent=None, history=None):
                pass

            def exec(self):
                return QDialog.DialogCode.Rejected.value

        monkeypatch.setattr("ventocontrol.ui.fan_window.ConnectDialog", FakeConnectDialog)

        emitted: list[tuple] = []
        window._sig_connect.connect(emitted.append)
        window._open_initial_connect_dialog()

        assert emitted == []  # no connection to any fan was started
        assert window._current_device_id == ""
        assert window.isVisible() is False  # the blank window closed itself


# ── Requirement: show why the fan needs attention in the details window ────────


class TestAttentionReason:
    def test_alarm_reason_shown_above_humidity(self, details_dialog):
        state = DeviceState(ip="192.168.1.1", device_id="TESTDEVICE000001", alarm_status=1)
        details_dialog.refresh(state)
        assert details_dialog._attention_lbl.text() == "Alarm"
        assert details_dialog._attention_lbl.isHidden() is False

    def test_filter_reason_shown(self, details_dialog):
        from blauberg_vento.models import FilterCountdown

        state = DeviceState(ip="192.168.1.1", device_id="TESTDEVICE000001", filter_countdown=FilterCountdown(0, 0, 0))
        details_dialog.refresh(state)
        assert details_dialog._attention_lbl.text() == "Filter timer expired"
        assert details_dialog._attention_lbl.isHidden() is False

    def test_both_reasons_joined(self, details_dialog):
        from blauberg_vento.models import FilterCountdown

        state = DeviceState(
            ip="192.168.1.1",
            device_id="TESTDEVICE000001",
            alarm_status=1,
            filter_countdown=FilterCountdown(0, 0, 0),
        )
        details_dialog.refresh(state)
        assert details_dialog._attention_lbl.text() == "Alarm · Filter timer expired"

    def test_healthy_fan_hides_reason(self, details_dialog):
        from blauberg_vento.models import FilterCountdown

        state = DeviceState(
            ip="192.168.1.1", device_id="TESTDEVICE000001", filter_countdown=FilterCountdown(90, 12, 30)
        )
        details_dialog.refresh(state)
        assert details_dialog._attention_lbl.text() == ""
        assert details_dialog._attention_lbl.isHidden() is True

    def test_reason_clears_after_alarm_resolves(self, details_dialog):
        state = DeviceState(ip="192.168.1.1", device_id="TESTDEVICE000001", alarm_status=1)
        details_dialog.refresh(state)
        assert details_dialog._attention_lbl.isHidden() is False
        state.alarm_status = 0
        details_dialog.refresh(state)
        assert details_dialog._attention_lbl.isHidden() is True
