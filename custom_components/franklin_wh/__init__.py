"""The FranklinWH integration.

Modern config-entry-driven setup. YAML platform configurations from earlier
versions are auto-imported into the UI flow on first run; the YAML keys
themselves remain functional for one release cycle and emit a deprecation
issue via the Repairs registry.
"""

from __future__ import annotations

from datetime import timedelta
import logging

import franklinwh

from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.const import CONF_ID, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.typing import ConfigType

from .const import (
    CONF_GATEWAY,
    CONF_TOLERATE_STALE_DATA,
    CONF_UPDATE_INTERVAL,
    DEFAULT_TOLERATE_STALE_DATA,
    DEFAULT_UPDATE_INTERVAL_SECONDS,
    DOMAIN,
    PLATFORMS,
)
from .coordinator import (
    FranklinDataUpdateCoordinator,
    install_http_client_factory,
)
from .services import async_register_services, async_unregister_services

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Detect legacy `franklin_wh` YAML platform entries and import them."""
    yaml_imports: list[dict] = []
    for section in ("sensor", "switch"):
        for raw in config.get(section, []) or []:
            if isinstance(raw, dict) and raw.get("platform") == DOMAIN:
                yaml_imports.append(raw)

    for raw in yaml_imports:
        gateway = raw.get(CONF_ID) or raw.get(CONF_GATEWAY)
        if not gateway or not raw.get(CONF_USERNAME) or not raw.get(CONF_PASSWORD):
            continue
        ir.async_create_issue(
            hass,
            DOMAIN,
            f"yaml_deprecated_{gateway}",
            is_fixable=False,
            severity=ir.IssueSeverity.WARNING,
            translation_key="yaml_deprecated",
            translation_placeholders={"gateway": str(gateway)},
        )
        hass.async_create_task(
            hass.config_entries.flow.async_init(
                DOMAIN,
                context={"source": SOURCE_IMPORT},
                data={
                    CONF_USERNAME: raw[CONF_USERNAME],
                    CONF_PASSWORD: raw[CONF_PASSWORD],
                    CONF_GATEWAY: str(gateway),
                },
            )
        )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up FranklinWH from a config entry."""
    install_http_client_factory(hass)

    username = entry.data[CONF_USERNAME]
    password = entry.data[CONF_PASSWORD]
    gateway = entry.data[CONF_GATEWAY]

    fetcher = franklinwh.TokenFetcher(username, password)
    client = franklinwh.Client(fetcher, gateway)

    interval_s = entry.options.get(
        CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL_SECONDS
    )
    tolerate_stale = entry.options.get(
        CONF_TOLERATE_STALE_DATA, DEFAULT_TOLERATE_STALE_DATA
    )

    coordinator = FranklinDataUpdateCoordinator(
        hass,
        client=client,
        gateway_id=gateway,
        update_interval=timedelta(seconds=int(interval_s)),
        tolerate_stale_data=bool(tolerate_stale),
    )
    await coordinator.async_refresh()
    if not coordinator.last_update_success:
        raise ConfigEntryNotReady(
            f"FranklinWH gateway {gateway!r} not reachable at startup; will retry"
        )

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await async_register_services(hass)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_options_updated))
    return True


async def _async_options_updated(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the entry whenever the options flow saves changes."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id, None)
        if not hass.data[DOMAIN]:
            await async_unregister_services(hass)
    return unloaded
