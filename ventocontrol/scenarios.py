"""ScenarioStore — persist fan scenarios to ~/.ventocontrol/scenarios.json.

v2 format: global scenario list (not per-device), fan list inside each scenario.
Automatic migration from v1 (per-device) format on first load.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional

_SCENARIOS_DIR  = Path.home() / ".ventocontrol"
_SCENARIOS_FILE = _SCENARIOS_DIR / "scenarios.json"
_MAX_SCENARIOS  = 10
_QUICK_SLOTS    = 3
_VERSION        = 2


@dataclass
class ScenarioSettings:
    """Snapshot of the controllable fan state fields."""
    power:               Optional[bool] = None
    speed:               Optional[int]  = None   # 1/2/3 preset or 255 = manual
    manual_speed:        Optional[int]  = None   # 0-255; only meaningful if speed==255
    operation_mode:      Optional[int]  = None   # 0=Ventilation, 1=Heat Recovery, 2=Supply
    boost_active:        Optional[bool] = None
    humidity_sensor:     Optional[int]  = None   # 0=off, 1=on
    humidity_threshold:  Optional[int]  = None   # 40-80 %RH


@dataclass
class FanSettings:
    """Settings for one specific fan device within a scenario."""
    device_id: str
    settings:  ScenarioSettings


@dataclass
class ScenarioEntry:
    name: str
    fans: list[FanSettings]   # one entry per fan device in the scenario


def get_settings_for_device(
    entry: ScenarioEntry, device_id: str
) -> Optional[ScenarioSettings]:
    """Return the ScenarioSettings for a specific device, or None if not in the scenario."""
    for fan in entry.fans:
        if fan.device_id == device_id:
            return fan.settings
    return None


class ScenarioStore:
    """Global scenario storage.  All operations are file-level atomic writes."""

    def __init__(self):
        self._scenarios:   list[dict]        = []
        self._quick_slots: dict[str, list]   = {}  # device_id → [name|None, ...]
        self._load()

    # ── Public API ───────────────────────────────────────────────────────

    def get_scenarios(self) -> list[ScenarioEntry]:
        """Return all scenarios in creation order."""
        result = []
        for item in self._scenarios:
            try:
                fans = [
                    FanSettings(
                        device_id=f["device_id"],
                        settings=ScenarioSettings(**f["settings"]),
                    )
                    for f in item["fans"]
                ]
                result.append(ScenarioEntry(name=item["name"], fans=fans))
            except (KeyError, TypeError):
                continue   # skip silently if JSON is malformed
        return result

    def save_scenario(self, entry: ScenarioEntry) -> None:
        """
        Add or overwrite a scenario by name.
        - Existing name → overwrite in-place (preserves list order).
        - New name       → append; if at cap, evict oldest (index 0) first.
        """
        # Update in-place if name already exists
        for i, s in enumerate(self._scenarios):
            if s["name"] == entry.name:
                self._scenarios[i] = self._to_dict(entry)
                self._save()
                return

        # New entry: enforce cap
        if len(self._scenarios) >= _MAX_SCENARIOS:
            evicted = self._scenarios.pop(0)["name"]
            # Clear quick slots that pointed to the evicted scenario
            for dev_slots in self._quick_slots.values():
                for j, slot in enumerate(dev_slots):
                    if slot == evicted:
                        dev_slots[j] = None

        self._scenarios.append(self._to_dict(entry))
        self._save()

    def delete_scenario(self, name: str) -> None:
        """Remove a scenario by name and clear any quick slots pointing to it."""
        self._scenarios = [s for s in self._scenarios if s["name"] != name]
        for dev_slots in self._quick_slots.values():
            for i, slot in enumerate(dev_slots):
                if slot == name:
                    dev_slots[i] = None
        self._save()

    def get_quick_slots(self, device_id: str) -> list[Optional[str]]:
        """Always returns a list of exactly _QUICK_SLOTS elements (str or None)."""
        slots = list(self._quick_slots.get(device_id, []))
        slots = slots[:_QUICK_SLOTS]
        while len(slots) < _QUICK_SLOTS:
            slots.append(None)
        return slots

    def set_quick_slots(self, device_id: str, slots: list[Optional[str]]) -> None:
        """Persist a 3-element quick-slot assignment list."""
        self._quick_slots[device_id] = list(slots)[:_QUICK_SLOTS]
        self._save()

    # ── Internal helpers ─────────────────────────────────────────────────

    @staticmethod
    def _to_dict(entry: ScenarioEntry) -> dict:
        return {
            "name": entry.name,
            "fans": [
                {"device_id": f.device_id, "settings": asdict(f.settings)}
                for f in entry.fans
            ],
        }

    def _load(self) -> None:
        try:
            raw = json.loads(_SCENARIOS_FILE.read_text())
            if raw.get("version", 1) < _VERSION:
                raw = self._migrate_v1(raw)
            self._scenarios   = raw.get("scenarios", [])
            self._quick_slots = raw.get("quick_slots", {})
        except (FileNotFoundError, json.JSONDecodeError, TypeError, KeyError):
            self._scenarios   = []
            self._quick_slots = {}

    def _save(self) -> None:
        try:
            _SCENARIOS_DIR.mkdir(parents=True, exist_ok=True)
            _SCENARIOS_FILE.write_text(
                json.dumps(
                    {
                        "version":     _VERSION,
                        "scenarios":   self._scenarios,
                        "quick_slots": self._quick_slots,
                    },
                    indent=2,
                )
            )
        except OSError:
            pass   # best-effort — never crash on persistence failure

    @staticmethod
    def _migrate_v1(raw: dict) -> dict:
        """Convert a v1 per-device JSON structure to the v2 global format."""
        scenarios:   list[dict]      = []
        quick_slots: dict[str, list] = {}

        for device_id, bucket in raw.get("devices", {}).items():
            for s in bucket.get("scenarios", []):
                name = s["name"]
                # Avoid name collisions from multiple devices
                if any(sc["name"] == name for sc in scenarios):
                    name = f"{name} ({device_id[-4:]})"
                scenarios.append({
                    "name": name,
                    "fans": [{"device_id": device_id, "settings": s["settings"]}],
                })
            quick_slots[device_id] = bucket.get("quick_slots", [None, None, None])

        return {"version": _VERSION, "scenarios": scenarios, "quick_slots": quick_slots}
