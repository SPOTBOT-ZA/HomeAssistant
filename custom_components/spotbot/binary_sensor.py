"""Binary sensor platform: device online + per-camera connectivity."""

from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONN_STATUS_ERROR,
    CONN_STATUS_OK,
    CONN_STATUS_WARNING,
    KEY_CAMERA_CONNECTIVITY,
    KEY_ONLINE,
)
from .coordinator import SpotBotConfigEntry, SpotBotCoordinator
from .entity import SpotBotEntity

CONN_STATUS_TEXT = {
    CONN_STATUS_OK: "fine",
    CONN_STATUS_WARNING: "warning",
    CONN_STATUS_ERROR: "error",
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SpotBotConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up SpotBot binary sensors."""
    coordinator = entry.runtime_data
    known: set[tuple[str, str]] = set()

    @callback
    def add_new_entities() -> None:
        new: list[BinarySensorEntity] = []
        for serial, data in (coordinator.data or {}).items():
            if (serial, "") not in known:
                known.add((serial, ""))
                new.append(SpotBotOnlineSensor(coordinator, serial))
            for cam in data.status.cameras if data.status else []:
                if (serial, cam.cam_nr) in known:
                    continue
                known.add((serial, cam.cam_nr))
                new.append(
                    SpotBotCameraConnectivitySensor(coordinator, serial, cam.cam_nr)
                )
        if new:
            async_add_entities(new)

    add_new_entities()
    entry.async_on_unload(coordinator.async_add_listener(add_new_entities))


class SpotBotOnlineSensor(SpotBotEntity, BinarySensorEntity):
    """Whether the SpotBot itself is reachable (retained MQTT presence)."""

    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: SpotBotCoordinator, serial: str) -> None:
        super().__init__(coordinator, serial, KEY_ONLINE)

    @property
    def available(self) -> bool:
        """Stay available while offline — 'off' is this sensor's payload."""
        return self.coordinator.last_update_success and self.device_data is not None

    @property
    def is_on(self) -> bool | None:
        data = self.device_data
        return data.online if data else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        data = self.device_data
        if not data or not data.presence:
            return {}
        return {"firmware": data.presence.fw, "last_seen_ts": data.presence.ts}


class SpotBotCameraConnectivitySensor(SpotBotEntity, BinarySensorEntity):
    """Whether a camera is connected to its SpotBot (cam_status.conn_status).

    conn_status is a fault code — 0 "Fine", 1 warning, 2 error/video off,
    anything else unknown — so only 0 counts as connected. The code itself
    is exposed as an attribute, since "warning" and "error" are different
    problems and the binary sensor flattens both to off.
    """

    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_translation_key = KEY_CAMERA_CONNECTIVITY

    def __init__(self, coordinator: SpotBotCoordinator, serial: str, cam_nr: str) -> None:
        super().__init__(coordinator, serial, KEY_CAMERA_CONNECTIVITY, cam_nr)
        cam = self.camera
        self._attr_translation_placeholders = {
            "camera": cam.name if cam and cam.name else f"Camera {cam_nr}"
        }

    @property
    def is_on(self) -> bool | None:
        cam = self.camera
        return cam.connected if cam else None

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        cam = self.camera
        if cam is None:
            return None
        return {
            "conn_status": cam.conn_status,
            "conn_status_text": CONN_STATUS_TEXT.get(cam.conn_status, "unknown"),
        }
