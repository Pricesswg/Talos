<p align="center">
  <img src="custom_components/talos/brand/logo.png" alt="Talos - HA Security scanner" width="512">
</p>

# Talos - HA Security scanner

Talos maps where the data in my house comes from and where it goes. It reads what Home Assistant
declares about its own devices, watches what my DNS resolver actually sees them do, and puts the two
side by side. Everything it reports is labelled with the evidence behind it, so a number in the panel
can always be traced back to a registry entry or a query log line.

I wrote it because `iot_class` in a manifest tells you how Home Assistant talks to a device, and
nothing at all about how that device talks to the internet. A Shelly on `local_push` can have Shelly
Cloud enabled in parallel and Home Assistant will never know. Those are two independent facts, and
Talos keeps them independent all the way through.

## How it works

Every scan, by default every 15 minutes, runs the same five steps.

**1. Read the declared side.** The registries are read in process: `config_entries`, the device
registry, the entity registry, the area registry, plus the integration manifests through
`async_get_integrations`. The unit is the **config entry**, not the device, because `mobile_app`,
weather and TTS own entities without owning any device, and those are the most cloud bound things in
the house. Disabled entries, devices and entities are skipped. The result is a scan carrying
`evidence: declared` and nothing else.

**2. Poll AdGuard Home.** The query log is a rolling buffer, not a queryable history, so Talos walks
it newest first with the `older_than` cursor and stops at the cursor from the previous poll. Running
totals per client and domain live in its own SQLite file under `config/talos/`, never in the recorder
database, because AdGuard's retention rolls over and a device that resolved a domain four thousand
times last week would otherwise read as a handful today.

**3. Join the two.** The device registry knows MACs. The query log knows IPs. The DHCP leases are the
only place both appear on the same row, which is why they matter (see below). Anything the join
cannot attribute becomes an `unknown_host` conduit rather than being dropped.

**4. Classify and attribute.** Domains are resolved against a list in
`talos_core/data/domains.json`: vendor cloud, telemetry, push service, CDN, NTP, updates, local
broker. Unclassified domains stay counted and visible. Devices with no IP of their own, Zigbee and
Z-Wave nodes, cannot have direct egress, so when their hub is seen contacting a vendor they get an
`inherited` conduit pointing at that hub instead of a fabricated direct one.

**5. Derive and check.** From the joined scan Talos builds the matrix, the offline autonomy figures
and the exposure figures, then runs the posture checks from
`talos_core/data/checks.json`. Output goes to the panel, to nine summary entities, and to an HTML or
JSON export.

The whole pipeline is a pure function of the collected data. The same input always produces the same
report, which is what makes any of it worth arguing with.

### The matrix

The crossing of those two axes is the thing I could not get from any existing tool:

| | No egress observed | Egress observed |
|---|---|---|
| **Local to HA** (`local_push`, `local_polling`) | Fully local | **The device phones home behind Home Assistant's back** |
| **Cloud to HA** (`cloud_push`, `cloud_polling`) | Anomaly worth investigating | Declared dependency, confirmed |

The top right cell is the one the whole project exists to fill. The bottom left is not a merit: a
device declared cloud that never speaks usually means it is not correlated, or the integration is
broken.

### Offline autonomy and external exposure

These are two separate figures and Talos never merges them into a single score. A camera can send
telemetry every minute and keep working perfectly with the router unplugged, while another can be
silent on the wire and die the moment its vendor's API hiccups. One number flattens four different
situations and none of them gets the fix it needs.

**Autonomy** counts the entities and integrations that keep working with the uplink down, derived
from `iot_class` and grouped by vendor, so the report can say what a single vendor outage takes with
it. **Exposure** counts the devices seen reaching outside, grouped by vendor, with the query volume
and whether AdGuard blocked any of it. Reolink cameras in my house show up prominently in the second
and not at all in the first, which is exactly right: they chat with their vendor but Home Assistant
drives them locally.

## What it checks, and what it does not

**It checks:**

- Devices that Home Assistant drives locally but that were observed contacting their vendor's cloud
- Hosts holding a DHCP lease that never query the resolver, so they are running a DNS server
  hardcoded in firmware and are a blind spot for everything else here
- Third party integrations, not shipped with Home Assistant, that declare cloud access
- Devices reaching outside from the trusted LAN rather than from an IoT VLAN
- Integrations declared cloud that were never seen contacting anything
- Which entities and automations stop working when the internet drops, and which vendor takes the
  biggest share with it
- Domains nobody has classified yet, counted and listed rather than hidden

**It does not check, and will not:**

- No CVE matching, no vulnerability database, no exploit attempts
- No port scanning and no active probing of any device
- No traffic inspection. DNS says **who** a device talked to, never what was said or how much. The
  report says "dependency detected" and never "data exfiltration"
- Nothing is modified. Every source is read only

Five checks in the rule file are declared but not implemented yet: anonymous MQTT broker, unknown
MQTT clients, Z-Wave nodes without S2, cleartext RTSP, and ARP against the registry. They appear in
the unverified list with the reason and the source that would be needed, rather than being silently
absent.

### Unverified is its own category

A check that could not run is not a pass. If AdGuard is unreachable, the "local with egress" quadrant
is empty because nothing was observed, not because nothing is wrong, and reporting that as green
would be the exact failure this tool exists to avoid. Every check declares its preconditions, and
when one is not met the check moves to the unverified list with the reason spelled out. That count
sits next to the other two in the panel and cannot be hidden.

## The two views

The panel is deliberately split by question rather than by density of data. It is not the same screen
with fewer columns.

**Basic** answers two things: what stops working without internet, and which devices talk outside.
Findings are the high and medium severity checks with the remediation next to each one, written
without network jargon, plus the explicit count of what could not be verified.

**Advanced** answers who talks to whom and on what evidence: the matrix, a column graph of the flows
where the arcs that bypass Home Assistant are drawn in red, the full conduit table with each row
labelled `declared`, `observed` or `inherited`, the check results with their subjects, and the
unverified list with each reason.

Both views come from the same derivations. There is no second code path that could drift.

## Installation

### HACS

1. HACS, Integrations, three dot menu, **Custom repositories**
2. Add `https://github.com/Pricesswg/Talos`, category **Integration**
3. Install, restart Home Assistant
4. **Settings, Devices and services, Add integration, Talos**

### Manual

Copy `custom_components/talos` into the `custom_components` folder of your configuration and restart.
The bundled core under `vendor/` is committed on purpose, so a copy of that folder is self contained.

## Configuration

**AdGuard Home is optional.** Without it Talos still answers the autonomy question from what Home
Assistant declares. It cannot answer the exposure question, and it writes that into the report rather
than leaving the column blank.

> ### Why the DHCP leases matter
>
> The Home Assistant registry knows **MACs**. The query log knows **IPs**. The DHCP leases are the
> only place the two appear together.
>
> Without leases every observation stays attributed to an unknown host. Talos can say that somebody
> contacted a vendor, but not **which device it was**, so the quadrant that matters comes out empty:
> not because there is nothing there, but because nothing can be attributed. The resolver's clients
> also cannot be compared against the devices on the network, so an appliance with a hardcoded DNS
> server never surfaces at all.
>
> For full coverage, enable AdGuard Home's DHCP server, or supply the router's leases. The report
> always states which of the two situations it is describing.

In the options you set the scan interval, the **network ranges** for the trusted LAN and the IoT
VLAN, and retention. Until a range is given, the checks that depend on zones declare themselves
unrunnable instead of passing.

### Retention

The query log produces one row per client and domain pair, so the database would grow without bound.
Two limits, both applied on every scan, because either one alone fails:

| Setting | Default | What it does |
|---|---|---|
| `observation_days` | 90 | A device replaced months ago stops shaping today's report |
| `max_observations` | 20000 | **This is what bounds the file.** Roughly 4 MB in practice |
| `scan_history` | 5 | Snapshots are a convenience, the observations are the historical record |

Freed pages are actually returned to the filesystem (`auto_vacuum=INCREMENTAL`). A plain `DELETE`
does not shrink a SQLite file.

## The panel is admin only

Talos registers a sidebar panel with `require_admin`, not a Lovelace card. A card ends up on a
dashboard, and a dashboard ends up on the kitchen tablet or on a guest account. This report lists
addresses, MACs and the topology of the house, so not being embeddable is deliberate.

The same reasoning applies to `talos.export_report`: the default target is `config/talos/`, not
`config/www/`, because that directory is served at `/local/` without authentication. Writing there is
allowed but the service logs a warning when it happens.

## Command line

The core is a plain Python package with no dependencies and no `homeassistant.*` imports, so it runs
out of band: a container on another machine, a cron job, a laptop.

```bash
export TALOS_HA_TOKEN=...            # long lived access token
export TALOS_ADGUARD_PASSWORD=...

talos scan --url ws://homeassistant.local:8123/api/websocket \
           --adguard http://192.168.1.10:3000 \
           --zone-trusted 192.168.1.0/24 \
           --db ~/talos.db --html report.html
```

Credentials are read from the environment because a command line ends up in shell history and in
process listings. The exit code is `1` when there are high severity findings, so cron notices. The
HTML file is self contained: no scripts, no external assets, it opens from an archive a year later on
a machine with no network.

Also available: `talos validate scan.json` and `talos report scan.json --html out.html`.

## Extending it without touching code

- **Domains**, `talos_core/data/domains.json`. That `*.tuya.com` is a vendor cloud is something a
  person knows, not something an algorithm derives. Your rules are layered on top of the shipped
  list, never replacing it.
- **Checks**, `talos_core/data/checks.json`. Severity and remediation are data. The selectors are a
  small declared vocabulary: a DSL rich enough to express arbitrary logic would be a programming
  language dressed up as a configuration file.

Both accept JSON always, and YAML when PyYAML is present, which inside Home Assistant it always is.
Point at your own file from the integration options.

## Known limits

- **DNS over HTTPS.** A device that encrypts its own DNS queries on port 443 is indistinguishable
  from ordinary traffic. A structural gap this approach does not cover.
- **Home Assistant's exposure on the internet.** An instance cannot test its own reachability from
  outside. Marked unverifiable, not faked.
- **The ARP table.** Inside a container the ARP cache only holds peers Home Assistant spoke to
  recently, not the whole LAN. DHCP leases stay the better source.
- **The flow graph** groups devices by integration above ten origins and states what it is not
  drawing. It does not use a graph layout library.

## Architecture

```
talos_core/                plain Python package, no dependencies, no homeassistant imports
├── model, validate        data model and validator with stable error codes
├── derive, checks         matrix, autonomy, exposure, posture check engine
├── sources/               declared side (WebSocket API and in process registries)
├── observed/              observed side (AdGuard), classification, join
└── storage, cli, export   persistence with retention, CLI, HTML report

custom_components/talos/   thin wrapper: config flow, coordinator, entities, panel
```

The split is not cosmetic. The core has to be testable against JSON fixtures without running Home
Assistant, otherwise it stops being testable in CI and every Home Assistant release becomes a
regression risk.

```bash
python3 -m unittest discover -s tests -t .
```

216 tests, none of which need a network or a Home Assistant instance.

## License

MIT, see [LICENSE](LICENSE).
