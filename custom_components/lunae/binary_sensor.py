"""Lunae binary sensor: Moon above the horizon."""
from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import LunaeConfigEntry
from .entity import LunaeEntity

ABOVE_HORIZON = BinarySensorEntityDescription(key="above_horizon", translation_key="above_horizon")


async def async_setup_entry(
    hass: HomeAssistant,
    entry: LunaeConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    async_add_entities([LunaeAboveHorizon(entry.runtime_data, ABOVE_HORIZON)])


class LunaeAboveHorizon(LunaeEntity, BinarySensorEntity):
    @property
    def is_on(self) -> bool:
        return self.coordinator.data.above_horizon
