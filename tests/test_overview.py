"""Tests for the Overview launch window — cards, icon, worker, and fan windows."""

from __future__ import annotations

import os
import sys
from typing import cast

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from blauberg_vento.models import DeviceState, FilterCountdown, RtcCalendar, RtcTime
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QLabel, QWidget
from ventocontrol.controllers import overview_worker as ow
from ventocontrol.controllers.overview_worker import FanSpec, OverviewWorker
from ventocontrol.history import DeviceHistory, HistoryEntry
from ventocontrol.ui.overview_window import FanCard, OverviewWindow, format_date, format_humidity, format_time
from ventocontrol.widgets.airflow_fan_icon import AirflowFanIcon, needs_attention

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


def _make_state(
    device_id="FANDEVICE000001",
    power=True,
    operation_mode=1,
    humidity=57,
    rtc=True,
    filt=True,
    alarm=None,
    filter_replace=False,
) -> DeviceState:
    return DeviceState(
        ip="10.0.0.5",
        device_id=device_id,
        unit_type=5,
        power=power,
        speed=2,
        manual_speed=128,
        operation_mode=operation_mode,
        current_humidity=humidity,
        rtc_time=RtcTime(14, 30, 5) if rtc else None,
        rtc_calendar=RtcCalendar(2026, 10, 3, 6) if rtc else None,
        filter_countdown=(
            filt if isinstance(filt, FilterCountdown) else (FilterCountdown(90, 12, 30) if filt else None)
        ),
        alarm_status=alarm,
        filter_needs_replacement=filter_replace,
    )


class _FakeMouse:
    """Just enough of a QMouseEvent for FanCard.mousePressEvent."""

    def __init__(self, button):
        self._button = button

    def button(self):
        return self._button


def _entry(device_id: str, name: str = "", unit: str = "Vento Expert") -> HistoryEntry:
    return HistoryEntry(
        device_id=device_id,
        ip="10.0.0.9",
        unit_type_name=unit,
        password="1111",
        name=name,
    )


def _history_with(*entries: HistoryEntry) -> DeviceHistory:
    history = DeviceHistory.__new__(DeviceHistory)
    history._entries = list(entries)
    history._observers = []
    return history


# ── Formatting helpers ───────────────────────────────────────────────────────


class TestFormatting:
    def test_time(self):
        assert format_time(_make_state()) == "14:30:05"
        assert format_time(_make_state(rtc=False)) == "—"

    def test_date(self):
        assert format_date(_make_state()) == "2026-10-03 (Sat)"
        assert format_date(_make_state(rtc=False)) == "—"

    def test_humidity(self):
        assert format_humidity(_make_state(humidity=57)) == "57% RH"
        assert format_humidity(_make_state(humidity=None)) == "—"

    def test_needs_attention_on_alarm(self):
        assert needs_attention(_make_state(alarm=1)) is True

    def test_needs_attention_on_expired_filter(self):
        assert needs_attention(_make_state(filt=FilterCountdown(0, 0, 0))) is True

    def test_needs_attention_on_replacement_flag(self):
        assert needs_attention(_make_state(filter_replace=True)) is True

    def test_needs_attention_healthy_fan(self):
        assert needs_attention(_make_state()) is False


# ── AirflowFanIcon ────────────────────────────────────────────────────────────


class TestAirflowFanIcon:
    def test_starts_unavailable_with_unknown_mode(self, qapp):
        icon = AirflowFanIcon()
        assert icon.is_available() is False
        assert icon.mode() is None

    def test_availability_warning_and_mode_track_setters(self, qapp):
        icon = AirflowFanIcon()
        icon.set_available(True)
        icon.set_warning(True)
        icon.set_mode(2)
        assert icon.is_available() is True
        assert icon.is_warning() is True
        assert icon.mode() == 2
        icon.set_mode(None)
        assert icon.mode() is None

    def test_paints_without_error_for_every_state(self, qapp):
        # grab() forces a synchronous paint — deliberately no processEvents(),
        # which would deliver stale modal-dialog timers from earlier tests.
        icon = AirflowFanIcon()
        for available in (False, True):
            for warning in (False, True):
                icon.set_available(available)
                icon.set_warning(warning)
                for mode in (None, 0, 1, 2):
                    icon.set_mode(mode)
                    assert not icon.grab().isNull()


# ── FanCard ───────────────────────────────────────────────────────────────────


class TestFanCard:
    def test_card_starts_offline_with_placeholder_labels(self, qapp):
        card = FanCard(title="Kitchen", device_id="DEV1")
        assert card.is_online() is False
        assert card.time_text == "—"
        assert card.date_text == "—"
        assert card.humidity == "—"
        assert card.title == "Kitchen"
        assert card.device_id == "DEV1"

    def test_refresh_updates_labels_and_icon(self, qapp):
        card = FanCard(title="Kitchen", device_id="DEV1")
        card.refresh(_make_state(device_id="DEV1", power=True, operation_mode=1, humidity=62))
        assert card.is_online() is True
        assert card.time_text == "14:30:05"
        assert card.date_text == "2026-10-03 (Sat)"
        assert card.humidity == "62% RH"
        assert card._icon.is_available() is True
        assert card._icon.mode() == 1

    def test_alarm_marks_icon_yellow(self, qapp):
        card = FanCard(title="Kitchen", device_id="DEV1")
        card.refresh(_make_state(alarm=1))
        assert card._icon.is_warning() is True

    def test_expired_filter_marks_icon_yellow(self, qapp):
        card = FanCard(title="Kitchen", device_id="DEV1")
        card.refresh(_make_state(filt=FilterCountdown(0, 0, 0)))
        assert card._icon.is_warning() is True

    def test_healthy_fan_icon_not_yellow(self, qapp):
        card = FanCard(title="Kitchen", device_id="DEV1")
        card.refresh(_make_state())
        assert card._icon.is_warning() is False

    def test_power_state_does_not_change_icon_colour(self, qapp):
        # The icon colour encodes availability, not the power state — the
        # arrows carry the mode, so an off-but-reachable fan stays green.
        card = FanCard(title="Kitchen", device_id="DEV1")
        card.refresh(_make_state(power=False))
        assert card._icon.is_available() is True

    def test_mark_offline_greys_icon_and_clears_labels(self, qapp):
        card = FanCard(title="Kitchen", device_id="DEV1")
        card.refresh(_make_state())
        card.mark_offline()
        assert card.is_online() is False
        assert card._icon.is_available() is False
        assert card._icon.is_warning() is False
        assert card._icon.mode() is None
        assert card.time_text == "—"
        assert card.date_text == "—"
        assert card.humidity == "—"

    def test_long_title_is_elided_but_kept_in_full(self, qapp):
        long_name = "Very Long Fan Name That Cannot Fit On A Narrow Tile"
        card = FanCard(title=long_name, device_id="DEV1")
        card.resize(160, 200)
        layout = card.layout()
        assert layout is not None
        layout.activate()  # give the title label its real narrow width
        # Hidden widgets receive no resize events, so drive the same code path
        # that the resize event triggers in a shown window.
        card._title_lbl._apply_elision()
        assert card.title == long_name
        assert card._title_lbl.text().endswith("…")
        assert card._title_lbl.text() != long_name

    def test_left_click_emits_activated(self, qapp):
        card = FanCard(title="Kitchen", device_id="DEV1")
        clicks: list[str] = []
        card.activated.connect(clicks.append)
        card.mousePressEvent(_FakeMouse(Qt.MouseButton.LeftButton))
        assert clicks == ["DEV1"]

    def test_right_click_does_not_open_fan_window(self, qapp):
        """Regression: a right-click must open the menu, not the fan window."""
        card = FanCard(title="Kitchen", device_id="DEV1")
        clicks: list[str] = []
        card.activated.connect(clicks.append)
        card.mousePressEvent(_FakeMouse(Qt.MouseButton.RightButton))
        assert clicks == []

    def test_set_title(self, qapp):
        card = FanCard(title="Old", device_id="DEV1")
        card.set_title("Kitchen")
        assert card.title == "Kitchen"


# ── OverviewWindow ────────────────────────────────────────────────────────────


class TestOverviewWindowEmptyState:
    def test_empty_history_shows_hint_and_disables_actions(self, qapp):
        win = OverviewWindow(history=None, polling_enabled=False)
        assert win._cards == {}
        labels = [w.text() for w in win.findChildren(QLabel)]
        assert any("No fans yet" in text for text in labels)
        assert win._refresh_btn.isEnabled() is False
        assert win._sync_btn.isEnabled() is False
        assert win._connect_btn.isEnabled() is True
        win.close()

    def test_cards_enable_refresh_and_sync(self, qapp):
        history = _history_with(_entry("DEV1"))
        win = OverviewWindow(history=history, polling_enabled=False)
        assert win._refresh_btn.isEnabled() is True
        assert win._sync_btn.isEnabled() is True
        win.close()


class TestOverviewWindowCards:
    def test_one_card_per_history_entry(self, qapp):
        history = _history_with(_entry("DEV1", name="Kitchen"), _entry("DEV2"), _entry("DEV3"))
        win = OverviewWindow(history=history, polling_enabled=False)
        assert set(win._cards) == {"DEV1", "DEV2", "DEV3"}
        assert win._cards["DEV1"].title == "Kitchen"
        assert win._cards["DEV2"].title == "Vento Expert"
        win.close()

    def test_fan_state_updates_matching_card(self, qapp):
        history = _history_with(_entry("DEV1"), _entry("DEV2"))
        win = OverviewWindow(history=history, polling_enabled=False)
        win._on_fan_state(_make_state(device_id="DEV2", operation_mode=2))
        assert win._cards["DEV2"]._icon.mode() == 2
        assert win._cards["DEV1"].is_online() is False
        win.close()

    def test_cards_lay_out_two_per_line(self, qapp):
        history = _history_with(_entry("DEV1"), _entry("DEV2"), _entry("DEV3"))
        win = OverviewWindow(history=history, polling_enabled=False)
        grid = win._cards_grid
        # PySide6 stubs type getItemPosition as plain object — cast to its real tuple
        positions = [
            cast(tuple[int, ...], grid.getItemPosition(grid.indexOf(win._cards[f"DEV{i}"]))) for i in (1, 2, 3)
        ]
        assert [(p[0], p[1]) for p in positions] == [(0, 0), (0, 1), (1, 0)]
        win.close()

    def test_unreachable_fan_marked_offline(self, qapp):
        history = _history_with(_entry("DEV1"))
        win = OverviewWindow(history=history, polling_enabled=False)
        win._on_fan_state(_make_state(device_id="DEV1"))
        win._on_fan_unreachable("DEV1")
        assert win._cards["DEV1"].is_online() is False
        win.close()

    def test_unknown_device_id_is_ignored(self, qapp):
        history = _history_with(_entry("DEV1"))
        win = OverviewWindow(history=history, polling_enabled=False)
        win._on_fan_state(_make_state(device_id="STRANGER"))
        win._on_fan_unreachable("STRANGER")
        assert win._cards["DEV1"].is_online() is False
        win.close()


class TestOverviewWindowHistorySync:
    def test_new_history_entry_gains_a_card(self, qapp, tmp_history):
        win = OverviewWindow(history=tmp_history, polling_enabled=False)
        assert win._cards == {}
        tmp_history.record(device_id="NEWDEV", ip="10.0.0.7", unit_type_name="Vento Expert", password="1111")
        assert set(win._cards) == {"NEWDEV"}
        win.close()

    def test_rename_updates_card_title(self, qapp, tmp_history):
        tmp_history.record(device_id="DEV1", ip="10.0.0.7", unit_type_name="Vento Expert", password="1111")
        win = OverviewWindow(history=tmp_history, polling_enabled=False)
        assert win._cards["DEV1"].title == "Vento Expert"
        tmp_history.rename("DEV1", "Kitchen")
        assert win._cards["DEV1"].title == "Kitchen"
        win.close()


class TestOverviewWindowSync:
    def test_sync_click_shows_progress_and_finish_reenables(self, qapp):
        history = _history_with(_entry("DEV1"), _entry("DEV2"))
        win = OverviewWindow(history=history, polling_enabled=False)
        win._on_sync_clicked()
        assert win._sync_lbl.text() == "Syncing clocks…"
        assert win._sync_btn.isEnabled() is False
        win._on_rtc_synced("DEV1")
        assert "Clocks synced: 1" in win._sync_lbl.text()
        win._on_rtc_sync_finished()
        assert win._sync_btn.isEnabled() is True
        assert "1 offline" in win._sync_lbl.text()
        win.close()

    def test_sync_finished_all_online(self, qapp):
        history = _history_with(_entry("DEV1"))
        win = OverviewWindow(history=history, polling_enabled=False)
        win._on_sync_clicked()
        win._on_rtc_synced("DEV1")
        win._on_rtc_sync_finished()
        assert "offline" not in win._sync_lbl.text()
        win.close()


class TestFanWindowOpening:
    @pytest.fixture
    def fake_fan_window(self, monkeypatch):
        created: list[FakeFanWindow] = []

        class FakeFanWindow:
            def __init__(self, host="", device_id="", password="", history=None, registry=None):
                self.host = host
                self.device_id = device_id
                self.password = password
                self._visible = False
                self.raised = False
                created.append(self)

            def isVisible(self):
                return self._visible

            def raise_(self):
                self.raised = True

            def activateWindow(self):
                pass

            def show(self):
                self._visible = True

            def close(self):
                self._visible = False

        monkeypatch.setattr("ventocontrol.ui.fan_window.FanWindow", FakeFanWindow)
        return created

    def test_card_click_opens_fan_window_with_entry_params(self, qapp, fake_fan_window):
        history = _history_with(_entry("DEV1", name="Kitchen"))
        win = OverviewWindow(history=history, polling_enabled=False)
        win._open_fan_window("DEV1")
        assert len(fake_fan_window) == 1
        fan_win = fake_fan_window[0]
        assert (fan_win.host, fan_win.device_id, fan_win.password) == ("10.0.0.9", "DEV1", "1111")
        assert fan_win.isVisible()
        win.close()

    def test_second_click_raises_existing_window(self, qapp, fake_fan_window):
        history = _history_with(_entry("DEV1"))
        win = OverviewWindow(history=history, polling_enabled=False)
        win._open_fan_window("DEV1")
        win._open_fan_window("DEV1")
        assert len(fake_fan_window) == 1
        assert fake_fan_window[0].raised is True
        win.close()

    def test_unknown_device_opens_nothing(self, qapp, fake_fan_window):
        history = _history_with(_entry("DEV1"))
        win = OverviewWindow(history=history, polling_enabled=False)
        win._open_fan_window("GHOST")
        assert fake_fan_window == []
        win.close()

    def test_connect_new_opens_blank_window(self, qapp, fake_fan_window):
        history = _history_with()
        win = OverviewWindow(history=history, polling_enabled=False)
        win._on_connect_new_clicked()
        assert len(fake_fan_window) == 1
        assert fake_fan_window[0].host == ""
        win.close()


# ── OverviewWorker ────────────────────────────────────────────────────────────


class TestOverviewWorker:
    def test_poll_all_emits_state_per_fan(self, monkeypatch):
        class FakeClient:
            def __init__(self, host, device_id, password, timeout):
                self.device_id = device_id

            def get_state(self):
                return _make_state(device_id=self.device_id)

        monkeypatch.setattr(ow, "VentoClient", FakeClient)
        worker = OverviewWorker([FanSpec("DEV1", "10.0.0.1", "1111"), FanSpec("DEV2", "10.0.0.2", "1111")])

        states: list[DeviceState] = []
        worker.fan_state_updated.connect(states.append)
        worker.do_poll_all()

        assert [s.device_id for s in states] == ["DEV1", "DEV2"]

    def test_unreachable_fan_reported(self, monkeypatch):
        class FakeClient:
            def __init__(self, host, device_id, password, timeout):
                if device_id == "DEAD":
                    raise OSError("host down")
                self.device_id = device_id

            def get_state(self):
                return _make_state(device_id=self.device_id)

        monkeypatch.setattr(ow, "VentoClient", FakeClient)
        worker = OverviewWorker([FanSpec("DEAD", "10.0.0.1", "1111"), FanSpec("ALIVE", "10.0.0.2", "1111")])

        states: list[DeviceState] = []
        unreachable: list[str] = []
        worker.fan_state_updated.connect(states.append)
        worker.fan_unreachable.connect(unreachable.append)
        worker.do_poll_all()

        assert unreachable == ["DEAD"]
        assert [s.device_id for s in states] == ["ALIVE"]

    def test_sync_all_rtc_syncs_each_fan_then_repolls(self, monkeypatch):
        synced_with: list[str] = []
        polled: list[str] = []

        class FakeClient:
            def __init__(self, host, device_id, password, timeout):
                self.device_id = device_id

            def sync_rtc(self):
                synced_with.append(self.device_id)

            def get_state(self):
                polled.append(self.device_id)
                return _make_state(device_id=self.device_id)

        monkeypatch.setattr(ow, "VentoClient", FakeClient)
        worker = OverviewWorker([FanSpec("DEV1", "10.0.0.1", "1111"), FanSpec("DEV2", "10.0.0.2", "1111")])

        synced: list[str] = []
        finished: list[bool] = []
        worker.rtc_synced.connect(synced.append)
        worker.rtc_sync_finished.connect(lambda: finished.append(True))
        worker.do_sync_all_rtc()

        assert synced_with == ["DEV1", "DEV2"]
        assert synced == ["DEV1", "DEV2"]
        assert finished == [True]
        assert polled == ["DEV1", "DEV2"]  # the automatic re-poll after syncing

    def test_sync_failure_reports_unreachable_and_finishes(self, monkeypatch):
        class FakeClient:
            def __init__(self, host, device_id, password, timeout):
                if device_id == "DEAD":
                    raise OSError("host down")

            def sync_rtc(self):
                pass

            def get_state(self):
                return _make_state(device_id="ALIVE")

        monkeypatch.setattr(ow, "VentoClient", FakeClient)
        worker = OverviewWorker([FanSpec("DEAD", "10.0.0.1", "1111"), FanSpec("ALIVE", "10.0.0.2", "1111")])

        unreachable: list[str] = []
        finished: list[bool] = []
        worker.fan_unreachable.connect(unreachable.append)
        worker.rtc_sync_finished.connect(lambda: finished.append(True))
        worker.do_sync_all_rtc()

        assert unreachable == ["DEAD", "DEAD"]  # once during sync, once during the re-poll
        assert finished == [True]


# ── Tile right-click actions ──────────────────────────────────────────────────


class TestFanCardContextMenu:
    def test_menu_offers_all_six_actions(self, qapp):
        card = FanCard(title="Kitchen", device_id="DEV1")
        menu = card._build_action_menu()
        labels = [a.text() for a in menu.actions()]
        assert labels == ["Open…", "Details…", "Rename…", "Scenario…", "Sync Clock to PC", "Remove from List"]

    def test_triggering_menu_action_emits_key(self, qapp):
        card = FanCard(title="Kitchen", device_id="DEV1")
        requested: list[tuple[str, str]] = []
        card.action_requested.connect(lambda device_id, action: requested.append((device_id, action)))
        menu = card._build_action_menu()
        menu.actions()[5].trigger()  # Remove from List
        assert requested == [("DEV1", "remove")]


class TestTileActions:
    @pytest.fixture
    def overview(self, qapp, tmp_history):
        tmp_history.record(device_id="DEV1", ip="10.0.0.9", unit_type_name="Vento Expert", password="1111")
        tmp_history.record(device_id="DEV2", ip="10.0.0.10", unit_type_name="Vento Expert", password="1111")
        win = OverviewWindow(history=tmp_history, polling_enabled=False)
        yield win
        win.close()

    def test_unknown_action_is_ignored(self, overview):
        overview._on_card_action("DEV1", "nonsense")  # must not raise

    def test_details_opens_fan_window_and_its_dialog(self, overview, monkeypatch):
        opened_details: list[str] = []

        class FakeFanWindow:
            def __init__(self, host="", device_id="", password="", history=None, registry=None):
                self.device_id = device_id
                self._visible = False

            def isVisible(self):
                return self._visible

            def show(self):
                self._visible = True

            def close(self):
                self._visible = False

            def _open_fan_details(self):
                opened_details.append(self.device_id)

        monkeypatch.setattr("ventocontrol.ui.fan_window.FanWindow", FakeFanWindow)
        overview._open_fan_details("DEV1")
        assert opened_details == ["DEV1"]

    def test_rename_updates_tile_title(self, overview, monkeypatch):
        class FakeRenameDialog:
            DialogCode = type("D", (), {"Accepted": 1})

            def __init__(self, current_name="", parent=None):
                self.current_name = current_name

            def exec(self):
                return 1  # accepted

            def name(self):
                return "Kitchen"

        monkeypatch.setattr("ventocontrol.ui.overview_window.RenameDialog", FakeRenameDialog)
        overview._rename_fan("DEV1")
        assert overview._cards["DEV1"].title == "Kitchen"

    def test_scenario_dialog_gets_device_id(self, overview, monkeypatch):
        received: list[dict] = []

        class FakeScenarioDialog:
            def __init__(self, store, device_id, registry, history, parent):
                received.append({"device_id": device_id, "store": store})
                self.DialogCode = None

            def exec(self):
                return 0

        monkeypatch.setattr("ventocontrol.ui.overview_window.ManageScenariosDialog", FakeScenarioDialog)
        overview._open_fan_scenarios("DEV2")
        assert received == [{"device_id": "DEV2", "store": overview._scenarios}]

    def test_sync_fan_clock_emits_without_label_text(self, overview):
        """A single-fan sync is silent — the tile clock is the feedback."""
        emitted: list[str] = []
        overview._sig_sync_one.connect(emitted.append)
        overview._worker = object()  # present-but-idle worker: the signal goes nowhere
        overview._sync_fan_clock("DEV1")
        assert emitted == ["DEV1"]
        assert overview._sync_lbl.text() == ""

    def test_single_fan_sync_does_not_write_sync_label(self, overview):
        overview._on_rtc_synced("DEV1")  # no all-fans pass running
        assert overview._sync_lbl.text() == ""
        assert overview._synced_count == 0

    def test_sync_fan_clock_without_worker_is_noop(self, overview):
        overview._sync_fan_clock("DEV1")  # worker is None with polling disabled
        assert overview._sync_lbl.text() == ""

    def test_remove_fan_drops_tile(self, overview):
        assert set(overview._cards) == {"DEV1", "DEV2"}
        overview._remove_fan("DEV1")
        assert set(overview._cards) == {"DEV2"}

    def test_card_action_signal_reaches_handler(self, overview, monkeypatch):
        calls: list[tuple[str, str]] = []
        monkeypatch.setattr(overview, "_on_card_action", lambda device_id, action: calls.append((device_id, action)))
        card = overview._cards["DEV1"]
        card.action_requested.emit("DEV1", "sync_clock")
        assert calls == [("DEV1", "sync_clock")]


class TestOverviewWorkerSingleSync:
    def test_sync_rtc_syncs_only_target_fan(self, monkeypatch):
        synced_with: list[str] = []
        polled: list[str] = []

        class FakeClient:
            def __init__(self, host, device_id, password, timeout):
                self.device_id = device_id

            def sync_rtc(self):
                synced_with.append(self.device_id)

            def get_state(self):
                polled.append(self.device_id)
                return _make_state(device_id=self.device_id)

        monkeypatch.setattr(ow, "VentoClient", FakeClient)
        worker = OverviewWorker([FanSpec("DEV1", "10.0.0.1", "1111"), FanSpec("DEV2", "10.0.0.2", "1111")])

        synced: list[str] = []
        worker.rtc_synced.connect(synced.append)
        worker.do_sync_rtc("DEV2")

        assert synced_with == ["DEV2"]
        assert synced == ["DEV2"]
        assert polled == ["DEV2"]  # only the target fan is re-polled

    def test_sync_rtc_unknown_fan_is_noop(self, monkeypatch):
        class FakeClient:
            def __init__(self, host, device_id, password, timeout):
                raise AssertionError("no client should be created for an unknown fan")

        monkeypatch.setattr(ow, "VentoClient", FakeClient)
        worker = OverviewWorker([FanSpec("DEV1", "10.0.0.1", "1111")])
        worker.do_sync_rtc("GHOST")  # must not raise


# ── Closing the Overview closes every window it opened ───────────────────────


class TestCloseClosesAllWindows:
    def test_closing_overview_closes_fan_and_connect_windows(self, qapp, tmp_history):
        class RecordingWindow(QWidget):
            def __init__(self):
                super().__init__()
                self.closed = False

            def close(self) -> bool:
                self.closed = True
                return True

        tmp_history.record(device_id="DEV1", ip="10.0.0.9", unit_type_name="Vento Expert", password="1111")
        win = OverviewWindow(history=tmp_history, polling_enabled=False)

        fan_win = RecordingWindow()
        connect_win = RecordingWindow()
        win._fan_windows["DEV1"] = fan_win
        win._connect_windows.append(connect_win)

        win.close()

        assert fan_win.closed is True
        assert connect_win.closed is True
        assert win._fan_windows == {}
        assert win._connect_windows == []
