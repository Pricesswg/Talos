"""The polling coordinator.

Everything blocking happens in the executor: the SQLite store, the mapping
walk over the registries, the derivations. The query log is paginated and can
be long, so nothing here may sit on the event loop.

A scan is always produced, even when the observed side fails. Losing AdGuard
must degrade the report to `declared` only, with a note saying so, never
leave the panel showing yesterday's numbers as if they were today's.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import timedelta
from pathlib import Path
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_ADGUARD_PASSWORD,
    CONF_ADGUARD_URL,
    CONF_ADGUARD_USERNAME,
    CONF_MQTT_API_KEY,
    CONF_MQTT_API_SECRET,
    CONF_MQTT_API_URL,
    CONF_MQTT_HOST,
    CONF_MQTT_PASSWORD,
    CONF_MQTT_PORT,
    CONF_MQTT_TLS,
    CONF_MQTT_USERNAME,
    DEFAULT_MQTT_PORT,
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
    STORAGE_DIR,
    STORAGE_FILE,
)
from .core import (
    AdGuardCollector,
    CheckEngine,
    Derived,
    DomainClassifier,
    ObservedAuthError,
    ObservedError,
    RetentionPolicy,
    Scan,
    TalosStore,
    UnverifiedCheck,
    ZoneMap,
    derive,
    merge_observed,
)
from .http_transport import HassHttpTransport
from .core import DiagnosticRun, apply_mesh_roles
from .mqtt_source import collect_mqtt, collect_zigbee
from .native_source import NativeSource

_LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class TalosData:
    """One complete run, ready for the panel and the entities."""

    scan: Scan
    derived: Derived
    store_stats: dict[str, Any] = field(default_factory=dict)
    retention: dict[str, Any] = field(default_factory=dict)
    observed_available: bool = False
    observed_error: str | None = None


class TalosCoordinator(DataUpdateCoordinator[TalosData]):
    """Collects, joins, derives and persists on a fixed interval."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.entry = entry
        self._store: TalosStore | None = None
        self._classifier: DomainClassifier | None = None
        self._engine: CheckEngine | None = None
        self._zones = ZoneMap()

        self._setup_state: tuple[Any, ...] | None = None
        # The last diagnostic run. Never persisted: it is a measurement taken
        # at a moment, and the moment is part of what it says.
        self.last_diagnostics: DiagnosticRun | None = None
        self.diagnostics_running: bool = False

        minutes = int(entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL))
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=minutes),
        )
        self.remember_setup(entry)

    # ── setup ─────────────────────────────────────────────────────────────

    @property
    def database_path(self) -> Path:
        return Path(self.hass.config.path(STORAGE_DIR)) / STORAGE_FILE

    def retention_policy(self) -> RetentionPolicy:
        options = self.entry.options
        default = RetentionPolicy()
        return RetentionPolicy(
            observation_days=int(options.get(CONF_OBSERVATION_DAYS, default.observation_days)),
            max_observations=int(options.get(CONF_MAX_OBSERVATIONS, default.max_observations)),
            scan_history=int(options.get(CONF_SCAN_HISTORY, default.scan_history)),
            vacuum_every=default.vacuum_every,
        )

    async def async_prepare(self) -> None:
        """Open the store and load the domain rules. Both touch the disk."""
        policy = self.retention_policy()
        path = self.database_path
        self._store = await self.hass.async_add_executor_job(
            lambda: TalosStore(path, policy)
        )

        rules_path = self.entry.options.get(CONF_DOMAIN_RULES)
        self._classifier = await self.hass.async_add_executor_job(
            self._load_classifier, rules_path
        )
        self._engine = await self.hass.async_add_executor_job(
            self._load_engine, self.entry.options.get(CONF_CHECK_RULES)
        )
        self._zones = ZoneMap.from_dict(
            {
                "trusted_lan": self.entry.options.get(CONF_ZONE_TRUSTED, ""),
                "iot_vlan": self.entry.options.get(CONF_ZONE_IOT, ""),
                "guest": self.entry.options.get(CONF_ZONE_GUEST, ""),
            }
        )

    def _load_classifier(self, rules_path: str | None) -> DomainClassifier:
        classifier = DomainClassifier.load()
        if not rules_path:
            return classifier
        try:
            extra = DomainClassifier.load(rules_path)
        except Exception as err:  # noqa: BLE001 - a bad user file must not stop the scan
            _LOGGER.warning("Custom domain list not loaded (%s): %s", rules_path, err)
            return classifier
        # The user's rules layer on top of the shipped ones, never replace them.
        return classifier.merged_with(extra)

    def _load_engine(self, rules_path: str | None) -> CheckEngine:
        if not rules_path:
            return CheckEngine.load()
        try:
            return CheckEngine.load(rules_path)
        except Exception as err:  # noqa: BLE001 - a bad user file must not stop the scan
            _LOGGER.warning("Custom check rules not loaded (%s): %s", rules_path, err)
            return CheckEngine.load()

    async def async_shutdown_store(self) -> None:
        if self._store is not None:
            store = self._store
            self._store = None
            await self.hass.async_add_executor_job(store.close)

    # ── the run ───────────────────────────────────────────────────────────

    # What is read once at setup and therefore only changes on a reload. The
    # broker account is deliberately absent: it is read on every scan.
    RELOAD_KEYS: tuple[str, ...] = (
        CONF_ADGUARD_URL,
        CONF_ADGUARD_USERNAME,
        CONF_ADGUARD_PASSWORD,
        CONF_VERIFY_SSL,
    )

    def remember_setup(self, entry: ConfigEntry | None = None) -> None:
        """Snapshot the values a reload would be needed to pick up."""
        entry = entry or self.entry
        self.entry = entry
        self._setup_state = self._setup_snapshot(entry)

    def _setup_snapshot(self, entry: ConfigEntry) -> tuple[Any, ...]:
        return (
            tuple(sorted(entry.options.items())),
            tuple(entry.data.get(key) for key in self.RELOAD_KEYS),
        )

    def needs_reload(self, entry: ConfigEntry) -> bool:
        """Whether the change that just landed is one a reload is for."""
        if self._setup_state is None:
            return True
        return self._setup_snapshot(entry) != self._setup_state

    def _device_identifiers(self) -> dict[str, list[str]]:
        """Device id to the identifier values the registry holds for it.

        The scan drops identifiers once it has read what it needed from them,
        and the IEEE address is only ever in there, so the join needs the
        registry a second time. It is an in-memory read.
        """
        from homeassistant.helpers import device_registry

        return {
            device.id: [str(pair[1]) for pair in device.identifiers if len(pair) >= 2]
            for device in device_registry.async_get(self.hass).devices.values()
        }

    def _mqtt_api(self) -> dict[str, Any] | None:
        """The EMQX API, if one is configured. Preferred where it exists."""
        data = self.entry.data
        url = str(data.get(CONF_MQTT_API_URL) or "").strip()
        if not url:
            return None
        return {
            "url": url,
            "key": data.get(CONF_MQTT_API_KEY) or "",
            "secret": data.get(CONF_MQTT_API_SECRET) or "",
            "verify_ssl": bool(data.get(CONF_VERIFY_SSL, True)),
        }

    def _mqtt_credentials(self, scan: Scan | None = None) -> dict[str, Any] | None:
        """The read-only account, if one is configured.

        The address is optional: when only a user and a password are given,
        the broker is the one the MQTT config entry already names, so the
        common case is two fields instead of four.
        """
        data = self.entry.data
        if not (data.get(CONF_MQTT_USERNAME) or data.get(CONF_MQTT_HOST)):
            return None
        host = str(data.get(CONF_MQTT_HOST) or "").strip()
        port = int(data.get(CONF_MQTT_PORT) or DEFAULT_MQTT_PORT)
        if not host and scan is not None:
            for conduit in scan.conduits:
                integration = scan.integration(conduit.source.id)
                if conduit.evidence != "declared" or integration is None:
                    continue
                if integration.domain != "mqtt":
                    continue
                destination = scan.destination(conduit.destination_id)
                if destination is not None:
                    host = destination.fqdn
                    port = conduit.port or port
                    break
        if not host:
            return None
        return {
            "host": host,
            "port": port,
            "username": data.get(CONF_MQTT_USERNAME) or "",
            "password": data.get(CONF_MQTT_PASSWORD) or "",
            "tls": bool(data.get(CONF_MQTT_TLS)),
        }

    async def _async_update_data(self) -> TalosData:
        if self._store is None or self._classifier is None:
            await self.async_prepare()
        assert self._store is not None and self._classifier is not None
        store = self._store

        try:
            scan = await NativeSource(self.hass).fetch()
        except Exception as err:  # noqa: BLE001
            raise UpdateFailed(f"reading the registries failed: {err}") from err

        observed_available = False
        observed_error: str | None = None
        url = self.entry.data.get(CONF_ADGUARD_URL)

        if url:
            try:
                scan = await self._merge_observed(scan, store, url)
                observed_available = True
            except ObservedAuthError as err:
                observed_error = f"AdGuard credentials rejected: {err}"
            except ObservedError as err:
                observed_error = f"AdGuard unreachable: {err}"
            except Exception as err:  # noqa: BLE001
                observed_error = f"observed collection failed: {err}"

            if observed_error:
                # Say it in the report, not only in the log: a scan that
                # silently lost half its evidence reads like a clean one.
                _LOGGER.warning("Talos: %s", observed_error)
                scan.unverified.append(
                    UnverifiedCheck(
                        id="unv.observed_source_unavailable",
                        title="Observed side unavailable in this scan",
                        reason="missing_data",
                        detail=(
                            f"{observed_error}. This scan holds only what Home"
                            " Assistant declares about itself: no 'egress observed'"
                            " column has been verified, so an empty cell does not"
                            " mean an absence of traffic."
                        ),
                    )
                )

        # Only when the MQTT integration is loaded, because the whole point is
        # to reuse the session it already holds rather than open one.
        credentials = self._mqtt_credentials(scan)
        api = self._mqtt_api()
        if api or credentials or "mqtt" in self.hass.config.components:
            scan.mqtt = await collect_mqtt(self.hass, scan, credentials, api=api)

        # The Zigbee coordinator's own view, from retained topics. Nothing is
        # asked of the mesh, so this costs a subscription and no radio time.
        if "mqtt" in self.hass.config.components:
            scan.zigbee, roles = await collect_zigbee(self.hass)
            if roles:
                apply_mesh_roles(scan.devices, roles, self._device_identifiers())
            # One line per route at INFO, so the log answers "did the key
            # work" without opening the panel.
            for route in scan.mqtt.routes:
                _LOGGER.info(
                    "Talos: MQTT route %s: %s%s",
                    route.name,
                    f"{route.clients} clients" if route.ok else "no answer",
                    f" ({route.error})" if route.error else "",
                )

        derived = await self.hass.async_add_executor_job(derive, scan, self._engine)

        def persist() -> tuple[dict[str, Any], dict[str, Any]]:
            store.save_scan(scan)
            report = store.prune()
            return store.stats().to_dict(), {
                "policy": store.policy.to_dict(),
                "last_prune": {
                    "observations_expired": report.observations_expired,
                    "observations_over_cap": report.observations_over_cap,
                    "scans_removed": report.scans_removed,
                    "vacuumed": report.vacuumed,
                },
            }

        store_stats, retention = await self.hass.async_add_executor_job(persist)

        return TalosData(
            scan=scan,
            derived=derived,
            store_stats=store_stats,
            retention=retention,
            observed_available=observed_available,
            observed_error=observed_error,
        )

    async def _merge_observed(self, scan: Scan, store: TalosStore, url: str) -> Scan:
        transport = HassHttpTransport(
            self.hass,
            url,
            self.entry.data.get(CONF_ADGUARD_USERNAME, ""),
            self.entry.data.get(CONF_ADGUARD_PASSWORD, ""),
            bool(self.entry.data.get(CONF_VERIFY_SSL, True)),
        )
        collector = AdGuardCollector(
            transport,
            page_size=int(self.entry.options.get(CONF_PAGE_SIZE, DEFAULT_PAGE_SIZE)),
            max_pages=int(self.entry.options.get(CONF_MAX_PAGES, DEFAULT_MAX_PAGES)),
        )

        cursor, previous = await self.hass.async_add_executor_job(
            lambda: (store.get_cursor(), store.load_observations())
        )
        facts = await collector.fetch(since=cursor, previous=previous)

        # Totals are folded on our side because AdGuard's retention is limited
        # and the log rolls over; persist before deriving anything from them.
        def save() -> None:
            store.save_observations(facts.observations)
            store.save_leases(facts.leases)
            store.set_cursor(facts.cursor)

        await self.hass.async_add_executor_job(save)

        classifier = self._classifier
        assert classifier is not None
        return await self.hass.async_add_executor_job(
            merge_observed, scan, facts, classifier, self._zones
        )
