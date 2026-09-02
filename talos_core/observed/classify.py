"""Domain classification.

Deliberately a list, not a classifier. That `*.tuya.com` is a vendor cloud is
something a person knows; no algorithm derives it from the string. A general
heuristic here would produce confident nonsense on exactly the domains that
matter most.

`unknown` is a first-class outcome, counted and shown. It never falls into a
benign catch-all, because the domains nobody has classified yet are the ones
worth looking at.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

DEFAULT_RULES_PATH = Path(__file__).resolve().parent.parent / "data" / "domains.json"


@dataclass(frozen=True, slots=True)
class DomainRule:
    """A rule keyed on the suffix, on the leftmost label, or on both.

    A suffix names an operator: `tuyaeu.com` is Tuya, whoever runs the host.
    A label names a function: anything called `stun.something` or
    `stun-something` is a STUN server no matter who runs it, and enumerating
    every one of them is not possible. Both forms exist because both questions
    get asked, and a rule that carries a suffix keeps behaving as it did.
    """

    suffix: str = ""
    label: str = ""
    kind: str = "unknown"
    vendor: str | None = None

    def matches(self, name: str) -> bool:
        if self.suffix:
            return name == self.suffix or name.endswith(f".{self.suffix}")
        if self.label:
            head = name.split(".", 1)[0]
            return head == self.label or head.startswith(f"{self.label}-")
        return False


@dataclass(frozen=True, slots=True)
class Classification:
    kind: str
    vendor: str | None
    matched: str | None

    @property
    def is_known(self) -> bool:
        return self.matched is not None


class DomainClassifier:
    """Longest matching suffix wins, so `tuyaeu.com` beats `com`."""

    def __init__(
        self,
        rules: Iterable[DomainRule] = (),
        ignore: Iterable[str] = (),
    ) -> None:
        # Suffix rules first and longest first, so `tuyaeu.com` beats `com`
        # and an explicit host always beats a rule about what it is called.
        ordered = list(rules)
        self._rules = sorted(
            (rule for rule in ordered if rule.suffix), key=lambda r: len(r.suffix), reverse=True
        ) + [rule for rule in ordered if not rule.suffix and rule.label]
        self._ignore = tuple(s.lower().lstrip(".") for s in ignore)
        self.unknown: set[str] = set()

    @classmethod
    def load(cls, path: str | Path | None = None) -> DomainClassifier:
        """Load rules from JSON, or from YAML when PyYAML is available.

        The core declares no dependencies, so YAML is read only if the parser
        happens to be installed. Inside Home Assistant it always is.
        """
        source = Path(path) if path else DEFAULT_RULES_PATH
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
        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DomainClassifier:
        rules = [
            DomainRule(
                suffix=str(entry.get("suffix") or "").lower().lstrip("."),
                label=str(entry.get("label") or "").lower().strip("."),
                kind=str(entry.get("kind") or "unknown"),
                vendor=entry.get("vendor"),
            )
            for entry in (data.get("rules") or ())
            if entry.get("suffix") or entry.get("label")
        ]
        return cls(rules, data.get("ignore") or ())

    def extend(self, data: dict[str, Any]) -> DomainClassifier:
        """Layer the user's own list on top of the shipped one."""
        extra = DomainClassifier.from_dict(data)
        return DomainClassifier(
            rules=[*self._rules, *extra._rules],
            ignore=[*self._ignore, *extra._ignore],
        )

    def merged_with(self, other: DomainClassifier) -> DomainClassifier:
        """Layer another classifier on top of this one, keeping both lists."""
        return DomainClassifier(
            rules=[*self._rules, *other._rules],
            ignore=[*self._ignore, *other._ignore],
        )

    def is_ignored(self, fqdn: str) -> bool:
        """Local name lookups are not egress and must not become conduits."""
        name = fqdn.lower().rstrip(".")
        return any(name == suffix or name.endswith(f".{suffix}") for suffix in self._ignore)

    def classify(self, fqdn: str) -> Classification:
        name = fqdn.lower().rstrip(".")
        for rule in self._rules:
            if rule.matches(name):
                return Classification(rule.kind, rule.vendor, rule.suffix or f"*{rule.label}")
        # Remembered so the scan can say how much of the traffic it could not
        # name, instead of presenting a partial map as a complete one.
        self.unknown.add(name)
        return Classification("unknown", None, None)
