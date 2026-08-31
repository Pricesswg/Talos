"""Panel checks that do not need a browser.

The panel is the one file no Python test would otherwise touch, and its two
failure modes are silent: a translation key that exists in one language and
not the other renders as a raw key, and a dynamic key whose vocabulary drifted
away from the core renders as `kind.something`. Both are caught here.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

from talos_core.const import (
    DESTINATION_KINDS,
    EVIDENCE,
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
        self.assertEqual(
            self.it ^ self.en,
            set(),
            "these keys exist in one language only and would render raw",
        )

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
        ):
            for value in values:
                with self.subTest(key=f"{prefix}.{value}"):
                    self.assertIn(f"{prefix}.{value}", self.en)
                    self.assertIn(f"{prefix}.{value}", self.it)

    def test_dynamic_key_prefixes_are_the_ones_we_checked(self) -> None:
        # If a new `this.t(\`x.${...}\`)` appears, this test must be taught
        # about it rather than silently ignoring it.
        found = set(re.findall(r"this\.t\(`([\w.]+)\.\$\{", SOURCE))
        self.assertEqual(found, {"severity", "evidence", "kind", "reason", "opt", "opt.hint"})

    def test_every_editable_option_has_a_label(self) -> None:
        # The settings screen builds `opt.<key>` at runtime from the option
        # list in const.py, so the two have to stay in step.
        for option in editable_options():
            with self.subTest(option=option):
                self.assertIn(f"opt.{option}", self.en)
                self.assertIn(f"opt.{option}", self.it)


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
