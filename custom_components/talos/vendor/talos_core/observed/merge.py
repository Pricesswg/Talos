"""Join the observed side onto a declared scan.

This is where `evidence: observed` and `evidence: inherited` enter the
document, and where the tool stops describing what Home Assistant already
knows and starts adding something.

The join runs on the MAC. A device registry has no address and a query log has
no MAC, so something has to hold both. The DHCP leases are the usual place;
a router based device tracker already inside Home Assistant is the other, and
an install whose router does the DHCP is not condemned to zero correlation
because of it. What could not be attributed falls back to `unknown_host`, and
which sources actually carried the join is recorded rather than assumed.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any, Iterable

from ..const import PHONE_HOME_DESTINATION_KINDS
from ..zones import ZoneMap
from ..model import Conduit, Correlation, Destination, Device, Scan, SourceRef, UnverifiedCheck
from .classify import DomainClassifier
from .forwarder import find_forwarder, is_supervisor_client
from .mapping import Lease, ObservedFacts, ZeroCheck, parse_time

# Only a relationship with somebody worth naming is worth attributing to the
# children of a hub. Inheriting a clock sync would be noise, not evidence.
INHERITABLE_KINDS = PHONE_HOME_DESTINATION_KINDS


def merge_observed(
    scan: Scan,
    facts: ObservedFacts,
    classifier: DomainClassifier | None = None,
    zones: ZoneMap | None = None,
) -> Scan:
    """Return a new scan carrying the observations. The input is left alone."""
    classifier = classifier or DomainClassifier.load()
    zones = zones or ZoneMap()

    lease_by_mac = {lease.mac: lease for lease in _pick_address_per_mac(facts.leases)}
    from_leases = 0
    from_network = 0
    from_declared = 0
    devices = []
    for device in scan.devices:
        lease = lease_by_mac.get(device.mac) if device.mac else None
        leased = lease.ip if lease else None
        # A lease is the fresher of the two, so it wins; the address Home
        # Assistant already held covers everything the leases do not reach.
        ip = leased or device.ip
        if lease and lease.origin == "network":
            from_network += 1
        elif leased:
            from_leases += 1
        elif ip:
            from_declared += 1
        # A zone is only assigned once an address is known and a range was
        # configured for it; otherwise it stays unknown on purpose.
        devices.append(replace(device, ip=ip, zone=zones.zone_for(ip) if ip else device.zone))
    device_by_ip = {d.ip: d.id for d in devices if d.ip}

    destinations: dict[str, Destination] = {d.id: d for d in scan.destinations}
    conduits: list[Conduit] = list(scan.conduits)
    ignored = 0
    # On Home Assistant OS and Supervised, everything in the Home Assistant
    # stack resolves through the Supervisor's DNS plugin, which reaches the
    # resolver from its own network: those queries are Home Assistant's own,
    # not an unknown host's. Only there: a bare 172.30.32.x on a Container
    # install is somebody's Docker network and stays unknown.
    supervised = any(integration.domain == "hassio" for integration in scan.integrations)
    supervisor_seen: dict[str, tuple[int, set[str]]] = {}

    for observation in facts.observations:
        if classifier.is_ignored(observation.fqdn):
            ignored += 1
            continue

        verdict = classifier.classify(observation.fqdn)
        destination_id = f"dst.{observation.fqdn}"
        if destination_id not in destinations:
            destinations[destination_id] = Destination(
                id=destination_id,
                fqdn=observation.fqdn,
                kind=verdict.kind,
                vendor=verdict.vendor,
            )

        device_id = device_by_ip.get(observation.client)
        if device_id:
            source = SourceRef("device", device_id)
            key = device_id
        elif supervised and is_supervisor_client(observation.client):
            source = SourceRef("ha_core")
            key = observation.client
            queries, seen_names = supervisor_seen.setdefault(observation.client, (0, set()))
            supervisor_seen[observation.client] = (queries + observation.count, seen_names | {observation.fqdn})
        else:
            # Seen by the resolver, absent from the registry. Not a broken
            # reference: a host we cannot name, which is worth saying so.
            source = SourceRef("unknown_host", observation.client)
            key = observation.client

        conduits.append(
            Conduit(
                id=f"cnd.{key}.{observation.fqdn}",
                source=source,
                destination_id=destination_id,
                evidence="observed",
                encrypted="unknown",
                first_seen=observation.first_seen,
                last_seen=observation.last_seen,
                query_count=observation.count,
                filter_status=observation.filter_status,
            )
        )

    conduits.extend(_inherit_through_hubs(devices, destinations, conduits))

    # `replace`, not a new Scan: every scalar the collector recorded, the
    # version, the uptime, whatever comes next, survives the merge unlisted.
    return replace(
        scan,
        integrations=list(scan.integrations),
        devices=devices,
        destinations=sorted(destinations.values(), key=lambda d: d.id),
        conduits=conduits,
        correlation=Correlation(
            devices_total=len(devices),
            devices_correlated=sum(1 for d in devices if d.ip),
            method=_method(from_leases, from_declared, from_network),
        ),
        unverified=[
            *scan.unverified,
            *_notes(scan, facts, classifier, devices, ignored, device_by_ip, supervisor_seen),
        ],
    )


def _pick_address_per_mac(leases: Iterable[Lease]) -> list[Lease]:
    """One address per device for the join.

    A lease the resolver handed out outranks a pair merely seen on the
    wire. Among wire pairs an IPv4 outranks an IPv6, because that is what
    the registry and the log speak, and the most recently seen one wins:
    Pi-hole lists a device's addresses newest first, so taking the last
    would join it to its oldest address, or to a link-local IPv6."""
    best: dict[str, Lease] = {}

    def rank(lease: Lease) -> tuple[int, int, float]:
        seen = parse_time(lease.seen_at) if lease.seen_at else None
        return (
            1 if lease.origin != "network" else 0,
            0 if ":" in lease.ip else 1,
            seen.timestamp() if seen else float("-inf"),
        )

    for lease in leases:
        current = best.get(lease.mac)
        if current is None or rank(lease) > rank(current):
            best[lease.mac] = lease
    return list(best.values())


def _method(from_leases: int, from_declared: int, from_network: int = 0) -> str:
    """Name the sources that actually carried the join, not the ones that
    were available. A method nobody used has no business in the report."""
    used = []
    if from_leases:
        used.append("dhcp")
    if from_network:
        used.append("network")
    if from_declared:
        used.append("tracker")
    return f"mac_{'_'.join(used)}" if used else "none"


def _inherit_through_hubs(
    devices: list[Device],
    destinations: dict[str, Destination],
    conduits: list[Conduit],
) -> list[Conduit]:
    """Attribute a hub's egress to the devices that can only reach the world
    through it.

    A Zigbee lamp has no IP and therefore no direct egress, but its traffic
    does leave the house, through the bridge. Recording that as `inherited`
    keeps it visible without pretending it was observed first-hand.
    """
    by_id = {device.id: device for device in devices}
    children: dict[str, list[str]] = {}
    for device in devices:
        if device.via_device_id:
            children.setdefault(device.via_device_id, []).append(device.id)
    if not children:
        return []

    inherited: list[Conduit] = []
    for conduit in list(conduits):
        if conduit.evidence != "observed" or conduit.source.kind != "device":
            continue
        destination = destinations.get(conduit.destination_id)
        if destination is None or destination.kind not in INHERITABLE_KINDS:
            continue

        hub_id = conduit.source.id
        assert hub_id is not None
        for descendant in _descendants(hub_id, children):
            if by_id[descendant].ip:
                continue  # it reaches the world on its own; not second-hand
            inherited.append(
                Conduit(
                    id=f"cnd.{descendant}.{destination.fqdn}.inherited",
                    source=SourceRef("device", descendant),
                    destination_id=conduit.destination_id,
                    evidence="inherited",
                    encrypted=conduit.encrypted,
                    inherited_from=hub_id,
                )
            )
    return inherited


def _descendants(root: str, children: dict[str, list[str]]) -> list[str]:
    found: list[str] = []
    seen = {root}
    queue = list(children.get(root, ()))
    while queue:
        current = queue.pop()
        if current in seen:
            continue
        seen.add(current)
        found.append(current)
        queue.extend(children.get(current, ()))
    return found


def _forwarder_note(found: Any, facts: ObservedFacts) -> UnverifiedCheck:
    hours = facts.window_hours or 24
    share = f"{found.share * 100:.0f}"
    if found.tier in ("house", "single"):
        who = found.address + (f" ({found.label})" if found.label else "")
        identity = {
            "gateway_address": "It sits at the gateway address of its network, where a router lives.",
            "registry_model": f"Home Assistant lists it as {found.label}.",
            "name": f"The resolver names it {found.label}.",
        }.get(found.identity or "", "Nothing names it as a router.")
        single = (
            f" With {found.names} names it also looks like a single machine, the one host"
            " pointed at this resolver by hand while the rest of the network resolves"
            " elsewhere."
            if found.tier == "single"
            else ""
        )
        detail = (
            f"{who} is the source of {share}% of the queries the resolver heard in the"
            f" last {hours} hours, {found.names} distinct names, with {found.live_clients - 1}"
            f" other host(s) speaking in that time; of the {found.known} addresses the"
            f" leases and Home Assistant know, {found.known_heard} were heard. {identity}"
            " That is what the log looks like when one host answers DNS for everyone"
            " behind it: the router's DHCP hands out the router as DNS and the router"
            " forwards cache misses here (Fritz!Box, Google and Nest Wifi, eero, Deco and"
            " Orbi in router mode, most ISP boxes, over IPv6 as well when the box"
            " announces itself as DNSv6), a second router does NAT in front of this"
            f" resolver, or this resolver is only the router's upstream.{single} Either"
            f" way nothing behind {found.address} can be attributed to a device: the"
            " observed side of this report describes one host, every lease listed as"
            " silent may simply be behind it, and the checks that read the query log"
            " are withheld, not passed. Hand the resolver's own address to the clients"
            " in the router's DHCP DNS option (Fritz!Box: Home Network, Network, IPv4"
            " settings, Local DNS server, and Local DNSv6 server under IPv6; UniFi: the"
            " network's DHCP Name Server set to Manual; OpenWrt: dhcp_option 6; ASUS:"
            " LAN, DHCP Server, DNS Server 1) instead of the router's upstream field,"
            " which gives filtering and no attribution. On a router that cannot (Google"
            " and Nest Wifi, most ISP boxes), let the resolver serve DHCP and turn the"
            " router's off, or run the mesh in bridge mode behind a router that can."
            " Behind a second router doing NAT, bridge the outer box or move the"
            " resolver inside it."
        )
    elif found.tier == "loopback":
        detail = (
            f"Every query the resolver heard in the last {hours} hours came from"
            f" 127.0.0.1, {found.names} distinct names: a forwarder on the same machine"
            " (dnsmasq, systemd-resolved, the router's own DNS when the resolver runs"
            " on the router) sits in front of it and hands the queries in from"
            " loopback, so the log holds no client address at all. Point the clients"
            " at the resolver's listen address directly and stop the local forwarder,"
            " or make the forwarder pass the client address through, which dnsmasq"
            " cannot."
        )
    else:
        which = (
            "the gateway address of a container network"
            if found.tier == "container"
            else "a container bridge gateway or the router of a network numbered inside"
            " 172.16.0.0/12; nothing in the leases or the registry says which"
        )
        detail = (
            f"Every query the resolver heard in the last {hours} hours came from"
            f" {found.address}, {which}, {found.names} distinct names. A resolver in a"
            " container with published ports has its queries re-originated by the"
            " userland proxy from the bridge gateway, so the clients' addresses never"
            " reach the log. Not a router setting. Run the container with host"
            " networking or on a macvlan with its own LAN address (Synology Container"
            " Manager and QNAP Container Station: network mode host; Docker Engine:"
            " network_mode host; userland-proxy false only fixes the host-local and"
            " IPv6 paths)."
        )
    detail += (
        " This note clears the day after the clients start speaking for themselves;"
        " a lease renews on its own schedule and can lag behind."
    )
    return UnverifiedCheck(
        id="unv.resolver_forwarder",
        title="One host carries the resolver's log",
        reason="method_limit",
        detail=detail,
        subjects=[found.address],
    )


def _hosts(leases: Iterable[Lease]) -> str:
    return ", ".join(
        f"{lease.ip} ({lease.hostname})" if lease.hostname else lease.ip for lease in leases
    )


def _window_text(zero: ZeroCheck) -> str:
    window = zero.window
    if window is None or not window.entries:
        return "this poll read no entries"
    span = ""
    if window.oldest and window.newest:
        span = f", from {window.oldest} to {window.newest}"
    text = f"this poll read {window.entries} entries{span}"
    if window.truncated:
        text += ", and stopped at its page budget before the end of the log"
    return text


def _unlogged_note(unlogged: Iterable[str], leases: Iterable[Lease]) -> UnverifiedCheck:
    hosts = _hosts(leases)
    identifiers = ", ".join(unlogged)
    return UnverifiedCheck(
        id="unv.resolver_unlogged_clients",
        title="Clients the resolver is configured not to log",
        reason="method_limit",
        detail=(
            f"The resolver keeps these clients out of its query log by its own"
            f" configuration, AdGuard's ignore_querylog or Pi-hole's"
            f" excludeClients: {identifiers}."
            + (f" On this network that covers {hosts}." if hosts else "")
            + " Their absence from the log is a setting, not a behaviour, so it"
            " says nothing either way: whether they use the resolver cannot be"
            " read from its log, and they are neither reported as bypassing it"
            " nor counted as clean. Clear the setting on the resolver to bring"
            " them into view."
        ),
        subjects=[lease.ip for lease in leases],
    )


def _retention_text(zero: ZeroCheck) -> str:
    """What the log holds, as evidence, then how long it keeps things, as
    the ceiling: a 30 day setting on a log that holds 3 days is not 30
    days of evidence."""
    seconds = zero.retention_seconds
    kept = ""
    if seconds:
        days = seconds / 86400.0
        kept = (
            f", which it keeps for up to {days:g} days"
            if days >= 1
            else f", which it keeps for up to {seconds / 3600.0:g} hours"
        )
    begins = ""
    if zero.window is not None and zero.window.oldest and not zero.window.truncated:
        begins = f" and which begins at {zero.window.oldest}"
    return f"in everything the resolver's log holds{kept}{begins}"


def _silence_notes(
    zero: ZeroCheck,
    log_hidden: str | None = None,
    unlogged: Iterable[str] = (),
    forwarder: str | None = None,
) -> list[UnverifiedCheck]:
    """One note per outcome of the silence question, none of which is the
    same thing as another. Only the confirmed one drives a check."""
    notes: list[UnverifiedCheck] = []

    if zero.unlogged_leases:
        notes.append(_unlogged_note(unlogged, zero.unlogged_leases))

    if zero.silent_leases:
        reason = (
            f"With {forwarder} carrying the log, the likely reason is that they resolve"
            " through it, not a hardcoded server."
            if forwarder
            else "The usual reason is a DNS server hardcoded in the firmware."
        )
        notes.append(
            UnverifiedCheck(
                id="unv.resolver_bypassed",
                title="Devices with a lease and no query in the resolver's log",
                reason="method_limit",
                detail=(
                    "They hold a lease, or were seen on the wire by the resolver,"
                    " and there is no query from any of their addresses"
                    f" {_retention_text(zero)}: {_hosts(zero.silent_leases)}."
                    " Each one was confirmed with a targeted search of the full"
                    " log, not inferred from the window this poll read"
                    f" ({_window_text(zero)}). {reason} A device powered off for longer"
                    " than the log is kept looks the same, and so does one that"
                    " queries less often than that. Either way every DNS-based"
                    " check is blind on these hosts: they are not clean results,"
                    " they are invisible."
                ),
                subjects=[lease.ip for lease in zero.silent_leases],
            )
        )

    if zero.outside_window:
        notes.append(
            UnverifiedCheck(
                id="unv.observation_window",
                title="Hosts seen only before the window this poll read",
                reason="method_limit",
                detail=(
                    f"{_window_text(zero)[0].upper()}{_window_text(zero)[1:]}. These hosts queried the"
                    " resolver, but only earlier than that, or the network table"
                    " counts queries from them older than the log, so the walk"
                    f" never counted them: {_hosts(zero.outside_window)}. Devices that"
                    " phone home a few times a day fall past a short window on a"
                    " busy resolver. They are not bypassing it. The one entry the"
                    " confirmation found for each is folded into the totals, so"
                    " the host counts as seen from now on; the rest of its earlier"
                    " queries are not, and only what it asks from here on is"
                    " counted in full. Raising the page budget in Settings,"
                    " Collection, widens what each poll reads."
                ),
                subjects=[lease.ip for lease in zero.outside_window],
            )
        )

    pending = [*zero.unconfirmed, *zero.not_asked]
    if pending:
        if log_hidden and "client" in log_hidden:
            why = f"the resolver hides who asked ({log_hidden}), so no search can answer"
        elif zero.retention_seconds is not None and zero.retention_seconds < 7 * 86400:
            why = (
                f"the resolver keeps its log for {zero.retention_seconds / 3600:g} hours,"
                " too short to vouch for a device that phones home weekly"
            )
        elif zero.not_asked and not zero.unconfirmed:
            why = "this poll's budget of targeted searches ran out before reaching them"
        elif not zero.confirmed:
            why = "the confirmation could not be run"
        else:
            why = (
                "the confirmation did not answer for them"
                + (", or the budget ran out before reaching them" if zero.not_asked else "")
            )
        notes.append(
            UnverifiedCheck(
                id="unv.resolver_silence_unconfirmed",
                title="Hosts with no query in the walked window, unconfirmed",
                reason="method_limit",
                detail=(
                    f"No query from these hosts in the window this poll read"
                    f" ({_window_text(zero)}), and {why}, so whether the full log"
                    f" holds any is unknown: {_hosts(pending)}. They are not"
                    " reported as bypassing the resolver. The hosts not yet asked"
                    " go first on a later poll; while the resolver cannot answer,"
                    " no poll can."
                ),
                subjects=[lease.ip for lease in pending],
            )
        )

    if zero.stale_pairs:
        notes.append(
            UnverifiedCheck(
                id="unv.resolver_stale_pairs",
                title="Addresses last seen on the wire before the log began",
                reason="method_limit",
                detail=(
                    "The resolver's network table remembers these addresses, but"
                    " it last saw them before anything the query log holds"
                    f" ({_retention_text(zero)}): {_hosts(zero.stale_pairs)}. As"
                    " far as the log can tell they belong to something that left"
                    " the network, so they were not asked about: a search could"
                    " only ever answer no, and no would mean nothing."
                ),
                subjects=[lease.ip for lease in zero.stale_pairs],
            )
        )

    if zero.unleased_clients:
        hosts = ", ".join(zero.unleased_clients)
        supervisor = any(
            c.startswith("172.30.32.") or c.startswith("172.30.33.") or c.startswith("127.")
            for c in zero.unleased_clients
        )
        notes.append(
            UnverifiedCheck(
                id="unv.resolver_unleased_clients",
                title="Clients that asked the resolver but hold no lease",
                reason="method_limit",
                detail=(
                    f"The resolver answered these addresses and none holds a lease"
                    f" or a pair in the address table: {hosts}. Their queries are"
                    " counted, attributed to an unknown host, and cannot be tied"
                    " to a device."
                    + (
                        " One of them is on Home Assistant's own supervisor network:"
                        " when the resolver runs on this host, Home Assistant's queries"
                        " reach it from there and not from the host's LAN lease, so"
                        " that lease can look silent while Home Assistant is using the"
                        " resolver all along."
                        if supervisor
                        else ""
                    )
                ),
                subjects=list(zero.unleased_clients),
            )
        )
    return notes


def _notes(
    scan: Scan,
    facts: ObservedFacts,
    classifier: DomainClassifier,
    devices: list[Device],
    ignored: int,
    device_by_ip: dict[str, str] | None = None,
    supervisor_seen: dict[str, tuple[int, set[str]]] | None = None,
) -> list[UnverifiedCheck]:
    notes: list[UnverifiedCheck] = []

    forwarder = find_forwarder(facts, devices, device_by_ip or {}, classifier)
    if forwarder is not None:
        notes.append(_forwarder_note(forwarder, facts))

    if supervisor_seen:
        addresses = sorted(supervisor_seen)
        queries = sum(q for q, _ in supervisor_seen.values())
        names = set().union(*(n for _, n in supervisor_seen.values()))
        notes.append(
            UnverifiedCheck(
                id="unv.supervisor_dns",
                title="Home Assistant's own queries arrive from the Supervisor's DNS",
                reason="method_limit",
                detail=(
                    "Home Assistant, the Supervisor and every add-on resolve through"
                    " the Supervisor's DNS plugin at 172.30.32.3, and an add-on that"
                    f" resolves on its own shows as another 172.30.33.x address: {queries}"
                    f" queries to {len(names)} names arrived from {', '.join(addresses)}."
                    " They are Home Assistant's own traffic and are recorded as such,"
                    " not as an unknown host, and they cannot be split per add-on: an"
                    " add-on with a hardcoded phone-home looks the same as a core"
                    " integration. With the plugin's fallback enabled, the default,"
                    " anything this resolver refuses or fails, and everything while it"
                    " is down, is asked again over DNS over TLS to Cloudflare and never"
                    " appears here. A lease named homeassistant that shows as silent is"
                    " expected: the host reaches the resolver as 172.30.32.3, not from"
                    " its LAN address. To close the Cloudflare path: ha dns options"
                    " --fallback=false."
                ),
                subjects=addresses,
            )
        )

    if not facts.zero.dhcp_available:
        notes.append(
            UnverifiedCheck(
                id="unv.dhcp_leases_unavailable",
                title="No address table: the zero check cannot run",
                reason="missing_data",
                detail=(
                    "The Home Assistant registry knows MACs, the query log knows IPs:"
                    " something has to hold both. DHCP leases from the resolver are"
                    " one witness, Pi-hole's network table is another, and a router"
                    " based device tracker inside Home Assistant is the third:"
                    " whatever the trackers already know is used, and the rest of the"
                    " observations stay attributed to an unknown host. Nor can the"
                    " resolver's clients be compared against the devices on the"
                    " network, so an appliance with a hardcoded DNS server never"
                    " surfaces. For full coverage: let AdGuard Home serve DHCP, or"
                    " use a Pi-hole, which records the pairs it sees on the wire"
                    " whoever serves DHCP. This check did not fail, it did not run."
                ),
            )
        )
    else:
        notes.extend(
            _silence_notes(
                facts.zero, facts.log_hidden, facts.unlogged,
                forwarder.address if forwarder is not None else None,
            )
        )

    if facts.unlogged and not facts.zero.dhcp_available:
        # Without a table nothing is compared, but the operator's exclusions
        # are still a fact about what the log can show.
        notes.append(_unlogged_note(facts.unlogged, ()))

    if facts.log_hidden:
        notes.append(
            UnverifiedCheck(
                id="unv.resolver_log_hidden",
                title="The resolver's privacy level hides the log",
                reason="method_limit",
                detail=(
                    f"On this resolver {facts.log_hidden}. What the log does not"
                    " show cannot be attributed to anything: the observed side of"
                    " this report is empty by the resolver's own setting, not"
                    " because nothing was asked. Lower the privacy level to 0 in"
                    " the resolver's settings to make the log readable."
                ),
            )
        )

    without_mac = sum(1 for device in devices if not device.mac and not device.ip)
    if without_mac:
        notes.append(
            UnverifiedCheck(
                id="unv.devices_without_identifier",
                title="Devices with no MAC in the registry",
                reason="missing_data",
                detail=(
                    f"{without_mac} of {len(devices)} devices expose no MAC: they"
                    " cannot be correlated against the query log. Any direct egress"
                    " from them would go unseen, so the 'local with egress' quadrant"
                    " is a minimum, not a total."
                ),
            )
        )

    if classifier.unknown:
        sample = ", ".join(sorted(classifier.unknown)[:8])
        more = "" if len(classifier.unknown) <= 8 else f" (+{len(classifier.unknown) - 8})"
        notes.append(
            UnverifiedCheck(
                id="unv.unclassified_domains",
                title="Unclassified domains",
                reason="missing_data",
                detail=(
                    f"{len(classifier.unknown)} domains with no rule: {sample}{more}."
                    " They stay counted and visible rather than falling into a"
                    " catch-all. Most of a home resolver's log is phones and"
                    " computers browsing, and naming every site anybody visits is"
                    " not what this list is for: what matters is a domain reached"
                    " by a device in the registry. Extend the domain list to name"
                    " the ones that are."
                ),
            )
        )

    notes.append(
        UnverifiedCheck(
            id="unv.doh",
            title="DNS over HTTPS traffic",
            reason="method_limit",
            detail=(
                "A device that encrypts its DNS queries too (DoH, port 443) is"
                " indistinguishable from ordinary traffic. A declared structural"
                " gap: this approach does not cover it."
            ),
        )
    )

    return notes
