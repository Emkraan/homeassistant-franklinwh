"""Constants for the FranklinWH integration."""

from __future__ import annotations

from datetime import timedelta

from homeassistant.const import Platform

DOMAIN = "franklin_wh"
MANUFACTURER = "FranklinWH"

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.SWITCH,
    Platform.BINARY_SENSOR,
    Platform.NUMBER,
    Platform.SELECT,
]

# Config-entry data keys
CONF_GATEWAY = "gateway"

# Options keys
CONF_PREFIX = "prefix"
CONF_UPDATE_INTERVAL = "update_interval"
CONF_TOLERATE_STALE_DATA = "tolerate_stale_data"
CONF_REVERSE_BATTERY_SIGN = "reverse_battery_sign"
CONF_REVERSE_GRID_SIGN = "reverse_grid_sign"
CONF_SMART_CIRCUIT_GROUPS = "smart_circuit_groups"

DEFAULT_UPDATE_INTERVAL_SECONDS = 30
DEFAULT_UPDATE_INTERVAL = timedelta(seconds=DEFAULT_UPDATE_INTERVAL_SECONDS)
DEFAULT_PREFIX = "FranklinWH"
DEFAULT_TOLERATE_STALE_DATA = True

MIN_UPDATE_INTERVAL_SECONDS = 10
MAX_UPDATE_INTERVAL_SECONDS = 600

# Mode tokens (mirrors franklinwh.client.MODE_*)
MODE_TIME_OF_USE = "time_of_use"
MODE_SELF_CONSUMPTION = "self_consumption"
MODE_EMERGENCY_BACKUP = "emergency_backup"

ALL_MODES = [MODE_TIME_OF_USE, MODE_SELF_CONSUMPTION, MODE_EMERGENCY_BACKUP]

# Service names
SERVICE_SET_MODE = "set_mode"
SERVICE_SET_EXPORT_SETTINGS = "set_export_settings"
SERVICE_SET_GENERATOR = "set_generator"

ATTR_MODE = "mode"
ATTR_RESERVE_SOC = "reserve_soc"
ATTR_EXPORT_MODE = "export_mode"
ATTR_EXPORT_LIMIT_KW = "export_limit_kw"
ATTR_ENABLED = "enabled"
ATTR_GATEWAY = "gateway"
