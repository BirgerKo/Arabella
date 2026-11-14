#!/bin/sh
# Launcher for the VentoControl Flatpak. The app and its Python deps live
# under /app; the KDE runtime's python3 does not search /app automatically.
export PYTHONPATH="/app/lib/python3.12/site-packages${PYTHONPATH:+:$PYTHONPATH}"
exec /usr/bin/python3 -m ventocontrol.main "$@"
