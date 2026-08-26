"""Base entity for the SpotBot integration."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import SpotBotCamera, SpotBotDeviceData
from .const import DOMAIN, MANUFACTURER, MODEL
from .coordinator import SpotBotCoordinator


class SpotBotEntity(CoordinatorEntity[SpotBotCoordinator]):
    """Common base: one HA device per SpotBot serial."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: SpotBotCoordinator,
        serial: str,
        key: str,
        cam_nr: str | None = None,
    ) -> None:
        super().__init__(coordinator)
        self._serial = serial
        self._cam_nr = cam_nr
        self._attr_unique_id = f"{serial}_{key}" + (f"_cam{cam_nr}" if cam_nr else "")
        data = self.device_data
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, serial)},
            name=data.device.display_name if data else serial,
            manufacturer=MANUFACTURER,
            model=MODEL,
            serial_number=serial,
            sw_version=(data.status.sw_version if data and data.status else None),
        )

    @property
    def device_data(self) -> SpotBotDeviceData | None:
        return (self.coordinator.data or {}).get(self._serial)

    @property
    def camera(self) -> SpotBotCamera | None:
        """The cam_status entry this entity is bound to, if any."""
        data = self.device_data
        if not data or not data.status or self._cam_nr is None:
            return None
        for cam in data.status.cameras:
            if cam.cam_nr == self._cam_nr:
                return cam
        return None

    @property
    def available(self) -> bool:
        """Unavailable while the device is offline (504 territory)."""
        data = self.device_data
        return super().available and data is not None and data.online
