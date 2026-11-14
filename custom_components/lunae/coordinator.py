"""Recompute the Moon state once a minute, off the event loop."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_LATITUDE, CONF_LONGITUDE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
import homeassistant.util.dt as dt_util

from . import astro
from .const import CONF_GEOCENTRIC, DOMAIN, UPDATE_INTERVAL

_LOGGER = logging.getLogger(__name__)


class LunaeCoordinator(DataUpdateCoordinator[astro.MoonState]):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=UPDATE_INTERVAL,
            always_update=False,
        )
        self.geocentric: bool = entry.data.get(CONF_GEOCENTRIC, False)
        self.latitude: float | None = entry.data.get(CONF_LATITUDE)
        self.longitude: float | None = entry.data.get(CONF_LONGITUDE)

    async def _async_update_data(self) -> astro.MoonState:
        if self.geocentric:
            return await self.hass.async_add_executor_job(
                astro.compute_geocentric, dt_util.utcnow()
            )
        return await self.hass.async_add_executor_job(
            astro.compute, self.latitude, self.longitude, dt_util.utcnow()
        )
