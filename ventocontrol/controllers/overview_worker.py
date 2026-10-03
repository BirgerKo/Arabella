"""OverviewWorker — polls and syncs every known fan in one background thread."""

from __future__ import annotations

from dataclasses import dataclass

from blauberg_vento import VentoClient
from blauberg_vento.exceptions import VentoError
from PySide6.QtCore import QObject, Signal, Slot

_TIMEOUT_SECONDS = 2.0


@dataclass(frozen=True)
class FanSpec:
    """Connection parameters for one fan shown in the Overview."""

    device_id: str
    host: str
    password: str


class OverviewWorker(QObject):
    """Polls all known fans and reports each one's state (or failure)."""

    fan_state_updated = Signal(object)  # DeviceState of one reachable fan
    fan_unreachable = Signal(str)  # device_id of a fan that did not answer
    rtc_synced = Signal(str)  # device_id of a fan whose RTC was set from PC time
    rtc_sync_finished = Signal()  # the whole sync pass completed

    def __init__(self, fans: list[FanSpec], parent=None):
        super().__init__(parent)
        self._fans = fans

    @Slot()
    def do_poll_all(self):
        for fan in self._fans:
            self._poll_one(fan)

    @Slot()
    def do_sync_all_rtc(self):
        """Set every fan's clock from the PC system time, then re-poll."""
        for fan in self._fans:
            self._sync_rtc_one(fan)
        self.rtc_sync_finished.emit()
        self.do_poll_all()

    @Slot(str)
    def do_sync_rtc(self, device_id: str):
        """Set one fan's clock from the PC system time, then re-poll it."""
        fan = next((f for f in self._fans if f.device_id == device_id), None)
        if fan is None:
            return
        self._sync_rtc_one(fan)
        self._poll_one(fan)

    # ------------------------------------------------------------------
    # Per-fan helpers
    # ------------------------------------------------------------------

    def _poll_one(self, fan: FanSpec):
        try:
            state = self._client_for(fan).get_state()
            self.fan_state_updated.emit(state)
        except VentoError:
            self.fan_unreachable.emit(fan.device_id)
        except Exception:
            # Raw socket/OS errors (e.g. OSError on an unreachable host) also
            # mean the fan is offline — report it the same way.
            self.fan_unreachable.emit(fan.device_id)

    def _sync_rtc_one(self, fan: FanSpec):
        try:
            self._client_for(fan).sync_rtc()
            self.rtc_synced.emit(fan.device_id)
        except VentoError:
            self.fan_unreachable.emit(fan.device_id)
        except Exception:
            self.fan_unreachable.emit(fan.device_id)

    def _client_for(self, fan: FanSpec) -> VentoClient:
        return VentoClient(
            host=fan.host,
            device_id=fan.device_id,
            password=fan.password,
            timeout=_TIMEOUT_SECONDS,
        )
