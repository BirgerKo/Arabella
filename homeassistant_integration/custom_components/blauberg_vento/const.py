"""Constants for the Blauberg Vento integration."""

from __future__ import annotations

from homeassistant.const import Platform

DOMAIN = "blauberg_vento"
PLATFORMS = [Platform.FAN, Platform.SENSOR, Platform.BINARY_SENSOR, Platform.NUMBER]

DEFAULT_PASSWORD = "1111"
DEFAULT_NAME = "Vento Fan"
CONF_DEVICE_ID = "device_id"

SPEED_MIN = 1
SPEED_MAX = 3
MANUAL_SPEED_MIN = 0
MANUAL_SPEED_MAX = 255
