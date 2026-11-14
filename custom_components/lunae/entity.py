"""Base entity: one device per config entry (location)."""
from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import LunaeCoordinator


class LunaeEntity(CoordinatorEntity[LunaeCoordinator]):
    _attr_has_entity_name = True

    def __init__(self, coordinator: LunaeCoordinator, description: EntityDescription) -> None:
        super().__init__(coordinator)
        entry = coordinator.config_entry
        self.entity_description = description
        # Horizon-dependent values don't exist at the Earth's centre: create the
        # entities (so the device looks the same) but disable them by default.
        if coordinator.geocentric and getattr(description, "needs_horizon", False):
            self._attr_entity_registry_enabled_default = False
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            entry_type=DeviceEntryType.SERVICE,
        )
