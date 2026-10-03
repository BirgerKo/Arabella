"""DeviceHistory — persist recently connected fans to ~/.ventocontrol/history.json."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

_HISTORY_DIR = Path.home() / ".ventocontrol"
_HISTORY_FILE = _HISTORY_DIR / "history.json"
_MAX_ENTRIES = 10


@dataclass
class HistoryEntry:
    device_id: str
    ip: str
    unit_type_name: str
    password: str = "1111"
    last_seen: str = ""  # ISO 8601 UTC timestamp
    name: str = ""  # user-defined display name (4–30 chars)


class DeviceHistory:
    """Ordered (most-recent-first) list of previously connected Vento fans.

    Observers (e.g. the Overview window) can register a callback that is
    invoked whenever the entry list changes.
    """

    def __init__(self):
        self._entries: list[HistoryEntry] = []
        self._observers: list = []  # list[Callable[[], None]]
        self._load()

    # ── Public API ───────────────────────────────────────────────────────

    @property
    def entries(self) -> list[HistoryEntry]:
        """All history entries, most-recently-used first."""
        return list(self._entries)

    @property
    def last_used(self) -> HistoryEntry | None:
        """The most recently connected device, or None if history is empty."""
        return self._entries[0] if self._entries else None

    def add_observer(self, callback) -> None:
        """Register a no-arg callback fired after every history change."""
        self._observers.append(callback)

    def record(self, device_id: str, ip: str, unit_type_name: str, password: str) -> None:
        """Add or refresh an entry.  Moves existing device_id to front.

        Any user-set display name on the existing entry is preserved so that
        reconnecting to a device never wipes a custom name.
        """
        ts = datetime.now(UTC).isoformat()
        # Preserve the user-set name from any existing entry for this device
        existing = next((e for e in self._entries if e.device_id == device_id), None)
        preserved_name = existing.name if existing else ""
        # Remove the stale entry so the refreshed one goes to position 0
        self._entries = [e for e in self._entries if e.device_id != device_id]
        self._entries.insert(
            0,
            HistoryEntry(
                device_id=device_id,
                ip=ip,
                unit_type_name=unit_type_name,
                password=password,
                last_seen=ts,
                name=preserved_name,
            ),
        )
        self._entries = self._entries[:_MAX_ENTRIES]
        self._save()
        self._notify()

    def rename(self, device_id: str, name: str) -> None:
        """Set or clear the custom display name for a device."""
        for entry in self._entries:
            if entry.device_id == device_id:
                entry.name = name
                break
        self._save()
        self._notify()

    def remove(self, device_id: str) -> None:
        """Remove one device from the history entirely."""
        self._entries = [e for e in self._entries if e.device_id != device_id]
        self._save()
        self._notify()

    def clear(self) -> None:
        """Remove all entries and persist the empty list."""
        self._entries = []
        self._save()
        self._notify()

    # ── Observers ────────────────────────────────────────────────────────

    def _notify(self) -> None:
        """Invoke observers; a broken observer must never break persistence."""
        for callback in self._observers:
            try:
                callback()
            except Exception:
                pass  # observer failures are non-fatal by design

    # ── Persistence ──────────────────────────────────────────────────────

    def _load(self) -> None:
        try:
            raw = json.loads(_HISTORY_FILE.read_text())
            self._entries = [HistoryEntry(**e) for e in raw.get("devices", [])]
        except (FileNotFoundError, json.JSONDecodeError, TypeError, KeyError):
            self._entries = []

    def _save(self) -> None:
        try:
            _HISTORY_DIR.mkdir(parents=True, exist_ok=True)
            data = {"devices": [asdict(e) for e in self._entries]}
            _HISTORY_FILE.write_text(json.dumps(data, indent=2))
        except OSError:
            pass  # best-effort — never crash on a persistence failure
