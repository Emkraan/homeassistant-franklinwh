"""Number platform — battery reserve SoC and grid-export power limit."""

from __future__ import annotations

import logging

from franklinwh import ExportMode, Mode

from homeassistant.components.number import (
    NumberDeviceClass,
    NumberEntity,
    NumberMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfPower
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    MODE_EMERGENCY_BACKUP,
    MODE_SELF_CONSUMPTION,
    MODE_TIME_OF_USE,
)
from .coordinator import FranklinDataUpdateCoordinator
from .entity import FranklinBaseEntity

_LOGGER = logging.getLogger(__name__)

_MODE_FACTORY = {
    MODE_TIME_OF_USE: Mode.time_of_use,
    MODE_SELF_CONSUMPTION: Mode.self_consumption,
    MODE_EMERGENCY_BACKUP: Mode.emergency_backup,
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add Number entities."""
    coordinator: FranklinDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[NumberEntity] = [BatteryReserveNumber(coordinator)]
    if coordinator.data and coordinator.data.export_settings is not None:
        entities.append(ExportLimitNumber(coordinator))
    async_add_entities(entities)


class BatteryReserveNumber(FranklinBaseEntity, NumberEntity):
    """Battery minimum SoC reserve % for the active operating mode."""

    _attr_translation_key = "battery_reserve"
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_device_class = NumberDeviceClass.BATTERY
    _attr_native_min_value = 0
    _attr_native_max_value = 100
    _attr_native_step = 1
    _attr_mode = NumberMode.SLIDER

    def __init__(self, coordinator: FranklinDataUpdateCoordinator) -> None:
        """Initialize."""
        super().__init__(coordinator, "battery_reserve")

    @property
    def native_value(self) -> float | None:
        """Current SoC reserve from get_mode()."""
        if self.coordinator.data is None or self.coordinator.data.mode is None:
            return None
        return float(self.coordinator.data.mode[1])

    async def async_set_native_value(self, value: float) -> None:
        """Re-issue the active mode with the new SoC reserve."""
        if self.coordinator.data is None or self.coordinator.data.mode is None:
            _LOGGER.warning("Cannot set reserve — current mode unknown")
            return
        mode_name = self.coordinator.data.mode[0]
        factory = _MODE_FACTORY.get(mode_name)
        if factory is None:
            _LOGGER.warning("Unknown mode '%s' — cannot update reserve", mode_name)
            return
        await self.coordinator.client.set_mode(factory(int(value)))
        await self.coordinator.async_request_refresh()


class ExportLimitNumber(FranklinBaseEntity, NumberEntity):
    """Grid-export power cap (kW). Disabled when export mode is NO_EXPORT."""

    _attr_translation_key = "export_limit"
    _attr_native_unit_of_measurement = UnitOfPower.KILO_WATT
    _attr_device_class = NumberDeviceClass.POWER
    _attr_native_min_value = 0.0
    _attr_native_max_value = 100.0
    _attr_native_step = 0.1
    _attr_mode = NumberMode.BOX

    def __init__(self, coordinator: FranklinDataUpdateCoordinator) -> None:
        """Initialize."""
        super().__init__(coordinator, "export_limit")

    @property
    def native_value(self) -> float | None:
        """Current export limit in kW (None means unlimited)."""
        if (
            self.coordinator.data is None
            or self.coordinator.data.export_settings is None
        ):
            return None
        return self.coordinator.data.export_settings.limit_kw

    @property
    def available(self) -> bool:
        """Hide when export is disabled entirely."""
        if not super().available:
            return False
        es = self.coordinator.data.export_settings if self.coordinator.data else None
        return es is not None and es.mode != ExportMode.NO_EXPORT

    async def async_set_native_value(self, value: float) -> None:
        """Push a new export cap, preserving current mode."""
        if (
            self.coordinator.data is None
            or self.coordinator.data.export_settings is None
        ):
            return
        current_mode = self.coordinator.data.export_settings.mode
        await self.coordinator.client.set_export_settings(current_mode, float(value))
        await self.coordinator.async_request_refresh()
