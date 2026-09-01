"""Vocabularies and invariants of the Talos data model.

Every enumerated value used by the schema lives here, so that the validator,
the collectors and the exporter can never drift apart on what is legal.
"""

from __future__ import annotations

from typing import Final

SCHEMA_VERSION: Final = "1.0"
SUPPORTED_SCHEMA_VERSIONS: Final = frozenset({"1.0"})

# How the declarative side was collected. Same normalised output either way.
COLLECTOR_SOURCES: Final = frozenset({"native", "websocket"})

# The invariant of the whole project. `declared` is what Home Assistant says
# about itself, `observed` is what the DNS query log actually saw, `inherited`
# is an observation made on a parent hub and attributed to its children.
# They are never merged into a single view without an explicit label.
EVIDENCE: Final = frozenset({"declared", "observed", "inherited"})

# How HA talks to the device. Says nothing about how the device talks to the
# internet: the two dimensions are independent and stay independent here.
IOT_CLASSES: Final = frozenset(
    {
        "local_push",
        "local_polling",
        "cloud_push",
        "cloud_polling",
        "assumed_state",
        "calculated",
        "unknown",
    }
)
LOCAL_IOT_CLASSES: Final = frozenset({"local_push", "local_polling"})
CLOUD_IOT_CLASSES: Final = frozenset({"cloud_push", "cloud_polling"})

# What an integration does, beyond how it talks. A bus that carries other
# systems and a service that carries a continuous media stream are both worth
# seeing on their own, and neither is a transport: Zigbee2MQTT rides on MQTT
# and an ONVIF camera rides on Wi-Fi.
INTEGRATION_ROLES: Final = frozenset({"aggregator", "streaming", "unknown"})

TRANSPORTS: Final = frozenset(
    {
        "zigbee",
        "zwave",
        "wifi",
        "ethernet",
        "ble",
        "thread",
        "matter",
        "virtual",
        "unknown",
    }
)

# Transports that cannot carry IP traffic on their own. A device on one of
# these has no direct egress; whatever it reaches, it reaches through its hub.
NON_IP_TRANSPORTS: Final = frozenset({"zigbee", "zwave", "ble", "thread"})

# What an integration does, beyond how it talks. A bus that carries other
# systems and a service that carries a continuous media stream are both worth
# seeing on their own, and neither is a transport: Zigbee2MQTT rides on MQTT
# and an ONVIF camera rides on Wi-Fi.
INTEGRATION_ROLES: Final = frozenset({"aggregator", "streaming", "unknown"})

DESTINATION_KINDS: Final = frozenset(
    {
        "ha_core",
        "local_broker",
        "vendor_cloud",
        "telemetry",
        "ota_update",
        "push_service",
        "ntp",
        "cdn",
        "unknown",
    }
)

# Destinations that live inside the house. Reaching one is not egress.
INTERNAL_DESTINATION_KINDS: Final = frozenset({"ha_core", "local_broker"})

# Outside the house but not a vendor relationship. Kept out of the matrix's
# egress column and reported on its own, so that a clock sync never reads as
# a device phoning home.
INFRA_DESTINATION_KINDS: Final = frozenset({"ntp", "ota_update"})

# A device reaching one of these is talking to someone about itself. `cdn`
# is in here on purpose: it often fronts the vendor cloud. `unknown` is in
# here because an unclassified destination must stay visible, not fall into
# a benign catch-all.
PHONE_HOME_DESTINATION_KINDS: Final = frozenset(
    {"vendor_cloud", "telemetry", "push_service", "cdn", "unknown"}
)

# Destinations whose outage is a functional dependency worth naming a vendor for.
VENDOR_DESTINATION_KINDS: Final = frozenset({"vendor_cloud", "telemetry", "push_service"})

ZONES: Final = frozenset({"trusted_lan", "iot_vlan", "guest", "dmz", "external", "unknown"})

FILTER_STATUS: Final = frozenset({"allowed", "blocked", "unknown"})

# What a conduit can start from. `unknown_host` carries an IP seen by the
# resolver that matches nothing in the HA registry: it is the whole point of
# the zero check, so the model has to be able to express it.
SOURCE_KINDS: Final = frozenset({"device", "integration", "ha_core", "unknown_host"})

# Why a posture check could not run. Never counted among the passes.
UNVERIFIED_REASONS: Final = frozenset({"not_executable", "missing_data", "method_limit"})

# Fields that only make sense on a first-hand observation. Present on a
# `declared` or `inherited` conduit they would silently blur the invariant,
# so the validator rejects them there.
OBSERVED_ONLY_FIELDS: Final = ("first_seen", "last_seen", "query_count", "filter_status")
