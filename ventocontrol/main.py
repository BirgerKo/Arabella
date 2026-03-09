"""VentoControl entry point."""
from __future__ import annotations

import sys

from ventocontrol.app import VentoApp
from ventocontrol.history import DeviceHistory
from ventocontrol.registry import WindowRegistry
from ventocontrol.ui.connect_dialog import ConnectDialog
from ventocontrol.ui.main_window import MainWindow


def main():
    app = VentoApp(sys.argv)

    history  = DeviceHistory()
    registry = WindowRegistry()
    last     = history.last_used

    if last:
        # Auto-connect to the most-recently-used device — skip the dialog
        host, device_id, password = last.ip, last.device_id, last.password
    else:
        # No history yet — show the connection dialog
        dlg = ConnectDialog(history=history)
        if dlg.exec() != ConnectDialog.DialogCode.Accepted:
            sys.exit(0)
        host, device_id, password = dlg.connection_params()
        if not host or not device_id:
            sys.exit(0)

    win = MainWindow(
        host=host,
        device_id=device_id,
        password=password,
        history=history,
        registry=registry,
    )
    win.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
