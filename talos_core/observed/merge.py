"""Join the observed side onto a declared scan.

This is where `evidence: observed` and `evidence: inherited` enter the
document, and where the tool stops describing what Home Assistant already
knows and starts adding something.

The join runs on the MAC. A device registry has no address, and a query log
has no MAC: **the DHCP leases are the only place the two meet.** Without them
Talos can still see that someone spoke to a vendor, but not which device it
was, and every observation falls back to `unknown_host`. That degradation is
reported, never hidden.
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
    devices = []
    for device in scan.devices:
        ip = lease_ip_by_mac.get(device.mac) if device.mac else device.ip
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
            method="mac_dhcp",
        ),
        unverified=[*scan.unverified, *_notes(scan, facts, classifier, devices, ignored)],
    )


def _inherit_through_hubs(
    devices: list[Device],
    destinations: dict[str, Destination],
    conduits: list[Conduit],
) -> list[Conduit]:
    """Attribute a hub's egress to the devices that can only reach the world
    through it.

    A Zigbee lamp has no IP and therefore no direct egress, but its traffic
    does leave the house — through the bridge. Recording that as `inherited`
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
                title="Lease DHCP non disponibili: controllo zero non eseguibile",
                reason="missing_data",
                detail=(
                    "Il registro di Home Assistant conosce i MAC, il query log conosce"
                    " gli IP: le lease DHCP sono l'unico punto in cui i due si"
                    " incontrano. Senza, ogni osservazione resta attribuita a un host"
                    " sconosciuto e Talos puo' dire che qualcuno ha contattato un"
                    " produttore, ma non quale dispositivo sia. Non e' possibile"
                    " nemmeno confrontare i client visti dal resolver con i"
                    " dispositivi presenti in rete, quindi un apparecchio con DNS"
                    " scritto nel firmware non emerge. Per una copertura piena:"
                    " attiva il server DHCP di AdGuard Home, oppure fornisci le lease"
                    " del router. Questo controllo non e' fallito, non e' stato"
                    " eseguito."
                ),
            )
        )
    elif facts.zero.silent_leases:
        hosts = ", ".join(f"{lease.ip} ({lease.mac})" for lease in facts.zero.silent_leases)
        notes.append(
            UnverifiedCheck(
                id="unv.resolver_bypassed",
                title="Dispositivi che non passano dal resolver",
                reason="method_limit",
                detail=(
                    f"Hanno una lease DHCP ma non hanno mai interrogato AdGuard: {hosts}."
                    " Usano un DNS scritto nel firmware. Su questi host ogni controllo"
                    " basato sul DNS e' cieco: non sono risultati puliti, sono invisibili."
                ),
                subjects=[lease.ip for lease in facts.zero.silent_leases],
            )
        )

    without_mac = sum(1 for device in devices if not device.mac and not device.ip)
    if without_mac:
        notes.append(
            UnverifiedCheck(
                id="unv.devices_without_identifier",
                title="Dispositivi senza MAC nel registry",
                reason="missing_data",
                detail=(
                    f"{without_mac} dispositivi su {len(devices)} non espongono un MAC:"
                    " la correlazione con il query log non e' possibile. Un eventuale"
                    " egress diretto di questi dispositivi non sarebbe visto. Il"
                    " quadrante 'locale con egress' e' quindi un minimo, non un totale."
                ),
            )
        )

    if classifier.unknown:
        sample = ", ".join(sorted(classifier.unknown)[:8])
        more = "" if len(classifier.unknown) <= 8 else f" (+{len(classifier.unknown) - 8})"
        notes.append(
            UnverifiedCheck(
                id="unv.unclassified_domains",
                title="Domini non classificati",
                reason="missing_data",
                detail=(
                    f"{len(classifier.unknown)} domini senza una regola: {sample}{more}."
                    " Restano contati e visibili invece di finire in un catch-all."
                    " Estendibili aggiungendo regole alla lista domini."
                ),
            )
        )

    notes.append(
        UnverifiedCheck(
            id="unv.doh",
            title="Traffico DNS su HTTPS",
            reason="method_limit",
            detail=(
                "Un dispositivo che cifra anche le proprie richieste DNS (DoH, porta"
                " 443) e' indistinguibile dal traffico normale. Buco strutturale"
                " dichiarato: questo approccio non lo copre."
            ),
        )
    )

    return notes
