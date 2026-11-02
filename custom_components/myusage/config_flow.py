"""Config flow for MyUsage integration."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import ConfigEntryAuthFailed

from .const import DOMAIN, CONF_EMAIL, CONF_PASSWORD
from .coordinator import _fetch_myusage_data

STEP_USER_DATA_SCHEMA = vol.Schema({
    vol.Required(CONF_EMAIL):    str,
    vol.Required(CONF_PASSWORD): str,
})

STEP_REAUTH_DATA_SCHEMA = vol.Schema({
    vol.Required(CONF_PASSWORD): str,
})


class MyUsageConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the MyUsage config flow."""

    VERSION = 1

    async def _async_validate(self, email: str, password: str) -> str | None:
        """Try a real login and fetch; return an error key, or None on success."""
        try:
            await self.hass.async_add_executor_job(
                _fetch_myusage_data, email, password
            )
        except ConfigEntryAuthFailed:
            return "invalid_auth"
        except Exception:
            return "cannot_connect"
        return None

    async def async_step_user(self, user_input: dict | None = None) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            email    = user_input[CONF_EMAIL].strip()
            password = user_input[CONF_PASSWORD]

            if error := await self._async_validate(email, password):
                errors["base"] = error
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

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> FlowResult:
        """Start reauth when the stored credentials stop working."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict | None = None
    ) -> FlowResult:
        """Ask for the new password, validate it and update the entry."""
        errors: dict[str, str] = {}
        entry = self._get_reauth_entry()
        email = entry.data[CONF_EMAIL]

        if user_input is not None:
            password = user_input[CONF_PASSWORD]
            if error := await self._async_validate(email, password):
                errors["base"] = error
            else:
                return self.async_update_reload_and_abort(
                    entry, data_updates={CONF_PASSWORD: password}
                )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=STEP_REAUTH_DATA_SCHEMA,
            description_placeholders={"email": email},
            errors=errors,
        )
