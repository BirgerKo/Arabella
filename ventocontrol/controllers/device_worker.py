"""DeviceWorker — runs VentoClient I/O on a dedicated QThread."""
from __future__ import annotations

from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot

from blauberg_vento import VentoClient
from blauberg_vento.exceptions import VentoError
from blauberg_vento.models import DeviceState, DiscoveredDevice
from blauberg_vento.parameters import Param


class DeviceWorker(QObject):
    """All blocking VentoClient calls happen here (runs in its own QThread)."""

    # Outgoing signals
    discovery_result = pyqtSignal(list)          # list[DiscoveredDevice]
    connected        = pyqtSignal(object)        # DeviceState on first successful poll
    state_updated    = pyqtSignal(object)        # DeviceState
    error            = pyqtSignal(str)           # human-readable error text
    command_done     = pyqtSignal()              # a write command completed OK

    def __init__(self, parent=None):
        super().__init__(parent)
        self._client: VentoClient | None = None

    # ------------------------------------------------------------------
    # Discovery & Connection
    # ------------------------------------------------------------------

    @pyqtSlot()
    def do_discover(self):
        try:
            devices = VentoClient.discover(timeout=2.0)
            self.discovery_result.emit(devices)
        except VentoError as exc:
            self.error.emit(f"Discovery failed: {exc}")
        except Exception as exc:
            self.error.emit(f"Unexpected discovery error: {exc}")

    @pyqtSlot()
    def do_docker_discover(self):
        """Probe loopback alias IPs 127.0.0.11 … 127.0.0.41 directly.

        Each fan container is port-mapped to 127.0.0.1x:4000 via a macOS
        loopback alias (sudo ifconfig lo0 alias 127.0.0.1x).  No DNS
        resolution is needed.  Scanning stops at the first IP that returns
        no response — fans are allocated contiguously starting at .11.
        """
        devices = []
        for last_octet in range(11, 42):        # 127.0.0.11 … 127.0.0.41
            ip = f"127.0.0.{last_octet}"
            try:
                found = VentoClient.discover(broadcast=ip, timeout=0.5)
                if not found:
                    break                       # no fan here — stop scanning
                devices.extend(found)
            except VentoError:
                break
        self.discovery_result.emit(devices)

    @pyqtSlot(str, str, str)
    def do_connect(self, host: str, device_id: str, password: str):
        try:
            self._client = VentoClient(
                host=host,
                device_id=device_id,
                password=password,
                timeout=4.0,
            )
            state = self._client.get_state()
            self.connected.emit(state)
        except VentoError as exc:
            self._client = None
            self.error.emit(f"Connection failed: {exc}")
        except Exception as exc:
            self._client = None
            self.error.emit(f"Unexpected connection error: {exc}")

    # ------------------------------------------------------------------
    # Polling
    # ------------------------------------------------------------------

    @pyqtSlot()
    def do_poll(self):
        if self._client is None:
            return
        try:
            state = self._client.get_state()
            self.state_updated.emit(state)
        except VentoError as exc:
            self.error.emit(f"Poll error: {exc}")
        except Exception as exc:
            self.error.emit(f"Unexpected poll error: {exc}")

    # ------------------------------------------------------------------
    # Write commands — each emits command_done on success, error on fail
    # ------------------------------------------------------------------

    def _run(self, fn, *args):
        """Helper: call fn(*args), emit command_done or error."""
        if self._client is None:
            self.error.emit("Not connected")
            return
        try:
            fn(*args)
            self.command_done.emit()
        except VentoError as exc:
            self.error.emit(str(exc))
        except Exception as exc:
            self.error.emit(f"Unexpected error: {exc}")

    @pyqtSlot(bool)
    def do_set_power(self, on: bool):
        if on:
            self._run(self._client.turn_on)
        else:
            self._run(self._client.turn_off)

    @pyqtSlot(int)
    def do_set_speed(self, speed: int):
        self._run(self._client.set_speed, speed)

    @pyqtSlot(int)
    def do_set_manual_speed(self, value: int):
        self._run(self._client.set_manual_speed, value)

    @pyqtSlot(int)
    def do_set_mode(self, mode: int):
        self._run(self._client.set_mode, mode)

    @pyqtSlot(bool)
    def do_set_boost(self, on: bool):
        self._run(
            self._client.write_params_with_response,
            {Param.BOOST_STATUS: int(on)},
        )

    @pyqtSlot(int)
    def do_set_humidity_sensor(self, state: int):
        self._run(self._client.set_humidity_sensor, state)

    @pyqtSlot(int)
    def do_set_humidity_threshold(self, rh: int):
        self._run(self._client.set_humidity_threshold, rh)
