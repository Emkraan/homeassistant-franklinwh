"""Service handlers for the FranklinWH integration."""

from __future__ import annotations

import logging

from franklinwh import ExportMode, Mode
from franklinwh.client import InvalidCredentialsException
import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
import homeassistant.helpers.config_validation as cv

from .const import (
    ALL_MODES,
    ATTR_ENABLED,
    ATTR_EXPORT_LIMIT_KW,
    ATTR_EXPORT_MODE,
    ATTR_GATEWAY,
    ATTR_MODE,
    ATTR_RESERVE_SOC,
    DOMAIN,
    MODE_EMERGENCY_BACKUP,
    MODE_SELF_CONSUMPTION,
    MODE_TIME_OF_USE,
    SERVICE_SET_EXPORT_SETTINGS,
    SERVICE_SET_GENERATOR,
    SERVICE_SET_MODE,
)
from .coordinator import FranklinDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

_MODE_FACTORY = {
    MODE_TIME_OF_USE: Mode.time_of_use,
    MODE_SELF_CONSUMPTION: Mode.self_consumption,
    MODE_EMERGENCY_BACKUP: Mode.emergency_backup,
}

_EXPORT_MODE_BY_NAME = {m.name.lower(): m for m in ExportMode}

SET_MODE_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_GATEWAY): cv.string,
        vol.Required(ATTR_MODE): vol.In(ALL_MODES),
        vol.Optional(ATTR_RESERVE_SOC): vol.All(
            vol.Coerce(int), vol.Range(min=0, max=100)
        ),
    }
)

SET_EXPORT_SETTINGS_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_GATEWAY): cv.string,
        vol.Required(ATTR_EXPORT_MODE): vol.In(list(_EXPORT_MODE_BY_NAME)),
        vol.Optional(ATTR_EXPORT_LIMIT_KW): vol.All(
            vol.Coerce(float), vol.Range(min=0.0, max=10000.0)
        ),
    }
)

SET_GENERATOR_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_GATEWAY): cv.string,
        vol.Required(ATTR_ENABLED): cv.boolean,
    }
)


def _resolve_coordinator(
    hass: HomeAssistant, gateway: str | None
) -> FranklinDataUpdateCoordinator:
    """Pick a coordinator from `hass.data[DOMAIN]`, optionally filtered by gateway."""
    bucket: dict = hass.data.get(DOMAIN, {})
    coordinators: list[FranklinDataUpdateCoordinator] = list(bucket.values())
    if not coordinators:
        raise ServiceValidationError("No FranklinWH gateway is currently configured.")
    if gateway:
        for c in coordinators:
            if c.gateway_id == gateway:
                return c
        raise ServiceValidationError(f"Gateway '{gateway}' is not configured.")
    if len(coordinators) > 1:
        raise ServiceValidationError(
            "Multiple gateways configured — specify 'gateway' in the service call."
        )
    return coordinators[0]


async def _async_set_mode(call: ServiceCall) -> None:
    coord = _resolve_coordinator(call.hass, call.data.get(ATTR_GATEWAY))
    mode_name: str = call.data[ATTR_MODE]
    soc = call.data.get(ATTR_RESERVE_SOC)

    factory = _MODE_FACTORY[mode_name]
    mode = factory(soc) if soc is not None else factory()
    try:
        await coord.client.set_mode(mode)
    except InvalidCredentialsException as err:
        raise HomeAssistantError(f"Invalid credentials: {err}") from err
    await coord.async_request_refresh()


async def _async_set_export_settings(call: ServiceCall) -> None:
    coord = _resolve_coordinator(call.hass, call.data.get(ATTR_GATEWAY))
    mode = _EXPORT_MODE_BY_NAME[call.data[ATTR_EXPORT_MODE]]
    limit_kw = call.data.get(ATTR_EXPORT_LIMIT_KW)
    try:
        await coord.client.set_export_settings(mode, limit_kw)
    except InvalidCredentialsException as err:
        raise HomeAssistantError(f"Invalid credentials: {err}") from err
    await coord.async_request_refresh()


async def _async_set_generator(call: ServiceCall) -> None:
    coord = _resolve_coordinator(call.hass, call.data.get(ATTR_GATEWAY))
    try:
        await coord.client.set_generator(bool(call.data[ATTR_ENABLED]))
    except InvalidCredentialsException as err:
        raise HomeAssistantError(f"Invalid credentials: {err}") from err
    await coord.async_request_refresh()


async def async_register_services(hass: HomeAssistant) -> None:
    """Register integration services (idempotent)."""
    if hass.services.has_service(DOMAIN, SERVICE_SET_MODE):
        return
    hass.services.async_register(
        DOMAIN, SERVICE_SET_MODE, _async_set_mode, schema=SET_MODE_SCHEMA
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_EXPORT_SETTINGS,
        _async_set_export_settings,
        schema=SET_EXPORT_SETTINGS_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN, SERVICE_SET_GENERATOR, _async_set_generator, schema=SET_GENERATOR_SCHEMA
    )


async def async_unregister_services(hass: HomeAssistant) -> None:
    """Remove all integration services."""
    for svc in (SERVICE_SET_MODE, SERVICE_SET_EXPORT_SETTINGS, SERVICE_SET_GENERATOR):
        if hass.services.has_service(DOMAIN, svc):
            hass.services.async_remove(DOMAIN, svc)
