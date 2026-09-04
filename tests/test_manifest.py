"""The manifest, checked the way hassfest checks it, without Docker.

hassfest refuses an integration that imports a component it does not declare.
It runs in CI after the push, which is how a missing line went unnoticed for
ten releases: the local loop was tests, bundle and panel, and hassfest was
not in it. This is the same rule, in milliseconds, before the push.
"""

from __future__ import annotations

import ast
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COMPONENT = ROOT / "custom_components" / "talos"
MANIFEST = json.loads((COMPONENT / "manifest.json").read_text(encoding="utf-8"))

# What hassfest lets an integration import without declaring it. The proof
# is empirical: every one of these was imported at 1.7.0, the last release
# hassfest passed, so they are exempt. `mqtt` was the only import added
# since, and the only one hassfest named. Add to this list only with the
# same kind of evidence.
CORE_EXEMPT = frozenset({"http", "websocket_api", "diagnostics"})


def imported_components(root: Path) -> dict[str, set[str]]:
    """Component name to the files that import it, read from the AST.

    Both forms count: `from homeassistant.components import mqtt` and
    `homeassistant.components.mqtt.something`. The vendored core is skipped,
    it is not part of the integration's manifest.
    """
    found: dict[str, set[str]] = {}

    def add(name: str, path: Path) -> None:
        found.setdefault(name, set()).add(path.relative_to(ROOT).as_posix())

    for path in root.rglob("*.py"):
        if "vendor" in path.parts:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                parts = node.module.split(".")
                if parts[:2] == ["homeassistant", "components"]:
                    if len(parts) >= 3:
                        add(parts[2], path)
                    else:
                        for alias in node.names:
                            add(alias.name, path)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    parts = alias.name.split(".")
                    if parts[:2] == ["homeassistant", "components"] and len(parts) >= 3:
                        add(parts[2], path)
    return found


def own_platforms(root: Path) -> set[str]:
    """Platforms the integration ships. `sensor.py` importing the sensor
    component is the integration providing that platform, not depending on
    it, and hassfest treats it that way."""
    return {path.stem for path in root.glob("*.py") if path.stem not in {"__init__"}}


def undeclared(manifest: dict, imports: dict[str, set[str]], platforms: set[str]) -> dict[str, set[str]]:
    declared = set(manifest.get("dependencies", ())) | set(manifest.get("after_dependencies", ()))
    return {
        name: files
        for name, files in imports.items()
        if name not in declared and name not in platforms and name not in CORE_EXEMPT
    }


class TestManifestDependencies(unittest.TestCase):
    def setUp(self) -> None:
        self.imports = imported_components(COMPONENT)

    def test_the_scanner_actually_sees_the_imports(self) -> None:
        """A scanner that found nothing would pass everything. It has to
        find the imports this integration is known to make."""
        for name in ("mqtt", "frontend", "panel_custom", "websocket_api"):
            with self.subTest(component=name):
                self.assertIn(name, self.imports)

    def test_every_imported_component_is_declared(self) -> None:
        missing = undeclared(MANIFEST, self.imports, own_platforms(COMPONENT))
        self.assertEqual(
            missing,
            {},
            "hassfest will refuse this: declare each in dependencies or after_dependencies",
        )

    def test_mqtt_is_optional_not_required(self) -> None:
        """MQTT is used when it is there and Talos loads without it. In
        `dependencies` it would become mandatory, which the code does not
        want and the user did not ask for."""
        self.assertIn("mqtt", MANIFEST.get("after_dependencies", ()))
        self.assertNotIn("mqtt", MANIFEST.get("dependencies", ()))

    def test_the_rule_bites_when_a_declaration_is_missing(self) -> None:
        """Run the same check against the manifest as it was before 1.17.1,
        so a future edit that quietly weakens the scanner is caught."""
        broken = {**MANIFEST, "after_dependencies": []}
        missing = undeclared(broken, self.imports, own_platforms(COMPONENT))
        self.assertEqual(set(missing), {"mqtt"})
        self.assertTrue(any(f.endswith("mqtt_source.py") for f in missing["mqtt"]))


if __name__ == "__main__":
    unittest.main()
