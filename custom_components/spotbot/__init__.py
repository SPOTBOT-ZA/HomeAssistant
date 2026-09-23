"""The SpotBot integration."""

from __future__ import annotations

import aiohttp

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers import config_entry_oauth2_flow, config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.typing import ConfigType

from .api import AsyncConfigEntryAuth, SpotBotApiClient
from .application_credentials import async_ensure_client_credential
from .const import CONF_BASE_URL, DEFAULT_BASE_URL, DOMAIN
from .coordinator import SpotBotConfigEntry, SpotBotCoordinator

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.SWITCH,
]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Restore the built-in SpotBot OAuth client on startup.

    The config flow registers it too (and is what covers a fresh install,
    where this never runs). This call is what puts it back for an existing
    installation whose credential was deleted by hand, so a reauth still has
    an implementation to use.
    """
    await async_ensure_client_credential(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: SpotBotConfigEntry) -> bool:
    """Set up SpotBot from a config entry."""
    implementation = (
        await config_entry_oauth2_flow.async_get_config_entry_implementation(
            hass, entry
        )
    )
    session = config_entry_oauth2_flow.OAuth2Session(hass, entry, implementation)

    try:
        await session.async_ensure_token_valid()
    except aiohttp.ClientResponseError as err:
        if err.status in (400, 401, 403):
            raise ConfigEntryAuthFailed("OAuth token refresh rejected") from err
        raise ConfigEntryNotReady(f"Token refresh failed: {err}") from err
    except aiohttp.ClientError as err:
        raise ConfigEntryNotReady(f"Cannot reach SpotBot OAuth server: {err}") from err

    auth = AsyncConfigEntryAuth(session)
    client = SpotBotApiClient(
        auth,
        async_get_clientsession(hass),
        entry.data.get(CONF_BASE_URL, DEFAULT_BASE_URL),
    )

    coordinator = SpotBotCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: SpotBotConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
