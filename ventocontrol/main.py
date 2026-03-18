"""VentoControl entry point."""
from __future__ import annotations

import sys

from ventocontrol.app import VentoApp
from ventocontrol.history import DeviceHistory
from ventocontrol.registry import WindowRegistry
from ventocontrol.ui.main_window import MainWindow


def main():
    app = VentoApp(sys.argv)

    history  = DeviceHistory()
    registry = WindowRegistry()

    entry = history.last_used
    win = MainWindow(
        host=entry.ip       if entry else "",
        device_id=entry.device_id if entry else "",
        password=entry.password   if entry else "",
        history=history,
        registry=registry,
    )
    win.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
