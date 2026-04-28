"""Config flow for the FranklinWH integration."""

from __future__ import annotations

from collections.abc import Mapping
import logging
from typing import Any

import franklinwh
from franklinwh.client import (
    AccountLockedException,
    InvalidCredentialsException,
)
import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    BooleanSelector,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .const import (
    CONF_GATEWAY,
    CONF_PREFIX,
    CONF_REVERSE_BATTERY_SIGN,
    CONF_REVERSE_GRID_SIGN,
    CONF_TOLERATE_STALE_DATA,
    CONF_UPDATE_INTERVAL,
    DEFAULT_PREFIX,
    DEFAULT_TOLERATE_STALE_DATA,
    DEFAULT_UPDATE_INTERVAL_SECONDS,
    DOMAIN,
    MAX_UPDATE_INTERVAL_SECONDS,
    MIN_UPDATE_INTERVAL_SECONDS,
)
from .coordinator import install_http_client_factory

_LOGGER = logging.getLogger(__name__)


def _user_schema(defaults: Mapping[str, Any] | None = None) -> vol.Schema:
    defaults = defaults or {}
    return vol.Schema(
        {
            vol.Required(
                CONF_USERNAME, default=defaults.get(CONF_USERNAME, "")
            ): TextSelector(TextSelectorConfig(type=TextSelectorType.EMAIL)),
            vol.Required(
                CONF_PASSWORD, default=defaults.get(CONF_PASSWORD, "")
            ): TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD)),
        }
    )


async def _validate_credentials(username: str, password: str) -> dict:
    """Return the raw login info dict on success or raise the upstream error."""
    fetcher = franklinwh.TokenFetcher(username, password)
    await fetcher.get_token()
    return fetcher.info or {}


async def _list_gateways(username: str, password: str) -> list[dict]:
    """Return the gateway list for the account."""
    fetcher = franklinwh.TokenFetcher(username, password)
    token = await fetcher.get_token()
    # gateway argument is unused by getHomeGatewayList; pass empty placeholder
    client = franklinwh.Client(fetcher, "")
    client.token = token
    return await client.get_home_gateway_list() or []


class FranklinWHConfigFlow(ConfigFlow, domain=DOMAIN):
    """Config flow for FranklinWH."""

    VERSION = 1

    def __init__(self) -> None:
        """Init transient state."""
        self._username: str | None = None
        self._password: str | None = None
        self._gateways: list[dict] = []

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Collect credentials, then proceed to gateway selection."""
        errors: dict[str, str] = {}

        if user_input is not None:
            install_http_client_factory(self.hass)
            try:
                gateways = await _list_gateways(
                    user_input[CONF_USERNAME], user_input[CONF_PASSWORD]
                )
            except InvalidCredentialsException:
                errors["base"] = "invalid_auth"
            except AccountLockedException:
                errors["base"] = "account_locked"
            except Exception as err:  # noqa: BLE001
                _LOGGER.exception("Unexpected error contacting FranklinWH: %s", err)
                errors["base"] = "cannot_connect"
            else:
                self._username = user_input[CONF_USERNAME]
                self._password = user_input[CONF_PASSWORD]
                self._gateways = gateways

                if not gateways:
                    errors["base"] = "no_gateways"
                elif len(gateways) == 1:
                    return await self._create_entry(self._gateway_id(gateways[0]))
                else:
                    return await self.async_step_pick_gateway()

        return self.async_show_form(
            step_id="user",
            data_schema=_user_schema(user_input),
            errors=errors,
        )

    async def async_step_pick_gateway(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Choose which gateway this entry represents."""
        if user_input is not None:
            return await self._create_entry(user_input[CONF_GATEWAY])

        options = [
            {
                "value": self._gateway_id(g),
                "label": self._gateway_label(g),
            }
            for g in self._gateways
        ]
        return self.async_show_form(
            step_id="pick_gateway",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_GATEWAY): SelectSelector(
                        SelectSelectorConfig(
                            options=options, mode=SelectSelectorMode.DROPDOWN
                        )
                    )
                }
            ),
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Triggered when stored credentials stop working."""
        self._username = entry_data.get(CONF_USERNAME)
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Re-prompt for the password."""
        errors: dict[str, str] = {}
        entry = self._get_reauth_entry()

        if user_input is not None:
            install_http_client_factory(self.hass)
            try:
                await _validate_credentials(
                    user_input[CONF_USERNAME], user_input[CONF_PASSWORD]
                )
            except InvalidCredentialsException:
                errors["base"] = "invalid_auth"
            except AccountLockedException:
                errors["base"] = "account_locked"
            except Exception as err:  # noqa: BLE001
                _LOGGER.exception("Reauth check failed: %s", err)
                errors["base"] = "cannot_connect"
            else:
                self.hass.config_entries.async_update_entry(
                    entry,
                    data={
                        **entry.data,
                        CONF_USERNAME: user_input[CONF_USERNAME],
                        CONF_PASSWORD: user_input[CONF_PASSWORD],
                    },
                )
                await self.hass.config_entries.async_reload(entry.entry_id)
                return self.async_abort(reason="reauth_successful")

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=_user_schema(
                {CONF_USERNAME: self._username or entry.data.get(CONF_USERNAME, "")}
            ),
            errors=errors,
        )

    async def async_step_import(self, import_data: dict[str, Any]) -> ConfigFlowResult:
        """Import legacy YAML configuration as a config entry."""
        install_http_client_factory(self.hass)
        username = import_data[CONF_USERNAME]
        password = import_data[CONF_PASSWORD]
        gateway = import_data[CONF_GATEWAY]

        await self.async_set_unique_id(gateway)
        self._abort_if_unique_id_configured()

        try:
            await _validate_credentials(username, password)
        except Exception as err:  # noqa: BLE001
            _LOGGER.warning(
                "YAML import for gateway %s failed validation: %s", gateway, err
            )
            return self.async_abort(reason="cannot_connect")

        return self.async_create_entry(
            title=f"FranklinWH {gateway}",
            data={
                CONF_USERNAME: username,
                CONF_PASSWORD: password,
                CONF_GATEWAY: gateway,
            },
            options=import_data.get("options", {}),
        )

    async def _create_entry(self, gateway_id: str) -> ConfigFlowResult:
        """Finalize the entry once we know the gateway."""
        await self.async_set_unique_id(gateway_id)
        self._abort_if_unique_id_configured()
        assert self._username and self._password
        return self.async_create_entry(
            title=f"FranklinWH {gateway_id}",
            data={
                CONF_USERNAME: self._username,
                CONF_PASSWORD: self._password,
                CONF_GATEWAY: gateway_id,
            },
        )

    @staticmethod
    def _gateway_id(g: dict) -> str:
        for key in ("gatewayId", "snno", "sn", "id"):
            if g.get(key):
                return str(g[key])
        return str(g)

    @staticmethod
    def _gateway_label(g: dict) -> str:
        gid = FranklinWHConfigFlow._gateway_id(g)
        model = g.get("model") or g.get("gatewayModel") or "aGate"
        status_raw = g.get("status") or g.get("onlineStatus")
        status = "online" if status_raw in (1, "1", "online", True) else "offline"
        return f"{gid} — {model} ({status})"

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Return the options flow handler."""
        return FranklinWHOptionsFlow(config_entry)


class FranklinWHOptionsFlow(OptionsFlow):
    """Options flow for FranklinWH."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Init."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Single options page."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        opts = self.config_entry.options
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_PREFIX,
                        default=opts.get(CONF_PREFIX, DEFAULT_PREFIX),
                    ): str,
                    vol.Optional(
                        CONF_UPDATE_INTERVAL,
                        default=opts.get(
                            CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL_SECONDS
                        ),
                    ): NumberSelector(
                        NumberSelectorConfig(
                            min=MIN_UPDATE_INTERVAL_SECONDS,
                            max=MAX_UPDATE_INTERVAL_SECONDS,
                            step=5,
                            unit_of_measurement="s",
                            mode=NumberSelectorMode.SLIDER,
                        )
                    ),
                    vol.Optional(
                        CONF_TOLERATE_STALE_DATA,
                        default=opts.get(
                            CONF_TOLERATE_STALE_DATA, DEFAULT_TOLERATE_STALE_DATA
                        ),
                    ): BooleanSelector(),
                    vol.Optional(
                        CONF_REVERSE_BATTERY_SIGN,
                        default=opts.get(CONF_REVERSE_BATTERY_SIGN, False),
                    ): BooleanSelector(),
                    vol.Optional(
                        CONF_REVERSE_GRID_SIGN,
                        default=opts.get(CONF_REVERSE_GRID_SIGN, False),
                    ): BooleanSelector(),
                }
            ),
        )
