"""Diagnostics support for the SpotBot integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from .coordinator import SpotBotConfigEntry

TO_REDACT = {
    "token",
    "access_token",
    "refresh_token",
    "cell",
    "cellnumber",
    "email",
    "sb_id",
    "name",
    "surname",
    "Chat_id",
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: SpotBotConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = entry.runtime_data
    devices = {
        serial: {
            "device": data.device.raw,
            "online": data.online,
            "presence": data.presence.raw if data.presence else None,
            "status": data.status.raw if data.status else None,
        }
        for serial, data in (coordinator.data or {}).items()
    }
    return async_redact_data(
        {
            "entry_data": dict(entry.data),
            "base_url": coordinator.client.base_url,
            "devices": devices,
        },
        TO_REDACT,
    )
