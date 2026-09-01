"""Panel checks that do not need a browser.

The panel is the one file no Python test would otherwise touch, and its two
failure modes are silent: a translation key that exists in one language and
not the other renders as a raw key, and a dynamic key whose vocabulary drifted
away from the core renders as `kind.something`. Both are caught here.
"""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

from talos_core.const import (
    DESTINATION_KINDS,
    EVIDENCE,
    TRANSPORTS,
    UNVERIFIED_REASONS,
)
from talos_core.checks import SEVERITIES

ROOT = Path(__file__).resolve().parent.parent
PANEL = ROOT / "custom_components" / "talos" / "www" / "talos-panel.js"
CONST = ROOT / "custom_components" / "talos" / "const.py"
SOURCE = PANEL.read_text(encoding="utf-8")


def editable_options() -> set[str]:
    """The option keys the panel is expected to label, read from const.py.

    Parsed rather than duplicated: adding an option in Python and forgetting
    its label would otherwise show a raw key in the settings screen.
    """
    import ast

    tree = ast.parse(CONST.read_text(encoding="utf-8"))
    constants: dict[str, str] = {}
    numeric: list[str] = []
    text: list[str] = []
    for node in tree.body:
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            name, value = node.target.id, node.value
        elif isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name):
            name, value = node.targets[0].id, node.value
        else:
            continue
        if isinstance(value, ast.Constant) and isinstance(value.value, str):
            constants[name] = value.value
        elif name == "OPTION_BOUNDS" and isinstance(value, ast.Dict):
            numeric = [k.id for k in value.keys if isinstance(k, ast.Name)]
        elif name == "TEXT_OPTIONS" and isinstance(value, ast.Tuple):
            text = [e.id for e in value.elts if isinstance(e, ast.Name)]

    assert numeric and text, "could not read the option lists from const.py"
    return {constants[name] for name in (*numeric, *text)}


def table(language: str) -> set[str]:
    """Pull one language block out of the I18N object."""
    start = SOURCE.index(f"\n  {language}: {{")
    depth = 0
    for index in range(start, len(SOURCE)):
        if SOURCE[index] == "{":
            depth += 1
        elif SOURCE[index] == "}":
            depth -= 1
            if depth == 0:
                block = SOURCE[start : index + 1]
                break
    else:  # pragma: no cover - the file would be unparseable
        raise AssertionError(f"language block {language} not found")
    return set(re.findall(r'^\s{4}"([\w.]+)":', block, re.MULTILINE))


class TestTranslations(unittest.TestCase):
    def setUp(self) -> None:
        self.it = table("it")
        self.en = table("en")

    def test_both_languages_are_complete(self) -> None:
        self.assertTrue(self.it, "the Italian table is empty")
        # Check copy is authored in checks.json, in English, and that stays
        # the canonical text: checkText() falls back to the document itself
        # when a language has no entry. So an English key here would only
        # duplicate the document, and its absence renders nothing raw.
        ui_it = {key for key in self.it if not key.startswith(("chk.", "unv."))}
        ui_en = {key for key in self.en if not key.startswith(("chk.", "unv."))}
        self.assertEqual(
            ui_it ^ ui_en,
            set(),
            "these keys exist in one language only and would render raw",
        )

    def test_every_check_is_translated(self) -> None:
        """The whole point of the fallback is that it never has to be used."""
        checks = json.loads(
            (ROOT / "talos_core" / "data" / "checks.json").read_text(encoding="utf-8")
        )["checks"]
        for check in checks:
            for field in ("title", "detail", "remediation"):
                if field in check or (field == "detail" and "unverifiable" in check):
                    self.assertIn(f"{check['id']}.{field}", self.it, check["id"])

    def test_every_static_key_is_defined(self) -> None:
        used = set(re.findall(r'this\.t\(\s*"([\w.]+)"', SOURCE))
        self.assertTrue(used)
        self.assertEqual(used - self.en, set())

    def test_dynamic_keys_cover_the_core_vocabulary(self) -> None:
        # The panel builds these keys at runtime from values the core defines,
        # so the two vocabularies have to stay in step.
        for prefix, values in (
            ("severity", SEVERITIES),
            ("evidence", EVIDENCE),
            ("kind", DESTINATION_KINDS),
            ("reason", UNVERIFIED_REASONS),
            ("transport", TRANSPORTS),
        ):
            for value in values:
                with self.subTest(key=f"{prefix}.{value}"):
                    self.assertIn(f"{prefix}.{value}", self.en)
                    self.assertIn(f"{prefix}.{value}", self.it)

    def test_dynamic_key_prefixes_are_the_ones_we_checked(self) -> None:
        # If a new `this.t(\`x.${...}\`)` appears, this test must be taught
        # about it rather than silently ignoring it.
        found = set(re.findall(r"this\.t\(`([\w.]+)\.\$\{", SOURCE))
        self.assertEqual(
            found,
            {
                "severity",
                "evidence",
                "kind",
                "reason",
                "opt",
                "opt.hint",
                "transport",
                "map.detail",
                "map.scope",
                "role",
                "settings.scope.item",
            },
        )

    def test_every_scope_item_has_a_label(self) -> None:
        """The list is driven by a constant, so a name added there without a
        string would render the key to the user."""
        items = re.search(r"const SCOPE_ITEMS = \[(.*?)\];", SOURCE, re.S)
        assert items
        for key in re.findall(r'"(\w+)"', items.group(1)):
            with self.subTest(item=key):
                self.assertIn(f"settings.scope.item.{key}", self.it)
                self.assertIn(f"settings.scope.item.{key}", self.en)

    def test_every_integration_role_has_a_label(self) -> None:
        from talos_core.const import INTEGRATION_ROLES

        for role in INTEGRATION_ROLES:
            with self.subTest(role=role):
                self.assertIn(f"role.{role}", self.en)
                self.assertIn(f"role.{role}", self.it)

    def test_every_map_scope_kind_has_a_label(self) -> None:
        # The badge builds map.scope.<kind> from the active filter.
        for kind in ("transport", "integration", "role"):
            with self.subTest(kind=kind):
                self.assertIn(f"map.scope.{kind}", self.en)
                self.assertIn(f"map.scope.{kind}", self.it)

    def test_every_map_detail_level_has_a_label(self) -> None:
        # The map builds map.detail.<n> from its own level counter.
        for level in (1, 2, 3):
            with self.subTest(level=level):
                self.assertIn(f"map.detail.{level}", self.en)
                self.assertIn(f"map.detail.{level}", self.it)

    def test_every_editable_option_has_a_label(self) -> None:
        # The settings screen builds `opt.<key>` at runtime from the option
        # list in const.py, so the two have to stay in step.
        for option in editable_options():
            with self.subTest(option=option):
                self.assertIn(f"opt.{option}", self.en)
                self.assertIn(f"opt.{option}", self.it)


class TestIntegrationTranslations(unittest.TestCase):
    """hassfest rejects anything that looks like HTML in a translation."""

    def test_no_angle_brackets(self) -> None:
        import json
        import re

        base = ROOT / "custom_components" / "talos"
        for name in ("translations/en.json", "translations/it.json", "strings.json"):
            path = base / name

            def walk(node: object, where: str) -> None:
                if isinstance(node, dict):
                    for key, value in node.items():
                        walk(value, f"{where}.{key}" if where else key)
                elif isinstance(node, str):
                    self.assertIsNone(
                        re.search(r"<[^>\s][^>]*>", node),
                        f"{name}: {where} would be read as HTML by hassfest",
                    )

            walk(json.loads(path.read_text(encoding="utf-8")), "")

    def test_english_and_italian_cover_the_same_keys(self) -> None:
        import json

        base = ROOT / "custom_components" / "talos" / "translations"

        def keys(node: object, where: str = "") -> set[str]:
            if not isinstance(node, dict):
                return {where}
            found: set[str] = set()
            for key, value in node.items():
                found |= keys(value, f"{where}.{key}" if where else key)
            return found

        english = keys(json.loads((base / "en.json").read_text(encoding="utf-8")))
        italian = keys(json.loads((base / "it.json").read_text(encoding="utf-8")))
        self.assertEqual(english ^ italian, set())


class TestMethodCoverage(unittest.TestCase):
    """Every `this.x()` has to resolve to something.

    An editing slip once removed a method while its call sites stayed, and
    the panel died at runtime with the rest of the suite green: nothing here
    executes the JavaScript.
    """

    # Inherited from HTMLElement, not declared in the class.
    INHERITED = {"attachShadow", "setAttribute", "getAttribute", "addEventListener"}

    def test_no_call_without_a_definition(self) -> None:
        defined = set(re.findall(r"^  (?:async |get |set )?([a-zA-Z_]\w*)\s*\(", SOURCE, re.M))
        called = set(re.findall(r"this\.([a-zA-Z_]\w*)\(", SOURCE))
        # Names starting with an underscore are stored callables, not methods.
        missing = {
            name
            for name in called
            if name not in defined and name not in self.INHERITED and not name.startswith("_")
        }
        self.assertEqual(missing, set())


class TestEscaping(unittest.TestCase):
    def test_untrusted_values_go_through_esc(self) -> None:
        # Device names, domains and check text come from the network and from
        # user-editable rule files; none may be interpolated raw.
        self.assertIn("const esc =", SOURCE)
        for raw in ("${device.name}", "${destination.fqdn}", "${check.detail}", "${result.title}"):
            with self.subTest(expression=raw):
                self.assertNotIn(raw, SOURCE)


class TestGraphScaling(unittest.TestCase):
    def test_it_groups_instead_of_truncating(self) -> None:
        self.assertIn("GROUP_THRESHOLD", SOURCE)
        self.assertIn("graph.grouped", SOURCE)
        # And it says what it is not showing.
        self.assertIn("graph.hidden", SOURCE)


SVG_NAMESPACE = "http://www.w3.org/2000/svg"


class TestNoExternalResources(unittest.TestCase):
    def test_panel_pulls_nothing_from_the_network(self) -> None:
        # The SVG namespace is an identifier, not an address anything fetches;
        # everything else that looks like a URL would be a real dependency.
        self.assertIn(SVG_NAMESPACE, SOURCE)
        body = SOURCE.replace(SVG_NAMESPACE, "")
        for marker in ("http://", "https://", "//cdn", "import(", "fetch("):
            with self.subTest(marker=marker):
                self.assertNotIn(marker, body)


if __name__ == "__main__":
    unittest.main()
