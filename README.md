<p align="center">
  <img src="custom_components/talos/brand/logo.png" alt="Talos - HA Security scanner" width="512">
</p>

# Talos - HA Security scanner

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
![hass](https://img.shields.io/badge/Home%20Assistant-2024.6%2B-blue.svg)
![license](https://img.shields.io/badge/license-MIT-green.svg)

**Talos** maps where the data in a Home Assistant install comes from and where it goes. It reads what
Home Assistant declares about its own devices, cross-references it with what the DNS resolver
actually observed those devices doing, and reports both sides with the evidence attached to every
row. It also answers the question no integration answers today: what stops working when the internet
drops, and which vendor takes the largest share of the house with it.

The reason it exists in one sentence: `iot_class` in a manifest says how Home Assistant talks to a
device, and nothing about how that device talks to the internet. A Shelly on `local_push` can have
Shelly Cloud enabled in parallel and Home Assistant will never know. Talos keeps those two facts
separate everywhere, and crosses them only in one place, the matrix below.

A single admin-only panel provides:

- Basic, Map, Advanced and Settings views, split by question rather than by density of data, all
  derived from the same computation so they cannot drift apart
- A connection map grouping every device by transport and by integration, with the hub hierarchy
  spelled out. Declared data only, so it works with no AdGuard configured
- The declared / observed matrix, with the quadrant that matters (local to Home Assistant, yet caught
  phoning home) highlighted as the only red thing in the interface
- Offline autonomy: entities and integrations that keep working with the uplink down, grouped by
  vendor so a single vendor outage can be costed
- External exposure: devices seen reaching outside, with query volume, vendor and whether AdGuard
  filtered any of it
- A column graph of the flows, where the arcs that bypass Home Assistant entirely are the point of
  the picture, grouping by integration above ten origins instead of truncating
- A conduit table where every row is labelled `declared`, `observed` or `inherited`, never mixed
- Posture checks with severity and remediation, and an explicit count of the checks that could not
  run, which are never folded into the passes
- The zero check: hosts holding a DHCP lease that never query the resolver, which are the blind spots
  of the tool itself
- Nine summary entities and one problem binary sensor, no per-device entity pollution
- A self-contained HTML export, no scripts and no external assets, for archiving or sharing
- A standalone CLI that runs the same pipeline out of band, against a remote instance
- Domain list and check list in data files, extensible without touching code, JSON always and YAML
  when PyYAML is present
- Setup that finds the AdGuard Home endpoint on its own, from the official integration or the add-on,
  and pre-fills the form with whatever actually answered

Everything is read-only. No port scanning, no active probing, no traffic inspection, no CVE matching.

## Why "Talos"?

In Greek mythology Talos is the bronze automaton that circled Crete three times a day, watching who
approached the shore and what they carried. He did not attack the island's own people and he did not
guess: he watched, and he reported. That is what this integration does for a house, which is also why
it refuses to call a heuristic on metadata a vulnerability.

## How a scan works

Every scan, by default every 15 minutes, runs the same five steps.

**1. Read the declared side.** The registries are read in process: `config_entries`, the device
registry, the entity registry, the area registry, plus the integration manifests through
`async_get_integrations`. The canonical unit is the **config entry**, not the device, because
`mobile_app`, weather and TTS own entities without owning any device and are the most cloud-bound
things in a typical install. Disabled entries, devices and entities are skipped. The result is a scan
carrying `evidence: declared` and nothing else.

**2. Poll AdGuard Home.** The query log is a rolling buffer, not a queryable history, so Talos walks
it newest first with the `older_than` cursor and stops at the cursor left by the previous poll.
Running totals per client and domain live in a dedicated SQLite file under `config/talos/`, never in
the recorder database, because AdGuard's retention rolls over and a device that resolved a domain
four thousand times last week would otherwise read as a handful today.

**3. Join the two.** The device registry knows MACs. The query log knows IPs. The DHCP leases are the
only place both appear on the same row, which is why they matter. Anything the join cannot attribute
becomes an `unknown_host` conduit instead of being dropped.

**4. Classify and attribute.** Domains are resolved against `talos_core/data/domains.json`: vendor
cloud, telemetry, push service, CDN, NTP, updates, local broker. Unclassified domains stay counted
and listed. Zigbee and Z-Wave nodes carry no IP and therefore cannot have direct egress, so when
their hub is observed contacting a vendor the children get an `inherited` conduit pointing at that
hub, rather than a fabricated direct one. Nine Hue bulbs behind one talkative bridge are one thing to
fix, not ten.

**5. Derive and check.** From the joined scan Talos builds the matrix, the autonomy figures and the
exposure figures, then runs the posture checks from `talos_core/data/checks.json`. Output goes to the
panel, to the summary entities, and to the HTML or JSON export.

The pipeline is a pure function of the collected data. The same input always produces the same
report.

### The matrix

| | No egress observed | Egress observed |
|---|---|---|
| **Local to HA** (`local_push`, `local_polling`) | Fully local | **The device phones home behind Home Assistant's back** |
| **Cloud to HA** (`cloud_push`, `cloud_polling`) | Anomaly worth investigating | Declared dependency, confirmed |

The top-right cell is the one the project exists to fill. The bottom-left is not a merit: a device
declared cloud that never speaks usually means it is not correlated, uses its own resolver, or the
integration is broken.

### Autonomy and exposure are two numbers, never one score

A camera can send telemetry every minute and keep working perfectly with the router unplugged, while
another can be silent on the wire and die the moment its vendor's API hiccups. A single score
flattens four different situations and none of them gets the fix it needs, so Talos reports the two
separately. Reolink cameras show up prominently in exposure and not at all in autonomy, which is
correct: they chat with their vendor, but Home Assistant drives them locally.

## What it checks, and what it does not

It checks:

- Devices Home Assistant drives locally that were observed contacting their vendor's cloud
- Hosts with a DHCP lease that never query the resolver, so they run a DNS server hardcoded in
  firmware and are invisible to every other check here
- Third-party integrations, not shipped with Home Assistant, that declare cloud access
- Devices reaching outside from the trusted LAN rather than from an IoT VLAN
- Integrations declared cloud that were never seen contacting anything
- Which entities stop working when the internet drops, and which vendor accounts for most of them
- Domains nobody has classified yet, counted and listed rather than hidden

It does not check, and will not:

- No CVE matching, no vulnerability database, no exploit attempts
- No port scanning and no active probing of any device
- No traffic inspection. DNS says **who** a device talked to, never what was said or how much. The
  report says "dependency detected" and never "data exfiltration"
- Nothing is modified. Every source is read-only

Five checks in the rule file are declared but not implemented yet: anonymous MQTT broker, unknown
MQTT clients, Z-Wave nodes without S2, cleartext RTSP, and ARP against the registry. They appear in
the unverified list with the reason and the source that would be needed, rather than being silently
absent.

### Unverified is its own category

A check that could not run is not a pass. If AdGuard is unreachable the "local with egress" quadrant
comes out empty because nothing was observed, not because nothing is wrong, and reporting that as
green would be the exact failure this tool exists to avoid. Every check declares its preconditions,
and when one is not met the check moves to the unverified list with the reason spelled out. That
count sits next to the other two in the panel and cannot be hidden.

## The two views

**Basic** answers two things: what stops working without internet, and which devices talk outside.
Findings are the high and medium severity checks with the remediation next to each one, written
without network jargon, plus the explicit count of what could not be verified.

**Map** answers how devices reach Home Assistant. A graph centred on Home Assistant branches out to
the transports (Zigbee, Wi-Fi, Z-Wave, Thread, Matter, Bluetooth, Ethernet) and then to the
integrations and their devices. The layout is deterministic rather than a force simulation, so the
same house always draws the same picture and two people can talk about it; the angular width of a
branch is its share of the devices, so the shape of the drawing is the shape of the install.

Three detail levels, stepped with the plus and minus buttons: transports, integrations, devices.
Labels sit horizontally under their node, and device labels appear as you zoom in, so a wide view
stays readable and a close one names everything.

Three ways to narrow it down. A chip per transport keeps only that trunk. Clicking an integration
isolates it, showing its devices and nothing else. The search box filters devices by name or area
rather than dimming them, so what is left on screen is the answer. Any of them clears from the badge
in the toolbar.

Nodes can be dragged, and the rest settle around them: after each layout a fixed number of
relaxation passes push overlapping nodes apart and slide them back onto their ring, so a crowded
branch spreads out instead of piling up. Wheel zooms, drag pans. Below the graph, the hubs and the
devices behind them, then the full list by transport.

It reads the registry only, so it populates even with no AdGuard configured.

**Advanced** answers who talks to whom and on what evidence: the matrix, the flow graph, the full
conduit table with its evidence labels, the check results with their subjects, and the unverified
list with each reason. The flow graph draws observed egress, so it stays empty until AdGuard is
connected, and says so rather than showing empty bands.

**Settings** holds the language, the AdGuard connection shown read only, and the editable options:
interval, retention, network ranges and rule file paths.

## Installation

### Through HACS (recommended)

[![Add to HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Pricesswg&repository=Talos&category=integration)

1. HACS, Integrations, three-dot menu, **Custom repositories**
2. Add `https://github.com/Pricesswg/Talos`, category **Integration**
3. Install and restart Home Assistant

Then add the integration:

[![Add Talos integration](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=talos)

### Manual installation

Copy `custom_components/talos` into the `custom_components` folder of your configuration and restart.
The bundled core under `vendor/` is committed on purpose, so that folder is self-contained.

## First-time setup

The config flow looks for AdGuard Home before asking. It reads the configuration of the official
AdGuard integration if you have it, then tries the community add-on's hostname and the address Home
Assistant knows itself by, and probes each one against `/control/status`. The first address that
answers is put in the form, together with the credentials it found, and you confirm or change it.

Nothing is used silently and nothing is assumed: a candidate only counts once the API has answered
on it, because a wrong address that looks plausible produces an empty report that reads like a clean
one. If nothing answers, the form comes up empty and you fill it in by hand. The same probe runs
when you reconfigure an entry that has no address yet.

### Which address to use for AdGuard

| Setup | Address |
|---|---|
| AdGuard Home add-on on HAOS or Supervised | `http://a0d7b954-adguard:3000`, the add-on's internal hostname, which survives an IP change |
| Anything else | The LAN address of the machine, `http://192.168.1.10:3000` |

Do not use `127.0.0.1` unless Home Assistant runs with host networking. Inside a container that
address is the container itself, not the machine. The port is the one you open the AdGuard web
interface on, 3000 by default but often moved to 80 after the first setup.

Check the address in a browser before typing it into the config flow: the address followed by
`/control/status` must return JSON with `running` and `dns_addresses`. That is the exact endpoint
the config flow probes.

**AdGuard is optional.** Without it Talos still answers the autonomy question from what Home
Assistant declares. It cannot answer the exposure question, and it writes that into the report rather
than leaving the column blank.

Straight after setup, open the options and set the **network ranges**. Until a range is given, the
checks that depend on zones declare themselves unrunnable instead of passing.

### Why the DHCP leases matter

The Home Assistant registry knows **MACs**. The query log knows **IPs**. The DHCP leases are the only
place the two appear together.

Without leases every observation stays attributed to an unknown host. Talos can say that somebody
contacted a vendor, but not **which device it was**, so the quadrant that matters comes out empty:
not because there is nothing in it, but because nothing can be attributed. The resolver's clients
also cannot be compared against the devices on the network, so an appliance with a hardcoded DNS
server never surfaces at all.

For full coverage, enable AdGuard Home's DHCP server, or supply the router's leases. The report
always states which of the two situations it is describing.

## Options

| Option | Default | What it does |
|---|---|---|
| Scan interval | 15 min | The query log is paginated and can be long, so the default is conservative |
| Trusted LAN / IoT VLAN / Guest subnet | empty | Comma-separated CIDR ranges. An address matching none stays `unknown` and is never assumed trusted |
| `observation_days` | 90 | A device replaced months ago stops shaping today's report |
| `max_observations` | 20000 | **This is what bounds the database file.** Roughly 4 MB in practice |
| `scan_history` | 5 | Snapshots are a convenience, the observations are the historical record |
| Query log page size | 500 | Records fetched per request |
| Maximum pages per scan | 40 | A budget, so one scan cannot walk a busy log for minutes |
| Extra domain rules | empty | Absolute path to a JSON or YAML file, layered on top of the built-in list |
| Extra posture checks | empty | Absolute path to a JSON or YAML file replacing the check list |

Retention applies **both** limits on every scan, because either one alone fails: a time window does
not bound a busy network, and a row cap alone keeps stale rows forever while dropping fresh ones.
Freed pages are actually returned to the filesystem (`auto_vacuum=INCREMENTAL`), since a plain
`DELETE` does not shrink a SQLite file.

## Entities

All under one service device. No per-asset entities: a house with three hundred devices would
otherwise gain three hundred registry entries for numbers the panel already shows.

| Entity | What it reports |
|---|---|
| `sensor.talos_local_devices_phoning_home` | Size of the quadrant that matters, with the device names as an attribute |
| `sensor.talos_high_severity_findings` | Failed checks at high severity, with the full counts by severity |
| `sensor.talos_entities_that_stop_offline` | Entities lost when the uplink drops, broken down by vendor |
| `sensor.talos_offline_autonomy` | Percentage of entities that keep working |
| `sensor.talos_devices_talking_outside` | Devices with first-hand observed egress, plus unknown hosts |
| `sensor.talos_unverified_checks` | Checks that could not run, with the reason for each |
| `sensor.talos_correlation_coverage` | How much of the house the MAC/IP join could reach |
| `sensor.talos_database_size` | Size of the Talos database, disabled by default |
| `sensor.talos_last_scan` | Timestamp of the last completed scan |
| `binary_sensor.talos_blind_spot` | On when a host bypasses the resolver, or when the zero check could not run at all |

## Services

| Service | Description |
|---|---|
| `talos.export_report` | Writes the self-contained report of the last scan. `format` is `html` or `json`, `path` is relative to the configuration directory. Returns the path, the size and the finding counts |
| `talos.refresh` | Forces a fresh collection without waiting for the interval |

Example, export a report every Monday morning and notify when there is something at high severity:

```yaml
automation:
  - alias: Weekly Talos report
    triggers:
      - trigger: time
        at: "07:00:00"
    conditions:
      - condition: time
        weekday: [mon]
    actions:
      - action: talos.export_report
        data:
          format: html
        response_variable: report
      - if:
          - condition: template
            value_template: "{{ report.findings_high > 0 }}"
        then:
          - action: notify.mobile_app_iphone
            data:
              message: >
                Talos: {{ report.findings_high }} high severity findings,
                {{ report.unverified }} checks could not run.
```

## The panel is admin only

Talos registers a sidebar panel with `require_admin`, not a Lovelace card. A card ends up on a
dashboard, and a dashboard ends up on the kitchen tablet or on a guest account. This report lists
addresses, MACs and the topology of the house, so not being embeddable is deliberate.

The same reasoning applies to `talos.export_report`: the default target is `config/talos/`, not
`config/www/`, because that directory is served at `/local/` without authentication. Writing there is
allowed, but the service logs a warning when it happens.

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
HTML file is self-contained: no scripts, no external assets, it opens from an archive a year later on
a machine with no network.

Also available: `talos validate scan.json` and `talos report scan.json --html out.html`.

## Extending it without touching code

- **Domains**, `talos_core/data/domains.json`. That `*.tuya.com` is a vendor cloud is something a
  person knows, not something an algorithm derives. Your rules are layered on top of the shipped
  list, never replacing it.
- **Checks**, `talos_core/data/checks.json`. Severity and remediation are data. The selectors are a
  small declared vocabulary: a DSL rich enough to express arbitrary logic would be a programming
  language dressed up as a configuration file.

Point at your own file from the integration options, or with `--domains` and `--checks` on the CLI.

## Known limits

- **DNS over HTTPS.** A device that encrypts its own DNS queries on port 443 is indistinguishable
  from ordinary traffic. A structural gap this approach does not cover.
- **Home Assistant's exposure on the internet.** An instance cannot test its own reachability from
  outside. Marked unverifiable, not faked.
- **The ARP table.** Inside a container the ARP cache only holds peers Home Assistant spoke to
  recently, not the whole LAN. DHCP leases stay the better source.
- **The flow graph** groups by integration above ten origins and states what it is not drawing. It
  does not use a graph layout library.

## Translations

The integration UI is available in English and Italian, selectable from Settings, Language. English
is the source language and the fallback: a new string that has not been translated yet shows up in
English rather than breaking. The panel carries its own string table with the same two languages, and
a test fails if the two tables ever drift apart.

## Architecture

```
talos_core/                plain Python package, no dependencies, no homeassistant imports
├── model, validate        data model and validator with stable error codes
├── derive, checks         matrix, autonomy, exposure, posture check engine
├── sources/               declared side (WebSocket API and in-process registries)
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

Releases are produced with `scripts/release.sh <version> "<release notes>"`, which bumps the version
in `manifest.json`, `pyproject.toml` and `talos_core/__init__.py`, re-bundles the core into
`custom_components/talos/vendor/`, commits, tags, pushes and creates the GitHub release. A CI job
fails if the bundled copy ever drifts from the source at the root.

## Support the integration

You can support the development of this integration by giving a small donation here:
<a href='https://ko-fi.com/W7W21XGKFV' target='_blank'><img height='36' style='border:0px;height:36px;' src='https://storage.ko-fi.com/cdn/kofi2.png?v=6' border='0' alt='Buy Me a Coffee at ko-fi.com' /></a>

## License

MIT, see [LICENSE](LICENSE).
