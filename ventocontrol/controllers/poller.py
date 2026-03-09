"""Poller — QTimer that fires do_poll() on the DeviceWorker at a fixed interval."""
from __future__ import annotations

from PySide6.QtCore import QObject, QTimer, Slot


class Poller(QObject):
    """Fires worker.do_poll() every `interval_ms` milliseconds."""

    DEFAULT_INTERVAL_MS = 5_000   # 5 seconds

    def __init__(self, worker, interval_ms: int = DEFAULT_INTERVAL_MS, parent=None):
        super().__init__(parent)
        self._worker = worker
        self._timer = QTimer(self)
        self._timer.setInterval(interval_ms)
        self._timer.timeout.connect(self._worker.do_poll)

    def start(self):
        self._timer.start()

    def stop(self):
        self._timer.stop()

    @property
    def is_running(self) -> bool:
        return self._timer.isActive()

    def set_interval(self, ms: int):
        self._timer.setInterval(ms)
