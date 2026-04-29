"""Switch platform for FranklinWH smart circuits."""

from __future__ import annotations

import logging

from franklinwh import SwitchState

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import FranklinDataUpdateCoordinator
from .entity import FranklinBaseEntity

_LOGGER = logging.getLogger(__name__)

# Three relays exposed by the Smart Circuit module.
RELAY_LABELS = ("switch_1", "switch_2", "v2l_switch")
RELAY_FRIENDLY = ("Smart Circuit 1", "Smart Circuit 2", "V2L Circuit")


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add one switch per physical relay if the gateway reports a Smart Circuit module."""
    coordinator: FranklinDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    data = coordinator.data
    if data is None or not data.has_smart_circuits or data.switches is None:
        _LOGGER.debug(
            "No Smart Circuit module reported for %s — skipping switches",
            coordinator.gateway_id,
        )
        return

    async_add_entities(FranklinSmartSwitch(coordinator, idx) for idx in range(3))


class FranklinSmartSwitch(FranklinBaseEntity, SwitchEntity):
    """A single FranklinWH smart-circuit relay."""

    def __init__(
        self,
        coordinator: FranklinDataUpdateCoordinator,
        index: int,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator, RELAY_LABELS[index])
        self._index = index
        self._attr_translation_key = RELAY_LABELS[index]
        self._attr_name = RELAY_FRIENDLY[index]

    @property
    def is_on(self) -> bool | None:
        """Current relay state."""
        data = self.coordinator.data
        if data is None or data.switches is None:
            return None
        try:
            return bool(data.switches[self._index])
        except (IndexError, TypeError):
            return None

    async def async_turn_on(self, **kwargs) -> None:
        """Turn this relay on."""
        await self._set(True)

    async def async_turn_off(self, **kwargs) -> None:
        """Turn this relay off."""
        await self._set(False)

    async def _set(self, value: bool) -> None:
        state: list[bool | None] = [None, None, None]
        state[self._index] = value
        try:
            await self.coordinator.client.set_smart_switch_state(SwitchState(state))
        except RuntimeError as err:
            # Gateway reports merged switches — abort cleanly so HA surfaces the error.
            _LOGGER.error("Smart-switch set failed: %s", err)
            raise
        await self.coordinator.async_request_refresh()

    @callback
    def _handle_coordinator_update(self) -> None:
        self.async_write_ha_state()
