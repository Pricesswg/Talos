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
    CONF_AUTO_RETENTION,
    CONF_CHECK_RULES,
    CONF_DOMAIN_RULES,
    CONF_MAX_OBSERVATIONS,
    CONF_MAX_PAGES,
    CONF_MQTT_HOST,
    CONF_MQTT_PASSWORD,
    CONF_MQTT_PORT,
    CONF_MQTT_TLS,
    CONF_MQTT_USERNAME,
    CONF_OBSERVATION_DAYS,
    CONF_PAGE_SIZE,
    CONF_RETENTION_DAYS,
    CONF_SCAN_HISTORY,
    CONF_SCAN_INTERVAL,
    CONF_VERIFY_SSL,
    DEFAULT_MQTT_PORT,
    DEFAULT_RETENTION_DAYS,
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
from .mqtt_source import NO_CLIENT_IDS

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
            # A read-only account on the broker. Optional throughout: without
            # it Talos falls back to the session Home Assistant already holds,
            # which works until the broker restricts $SYS, and most do.
            vol.Optional(CONF_MQTT_HOST, default=current.get(CONF_MQTT_HOST, "")): str,
            vol.Optional(
                CONF_MQTT_PORT, default=current.get(CONF_MQTT_PORT, DEFAULT_MQTT_PORT)
            ): NumberSelector(
                NumberSelectorConfig(min=1, max=65535, step=1, mode=NumberSelectorMode.BOX)
            ),
            vol.Optional(CONF_MQTT_USERNAME, default=current.get(CONF_MQTT_USERNAME, "")): str,
            vol.Optional(
                CONF_MQTT_PASSWORD, default=current.get(CONF_MQTT_PASSWORD, "")
            ): TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD)),
            vol.Optional(CONF_MQTT_TLS, default=current.get(CONF_MQTT_TLS, False)): bool,
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
        data, error = await self._validated(user_input)
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
            data=data,
            options={CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL},
        )

    async def _validated(self, user_input: dict[str, Any]) -> tuple[dict[str, Any], str | None]:
        """Clean the form and try both endpoints. Neither is required, and a
        broker that will not answer is reported here rather than every fifteen
        minutes in the log."""
        data = {**user_input}
        data[CONF_ADGUARD_URL] = (user_input.get(CONF_ADGUARD_URL) or "").strip()
        data[CONF_MQTT_HOST] = (user_input.get(CONF_MQTT_HOST) or "").strip()
        # A NumberSelector hands back a float, and a port is not a float.
        data[CONF_MQTT_PORT] = int(user_input.get(CONF_MQTT_PORT) or DEFAULT_MQTT_PORT)

        if data[CONF_ADGUARD_URL]:
            error = await self._test_adguard(user_input, data[CONF_ADGUARD_URL])
            if error:
                return data, error
        if data[CONF_MQTT_HOST]:
            error = await self._test_mqtt(data)
            if error:
                return data, error
        return data, None

    async def _test_mqtt(self, data: dict[str, Any]) -> str | None:
        """Connect once with the account given, and say so if it will not.

        Reaching the broker is what is checked. Whether $SYS answers is a
        separate question the scan reports on its own, because an account that
        connects but cannot read the tree is a working configuration with a
        limit, not a rejected form.
        """
        from .mqtt_source import read_sys_blocking

        _found, error = await self.hass.async_add_executor_job(
            read_sys_blocking,
            data[CONF_MQTT_HOST],
            data[CONF_MQTT_PORT],
            data.get(CONF_MQTT_USERNAME) or "",
            data.get(CONF_MQTT_PASSWORD) or "",
            bool(data.get(CONF_MQTT_TLS)),
            1.5,
        )
        if not error:
            return None
        if "refused" in error or "not authorised" in error.lower():
            return "mqtt_invalid_auth"
        # No client id is not a connection failure: the account works, the
        # broker simply keeps $SYS to itself. Saving that is correct.
        if error == NO_CLIENT_IDS:
            return None
        return "mqtt_cannot_connect"

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
            data, error = await self._validated(user_input)
            if error:
                errors["base"] = error
            else:
                return self.async_update_reload_and_abort(entry, data_updates=data)

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
                    CONF_RETENTION_DAYS,
                    default=options.get(CONF_RETENTION_DAYS, DEFAULT_RETENTION_DAYS),
                ): _bounded(CONF_RETENTION_DAYS, "d"),
                vol.Required(
                    CONF_AUTO_RETENTION, default=options.get(CONF_AUTO_RETENTION, True)
                ): bool,
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
