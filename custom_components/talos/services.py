"""Services.

`export_report` writes the same self-contained report the CLI produces, from
inside Home Assistant. The default target is `config/talos/`, deliberately not
`config/www/`: that directory is served at `/local/` without authentication,
and this report is a map of the house. Writing there is allowed, some people
want it, but it says so out loud in the log.
"""

from __future__ import annotations

import logging
from pathlib import Path

import voluptuous as vol
from homeassistant.core import HomeAssistant, ServiceCall, ServiceResponse, SupportsResponse, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN, STORAGE_DIR
from .core import render_html, render_json
from .coordinator import TalosCoordinator

_LOGGER = logging.getLogger(__name__)

SERVICE_EXPORT_REPORT = "export_report"
SERVICE_REFRESH = "refresh"

DEFAULT_NAMES = {"html": "report.html", "json": "report.json"}

EXPORT_SCHEMA = vol.Schema(
    {
        vol.Optional("path"): cv.string,
        vol.Optional("format", default="html"): vol.In(("html", "json")),
    }
)

_REGISTERED = f"{DOMAIN}_services_registered"


@callback
def async_register(hass: HomeAssistant) -> None:
    if hass.services.has_service(DOMAIN, SERVICE_EXPORT_REPORT):
        return

    async def export_report(call: ServiceCall) -> ServiceResponse:
        coordinator = _coordinator(hass)
        data = coordinator.data
        if data is None:
            raise HomeAssistantError("Talos has not completed a scan yet")

        fmt = call.data.get("format", "html")
        target = _resolve(hass, call.data.get("path"), fmt)

        # Rendering walks every conduit and the whole check report: executor.
        def write() -> int:
            body = (
                render_json(data.scan, data.derived)
                if fmt == "json"
                else render_html(data.scan, data.derived)
            )
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(body, encoding="utf-8")
            return len(body)

        size = await hass.async_add_executor_job(write)
        _LOGGER.info("Talos: report written to %s (%d bytes)", target, size)

        return {
            "path": str(target),
            "format": fmt,
            "bytes": size,
            "findings_high": data.derived.checks.counts["failed_high"],
            "unverified": data.derived.checks.counts["unverified"],
        }

    async def refresh(call: ServiceCall) -> None:
        await _coordinator(hass).async_request_refresh()

    hass.services.async_register(
        DOMAIN,
        SERVICE_EXPORT_REPORT,
        export_report,
        schema=EXPORT_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )
    hass.services.async_register(DOMAIN, SERVICE_REFRESH, refresh)
    hass.data[_REGISTERED] = True


@callback
def async_unregister(hass: HomeAssistant) -> None:
    for service in (SERVICE_EXPORT_REPORT, SERVICE_REFRESH):
        hass.services.async_remove(DOMAIN, service)
    hass.data.pop(_REGISTERED, None)


def _coordinator(hass: HomeAssistant) -> TalosCoordinator:
    for value in (hass.data.get(DOMAIN) or {}).values():
        if isinstance(value, TalosCoordinator):
            return value
    raise HomeAssistantError("Talos is not configured")


def _resolve(hass: HomeAssistant, raw: str | None, fmt: str) -> Path:
    """Resolve the target inside the configuration directory, and only there."""
    default = Path(hass.config.path(STORAGE_DIR)) / DEFAULT_NAMES[fmt]
    if not raw:
        return default

    candidate = Path(raw)
    if not candidate.is_absolute():
        candidate = Path(hass.config.path(raw))
    candidate = candidate.resolve()

    root = Path(hass.config.config_dir).resolve()
    if root not in candidate.parents:
        raise HomeAssistantError(
            f"{candidate} is outside the configuration directory: refused"
        )
    if not hass.config.is_allowed_path(str(candidate.parent)):
        raise HomeAssistantError(
            f"{candidate.parent} is not among the allowed paths"
            " (allowlist_external_dirs)"
        )
    if (root / "www").resolve() in (candidate, *candidate.parents):
        # Not refused: some people want it. But /local/ is served without
        # authentication, and this file maps the whole house.
        _LOGGER.warning(
            "Talos: %s lands under config/www, which Home Assistant serves at"
            " /local/ without authentication. The report lists addresses, MACs"
            " and network topology.",
            candidate,
        )
    return candidate
