"""Lunae binary sensor: Moon above the horizon."""
from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import LunaeConfigEntry
from .entity import LunaeEntity

@dataclass(frozen=True, kw_only=True)
class LunaeBinarySensorDescription(BinarySensorEntityDescription):
    needs_horizon: bool = False


ABOVE_HORIZON = LunaeBinarySensorDescription(
    key="above_horizon", translation_key="above_horizon", needs_horizon=True
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: LunaeConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    async_add_entities([LunaeAboveHorizon(entry.runtime_data, ABOVE_HORIZON)])


class LunaeAboveHorizon(LunaeEntity, BinarySensorEntity):
    @property
    def is_on(self) -> bool | None:
        return self.coordinator.data.above_horizon
