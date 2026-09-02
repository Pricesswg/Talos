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

# A config entry only serves its entities while it is loaded. Anything else,
# a broker that is down, a retry loop, a failed migration, means the entities
# are unavailable right now, which is not the same as working offline.
LOADED_ENTRY_STATES: Final = frozenset({"loaded"})

TRANSPORTS: Final = frozenset(
    {
        "zigbee",
        "zwave",
        "wifi",
        "ethernet",
        "ble",
        "thread",
        "matter",
        # A device with a MAC and an IP is on the network. Whether the last
        # metre is copper or radio is not in any registry, and guessing it
        # would be inventing, so it stays "ip" rather than becoming "wifi".
        "ip",
        "virtual",
        "unknown",
    }
)

# Transports that cannot carry IP traffic on their own. A device on one of
# these has no direct egress; whatever it reaches, it reaches through its hub.
NON_IP_TRANSPORTS: Final = frozenset({"zigbee", "zwave", "ble", "thread"})

# What part a node plays in a mesh. A router relays for the nodes around it
# and is mains powered; an end device sleeps and depends on a router being in
# range. It is the shape of the network, and it is the one thing a mesh
# coordinator will state without being asked to interrogate anybody.
MESH_ROLES: Final = frozenset({"coordinator", "router", "end_device", "unknown"})

# Schemes that carry a media stream. Named explicitly because `protocol` on a
# conduit can also hold a transport, `tcp` or `udp`, and a transport is not a
# stream: a precondition that accepted either would run the cleartext check on
# a document that declared no stream at all.
STREAM_PROTOCOLS: Final = frozenset(
    {"rtsp", "rtsps", "rtmp", "rtmps", "srtp", "http", "https"}
)

# What an integration does, beyond how it talks. A bus that carries other
# systems and a service that carries a continuous media stream are both worth
# seeing on their own, and neither is a transport: Zigbee2MQTT rides on MQTT
# and an ONVIF camera rides on Wi-Fi.
INTEGRATION_ROLES: Final = frozenset({"aggregator", "streaming", "unknown"})

# A config entry only serves its entities while it is loaded. Anything else,
# a broker that is down, a retry loop, a failed migration, means the entities
# are unavailable right now, which is not the same as working offline.
LOADED_ENTRY_STATES: Final = frozenset({"loaded"})

DESTINATION_KINDS: Final = frozenset(
    {
        "ha_core",
        "local_broker",
        # A hub inside the house that other devices reach the world through.
        # A Zigbee coordinator is not a broker and not a cloud, but it is
        # certainly the other end of a conduit.
        "local_hub",
        "vendor_cloud",
        "telemetry",
        "ota_update",
        "push_service",
        "ntp",
        "cdn",
        # A STUN or TURN server is not a destination anyone browses to: a
        # device reaching one is opening a path back into the house from
        # outside, which is the single most interesting thing DNS can show.
        "nat_traversal",
        "unknown",
    }
)

# Destinations that live inside the house. Reaching one is not egress.
INTERNAL_DESTINATION_KINDS: Final = frozenset({"ha_core", "local_broker", "local_hub"})

# Outside the house but not a vendor relationship. Kept out of the matrix's
# egress column and reported on its own, so that a clock sync never reads as
# a device phoning home.
INFRA_DESTINATION_KINDS: Final = frozenset({"ntp", "ota_update"})

# A device reaching one of these is talking to someone about itself. `cdn`
# is in here on purpose: it often fronts the vendor cloud. `unknown` is in
# here because an unclassified destination must stay visible, not fall into
# a benign catch-all.
PHONE_HOME_DESTINATION_KINDS: Final = frozenset(
    {"vendor_cloud", "telemetry", "push_service", "cdn", "nat_traversal", "unknown"}
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
