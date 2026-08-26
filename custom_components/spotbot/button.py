"""Button platform: panic trigger."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import KEY_PANIC
from .coordinator import SpotBotConfigEntry, SpotBotCoordinator
from .entity import SpotBotEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SpotBotConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up SpotBot buttons."""
    coordinator = entry.runtime_data
    async_add_entities(
        SpotBotPanicButton(coordinator, serial) for serial in (coordinator.data or {})
    )


class SpotBotPanicButton(SpotBotEntity, ButtonEntity):
    """Send a panic message (POST /devices/{serial}/panic).

    This triggers a REAL armed-response/panic notification chain, so the
    entity ships disabled by default — the user must consciously enable it
    in the entity registry.
    """

    _attr_translation_key = KEY_PANIC
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: SpotBotCoordinator, serial: str) -> None:
        super().__init__(coordinator, serial, KEY_PANIC)

    async def async_press(self) -> None:
        await self.coordinator.async_command(
            lambda: self.coordinator.client.async_panic(self._serial)
        )
