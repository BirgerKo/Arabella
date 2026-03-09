"""WindowRegistry — tracks all open MainWindow instances for cross-window dispatch."""
from __future__ import annotations


class WindowRegistry:
    """
    Maintains a list of MainWindow instances so multi-fan scenarios
    can target the correct window for each device.
    """

    def __init__(self):
        self._windows = []   # list[MainWindow]

    def register(self, window) -> None:
        """Add a window to the registry (idempotent)."""
        if window not in self._windows:
            self._windows.append(window)

    def unregister(self, window) -> None:
        """Remove a window from the registry."""
        self._windows = [w for w in self._windows if w is not window]

    def get_for_device(self, device_id: str):
        """Return the first visible window connected to device_id, or None."""
        for w in self._windows:
            if w._current_device_id == device_id and w.isVisible():
                return w
        return None

    @property
    def all_connected(self) -> list:
        """All visible windows that have a connected device."""
        return [
            w for w in self._windows
            if w._current_device_id and w.isVisible()
        ]
