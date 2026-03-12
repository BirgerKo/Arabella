"""FastAPI dependency providers.

These are thin adapters that expose singletons to request handlers.
"""
from __future__ import annotations

from typing import Generator

from ventocontrol.scenarios import ScenarioStore
from webdashboard.backend.device_manager import DeviceManager
from webdashboard.backend.hub import ConnectionHub

# Module-level singletons — created once at startup in main.py
_device_manager: DeviceManager | None = None
_hub: ConnectionHub | None = None
_scenario_store: ScenarioStore | None = None


def init_singletons() -> tuple[DeviceManager, ConnectionHub, ScenarioStore]:
    global _device_manager, _hub, _scenario_store
    _device_manager = DeviceManager()
    _hub = ConnectionHub()
    _scenario_store = ScenarioStore()
    _device_manager.set_broadcast_callback(_hub.broadcast)
    return _device_manager, _hub, _scenario_store


def get_device_manager() -> DeviceManager:
    assert _device_manager is not None, "Singletons not initialised"
    return _device_manager


def get_hub() -> ConnectionHub:
    assert _hub is not None, "Singletons not initialised"
    return _hub


def get_scenario_store() -> ScenarioStore:
    assert _scenario_store is not None, "Singletons not initialised"
    return _scenario_store
