"""Schema, reference and coherence validation for a Talos scan document.

Runs on the raw parsed JSON, not on the model, so that a malformed document
produces a list of addressed findings instead of an exception from the first
bad field. Three passes, in order, because each depends on the previous one
having weeded out entries it cannot reason about:

    1. schema      shape, types, vocabularies, duplicate ids
    2. references  every id resolves, the via_device chain is acyclic
    3. coherence   the document does not contradict its own invariants

Findings never abort the run: the caller gets everything wrong with the
document in one go.
"""

from __future__ import annotations

from typing import Any, Iterable, NamedTuple, Sequence

from .const import (
    COLLECTOR_SOURCES,
    DESTINATION_KINDS,
    EVIDENCE,
    FILTER_STATUS,
    IOT_CLASSES,
    OBSERVED_ONLY_FIELDS,
    SOURCE_KINDS,
    SUPPORTED_SCHEMA_VERSIONS,
    TRANSPORTS,
    UNVERIFIED_REASONS,
    ZONES,
)
from .errors import (
    E_CORRELATION_RANGE,
    E_DUPLICATE_ID,
    E_ENTITY_COUNT_BELOW_DEVICES,
    E_INHERITED_FROM_MISPLACED,
    E_INHERITED_NO_BASIS,
    E_INHERITED_NO_PARENT,
    E_INHERITED_NOT_ANCESTOR,
    E_OBSERVED_FIELD_MISPLACED,
    E_OBSERVED_INCOMPLETE,
    E_OBSERVED_WITHOUT_IP,
    E_REF_DESTINATION,
    E_REF_INHERITED_FROM,
    E_REF_INTEGRATION,
    E_REF_SOURCE,
    E_REF_VIA_DEVICE,
    E_SCHEMA_ENUM,
    E_SCHEMA_MISSING,
    E_SCHEMA_RANGE,
    E_SCHEMA_TYPE,
    E_SCHEMA_VERSION,
    E_UNKNOWN_HOST_NOT_OBSERVED,
    E_VIA_CYCLE,
    Finding,
)

_STR = (str,)
_INT = (int,)
_BOOL = (bool,)
_LIST = (list,)
_DICT = (dict,)


class _Entry(NamedTuple):
    """An indexed entry and the JSON path it came from.

    The path travels alongside the data rather than inside it: writing it into
    the entry would leave a private key in a document the caller may well
    re-serialise.
    """

    path: str
    data: dict[str, Any]


_Index = dict[str, _Entry]


def validate(raw: Any) -> list[Finding]:
    """Return every problem found in a parsed scan document, in document order."""
    out: list[Finding] = []

    if not isinstance(raw, dict):
        return [Finding(E_SCHEMA_TYPE, "$", "document root must be an object")]

    _check_root(out, raw)
    integrations = _check_integrations(out, raw)
    devices = _check_devices(out, raw)
    destinations = _check_destinations(out, raw)
    conduits = _check_conduits(out, raw)
    _check_correlation(out, raw)
    _check_unverified(out, raw)

    _check_references(out, integrations, devices, destinations, conduits)
    _check_coherence(out, devices, conduits)
    _check_entity_counts(out, integrations, devices)

    return out


def is_valid(raw: Any) -> bool:
    return not validate(raw)


# ── field helpers ─────────────────────────────────────────────────────────


def _field(
    out: list[Finding],
    path: str,
    obj: dict[str, Any],
    key: str,
    types: tuple[type, ...],
    *,
    required: bool = True,
    nullable: bool = False,
    enum: Iterable[str] | None = None,
    minimum: int | None = None,
) -> Any:
    """Check one field and return it when usable, else None.

    Returning None on failure lets callers keep walking the document instead
    of branching on every field.
    """
    where = f"{path}.{key}"

    if key not in obj:
        if required:
            out.append(Finding(E_SCHEMA_MISSING, where, f"required field '{key}' is missing"))
        return None

    value = obj[key]

    if value is None:
        if not nullable:
            out.append(Finding(E_SCHEMA_TYPE, where, f"'{key}' must not be null"))
        return None

    # bool is a subclass of int; an int field must not silently accept True.
    ok = isinstance(value, types)
    if ok and isinstance(value, bool) and bool not in types:
        ok = False
    if not ok:
        names = " or ".join(t.__name__ for t in types)
        out.append(Finding(E_SCHEMA_TYPE, where, f"'{key}' must be {names}"))
        return None

    if enum is not None and value not in enum:
        allowed = ", ".join(sorted(enum))
        out.append(Finding(E_SCHEMA_ENUM, where, f"'{value}' is not one of: {allowed}"))
        return None

    if minimum is not None and isinstance(value, int) and value < minimum:
        out.append(Finding(E_SCHEMA_RANGE, where, f"'{key}' must be >= {minimum}"))
        return None

    return value


def _collection(out: list[Finding], raw: dict[str, Any], key: str) -> list[Any]:
    value = raw.get(key)
    if key not in raw:
        out.append(Finding(E_SCHEMA_MISSING, f"$.{key}", f"required field '{key}' is missing"))
        return []
    if not isinstance(value, list):
        out.append(Finding(E_SCHEMA_TYPE, f"$.{key}", f"'{key}' must be a list"))
        return []
    return value


def _entries(
    out: list[Finding], items: Sequence[Any], key: str
) -> list[tuple[int, dict[str, Any]]]:
    """Keep the entries that are objects; report the ones that are not."""
    kept: list[tuple[int, dict[str, Any]]] = []
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            out.append(Finding(E_SCHEMA_TYPE, f"$.{key}[{index}]", "entry must be an object"))
            continue
        kept.append((index, item))
    return kept


def _register_id(
    out: list[Finding], seen: _Index, entry_id: Any, path: str, entry: dict[str, Any]
) -> None:
    if not isinstance(entry_id, str) or not entry_id:
        return
    if entry_id in seen:
        out.append(Finding(E_DUPLICATE_ID, f"{path}.id", f"id '{entry_id}' is already in use"))
        return
    seen[entry_id] = _Entry(path, entry)


# ── schema pass ───────────────────────────────────────────────────────────


def _check_root(out: list[Finding], raw: dict[str, Any]) -> None:
    version = raw.get("schema_version")
    if not isinstance(version, str) or version not in SUPPORTED_SCHEMA_VERSIONS:
        supported = ", ".join(sorted(SUPPORTED_SCHEMA_VERSIONS))
        out.append(
            Finding(
                E_SCHEMA_VERSION,
                "$.schema_version",
                f"'{version}' is not a supported schema version (supported: {supported})",
            )
        )
    _field(out, "$", raw, "generated_at", _STR)
    _field(out, "$", raw, "collector", _STR, enum=COLLECTOR_SOURCES)
    _field(out, "$", raw, "ha_version", _STR, required=False, nullable=True)


def _check_integrations(out: list[Finding], raw: dict[str, Any]) -> _Index:
    seen: _Index = {}
    for index, entry in _entries(out, _collection(out, raw, "integrations"), "integrations"):
        path = f"$.integrations[{index}]"
        entry_id = _field(out, path, entry, "id", _STR)
        _field(out, path, entry, "domain", _STR)
        _field(out, path, entry, "title", _STR)
        _field(out, path, entry, "iot_class", _STR, enum=IOT_CLASSES)
        _field(out, path, entry, "is_built_in", _BOOL)
        _field(out, path, entry, "state", _STR, required=False)
        _field(out, path, entry, "entity_count", _INT, required=False, minimum=0)
        deps = _field(out, path, entry, "dependencies", _LIST, required=False)
        for d_index, dep in enumerate(deps or []):
            if not isinstance(dep, str):
                out.append(
                    Finding(
                        E_SCHEMA_TYPE,
                        f"{path}.dependencies[{d_index}]",
                        "dependency must be a string",
                    )
                )
        _register_id(out, seen, entry_id, path, entry)
    return seen


def _check_devices(out: list[Finding], raw: dict[str, Any]) -> _Index:
    seen: _Index = {}
    for index, entry in _entries(out, _collection(out, raw, "devices"), "devices"):
        path = f"$.devices[{index}]"
        entry_id = _field(out, path, entry, "id", _STR)
        _field(out, path, entry, "integration_id", _STR)
        _field(out, path, entry, "name", _STR)
        _field(out, path, entry, "transport", _STR, enum=TRANSPORTS)
        for optional in ("manufacturer", "model", "area", "mac", "ip", "origin"):
            _field(out, path, entry, optional, _STR, required=False, nullable=True)
        _field(out, path, entry, "zone", _STR, required=False, nullable=True, enum=ZONES)
        _field(out, path, entry, "via_device_id", _STR, required=False, nullable=True)
        _field(out, path, entry, "entity_count", _INT, required=False, minimum=0)
        _register_id(out, seen, entry_id, path, entry)
    return seen


def _check_destinations(out: list[Finding], raw: dict[str, Any]) -> _Index:
    seen: _Index = {}
    for index, entry in _entries(out, _collection(out, raw, "destinations"), "destinations"):
        path = f"$.destinations[{index}]"
        entry_id = _field(out, path, entry, "id", _STR)
        _field(out, path, entry, "fqdn", _STR)
        _field(out, path, entry, "kind", _STR, enum=DESTINATION_KINDS)
        _field(out, path, entry, "vendor", _STR, required=False, nullable=True)
        _register_id(out, seen, entry_id, path, entry)
    return seen


def _check_conduits(out: list[Finding], raw: dict[str, Any]) -> _Index:
    seen: _Index = {}
    for index, entry in _entries(out, _collection(out, raw, "conduits"), "conduits"):
        path = f"$.conduits[{index}]"
        entry_id = _field(out, path, entry, "id", _STR)
        _field(out, path, entry, "destination_id", _STR)
        _field(out, path, entry, "evidence", _STR, enum=EVIDENCE)
        _field(out, path, entry, "protocol", _STR, required=False, nullable=True)
        _field(out, path, entry, "port", _INT, required=False, nullable=True, minimum=0)
        _field(out, path, entry, "first_seen", _STR, required=False, nullable=True)
        _field(out, path, entry, "last_seen", _STR, required=False, nullable=True)
        _field(out, path, entry, "query_count", _INT, required=False, nullable=True, minimum=0)
        _field(
            out,
            path,
            entry,
            "filter_status",
            _STR,
            required=False,
            nullable=True,
            enum=FILTER_STATUS,
        )
        _field(out, path, entry, "inherited_from", _STR, required=False, nullable=True)

        # encrypted is deliberately tri-state: unknown is a real answer here,
        # and collapsing it to false would invent a fact we do not have.
        if "encrypted" in entry and entry["encrypted"] is not None:
            value = entry["encrypted"]
            if not (isinstance(value, bool) or value == "unknown"):
                out.append(
                    Finding(
                        E_SCHEMA_ENUM,
                        f"{path}.encrypted",
                        "'encrypted' must be true, false or \"unknown\"",
                    )
                )

        source = _field(out, path, entry, "source", _DICT)
        if source is not None:
            kind = _field(out, f"{path}.source", source, "kind", _STR, enum=SOURCE_KINDS)
            source_id = _field(
                out, f"{path}.source", source, "id", _STR, required=False, nullable=True
            )
            # ha_core is the only source that identifies itself by kind alone.
            if kind is not None and kind != "ha_core" and not source_id:
                out.append(
                    Finding(
                        E_SCHEMA_MISSING,
                        f"{path}.source.id",
                        f"source of kind '{kind}' requires an id",
                    )
                )

        _register_id(out, seen, entry_id, path, entry)
    return seen


def _check_correlation(out: list[Finding], raw: dict[str, Any]) -> None:
    correlation = raw.get("correlation")
    if "correlation" not in raw:
        out.append(
            Finding(E_SCHEMA_MISSING, "$.correlation", "required field 'correlation' is missing")
        )
        return
    if not isinstance(correlation, dict):
        out.append(Finding(E_SCHEMA_TYPE, "$.correlation", "'correlation' must be an object"))
        return

    total = _field(out, "$.correlation", correlation, "devices_total", _INT, minimum=0)
    matched = _field(out, "$.correlation", correlation, "devices_correlated", _INT, minimum=0)
    _field(out, "$.correlation", correlation, "method", _STR, required=False)

    if isinstance(total, int) and isinstance(matched, int) and matched > total:
        out.append(
            Finding(
                E_CORRELATION_RANGE,
                "$.correlation.devices_correlated",
                f"{matched} correlated of {total} total",
            )
        )


def _check_unverified(out: list[Finding], raw: dict[str, Any]) -> None:
    seen: _Index = {}
    for index, entry in _entries(out, _collection(out, raw, "unverified"), "unverified"):
        path = f"$.unverified[{index}]"
        entry_id = _field(out, path, entry, "id", _STR)
        _field(out, path, entry, "title", _STR)
        _field(out, path, entry, "reason", _STR, enum=UNVERIFIED_REASONS)
        _field(out, path, entry, "detail", _STR, required=False, nullable=True)
        subjects = _field(out, path, entry, "subjects", _LIST, required=False)
        for s_index, subject in enumerate(subjects or []):
            if not isinstance(subject, str):
                out.append(
                    Finding(
                        E_SCHEMA_TYPE,
                        f"{path}.subjects[{s_index}]",
                        "subject must be a string",
                    )
                )
        _register_id(out, seen, entry_id, path, entry)


# ── reference pass ────────────────────────────────────────────────────────


def _check_references(
    out: list[Finding],
    integrations: _Index,
    devices: _Index,
    destinations: _Index,
    conduits: _Index,
) -> None:
    for path, device in devices.values():
        integration_id = device.get("integration_id")
        if isinstance(integration_id, str) and integration_id not in integrations:
            out.append(
                Finding(
                    E_REF_INTEGRATION,
                    f"{path}.integration_id",
                    f"no integration with id '{integration_id}'",
                )
            )
        via = device.get("via_device_id")
        if isinstance(via, str) and via and via not in devices:
            out.append(
                Finding(E_REF_VIA_DEVICE, f"{path}.via_device_id", f"no device with id '{via}'")
            )

    _check_via_cycles(out, devices)

    for path, conduit in conduits.values():
        destination_id = conduit.get("destination_id")
        if isinstance(destination_id, str) and destination_id not in destinations:
            out.append(
                Finding(
                    E_REF_DESTINATION,
                    f"{path}.destination_id",
                    f"no destination with id '{destination_id}'",
                )
            )

        source = conduit.get("source")
        if isinstance(source, dict):
            kind, source_id = source.get("kind"), source.get("id")
            if isinstance(source_id, str) and source_id:
                if kind == "device" and source_id not in devices:
                    out.append(
                        Finding(
                            E_REF_SOURCE, f"{path}.source.id", f"no device with id '{source_id}'"
                        )
                    )
                elif kind == "integration" and source_id not in integrations:
                    out.append(
                        Finding(
                            E_REF_SOURCE,
                            f"{path}.source.id",
                            f"no integration with id '{source_id}'",
                        )
                    )

        inherited_from = conduit.get("inherited_from")
        if isinstance(inherited_from, str) and inherited_from and inherited_from not in devices:
            out.append(
                Finding(
                    E_REF_INHERITED_FROM,
                    f"{path}.inherited_from",
                    f"no device with id '{inherited_from}'",
                )
            )


def _check_via_cycles(out: list[Finding], devices: _Index) -> None:
    """Report each via_device cycle once, at its lowest-sorting member.

    A cycle has no natural "first" node, so without a stable anchor the same
    loop would be reported once per participant.
    """
    reported: set[str] = set()
    for start in sorted(devices):
        if start in reported:
            continue
        path_seen: list[str] = []
        current: str | None = start
        while current is not None and current in devices:
            if current in path_seen:
                cycle = path_seen[path_seen.index(current) :]
                anchor = min(cycle)
                if anchor not in reported:
                    reported.update(cycle)
                    out.append(
                        Finding(
                            E_VIA_CYCLE,
                            f"{devices[anchor].path}.via_device_id",
                            "via_device chain loops: " + " -> ".join(cycle + [cycle[0]]),
                        )
                    )
                break
            path_seen.append(current)
            via = devices[current].data.get("via_device_id")
            current = via if isinstance(via, str) and via else None


# ── coherence pass ────────────────────────────────────────────────────────


def _check_coherence(out: list[Finding], devices: _Index, conduits: _Index) -> None:
    # First-hand conduits, indexed by the asset that owns them. An inherited
    # conduit must point at a hub that appears in here for the same destination.
    firsthand: set[tuple[str, str]] = set()
    for _, conduit in conduits.values():
        source = conduit.get("source")
        if not isinstance(source, dict):
            continue
        source_id, destination_id = source.get("id"), conduit.get("destination_id")
        if (
            conduit.get("evidence") in ("observed", "declared")
            and isinstance(source_id, str)
            and isinstance(destination_id, str)
        ):
            firsthand.add((source_id, destination_id))

    for path, conduit in conduits.values():
        evidence = conduit.get("evidence")
        if evidence not in EVIDENCE:
            continue  # already reported by the schema pass

        source = conduit.get("source")
        source_kind = source.get("kind") if isinstance(source, dict) else None
        source_id = source.get("id") if isinstance(source, dict) else None
        inherited_from = conduit.get("inherited_from")

        # An observation field on anything but an observation blurs the
        # invariant the whole tool rests on.
        if evidence != "observed":
            for name in OBSERVED_ONLY_FIELDS:
                if conduit.get(name) is not None:
                    out.append(
                        Finding(
                            E_OBSERVED_FIELD_MISPLACED,
                            f"{path}.{name}",
                            f"'{name}' is only meaningful on an observed conduit,"
                            f" this one is '{evidence}'",
                        )
                    )
        elif conduit.get("last_seen") is None:
            out.append(
                Finding(
                    E_OBSERVED_INCOMPLETE,
                    f"{path}.last_seen",
                    "an observed conduit must record when it was last seen",
                )
            )

        if evidence == "inherited":
            if not isinstance(inherited_from, str) or not inherited_from:
                out.append(
                    Finding(
                        E_INHERITED_NO_PARENT,
                        f"{path}.inherited_from",
                        "an inherited conduit must name the hub it was inherited from",
                    )
                )
            else:
                destination_id = conduit.get("destination_id")
                if (
                    isinstance(destination_id, str)
                    and inherited_from in devices
                    and (inherited_from, destination_id) not in firsthand
                ):
                    out.append(
                        Finding(
                            E_INHERITED_NO_BASIS,
                            f"{path}.inherited_from",
                            f"'{inherited_from}' has no declared or observed conduit to"
                            f" '{destination_id}' to inherit from",
                        )
                    )
                if (
                    source_kind == "device"
                    and isinstance(source_id, str)
                    and source_id in devices
                    and inherited_from in devices
                    and inherited_from not in _ancestors(devices, source_id)
                ):
                    out.append(
                        Finding(
                            E_INHERITED_NOT_ANCESTOR,
                            f"{path}.inherited_from",
                            f"'{inherited_from}' is not upstream of '{source_id}'"
                            " in the via_device chain",
                        )
                    )
        elif inherited_from is not None:
            out.append(
                Finding(
                    E_INHERITED_FROM_MISPLACED,
                    f"{path}.inherited_from",
                    f"'inherited_from' is only meaningful on an inherited conduit,"
                    f" this one is '{evidence}'",
                )
            )

        # An unknown host exists only because the resolver saw it. Nothing
        # declares a host that is, by definition, absent from the registry.
        if source_kind == "unknown_host" and evidence != "observed":
            out.append(
                Finding(
                    E_UNKNOWN_HOST_NOT_OBSERVED,
                    f"{path}.evidence",
                    f"an unknown_host source can only be observed, not '{evidence}'",
                )
            )

        # The join runs on MAC/IP. An observation attributed to a device with
        # no IP was not correlated, it was guessed.
        if (
            evidence == "observed"
            and source_kind == "device"
            and isinstance(source_id, str)
            and source_id in devices
            and not devices[source_id].data.get("ip")
        ):
            out.append(
                Finding(
                    E_OBSERVED_WITHOUT_IP,
                    f"{path}.source.id",
                    f"device '{source_id}' has no ip: this observation cannot have been"
                    " correlated to it (inherited evidence may be what is meant)",
                )
            )


def _check_entity_counts(out: list[Finding], integrations: _Index, devices: _Index) -> None:
    """An integration owns at least the entities of its own devices.

    A lower count means the collector counted device entities but missed the
    device-less ones, which is precisely the category the config-entry unit
    exists to keep.
    """
    per_integration: dict[str, int] = {}
    for _, device in devices.values():
        integration_id = device.get("integration_id")
        count = device.get("entity_count")
        if isinstance(integration_id, str) and isinstance(count, int) and not isinstance(count, bool):
            per_integration[integration_id] = per_integration.get(integration_id, 0) + count

    for integration_id, (path, integration) in integrations.items():
        declared = integration.get("entity_count")
        if not isinstance(declared, int) or isinstance(declared, bool):
            continue
        from_devices = per_integration.get(integration_id, 0)
        if declared < from_devices:
            out.append(
                Finding(
                    E_ENTITY_COUNT_BELOW_DEVICES,
                    f"{path}.entity_count",
                    f"{declared} declared but its devices already account for {from_devices}",
                )
            )


def _ancestors(devices: _Index, device_id: str) -> set[str]:
    """Every hub above a device, cycle-safe."""
    found: set[str] = set()
    start = devices.get(device_id)
    current = start.data.get("via_device_id") if start else None
    while isinstance(current, str) and current and current not in found and current in devices:
        found.add(current)
        current = devices[current].data.get("via_device_id")
    return found
