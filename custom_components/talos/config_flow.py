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
    OPTION_BOUNDS,
)
from .core import ObservedAuthError, ObservedError, RetentionPolicy
from .discovery import (
    STATUS_PATH,
    Candidate,
    async_probe,
    candidates_from_adguard_entries,
    deduplicate,
    fallback_candidates,
)
from .http_transport import HassHttpTransport

_LOGGER = logging.getLogger(__name__)

# Short, because the flow waits on it and most candidates are misses.
PROBE_TIMEOUT = 2.5

def _connection_schema(current: dict[str, Any] | None = None) -> vol.Schema:
    """The AdGuard endpoint, pre-filled when reconfiguring."""
    current = current or {}
    return vol.Schema(
        {
            vol.Optional(
                CONF_ADGUARD_URL, default=current.get(CONF_ADGUARD_URL, "")
            ): TextSelector(TextSelectorConfig(type=TextSelectorType.URL)),
            vol.Optional(
                CONF_ADGUARD_USERNAME, default=current.get(CONF_ADGUARD_USERNAME, "")
            ): str,
            vol.Optional(
                CONF_ADGUARD_PASSWORD, default=current.get(CONF_ADGUARD_PASSWORD, "")
            ): TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD)),
            vol.Optional(
                CONF_VERIFY_SSL, default=current.get(CONF_VERIFY_SSL, True)
            ): bool,
        }
    )


def _as_input(candidate: Candidate) -> dict[str, Any]:
    """A discovered endpoint, shaped like the form that will show it."""
    return {
        CONF_ADGUARD_URL: candidate.url,
        CONF_ADGUARD_USERNAME: candidate.username,
        CONF_ADGUARD_PASSWORD: candidate.password,
        CONF_VERIFY_SSL: candidate.verify_ssl,
    }


def _bounded(option: str, unit: str | None = None) -> NumberSelector:
    """A box bounded by OPTION_BOUNDS, so the flow and the panel agree."""
    minimum, maximum = OPTION_BOUNDS[option]
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

        if user_input is not None:
            return await self._async_submit("user", user_input)

        # Look before asking. Whatever turns up is put in the form where it
        # can be seen and changed, never used silently.
        found = await self._async_discover()
        if found is not None:
            self._discovered = found
            return self.async_show_form(
                step_id="discovered",
                data_schema=_connection_schema(_as_input(found)),
                description_placeholders={"url": found.url},
            )

        return self.async_show_form(step_id="user", data_schema=_connection_schema())

    async def async_step_discovered(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """The same form as `user`, reached when an endpoint was found."""
        if user_input is None:
            found = getattr(self, "_discovered", None)
            return self.async_show_form(
                step_id="discovered",
                data_schema=_connection_schema(_as_input(found) if found else None),
                description_placeholders={"url": found.url if found else ""},
            )
        return await self._async_submit("discovered", user_input)

    async def _async_submit(self, step_id: str, user_input: dict[str, Any]) -> ConfigFlowResult:
        url = (user_input.get(CONF_ADGUARD_URL) or "").strip()
        if url:
            error = await self._test_adguard(user_input, url)
            if error:
                found = getattr(self, "_discovered", None)
                return self.async_show_form(
                    step_id=step_id,
                    data_schema=_connection_schema(user_input),
                    errors={"base": error},
                    description_placeholders={"url": found.url if found else ""},
                )
        return self.async_create_entry(
            title="Talos",
            data={**user_input, CONF_ADGUARD_URL: url},
            options={CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL},
        )

    async def _async_discover(self) -> Candidate | None:
        """Ask the places that already know: the AdGuard integration first,
        then the add-on hostname and the address Home Assistant knows itself
        by. A candidate counts only once /control/status has answered."""
        entries = [
            dict(entry.data) for entry in self.hass.config_entries.async_entries("adguard")
        ]
        candidates = deduplicate(
            [
                *candidates_from_adguard_entries(entries),
                *fallback_candidates(self.hass.config.internal_url),
            ]
        )

        async def check(candidate: Candidate) -> str | None:
            transport = HassHttpTransport(
                self.hass,
                candidate.url,
                candidate.username,
                candidate.password,
                candidate.verify_ssl,
                timeout=PROBE_TIMEOUT,
            )
            try:
                await transport.get_json(STATUS_PATH)
            except ObservedAuthError:
                # The address is right, the credentials are not ours to guess.
                return "auth"
            except Exception:  # noqa: BLE001 - any failure just means "not here"
                return None
            return "ok"

        try:
            return await async_probe(check, candidates)
        except Exception:  # noqa: BLE001 - discovery must never block setup
            _LOGGER.debug("AdGuard discovery failed", exc_info=True)
            return None

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Change the AdGuard endpoint after setup.

        Without this the endpoint could only be set while adding the
        integration: anyone who set Talos up before knowing the address had to
        delete the entry and start over.
        """
        entry = self._reconfigure_entry()

        # An entry created before the address was known has nothing to
        # pre-fill, so this is exactly where discovery earns its keep.
        if user_input is None and not entry.data.get(CONF_ADGUARD_URL):
            found = await self._async_discover()
            if found is not None:
                return self.async_show_form(
                    step_id="reconfigure", data_schema=_connection_schema(_as_input(found))
                )

        errors: dict[str, str] = {}
        if user_input is not None:
            url = (user_input.get(CONF_ADGUARD_URL) or "").strip()
            if url:
                error = await self._test_adguard(user_input, url)
                if error:
                    errors["base"] = error
            if not errors:
                return self.async_update_reload_and_abort(
                    entry, data_updates={**user_input, CONF_ADGUARD_URL: url}
                )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=_connection_schema(user_input or dict(entry.data)),
            errors=errors,
        )

    def _reconfigure_entry(self) -> ConfigEntry:
        # _get_reconfigure_entry landed in 2024.11; fall back to the context.
        getter = getattr(self, "_get_reconfigure_entry", None)
        if getter is not None:
            return getter()
        entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
        assert entry is not None
        return entry

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
            _LOGGER.exception("AdGuard check failed unexpectedly")
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
                ): _bounded(CONF_SCAN_INTERVAL, "min"),
                vol.Required(
                    CONF_OBSERVATION_DAYS,
                    default=options.get(CONF_OBSERVATION_DAYS, default.observation_days),
                ): _bounded(CONF_OBSERVATION_DAYS, "d"),
                vol.Required(
                    CONF_MAX_OBSERVATIONS,
                    default=options.get(CONF_MAX_OBSERVATIONS, default.max_observations),
                ): _bounded(CONF_MAX_OBSERVATIONS),
                vol.Required(
                    CONF_SCAN_HISTORY,
                    default=options.get(CONF_SCAN_HISTORY, default.scan_history),
                ): _bounded(CONF_SCAN_HISTORY),
                vol.Required(
                    CONF_PAGE_SIZE,
                    default=options.get(CONF_PAGE_SIZE, DEFAULT_PAGE_SIZE),
                ): _bounded(CONF_PAGE_SIZE),
                vol.Required(
                    CONF_MAX_PAGES,
                    default=options.get(CONF_MAX_PAGES, DEFAULT_MAX_PAGES),
                ): _bounded(CONF_MAX_PAGES),
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
