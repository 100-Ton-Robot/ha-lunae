"""Lunae sensors."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import DEGREE, PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import LunaeConfigEntry, astro
from .entity import LunaeEntity


@dataclass(frozen=True, kw_only=True)
class LunaeSensorDescription(SensorEntityDescription):
    value_fn: Callable[[astro.MoonState], float | str | datetime | None]
    has_limits: bool = False
    needs_horizon: bool = False


SENSORS: tuple[LunaeSensorDescription, ...] = (
    LunaeSensorDescription(
        key="azimuth",
        needs_horizon=True,
        translation_key="azimuth",
        native_unit_of_measurement=DEGREE,
        state_class=SensorStateClass.MEASUREMENT_ANGLE,
        suggested_display_precision=1,
        value_fn=lambda s: s.azimuth,
    ),
    LunaeSensorDescription(
        key="elevation",
        needs_horizon=True,
        translation_key="elevation",
        native_unit_of_measurement=DEGREE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda s: s.elevation,
    ),
    LunaeSensorDescription(
        key="illumination",
        translation_key="illumination",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda s: s.illumination,
    ),
    LunaeSensorDescription(
        key="phase",
        translation_key="phase",
        device_class=SensorDeviceClass.ENUM,
        options=astro.PHASES,
        value_fn=lambda s: s.phase,
    ),
    LunaeSensorDescription(
        key="angular_size",
        translation_key="angular_size",
        native_unit_of_measurement=DEGREE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=3,
        value_fn=lambda s: s.angular_size,
        has_limits=True,
    ),
    LunaeSensorDescription(
        key="next_rising",
        needs_horizon=True,
        translation_key="next_rising",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda s: s.next_rising,
    ),
    LunaeSensorDescription(
        key="next_setting",
        needs_horizon=True,
        translation_key="next_setting",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda s: s.next_setting,
    ),
    LunaeSensorDescription(
        key="next_full_moon",
        translation_key="next_full_moon",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda s: s.next_full_moon,
    ),
    LunaeSensorDescription(
        key="next_new_moon",
        translation_key="next_new_moon",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda s: s.next_new_moon,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: LunaeConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    async_add_entities(LunaeSensor(entry.runtime_data, desc) for desc in SENSORS)


class LunaeSensor(LunaeEntity, SensorEntity):
    entity_description: LunaeSensorDescription
    # Constant limits: keep them out of the recorder's attribute history.
    _unrecorded_attributes = frozenset({"min", "max"})

    @property
    def native_value(self):
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict | None:
        if not self.entity_description.has_limits:
            return None
        if self.coordinator.geocentric:
            return {"min": astro.GEO_ANGULAR_SIZE_MIN, "max": astro.GEO_ANGULAR_SIZE_MAX}
        return {"min": astro.ANGULAR_SIZE_MIN, "max": astro.ANGULAR_SIZE_MAX}
