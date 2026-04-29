"""Select platform — operating mode and grid-export mode."""

from __future__ import annotations

import logging

from franklinwh import ExportMode, Mode

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    ALL_MODES,
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

EXPORT_MODE_OPTIONS = [m.name.lower() for m in ExportMode]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add Select entities."""
    coordinator: FranklinDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[SelectEntity] = [OperatingModeSelect(coordinator)]
    if coordinator.data and coordinator.data.export_settings is not None:
        entities.append(ExportModeSelect(coordinator))
    async_add_entities(entities)


class OperatingModeSelect(FranklinBaseEntity, SelectEntity):
    """Time-of-use / self-consumption / emergency-backup selector."""

    _attr_translation_key = "operating_mode"
    _attr_options = ALL_MODES

    def __init__(self, coordinator: FranklinDataUpdateCoordinator) -> None:
        """Initialize."""
        super().__init__(coordinator, "operating_mode")

    @property
    def current_option(self) -> str | None:
        """Return current mode name."""
        if self.coordinator.data is None or self.coordinator.data.mode is None:
            return None
        return self.coordinator.data.mode[0]

    async def async_select_option(self, option: str) -> None:
        """Switch operating mode, keeping current SoC reserve."""
        factory = _MODE_FACTORY[option]
        current_soc = (
            self.coordinator.data.mode[1]
            if self.coordinator.data and self.coordinator.data.mode
            else None
        )
        await self.coordinator.client.set_mode(
            factory(current_soc) if current_soc is not None else factory()
        )
        await self.coordinator.async_request_refresh()


class ExportModeSelect(FranklinBaseEntity, SelectEntity):
    """Solar-only / solar+aPower / no-export selector."""

    _attr_translation_key = "export_mode"
    _attr_options = EXPORT_MODE_OPTIONS

    def __init__(self, coordinator: FranklinDataUpdateCoordinator) -> None:
        """Initialize."""
        super().__init__(coordinator, "export_mode")

    @property
    def current_option(self) -> str | None:
        """Return current export mode."""
        if (
            self.coordinator.data is None
            or self.coordinator.data.export_settings is None
        ):
            return None
        return self.coordinator.data.export_settings.mode.name.lower()

    async def async_select_option(self, option: str) -> None:
        """Set export mode, preserving current limit."""
        new_mode = ExportMode[option.upper()]
        current_limit = (
            self.coordinator.data.export_settings.limit_kw
            if self.coordinator.data and self.coordinator.data.export_settings
            else None
        )
        await self.coordinator.client.set_export_settings(new_mode, current_limit)
        await self.coordinator.async_request_refresh()
