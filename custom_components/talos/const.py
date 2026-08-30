"""Constants for the Talos integration."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "talos"

# Config entry data
CONF_ADGUARD_URL: Final = "adguard_url"
CONF_ADGUARD_USERNAME: Final = "adguard_username"
CONF_ADGUARD_PASSWORD: Final = "adguard_password"
CONF_VERIFY_SSL: Final = "verify_ssl"

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

# Its own file, never the recorder's database.
STORAGE_DIR: Final = "talos"
STORAGE_FILE: Final = "talos.db"

PANEL_URL: Final = "talos"
PANEL_TITLE: Final = "Talos"
PANEL_ICON: Final = "mdi:shield-search"
PANEL_COMPONENT: Final = "talos-panel"
PANEL_SCRIPT: Final = "talos-panel.js"
STATIC_URL: Final = "/talos_static"
