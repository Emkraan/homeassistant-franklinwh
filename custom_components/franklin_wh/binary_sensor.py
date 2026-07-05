"""Binary-sensor platform for FranklinWH."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from franklinwh import GridStatus

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import FranklinData, FranklinDataUpdateCoordinator
from .entity import FranklinBaseEntity


@dataclass(frozen=True, kw_only=True)
class FranklinBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Describes a FranklinWH binary sensor."""

    is_on_fn: Callable[[FranklinData], bool | None]


BINARY_SENSORS: tuple[FranklinBinarySensorEntityDescription, ...] = (
    FranklinBinarySensorEntityDescription(
        key="grid_online",
        translation_key="grid_online",
        device_class=BinarySensorDeviceClass.POWER,
        is_on_fn=lambda d: d.stats.current.grid_status == GridStatus.NORMAL,
    ),
    FranklinBinarySensorEntityDescription(
        key="generator_enabled",
        translation_key="generator_enabled",
        device_class=BinarySensorDeviceClass.RUNNING,
        is_on_fn=lambda d: d.stats.current.generator_enabled,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add binary sensors."""
    coordinator: FranklinDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(FranklinBinarySensor(coordinator, d) for d in BINARY_SENSORS)


class FranklinBinarySensor(FranklinBaseEntity, BinarySensorEntity):
    """Description-driven binary sensor."""

    entity_description: FranklinBinarySensorEntityDescription

    def __init__(
        self,
        coordinator: FranklinDataUpdateCoordinator,
        description: FranklinBinarySensorEntityDescription,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        """Compute on/off state."""
        if self.coordinator.data is None:
            return None
        return self.entity_description.is_on_fn(self.coordinator.data)
