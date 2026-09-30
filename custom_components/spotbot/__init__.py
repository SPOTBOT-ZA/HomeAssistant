"""The SpotBot integration."""

from __future__ import annotations

import asyncio
import logging

import aiohttp

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers import config_entry_oauth2_flow, config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.typing import ConfigType

from .api import (
    AsyncConfigEntryAuth,
    SpotBotApiClient,
    SpotBotApiError,
    SpotBotPermissionError,
)
from .application_credentials import async_ensure_client_credential
from .const import (
    CONF_BASE_URL,
    CONF_SYNCED_DEVICE_ID,
    CONF_SYNCED_SERIALS,
    DEFAULT_BASE_URL,
    DOMAIN,
    PARALLEL_DEVICE_REQUESTS,
)
from .coordinator import SpotBotConfigEntry, SpotBotCoordinator

_LOGGER = logging.getLogger(__name__)

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

    # Backgrounded: each sync is an MQTT round trip, and nothing here should
    # hold up setup or fail it.
    entry.async_create_background_task(
        hass,
        _async_sync_users(hass, entry, coordinator, client),
        f"{DOMAIN}_user_sync",
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def _async_sync_users(
    hass: HomeAssistant,
    entry: SpotBotConfigEntry,
    coordinator: SpotBotCoordinator,
    client: SpotBotApiClient,
) -> None:
    """Tell each SpotBot to pick up this session's oauth device id.

    Signing in mints a new device id, recorded server-side but unknown to the
    devices themselves until they sync. Until then every command is refused
    with an RPC-level "Authentication failed" while the entities look
    perfectly healthy — so this runs once per device id, not once per setup,
    and retries any serial that was offline at the time.
    """
    token = entry.data.get("token") or {}
    device_id = token.get("oauth_device_id")
    sb_id = entry.unique_id
    if not device_id or not sb_id:
        _LOGGER.debug("No device id or sb_id on the entry; skipping user sync")
        return

    already = set(entry.data.get(CONF_SYNCED_SERIALS) or [])
    if entry.data.get(CONF_SYNCED_DEVICE_ID) != device_id:
        already = set()  # new sign-in: every device has to be told again

    pending = [s for s in (coordinator.data or {}) if s not in already]
    if not pending:
        return

    semaphore = asyncio.Semaphore(PARALLEL_DEVICE_REQUESTS)

    async def sync_one(serial: str) -> str | None:
        async with semaphore:
            await client.async_sync_users(serial, device_id, sb_id)
            return serial

    results = await asyncio.gather(
        *(sync_one(serial) for serial in pending), return_exceptions=True
    )

    synced: set[str] = set(already)
    for serial, result in zip(pending, results):
        if isinstance(result, SpotBotPermissionError):
            # Account-wide, not per device: say it once and stop.
            _LOGGER.warning(
                "Cannot sync this session to your SpotBots: the OAuth client's "
                "endpoint mask does not allow %s. Until it does, the devices "
                "will not recognise this Home Assistant session and will "
                "refuse commands with an authentication error (%s)",
                "users/sync (endpoint group 3)",
                result,
            )
            return
        if isinstance(result, SpotBotApiError):
            _LOGGER.debug("User sync failed for %s, will retry: %s", serial, result)
            continue
        if isinstance(result, BaseException):
            _LOGGER.debug("User sync errored for %s: %s", serial, result)
            continue
        synced.add(serial)

    if synced != already or entry.data.get(CONF_SYNCED_DEVICE_ID) != device_id:
        hass.config_entries.async_update_entry(
            entry,
            data={
                **entry.data,
                CONF_SYNCED_DEVICE_ID: device_id,
                CONF_SYNCED_SERIALS: sorted(synced),
            },
        )
    _LOGGER.debug("Synced device id to %d of %d SpotBots", len(synced), len(pending))


async def async_unload_entry(hass: HomeAssistant, entry: SpotBotConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
