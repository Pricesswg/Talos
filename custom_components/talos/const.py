"""Constants for the Talos integration."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "talos"

# Config entry data
CONF_ADGUARD_URL: Final = "adguard_url"
CONF_ADGUARD_USERNAME: Final = "adguard_username"
CONF_ADGUARD_PASSWORD: Final = "adguard_password"
CONF_VERIFY_SSL: Final = "verify_ssl"

# A read-only account on the broker, for the one thing Home Assistant's own
# session usually cannot do: read $SYS. Most brokers restrict that tree, and
# the MQTT integration's user has no business holding the right to it.
CONF_MQTT_HOST: Final = "mqtt_host"
CONF_MQTT_PORT: Final = "mqtt_port"
CONF_MQTT_USERNAME: Final = "mqtt_username"
CONF_MQTT_PASSWORD: Final = "mqtt_password"
CONF_MQTT_TLS: Final = "mqtt_tls"
# EMQX 5 removed the per-client $SYS topics and left only gauges there, so on
# that broker the subscription can never answer. Its own API can, and it
# reports the address each client connected from, which a subscription never
# did.
CONF_MQTT_API_URL: Final = "mqtt_api_url"
CONF_MQTT_API_KEY: Final = "mqtt_api_key"
CONF_MQTT_API_SECRET: Final = "mqtt_api_secret"
DEFAULT_MQTT_PORT: Final = 1883

# Options
CONF_SCAN_INTERVAL: Final = "scan_interval_minutes"
CONF_OBSERVATION_DAYS: Final = "observation_days"
CONF_MAX_OBSERVATIONS: Final = "max_observations"
CONF_SCAN_HISTORY: Final = "scan_history"
CONF_PAGE_SIZE: Final = "page_size"
CONF_MAX_PAGES: Final = "max_pages"
CONF_DOMAIN_RULES: Final = "domain_rules_path"
CONF_CHECK_RULES: Final = "check_rules_path"
# Home Assistant cannot know which subnet is the IoT VLAN. Until these are
# given, the checks that depend on them report themselves unverifiable.
CONF_ZONE_TRUSTED: Final = "zone_trusted_lan"
CONF_ZONE_IOT: Final = "zone_iot_vlan"
CONF_ZONE_GUEST: Final = "zone_guest"

# The query log is paginated and can be long; a conservative default keeps the
# poll well clear of anything the user would notice.
DEFAULT_SCAN_INTERVAL: Final = 15
DEFAULT_PAGE_SIZE: Final = 500
DEFAULT_MAX_PAGES: Final = 40

# Bounds for the numeric options, shared by the options flow and the panel so
# the two can never disagree about what is acceptable.
OPTION_BOUNDS: Final[dict[str, tuple[int, int]]] = {
    CONF_SCAN_INTERVAL: (5, 1440),
    CONF_OBSERVATION_DAYS: (1, 3650),
    CONF_MAX_OBSERVATIONS: (500, 500_000),
    CONF_SCAN_HISTORY: (1, 200),
    CONF_PAGE_SIZE: (50, 2000),
    CONF_MAX_PAGES: (1, 500),
}

# Free text options: network ranges and paths to user rule files.
TEXT_OPTIONS: Final[tuple[str, ...]] = (
    CONF_ZONE_TRUSTED,
    CONF_ZONE_IOT,
    CONF_ZONE_GUEST,
    CONF_DOMAIN_RULES,
    CONF_CHECK_RULES,
)

# Its own file, never the recorder's database.
STORAGE_DIR: Final = "talos"
STORAGE_FILE: Final = "talos.db"

PANEL_URL: Final = "talos"
PANEL_TITLE: Final = "Talos"
PANEL_ICON: Final = "mdi:shield-search"
PANEL_COMPONENT: Final = "talos-panel"
PANEL_SCRIPT: Final = "talos-panel.js"
STATIC_URL: Final = "/talos_static"
