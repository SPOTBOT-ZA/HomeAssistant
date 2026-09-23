"""Config flow for the SpotBot integration (OAuth2 authorization-code flow).

Login on the SpotBot side is phone number + SMS/push OTP rendered by the
OAuth server itself; there is no consent screen. The server supports no
PKCE, so the registered client is confidential and users supply the
client_id/client_secret through Home Assistant's Application Credentials UI.
"""

from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant.config_entries import SOURCE_REAUTH, ConfigFlowResult
from homeassistant.helpers import aiohttp_client, config_entry_oauth2_flow

from .application_credentials import async_ensure_client_credential
from .const import API_TIMEOUT, CONF_BASE_URL, DEFAULT_BASE_URL, DOMAIN

_LOGGER = logging.getLogger(__name__)


class SpotBotOAuth2FlowHandler(
    config_entry_oauth2_flow.AbstractOAuth2FlowHandler, domain=DOMAIN
):
    """Handle the SpotBot OAuth2 config flow."""

    DOMAIN = DOMAIN
    VERSION = 1

    @property
    def logger(self) -> logging.Logger:
        """Return the logger."""
        return _LOGGER

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Register the built-in client, then run the normal OAuth step.

        This is the first of our code that runs when the user clicks Add
        Integration, and on a fresh install nothing has registered the
        credential yet — async_setup only runs once a config entry exists.
        Without this the flow would abort with missing_credentials and send
        the user to the Application Credentials dialog for a client ID and
        secret that ship with the integration.
        """
        await async_ensure_client_credential(self.hass)
        return await super().async_step_user(user_input)

    @property
    def extra_authorize_data(self) -> dict[str, Any]:
        """Extra parameters for the authorize URL.

        The server ignores OAuth scopes entirely (authorization is the
        client's epm bitmask), and Home Assistant supplies the mandatory
        ``state`` parameter itself.
        """
        return {}

    async def async_step_reauth(
        self, entry_data: dict[str, Any]
    ) -> ConfigFlowResult:
        """Start reauthentication (e.g. the refresh token died or the user
        deleted the 'ha-' device from their SpotBot account)."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm before re-running the OAuth dance."""
        if user_input is None:
            return self.async_show_form(
                step_id="reauth_confirm", data_schema=vol.Schema({})
            )
        return await self.async_step_user()

    async def async_oauth_create_entry(
        self, data: dict[str, Any]
    ) -> ConfigFlowResult:
        """Create (or update, on reauth) the entry once tokens are obtained.

        Identity comes from GET /oauth/userinfo — the account's ``sb_id`` is
        the unique_id, giving one config entry per SpotBot account.
        """
        access_token = data["token"]["access_token"]
        session = aiohttp_client.async_get_clientsession(self.hass)
        try:
            async with session.get(
                f"{DEFAULT_BASE_URL}/oauth/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=aiohttp.ClientTimeout(total=API_TIMEOUT),
            ) as resp:
                resp.raise_for_status()
                userinfo = await resp.json(content_type=None)
        except (aiohttp.ClientError, TimeoutError):
            _LOGGER.exception("Error fetching SpotBot userinfo")
            return self.async_abort(reason="cannot_connect")

        sb_id = str(userinfo.get("sb_id") or "")
        if not sb_id:
            _LOGGER.error("SpotBot userinfo carried no sb_id: %s", userinfo)
            return self.async_abort(reason="cannot_connect")

        await self.async_set_unique_id(sb_id)

        full_name = " ".join(
            part
            for part in (userinfo.get("name"), userinfo.get("surname"))
            if part
        ).strip()
        title = full_name or str(userinfo.get("cellnumber") or f"SpotBot {sb_id}")

        # Entries are self-describing: the base URL used at auth time rides
        # along so a future multi-deployment picker needs no migration.
        entry_data = {**data, CONF_BASE_URL: DEFAULT_BASE_URL}

        if self.source == SOURCE_REAUTH:
            self._abort_if_unique_id_mismatch(reason="wrong_account")
            return self.async_update_reload_and_abort(
                self._get_reauth_entry(), data=entry_data
            )

        self._abort_if_unique_id_configured()
        return self.async_create_entry(title=title, data=entry_data)
