"""The posture check engine.

Severity and remediation live in `data/checks.json`, separate from this file,
so the wording and the weighting can be tuned without touching code. The
selectors are a deliberately small vocabulary rather than a general rule
language: a DSL rich enough to express arbitrary logic is a programming
language wearing a configuration file's clothes, and it would be worse at
being either.

The part that matters most is `requires`. A check whose precondition is not
met is **not** a pass: it goes to the unverified list with the reason. An
empty "local with egress" quadrant means nothing at all until something has
actually been observed, and reporting it as green would be the exact failure
this project exists to avoid.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable, Sequence

from .const import PHONE_HOME_DESTINATION_KINDS
from .model import Scan, UnverifiedCheck

DEFAULT_CHECKS_PATH = Path(__file__).resolve().parent / "data" / "checks.json"

SEVERITIES: tuple[str, ...] = ("high", "medium", "low")

# What a precondition means, in one line each, for the message the user reads
# when a check could not run.
PRECONDITION_REASONS: dict[str, str] = {
    "observed_evidence": (
        "nothing was observed in this scan: without a query log, an empty cell"
        " does not mean an absence of traffic"
    ),
    "zones_configured": (
        "no network ranges configured: Talos does not know which subnet is the"
        " trusted LAN and which is the IoT VLAN"
    ),
    "dhcp_leases": (
        "DHCP leases unavailable: the resolver's clients cannot be compared"
        " against the devices present on the network"
    ),
    "manifests": (
        "integration manifests unreadable: iot_class and is_built_in are not"
        " trustworthy in this scan"
    ),
    "mqtt_clients": (
        "the broker reported no client list: without $SYS there is nothing to"
        " compare against the registry, and an empty list is not an answer"
    ),
    "entry_endpoints": (
        "no config entry stated where it connects: from outside Home Assistant"
        " that data is not exposed, so whether a connection carries credentials"
        " is unknown rather than absent"
    ),
}


@dataclass(frozen=True, slots=True)
class CheckResult:
    """One executed check. `passed` only ever means it actually ran."""

    id: str
    title: str
    severity: str
    passed: bool
    subject_kind: str
    subjects: tuple[str, ...]
    detail: str
    remediation: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "severity": self.severity,
            "passed": self.passed,
            "subject_kind": self.subject_kind,
            "subjects": list(self.subjects),
            "detail": self.detail,
            "remediation": self.remediation,
        }


@dataclass(frozen=True, slots=True)
class CheckReport:
    """Three buckets that never bleed into each other."""

    results: tuple[CheckResult, ...] = ()
    unverified: tuple[UnverifiedCheck, ...] = ()

    @property
    def failed(self) -> tuple[CheckResult, ...]:
        order = {severity: index for index, severity in enumerate(SEVERITIES)}
        return tuple(
            sorted(
                (result for result in self.results if not result.passed),
                key=lambda result: (order.get(result.severity, 99), result.id),
            )
        )

    @property
    def passed(self) -> tuple[CheckResult, ...]:
        return tuple(result for result in self.results if result.passed)

    def failed_by_severity(self, severity: str) -> tuple[CheckResult, ...]:
        return tuple(result for result in self.failed if result.severity == severity)

    @property
    def counts(self) -> dict[str, int]:
        return {
            "failed_high": len(self.failed_by_severity("high")),
            "failed_medium": len(self.failed_by_severity("medium")),
            "failed_low": len(self.failed_by_severity("low")),
            "passed": len(self.passed),
            "unverified": len(self.unverified),
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "counts": self.counts,
            "failed": [result.to_dict() for result in self.failed],
            "passed": [result.to_dict() for result in self.passed],
            "unverified": [check.to_dict() for check in self.unverified],
        }


class CheckEngine:
    """Runs the rule file against a scan and its matrix."""

    def __init__(self, rules: Iterable[dict[str, Any]]) -> None:
        self._rules = [rule for rule in rules if rule.get("id")]

    @classmethod
    def load(cls, path: str | Path | None = None) -> CheckEngine:
        source = Path(path) if path else DEFAULT_CHECKS_PATH
        text = source.read_text(encoding="utf-8")
        if source.suffix.lower() in (".yaml", ".yml"):
            try:
                import yaml
            except ImportError as err:  # pragma: no cover - depends on the install
                raise RuntimeError(
                    f"{source.name} needs PyYAML; use a .json rules file instead"
                ) from err
            data = yaml.safe_load(text)
        else:
            data = json.loads(text)
        return cls((data or {}).get("checks") or ())

    def run(self, scan: Scan, matrix: Any) -> CheckReport:
        context = _Context(scan)
        results: list[CheckResult] = []
        unverified: list[UnverifiedCheck] = list(scan.unverified)

        for rule in self._rules:
            declared = rule.get("unverifiable")
            if declared:
                unverified.append(
                    UnverifiedCheck(
                        id=rule["id"],
                        title=rule.get("title") or rule["id"],
                        reason=declared.get("reason") or "missing_data",
                        detail=declared.get("detail") or "",
                    )
                )
                continue

            missing = [
                name
                for name in (rule.get("requires") or ())
                if not context.precondition(name)
            ]
            if missing:
                unverified.append(
                    UnverifiedCheck(
                        id=rule["id"],
                        title=rule.get("title") or rule["id"],
                        reason="missing_data",
                        detail=(
                            "Check not run: "
                            + "; ".join(
                                PRECONDITION_REASONS.get(name, name) for name in missing
                            )
                            + ". This is not a pass."
                        ),
                    )
                )
                continue

            subject_kind, subjects = _select(rule.get("selector") or {}, scan, matrix, context)
            results.append(
                CheckResult(
                    id=rule["id"],
                    title=rule.get("title") or rule["id"],
                    severity=rule.get("severity") or "low",
                    passed=not subjects,
                    subject_kind=subject_kind,
                    subjects=tuple(subjects),
                    detail=rule.get("detail") or "",
                    remediation=rule.get("remediation") or "",
                )
            )

        return CheckReport(results=tuple(results), unverified=tuple(unverified))


@lru_cache(maxsize=1)
def default_engine() -> CheckEngine:
    """Cached: the rule file is read once per process, not once per scan."""
    return CheckEngine.load()


class _Context:
    """Facts the selectors and preconditions share, computed once."""

    def __init__(self, scan: Scan) -> None:
        self.scan = scan
        self.unverified_ids = {check.id: check for check in scan.unverified}
        self.destinations = {destination.id: destination for destination in scan.destinations}

        self.phone_home_devices: set[str] = set()
        self.has_observation = False
        for conduit in scan.conduits:
            if conduit.evidence == "observed":
                self.has_observation = True
            destination = self.destinations.get(conduit.destination_id)
            if destination is None or destination.kind not in PHONE_HOME_DESTINATION_KINDS:
                continue
            if conduit.source.kind == "device" and conduit.source.id:
                self.phone_home_devices.add(conduit.source.id)

    def precondition(self, name: str) -> bool:
        if name == "observed_evidence":
            return self.has_observation
        if name == "zones_configured":
            return any(device.zone != "unknown" for device in self.scan.devices)
        if name == "dhcp_leases":
            return "unv.dhcp_leases_unavailable" not in self.unverified_ids
        if name == "mqtt_clients":
            return bool(self.scan.mqtt and self.scan.mqtt.available)
        if name == "entry_endpoints":
            # None means the question does not apply. If it applies to nobody,
            # the collector could not read it, and silence is not a pass.
            return any(
                integration.authenticated is not None
                for integration in self.scan.integrations
            )
        if name == "manifests":
            return not (
                {"unv.manifests_unavailable", "unv.manifest_list_unreadable"}
                & set(self.unverified_ids)
            )
        # An unknown precondition is a rule-file mistake, and must not silently
        # let a check run on an assumption nobody checked.
        return False


def _select(
    selector: dict[str, Any], scan: Scan, matrix: Any, context: _Context
) -> tuple[str, Sequence[str]]:
    kind = selector.get("type")

    if kind == "matrix_quadrant":
        quadrant = selector.get("quadrant") or ""
        return "device", tuple(getattr(matrix, quadrant, ()) or ())

    if kind == "integration_where":
        wanted_classes = set(selector.get("iot_class_in") or ())
        excluded_states = set(selector.get("state_not_in") or ())
        built_in = selector.get("is_built_in")
        wanted_domains = set(selector.get("domain_in") or ())
        authenticated = selector.get("authenticated")
        matched = [
            integration.id
            for integration in scan.integrations
            if (built_in is None or integration.is_built_in is bool(built_in))
            and (not wanted_classes or integration.iot_class in wanted_classes)
            and (not excluded_states or integration.state not in excluded_states)
            and (not wanted_domains or integration.domain in wanted_domains)
            # `is` on purpose: None means the question does not apply to this
            # entry, and must not match a check looking for False.
            and (authenticated is None or integration.authenticated is bool(authenticated))
        ]
        return "integration", tuple(sorted(matched))

    if kind == "device_where":
        zones = set(selector.get("zone_in") or ())
        needs_egress = bool(selector.get("has_phone_home_egress"))
        matched = [
            device.id
            for device in scan.devices
            if (not zones or device.zone in zones)
            and (not needs_egress or device.id in context.phone_home_devices)
        ]
        return "device", tuple(sorted(matched))

    if kind == "mqtt_client_where":
        # A client the broker knows and the registry does not. Reported by
        # client id, because that is the only name the broker has for it.
        facts = scan.mqtt
        if facts is None:
            return "unknown", ()
        matched = selector.get("matched")
        clients = [
            client.client_id
            for client in facts.clients
            if matched is None or bool(client.matched) is bool(matched)
        ]
        return "unknown", tuple(sorted(clients))

    if kind == "unverified_present":
        check_id = selector.get("check_id") or ""
        note = context.unverified_ids.get(check_id)
        if note is None:
            return "note", ()
        # Prefer the structured subjects the note recorded; fall back to its
        # own id so the finding still points somewhere.
        return ("host", tuple(note.subjects)) if note.subjects else ("note", (check_id,))

    # An unrecognised selector must not quietly produce an empty, passing set.
    raise ValueError(f"unsupported selector type: {kind!r}")
