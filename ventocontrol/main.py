"""VentoControl entry point."""

from __future__ import annotations

import sys

from ventocontrol.app import VentoApp
from ventocontrol.history import DeviceHistory
from ventocontrol.registry import WindowRegistry
from ventocontrol.ui.overview_window import OverviewWindow


def main():
    app = VentoApp(sys.argv)

    history = DeviceHistory()
    registry = WindowRegistry()

    # The Overview window is the opening screen; clicking a fan card
    # opens that fan's control window.
    win = OverviewWindow(history=history, registry=registry)
    win.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
