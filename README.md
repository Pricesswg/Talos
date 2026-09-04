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

Two things get read off the entry itself. The first is **the address it connects to**, taken from the
`broker`, `host`, `server`, `hostname`, `address` or `url` key in its data, plus the port. That is the
only way to tell two brokers apart: with EMQX and Mosquitto both installed the domain says `mqtt` for
both, and only the entry says which one the devices actually arrive through. Nothing else in the entry
is read, because the same dictionary holds usernames, passwords and tokens, and none of them belong in
a document meant to be exported. Nothing is pinged either: this is what the entry declares, and it is
labelled `declared` like everything else in this step. The second is **the entry state**. An entry in
`setup_retry` is serving nothing right now, so its entities are counted as unavailable rather than as
local, and a check reports it. Working offline and not working at all are not the same result.

**2. Poll AdGuard Home.** The query log is a rolling buffer, not a queryable history, so Talos walks
it newest first with the `older_than` cursor and stops at the cursor left by the previous poll.
Running totals per client and domain live in a dedicated SQLite file under `config/talos/`, never in
the recorder database, because AdGuard's retention rolls over and a device that resolved a domain
four thousand times last week would otherwise read as a handful today.

A radio is a conduit too. A Zigbee lamp exchanges data with its coordinator constantly and never
touches IP, so it owns no address, appears in no query log, and used to be absent from every view
built on conduits: the flows graph showed the part of the house that talks to the internet and left
out the part that does not, which said the branch was not there rather than that it never leaves the
hub. Each device that hangs off another now carries a declared conduit to it, with the transport as
the protocol, ending at a `local_hub` destination. It stops there: what the hub does next is the
hub's own conduit, and the parent of a mesh node is still never claimed.

**3. Join the two.** The device registry knows MACs. The query log knows IPs. Something has to hold
both, and there are two candidates. The DHCP leases are the usual one. The other is already inside
Home Assistant: a router-based device tracker, AsusWRT, UniFi, Fritz, OPNsense, publishes an `ip` and
a `mac` attribute for every host it sees, and Talos reads those from the entity states. Only those two
attributes are read, and only when both are present and the address parses as an IP, because a
hostname would join with nothing while looking like a correlation that worked. A lease wins over a
tracker when both know a MAC, and `correlation.method` names the sources that actually carried the
join, `mac_dhcp`, `mac_tracker`, `mac_dhcp_tracker`, or `none`. It matters because an install whose
router does the DHCP has no leases to read, and used to correlate exactly nothing. Anything the join
cannot attribute becomes an `unknown_host` conduit instead of being dropped.

**4. Classify and attribute.** Domains are resolved against `talos_core/data/domains.json`: vendor
cloud, telemetry, push service, CDN, NTP, updates, local broker, NAT traversal. A rule matches on the
suffix, which names an operator, or on the leftmost label, which names a function: `tuyaeu.com` is
Tuya whoever runs the host, and anything called `stun.something` is a STUN server whoever runs it,
which is not a list that can be enumerated. Suffix rules win, so an explicit host always beats a rule
about what it is called. Unclassified domains stay counted and listed, with the caveat that most of a
home resolver's log is phones and computers browsing: what matters is a domain reached by a device in
the registry.

NAT traversal is its own kind because it answers the question this tool exists for. Nobody browses to
a STUN server: it is what a device asks for when it wants a path back into the house that does not go
through the router's rules, which is how a vendor app reaches a camera from anywhere, port forwarding
or not.

The transport of a device is read from the best evidence available, in order: a connection type
stated by the integration, then an identifier prefix, then the radio its hub was found to speak,
then the integration domain. The identifier step matters because a bus is not a radio: Zigbee2MQTT
devices arrive through the MQTT integration, so the config entry says `mqtt` and only the device
identifier says Zigbee. Anything still unresolved stays `unknown` and visible rather than being
folded into a plausible default. A device Home Assistant itself marks as an `entry_type` of service,
a Supervisor add-on or a HACS repository, is `virtual`: it is a registry entry, not something attached
to a network, and calling it undetermined said the wrong thing about hundreds of rows. Zigbee and
Z-Wave nodes carry no IP and therefore cannot have direct egress, so when
their hub is observed contacting a vendor the children get an `inherited` conduit pointing at that
hub, rather than a fabricated direct one. Nine Hue bulbs behind one talkative bridge are one thing to
fix, not ten.

**5. Derive and check.** From the joined scan Talos builds the matrix, the autonomy figures and the
exposure figures, then runs the posture checks from `talos_core/data/checks.json`. Output goes to the
panel, to the summary entities, and to the HTML or JSON export.

In the panel every check is a line you can open: the summary says what was found and how serious it
is, and the body names the assets involved with the evidence that made each one a subject, so a
finding about vendor traffic lists the devices and the domains they resolved. Checks that could not
run are kept apart from notes about where the collection itself does not reach, because only the
first kind belongs to the tally of declared checks and neither is an outcome.

The pipeline is a pure function of the collected data. The same input always produces the same
report.

### The colour code

Colour answers "what is at the other end", never "how bad is it". Outward, a link takes its
destination's kind: slate for infrastructure, time and updates and CDN; purple for the vendor, its
telemetry and its push service; rust for a tunnel or a STUN server; grey for a domain nobody has
named. Inward, a link takes its transport's own colour, the same one the map uses, so Zigbee is the
same green in both views. A solid line is declared, a dashed one was observed in the query log.

Red is spent on exactly one thing in the whole panel, and nothing else may take it: a device Home
Assistant drives locally that was observed reaching its vendor anyway. If a red line appears, it
means that and only that.

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
- An MQTT broker reached with no credentials, and clients on it that match nothing Talos knows
- Devices resolving a STUN, TURN or tunnel broker, which is a path back into the house from outside
- A Zigbee network left open to joining
- Camera entries that declare a cleartext RTSP stream
- Config entries that are not loaded, whose entities are unavailable right now rather than
  merely cloud-dependent
- Which entities stop working when the internet drops, and which vendor accounts for most of them
- Domains nobody has classified yet, counted and listed rather than hidden

It does not check, and will not:

- No CVE matching, no vulnerability database, no exploit attempts
- No port scanning and no active probing of any device
- No traffic inspection. DNS says **who** a device talked to, never what was said or how much. The
  report says "dependency detected" and never "data exfiltration"
- Nothing is modified. Every source is read-only

The Zigbee network is read from Zigbee2MQTT's retained `bridge/devices` and `bridge/info` topics, on
whatever base topic it publishes under. That gives the part each node plays, coordinator, router or
end device, which is the shape of the mesh, plus the channel and whether the network is currently
open to joining. The parent of a node is deliberately not claimed: the topic that would give it is
`bridge/request/networkmap`, and requesting one interrogates every device on the mesh, which is a
probe. A role is joined onto the registry by IEEE address, and a node the coordinator did not name
keeps `unknown`.

**Cleartext streams** are read the same way, from the config entry rather than from the wire. A camera
entry that names an `rtsp://` stream is declaring that its video and its credentials cross the network
in the clear; `rtsps://` says the opposite. Only the scheme, the host and the port are taken: a stream
URL is the one field in a config entry that reliably carries a password, so the URL itself, the path
and anything before the `@` never reach the document. Where nothing on the install carries video the check passes: there is no stream to be in the clear.
Whether something carries video is decided by domain, against a table of camera and NVR integrations,
and not by the streaming role, which also covers audio: Sonos, Spotify or a DLNA renderer have no RTSP
stream to be in the clear, and naming them as uninspectable for one would be wrong. A video
integration that negotiates its stream URL at connection time, ONVIF and Reolink among them, declares
nothing to read. There the check is **verified in part**: it ran on what declared a stream and found
none in the clear, and it names the integrations it could not inspect. That is a fourth outcome, and
it has its own colour, blue, because green would claim everything was seen and grey would claim
nothing was looked at, and neither is what happened. A partial result is counted on its own, never
among the passes.

Two checks that used to sit in the rule file are gone. Z-Wave S2 needed the security class, which
lives only inside another integration's driver object, so the check would have broken on somebody
else's refactor rather than on a change to this repository. ARP was already answered better by the
DHCP leases and the query log, which name the hosts on the network that Home Assistant does not know
about without reading a cache that, inside a container, holds only the peers Home Assistant spoke to
recently.

The two MQTT checks are implemented, and neither of them probes the broker. **Anonymous access** is
read off the config entry: if Home Assistant reaches the broker carrying no credential at all, then
the broker accepts anonymous connections, and that is the broker's own answer already on record.
Whether a credential exists is the only thing read, never its value. **Unknown clients** come from a
read-only subscription to `$SYS`. By default that runs on the session the MQTT integration already
holds, so there is no second connection and no credentials of Talos's own. The catch is that most
brokers reserve the `$SYS` tree for an account that holds the right to read it, and the MQTT
integration's user has no reason to be one, so on a locked-down broker that path returns nothing.

For those, Talos takes its own read-only account: broker, port, user, password and a TLS flag. Set it
either in the panel under Settings, or in the config flow through Settings, Devices and services,
Talos, Reconfigure. Both write the same config entry, both go over the same authenticated admin
socket, and the stored password is never sent back: the panel is told only whether one is set, and
leaving the password box empty keeps the stored one rather than clearing it. Leave the address empty
and it uses the broker the MQTT config entry already names, so the usual case is two fields.

The address is normalised on the way in: what somebody reads off the EMQX dashboard and types is
`192.168.50.92:18083`, which without a scheme parses to no host at all and fails in a way that says
nothing about the cause, so the scheme is filled in and a pasted `/api/v5` tail is dropped.

Every route that was filled in is tested, and the form is stored either way. A route that does not
answer is a configuration with a problem, not an invalid form: refusing to save threw away what had
just been typed, so a key that needed a permission fixed on the broker could not be kept while the
user went and fixed it. Both results come back, so filling in both says something about both.

The connection is tested before it is stored, and the three outcomes are distinct. Reached with
`$SYS` readable is a working account. Reached but `$SYS` silent is also saved, because that is a
valid account with a limit, and the panel says so instead of pretending the check will now run.
Refused is not saved, and the broker's own words are shown. Talos publishes nothing and subscribes to
`$SYS` and nothing else, under the fixed client id `talos-scanner` so its own connection is
recognisable in the list it reads.

**On EMQX 5 the subscription cannot work at all**, whatever the ACL says: EMQX 5 removed the
per-client `$SYS` topics that EMQX 4 published and left only gauges there, so the tree answers with
numbers and never a name. For that broker Talos reads `/api/v5/clients` over HTTP instead, with an
API key created under System, API Key in its dashboard. Read-only permissions are enough, there is no
subscription and no session on the broker, and the answer carries the address each client connected
from. That address is worth more than the subscription ever was: a client id is a name the client
chose for itself, an address joins against the devices in the scan, so a client that matches nothing
by name can still be attributed to the device it connected from.

Every configured route runs, and the clients are the union. The EMQX API and Talos's own account see
different things, the API the address each client connected from, the subscription what the broker
publishes, and one is not asked to stand in for the other: with both configured both are read, a
client is joined by id, its address comes from whichever route had one, and a client the name
matching could not place is tried again by that address against the devices in the scan. Home
Assistant's own session is the route of last resort, used only when nothing else is configured,
because it needs nothing and on most brokers answers with nothing. The panel shows each route's own
outcome, and a Test now button runs them all on demand and reports each one verbatim, so a key that
was rejected reads as exactly that even when the subscription made up for it. The same outcomes go
to the Home Assistant log at INFO, one line per route.

None of these credentials cause a reload. They are read again on every scan, so saving them updates
the entry and runs one scan, rather than tearing down the store, the coordinator and every entity the
way a change to the interval or the retention policy has to.

Client ids are matched against the names in the scan, and anything left over is reported as
unmatched, which is not the same as hostile. A client id is only ever a name the client gave itself,
so the panel shows the address it connected from beside it, and says whether the resolver has seen
that host doing anything else: an unattributed client on an address that has been resolving STUN
servers is a different thing from one that has never appeared anywhere.

The client list is shown whether the check passed, failed or could not run, because "which ones could
you not account for" has an answer in all three cases. When no client id arrives at all, by either
route, the check declares itself unable to run rather than passing on an empty list, and the panel
prints the broker's reason next to the empty list instead of leaving it looking like a clean result.

### Unverified is its own category

A check that could not run names the preconditions it lacked, as data and not only as prose: the
document carries `missing: ["dhcp_leases"]` next to the English sentence, and the panel turns each
name into what is missing and where to supply it, the settings page, the add-on to enable, the
tracker that would provide it. A reason of "missing data" that does not say which data is no reason,
and for a while that is what the panel showed, because it preferred the translated description of the
finding over the reason it did not run.

A check that could not run is not a pass. If AdGuard is unreachable the "local with egress" quadrant
comes out empty because nothing was observed, not because nothing is wrong, and reporting that as
green would be the exact failure this tool exists to avoid. Every check declares its preconditions,
and when one is not met the check moves to the unverified list with the reason spelled out. That
count sits next to the other two in the panel and cannot be hidden.

## Diagnostics, on demand

A different kind of evidence, and kept apart from the scan on purpose. The scan is passive and
periodic, and every row carries a proof that is declared or observed. A diagnostic run is something
you start from its own tab, it lasts the window you pick, thirty seconds to two minutes, and then it
stops: it is never scheduled, it feeds no posture check, and the last run is held in memory until the
next one rather than stored. Every row carries the time it was measured, because the moment is part
of the data.

Three measures, each attributable to a config entry:

- **State changes per integration.** The event bus is listened to for the window and every
  `state_changed` is attributed to its entry through the entity registry. Every change is a row in
  the recorder and a turn on the loop, so the integration producing hundreds a minute is the one
  filling the database and keeping the system busy, even when each single write is harmless.
  Changes that belong to no entry, YAML entities and helpers, are counted but not attributed, so the
  total adds up.
- **Calls that block the loop.** Home Assistant logs every call that blocked the event loop with the
  integration that made it. The tail of the log is read once, bounded to four megabytes, and the
  warnings are counted by integration. While the loop is blocked nothing else runs, which makes this
  the most direct signal of "this thing slows everything down". Nothing is executed to get it.
- **Reachability of declared endpoints.** One TCP connection, timed, to every host and port the
  config entries declare, a few at a time with a three second timeout. Only to what you configured,
  only on the port you wrote, never ICMP and never a sweep. That is the line between checking the
  broker answers and knocking on doors on the network, and this stays on the right side of it. An
  endpoint that names no port is skipped rather than guessed at.

- **Add-ons and system resources.** Where the Supervisor is there to ask, on Home Assistant OS or a
  Supervised install, every started add-on is asked for its CPU, memory and network, with Home
  Assistant Core listed alongside as the yardstick. CPU and memory are read at the end of the window.
  Network is a rate: the Supervisor hands out bytes as counters growing since the container started,
  and a counter says nothing about now, so a sample is taken at each end of the window and the
  difference is divided by the seconds. A counter that went backwards, which a restart does, yields
  no rate rather than a negative one. A stopped add-on is listed with no numbers, so the picture is
  complete rather than only its noisy part. The Supervisor token goes in the request header and
  nowhere else: it never reaches a result, a log line or the panel.

  Three pies show the shares. CPU and memory have a whole to be a share of, so each gets a remainder
  wedge for what nothing measured is using: idle CPU, and memory held by the host and by whatever is
  not a container. The Supervisor's CPU figure is relative to one core, so on four cores an add-on
  can report 250 and the wedges would not close; dividing by the core count the container sees makes
  it a share of the machine. Memory is taken against the container limit, which for an uncapped
  add-on is the host's RAM. Network has no whole, nobody knows what the link could carry, so that
  pie is the split among what was measured, and the label says so.

What could not be measured is listed under the results with the reason, in the same spirit as the
scan's unverified list: a section that is empty and a section that was not looked at are different
things. On a Container or Core install the add-on section is one such note. Two runs cannot overlap,
because they would measure each other.

### The map

The map is a force layout in the manner of Obsidian's graph view, drawn by the panel with no library.
The radial layout is the starting position; from there the nodes settle under springs and repulsion,
and once at rest they keep breathing, a whisper of seeded noise, so the picture stays alive without
ever being a different picture. Rest lengths shorten with depth: a device sits close to its hub or
integration, an integration close to its transport, a transport further from the centre. Each
integration becomes a tight tuft with a halo of devices, and the trunks stay long, which is the shape
the screenshot of Obsidian has and the shape a house has.

Determinism is kept as far as a simulation allows. The seed is the same radial picture every time,
the noise comes from a generator with a fixed seed, and the settle runs a fixed number of steps, so
the same house gives the same shape, only moving. Repulsion is found through a uniform grid the size
of its reach, so a tick on six hundred nodes costs a fraction of a frame rather than a frame. The loop
pauses while the tab is hidden and while a node is being dragged, and under `prefers-reduced-motion`
it settles and stops.

A node carries its name and nothing else; a second line under every dot was what made the picture
hard to read, and the names have a halo the colour of the surface so they stay legible across an
edge. The transports, the publishing systems and the integrations with five or more devices are always
named: they are the tufts, they are few, and they are what orients you. An integration with a device
or two, which on a large install is most of them, is named the way a device is. A device's name shows only when it can be read, the way
Obsidian reveals them: the nearest dozen to the pointer, the focused node and its neighbours, and
whatever the search matched. Four hundred names at once are a wall whatever the halo does for each,
and that wall was the complaint. Everything else is a click away: the popup shows the device's transport, integration, origin,
mesh role, area, address, model and entity count, or the integration's domain, class, role, state and
declared endpoint, plus the conduits it is the source of. Clicking also lights the path the data
takes: the node and its neighbours stay, the rest fades, and the edges touching it carry a running
dash from the leaf towards the hub, which is the direction the data goes. Escape or a click on empty
space clears it. Dragging a node pins it to the pointer and lets the rest settle around it; letting
go frees it.

### History, and how the store is sized

Every scan leaves one compact row behind: findings by severity, passed, partial and could-not-run,
local and cloud entities, exposed devices, unclassified domains, correlation. The scan documents are
heavy and pruned early; these rows cost a few hundred bytes each and are kept for the whole retention
window, and they are what the charts at the bottom of the overview draw. A picture says where you
are; the rows say whether it is getting better.

The store is sized from one answer: for how long to keep the data. The three knobs it enforces, the
age of an observation, the ceiling on rows and the number of scan documents, are derived from the
days and from the rate the install actually produces, which the store already knows from how many
observations it holds and how old the oldest is. A ceiling that is not derived from the rate is
either so high it bounds nothing or so low it cuts the window short without saying so. The derived
numbers and a size estimate are shown in Settings, labelled as measured or assumed, and the three
knobs can still be set by hand with auto sizing off.

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

An integration is not always the source. An MQTT entry can be fed by Zigbee2MQTT and a SwitchBot
bridge at the same time, so when the devices under an integration come from different systems those
sources get their own ring between the integration and its devices, read from the device identifiers.

Integrations also carry a role, which is not a transport. An **aggregator** is a bus or coordinator
that carries other systems: MQTT is the clearest case, and any entry whose devices name more than one
origin is marked one by evidence, whatever its domain. **Streaming** is a service carrying continuous
media: an ONVIF camera sits on Wi-Fi like a plug does, but what crosses the wire is not comparable.
Both get a filter chip of their own next to the transports.

Links that cross an integration boundary are drawn as dashed arcs across the tree. Two things
produce them: `via_device` pointing at a device owned by another entry, such as a Bluetooth proxy
owned by ESPHome serving MQTT devices, and a device whose origin names a system that is itself a
configured integration, such as SwitchBot devices published on MQTT while the SwitchBot integration
is also set up.

Three ways to narrow it down. A chip per transport keeps only that trunk. Clicking an integration
isolates it, showing its devices and nothing else. The search box filters devices by name or area
rather than dimming them, so what is left on screen is the answer. Any of them clears from the badge
in the toolbar.

The graph builds outwards one ring at a time rather than appearing at once, which makes the structure
readable while it settles. The reveal is skipped when the browser asks for reduced motion, and while
dragging.

Every section heading in every view folds its own section away when clicked, and the choice is
remembered per browser.

Nodes can be dragged, and the rest settle around them: after each layout a fixed number of
relaxation passes push overlapping nodes apart and slide them back onto their ring, so a crowded
branch spreads out instead of piling up. Wheel zooms, drag pans. Below the graph, the hubs and the
devices behind them, then the full list by transport.

It reads the registry only, so it populates even with no AdGuard configured.

**Advanced** answers who talks to whom and on what evidence: the matrix, the flow graph, the full
conduit table with its evidence labels, the check results with their subjects, and the unverified
list with each reason.

The flow graph shows both sides. Observed egress is drawn dashed, and the arcs that bypass Home
Assistant entirely are the point of the picture. Declared dependencies are drawn solid: a manifest
that says `cloud_push` states that the integration needs an external service without saying which
host, so the destination is named after whoever needs it and labelled **host not declared**. Nothing
is invented, and the graph has content before AdGuard is connected.

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

The integration UI is available in English, Italian, French, German, Spanish, Dutch, Polish and
Portuguese. English is the source language and the fallback: a new string that has not been translated
yet shows up in English rather than breaking.

The config flow and the entity names follow the Home Assistant language through the usual
`translations/<lang>.json` files. The panel has its own tables, one per language, in
`www/i18n/<lang>.json`: it fetches English at start and the active language next to it, and nothing
else, so a browser never downloads seven tables to read one. The language follows Home Assistant and can
be overridden from Settings, Language, for that browser only. The check copy in `checks.json` stays the
canonical English text; every table carries its translation, and a test fails if any table drifts from
the English keys, drops a placeholder, or ships a language the panel does not offer.

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
