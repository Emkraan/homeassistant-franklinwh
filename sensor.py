"""Sensor platform for FranklinWH."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import logging

from franklinwh import GridStatus

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfEnergy, UnitOfPower
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_REVERSE_BATTERY_SIGN,
    CONF_REVERSE_GRID_SIGN,
    DOMAIN,
)
from .coordinator import FranklinData, FranklinDataUpdateCoordinator
from .entity import FranklinBaseEntity

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class FranklinSensorEntityDescription(SensorEntityDescription):
    """Describes a FranklinWH sensor."""

    value_fn: Callable[[FranklinData], float | str | None]


# fmt: off
SENSOR_DESCRIPTIONS: tuple[FranklinSensorEntityDescription, ...] = (
    FranklinSensorEntityDescription(
        key="state_of_charge",
        translation_key="state_of_charge",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.stats.current.battery_soc,
    ),
    FranklinSensorEntityDescription(
        key="home_load",
        translation_key="home_load",
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.stats.current.home_load,
    ),
    FranklinSensorEntityDescription(
        key="home_use",
        translation_key="home_use",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda d: d.stats.totals.home_use,
    ),
    FranklinSensorEntityDescription(
        key="battery_use",
        translation_key="battery_use",
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.stats.current.battery_use,
    ),
    FranklinSensorEntityDescription(
        key="grid_use",
        translation_key="grid_use",
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.stats.current.grid_use,
    ),
    FranklinSensorEntityDescription(
        key="grid_status",
        translation_key="grid_status",
        device_class=SensorDeviceClass.ENUM,
        options=[s.name for s in GridStatus],
        value_fn=lambda d: d.stats.current.grid_status.name,
    ),
    FranklinSensorEntityDescription(
        key="solar_production",
        translation_key="solar_production",
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.stats.current.solar_production,
    ),
    FranklinSensorEntityDescription(
        key="solar_energy",
        translation_key="solar_energy",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda d: d.stats.totals.solar,
    ),
    FranklinSensorEntityDescription(
        key="battery_charge",
        translation_key="battery_charge",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda d: d.stats.totals.battery_charge,
    ),
    FranklinSensorEntityDescription(
        key="battery_discharge",
        translation_key="battery_discharge",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda d: d.stats.totals.battery_discharge,
    ),
    FranklinSensorEntityDescription(
        key="generator_use",
        translation_key="generator_use",
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.stats.current.generator_production,
    ),
    FranklinSensorEntityDescription(
        key="generator_energy",
        translation_key="generator_energy",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda d: d.stats.totals.generator,
    ),
    FranklinSensorEntityDescription(
        key="grid_import",
        translation_key="grid_import",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda d: d.stats.totals.grid_import,
    ),
    FranklinSensorEntityDescription(
        key="grid_export",
        translation_key="grid_export",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda d: d.stats.totals.grid_export,
    ),
    FranklinSensorEntityDescription(
        key="switch_1_load",
        translation_key="switch_1_load",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.stats.current.switch_1_load,
    ),
    FranklinSensorEntityDescription(
        key="switch_1_lifetime_use",
        translation_key="switch_1_lifetime_use",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda d: d.stats.totals.switch_1_use,
    ),
    FranklinSensorEntityDescription(
        key="switch_2_load",
        translation_key="switch_2_load",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.stats.current.switch_2_load,
    ),
    FranklinSensorEntityDescription(
        key="switch_2_lifetime_use",
        translation_key="switch_2_lifetime_use",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda d: d.stats.totals.switch_2_use,
    ),
    FranklinSensorEntityDescription(
        key="v2l_use",
        translation_key="v2l_use",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.stats.current.v2l_use,
    ),
    FranklinSensorEntityDescription(
        key="v2l_export",
        translation_key="v2l_export",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda d: d.stats.totals.v2l_export,
    ),
    FranklinSensorEntityDescription(
        key="v2l_import",
        translation_key="v2l_import",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda d: d.stats.totals.v2l_import,
    ),
)
# fmt: on


# Sensor keys whose sign should flip when the corresponding option is set.
_BATTERY_SIGN_KEYS = {"battery_use"}
_GRID_SIGN_KEYS = {"grid_use"}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up FranklinWH sensors from a config entry."""
    coordinator: FranklinDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    reverse_battery = entry.options.get(CONF_REVERSE_BATTERY_SIGN, False)
    reverse_grid = entry.options.get(CONF_REVERSE_GRID_SIGN, False)

    async_add_entities(
        FranklinSensor(
            coordinator,
            description,
            reverse=(
                (reverse_battery and description.key in _BATTERY_SIGN_KEYS)
                or (reverse_grid and description.key in _GRID_SIGN_KEYS)
            ),
        )
        for description in SENSOR_DESCRIPTIONS
    )


class FranklinSensor(FranklinBaseEntity, SensorEntity):
    """Description-driven FranklinWH sensor."""

    entity_description: FranklinSensorEntityDescription

    def __init__(
        self,
        coordinator: FranklinDataUpdateCoordinator,
        description: FranklinSensorEntityDescription,
        *,
        reverse: bool = False,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator, description.key)
        self.entity_description = description
        self._reverse = reverse

    @property
    def native_value(self):
        """Compute the current value via the description's value_fn."""
        if self.coordinator.data is None:
            return None
        value = self.entity_description.value_fn(self.coordinator.data)
        if self._reverse and isinstance(value, (int, float)):
            return -value
        return value
