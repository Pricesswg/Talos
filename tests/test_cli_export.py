"""CLI and export tests.

Both are user-facing surfaces where a wrong exit code or a broken file is
silent: cron does not read prose, and an archived report is opened months
later with nobody around to notice it is empty.
"""

from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from talos_core import Scan, derive, validate
from talos_core.cli import EXIT_ERROR, EXIT_FINDINGS, EXIT_OK, main, summary
from talos_core.export_html import render_html, render_json

FIXTURES = Path(__file__).parent / "fixtures"


def scan() -> Scan:
    raw = json.loads((FIXTURES / "home.json").read_text(encoding="utf-8"))
    assert validate(raw) == []
    return Scan.from_dict(raw)


def run(*argv: str) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = main(list(argv))
    return code, out.getvalue(), err.getvalue()


class TestValidateCommand(unittest.TestCase):
    def test_valid_document_exits_zero(self) -> None:
        code, out, _ = run("validate", str(FIXTURES / "home.json"))
        self.assertEqual(code, EXIT_OK)
        self.assertIn("valido", out)

    def test_invalid_document_prints_codes_and_exits_one(self) -> None:
        code, out, err = run("validate", str(FIXTURES / "invalid_refs.json"))
        self.assertEqual(code, EXIT_FINDINGS)
        self.assertIn("TALOS-R001", out)
        self.assertIn("problema", err)

    def test_missing_file_is_an_error_not_a_crash(self) -> None:
        code, _, err = run("validate", str(FIXTURES / "nope.json"))
        self.assertEqual(code, EXIT_ERROR)
        self.assertIn("errore:", err)


class TestReportCommand(unittest.TestCase):
    def setUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        self.tmp = Path(self._dir.name)
        self.addCleanup(self._dir.cleanup)

    def test_writes_both_exports(self) -> None:
        html_out, json_out = self.tmp / "r.html", self.tmp / "r.json"
        code, _, _ = run(
            "report", str(FIXTURES / "home.json"),
            "--html", str(html_out), "--json", str(json_out), "--quiet",
        )
        # The reference house has a high finding, so a non-zero exit is right.
        self.assertEqual(code, EXIT_FINDINGS)
        self.assertTrue(html_out.read_text(encoding="utf-8").startswith("<!doctype html>"))
        payload = json.loads(json_out.read_text(encoding="utf-8"))
        self.assertIn("scan", payload)
        self.assertIn("derived", payload)

    def test_accepts_its_own_combined_export(self) -> None:
        json_out = self.tmp / "r.json"
        run("report", str(FIXTURES / "home.json"), "--json", str(json_out), "--quiet")
        code, out, _ = run("report", str(json_out))
        self.assertEqual(code, EXIT_FINDINGS)
        self.assertIn("autonomia", out)

    def test_refuses_an_invalid_document(self) -> None:
        code, _, err = run("report", str(FIXTURES / "invalid_refs.json"))
        self.assertEqual(code, EXIT_ERROR)
        self.assertIn("non valido", err)

    def test_exit_code_is_zero_without_high_findings(self) -> None:
        raw = json.loads((FIXTURES / "home.json").read_text(encoding="utf-8"))
        # Remove the observations: the egress check can no longer run, so it
        # must not fail — and must not pass either.
        raw["conduits"] = []
        raw["destinations"] = []
        path = self.tmp / "declared.json"
        path.write_text(json.dumps(raw), encoding="utf-8")
        code, out, _ = run("report", str(path))
        self.assertEqual(code, EXIT_OK)
        self.assertIn("NON VERIFICATI", out)

    def test_scan_without_credentials_fails_cleanly(self) -> None:
        code, _, err = run("scan")
        self.assertEqual(code, EXIT_ERROR)
        self.assertIn("--url", err)


class TestSummary(unittest.TestCase):
    def test_names_the_unverified_count_explicitly(self) -> None:
        text = summary(scan(), derive(scan()))
        self.assertIn("NON VERIFICATI", text)
        self.assertIn("non sono esiti positivi", text)


class TestHtmlExport(unittest.TestCase):
    def setUp(self) -> None:
        self.scan = scan()
        self.html = render_html(self.scan, derive(self.scan))

    def test_is_self_contained(self) -> None:
        # No script, no external asset: it has to open from an archive with no
        # network and no server.
        self.assertNotIn("<script", self.html.lower())
        for marker in ("src=", "href=", "@import", "fonts.googleapis"):
            with self.subTest(marker=marker):
                self.assertNotIn(marker, self.html)

    def test_carries_both_themes(self) -> None:
        self.assertIn("prefers-color-scheme:dark", self.html)

    def test_states_its_limits(self) -> None:
        self.assertIn("mai “sicuro”", self.html)
        self.assertIn("Non verificato", self.html)

    def test_escapes_hostile_content(self) -> None:
        raw = json.loads((FIXTURES / "home.json").read_text(encoding="utf-8"))
        raw["devices"][0]["name"] = '<img src=x onerror="alert(1)">'
        hostile = Scan.from_dict(raw)
        rendered = render_html(hostile, derive(hostile))
        self.assertNotIn("<img src=x", rendered)
        self.assertIn("&lt;img src=x", rendered)

    def test_json_export_round_trips(self) -> None:
        payload = json.loads(render_json(self.scan, derive(self.scan)))
        self.assertEqual(validate(payload["scan"]), [])
        self.assertIn("counts", payload["derived"]["checks"])

    def test_renders_an_empty_scan(self) -> None:
        empty = Scan(generated_at="2026-08-30T09:00:00+00:00", collector="native")
        rendered = render_html(empty, derive(empty))
        self.assertIn("Nessun condotto", rendered)


if __name__ == "__main__":
    unittest.main()
