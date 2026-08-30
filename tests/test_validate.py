"""Validator tests.

The invalid fixtures declare their own expectations: every entry that should
produce a finding carries an `_expect` key with the code it must produce, and
the test compares that set against what the validator actually emits. Adding a
case to a fixture without implementing its rule therefore fails, and so does
emitting a code the fixture never asked for.
"""

from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path
from typing import Any

from talos_core import CODES, SCHEMA_VERSION, validate
from talos_core.validate import is_valid

FIXTURES = Path(__file__).parent / "fixtures"


def load(name: str) -> dict[str, Any]:
    return json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))


def expected_codes(node: Any) -> set[str]:
    """Collect every `_expect` marker anywhere in a fixture."""
    found: set[str] = set()
    if isinstance(node, dict):
        if isinstance(node.get("_expect"), str):
            found.add(node["_expect"])
        for value in node.values():
            found |= expected_codes(value)
    elif isinstance(node, list):
        for item in node:
            found |= expected_codes(item)
    return found


def codes(raw: Any) -> set[str]:
    return {f.code for f in validate(raw)}


class TestValidHome(unittest.TestCase):
    def test_reference_house_is_clean(self) -> None:
        self.assertEqual(validate(load("home")), [])
        self.assertTrue(is_valid(load("home")))


class TestSelfDeclaringFixtures(unittest.TestCase):
    def test_evidence_violations(self) -> None:
        raw = load("invalid_evidence")
        self.assertEqual(codes(raw), expected_codes(raw))

    def test_reference_violations(self) -> None:
        raw = load("invalid_refs")
        self.assertEqual(codes(raw), expected_codes(raw))

    def test_one_finding_per_declared_case(self) -> None:
        # A rule that fires twice for one case would still pass the set
        # comparison above, so pin the count as well.
        for name in ("invalid_evidence", "invalid_refs"):
            raw = load(name)
            with self.subTest(fixture=name):
                self.assertEqual(len(validate(raw)), len(expected_codes(raw)))


class TestSchemaPass(unittest.TestCase):
    def test_root_must_be_an_object(self) -> None:
        for value in ([], "scan", 7, None):
            with self.subTest(value=value):
                self.assertEqual(codes(value), {"TALOS-S001"})

    def test_unsupported_schema_version(self) -> None:
        raw = load("home")
        raw["schema_version"] = "0.9"
        self.assertIn("TALOS-S004", codes(raw))

    def test_missing_schema_version(self) -> None:
        raw = load("home")
        del raw["schema_version"]
        self.assertIn("TALOS-S004", codes(raw))

    def test_missing_required_field(self) -> None:
        raw = load("home")
        del raw["devices"][0]["name"]
        self.assertIn("TALOS-S002", codes(raw))

    def test_missing_collection(self) -> None:
        raw = load("home")
        del raw["destinations"]
        found = codes(raw)
        self.assertIn("TALOS-S002", found)
        # Every conduit now points at a destination that cannot be resolved.
        self.assertIn("TALOS-R002", found)

    def test_unknown_enum_value(self) -> None:
        raw = load("home")
        raw["devices"][0]["transport"] = "carrier_pigeon"
        self.assertIn("TALOS-S003", codes(raw))

    def test_bool_is_not_accepted_as_int(self) -> None:
        raw = load("home")
        raw["devices"][0]["entity_count"] = True
        self.assertIn("TALOS-S001", codes(raw))

    def test_int_is_not_accepted_as_bool(self) -> None:
        raw = load("home")
        raw["integrations"][0]["is_built_in"] = 1
        self.assertIn("TALOS-S001", codes(raw))

    def test_negative_counts_rejected(self) -> None:
        raw = load("home")
        raw["conduits"][0]["query_count"] = -1
        self.assertIn("TALOS-S006", codes(raw))

    def test_null_on_a_non_nullable_field(self) -> None:
        raw = load("home")
        raw["devices"][0]["name"] = None
        self.assertIn("TALOS-S001", codes(raw))

    def test_nullable_optional_stays_clean(self) -> None:
        raw = load("home")
        raw["devices"][0]["model"] = None
        raw["ha_version"] = None
        self.assertEqual(validate(raw), [])

    def test_non_object_entry_in_a_collection(self) -> None:
        raw = load("home")
        raw["devices"].append("not a device")
        self.assertIn("TALOS-S001", codes(raw))

    def test_encrypted_is_tri_state(self) -> None:
        raw = load("home")
        for value in (True, False, "unknown"):
            with self.subTest(value=value):
                candidate = copy.deepcopy(raw)
                candidate["conduits"][0]["encrypted"] = value
                self.assertEqual(validate(candidate), [])

        raw["conduits"][0]["encrypted"] = "maybe"
        self.assertIn("TALOS-S003", codes(raw))


class TestSourceKinds(unittest.TestCase):
    def test_ha_core_needs_no_id(self) -> None:
        raw = load("home")
        for conduit in raw["conduits"]:
            if conduit["source"]["kind"] == "ha_core":
                del conduit["source"]["id"]
        self.assertEqual(validate(raw), [])

    def test_other_kinds_require_an_id(self) -> None:
        raw = load("home")
        raw["conduits"][0]["source"] = {"kind": "device"}
        self.assertIn("TALOS-S002", codes(raw))

    def test_unknown_host_is_not_a_dangling_reference(self) -> None:
        # An unknown host is by definition absent from the registry: it must
        # not be reported as a broken reference.
        raw = load("home")
        self.assertNotIn("TALOS-R003", codes(raw))


class TestEvidenceInvariant(unittest.TestCase):
    def test_inherited_needs_a_first_hand_basis_on_the_hub(self) -> None:
        raw = load("home")
        # Drop the bridge's own observation: the lamps now inherit from nothing.
        raw["conduits"] = [c for c in raw["conduits"] if c["id"] != "cnd.hue.bridge.remote"]
        found = [f for f in validate(raw) if f.code == "TALOS-C005"]
        self.assertEqual(len(found), 2, "one per inheriting lamp")

    def test_observation_fields_do_not_leak_onto_inherited_conduits(self) -> None:
        raw = load("home")
        inherited = next(c for c in raw["conduits"] if c["evidence"] == "inherited")
        inherited["query_count"] = 1204
        self.assertIn("TALOS-C001", codes(raw))

    def test_zigbee_device_cannot_be_observed_directly(self) -> None:
        raw = load("home")
        raw["conduits"].append(
            {
                "id": "cnd.bogus",
                "source": {"kind": "device", "id": "dev.z2m.motion"},
                "destination_id": "dst.hicloud",
                "evidence": "observed",
                "last_seen": "2026-08-30T09:00:00+02:00",
                "query_count": 3,
            }
        )
        self.assertIn("TALOS-C008", codes(raw))


class TestEntityCounts(unittest.TestCase):
    def test_integration_must_cover_its_own_devices(self) -> None:
        raw = load("home")
        # The two Reolink cameras alone account for 18 entities.
        next(i for i in raw["integrations"] if i["id"] == "int.reolink")["entity_count"] = 9
        self.assertIn("TALOS-C010", codes(raw))

    def test_device_less_entities_are_allowed_above_the_sum(self) -> None:
        raw = load("home")
        next(i for i in raw["integrations"] if i["id"] == "int.reolink")["entity_count"] = 25
        self.assertEqual(validate(raw), [])

    def test_field_is_optional(self) -> None:
        raw = load("home")
        for integration in raw["integrations"]:
            del integration["entity_count"]
        self.assertEqual(validate(raw), [])


class TestErrorCodeContract(unittest.TestCase):
    def test_every_emitted_code_is_documented(self) -> None:
        emitted: set[str] = set()
        for name in ("invalid_evidence", "invalid_refs"):
            emitted |= codes(load(name))
        emitted |= codes({"schema_version": SCHEMA_VERSION})
        broken = load("home")
        next(i for i in broken["integrations"] if i["id"] == "int.reolink")["entity_count"] = 0
        emitted |= codes(broken)
        emitted |= codes("not a document")
        undocumented = emitted - set(CODES)
        self.assertEqual(undocumented, set())

    def test_findings_are_addressed(self) -> None:
        for finding in validate(load("invalid_refs")):
            with self.subTest(code=finding.code):
                self.assertTrue(finding.path.startswith("$"))
                self.assertTrue(finding.message)


if __name__ == "__main__":
    unittest.main()
