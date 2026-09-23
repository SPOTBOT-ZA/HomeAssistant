"""Data update coordinator for the SpotBot integration."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Awaitable, Callable

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import (
    SpotBotApiClient,
    SpotBotApiError,
    SpotBotAuthError,
    SpotBotConnectionError,
    SpotBotDevice,
    SpotBotDeviceOfflineError,
    SpotBotPresence,
    SpotBotStatus,
)
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN, PARALLEL_DEVICE_REQUESTS

_LOGGER = logging.getLogger(__name__)

type SpotBotConfigEntry = ConfigEntry[SpotBotCoordinator]


@dataclass
class SpotBotDeviceData:
    """Everything the entities need about one SpotBot."""

    device: SpotBotDevice
    presence: SpotBotPresence | None = None
    # Last KNOWN status — kept when the device goes offline so switches don't
    # flap to unknown during outages.
    status: SpotBotStatus | None = None

    @property
    def online(self) -> bool:
        return bool(self.presence and self.presence.online)


class SpotBotCoordinator(DataUpdateCoordinator[dict[str, SpotBotDeviceData]]):
    """Poll the SpotBot cloud for all devices on the account.

    Every REST call is a synchronous MQTT round-trip that parks a PHP worker
    server-side, so the fan-out is throttled with a small semaphore and the
    status call is skipped entirely for offline devices (it would just burn
    the 8 s route timeout and come back 504).
    """

    config_entry: SpotBotConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        entry: SpotBotConfigEntry,
        client: SpotBotApiClient,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=DEFAULT_SCAN_INTERVAL,
        )
        self.client = client

    async def _async_update_data(self) -> dict[str, SpotBotDeviceData]:
        try:
            devices = await self.client.async_get_devices()
        except SpotBotAuthError as err:
            raise ConfigEntryAuthFailed(err) from err
        except SpotBotApiError as err:
            raise UpdateFailed(f"Device list failed: {err}") from err

        previous = self.data or {}
        semaphore = asyncio.Semaphore(PARALLEL_DEVICE_REQUESTS)

        async def refresh_device(device: SpotBotDevice) -> SpotBotDeviceData:
            prev = previous.get(device.serial)
            data = SpotBotDeviceData(
                device=device,
                status=prev.status if prev else None,
            )
            async with semaphore:
                try:
                    data.presence = await self.client.async_get_presence(device.serial)
                except SpotBotAuthError:
                    raise
                except (SpotBotConnectionError, SpotBotApiError) as err:
                    _LOGGER.debug("Presence failed for %s: %s", device.serial, err)
                    data.presence = None
                if data.online:
                    try:
                        data.status = await self.client.async_get_status(device.serial)
                    except SpotBotAuthError:
                        raise
                    except SpotBotDeviceOfflineError:
                        # Presence said online but the device didn't answer.
                        data.presence = None
                    except (SpotBotConnectionError, SpotBotApiError) as err:
                        _LOGGER.debug("Status failed for %s: %s", device.serial, err)
            return data

        try:
            results = await asyncio.gather(
                *(refresh_device(device) for device in devices)
            )
        except SpotBotAuthError as err:
            raise ConfigEntryAuthFailed(err) from err

        return {data.device.serial: data for data in results}

    async def async_command(self, command: Callable[[], Awaitable[Any]]) -> None:
        """Run a device command, then refresh so state converges.

        Everything the API can raise becomes a HomeAssistantError so the
        failure reaches the user as the message it carries, rather than as
        an "Unexpected exception" traceback in the log with nothing useful
        in the UI. Only a dead token still means reauth.
        """
        try:
            await command()
        except SpotBotAuthError as err:
            raise ConfigEntryAuthFailed(err) from err
        except SpotBotApiError as err:
            raise HomeAssistantError(str(err)) from err
        await self.async_request_refresh()
