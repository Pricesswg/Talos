"""Self-contained HTML export.

One file, no network, no scripts: it has to survive being emailed, archived
for a year, and opened on a machine with no internet. So the fonts are the
system stack, the CSS is inline, and nothing is interactive. An archived
report that needs a server to render is not an archive.

The wording follows the panel's: facts and their evidence, never a verdict
the data cannot support.
"""

from __future__ import annotations

import html
import json
from typing import Any

from .derive import Derived
from .model import Scan

SEVERITY_LABEL = {"high": "high", "medium": "medium", "low": "low"}
KIND_LABEL = {
    "vendor_cloud": "vendor cloud",
    "telemetry": "telemetry",
    "push_service": "push service",
    "ota_update": "updates",
    "ntp": "clock",
    "cdn": "CDN",
    "local_broker": "local broker",
    "ha_core": "Home Assistant",
    "unknown": "unclassified",
}
REASON_LABEL = {
    "not_executable": "not runnable",
    "missing_data": "missing data",
    "method_limit": "method limit",
}

_CSS = """
:root{--bg:#f4f6f6;--surface:#fff;--sunken:#e9ecec;--border:#dbe0e1;--ink:#172022;
--ink-soft:#5b696c;--ink-mute:#8b9698;--accent:#16697f;--k-local:#2f7d6a;--k-infra:#64768c;
--k-vendor:#8a4a86;--k-unknown:#868d8e;--alert:#b3261e;--alert-soft:#fbe9e7;--attention:#8a6516}
@media(prefers-color-scheme:dark){:root{--bg:#12191a;--surface:#1a2223;--sunken:#0e1415;
--border:#2b3436;--ink:#e7ecec;--ink-soft:#98a6a8;--ink-mute:#6d7a7c;--accent:#52b2c8;
--k-local:#52b195;--k-infra:#93a5bd;--k-vendor:#c07dbb;--k-unknown:#8d9799;--alert:#ff6f60;
--alert-soft:#331816;--attention:#d5a343}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font-size:14px;line-height:1.5;
font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
.mono{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-variant-numeric:tabular-nums}
.wrap{max-width:1080px;margin:0 auto;padding:32px 24px 64px}
header{border-bottom:1px solid var(--border);padding-bottom:18px;margin-bottom:28px}
h1{font-size:24px;margin:0 0 6px;letter-spacing:-.02em}
.meta{color:var(--ink-mute);font-size:12.5px}
h2{font-size:12px;letter-spacing:.1em;text-transform:uppercase;color:var(--ink-mute);
font-weight:500;margin:34px 0 12px;display:flex;align-items:center;gap:10px}
h2::after{content:"";flex:1;height:1px;background:var(--border)}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:14px}
.stat{background:var(--surface);border:1px solid var(--border);border-radius:14px;padding:18px}
.stat .l{font-size:11px;letter-spacing:.08em;text-transform:uppercase;color:var(--ink-mute)}
.stat .v{font-size:29px;line-height:1.1;margin:8px 0 6px}
.stat .v small{font-size:15px;color:var(--ink-mute)}
.stat .n{font-size:12.5px;color:var(--ink-soft)}
.find{background:var(--surface);border:1px solid var(--border);border-left:3px solid var(--border);
border-radius:12px;padding:14px 16px;margin-bottom:10px}
.find.high{border-left-color:var(--alert)}.find.medium{border-left-color:var(--attention)}
.find.low{border-left-color:var(--accent)}.find.ok{border-left-color:var(--k-local)}
.find .t{font-weight:600;margin-bottom:5px}
.find .d{color:var(--ink-soft);font-size:13px;max-width:74ch}
.find .r{margin-top:9px;padding:8px 11px;background:var(--sunken);border-radius:8px;font-size:12.5px;color:var(--ink-soft)}
table{border-collapse:collapse;width:100%;font-size:12.5px;background:var(--surface);
border:1px solid var(--border);border-radius:12px;overflow:hidden}
th{text-align:left;font-size:10.5px;letter-spacing:.08em;text-transform:uppercase;color:var(--ink-mute);
font-weight:500;padding:9px 12px;background:var(--sunken);border-bottom:1px solid var(--border);white-space:nowrap}
td{padding:9px 12px;border-bottom:1px solid var(--border);vertical-align:top}
tr:last-child td{border-bottom:none}
tr.key td{background:var(--alert-soft)}
.num{text-align:right;font-variant-numeric:tabular-nums}
.sub{display:block;font-size:11px;color:var(--ink-mute)}
.chip{display:inline-block;padding:1px 8px;border-radius:99px;font-size:11px;border:1px solid var(--border);color:var(--ink-soft)}
.matrix td{padding:14px 12px}
.matrix .n{font-size:22px}
.matrix .key{background:var(--alert-soft)}.matrix .key .n{color:var(--alert)}
.scroll{overflow-x:auto}
.note{border:1px dashed var(--border);border-radius:12px;padding:14px 16px;font-size:12.5px;
color:var(--ink-soft);max-width:78ch;margin-top:18px}
"""


def _e(value: Any) -> str:
    return html.escape("" if value is None else str(value))


def _n(value: Any) -> str:
    return "-" if value is None else f"{int(value):,}".replace(",", ".")


def render_html(scan: Scan, derived: Derived, title: str = "Talos") -> str:
    """Render one archivable page. Never raises on partial data."""
    devices = {device.id: device for device in scan.devices}
    integrations = {integration.id: integration for integration in scan.integrations}
    destinations = {destination.id: destination for destination in scan.destinations}
    autonomy = derived.autonomy
    checks = derived.checks

    mqtt_clients = {
        client.client_id: client for client in (scan.mqtt.clients if scan.mqtt else ())
    }

    def name_of(kind: str, identifier: str) -> str:
        if kind == "device":
            device = devices.get(identifier)
            return device.name if device else identifier
        if kind == "integration":
            integration = integrations.get(identifier)
            return integration.title if integration else identifier
        if kind == "mqtt_client":
            # The address is the only handle on a client nothing else names.
            client = mqtt_clients.get(identifier)
            return f"{identifier} ({client.address})" if client and client.address else identifier
        return identifier

    parts: list[str] = []
    parts.append(f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{_e(title)}</title><style>{_CSS}</style></head><body><div class="wrap">
<header>
  <h1>{_e(title)}</h1>
  <div class="meta mono">generated {_e(scan.generated_at)} · Home Assistant {_e(scan.ha_version or "n/a")}
  · collector {_e(scan.collector)} · schema {_e(scan.schema_version)}</div>
</header>""")

    correlation = derived.correlation
    parts.append(f"""<div class="stats">
  <div class="stat"><div class="l">If the internet drops</div>
    <div class="v">{_n(autonomy.entities_local)}<small>/{_n(autonomy.entities_total)} entities</small></div>
    <div class="n">{_n(autonomy.entities_cloud)} entities stop.</div></div>
  <div class="stat"><div class="l">Talking outside</div>
    <div class="v">{_n(len(derived.exposure.devices_direct))}<small>/{_n(derived.exposure.devices_total)} devices</small></div>
    <div class="n">{_n(len(derived.matrix.local_egress))} are local yet contact their vendor.</div></div>
  <div class="stat"><div class="l">Unverified</div>
    <div class="v">{_n(len(checks.unverified))}<small>checks</small></div>
    <div class="n">Not passed, not failed. They do not count as all clear.</div></div>
  <div class="stat"><div class="l">Correlation</div>
    <div class="v">{_n(correlation.devices_correlated)}<small>/{_n(correlation.devices_total)} devices</small></div>
    <div class="n">The uncorrelated ones may have egress I cannot see.</div></div>
</div>""")

    parts.append("<h2>Findings</h2>")
    if checks.failed:
        for result in checks.failed:
            names = [name_of(result.subject_kind, s) for s in result.subjects][:12]
            parts.append(f"""<div class="find {_e(result.severity)}">
  <div class="t">{_e(result.title)} <span class="chip">{_e(SEVERITY_LABEL.get(result.severity, result.severity))} severity · {len(result.subjects)}</span></div>
  <div class="d">{_e(result.detail)}{f'<br><span class="mono">{_e(", ".join(names))}</span>' if names else ""}</div>
  {f'<div class="r">{_e(result.remediation)}</div>' if result.remediation else ""}
</div>""")
    else:
        parts.append('<div class="find ok"><div class="t">No findings</div>'
                     '<div class="d">No runnable check produced a finding.</div></div>')
    for result in checks.passed:
        parts.append(f'<div class="find ok"><div class="t">{_e(result.title)} '
                     f'<span class="chip">passed</span></div></div>')

    matrix = derived.matrix

    def cell(ids: tuple[str, ...], text: str, key: bool = False) -> str:
        sample = ", ".join(name_of("device", i) for i in ids[:4])
        more = f" +{len(ids) - 4}" if len(ids) > 4 else ""
        return (f'<td class="{"key" if key and ids else ""}"><div class="n">{len(ids)}</div>'
                f'<div class="sub">{_e(text)}{_e(sample and " " + sample + more)}</div></td>')

    parts.append(f"""<h2>Matrix</h2><div class="scroll"><table class="matrix">
<tr><th>HA class / network</th><th>No egress observed</th><th>Egress observed</th></tr>
<tr><th>Local<span class="sub mono">local_push · local_polling</span></th>
{cell(matrix.local_silent, "No outbound lookup observed.")}
{cell(matrix.local_egress, "Phoning home behind Home Assistant's back.", True)}</tr>
<tr><th>Cloud<span class="sub mono">cloud_push · cloud_polling</span></th>
{cell(matrix.cloud_silent, "Declared cloud but silent. Worth investigating.")}
{cell(matrix.cloud_egress, "Declared dependency, confirmed.")}</tr>
</table></div>""")

    if matrix.inherited:
        inherited = ", ".join(
            f"{name_of('device', i.device_id)} (via {name_of('device', i.hub_id)})"
            for i in matrix.inherited[:10]
        )
        parts.append(f'<div class="note"><b>Exposed through a hub:</b> {_e(inherited)}. '
                     "Kept out of the quadrants: that is one thing to fix, not many.</div>")

    rows: list[str] = []
    for conduit in sorted(scan.conduits, key=lambda c: -(c.query_count or 0)):
        destination = destinations.get(conduit.destination_id)
        fqdn = destination.fqdn if destination else conduit.destination_id
        kind = destination.kind if destination else "unknown"
        if conduit.source.kind == "device":
            device = devices.get(conduit.source.id or "")
            origin = (f"{_e(device.name)}<span class='sub mono'>{_e(device.ip or device.transport)}</span>"
                      if device else _e(conduit.source.id))
        elif conduit.source.kind == "integration":
            integration = integrations.get(conduit.source.id or "")
            origin = (f"{_e(integration.title)}<span class='sub mono'>{_e(integration.domain)} · no device</span>"
                      if integration else _e(conduit.source.id))
        elif conduit.source.kind == "ha_core":
            origin = "Home Assistant<span class='sub mono'>core</span>"
        else:
            origin = f"Unidentified host<span class='sub mono'>{_e(conduit.source.id)}</span>"
        key = (conduit.evidence == "observed" and conduit.source.kind == "device"
               and conduit.source.id in matrix.local_egress)
        rows.append(f"""<tr class="{"key" if key else ""}"><td>{origin}</td>
<td class="mono">{_e(fqdn)}</td><td>{_e(KIND_LABEL.get(kind, kind))}</td>
<td class="mono">{_e(conduit.evidence)}</td><td class="num">{_n(conduit.query_count)}</td>
<td>{_e(conduit.filter_status or "-")}</td></tr>""")

    parts.append(f"""<h2>Conduits · {len(scan.conduits)}</h2><div class="scroll"><table>
<tr><th>Origin</th><th>Destination</th><th>Kind</th><th>Evidence</th><th class="num">Queries</th><th>Filter</th></tr>
{"".join(rows) or "<tr><td colspan='6'>No conduit in this scan.</td></tr>"}
</table></div>""")

    parts.append(f"<h2>Unverified · {len(checks.unverified)}</h2>")
    for check in checks.unverified:
        parts.append(f"""<div class="find">
  <div class="t">{_e(check.title)} <span class="chip">{_e(REASON_LABEL.get(check.reason, check.reason))}</span></div>
  <div class="d">{_e(check.detail)}</div></div>""")

    parts.append("""<div class="note"><b>What this report does not say.</b> Talos watches which
addresses devices ask for, not what they send nor how much. It opens no traffic, tries no
passwords, scans no ports. A device that encrypts its DNS queries too stays invisible: that is a
limit of the method, not a check that was skipped. An empty cell means "not observed", never
"safe".</div>""")

    parts.append("</div></body></html>")
    return "\n".join(parts)


def render_json(scan: Scan, derived: Derived) -> str:
    """The same run as data, for anything that wants to consume it."""
    return json.dumps({"scan": scan.to_dict(), "derived": derived.to_dict()}, indent=2, ensure_ascii=False)
