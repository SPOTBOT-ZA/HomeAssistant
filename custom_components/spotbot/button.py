"""Button platform: snooze and unsnooze."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import KEY_SNOOZE, KEY_UNSNOOZE
from .coordinator import SpotBotConfigEntry, SpotBotCoordinator
from .entity import SpotBotEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SpotBotConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up SpotBot buttons."""
    coordinator = entry.runtime_data
    entities: list[ButtonEntity] = []
    for serial in coordinator.data or {}:
        entities.append(SpotBotSnoozeButton(coordinator, serial))
        entities.append(SpotBotUnsnoozeButton(coordinator, serial))
    async_add_entities(entities)


class SpotBotSnoozeButton(SpotBotEntity, ButtonEntity):
    """Snooze every camera on the device (POST /snooze/all).

    A button rather than a switch because snooze is a timed action, not a
    state Home Assistant holds: the device expires it on its own after the
    duration, with nothing to switch back off. The server default of one
    hour applies — the endpoint's `time` field has no equivalent on a
    button, so a custom duration needs the API directly.
    """

    _attr_translation_key = KEY_SNOOZE

    def __init__(self, coordinator: SpotBotCoordinator, serial: str) -> None:
        super().__init__(coordinator, serial, KEY_SNOOZE)

    async def async_press(self) -> None:
        await self.coordinator.async_command(
            lambda: self.coordinator.client.async_snooze(self._serial, "all")
        )


class SpotBotUnsnoozeButton(SpotBotEntity, ButtonEntity):
    """Resume detection on every camera (POST /unsnooze/all)."""

    _attr_translation_key = KEY_UNSNOOZE

    def __init__(self, coordinator: SpotBotCoordinator, serial: str) -> None:
        super().__init__(coordinator, serial, KEY_UNSNOOZE)

    async def async_press(self) -> None:
        await self.coordinator.async_command(
            lambda: self.coordinator.client.async_unsnooze(self._serial, "all")
        )
