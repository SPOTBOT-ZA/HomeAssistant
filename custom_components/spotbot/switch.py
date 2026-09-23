"""Switch platform: per-camera detection & armed response, speaker mute.

Snooze is not here: it is a timed action that the device expires by itself,
and the device-level snooze flag is never set (state lives per camera), so
it ships as buttons on the button platform instead.
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import KEY_ARMED_RESPONSE, KEY_DETECTION, KEY_SPEAKER_MUTE
from .coordinator import SpotBotConfigEntry, SpotBotCoordinator
from .entity import SpotBotEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SpotBotConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up SpotBot switches for every device and camera."""
    coordinator = entry.runtime_data
    known_cams: set[tuple[str, str]] = set()

    @callback
    def add_new_entities() -> None:
        new: list[SwitchEntity] = []
        for serial, data in (coordinator.data or {}).items():
            if (serial, "") not in known_cams:
                known_cams.add((serial, ""))
                new.append(SpotBotSpeakerMuteSwitch(coordinator, serial))
            for cam in data.status.cameras if data.status else []:
                if (serial, cam.cam_nr) in known_cams:
                    continue
                known_cams.add((serial, cam.cam_nr))
                new.append(SpotBotDetectionSwitch(coordinator, serial, cam.cam_nr))
                new.append(SpotBotArmedResponseSwitch(coordinator, serial, cam.cam_nr))
        if new:
            async_add_entities(new)

    add_new_entities()
    entry.async_on_unload(coordinator.async_add_listener(add_new_entities))


class SpotBotDetectionSwitch(SpotBotEntity, SwitchEntity):
    """Camera detection on/off (POST /devices/{serial}/on|off/{cam})."""

    _attr_translation_key = KEY_DETECTION

    def __init__(self, coordinator: SpotBotCoordinator, serial: str, cam_nr: str) -> None:
        super().__init__(coordinator, serial, KEY_DETECTION, cam_nr)
        self._attr_translation_placeholders = {"camera": self._camera_label()}

    def _camera_label(self) -> str:
        cam = self.camera
        return (cam.name if cam and cam.name else f"Camera {self._cam_nr}")

    @property
    def is_on(self) -> bool | None:
        cam = self.camera
        return cam.detection_on if cam else None

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.async_command(
            lambda: self.coordinator.client.async_set_detection(
                self._serial, self._cam_nr, True
            )
        )

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.async_command(
            lambda: self.coordinator.client.async_set_detection(
                self._serial, self._cam_nr, False
            )
        )


class SpotBotArmedResponseSwitch(SpotBotEntity, SwitchEntity):
    """Armed response on/off per camera (POST ar_on|ar_off/{cam})."""

    _attr_translation_key = KEY_ARMED_RESPONSE

    def __init__(self, coordinator: SpotBotCoordinator, serial: str, cam_nr: str) -> None:
        super().__init__(coordinator, serial, KEY_ARMED_RESPONSE, cam_nr)
        cam = self.camera
        self._attr_translation_placeholders = {
            "camera": cam.name if cam and cam.name else f"Camera {cam_nr}"
        }

    @property
    def is_on(self) -> bool | None:
        cam = self.camera
        return cam.armed_response_on if cam else None

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.async_command(
            lambda: self.coordinator.client.async_set_armed_response(
                self._serial, self._cam_nr, True
            )
        )

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.async_command(
            lambda: self.coordinator.client.async_set_armed_response(
                self._serial, self._cam_nr, False
            )
        )


class SpotBotSpeakerMuteSwitch(SpotBotEntity, SwitchEntity):
    """Speaker mute (POST /speaker_mute)."""

    _attr_translation_key = KEY_SPEAKER_MUTE

    def __init__(self, coordinator: SpotBotCoordinator, serial: str) -> None:
        super().__init__(coordinator, serial, KEY_SPEAKER_MUTE)

    @property
    def is_on(self) -> bool | None:
        data = self.device_data
        return data.status.speaker_muted if data and data.status else None

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.async_command(
            lambda: self.coordinator.client.async_set_speaker_mute(self._serial, True)
        )

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.async_command(
            lambda: self.coordinator.client.async_set_speaker_mute(self._serial, False)
        )
