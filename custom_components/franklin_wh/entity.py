"""Base entity for the FranklinWH integration."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER
from .coordinator import FranklinDataUpdateCoordinator


class FranklinBaseEntity(CoordinatorEntity[FranklinDataUpdateCoordinator]):
    """Common base — sets device info and availability for every platform."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: FranklinDataUpdateCoordinator,
        unique_id_suffix: str,
    ) -> None:
        """Initialize the entity, anchoring it to the gateway device."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.gateway_id}_{unique_id_suffix}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.gateway_id)},
            manufacturer=MANUFACTURER,
            name=f"{MANUFACTURER} {coordinator.gateway_id}",
            model="aPower / aGate",
            configuration_url="https://energy.franklinwh.com/",
        )

    @property
    def available(self) -> bool:
        """Mirror coordinator availability."""
        return (
            super().available
            and self.coordinator.last_update_success
            and self.coordinator.data is not None
        )
