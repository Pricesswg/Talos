"""Command line entry point.

Runs the same pipeline the integration runs, out of band: a container on
another machine, a cron job, a laptop. Credentials are read from the
environment by default rather than from argv, because a command line ends up
in shell history and in process listings.

    export TALOS_HA_TOKEN=...            # long lived access token
    export TALOS_ADGUARD_PASSWORD=...
    talos scan --url ws://homeassistant.local:8123/api/websocket \\
               --adguard http://192.168.1.10:3000 --html report.html
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any, Sequence

from . import __version__
from .checks import CheckEngine
from .derive import Derived, derive
from .export_html import render_html, render_json
from .model import Scan
from .observed import AdGuardCollector, AiohttpJsonTransport, DomainClassifier, merge_observed
from .sources import AiohttpTransport, WebSocketSource
from .storage import RetentionPolicy, TalosStore
from .validate import validate
from .zones import ZoneMap

EXIT_OK = 0
EXIT_FINDINGS = 1
EXIT_ERROR = 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="talos", description="Data provenance and offline autonomy for Home Assistant")
    parser.add_argument("--version", action="version", version=f"talos-core {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    scan = sub.add_parser("scan", help="collect from Home Assistant (and AdGuard) and produce a report")
    scan.add_argument("--url", default=os.environ.get("TALOS_HA_URL"),
                      help="Home Assistant WebSocket, e.g. ws://host:8123/api/websocket")
    scan.add_argument("--token", default=os.environ.get("TALOS_HA_TOKEN"),
                      help="long lived access token (better via TALOS_HA_TOKEN)")
    scan.add_argument("--adguard", default=os.environ.get("TALOS_ADGUARD_URL"),
                      help="AdGuard Home base URL; without it the report stays declared-only")
    scan.add_argument("--adguard-user", default=os.environ.get("TALOS_ADGUARD_USERNAME", ""))
    scan.add_argument("--adguard-password", default=os.environ.get("TALOS_ADGUARD_PASSWORD", ""))
    scan.add_argument("--db", type=Path, help="SQLite file holding the incremental totals")
    scan.add_argument("--observation-days", type=int, default=RetentionPolicy().observation_days)
    scan.add_argument("--max-observations", type=int, default=RetentionPolicy().max_observations)
    _shared_output(scan)

    report = sub.add_parser("report", help="recompute and re-export from a saved scan")
    report.add_argument("file", type=Path, help="scan document in JSON")
    _shared_output(report)

    check = sub.add_parser("validate", help="validate a scan document")
    check.add_argument("file", type=Path)
    return parser


def _shared_output(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--zone-trusted", default="", help="trusted LAN subnet, e.g. 192.168.1.0/24")
    parser.add_argument("--zone-iot", default="", help="IoT VLAN subnet")
    parser.add_argument("--domains", type=Path, help="extra domain rules (JSON or YAML)")
    parser.add_argument("--checks", type=Path, help="alternative check list (JSON or YAML)")
    parser.add_argument("--json", dest="json_out", type=Path, help="write the scan and its derivations as JSON")
    parser.add_argument("--html", dest="html_out", type=Path, help="write a self-contained HTML report")
    parser.add_argument("--quiet", action="store_true", help="do not print the summary")


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "validate":
            return _cmd_validate(args)
        if args.command == "report":
            return _cmd_report(args)
        return asyncio.run(_cmd_scan(args))
    except KeyboardInterrupt:  # pragma: no cover
        return EXIT_ERROR
    except Exception as err:  # noqa: BLE001
        print(f"error: {err}", file=sys.stderr)
        return EXIT_ERROR


def _cmd_validate(args: Any) -> int:
    findings = validate(json.loads(args.file.read_text(encoding="utf-8")))
    if not findings:
        print(f"{args.file}: valid")
        return EXIT_OK
    for finding in findings:
        print(finding)
    print(f"\n{len(findings)} problem(s)", file=sys.stderr)
    return EXIT_FINDINGS


def _cmd_report(args: Any) -> int:
    raw = json.loads(args.file.read_text(encoding="utf-8"))
    # Accept both a bare scan and the combined export this CLI writes.
    document = raw.get("scan") if isinstance(raw, dict) and "scan" in raw else raw
    findings = validate(document)
    if findings:
        print(f"{args.file}: invalid document ({len(findings)} problems)", file=sys.stderr)
        for finding in findings[:5]:
            print(f"  {finding}", file=sys.stderr)
        return EXIT_ERROR
    scan = Scan.from_dict(document)
    return _finish(scan, derive(scan, _engine(args)), args)


async def _cmd_scan(args: Any) -> int:
    if not args.url or not args.token:
        print("--url and --token are required (or TALOS_HA_URL and TALOS_HA_TOKEN)", file=sys.stderr)
        return EXIT_ERROR

    async with AiohttpTransport(args.url, args.token) as transport:
        scan = await WebSocketSource(transport).fetch()

    store = None
    if args.db:
        store = TalosStore(
            args.db,
            RetentionPolicy(
                observation_days=args.observation_days,
                max_observations=args.max_observations,
            ),
        )

    try:
        if args.adguard:
            scan = await _collect_observed(scan, store, args)
        elif not args.quiet:
            print("note: no AdGuard given, the report stays declared-only\n")

        derived = derive(scan, _engine(args))
        if store is not None:
            store.save_scan(scan)
            report = store.prune()
            if not args.quiet and report.total_removed:
                print(f"retention: removed {report.total_removed} rows\n")
        return _finish(scan, derived, args)
    finally:
        if store is not None:
            store.close()


async def _collect_observed(scan: Scan, store: TalosStore | None, args: Any) -> Scan:
    classifier = DomainClassifier.load()
    if args.domains:
        classifier = classifier.merged_with(DomainClassifier.load(args.domains))

    cursor = store.get_cursor() if store else None
    previous = store.load_observations() if store else ()

    transport = AiohttpJsonTransport(args.adguard, args.adguard_user, args.adguard_password)
    try:
        facts = await AdGuardCollector(transport).fetch(since=cursor, previous=previous)
    finally:
        await transport.close()

    if store is not None:
        store.save_observations(facts.observations)
        store.save_leases(facts.leases)
        store.set_cursor(facts.cursor)

    zones = ZoneMap.from_dict({"trusted_lan": args.zone_trusted, "iot_vlan": args.zone_iot})
    return merge_observed(scan, facts, classifier, zones)


def _engine(args: Any) -> CheckEngine | None:
    return CheckEngine.load(args.checks) if getattr(args, "checks", None) else None


def _finish(scan: Scan, derived: Derived, args: Any) -> int:
    if args.json_out:
        args.json_out.write_text(render_json(scan, derived), encoding="utf-8")
        if not args.quiet:
            print(f"wrote {args.json_out}")
    if args.html_out:
        args.html_out.write_text(render_html(scan, derived), encoding="utf-8")
        if not args.quiet:
            print(f"wrote {args.html_out}")
    if not args.quiet:
        print(summary(scan, derived))
    # A non-zero exit when something needs attention, so cron can notice.
    return EXIT_FINDINGS if derived.checks.counts["failed_high"] else EXIT_OK


def summary(scan: Scan, derived: Derived) -> str:
    a, c, checks = derived.autonomy, derived.correlation, derived.checks
    lines = [
        f"Talos · {scan.generated_at} · HA {scan.ha_version or 'n/a'} · collector {scan.collector}",
        "",
        f"  autonomy      {a.entities_local}/{a.entities_total} entities keep working offline",
        f"  exposure      {len(derived.exposure.devices_direct)}/{derived.exposure.devices_total} devices talk outside",
        f"  correlation   {c.devices_correlated}/{c.devices_total} devices ({c.method})",
        f"  matrix        {len(derived.matrix.local_egress)} local with observed egress",
        "",
        f"  findings      high {checks.counts['failed_high']} · medium {checks.counts['failed_medium']}"
        f" · low {checks.counts['failed_low']} · passed {checks.counts['passed']}",
        f"  UNVERIFIED    {checks.counts['unverified']}, these are not passes",
    ]
    if checks.failed:
        lines.append("")
        for result in checks.failed:
            lines.append(f"  [{result.severity:6s}] {result.title} ({len(result.subjects)})")
    return "\n".join(lines)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
