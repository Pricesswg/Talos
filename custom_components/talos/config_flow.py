"""Config and options flow.

The AdGuard endpoint and its credentials are asked for, never guessed. It
often runs on the same machine as Home Assistant and just as often does not,
and a wrong assumption here produces an empty report that looks like a clean
one.

AdGuard is optional. Without it Talos still answers the offline-autonomy
question from what Home Assistant declares; it simply cannot answer the
exposure one, and says so in the report rather than leaving it blank.
"""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .const import (
    CONF_ADGUARD_PASSWORD,
    CONF_ADGUARD_URL,
    CONF_ADGUARD_USERNAME,
    CONF_CHECK_RULES,
    CONF_DOMAIN_RULES,
    CONF_MAX_OBSERVATIONS,
    CONF_MAX_PAGES,
    CONF_OBSERVATION_DAYS,
    CONF_PAGE_SIZE,
    CONF_SCAN_HISTORY,
    CONF_SCAN_INTERVAL,
    CONF_VERIFY_SSL,
    CONF_ZONE_GUEST,
    CONF_ZONE_IOT,
    CONF_ZONE_TRUSTED,
    DEFAULT_MAX_PAGES,
    DEFAULT_PAGE_SIZE,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)
from .core import ObservedAuthError, ObservedError, RetentionPolicy
from .http_transport import HassHttpTransport

_LOGGER = logging.getLogger(__name__)

STATUS_PATH = "/control/status"

USER_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_ADGUARD_URL, default=""): TextSelector(
            TextSelectorConfig(type=TextSelectorType.URL)
        ),
        vol.Optional(CONF_ADGUARD_USERNAME, default=""): str,
        vol.Optional(CONF_ADGUARD_PASSWORD, default=""): TextSelector(
            TextSelectorConfig(type=TextSelectorType.PASSWORD)
        ),
        vol.Optional(CONF_VERIFY_SSL, default=True): bool,
    }
)


def _number(minimum: int, maximum: int, unit: str | None = None) -> NumberSelector:
    return NumberSelector(
        NumberSelectorConfig(
            min=minimum, max=maximum, step=1, mode=NumberSelectorMode.BOX, unit_of_measurement=unit
        )
    )


class TalosConfigFlow(ConfigFlow, domain=DOMAIN):
    """One instance per Home Assistant: it maps the whole house."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        errors: dict[str, str] = {}
        if user_input is not None:
            url = (user_input.get(CONF_ADGUARD_URL) or "").strip()
            if url:
                error = await self._test_adguard(user_input, url)
                if error:
                    errors["base"] = error
            if not errors:
                return self.async_create_entry(
                    title="Talos",
                    data={**user_input, CONF_ADGUARD_URL: url},
                    options={CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL},
                )

        return self.async_show_form(
            step_id="user", data_schema=USER_SCHEMA, errors=errors
        )

    async def _test_adguard(self, user_input: dict[str, Any], url: str) -> str | None:
        transport = HassHttpTransport(
            self.hass,
            url,
            user_input.get(CONF_ADGUARD_USERNAME, ""),
            user_input.get(CONF_ADGUARD_PASSWORD, ""),
            bool(user_input.get(CONF_VERIFY_SSL, True)),
        )
        try:
            await transport.get_json(STATUS_PATH)
        except ObservedAuthError:
            return "invalid_auth"
        except ObservedError:
            return "cannot_connect"
        except Exception:  # noqa: BLE001
            _LOGGER.exception("Verifica AdGuard fallita in modo inatteso")
            return "unknown"
        return None

    @staticmethod
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return TalosOptionsFlow()


class TalosOptionsFlow(OptionsFlow):
    """Polling cadence, retention and collector budget."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(
                data={key: _as_int(value) for key, value in user_input.items()}
            )

        options = self.config_entry.options
        default = RetentionPolicy()
        schema = vol.Schema(
            {
                vol.Required(
                    CONF_SCAN_INTERVAL,
                    default=options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
                ): _number(5, 1440, "min"),
                vol.Required(
                    CONF_OBSERVATION_DAYS,
                    default=options.get(CONF_OBSERVATION_DAYS, default.observation_days),
                ): _number(1, 3650, "d"),
                vol.Required(
                    CONF_MAX_OBSERVATIONS,
                    default=options.get(CONF_MAX_OBSERVATIONS, default.max_observations),
                ): _number(500, 500_000),
                vol.Required(
                    CONF_SCAN_HISTORY,
                    default=options.get(CONF_SCAN_HISTORY, default.scan_history),
                ): _number(1, 200),
                vol.Required(
                    CONF_PAGE_SIZE,
                    default=options.get(CONF_PAGE_SIZE, DEFAULT_PAGE_SIZE),
                ): _number(50, 2000),
                vol.Required(
                    CONF_MAX_PAGES,
                    default=options.get(CONF_MAX_PAGES, DEFAULT_MAX_PAGES),
                ): _number(1, 500),
                # Network zones are configuration, not something Home
                # Assistant can know. Until these are given, the checks that
                # depend on them declare themselves unrunnable.
                vol.Optional(
                    CONF_ZONE_TRUSTED, default=options.get(CONF_ZONE_TRUSTED, "")
                ): str,
                vol.Optional(CONF_ZONE_IOT, default=options.get(CONF_ZONE_IOT, "")): str,
                vol.Optional(CONF_ZONE_GUEST, default=options.get(CONF_ZONE_GUEST, "")): str,
                vol.Optional(
                    CONF_DOMAIN_RULES, default=options.get(CONF_DOMAIN_RULES, "")
                ): str,
                vol.Optional(
                    CONF_CHECK_RULES, default=options.get(CONF_CHECK_RULES, "")
                ): str,
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)


def _as_int(value: Any) -> Any:
    """Number selectors hand back floats; the retention policy wants ints."""
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value
