"""Config flow for MyUsage integration."""
from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN, CONF_EMAIL, CONF_PASSWORD
from .coordinator import _fetch_myusage_data

STEP_USER_DATA_SCHEMA = vol.Schema({
    vol.Required(CONF_EMAIL):    str,
    vol.Required(CONF_PASSWORD): str,
})


class MyUsageConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the MyUsage config flow."""

    VERSION = 1

    async def async_step_user(self, user_input: dict | None = None) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            email    = user_input[CONF_EMAIL].strip()
            password = user_input[CONF_PASSWORD]

            # Validate credentials by attempting a real fetch
            try:
                data = await self.hass.async_add_executor_job(
                    _fetch_myusage_data, email, password
                )
            except Exception:
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(email.lower())
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"MyUsage ({email})",
                    data={CONF_EMAIL: email, CONF_PASSWORD: password},
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )
