"""Config flow: a map location (any number) or the Earth's centre (one)."""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_LATITUDE, CONF_LOCATION, CONF_LONGITUDE, CONF_NAME
from homeassistant.helpers.selector import LocationSelector, LocationSelectorConfig, TextSelector

from .const import (
    CONF_GEOCENTRIC,
    DEFAULT_GEOCENTRIC_NAME,
    DEFAULT_NAME,
    DOMAIN,
    GEOCENTRIC_UNIQUE_ID,
)


def _location_schema(name: str | None, latitude: float, longitude: float) -> vol.Schema:
    fields: dict = {}
    if name is not None:
        fields[vol.Required(CONF_NAME, default=name)] = TextSelector()
    fields[vol.Required(CONF_LOCATION, default={CONF_LATITUDE: latitude, CONF_LONGITUDE: longitude})] = (
        LocationSelector(LocationSelectorConfig(radius=False))
    )
    return vol.Schema(fields)


def _location_id(latitude: float, longitude: float) -> str:
    return f"{latitude:.4f}_{longitude:.4f}"


class LunaeConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        return self.async_show_menu(step_id="user", menu_options=["location", "geocentric"])

    async def async_step_location(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            lat = user_input[CONF_LOCATION][CONF_LATITUDE]
            lon = user_input[CONF_LOCATION][CONF_LONGITUDE]
            await self.async_set_unique_id(_location_id(lat, lon))
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=user_input[CONF_NAME],
                data={CONF_LATITUDE: lat, CONF_LONGITUDE: lon},
            )
        has_location_entry = any(
            not e.data.get(CONF_GEOCENTRIC) for e in self._async_current_entries()
        )
        return self.async_show_form(
            step_id="location",
            data_schema=_location_schema(
                "" if has_location_entry else DEFAULT_NAME,
                self.hass.config.latitude,
                self.hass.config.longitude,
            ),
        )

    async def async_step_geocentric(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        await self.async_set_unique_id(GEOCENTRIC_UNIQUE_ID)
        self._abort_if_unique_id_configured()
        if user_input is not None:
            return self.async_create_entry(
                title=user_input[CONF_NAME], data={CONF_GEOCENTRIC: True}
            )
        return self.async_show_form(
            step_id="geocentric",
            data_schema=vol.Schema(
                {vol.Required(CONF_NAME, default=DEFAULT_GEOCENTRIC_NAME): TextSelector()}
            ),
        )

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        entry = self._get_reconfigure_entry()
        if entry.data.get(CONF_GEOCENTRIC):
            return self.async_abort(reason="geocentric_no_location")
        if user_input is not None:
            lat = user_input[CONF_LOCATION][CONF_LATITUDE]
            lon = user_input[CONF_LOCATION][CONF_LONGITUDE]
            await self.async_set_unique_id(_location_id(lat, lon))
            if entry.unique_id != self.unique_id:
                self._abort_if_unique_id_configured()
            return self.async_update_reload_and_abort(
                entry,
                unique_id=self.unique_id,
                data={CONF_LATITUDE: lat, CONF_LONGITUDE: lon},
            )
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=_location_schema(None, entry.data[CONF_LATITUDE], entry.data[CONF_LONGITUDE]),
        )
