"""DataUpdateCoordinator for the FranklinWH integration.

A single coordinator per config entry fans out parallel API calls to the
FranklinWH cloud and exposes a single FranklinData snapshot to every
platform. Stale-tolerance keeps the previous snapshot alive across
transient cloud failures so dashboards stop strobing to "unavailable".
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import timedelta
import logging
from typing import Any

import franklinwh
from franklinwh import (
    AccessoryType,
    Client,
    ExportSettings,
    Stats,
    SwitchState,
)
from franklinwh.client import (
    AccountLockedException,
    DeviceTimeoutException,
    GatewayOfflineException,
    InvalidCredentialsException,
    InvalidDataException,
)
import httpx

from homeassistant.const import (
    MAJOR_VERSION as HASS_MAJOR_VERSION,
    MINOR_VERSION as HASS_MINOR_VERSION,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

_LOGGER = logging.getLogger(__name__)

# Track whether the global httpx factory has been wired to HA's client.
# The upstream library uses a class-level factory, so we configure it once
# per HA process — every Client instance then reuses HA's pooled client.
_FACTORY_INSTALLED = False


def supports_http2() -> bool:
    """Return whether the running HA version exposes ALPN HTTP/2 helpers."""
    if HASS_MAJOR_VERSION > 2026:
        return True
    if HASS_MAJOR_VERSION == 2026 and HASS_MINOR_VERSION >= 2:
        return True
    return False


def install_http_client_factory(hass: HomeAssistant) -> None:
    """Wire the upstream HttpClientFactory to HA's managed httpx client."""
    global _FACTORY_INSTALLED
    if _FACTORY_INSTALLED:
        return

    if supports_http2():
        # pylint: disable=no-name-in-module,import-outside-toplevel
        from homeassistant.helpers.httpx_client import (  # noqa: PLC0415
            SSL_ALPN_HTTP11_HTTP2,  # type: ignore[attr-defined]
            create_async_httpx_client,
        )

        def _factory() -> httpx.AsyncClient:
            return create_async_httpx_client(hass, alpn_protocols=SSL_ALPN_HTTP11_HTTP2)

    else:
        # pylint: disable=import-outside-toplevel
        from homeassistant.helpers.httpx_client import (  # noqa: PLC0415
            create_async_httpx_client,
        )

        def _factory() -> httpx.AsyncClient:
            return create_async_httpx_client(hass)

    franklinwh.HttpClientFactory.set_client_factory(_factory)
    _FACTORY_INSTALLED = True


@dataclass
class FranklinData:
    """Snapshot of every API surface read on each coordinator cycle."""

    stats: Stats
    switches: SwitchState | None = None
    mode: tuple[str, int] | None = None
    export_settings: ExportSettings | None = None
    accessories: list[dict[str, Any]] = field(default_factory=list)

    @property
    def has_smart_circuits(self) -> bool:
        """Whether the gateway reports a Smart Circuit accessory."""
        return any(
            a.get("type") == AccessoryType.SMART_CIRCUIT_MODULE.value
            or a.get("accessoryType") == AccessoryType.SMART_CIRCUIT_MODULE.value
            for a in self.accessories
        )

    @property
    def has_generator(self) -> bool:
        """Whether the gateway reports a Generator accessory."""
        return any(
            a.get("type") == AccessoryType.GENERATOR_MODULE.value
            or a.get("accessoryType") == AccessoryType.GENERATOR_MODULE.value
            for a in self.accessories
        )


class FranklinDataUpdateCoordinator(DataUpdateCoordinator[FranklinData]):
    """Single shared coordinator across all FranklinWH platforms."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: Client,
        gateway_id: str,
        update_interval: timedelta,
        tolerate_stale_data: bool,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=f"franklinwh:{gateway_id}",
            update_interval=update_interval,
            always_update=False,
        )
        self.client = client
        self.gateway_id = gateway_id
        self.tolerate_stale_data = tolerate_stale_data
        self._last_good: FranklinData | None = None
        self._accessories_cache: list[dict[str, Any]] | None = None

    async def _fetch_accessories(self) -> list[dict[str, Any]]:
        """Cache accessory list — it rarely changes and a 404 here is non-fatal."""
        if self._accessories_cache is not None:
            return self._accessories_cache
        try:
            self._accessories_cache = await self.client.get_accessories() or []
        except Exception as err:  # noqa: BLE001 — accessory call is best-effort
            _LOGGER.debug("get_accessories failed (non-fatal): %s", err)
            self._accessories_cache = []
        return self._accessories_cache

    async def _safe(self, coro):
        """Best-effort fetch — returns None on any error rather than raising."""
        try:
            return await coro
        except Exception as err:  # noqa: BLE001 — secondary fetch is best-effort
            _LOGGER.debug("Secondary fetch failed: %s", err)
            return None

    async def _async_update_data(self) -> FranklinData:
        """Fetch a single snapshot from the FranklinWH cloud."""
        try:
            stats, switches, mode, export_settings, accessories = await asyncio.gather(
                self.client.get_stats(),
                self._safe(self.client.get_smart_switch_state()),
                self._safe(self.client.get_mode()),
                self._safe(self.client.get_export_settings()),
                self._fetch_accessories(),
            )
        except InvalidCredentialsException as err:
            # Trigger reauth flow
            raise ConfigEntryAuthFailed(str(err)) from err
        except AccountLockedException as err:
            raise ConfigEntryAuthFailed(f"Account locked: {err}") from err
        except (
            DeviceTimeoutException,
            GatewayOfflineException,
            InvalidDataException,
            httpx.HTTPError,
        ) as err:
            if self.tolerate_stale_data and self._last_good is not None:
                _LOGGER.warning(
                    "FranklinWH fetch failed (%s); reusing last-known data", err
                )
                return self._last_good
            raise UpdateFailed(f"FranklinWH fetch failed: {err}") from err

        data = FranklinData(
            stats=stats,
            switches=switches,
            mode=mode,
            export_settings=export_settings,
            accessories=accessories,
        )
        self._last_good = data
        return data
