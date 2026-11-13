"""Config flow: one entry per location, defaulting to the HA home location."""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_LATITUDE, CONF_LOCATION, CONF_LONGITUDE, CONF_NAME
from homeassistant.helpers.selector import LocationSelector, LocationSelectorConfig, TextSelector

from .const import DEFAULT_NAME, DOMAIN


def _schema(name: str | None, latitude: float, longitude: float) -> vol.Schema:
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
        if user_input is not None:
            lat = user_input[CONF_LOCATION][CONF_LATITUDE]
            lon = user_input[CONF_LOCATION][CONF_LONGITUDE]
            await self.async_set_unique_id(_location_id(lat, lon))
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=user_input[CONF_NAME],
                data={CONF_LATITUDE: lat, CONF_LONGITUDE: lon},
            )
        name = DEFAULT_NAME if not self._async_current_entries() else ""
        return self.async_show_form(
            step_id="user",
            data_schema=_schema(name, self.hass.config.latitude, self.hass.config.longitude),
        )

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        entry = self._get_reconfigure_entry()
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
            data_schema=_schema(None, entry.data[CONF_LATITUDE], entry.data[CONF_LONGITUDE]),
        )
