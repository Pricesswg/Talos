"""Stable error codes for the schema validator.

Codes are part of the public contract: the panel, the CLI and any downstream
tooling key off them. Never renumber a code and never change what one means.
Retire a code by leaving it in RETIRED and allocating a new number.

    S: schema, shape, types, enums, duplicate identifiers
    R: references, an identifier that points at nothing, or at a cycle
    C: coherence, the document parses and resolves but contradicts itself
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

# ── Schema ────────────────────────────────────────────────────────────────
E_SCHEMA_TYPE: Final = "TALOS-S001"
E_SCHEMA_MISSING: Final = "TALOS-S002"
E_SCHEMA_ENUM: Final = "TALOS-S003"
E_SCHEMA_VERSION: Final = "TALOS-S004"
E_DUPLICATE_ID: Final = "TALOS-S005"
E_SCHEMA_RANGE: Final = "TALOS-S006"

# ── References ────────────────────────────────────────────────────────────
E_REF_INTEGRATION: Final = "TALOS-R001"
E_REF_DESTINATION: Final = "TALOS-R002"
E_REF_SOURCE: Final = "TALOS-R003"
E_REF_VIA_DEVICE: Final = "TALOS-R004"
E_VIA_CYCLE: Final = "TALOS-R005"
E_REF_INHERITED_FROM: Final = "TALOS-R006"

# ── Coherence ─────────────────────────────────────────────────────────────
E_OBSERVED_FIELD_MISPLACED: Final = "TALOS-C001"
E_OBSERVED_INCOMPLETE: Final = "TALOS-C002"
E_INHERITED_NO_PARENT: Final = "TALOS-C003"
E_INHERITED_FROM_MISPLACED: Final = "TALOS-C004"
E_INHERITED_NO_BASIS: Final = "TALOS-C005"
E_INHERITED_NOT_ANCESTOR: Final = "TALOS-C006"
E_CORRELATION_RANGE: Final = "TALOS-C007"
E_OBSERVED_WITHOUT_IP: Final = "TALOS-C008"
E_UNKNOWN_HOST_NOT_OBSERVED: Final = "TALOS-C009"
E_ENTITY_COUNT_BELOW_DEVICES: Final = "TALOS-C010"

CODES: Final[dict[str, str]] = {
    E_SCHEMA_TYPE: "value has the wrong type",
    E_SCHEMA_MISSING: "required field is missing",
    E_SCHEMA_ENUM: "value is outside the allowed vocabulary",
    E_SCHEMA_VERSION: "schema_version is absent or unsupported",
    E_DUPLICATE_ID: "identifier is used more than once in its collection",
    E_SCHEMA_RANGE: "numeric value is out of range",
    E_REF_INTEGRATION: "integration_id does not resolve to a known integration",
    E_REF_DESTINATION: "destination_id does not resolve to a known destination",
    E_REF_SOURCE: "conduit source does not resolve to a known asset",
    E_REF_VIA_DEVICE: "via_device_id does not resolve to a known device",
    E_VIA_CYCLE: "via_device chain contains a cycle",
    E_REF_INHERITED_FROM: "inherited_from does not resolve to a known device",
    E_OBSERVED_FIELD_MISPLACED: "observation field present on a conduit that was not observed",
    E_OBSERVED_INCOMPLETE: "observed conduit carries no last_seen",
    E_INHERITED_NO_PARENT: "inherited conduit carries no inherited_from",
    E_INHERITED_FROM_MISPLACED: "inherited_from present on a conduit that is not inherited",
    E_INHERITED_NO_BASIS: "inherited conduit has no first-hand conduit on the hub it cites",
    E_INHERITED_NOT_ANCESTOR: "inherited_from is not an ancestor of the source device",
    E_CORRELATION_RANGE: "correlated device count exceeds the total",
    E_OBSERVED_WITHOUT_IP: "observed conduit starts from a device with no IP to correlate on",
    E_UNKNOWN_HOST_NOT_OBSERVED: "unknown_host source on a conduit that was not observed",
    E_ENTITY_COUNT_BELOW_DEVICES: "integration entity_count is lower than the sum of its devices",
}

# Codes allocated in the past and no longer emitted. Kept so that a number is
# never reused with a different meaning.
RETIRED: Final[frozenset[str]] = frozenset()


@dataclass(frozen=True, slots=True)
class Finding:
    """One validation failure, addressed to a JSON path inside the document."""

    code: str
    path: str
    message: str

    def __str__(self) -> str:
        return f"{self.code} {self.path}: {self.message}"

    def as_dict(self) -> dict[str, str]:
        return {"code": self.code, "path": self.path, "message": self.message}


class TalosSchemaError(ValueError):
    """Raised when a document is loaded into the model without validating first."""

    def __init__(self, findings: list[Finding]) -> None:
        self.findings = findings
        head = "; ".join(str(f) for f in findings[:3])
        more = f" (+{len(findings) - 3} more)" if len(findings) > 3 else ""
        super().__init__(f"{len(findings)} validation error(s): {head}{more}")
