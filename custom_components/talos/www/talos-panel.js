/* Talos panel.
 *
 * A plain custom element on purpose: no build step, no bundled framework, one
 * file served straight from the integration. The design tokens follow the same
 * cascade as the rest of the family - a Home Assistant theme variable first,
 * our own value as the final fallback - so the panel follows whatever theme is
 * installed without knowing which one it is.
 *
 * Two views, split by question rather than by density. The basic one answers
 * "what stops working" and "who talks outside"; the advanced one answers "who
 * talks to whom, with what evidence". Colour is spent on the taxonomy, and red
 * means exactly one thing anywhere in this file: local to Home Assistant, yet
 * observed phoning home.
 */

/* ── strings ──────────────────────────────────────────────────────────────
 * Both languages carry the same keys; a test fails if they drift apart. The
 * wording is part of the product: it states facts and their evidence, and
 * never a verdict the data cannot support.
 */
const I18N = {
  it: {
    "app.subtitle": "ultima scansione {when}",
    "app.never": "mai",
    "app.loading": "Caricamento…",
    "app.refresh": "Ripeti la scansione",
    "mode.base": "Base",
    "mode.advanced": "Avanzata",

    "base.title": "Come sta messa la tua casa",
    "base.lead":
      "Due domande, tenute separate perché hanno rimedi diversi: cosa smette di funzionare se salta internet, e quali dispositivi parlano con server fuori casa.",
    "base.offline.label": "Se salta internet",
    "base.offline.unit": "/{total} entità",
    "base.offline.stops": "<strong>{n} entità</strong> si fermano.",
    "base.offline.none": "Nessuna entità dipende dal cloud.",
    "base.offline.unclassified": "{n} non classificate.",
    "base.exposure.label": "Parlano fuori casa",
    "base.exposure.unit": "/{total} dispositivi",
    "base.exposure.local":
      "<strong>{n}</strong> risultano locali a Home Assistant ma contattano comunque il produttore.",
    "base.exposure.none": "Nessun dispositivo locale risulta contattare il produttore.",
    "base.exposure.inherited": "{n} esposti tramite un hub.",
    "base.unverified.label": "Non ho potuto verificare",
    "base.unverified.unit": "controlli",
    "base.unverified.note":
      "Non sono passati, non sono falliti: non ho i dati per dirlo. <strong>Non contano come “tutto a posto”.</strong>",
    "base.findings": "Cosa guarderei per primo",
    "base.limits":
      "<b>Cosa questa pagina non sa dirti.</b> Talos guarda a chi i dispositivi chiedono gli indirizzi, non cosa mandano né quanto. Non apre il traffico, non prova password, non tocca niente. Un dispositivo che cifra anche le richieste DNS resta invisibile: è un limite della tecnica, non un controllo saltato.",

    "banner.declared":
      "<strong>Solo dati dichiarati.</strong> {reason}. Questa scansione contiene ciò che Home Assistant dichiara di sé: nessuna colonna “parlano fuori casa” è stata verificata, quindi le caselle vuote non significano assenza di traffico.",
    "banner.noAdguard": "AdGuard Home non è configurato",

    "find.contacted": " Contattati: <strong>{list}</strong>.",
    "find.queries": "{n} query",
    "find.severity": "severità {level}",
    "find.offline.title": "Senza internet si ferma {vendor}",
    "find.offline.body":
      "Si fermerebbero {list}. È il funzionamento normale di questi servizi.",
    "find.offline.entities": "{n} entità ({vendor})",
    "find.offline.do":
      "<b>Nessuna azione urgente.</b> Vale la pena saperlo se conti su qualcuna di queste entità per qualcosa di importante, tipo un allarme perdita d'acqua.",
    "find.clean.title": "Nessun rilievo di severità alta o media",
    "find.clean.body":
      "{passed} controlli superati. Ricorda che <strong>{unverified} non erano eseguibili</strong>: non contano come esito positivo.",

    "adv.title": "Provenienza e destinazione dei dati",
    "adv.lead":
      "Ogni riga è etichettata con la sua prova. {declared} viene dal registry di Home Assistant, {observed} dal query log, {inherited} dal comportamento di un hub padre.",
    "adv.matrix": "Matrice",
    "adv.matrix.head": "Classe HA / rete",
    "adv.matrix.silent": "Nessun egress osservato",
    "adv.matrix.egress": "Egress osservato",
    "adv.matrix.local": "Locale",
    "adv.matrix.cloud": "Cloud",
    "adv.matrix.unclassified": "Non classificati",
    "adv.matrix.unclassifiedSub": "iot_class assente",
    "adv.cell.localSilent": "Nessuna richiesta verso l'esterno osservata.",
    "adv.cell.localEgress": "Telefonano a casa alle spalle di HA.",
    "adv.cell.cloudSilent": "Dichiarati cloud ma silenziosi. Da indagare, non è un merito.",
    "adv.cell.cloudEgress": "Dipendenza dichiarata e confermata.",
    "adv.cell.unclassified":
      "Manifest non leggibile: non contati né fra i locali né fra i cloud.",
    "adv.correlation":
      "Correlati <strong class=\"mono\">{done}/{total}</strong> dispositivi ({pct}%, metodo <span class=\"mono\">{method}</span>). I non correlati potrebbero avere egress che non vedo: la casella in alto a destra è un <em>minimo</em>, non un totale.",
    "adv.correlation.infra":
      " {n} dispositivi hanno contattato solo orologio o aggiornamenti: restano nella colonna silenziosa.",
    "adv.correlation.inherited":
      " {n} dispositivi risultano esposti tramite un hub e sono tenuti fuori dai quadranti.",
    "adv.flows": "Flussi",
    "adv.checks": "Controlli",
    "adv.checks.none": "Nessun rilievo.",
    "adv.checks.passed": "superato",
    "adv.conduits": "Condotti",
    "adv.conduits.none": "Nessun condotto in questa scansione.",
    "adv.unverified": "Non verificato",
    "adv.unverified.none": "Tutti i controlli erano eseguibili.",

    "col.devices": "Dispositivi",
    "col.integrations": "Integrazioni",
    "col.transport": "Trasporto",
    "col.integration": "Integrazione",
    "col.destination": "Destinazione",
    "graph.grouped": "raggruppati per integrazione: {n} dispositivi",
    "graph.hidden": "+{n} dispositivi senza condotti non disegnati",
    "graph.devices": "{n} dispositivi",

    "legend.local": "locale",
    "legend.infra": "infrastruttura",
    "legend.vendor": "cloud produttore",
    "legend.key": "locale con egress",

    "table.origin": "Origine",
    "table.destination": "Destinazione",
    "table.kind": "Tipo",
    "table.evidence": "Prova",
    "table.queries": "Query",
    "table.filter": "Filtro",
    "table.noDevice": "nessun device",
    "table.unknownHost": "Host non identificato",
    "table.core": "core",

    "severity.high": "alta",
    "severity.medium": "media",
    "severity.low": "bassa",
    "evidence.declared": "dichiarata",
    "evidence.observed": "osservata",
    "evidence.inherited": "ereditata",
    "reason.not_executable": "non eseguibile",
    "reason.missing_data": "dati mancanti",
    "reason.method_limit": "limite di metodo",
    "kind.vendor_cloud": "cloud produttore",
    "kind.telemetry": "telemetria",
    "kind.push_service": "servizio push",
    "kind.ota_update": "aggiornamenti",
    "kind.ntp": "orologio",
    "kind.cdn": "CDN",
    "kind.local_broker": "broker locale",
    "kind.ha_core": "Home Assistant",
    "kind.unknown": "non classificato",
  },

  en: {
    "app.subtitle": "last scan {when}",
    "app.never": "never",
    "app.loading": "Loading…",
    "app.refresh": "Run the scan again",
    "mode.base": "Basic",
    "mode.advanced": "Advanced",

    "base.title": "How your house is doing",
    "base.lead":
      "Two questions, kept apart because they have different fixes: what stops working when the internet drops, and which devices talk to servers outside the house.",
    "base.offline.label": "If the internet drops",
    "base.offline.unit": "/{total} entities",
    "base.offline.stops": "<strong>{n} entities</strong> stop.",
    "base.offline.none": "Nothing depends on the cloud.",
    "base.offline.unclassified": "{n} unclassified.",
    "base.exposure.label": "Talking outside",
    "base.exposure.unit": "/{total} devices",
    "base.exposure.local":
      "<strong>{n}</strong> are local to Home Assistant yet still contact the vendor.",
    "base.exposure.none": "No local device is contacting its vendor.",
    "base.exposure.inherited": "{n} exposed through a hub.",
    "base.unverified.label": "I could not verify",
    "base.unverified.unit": "checks",
    "base.unverified.note":
      "Not passed, not failed: I do not have the data to say. <strong>They do not count as “all clear”.</strong>",
    "base.findings": "What I would look at first",
    "base.limits":
      "<b>What this page cannot tell you.</b> Talos watches which addresses devices ask for, not what they send, nor how much. It opens no traffic, tries no passwords, changes nothing. A device that encrypts its DNS queries too stays invisible: that is a limit of the method, not a check that was skipped.",

    "banner.declared":
      "<strong>Declared data only.</strong> {reason}. This scan holds what Home Assistant declares about itself: no “talking outside” column has been verified, so an empty cell does not mean an absence of traffic.",
    "banner.noAdguard": "AdGuard Home is not configured",

    "find.contacted": " Contacted: <strong>{list}</strong>.",
    "find.queries": "{n} queries",
    "find.severity": "{level} severity",
    "find.offline.title": "Without internet you lose {vendor}",
    "find.offline.body": "You would lose {list}. This is how these services normally work.",
    "find.offline.entities": "{n} entities ({vendor})",
    "find.offline.do":
      "<b>Nothing urgent.</b> Worth knowing if you rely on any of these for something that matters, like a water leak alarm.",
    "find.clean.title": "No high or medium severity findings",
    "find.clean.body":
      "{passed} checks passed. Remember that <strong>{unverified} could not run</strong>: they do not count as a pass.",

    "adv.title": "Where the data comes from and where it goes",
    "adv.lead":
      "Every row is labelled with its evidence. {declared} comes from the Home Assistant registry, {observed} from the query log, {inherited} from a parent hub's behaviour.",
    "adv.matrix": "Matrix",
    "adv.matrix.head": "HA class / network",
    "adv.matrix.silent": "No egress observed",
    "adv.matrix.egress": "Egress observed",
    "adv.matrix.local": "Local",
    "adv.matrix.cloud": "Cloud",
    "adv.matrix.unclassified": "Unclassified",
    "adv.matrix.unclassifiedSub": "no iot_class",
    "adv.cell.localSilent": "No outbound lookup observed.",
    "adv.cell.localEgress": "Phoning home behind Home Assistant's back.",
    "adv.cell.cloudSilent": "Declared cloud but silent. Worth investigating, not a merit.",
    "adv.cell.cloudEgress": "Declared dependency, confirmed.",
    "adv.cell.unclassified": "Manifest unreadable: counted neither as local nor as cloud.",
    "adv.correlation":
      "Correlated <strong class=\"mono\">{done}/{total}</strong> devices ({pct}%, method <span class=\"mono\">{method}</span>). The uncorrelated ones may have egress I cannot see: the top-right cell is a <em>minimum</em>, not a total.",
    "adv.correlation.infra":
      " {n} devices only reached a clock or an update server: they stay in the silent column.",
    "adv.correlation.inherited":
      " {n} devices are exposed through a hub and are kept out of the quadrants.",
    "adv.flows": "Flows",
    "adv.checks": "Checks",
    "adv.checks.none": "No findings.",
    "adv.checks.passed": "passed",
    "adv.conduits": "Conduits",
    "adv.conduits.none": "No conduit in this scan.",
    "adv.unverified": "Unverified",
    "adv.unverified.none": "Every check was runnable.",

    "col.devices": "Devices",
    "col.integrations": "Integrations",
    "col.transport": "Transport",
    "col.integration": "Integration",
    "col.destination": "Destination",
    "graph.grouped": "grouped by integration: {n} devices",
    "graph.hidden": "+{n} devices with no conduit not drawn",
    "graph.devices": "{n} devices",

    "legend.local": "local",
    "legend.infra": "infrastructure",
    "legend.vendor": "vendor cloud",
    "legend.key": "local with egress",

    "table.origin": "Origin",
    "table.destination": "Destination",
    "table.kind": "Kind",
    "table.evidence": "Evidence",
    "table.queries": "Queries",
    "table.filter": "Filter",
    "table.noDevice": "no device",
    "table.unknownHost": "Unidentified host",
    "table.core": "core",

    "severity.high": "high",
    "severity.medium": "medium",
    "severity.low": "low",
    "evidence.declared": "declared",
    "evidence.observed": "observed",
    "evidence.inherited": "inherited",
    "reason.not_executable": "not runnable",
    "reason.missing_data": "missing data",
    "reason.method_limit": "method limit",
    "kind.vendor_cloud": "vendor cloud",
    "kind.telemetry": "telemetry",
    "kind.push_service": "push service",
    "kind.ota_update": "updates",
    "kind.ntp": "clock",
    "kind.cdn": "CDN",
    "kind.local_broker": "local broker",
    "kind.ha_core": "Home Assistant",
    "kind.unknown": "unclassified",
  },
};

const FALLBACK_LANG = "en";

const STYLES = `
:host {
  --font-sans: "IBM Plex Sans", var(--paper-font-body1_-_font-family, system-ui), sans-serif;
  --font-mono: "IBM Plex Mono", ui-monospace, Menlo, monospace;

  --bg: var(--primary-background-color, #f4f6f6);
  --surface: var(--ha-card-background, var(--card-background-color, #ffffff));
  --sunken: var(--secondary-background-color, #e9ecec);
  --border: var(--divider-color, #dbe0e1);
  --ink: var(--primary-text-color, #172022);
  --ink-soft: var(--secondary-text-color, #5b696c);
  --ink-mute: var(--disabled-text-color, #8b9698);

  --accent: #16697f;
  --accent-soft: color-mix(in srgb, #16697f 12%, transparent);
  --accent-ink: #0f4a5b;

  --k-local: #2f7d6a;
  --k-infra: #64768c;
  --k-vendor: #8a4a86;
  --k-unknown: #868d8e;

  --alert: #b3261e;
  --alert-soft: color-mix(in srgb, #b3261e 10%, transparent);
  --attention: #8a6516;

  --r-sm: 6px; --r-md: 10px; --r-lg: 14px; --r-pill: 999px;

  display: block;
  height: 100%;
  overflow: auto;
  background: var(--bg);
  color: var(--ink);
  font-family: var(--font-sans);
  font-size: 14px;
  line-height: 1.5;
}
@media (prefers-color-scheme: dark) {
  :host {
    --accent: #52b2c8; --accent-ink: #9ad6e5;
    --k-local: #52b195; --k-infra: #93a5bd; --k-vendor: #c07dbb; --k-unknown: #8d9799;
    --alert: #ff6f60; --attention: #d5a343;
  }
}
* { box-sizing: border-box; }
button { font: inherit; color: inherit; background: none; border: none; cursor: pointer; padding: 0; }
:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; border-radius: var(--r-sm); }
.mono { font-family: var(--font-mono); font-variant-numeric: tabular-nums; }

.bar {
  display: flex; align-items: center; gap: 16px; flex-wrap: wrap;
  padding: 14px 24px; background: var(--surface);
  border-bottom: 1px solid var(--border); position: sticky; top: 0; z-index: 5;
}
.bar h1 { margin: 0; font-size: 16px; font-weight: 600; letter-spacing: -.01em; }
.bar .sub { font-size: 12px; color: var(--ink-mute); }
.spacer { flex: 1; }
.seg { display: inline-flex; gap: 3px; padding: 3px; background: var(--sunken); border-radius: var(--r-pill); }
.seg button { padding: 6px 16px; border-radius: var(--r-pill); font-size: 13px; color: var(--ink-soft); }
.seg button[aria-pressed="true"] { background: var(--surface); color: var(--ink); font-weight: 500; }
.icon-btn { padding: 8px; border-radius: var(--r-md); color: var(--ink-soft); }
.icon-btn:hover { background: var(--sunken); color: var(--ink); }

.wrap { padding: 22px 24px 60px; max-width: 1180px; }
.stack { display: flex; flex-direction: column; gap: 24px; }
h2.sec {
  font-size: 12px; letter-spacing: .1em; text-transform: uppercase;
  color: var(--ink-mute); font-weight: 500; margin: 0 0 12px;
  display: flex; align-items: center; gap: 10px;
}
h2.sec::after { content: ""; flex: 1; height: 1px; background: var(--border); }
h1.page { font-size: 21px; font-weight: 600; letter-spacing: -.02em; margin: 0 0 4px; }
p.page-sub { margin: 0; color: var(--ink-soft); max-width: 62ch; }

.stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 14px; }
.stat {
  background: var(--surface); border: 1px solid var(--border);
  border-radius: var(--r-lg); padding: 18px;
  display: flex; flex-direction: column; gap: 10px;
}
.stat__label { font-size: 11px; letter-spacing: .08em; text-transform: uppercase; color: var(--ink-mute); }
.stat__value { font-family: var(--font-mono); font-size: 30px; line-height: 1; }
.stat__value small { font-size: 15px; color: var(--ink-mute); margin-left: 4px; }
.stat__note { font-size: 12.5px; color: var(--ink-soft); }
.meter { height: 5px; border-radius: var(--r-pill); background: var(--sunken); overflow: hidden; display: flex; }
.meter span { display: block; height: 100%; }

.find {
  background: var(--surface); border: 1px solid var(--border);
  border-radius: var(--r-lg); padding: 16px 18px; margin-bottom: 10px;
  border-left: 3px solid var(--border);
}
.find[data-tone="alert"] { border-left-color: var(--alert); }
.find[data-tone="attention"] { border-left-color: var(--attention); }
.find[data-tone="info"] { border-left-color: var(--accent); }
.find__title { font-weight: 600; font-size: 14.5px; margin: 0 0 6px; }
.find__body { color: var(--ink-soft); font-size: 13.5px; max-width: 70ch; }
.find__body strong { color: var(--ink); font-weight: 500; }
.find__do { margin-top: 10px; padding: 9px 12px; background: var(--sunken); border-radius: var(--r-md); font-size: 13px; color: var(--ink-soft); }
.limits { border: 1px dashed var(--border); border-radius: var(--r-lg); padding: 14px 18px; font-size: 12.5px; color: var(--ink-soft); max-width: 74ch; }
.limits b { color: var(--ink); font-weight: 500; }

table.matrix { border-collapse: collapse; width: 100%; }
table.matrix th, table.matrix td { border: 1px solid var(--border); padding: 0; }
table.matrix thead th, table.matrix tbody th {
  background: var(--sunken); font-size: 11px; letter-spacing: .07em; text-transform: uppercase;
  color: var(--ink-mute); font-weight: 500; padding: 10px 12px; text-align: left;
}
table.matrix tbody th { text-transform: none; font-size: 12.5px; letter-spacing: 0; color: var(--ink-soft); width: 170px; }
table.matrix tbody th span { display: block; font-family: var(--font-mono); font-size: 11px; color: var(--ink-mute); }
.cell { padding: 15px 14px; background: var(--surface); min-height: 92px; }
.cell__n { font-family: var(--font-mono); font-size: 25px; line-height: 1; }
.cell__t { font-size: 12.5px; color: var(--ink-soft); margin-top: 6px; }
.cell--key { background: var(--alert-soft); }
.cell--key .cell__n { color: var(--alert); }

.card { background: var(--surface); border: 1px solid var(--border); border-radius: var(--r-lg); }
.card__head { padding: 12px 16px; border-bottom: 1px solid var(--border); display: flex; gap: 14px; flex-wrap: wrap; align-items: center; }
.legend { display: flex; gap: 14px; flex-wrap: wrap; font-size: 11.5px; color: var(--ink-soft); }
.legend span { display: inline-flex; align-items: center; gap: 6px; }
.dot { width: 7px; height: 7px; border-radius: 50%; }
.scroll-x { overflow-x: auto; }

table.data { border-collapse: collapse; width: 100%; min-width: 760px; font-size: 13px; }
table.data th {
  text-align: left; font-size: 10.5px; letter-spacing: .08em; text-transform: uppercase;
  color: var(--ink-mute); font-weight: 500; padding: 10px 14px;
  border-bottom: 1px solid var(--border); background: var(--sunken); white-space: nowrap;
}
table.data td { padding: 10px 14px; border-bottom: 1px solid var(--border); vertical-align: top; }
table.data tr.is-key td { background: var(--alert-soft); }
.num { text-align: right; font-family: var(--font-mono); font-variant-numeric: tabular-nums; }
.sub { display: block; font-size: 11px; color: var(--ink-mute); }
.ev {
  font-family: var(--font-mono); font-size: 10.5px; padding: 2px 7px;
  border-radius: var(--r-sm); border: 1px solid var(--border); color: var(--ink-soft);
  white-space: nowrap; display: inline-block; margin-right: 4px;
}
.ev--observed { border-style: dashed; color: var(--accent-ink); border-color: var(--accent); }
.ev--inherited { border-style: dotted; }
.chip {
  display: inline-flex; align-items: center; gap: 6px; padding: 2px 9px;
  border-radius: var(--r-pill); font-size: 11.5px; border: 1px solid var(--border);
  color: var(--ink-soft); white-space: nowrap;
}
.chip--vendor_cloud, .chip--telemetry, .chip--push_service { color: var(--k-vendor); }
.chip--ntp, .chip--ota_update, .chip--cdn { color: var(--k-infra); }
.chip--local_broker, .chip--ha_core { color: var(--k-local); }
.chip--unknown { color: var(--k-unknown); border-style: dashed; }

.check {
  display: flex; justify-content: space-between; gap: 14px; align-items: start;
  background: var(--surface); border: 1px solid var(--border);
  border-left: 3px solid var(--ink-mute);
  border-radius: var(--r-md); padding: 12px 14px; margin-bottom: 8px;
}
.check__t { font-size: 13.5px; font-weight: 500; }
.check__w { font-size: 12.5px; color: var(--ink-mute); margin-top: 4px; max-width: 74ch; }

.banner {
  border-radius: var(--r-lg); padding: 14px 18px; font-size: 13px;
  border: 1px solid var(--attention); color: var(--ink);
  background: color-mix(in srgb, var(--attention) 10%, transparent);
}
.empty { padding: 60px 24px; text-align: center; color: var(--ink-mute); }

svg.graph { display: block; min-width: 900px; }
svg.graph text { font-family: var(--font-sans); fill: var(--ink); }
svg.graph .col-title { font-size: 10px; letter-spacing: .11em; text-transform: uppercase; fill: var(--ink-mute); }
svg.graph .n-label { font-size: 11.5px; }
svg.graph .n-sub { font-size: 10px; fill: var(--ink-mute); font-family: var(--font-mono); }
svg.graph .band { fill: color-mix(in srgb, var(--ink) 5%, transparent); }
svg.graph .edge { fill: none; }
`;

const PHONE_HOME = new Set(["vendor_cloud", "telemetry", "push_service", "cdn", "unknown"]);
const SEVERITY_TONE = { high: "alert", medium: "attention", low: "info" };

/* Above this many devices carrying a conduit, the first column groups by
 * integration. A hand-laid SVG stays readable at a few dozen nodes and not at
 * a few hundred, and a truncated picture that hides the shape is worse than a
 * grouped one that shows it. */
const GROUP_THRESHOLD = 10;
const MAX_ROWS = 10;

const esc = (value) =>
  String(value == null ? "" : value).replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  })[c]);

class TalosPanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._mode = "base";
    this._data = null;
    this._status = null;
    this._error = null;
    this._loading = true;
    this._loaded = false;
    this._lang = FALLBACK_LANG;
  }

  set hass(hass) {
    this._hass = hass;
    const raw = (hass && ((hass.locale && hass.locale.language) || hass.language)) || "";
    const base = String(raw).toLowerCase().split("-")[0];
    this._lang = I18N[base] ? base : FALLBACK_LANG;
    if (!this._loaded) {
      this._loaded = true;
      this.load();
    }
  }

  connectedCallback() {
    this.render();
  }

  /* ── i18n ────────────────────────────────────────────────────────────── */

  t(key, vars) {
    const table = I18N[this._lang] || I18N[FALLBACK_LANG];
    let text = table[key];
    if (text === undefined) text = I18N[FALLBACK_LANG][key];
    if (text === undefined) return key;
    if (!vars) return text;
    return text.replace(/\{(\w+)\}/g, (match, name) =>
      Object.prototype.hasOwnProperty.call(vars, name) ? String(vars[name]) : match
    );
  }

  num(value) {
    if (value == null) return "-";
    return Number(value).toLocaleString(this._lang === "it" ? "it-IT" : "en-GB");
  }

  /* ── data ────────────────────────────────────────────────────────────── */

  async load() {
    this._loading = true;
    this.render();
    try {
      const [derived, status] = await Promise.all([
        this._hass.callWS({ type: "talos/derived" }),
        this._hass.callWS({ type: "talos/status" }),
      ]);
      this._data = derived;
      this._status = status;
      this._error = null;
    } catch (err) {
      this._error = err && err.message ? err.message : String(err);
    } finally {
      this._loading = false;
      this.render();
    }
  }

  async refresh() {
    try {
      await this._hass.callWS({ type: "talos/refresh" });
    } catch (err) {
      this._error = err && err.message ? err.message : String(err);
    }
    await this.load();
  }

  deviceName(id) {
    const device = this._data && this._data.labels.devices[id];
    return device ? device.name : id;
  }

  integrationName(id) {
    const integration = this._data && this._data.labels.integrations[id];
    return integration ? integration.title : id;
  }

  destination(id) {
    return (this._data && this._data.labels.destinations[id]) || { fqdn: id, kind: "unknown" };
  }

  /* ── render ──────────────────────────────────────────────────────────── */

  render() {
    const root = this.shadowRoot;
    if (!root.firstChild) {
      const style = document.createElement("style");
      style.textContent = STYLES;
      root.appendChild(style);
      root.appendChild(document.createElement("div"));
    }
    const host = root.lastChild;

    if (this._loading && !this._data) {
      host.innerHTML = `<div class="empty">${esc(this.t("app.loading"))}</div>`;
      return;
    }
    if (this._error && !this._data) {
      host.innerHTML = `<div class="empty">${esc(this._error)}</div>`;
      return;
    }

    host.innerHTML =
      this.toolbar() +
      `<div class="wrap">` +
      (this._mode === "base" ? this.viewBase() : this.viewAdvanced()) +
      `</div>`;

    host.querySelectorAll("[data-mode]").forEach((button) => {
      button.addEventListener("click", () => {
        this._mode = button.dataset.mode;
        this.render();
      });
    });
    const refresh = host.querySelector("[data-action='refresh']");
    if (refresh) refresh.addEventListener("click", () => this.refresh());

    const svg = host.querySelector("svg.graph");
    if (svg) this.drawGraph(svg);
  }

  toolbar() {
    const status = this._status || {};
    const when = status.generated_at
      ? new Date(status.generated_at).toLocaleString(this._lang === "it" ? "it-IT" : "en-GB")
      : this.t("app.never");
    return `
      <div class="bar">
        <div>
          <h1>Talos</h1>
          <div class="sub mono">${esc(this.t("app.subtitle", { when }))}</div>
        </div>
        <div class="spacer"></div>
        <div class="seg" role="group">
          <button data-mode="base" aria-pressed="${this._mode === "base"}">${esc(this.t("mode.base"))}</button>
          <button data-mode="advanced" aria-pressed="${this._mode === "advanced"}">${esc(this.t("mode.advanced"))}</button>
        </div>
        <button class="icon-btn" data-action="refresh" title="${esc(this.t("app.refresh"))}">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor"
               stroke-width="1.8" stroke-linecap="round"><path d="M20 11a8 8 0 1 0-2.3 5.7"/><path d="M20 5v6h-6"/></svg>
        </button>
      </div>`;
  }

  /* ── basic view ──────────────────────────────────────────────────────── */

  viewBase() {
    const d = this._data;
    const a = d.autonomy;
    const localPct = a.entities_total ? (a.entities_local / a.entities_total) * 100 : 0;
    const exposed = d.exposure.devices_direct.length;
    const total = d.exposure.devices_total;
    const unverified = ((d.checks || {}).unverified || []).length || d.unverified_count || 0;

    return `<div class="stack">
      <div>
        <h1 class="page">${esc(this.t("base.title"))}</h1>
        <p class="page-sub">${esc(this.t("base.lead"))}</p>
      </div>

      ${this.observedBanner()}

      <div class="stats">
        <div class="stat">
          <div class="stat__label">${esc(this.t("base.offline.label"))}</div>
          <div class="stat__value">${this.num(a.entities_local)}<small>${esc(
            this.t("base.offline.unit", { total: this.num(a.entities_total) })
          )}</small></div>
          <div class="meter">
            <span style="width:${localPct}%;background:var(--k-local)"></span>
            <span style="width:${100 - localPct}%;background:var(--k-vendor)"></span>
          </div>
          <div class="stat__note">${
            a.entities_cloud
              ? this.t("base.offline.stops", { n: this.num(a.entities_cloud) })
              : this.t("base.offline.none")
          } ${
            a.entities_unclassified
              ? this.t("base.offline.unclassified", { n: this.num(a.entities_unclassified) })
              : ""
          }</div>
        </div>

        <div class="stat">
          <div class="stat__label">${esc(this.t("base.exposure.label"))}</div>
          <div class="stat__value">${this.num(exposed)}<small>${esc(
            this.t("base.exposure.unit", { total: this.num(total) })
          )}</small></div>
          <div class="meter">
            <span style="width:${total ? (exposed / total) * 100 : 0}%;background:var(--k-vendor)"></span>
          </div>
          <div class="stat__note">${
            d.matrix.local_egress.length
              ? this.t("base.exposure.local", { n: d.matrix.local_egress.length })
              : this.t("base.exposure.none")
          } ${
            d.matrix.inherited.length
              ? this.t("base.exposure.inherited", { n: d.matrix.inherited.length })
              : ""
          }</div>
        </div>

        <div class="stat">
          <div class="stat__label">${esc(this.t("base.unverified.label"))}</div>
          <div class="stat__value">${this.num(unverified)}<small>${esc(this.t("base.unverified.unit"))}</small></div>
          <div class="meter"><span style="width:100%;background:repeating-linear-gradient(90deg,var(--ink-mute) 0 4px,transparent 4px 8px)"></span></div>
          <div class="stat__note">${this.t("base.unverified.note")}</div>
        </div>
      </div>

      <div>
        <h2 class="sec">${esc(this.t("base.findings"))}</h2>
        ${this.findings()}
      </div>

      <div class="limits">${this.t("base.limits")}</div>
    </div>`;
  }

  observedBanner() {
    if (!this._data || this._data.observed_available !== false) return "";
    const reason = this._data.observed_error || this.t("banner.noAdguard");
    return `<div class="banner">${this.t("banner.declared", { reason: esc(reason) })}</div>`;
  }

  subjectNames(result) {
    return result.subjects.map((id) => {
      if (result.subject_kind === "device") return this.deviceName(id);
      if (result.subject_kind === "integration") return this.integrationName(id);
      return id;
    });
  }

  /** Extra prose for the egress finding: who was contacted, how insistently. */
  egressDetail(result) {
    const byVendor = new Map();
    this._data.conduits.forEach((conduit) => {
      if (conduit.evidence !== "observed" || conduit.source.kind !== "device") return;
      if (!result.subjects.includes(conduit.source.id)) return;
      const destination = this.destination(conduit.destination_id);
      if (!PHONE_HOME.has(destination.kind)) return;
      const key = destination.vendor || destination.fqdn;
      byVendor.set(key, (byVendor.get(key) || 0) + (conduit.query_count || 0));
    });
    if (!byVendor.size) return "";
    const list = [...byVendor.entries()]
      .sort((a, b) => b[1] - a[1])
      .map(([vendor, queries]) => `${vendor} (${this.t("find.queries", { n: this.num(queries) })})`)
      .join(", ");
    return this.t("find.contacted", { list: esc(list) });
  }

  findingCard(result) {
    const names = this.subjectNames(result);
    const shown = names.slice(0, 6).join(", ");
    const more = names.length > 6 ? ` +${names.length - 6}` : "";
    const extra = result.id === "chk.local_with_egress" ? this.egressDetail(result) : "";
    const level = this.t(`severity.${result.severity}`);
    return `<div class="find" data-tone="${SEVERITY_TONE[result.severity] || "info"}">
      <div class="find__title">${esc(result.title)}
        <span class="chip">${esc(this.t("find.severity", { level }))}</span></div>
      <div class="find__body">${esc(result.detail)}${extra}
        ${names.length ? `<br><span class="mono">${esc(shown)}${more}</span>` : ""}</div>
      ${result.remediation ? `<div class="find__do">${esc(result.remediation)}</div>` : ""}
    </div>`;
  }

  findings() {
    const checks = this._data.checks || { failed: [], passed: [], unverified: [] };
    const cards = checks.failed
      .filter((result) => result.severity !== "low")
      .map((result) => this.findingCard(result));

    const losses = this._data.autonomy.losses.slice(0, 3);
    if (losses.length) {
      const list = losses
        .map((l) => this.t("find.offline.entities", { n: l.entities, vendor: l.vendor }))
        .join(", ");
      cards.push(`<div class="find" data-tone="attention">
        <div class="find__title">${esc(this.t("find.offline.title", { vendor: losses[0].vendor }))}</div>
        <div class="find__body">${esc(this.t("find.offline.body", { list }))}</div>
        <div class="find__do">${this.t("find.offline.do")}</div>
      </div>`);
    }

    if (!cards.length) {
      cards.push(`<div class="find" data-tone="info">
        <div class="find__title">${esc(this.t("find.clean.title"))}</div>
        <div class="find__body">${this.t("find.clean.body", {
          passed: this.num(checks.passed.length),
          unverified: this.num(checks.unverified.length),
        })}</div>
      </div>`);
    }
    return cards.join("");
  }

  /* ── advanced view ───────────────────────────────────────────────────── */

  viewAdvanced() {
    const d = this._data;
    const c = d.correlation;
    const pct = c.devices_total ? Math.round((c.devices_correlated / c.devices_total) * 100) : 0;
    const unverified = ((d.checks || {}).unverified || []);

    const lead = this.t("adv.lead", {
      declared: `<span class="ev">${esc(this.t("evidence.declared"))}</span>`,
      observed: `<span class="ev ev--observed">${esc(this.t("evidence.observed"))}</span>`,
      inherited: `<span class="ev ev--inherited">${esc(this.t("evidence.inherited"))}</span>`,
    });

    return `<div class="stack">
      <div>
        <h1 class="page">${esc(this.t("adv.title"))}</h1>
        <p class="page-sub">${lead}</p>
      </div>

      ${this.observedBanner()}

      <div>
        <h2 class="sec">${esc(this.t("adv.matrix"))}</h2>
        <table class="matrix">
          <thead><tr><th>${esc(this.t("adv.matrix.head"))}</th>
            <th>${esc(this.t("adv.matrix.silent"))}</th>
            <th>${esc(this.t("adv.matrix.egress"))}</th></tr></thead>
          <tbody>
            <tr>
              <th scope="row">${esc(this.t("adv.matrix.local"))} <span>local_push · local_polling</span></th>
              ${this.cell(d.matrix.local_silent, this.t("adv.cell.localSilent"))}
              ${this.cell(d.matrix.local_egress, this.t("adv.cell.localEgress"), true)}
            </tr>
            <tr>
              <th scope="row">${esc(this.t("adv.matrix.cloud"))} <span>cloud_push · cloud_polling</span></th>
              ${this.cell(d.matrix.cloud_silent, this.t("adv.cell.cloudSilent"))}
              ${this.cell(d.matrix.cloud_egress, this.t("adv.cell.cloudEgress"))}
            </tr>
            ${
              d.matrix.unclassified.length
                ? `<tr><th scope="row">${esc(this.t("adv.matrix.unclassified"))}
                     <span>${esc(this.t("adv.matrix.unclassifiedSub"))}</span></th>
                   ${this.cell(d.matrix.unclassified, this.t("adv.cell.unclassified"))}
                   <td></td></tr>`
                : ""
            }
          </tbody>
        </table>
        <p class="page-sub" style="margin-top:12px">
          ${this.t("adv.correlation", {
            done: c.devices_correlated, total: c.devices_total, pct, method: esc(c.method),
          })}
          ${d.matrix.infra_only.length ? this.t("adv.correlation.infra", { n: d.matrix.infra_only.length }) : ""}
          ${d.matrix.inherited.length ? this.t("adv.correlation.inherited", { n: d.matrix.inherited.length }) : ""}
        </p>
      </div>

      <div>
        <h2 class="sec">${esc(this.t("adv.flows"))}</h2>
        <div class="card">
          <div class="card__head">
            <div class="legend">
              <span><span class="dot" style="background:var(--k-local)"></span>${esc(this.t("legend.local"))}</span>
              <span><span class="dot" style="background:var(--k-infra)"></span>${esc(this.t("legend.infra"))}</span>
              <span><span class="dot" style="background:var(--k-vendor)"></span>${esc(this.t("legend.vendor"))}</span>
              <span><span class="dot" style="background:var(--alert)"></span>${esc(this.t("legend.key"))}</span>
            </div>
          </div>
          <div class="scroll-x"><svg class="graph" viewBox="0 0 980 560" role="img"
            aria-label="${esc(this.t("adv.flows"))}"></svg></div>
        </div>
      </div>

      <div>
        <h2 class="sec">${esc(this.t("adv.checks"))}</h2>
        ${this.checkList()}
      </div>

      <div>
        <h2 class="sec">${esc(this.t("adv.conduits"))} · ${d.conduits.length}</h2>
        <div class="card scroll-x">${this.conduitTable()}</div>
      </div>

      <div>
        <h2 class="sec">${esc(this.t("adv.unverified"))} · ${unverified.length}</h2>
        ${
          unverified
            .map(
              (check) => `<div class="check">
          <div>
            <div class="check__t">${esc(check.title)}</div>
            <div class="check__w">${esc(check.detail)}</div>
          </div>
          <span class="chip">${esc(this.t(`reason.${check.reason}`))}</span>
        </div>`
            )
            .join("") ||
          `<div class="check"><div class="check__t">${esc(this.t("adv.unverified.none"))}</div></div>`
        }
      </div>
    </div>`;
  }

  checkList() {
    const checks = this._data.checks || { failed: [], passed: [] };
    const failed = checks.failed
      .map((result) => {
        const names = this.subjectNames(result).slice(0, 8).join(", ");
        const colour =
          result.severity === "high" ? "alert" : result.severity === "medium" ? "attention" : "accent";
        return `<div class="check" style="border-left-color:var(--${colour})">
          <div>
            <div class="check__t">${esc(result.title)}</div>
            <div class="check__w">${esc(result.detail)}
              ${names ? `<br><span class="mono">${esc(names)}</span>` : ""}
              ${result.remediation ? `<br><em>${esc(result.remediation)}</em>` : ""}</div>
          </div>
          <span class="chip">${esc(this.t(`severity.${result.severity}`))} · ${result.subjects.length}</span>
        </div>`;
      })
      .join("");

    const passed = checks.passed
      .map(
        (result) => `<div class="check" style="border-left-color:var(--k-local)">
        <div><div class="check__t">${esc(result.title)}</div></div>
        <span class="chip">${esc(this.t("adv.checks.passed"))}</span>
      </div>`
      )
      .join("");

    return (
      (failed || `<div class="check"><div class="check__t">${esc(this.t("adv.checks.none"))}</div></div>`) +
      passed
    );
  }

  cell(ids, text, isKey) {
    const sample = ids.slice(0, 4).map((id) => this.deviceName(id)).join(", ");
    const more = ids.length > 4 ? ` +${ids.length - 4}` : "";
    return `<td><div class="cell${isKey && ids.length ? " cell--key" : ""}">
      <div class="cell__n">${ids.length}</div>
      <div class="cell__t">${esc(text)}${sample ? ` <span class="sub">${esc(sample)}${more}</span>` : ""}</div>
    </div></td>`;
  }

  conduitTable() {
    const d = this._data;
    const rows = d.conduits
      .slice()
      .sort((a, b) => (b.query_count || 0) - (a.query_count || 0))
      .map((conduit) => {
        const destination = this.destination(conduit.destination_id);
        const isKey =
          conduit.evidence === "observed" &&
          conduit.source.kind === "device" &&
          d.matrix.local_egress.includes(conduit.source.id) &&
          PHONE_HOME.has(destination.kind);

        let origin;
        if (conduit.source.kind === "device") {
          const device = d.labels.devices[conduit.source.id] || {};
          const integration = d.labels.integrations[device.integration_id] || {};
          origin = `${esc(device.name || conduit.source.id)}<span class="sub mono">${esc(
            [integration.iot_class, device.ip || device.transport].filter(Boolean).join(" · ")
          )}</span>`;
        } else if (conduit.source.kind === "integration") {
          const integration = d.labels.integrations[conduit.source.id] || {};
          origin = `${esc(integration.title || conduit.source.id)}<span class="sub mono">${esc(
            integration.domain || ""
          )} · ${esc(this.t("table.noDevice"))}</span>`;
        } else if (conduit.source.kind === "ha_core") {
          origin = `Home Assistant<span class="sub mono">${esc(this.t("table.core"))}</span>`;
        } else {
          origin = `${esc(this.t("table.unknownHost"))}<span class="sub mono">${esc(conduit.source.id)}</span>`;
        }

        return `<tr${isKey ? ' class="is-key"' : ""}>
          <td>${origin}</td>
          <td class="mono">${esc(destination.fqdn)}</td>
          <td><span class="chip chip--${esc(destination.kind)}"><span class="dot" style="background:currentColor"></span>${esc(
            this.t(`kind.${destination.kind}`)
          )}</span></td>
          <td><span class="ev ev--${esc(conduit.evidence)}">${esc(this.t(`evidence.${conduit.evidence}`))}</span></td>
          <td class="num">${conduit.query_count == null ? "-" : this.num(conduit.query_count)}</td>
          <td>${conduit.filter_status ? esc(conduit.filter_status) : "-"}</td>
        </tr>`;
      })
      .join("");

    return `<table class="data">
      <thead><tr><th>${esc(this.t("table.origin"))}</th><th>${esc(this.t("table.destination"))}</th>
      <th>${esc(this.t("table.kind"))}</th><th>${esc(this.t("table.evidence"))}</th>
      <th class="num">${esc(this.t("table.queries"))}</th><th>${esc(this.t("table.filter"))}</th></tr></thead>
      <tbody>${rows || `<tr><td colspan="6">${esc(this.t("adv.conduits.none"))}</td></tr>`}</tbody>
    </table>`;
  }

  /* ── graph ───────────────────────────────────────────────────────────── */

  /** Decide what the first column shows, and how the rest hangs off it. */
  graphModel() {
    const d = this._data;
    const devices = d.labels.devices || {};

    const withConduits = new Set();
    d.conduits.forEach((conduit) => {
      if (conduit.source.kind === "device" && conduit.source.id) withConduits.add(conduit.source.id);
    });

    const grouped = withConduits.size > GROUP_THRESHOLD;
    const originOf = (deviceId) =>
      grouped ? (devices[deviceId] || {}).integration_id || "?" : deviceId;

    // Origins ranked by how much traffic they account for, so the rows that
    // get drawn are the ones worth looking at.
    const weight = new Map();
    d.conduits.forEach((conduit) => {
      if (conduit.source.kind !== "device" || !conduit.source.id) return;
      const key = originOf(conduit.source.id);
      weight.set(key, (weight.get(key) || 0) + (conduit.query_count || 1));
    });
    const origins = [...weight.entries()]
      .sort((a, b) => b[1] - a[1])
      .slice(0, MAX_ROWS)
      .map(([id]) => id);

    const members = new Map();
    Object.keys(devices).forEach((deviceId) => {
      const key = originOf(deviceId);
      if (!members.has(key)) members.set(key, []);
      members.get(key).push(deviceId);
    });

    const destinations = [
      ...new Set(
        d.conduits
          .filter((conduit) => PHONE_HOME.has(this.destination(conduit.destination_id).kind))
          .map((conduit) => conduit.destination_id)
      ),
    ].slice(0, MAX_ROWS);

    const transports = [
      ...new Set(
        origins.flatMap((key) =>
          (members.get(key) || []).map((id) => (devices[id] || {}).transport || "unknown")
        )
      ),
    ].slice(0, 6);

    const integrations = grouped
      ? []
      : [...new Set(origins.map((id) => (devices[id] || {}).integration_id).filter(Boolean))].slice(0, MAX_ROWS);

    return { grouped, origins, members, originOf, destinations, transports, integrations, devices, withConduits };
  }

  drawGraph(svg) {
    const d = this._data;
    const model = this.graphModel();
    const NS = "http://www.w3.org/2000/svg";
    const el = (name, attrs) => {
      const node = document.createElementNS(NS, name);
      Object.entries(attrs || {}).forEach(([key, value]) => node.setAttribute(key, value));
      return node;
    };
    while (svg.firstChild) svg.removeChild(svg.firstChild);

    const columns = model.grouped
      ? [
          { key: "origin", x: 30, w: 210, title: this.t("col.integrations"), ids: model.origins },
          { key: "transport", x: 300, w: 130, title: this.t("col.transport"), ids: model.transports },
          { key: "destination", x: 700, w: 250, title: this.t("col.destination"), ids: model.destinations },
        ]
      : [
          { key: "origin", x: 30, w: 190, title: this.t("col.devices"), ids: model.origins },
          { key: "transport", x: 280, w: 120, title: this.t("col.transport"), ids: model.transports },
          { key: "integration", x: 460, w: 180, title: this.t("col.integration"), ids: model.integrations },
          { key: "destination", x: 700, w: 250, title: this.t("col.destination"), ids: model.destinations },
        ];

    const positions = {};
    const H = 560, TOP = 62, NH = 40;
    columns.forEach((column) => {
      const step = (H - TOP - 34) / Math.max(column.ids.length, 1);
      column.ids.forEach((id, index) => {
        positions[`${column.key}:${id}`] = {
          x: column.x, y: TOP + step * index + (step - NH) / 2, w: column.w, h: NH,
        };
      });
      svg.appendChild(
        el("rect", { class: "band", x: column.x - 12, y: 40, width: column.w + 24, height: H - 52, rx: 10 })
      );
      const title = el("text", { class: "col-title", x: column.x, y: 28 });
      title.textContent = column.title;
      svg.appendChild(title);
    });

    const edges = el("g", {});
    svg.appendChild(edges);

    const line = (from, to, colour, dash, width) => {
      if (!from || !to) return;
      const x1 = from.x + from.w, y1 = from.y + from.h / 2;
      const x2 = to.x, y2 = to.y + to.h / 2;
      const cx = (x2 - x1) * 0.55;
      const path = el("path", {
        class: "edge",
        d: `M${x1},${y1} C${x1 + cx},${y1} ${x2 - cx},${y2} ${x2},${y2}`,
        stroke: colour,
        "stroke-width": width || 1.2,
        "stroke-opacity": 0.75,
      });
      if (dash) path.setAttribute("stroke-dasharray", dash);
      edges.appendChild(path);
    };

    // origin -> transport (-> integration, when not grouped)
    model.origins.forEach((originId) => {
      (model.members.get(originId) || []).forEach((deviceId) => {
        const device = model.devices[deviceId] || {};
        const transport = device.transport || "unknown";
        line(positions[`origin:${originId}`], positions[`transport:${transport}`], "var(--ink-mute)");
        if (!model.grouped) {
          line(
            positions[`transport:${transport}`],
            positions[`integration:${device.integration_id}`],
            "var(--ink-mute)"
          );
        }
      });
    });

    // The bypass arc is the picture's thesis: the device reaches the vendor on
    // its own, with Home Assistant nowhere on the path.
    d.conduits.forEach((conduit) => {
      const destination = this.destination(conduit.destination_id);
      if (!PHONE_HOME.has(destination.kind)) return;
      const to = positions[`destination:${conduit.destination_id}`];
      if (!to) return;

      if (conduit.source.kind === "device") {
        const originId = model.originOf(conduit.source.id);
        const isKey = conduit.evidence === "observed" && d.matrix.local_egress.includes(conduit.source.id);
        line(
          positions[`origin:${originId}`],
          to,
          isKey ? "var(--alert)" : "var(--k-vendor)",
          conduit.evidence === "inherited" ? "1.5 4" : "6 4",
          isKey ? 2 : 1.4
        );
      } else if (conduit.source.kind === "integration" && !model.grouped) {
        line(positions[`integration:${conduit.source.id}`], to, "var(--ink-mute)", null, 1.2);
      }
    });

    columns.forEach((column) => {
      column.ids.forEach((id) => {
        const position = positions[`${column.key}:${id}`];
        let label = id;
        let sub = "";
        let colour = "var(--ink-mute)";

        if (column.key === "origin" && model.grouped) {
          const integration = d.labels.integrations[id] || {};
          const memberIds = model.members.get(id) || [];
          label = integration.domain || id;
          sub = this.t("graph.devices", { n: memberIds.length });
          colour = memberIds.some((deviceId) => d.matrix.local_egress.includes(deviceId))
            ? "var(--alert)"
            : "var(--k-local)";
        } else if (column.key === "origin") {
          const device = model.devices[id] || {};
          label = device.name || id;
          sub = device.ip || device.transport || "";
          colour = d.matrix.local_egress.includes(id) ? "var(--alert)" : "var(--k-local)";
        } else if (column.key === "integration") {
          const integration = d.labels.integrations[id] || {};
          label = integration.domain || id;
          sub = integration.iot_class || "";
          colour = (integration.iot_class || "").startsWith("cloud") ? "var(--k-vendor)" : "var(--k-local)";
        } else if (column.key === "destination") {
          const destination = this.destination(id);
          label = destination.fqdn;
          sub = this.t(`kind.${destination.kind}`);
          colour = destination.kind === "unknown" ? "var(--k-unknown)" : "var(--k-vendor)";
        }

        const group = el("g", {});
        group.appendChild(
          el("rect", {
            x: position.x, y: position.y, width: position.w, height: position.h,
            rx: 8, fill: "var(--surface)", stroke: colour, "stroke-width": 1.2,
          })
        );
        group.appendChild(
          el("rect", { x: position.x, y: position.y, width: 3, height: position.h, rx: 1.5, fill: colour })
        );
        const main = el("text", { class: "n-label", x: position.x + 13, y: position.y + (sub ? 17 : 24) });
        main.textContent = label.length > 28 ? `${label.slice(0, 27)}…` : label;
        group.appendChild(main);
        if (sub) {
          const secondary = el("text", { class: "n-sub", x: position.x + 13, y: position.y + 30 });
          secondary.textContent = sub;
          group.appendChild(secondary);
        }
        svg.appendChild(group);
      });
    });

    // Say what the picture is not showing, rather than quietly truncating.
    const notes = [];
    if (model.grouped) {
      notes.push(this.t("graph.grouped", { n: Object.keys(model.devices).length }));
    }
    const drawn = new Set(model.origins.flatMap((id) => model.members.get(id) || []));
    const hidden = [...model.withConduits].filter((id) => !drawn.has(id)).length;
    if (hidden > 0) notes.push(this.t("graph.hidden", { n: hidden }));
    if (notes.length) {
      const note = el("text", { class: "n-sub", x: 30, y: H - 12 });
      note.textContent = notes.join(" · ");
      svg.appendChild(note);
    }
  }
}

customElements.define("talos-panel", TalosPanel);
