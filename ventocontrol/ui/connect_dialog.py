"""ConnectDialog — device discovery + manual entry."""
from __future__ import annotations

from PyQt6.QtCore import Qt, QThread, pyqtSlot
from PyQt6.QtWidgets import (
    QDialog, QDialogButtonBox, QGroupBox, QHBoxLayout,
    QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QPushButton, QVBoxLayout,
)

from blauberg_vento.models import DiscoveredDevice
from ventocontrol.controllers.device_worker import DeviceWorker
from ventocontrol.history import DeviceHistory, HistoryEntry


class ConnectDialog(QDialog):
    """Shows recently connected devices, discovered devices, and manual entry."""

    def __init__(self, parent=None, *, history: DeviceHistory | None = None):
        super().__init__(parent)
        self._history = history
        self.setWindowTitle("Connect to Vento Fan")
        self.setMinimumWidth(480)
        self.setModal(True)

        # --- Worker + thread for discovery ---
        self._thread = QThread(self)
        self._worker = DeviceWorker()
        self._worker.moveToThread(self._thread)
        self._worker.discovery_result.connect(self._on_discovery_result)
        self._worker.error.connect(self._on_discovery_error)
        self._thread.start()

        # --- Recently connected ---
        self._hist_group = QGroupBox("Recently Connected")
        hist_layout = QVBoxLayout(self._hist_group)
        self._hist_list = QListWidget()
        self._hist_list.setMaximumHeight(120)
        self._hist_list.itemSelectionChanged.connect(self._on_hist_selection)
        hist_layout.addWidget(self._hist_list)
        clear_row = QHBoxLayout()
        clear_row.addStretch()
        self._clear_btn = QPushButton("Clear History")
        self._clear_btn.clicked.connect(self._on_clear_history)
        clear_row.addWidget(self._clear_btn)
        hist_layout.addLayout(clear_row)

        # --- Discovered devices list ---
        disc_group = QGroupBox("Discovered Devices")
        disc_layout = QVBoxLayout(disc_group)

        self._status_lbl = QLabel("Scanning…")
        self._status_lbl.setObjectName("ScanStatus")
        disc_layout.addWidget(self._status_lbl)

        self._device_list = QListWidget()
        self._device_list.setMinimumHeight(100)
        self._device_list.itemSelectionChanged.connect(self._on_disc_selection)
        disc_layout.addWidget(self._device_list)

        btn_row = QHBoxLayout()
        rescan_btn = QPushButton("Rescan")
        rescan_btn.clicked.connect(self._do_scan)
        btn_row.addWidget(rescan_btn)
        docker_btn = QPushButton("Scan Docker fans")
        docker_btn.setToolTip(
            "Probes 127.0.0.11 – 127.0.0.41 directly (no DNS needed).\n"
            "Each fan needs a loopback alias (sudo ./setup-loopback.sh)\n"
            "and a port mapping in docker-compose.yml."
        )
        docker_btn.clicked.connect(self._do_docker_scan)
        btn_row.addWidget(docker_btn)
        disc_layout.addLayout(btn_row)

        # --- Manual entry ---
        manual_group = QGroupBox("Manual Entry")
        manual_layout = QVBoxLayout(manual_group)

        ip_row = QHBoxLayout()
        ip_row.addWidget(QLabel("IP address:"))
        self._ip_edit = QLineEdit()
        self._ip_edit.setPlaceholderText("192.168.1.50")
        ip_row.addWidget(self._ip_edit)

        id_row = QHBoxLayout()
        id_row.addWidget(QLabel("Device ID:"))
        self._id_edit = QLineEdit()
        self._id_edit.setPlaceholderText("16-char ID from label")
        self._id_edit.setMaxLength(16)
        id_row.addWidget(self._id_edit)

        pw_row = QHBoxLayout()
        pw_row.addWidget(QLabel("Password:"))
        self._pw_edit = QLineEdit()
        self._pw_edit.setPlaceholderText("1111")
        self._pw_edit.setText("1111")
        self._pw_edit.setEchoMode(QLineEdit.EchoMode.Password)
        pw_row.addWidget(self._pw_edit)

        manual_layout.addLayout(ip_row)
        manual_layout.addLayout(id_row)
        manual_layout.addLayout(pw_row)

        for edit in (self._ip_edit, self._id_edit, self._pw_edit):
            edit.textChanged.connect(self._update_connect_btn)

        # --- Buttons ---
        self._button_box = QDialogButtonBox()
        self._connect_btn = self._button_box.addButton(
            "Connect", QDialogButtonBox.ButtonRole.AcceptRole
        )
        self._connect_btn.setEnabled(False)
        self._button_box.addButton(QDialogButtonBox.StandardButton.Cancel)
        self._button_box.accepted.connect(self.accept)
        self._button_box.rejected.connect(self.reject)

        # --- Main layout ---
        layout = QVBoxLayout(self)
        layout.addWidget(self._hist_group)
        layout.addWidget(disc_group)
        layout.addWidget(manual_group)
        layout.addWidget(self._button_box)

        # Populate history (also sets hist_group visibility)
        self._populate_history()

        # Kick off initial scan
        self._do_scan()

    # ------------------------------------------------------------------
    # Public: call after accept() to retrieve connection params
    # ------------------------------------------------------------------

    def connection_params(self) -> tuple[str, str, str]:
        """Returns (host, device_id, password). Priority: history > discovered > manual."""
        pw = self._pw_edit.text() or "1111"

        hist_sel = self._hist_list.selectedItems()
        if hist_sel:
            entry: HistoryEntry = hist_sel[0].data(Qt.ItemDataRole.UserRole)
            return entry.ip, entry.device_id, pw

        disc_sel = self._device_list.selectedItems()
        if disc_sel:
            dev: DiscoveredDevice = disc_sel[0].data(Qt.ItemDataRole.UserRole)
            return dev.ip, dev.device_id, pw

        return (
            self._ip_edit.text().strip(),
            self._id_edit.text().strip(),
            pw,
        )

    # ------------------------------------------------------------------
    # History helpers
    # ------------------------------------------------------------------

    def _populate_history(self) -> None:
        """Rebuild the history list widget from the DeviceHistory object."""
        self._hist_list.clear()
        entries = self._history.entries if self._history else []
        for entry in entries:
            label = entry.name if entry.name else entry.unit_type_name
            item = QListWidgetItem(f"{label}  —  {entry.ip}")
            item.setData(Qt.ItemDataRole.UserRole, entry)
            self._hist_list.addItem(item)
        self._hist_group.setVisible(bool(entries))

    @pyqtSlot()
    def _on_hist_selection(self) -> None:
        selected = self._hist_list.selectedItems()
        if selected:
            # Clear discovered selection to avoid ambiguity
            self._device_list.clearSelection()
            # Pre-fill password from the history entry
            entry: HistoryEntry = selected[0].data(Qt.ItemDataRole.UserRole)
            self._pw_edit.setText(entry.password)
        self._update_connect_btn()

    @pyqtSlot()
    def _on_disc_selection(self) -> None:
        if self._device_list.selectedItems():
            self._hist_list.clearSelection()
        self._update_connect_btn()

    @pyqtSlot()
    def _on_clear_history(self) -> None:
        if self._history:
            self._history.clear()
        self._populate_history()
        self._update_connect_btn()

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    def _do_scan(self):
        self._status_lbl.setText("Scanning…")
        self._device_list.clear()
        self._update_connect_btn()
        # Invoke on worker thread
        from PyQt6.QtCore import QMetaObject, Qt as _Qt
        QMetaObject.invokeMethod(self._worker, "do_discover",
                                 _Qt.ConnectionType.QueuedConnection)

    def _do_docker_scan(self):
        """Resolve fanN.vento hostnames and probe each container."""
        self._status_lbl.setText("Scanning Docker fans…")
        self._device_list.clear()
        self._update_connect_btn()
        from PyQt6.QtCore import QMetaObject, Qt as _Qt
        QMetaObject.invokeMethod(self._worker, "do_docker_discover",
                                 _Qt.ConnectionType.QueuedConnection)

    @pyqtSlot(list)
    def _on_discovery_result(self, devices: list[DiscoveredDevice]):
        self._device_list.clear()
        if not devices:
            self._status_lbl.setText("No devices found on this network.")
        else:
            self._status_lbl.setText(f"Found {len(devices)} device(s):")
            for dev in devices:
                item = QListWidgetItem(f"{dev.unit_type_name}  —  {dev.ip}")
                item.setData(Qt.ItemDataRole.UserRole, dev)
                self._device_list.addItem(item)
        self._update_connect_btn()

    @pyqtSlot(str)
    def _on_discovery_error(self, msg: str):
        self._status_lbl.setText(f"Scan error: {msg}")

    def _update_connect_btn(self):
        has_hist   = bool(self._hist_list.selectedItems())
        has_disc   = bool(self._device_list.selectedItems())
        has_manual = (
            bool(self._ip_edit.text().strip()) and
            bool(self._id_edit.text().strip())
        )
        self._connect_btn.setEnabled(has_hist or has_disc or has_manual)

    # ------------------------------------------------------------------
    # Thread teardown — called on accept, reject, and X-button close
    # ------------------------------------------------------------------

    def _stop_thread(self) -> None:
        """Stop the discovery thread.  Uses terminate() if it won't quit cleanly."""
        if self._thread.isRunning():
            self._thread.quit()
            if not self._thread.wait(400):   # 400 ms grace – discovery is ≤2 s
                self._thread.terminate()
                self._thread.wait(1000)

    def accept(self) -> None:
        self._stop_thread()
        super().accept()

    def reject(self) -> None:
        self._stop_thread()
        super().reject()

    def closeEvent(self, event) -> None:
        self._stop_thread()
        super().closeEvent(event)
