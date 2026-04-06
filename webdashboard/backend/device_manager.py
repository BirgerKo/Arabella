"""Device manager — async wrapper around AsyncVentoClient.

Runs all UDP I/O natively via AsyncVentoClient (which uses asyncio
internally).  Holds the current DeviceState and triggers hub broadcasts
after each successful poll or command.

Architecture note: this module contains the core use-case logic and must
not import FastAPI, Pydantic, or any other framework.
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import asdict
from typing import Any, Optional

from blauberg_vento.client import AsyncVentoClient, VentoClient
from blauberg_vento.models import DeviceState, DiscoveredDevice

log = logging.getLogger(__name__)

_POLL_INTERVAL_SECONDS = 2.0


def _state_to_dict(state: DeviceState) -> dict[str, Any]:
    """Convert a DeviceState to a JSON-serialisable dict."""
    return {
        "connected": True,
        "ip": state.ip,
        "device_id": state.device_id,
        "power": state.power,
        "speed": state.speed,
        "manual_speed": state.manual_speed,
        "operation_mode": state.operation_mode,
        "operation_mode_name": state.operation_mode_name,
        "boost_active": state.boost_active,
        "humidity_sensor": state.humidity_sensor,
        "humidity_threshold": state.humidity_threshold,
        "current_humidity": state.current_humidity,
        "fan1_rpm": state.fan1_rpm,
        "fan2_rpm": state.fan2_rpm,
        "alarm_status": state.alarm_status,
        "alarm_name": state.alarm_name,
        "weekly_schedule_enabled": state.weekly_schedule_enabled,
        "rtc_time": str(state.rtc_time) if state.rtc_time else None,
        "rtc_calendar": str(state.rtc_calendar) if state.rtc_calendar else None,
    }


class DeviceManager:
    """Manages the connection to a single Vento fan device."""

    def __init__(self) -> None:
        self._client: Optional[AsyncVentoClient] = None
        self._state: Optional[DeviceState] = None
        self._poll_task: Optional[asyncio.Task] = None
        self._broadcast_callback: Optional[Any] = None  # async callable(dict)

    def set_broadcast_callback(self, callback) -> None:
        """Register the async callback that receives state-update dicts."""
        self._broadcast_callback = callback

    # ── Connection ────────────────────────────────────────────────────────────

    async def connect(self, ip: str, device_id: str, password: str = "1111") -> DeviceState:
        """Connect to a device and perform an initial state fetch."""
        await self._stop_polling()
        self._client = AsyncVentoClient(ip, device_id, password)
        self._state = await self._client.get_state()
        self._start_polling()
        return self._state

    def disconnect(self) -> None:
        asyncio.create_task(self._stop_polling())
        self._client = None
        self._state = None

    @property
    def is_connected(self) -> bool:
        return self._client is not None and self._state is not None

    @property
    def current_state(self) -> Optional[DeviceState]:
        return self._state

    # ── Commands ──────────────────────────────────────────────────────────────

    async def set_power(self, on: bool) -> None:
        self._require_connection()
        if on:
            await self._client.turn_on()
        else:
            await self._client.turn_off()
        await self._poll_after_command()

    async def set_speed(self, speed: int) -> None:
        """Set speed: 1/2/3 for presets; 0-254 triggers manual_speed."""
        self._require_connection()
        if 1 <= speed <= 3:
            await self._client.set_speed(speed)
        else:
            await self._client.set_manual_speed(speed)
        await self._poll_after_command()

    async def set_mode(self, mode: int) -> None:
        """Set operation mode: 0=Ventilation, 1=Heat Recovery, 2=Supply."""
        self._require_connection()
        await self._client.set_mode(mode)
        await self._poll_after_command()

    async def set_boost(self, on: bool) -> None:
        self._require_connection()
        from blauberg_vento.parameters import Param
        await self._client.write_params({Param.BOOST_STATUS: 1 if on else 0})
        await self._poll_after_command()

    async def set_humidity_sensor(self, sensor: int) -> None:
        """Set humidity sensor mode: 0=Off, 1=On, 2=Invert."""
        self._require_connection()
        await self._client.set_humidity_sensor(sensor)
        await self._poll_after_command()

    async def set_humidity_threshold(self, threshold: int) -> None:
        """Set humidity threshold in percent relative humidity (40–80)."""
        self._require_connection()
        await self._client.set_humidity_threshold(threshold)
        await self._poll_after_command()

    async def enable_schedule(self, enabled: bool) -> None:
        """Enable or disable the weekly schedule."""
        self._require_connection()
        await self._client.enable_weekly_schedule(enabled)
        await self._poll_after_command()

    async def set_schedule_period(
        self, day: int, period: int, speed: int, end_h: int, end_m: int
    ) -> None:
        """Write one schedule period to the device."""
        self._require_connection()
        await self._client.set_schedule_period(day, period, speed, end_h, end_m)

    async def get_full_schedule(self) -> list[list]:
        """Read all 32 schedule periods (8 day groups × 4 periods) from the device."""
        self._require_connection()
        result = []
        for day in range(8):
            row = []
            for period in range(1, 5):
                sp = await self._client.get_schedule_period(day, period)
                row.append(sp)
            result.append(row)
        return result

    async def sync_rtc(self) -> None:
        """Synchronise the device real-time clock to system time."""
        self._require_connection()
        await self._client.sync_rtc()
        await self._poll_after_command()

    # ── Discovery ─────────────────────────────────────────────────────────────

    @staticmethod
    async def discover() -> list[DiscoveredDevice]:
        """Broadcast UDP discovery and return found devices."""
        return await AsyncVentoClient.discover()

    # ── Internal ──────────────────────────────────────────────────────────────

    def _require_connection(self) -> None:
        if not self.is_connected:
            raise RuntimeError("Not connected to any device")

    def _start_polling(self) -> None:
        self._poll_task = asyncio.create_task(self._poll_loop())

    async def _stop_polling(self) -> None:
        if self._poll_task and not self._poll_task.done():
            self._poll_task.cancel()
            try:
                await self._poll_task
            except asyncio.CancelledError:
                pass
        self._poll_task = None

    async def _poll_loop(self) -> None:
        while True:
            await asyncio.sleep(_POLL_INTERVAL_SECONDS)
            try:
                await self._poll_and_broadcast()
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                log.warning("Poll error: %s", exc)
                if self._broadcast_callback:
                    await self._broadcast_callback(
                        {"type": "error", "data": {"message": str(exc)}}
                    )

    async def _poll_after_command(self) -> None:
        """Wait briefly so the fan can apply the command, then broadcast fresh state."""
        await asyncio.sleep(0.3)
        await self._poll_and_broadcast()

    async def _poll_and_broadcast(self) -> None:
        if not self._client:
            return
        self._state = await self._client.get_state()
        if self._broadcast_callback:
            await self._broadcast_callback(
                {"type": "state", "data": _state_to_dict(self._state)}
            )
