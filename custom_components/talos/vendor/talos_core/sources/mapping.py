"""Home Assistant registry payloads -> a declared-only `Scan`.

Pure functions over plain dicts. No network, no clock, no `homeassistant.*`:
give it recorded payloads and it gives back a scan, which is the only way this
layer stays testable across HA releases.

Two rules govern everything below.

**Never invent.** A device registry has no IP field, so `ip` stays None here
and the join with the observed side happens later, on the MAC. A manifest that
could not be read leaves `iot_class` at `unknown` and adds an entry to the
unverified list, rather than defaulting to something that reads reassuring.

**Skip what is switched off.** Disabled devices and disabled entities are
excluded: they already do not work, so counting them among the things that
would stop working offline would inflate the number in the wrong direction.
"""

from __future__ import annotations

from typing import Any, Iterable

import ipaddress
import re

from ..const import SCHEMA_VERSION
from ..model import (
    Conduit,
    Correlation,
    Destination,
    Device,
    Integration,
    Scan,
    SourceRef,
    UnverifiedCheck,
)

# Hostnames that only resolve inside the house.
LOCAL_HOST_SUFFIXES: tuple[str, ...] = (".local", ".lan", ".internal", ".home.arpa")
LOCAL_HOST_PREFIXES: tuple[str, ...] = ("a0d7b954-", "core-", "addon_", "homeassistant", "localhost")

# A device registry does not say how a device is attached. The domain is one
# hint among several; anything still unresolved stays `unknown`, which is
# honest and stays visible rather than folded into a plausible default.
#
# `mqtt` is deliberately absent. MQTT is a bus, not a radio: what rides on it
# can be Zigbee, Bluetooth or a script on a Pi, and the transport has to come
# from the identifiers instead.
DOMAIN_TRANSPORT_HINTS: dict[str, str] = {
    "zha": "zigbee",
    "deconz": "zigbee",
    "zwave_js": "zwave",
    "matter": "matter",
    "thread": "thread",
    "esphome": "wifi",
    "shelly": "wifi",
    "tasmota": "wifi",
    "tplink": "wifi",
    "hue": "ethernet",
    "reolink": "wifi",
    "onvif": "wifi",
    "bluetooth": "ble",
    "bthome": "ble",
    "sonos": "wifi",
    "cast": "wifi",
    "tuya": "wifi",
    "wled": "wifi",
    "yeelight": "wifi",
    "roborock": "wifi",
    "switchbot": "ble",
    "androidtv": "wifi",
    "samsungtv": "wifi",
}

# What an integration does, beyond how it talks to Home Assistant.
#
# `aggregator`: a bus or coordinator that carries other systems. MQTT is the
# clearest case and the reason this exists: it is not a radio and not a device,
# it is the thing Zigbee2MQTT and a SwitchBot bridge both publish through.
#
# `streaming`: carries a continuous media stream rather than state updates. An
# ONVIF camera sits on Wi-Fi like a plug does, but what crosses the wire is
# not comparable, and the ports it uses are the ones a posture check cares
# about.
# The integrations that carry video, which is what a cleartext RTSP check
# is about. `streaming` as a role also covers audio, and Sonos or Spotify
# have no RTSP stream to be in the clear: naming them as uninspectable for
# one would be wrong, so the check draws on this list and not on the role.
VIDEO_DOMAINS: frozenset[str] = frozenset(
    {
        "onvif", "generic", "camera", "reolink", "amcrest", "hikvision", "dahua",
        "frigate", "motioneye", "unifiprotect", "ring", "nest", "go2rtc", "ffmpeg",
        "stream", "arlo", "wyze", "eufy", "tapo", "blink", "doorbird", "axis",
        "foscam", "synology_dsm", "agent_dvr", "zoneminder", "mjpeg",
    }
)

INTEGRATION_ROLE_BY_DOMAIN: dict[str, str] = {
    # Buses and coordinators
    "mqtt": "aggregator",
    "zha": "aggregator",
    "deconz": "aggregator",
    "zwave_js": "aggregator",
    "matter": "aggregator",
    "thread": "aggregator",
    "esphome": "aggregator",
    "bluetooth": "aggregator",
    "hue": "aggregator",
    "tuya": "aggregator",
    "homekit_controller": "aggregator",
    # Video
    "onvif": "streaming",
    "generic": "streaming",
    "camera": "streaming",
    "reolink": "streaming",
    "amcrest": "streaming",
    "hikvision": "streaming",
    "dahua": "streaming",
    "frigate": "streaming",
    "motioneye": "streaming",
    "unifiprotect": "streaming",
    "ring": "streaming",
    "nest": "streaming",
    "go2rtc": "streaming",
    "ffmpeg": "streaming",
    "stream": "streaming",
    # Audio and media
    "sonos": "streaming",
    "cast": "streaming",
    "dlna_dmr": "streaming",
    "dlna_dms": "streaming",
    "music_assistant": "streaming",
    "squeezebox": "streaming",
    "forked_daapd": "streaming",
    "spotify": "streaming",
    "plex": "streaming",
    "jellyfin": "streaming",
    "androidtv": "streaming",
    "samsungtv": "streaming",
    "apple_tv": "streaming",
    "roku": "streaming",
    "webostv": "streaming",
}

# What a hub's own radio is. Not the same as how the hub reaches Home
# Assistant: a Hue bridge sits on ethernet and speaks Zigbee to its bulbs, so
# a device behind it is Zigbee even though its integration says ethernet.
HUB_RADIO_BY_DOMAIN: dict[str, str] = {
    "hue": "zigbee",
    "zha": "zigbee",
    "deconz": "zigbee",
    "zwave_js": "zwave",
    "matter": "matter",
    "thread": "thread",
    "bluetooth": "ble",
}

# Device identifiers carry what the bus itself will not say. Zigbee2MQTT
# registers its devices through MQTT with an identifier of its own, and that
# prefix is the only evidence in the registry that the thing is Zigbee.
# Matched on the value's prefix, not as a substring, so a device merely named
# after a protocol is not mistaken for one.
# What actually produced the data, when it is not the integration that
# registered it. An MQTT config entry can be fed by Zigbee2MQTT and by a
# SwitchBot bridge at the same time: the integration is the bus, these are the
# sources on it. Matched on the value's prefix, like the transports.
IDENTIFIER_PREFIX_ORIGINS: tuple[tuple[str, str], ...] = (
    ("zigbee2mqtt", "zigbee2mqtt"),
    ("switchbot", "switchbot"),
    ("tasmota", "tasmota"),
    ("esphome", "esphome"),
    ("shelly", "shelly"),
    ("zwavejs2mqtt", "zwavejs2mqtt"),
    ("z2m", "zigbee2mqtt"),
    ("bthome", "bthome"),
    ("govee", "govee"),
    ("tuya", "tuya"),
)

# An IEEE EUI-64 written the way every Zigbee stack writes it. Zigbee2MQTT
# registers some devices under the bare address with no prefix at all, and
# then this is the only thing in the registry that names the radio.
IEEE_ADDRESS = re.compile(r"^0x[0-9a-f]{16}$")

# A Z-Wave JS UI node, which arrives over MQTT and not through zwave_js.
ZWAVEJS_NODE = re.compile(r"^[0-9]+-[0-9]+(-[0-9]+)?$")

IDENTIFIER_PREFIX_TRANSPORTS: tuple[tuple[str, str], ...] = (
    ("zigbee2mqtt", "zigbee"),
    ("z2m", "zigbee"),
    ("zbbridge", "zigbee"),
    ("zigbee", "zigbee"),
    ("zwave", "zwave"),
    ("matter", "matter"),
    ("thread", "thread"),
    ("ble", "ble"),
    ("bluetooth", "ble"),
    ("tasmota", "ip"),
    ("shelly", "ip"),
    ("zha", "zigbee"),
    ("deconz", "zigbee"),
    ("zwavejs", "zwave"),
    ("zwave_js", "zwave"),
    ("bthome", "ble"),
    ("switchbot", "ble"),
    ("esphome", "wifi"),
)

# Connection types in a device registry entry that pin the transport down
# better than the domain does.
CONNECTION_TRANSPORT: dict[str, str] = {
    "zigbee": "zigbee",
    "zwave": "zwave",
    "bluetooth": "ble",
    "matter": "matter",
}


class RegistryPayload:
    """Everything a collector managed to read, plus what it could not."""

    __slots__ = (
        "config_entries",
        "devices",
        "entities",
        "areas",
        "manifests",
        "addresses",
        "notes",
    )

    def __init__(
        self,
        *,
        config_entries: Iterable[dict[str, Any]] = (),
        devices: Iterable[dict[str, Any]] = (),
        entities: Iterable[dict[str, Any]] = (),
        areas: Iterable[dict[str, Any]] = (),
        manifests: Iterable[dict[str, Any]] = (),
        # MAC to IP pairs Home Assistant already holds, from whatever entity
        # publishes both. The other place the two halves of the join meet.
        addresses: Iterable[dict[str, Any]] = (),
        notes: Iterable[UnverifiedCheck] = (),
    ) -> None:
        self.config_entries = list(config_entries)
        self.devices = list(devices)
        self.entities = list(entities)
        self.areas = list(areas)
        self.manifests = list(manifests)
        self.addresses = list(addresses)
        self.notes = list(notes)


def build_scan(
    payload: RegistryPayload,
    *,
    generated_at: str,
    collector: str = "websocket",
    ha_version: str | None = None,
) -> Scan:
    """Normalise registry payloads into a scan. Declared evidence only."""
    areas = {a["area_id"]: a.get("name") for a in payload.areas if a.get("area_id")}
    manifests = {m["domain"]: m for m in payload.manifests if m.get("domain")}

    integrations, missing_manifests = _build_integrations(payload.config_entries, manifests)
    known_entries = {i.id for i in integrations}

    entry_domains = {i.id: i.domain for i in integrations}
    devices = _build_devices(
        payload.devices, known_entries, entry_domains, areas, payload.addresses
    )
    _count_entities(payload.entities, integrations, devices)
    _mark_aggregators(integrations, devices)

    unverified = list(payload.notes)
    if missing_manifests:
        unverified.append(
            UnverifiedCheck(
                id="unv.manifests_unavailable",
                title="iot_class of some integrations",
                reason="missing_data",
                detail=(
                    "Manifest unreadable for: "
                    + ", ".join(sorted(missing_manifests))
                    + ". These integrations stay 'unknown' and are counted neither"
                    " as local nor as cloud."
                ),
            )
        )

    orphan_entities = sum(
        1
        for entity in payload.entities
        if not entity.get("disabled_by")
        and not entity.get("config_entry_id")
        and not entity.get("device_id")
    )
    if orphan_entities:
        unverified.append(
            UnverifiedCheck(
                id="unv.entities_outside_registry",
                title="Entities that map to no config entry",
                reason="missing_data",
                detail=(
                    f"{orphan_entities} entities with neither a config entry nor a"
                    " device, typically defined in YAML. They are left out of the"
                    " autonomy count."
                ),
            )
        )

    destinations, conduits = _endpoints(payload.config_entries, known_entries)
    link_destinations, link_conduits = _local_links(devices)
    destinations = sorted([*destinations, *link_destinations], key=lambda d: d.id)
    conduits = [*conduits, *link_conduits]

    return Scan(
        schema_version=SCHEMA_VERSION,
        generated_at=generated_at,
        collector=collector,
        ha_version=ha_version,
        integrations=integrations,
        devices=devices,
        # A manifest never says which host an integration reaches, but a
        # config entry often does: the broker, the server, the appliance. That
        # is declared evidence, so it belongs in the document.
        destinations=destinations,
        conduits=conduits,
        correlation=_correlation(devices),
        unverified=unverified,
    )


def _mark_aggregators(integrations: list[Integration], devices: list[Device]) -> None:
    """An entry whose devices name other systems is a bus, by evidence.

    The domain table names the ones known in advance; this catches the rest.
    If two different origins publish through the same config entry, that entry
    is carrying them, whatever its domain happens to be.
    """
    origins: dict[str, set[str]] = {}
    for device in devices:
        if device.origin:
            origins.setdefault(device.integration_id, set()).add(device.origin)

    for integration in integrations:
        if integration.role == "unknown" and origins.get(integration.id):
            integration.role = "aggregator"


def _is_local_host(host: str) -> bool:
    name = host.lower().split("://")[-1].split("/")[0].split(":")[0]
    try:
        address = ipaddress.ip_address(name)
    except ValueError:
        return name.startswith(LOCAL_HOST_PREFIXES) or name.endswith(LOCAL_HOST_SUFFIXES)
    return address.is_private or address.is_loopback or address.is_link_local


def _endpoints(
    config_entries: Iterable[dict[str, Any]], known_entries: set[str]
) -> tuple[list[Destination], list[Conduit]]:
    """Declared conduits for the entries that name where they connect.

    Only what a config entry states about its own address. Nothing is probed
    and nothing is guessed: an entry that names no host produces nothing.
    """
    destinations: dict[str, Destination] = {}
    conduits: list[Conduit] = []

    def place(host: str, port: Any) -> str:
        destination_id = f"dst.{host}" + (f":{port}" if port else "")
        if destination_id not in destinations:
            destinations[destination_id] = Destination(
                id=destination_id,
                fqdn=host,
                kind="local_broker" if _is_local_host(host) else "vendor_cloud",
                vendor=None,
            )
        return destination_id

    for entry in config_entries:
        entry_id = entry.get("entry_id")
        if entry_id not in known_entries:
            continue

        endpoint = entry.get("endpoint")
        if isinstance(endpoint, dict) and str(endpoint.get("host") or "").strip():
            host = str(endpoint["host"]).strip()
            port = endpoint.get("port")
            conduits.append(
                Conduit(
                    id=f"cnd.{entry_id}.endpoint",
                    source=SourceRef("integration", entry_id),
                    destination_id=place(host, port),
                    evidence="declared",
                    port=int(port) if isinstance(port, int) else None,
                    encrypted="unknown",
                )
            )

        # A media stream the entry names. Its scheme is the whole finding: the
        # address was read from the configuration, nothing was connected to.
        for index, stream in enumerate(entry.get("streams") or ()):
            if not isinstance(stream, dict):
                continue
            host = str(stream.get("host") or "").strip()
            protocol = str(stream.get("protocol") or "").strip().lower()
            if not host or not protocol:
                continue
            port = stream.get("port")
            conduits.append(
                Conduit(
                    id=f"cnd.{entry_id}.stream.{index}",
                    source=SourceRef("integration", entry_id),
                    destination_id=place(host, port),
                    evidence="declared",
                    protocol=protocol,
                    port=int(port) if isinstance(port, int) else None,
                    encrypted=bool(stream.get("encrypted")),
                )
            )

    return sorted(destinations.values(), key=lambda d: d.id), conduits


def _local_links(devices: list[Device]) -> tuple[list[Destination], list[Conduit]]:
    """The link every device has to its hub, as a conduit.

    A radio is a conduit. A Zigbee lamp exchanges data with its coordinator
    continuously and never touches IP, so it owns no address, appears in no
    query log, and used to be absent from every view built on conduits. That
    said the branch was not there, when what is true is that it never leaves
    the hub. The registry states the parent and the transport, so this is
    declared evidence like any other, and it stops at the hub: what the hub
    does next is the hub's own conduit.
    """
    destinations: dict[str, Destination] = {}
    conduits: list[Conduit] = []
    by_id = {device.id: device for device in devices}

    for device in devices:
        parent = by_id.get(device.via_device_id or "")
        if parent is None or device.transport in {"unknown", "virtual"}:
            continue
        destination_id = f"dst.hub.{parent.id}"
        if destination_id not in destinations:
            destinations[destination_id] = Destination(
                id=destination_id,
                fqdn=parent.name,
                kind="local_hub",
                vendor=parent.manufacturer,
            )
        conduits.append(
            Conduit(
                id=f"cnd.{device.id}.link",
                source=SourceRef("device", device.id),
                destination_id=destination_id,
                evidence="declared",
                protocol=device.transport,
                # A radio link is encrypted or not depending on how the mesh
                # was set up, and the registry does not say which.
                encrypted="unknown",
            )
        )

    return sorted(destinations.values(), key=lambda d: d.id), conduits


def _build_integrations(
    config_entries: Iterable[dict[str, Any]],
    manifests: dict[str, dict[str, Any]],
) -> tuple[list[Integration], set[str]]:
    integrations: list[Integration] = []
    missing: set[str] = set()


    for entry in config_entries:
        entry_id, domain = entry.get("entry_id"), entry.get("domain")
        if not entry_id or not domain:
            continue
        if entry.get("disabled_by"):
            continue

        manifest = manifests.get(domain)
        if manifest is None:
            missing.add(domain)

        integrations.append(
            Integration(
                id=entry_id,
                domain=domain,
                title=entry.get("title") or domain,
                iot_class=(manifest or {}).get("iot_class") or "unknown",
                # Absent a manifest we cannot claim it is built in, and
                # claiming it is would understate the finding.
                is_built_in=bool((manifest or {}).get("is_built_in", False)),
                state=entry.get("state") or "loaded",
                role=INTEGRATION_ROLE_BY_DOMAIN.get(domain, "unknown"),
                # Only meaningful for an entry that names somewhere to connect.
                authenticated=(entry.get("endpoint") or {}).get("authenticated"),
                dependencies=list((manifest or {}).get("dependencies") or []),
            )
        )

    return integrations, missing


def _build_devices(
    raw_devices: Iterable[dict[str, Any]],
    known_entries: set[str],
    entry_domains: dict[str, str],
    areas: dict[str, Any],
    addresses: Iterable[dict[str, Any]] = (),
) -> list[Device]:
    kept: list[Device] = []
    attributed: dict[str, str] = {}
    ip_by_mac = {
        str(entry.get("mac")).lower(): str(entry.get("ip"))
        for entry in addresses
        if entry.get("mac") and entry.get("ip")
    }

    for raw in raw_devices:
        device_id = raw.get("id")
        if not device_id or raw.get("disabled_by"):
            continue
        entry_id = _primary_entry(raw, known_entries)
        if entry_id is None:
            # No config entry we kept: nothing to attribute it to.
            continue
        attributed[device_id] = entry_id

    for raw in raw_devices:
        device_id = raw.get("id")
        if device_id not in attributed:
            continue

        via = raw.get("via_device_id")
        kept.append(
            Device(
                id=device_id,
                integration_id=attributed[device_id],
                name=raw.get("name_by_user") or raw.get("name") or device_id,
                transport=_transport(
                    raw,
                    entry_domains.get(attributed[device_id]),
                    entry_domains.get(attributed.get(raw.get("via_device_id") or "", "")),
                ),
                manufacturer=raw.get("manufacturer"),
                model=raw.get("model"),
                area=areas.get(raw.get("area_id")),
                origin=_origin(raw, entry_domains.get(attributed[device_id])),
                mac=_mac(raw),
                # The device registry carries no address of its own. The IP
                # comes from whatever else in Home Assistant already knows it,
                # a router based tracker most often, and the DHCP leases add
                # to this on the observed side. Both join on the MAC.
                ip=ip_by_mac.get(_mac(raw) or ""),
                zone="unknown",
                # Drop a parent we did not keep, rather than emit a dangling
                # reference the validator would rightly reject.
                via_device_id=via if via in attributed else None,
                entity_count=0,
            )
        )

    _inherit_hub_radio(kept)
    _inherit_origin(kept)
    return kept


# Radios a child can only be speaking if its hub speaks them.
RADIO_TRANSPORTS: frozenset[str] = frozenset({"zigbee", "zwave", "thread", "matter", "ble"})


def _inherit_hub_radio(devices: list[Device]) -> None:
    """Give a still-unknown child the radio its hub was found to speak.

    The identifier prefixes cover the integrations we know by name; this
    catches the rest. If a hub resolved to Zigbee, everything hanging off it
    is on Zigbee too, whatever bus carried the discovery message.
    """
    by_id = {device.id: device for device in devices}
    for device in devices:
        if device.transport != "unknown" or not device.via_device_id:
            continue
        seen: set[str] = {device.id}
        parent = by_id.get(device.via_device_id)
        while parent is not None and parent.id not in seen:
            seen.add(parent.id)
            if parent.transport in RADIO_TRANSPORTS:
                device.transport = parent.transport
                break
            if not parent.via_device_id:
                break
            parent = by_id.get(parent.via_device_id)


def _inherit_origin(devices: list[Device]) -> None:
    """Give a child the system that produced its hub.

    A Zigbee2MQTT leaf registered under its bare IEEE address names no system
    at all; its bridge does. Walking up the hub chain is the same evidence the
    radio inheritance uses, and it is what keeps a branch attributed to
    Zigbee2MQTT rather than to MQTT, which is only the bus underneath.
    """
    by_id = {device.id: device for device in devices}
    for device in devices:
        if device.origin or not device.via_device_id:
            continue
        seen: set[str] = {device.id}
        parent = by_id.get(device.via_device_id)
        while parent is not None and parent.id not in seen:
            seen.add(parent.id)
            if parent.origin:
                device.origin = parent.origin
                break
            if not parent.via_device_id:
                break
            parent = by_id.get(parent.via_device_id)


def _primary_entry(raw: dict[str, Any], known_entries: set[str]) -> str | None:
    """A device can belong to several config entries; pick the one HA calls
    primary, else the first we recognise."""
    primary = raw.get("primary_config_entry")
    if primary in known_entries:
        return primary
    for entry_id in raw.get("config_entries") or ():
        if entry_id in known_entries:
            return entry_id
    return None


def _transport(
    raw: dict[str, Any], domain: str | None, parent_domain: str | None = None
) -> str:
    """Best evidence first, and `unknown` when there is none.

    Home Assistant's own `entry_type` settles it before anything else: a
    service entry is an add-on, a repository or a cloud account, and none of
    those is attached to a network in the sense this column means.

    A connection type is stated by the integration and settles it. Failing
    that, an identifier prefix can name a protocol the config entry cannot:
    Zigbee2MQTT devices arrive through MQTT and only their identifier says
    they are Zigbee. Only then does the hub, and last the domain.
    """
    if str(raw.get("entry_type") or "") == "service":
        return "virtual"

    for connection in raw.get("connections") or ():
        if not isinstance(connection, (list, tuple)) or not connection:
            continue
        hinted = CONNECTION_TRANSPORT.get(str(connection[0]))
        if hinted:
            return hinted

    for identifier in raw.get("identifiers") or ():
        if not isinstance(identifier, (list, tuple)) or len(identifier) < 2:
            continue
        value = str(identifier[1]).lower()
        for prefix, transport in IDENTIFIER_PREFIX_TRANSPORTS:
            if value.startswith(prefix):
                return transport
        if IEEE_ADDRESS.match(value):
            return "zigbee"
        if domain in {"zwave_js_ui", "zwavejs2mqtt"} and ZWAVEJS_NODE.match(value):
            return "zwave"

    # Behind a hub the transport is the hub's radio, not the hub's own uplink.
    # A miss here is not the end of the search: the domain may still know, and
    # the second pass can still inherit from a parent that resolved later.
    if raw.get("via_device_id"):
        radio = HUB_RADIO_BY_DOMAIN.get(parent_domain or "") or HUB_RADIO_BY_DOMAIN.get(domain or "")
        if radio:
            return radio

    if domain and domain in DOMAIN_TRANSPORT_HINTS:
        return DOMAIN_TRANSPORT_HINTS[domain]

    # Last resort, and still evidence: a MAC or an address to open in a browser
    # means the device is reachable over IP. Which medium carries the last hop
    # is not written anywhere, so it is not claimed.
    if _has_network_address(raw):
        return "ip"
    return "unknown"


def _has_network_address(raw: dict[str, Any]) -> bool:
    """Whether the registry entry itself shows the device holds an address."""
    for connection in raw.get("connections") or ():
        if isinstance(connection, (list, tuple)) and connection and str(connection[0]) == "mac":
            return True
    url = str(raw.get("configuration_url") or "")
    return url.startswith("http://") or url.startswith("https://")


def _origin(raw: dict[str, Any], domain: str | None) -> str | None:
    """Which system produced this device, when it is not the integration.

    Returns None when the integration is the source, so the common case adds
    nothing to the document and the field only appears where it says something.
    """
    for identifier in raw.get("identifiers") or ():
        if not isinstance(identifier, (list, tuple)) or len(identifier) < 2:
            continue
        value = str(identifier[1]).lower()
        for prefix, origin in IDENTIFIER_PREFIX_ORIGINS:
            if value.startswith(prefix):
                return None if origin == domain else origin
    return None


def apply_mesh_roles(
    devices: list[Device], roles: dict[str, str], identifiers: dict[str, list[str]]
) -> int:
    """Give each device the part its coordinator says it plays.

    The join is on the IEEE address, which is in the device identifier one way
    or another: bare on a Zigbee2MQTT device, or behind a prefix. Anything the
    coordinator did not name keeps `unknown`, which is the honest answer for a
    node on a mesh nobody asked about.
    """
    applied = 0
    for device in devices:
        for value in identifiers.get(device.id) or ():
            lowered = str(value).lower()
            ieee = lowered if lowered.startswith("0x") else _trailing_ieee(lowered)
            role = roles.get(ieee or "")
            if role:
                device.mesh_role = role
                applied += 1
                break
    return applied


def _trailing_ieee(value: str) -> str | None:
    """The IEEE address at the end of an identifier like `zigbee2mqtt_0x00...`."""
    match = re.search(r"(0x[0-9a-f]{16})$", value)
    return match.group(1) if match else None


def _mac(raw: dict[str, Any]) -> str | None:
    for connection in raw.get("connections") or ():
        if (
            isinstance(connection, (list, tuple))
            and len(connection) >= 2
            and str(connection[0]) == "mac"
        ):
            return str(connection[1]).lower()
    return None


def _count_entities(
    raw_entities: Iterable[dict[str, Any]],
    integrations: list[Integration],
    devices: list[Device],
) -> None:
    """Count active entities per device and per config entry.

    An integration is credited with every entity that names it *or* that
    belongs to one of its devices. The union keeps the per-integration total
    at or above the sum of its devices, which is the invariant `TALOS-C010`
    enforces on the way out.
    """
    device_entry = {d.id: d.integration_id for d in devices}
    per_device: dict[str, int] = {}
    per_integration: dict[str, int] = {}

    for entity in raw_entities:
        if entity.get("disabled_by"):
            continue
        device_id = entity.get("device_id")
        # An entity can name one config entry while its device belongs to
        # another: a Zigbee2MQTT device on the MQTT entry with an entity
        # owned by a helper, say. Both entries carry it, which is what makes
        # the total at least the sum of the devices rather than less.
        entries = set()
        if entity.get("config_entry_id"):
            entries.add(entity["config_entry_id"])

        if device_id in device_entry:
            per_device[device_id] = per_device.get(device_id, 0) + 1
            entries.add(device_entry[device_id])
        elif device_id:
            # Its device was skipped (disabled, or attributed to nothing).
            continue

        for entry_id in entries:
            per_integration[entry_id] = per_integration.get(entry_id, 0) + 1

    for device in devices:
        device.entity_count = per_device.get(device.id, 0)
    for integration in integrations:
        integration.entity_count = per_integration.get(integration.id, 0)


def _correlation(devices: list[Device]) -> Correlation:
    joinable = sum(1 for d in devices if d.mac or d.ip)
    return Correlation(
        devices_total=len(devices),
        devices_correlated=joinable,
        method="mac",
    )
