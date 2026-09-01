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

from ..const import PHONE_HOME_DESTINATION_KINDS
from ..zones import ZoneMap
from ..model import Conduit, Correlation, Destination, Device, Scan, SourceRef, UnverifiedCheck
from .classify import DomainClassifier
from .mapping import ObservedFacts

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

    lease_ip_by_mac = {lease.mac: lease.ip for lease in facts.leases}
    from_leases = 0
    from_declared = 0
    devices = []
    for device in scan.devices:
        leased = lease_ip_by_mac.get(device.mac) if device.mac else None
        # A lease is the fresher of the two, so it wins; the address Home
        # Assistant already held covers everything the leases do not reach.
        ip = leased or device.ip
        if leased:
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

    return Scan(
        schema_version=scan.schema_version,
        generated_at=scan.generated_at,
        collector=scan.collector,
        ha_version=scan.ha_version,
        integrations=list(scan.integrations),
        devices=devices,
        destinations=sorted(destinations.values(), key=lambda d: d.id),
        conduits=conduits,
        correlation=Correlation(
            devices_total=len(devices),
            devices_correlated=sum(1 for d in devices if d.ip),
            method=_method(from_leases, from_declared),
        ),
        unverified=[*scan.unverified, *_notes(scan, facts, classifier, devices, ignored)],
    )


def _method(from_leases: int, from_declared: int) -> str:
    """Name the sources that actually carried the join, not the ones that
    were available. A method nobody used has no business in the report."""
    used = []
    if from_leases:
        used.append("dhcp")
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


def _notes(
    scan: Scan,
    facts: ObservedFacts,
    classifier: DomainClassifier,
    devices: list[Device],
    ignored: int,
) -> list[UnverifiedCheck]:
    notes: list[UnverifiedCheck] = []

    if not facts.zero.dhcp_available:
        notes.append(
            UnverifiedCheck(
                id="unv.dhcp_leases_unavailable",
                title="DHCP leases unavailable: the zero check cannot run",
                reason="missing_data",
                detail=(
                    "The Home Assistant registry knows MACs, the query log knows IPs:"
                    " DHCP leases are one of the two places the two meet, and a"
                    " router based device tracker inside Home Assistant is the other:"
                    " whatever the trackers already know is used, and the rest of the"
                    " observations stay attributed to an unknown host. Nor can the"
                    " resolver's clients be compared against the"
                    " devices on the network, so an appliance with a hardcoded DNS"
                    " server never surfaces. For full coverage: enable AdGuard Home's"
                    " DHCP server, or supply the router's leases. This check did not"
                    " fail, it did not run."
                ),
            )
        )
    elif facts.zero.silent_leases:
        hosts = ", ".join(f"{lease.ip} ({lease.mac})" for lease in facts.zero.silent_leases)
        notes.append(
            UnverifiedCheck(
                id="unv.resolver_bypassed",
                title="Devices bypassing the resolver",
                reason="method_limit",
                detail=(
                    f"They hold a DHCP lease but have never queried AdGuard: {hosts}."
                    " They use a DNS server hardcoded in their firmware. Every"
                    " DNS-based check is blind on these hosts: they are not clean"
                    " results, they are invisible."
                ),
                subjects=[lease.ip for lease in facts.zero.silent_leases],
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
                    " catch-all. Extend the domain list to name them."
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
