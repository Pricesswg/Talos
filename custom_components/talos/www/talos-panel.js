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
 * Every language carries the same keys as English; a test fails if they
 * drift apart. The wording is part of the product: it states facts and their
 * evidence, and never a verdict the data cannot support.
 */
const I18N = {};

/** Strings live in i18n/<lang>.json next to this file, one table per
 *  language, and are fetched on demand: keeping eight languages inline would
 *  triple the size of the script every browser loads for one of them. The
 *  English table is always loaded and is the fallback for any key a language
 *  lacks. The URL carries the same ?v= as the script, so a release refreshes
 *  both together. */
const LANGUAGES = {
  en: "English",
  it: "Italiano",
  fr: "Français",
  de: "Deutsch",
  es: "Español",
  nl: "Nederlands",
  pl: "Polski",
  pt: "Português",
};
const LOCALES = {
  en: "en-GB",
  it: "it-IT",
  fr: "fr-FR",
  de: "de-DE",
  es: "es-ES",
  nl: "nl-NL",
  pl: "pl-PL",
  pt: "pt-PT",
};
const I18N_PENDING = {};

function loadLanguage(code) {
  if (I18N[code]) return Promise.resolve(I18N[code]);
  if (!I18N_PENDING[code]) {
    const url = new URL(`i18n/${code}.json`, import.meta.url);
    url.search = new URL(import.meta.url).search;
    I18N_PENDING[code] = fetch(url.href, { credentials: "same-origin" })
      .then((response) => {
        if (!response.ok) throw new Error(`${response.status} for ${code}.json`);
        return response.json();
      })
      .then((table) => {
        I18N[code] = table;
        return table;
      })
      .catch((err) => {
        // A missing table is not fatal: keys render raw, which is visible and
        // says exactly which file did not arrive.
        console.warn("talos: language table not loaded:", err);
        delete I18N_PENDING[code];
        return null;
      });
  }
  return I18N_PENDING[code];
}


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
  --k-tunnel: #a35a2a;
  --k-unknown: #868d8e;

  --t-zigbee: #2f7d6a;
  --t-zwave: #64768c;
  --t-wifi: #16697f;
  --t-ethernet: #6b5aa0;
  --t-thread: #4a7d3f;
  --t-matter: #2b7f8c;
  --t-ble: #3f6ea0;
  --t-ip: #3d6f86;
  --t-virtual: #8a7f6a;
  --t-unknown: #868d8e;

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
    --k-local: #52b195; --k-infra: #93a5bd; --k-vendor: #c07dbb; --k-tunnel: #d98d5a; --k-unknown: #8d9799;
    --alert: #ff6f60; --attention: #d5a343;
    --t-zigbee: #52b195; --t-zwave: #93a5bd; --t-wifi: #52b2c8;
    --t-ethernet: #a396d6; --t-thread: #7fbb70; --t-matter: #63c3d1;
    --t-ble: #7ba3d8; --t-ip: #6f9fb8; --t-virtual: #bdae94; --t-unknown: #8d9799;
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
h2.sec { cursor: pointer; user-select: none; }
h2.sec::before {
  content: "›"; display: inline-block; font-size: 15px; line-height: 1;
  color: var(--ink-mute); transform: rotate(90deg); transition: transform 140ms;
}
h2.sec:hover::before { color: var(--ink); }
[data-collapsed="1"] > h2.sec::before { transform: rotate(0deg); }
[data-collapsed="1"] > *:not(h2.sec) { display: none; }
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
/* One bar for every long operation. Colours come from the Home Assistant
   theme where it defines them, so it stays readable in both light and dark
   and in whatever palette the user picked. */
.toast {
  display: flex; align-items: center; gap: 10px;
  padding: 10px 14px; margin: 0 0 4px;
  border: 1px solid var(--border); border-left: 3px solid var(--tone);
  border-radius: var(--r-md); background: var(--surface);
  font-size: 13px; color: var(--ink);
}
.toast[data-tone="busy"] { --tone: var(--info-color, var(--accent)); }
.toast[data-tone="ok"] { --tone: var(--success-color, var(--k-local)); }
.toast[data-tone="error"] { --tone: var(--error-color, var(--alert)); }
.toast__dot {
  width: 9px; height: 9px; border-radius: 50%; background: var(--tone); flex: none;
}
.toast[data-tone="busy"] .toast__dot { animation: talos-pulse 1.1s ease-in-out infinite; }
@keyframes talos-pulse { 0%,100% { opacity: 1 } 50% { opacity: .25 } }
.toast__sub { color: var(--ink-mute); font-size: 12.5px; }
.icon-btn[data-busy="1"] svg { animation: talos-spin 1s linear infinite; }
@keyframes talos-spin { to { transform: rotate(360deg) } }

.filters { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; margin: 0 0 12px; }
.filters input[type="search"] {
  flex: 1 1 220px; min-width: 180px; padding: 7px 11px;
  border: 1px solid var(--border); border-radius: var(--r-md);
  background: var(--surface); color: var(--ink); font: inherit; font-size: 13px;
}
.filters input[type="search"]:focus { outline: 2px solid var(--accent); outline-offset: 1px; }
.chip--filter[aria-pressed="true"] { background: var(--accent-soft); border-color: var(--accent); }
.sugg {
  display: flex; gap: 8px; align-items: baseline; flex-wrap: wrap;
  margin-top: 6px; font-size: 12.5px; color: var(--ink-mute);
}
.sugg button {
  border: 1px solid var(--accent); color: var(--accent-ink, var(--accent));
  background: var(--accent-soft); border-radius: var(--r-pill);
  padding: 2px 10px; font-size: 12px; font-weight: 500;
}
.guide { margin-top: 10px; }
.guide h4 { margin: 14px 0 5px; font-size: 13px; font-weight: 600; color: var(--ink); }
.guide h4:first-child { margin-top: 0; }
.guide p { margin: 0 0 8px; font-size: 12.5px; color: var(--ink-soft); max-width: 84ch; }

.charts { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 14px; }
.chart { }
.chart__title { font-size: 12px; letter-spacing: .06em; text-transform: uppercase; color: var(--ink-mute); margin: 0 0 6px; }
.chart svg { width: 100%; height: 150px; display: block; }
.chart__legend { display: flex; gap: 12px; flex-wrap: wrap; font-size: 12px; color: var(--ink-soft); margin-top: 6px; }
.chart__legend span { display: inline-flex; align-items: center; gap: 6px; }
.chart__legend i { width: 14px; height: 3px; border-radius: 2px; display: inline-block; }
.chart__legend b { font-weight: 500; color: var(--ink); font-family: var(--font-mono); }
.chart text { font-family: var(--font-mono); font-size: 10px; fill: var(--ink-mute); }

.pies { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 14px; }
.pie { display: flex; gap: 14px; align-items: flex-start; }
.pie svg { width: 112px; height: 112px; flex: none; }
.pie__title { font-size: 12px; letter-spacing: .06em; text-transform: uppercase; color: var(--ink-mute); margin: 0 0 6px; }
.pie__legend { font-size: 12.5px; color: var(--ink-soft); }
.pie__legend div { display: flex; gap: 8px; align-items: baseline; padding: 2px 0; }
.pie__legend i { display: inline-block; width: 9px; height: 9px; border-radius: 2px; flex: none; }
.pie__legend b { font-weight: 500; color: var(--ink); }
.pie__legend span { margin-left: auto; font-family: var(--font-mono); font-variant-numeric: tabular-nums; }
.pie__note { font-size: 11.5px; color: var(--ink-mute); margin: 6px 0 0; }

.exp {
  border: 1px solid var(--border);
  border-left: 3px solid var(--ink-mute);
  border-radius: var(--r-md);
  background: var(--surface);
  margin-bottom: 8px;
}
.exp[data-tone="alert"] { border-left-color: var(--alert); }
.exp[data-tone="attention"] { border-left-color: var(--attention); }
.exp[data-tone="pass"] { border-left-color: var(--k-local); }
.exp[data-tone="info"] { border-left-color: var(--accent); }
.exp > summary {
  list-style: none; cursor: pointer; padding: 11px 14px;
  display: flex; gap: 9px; align-items: center; font-size: 13.5px;
}
.exp > summary::-webkit-details-marker { display: none; }
.exp > summary::before {
  content: "›"; color: var(--ink-mute); font-size: 15px; line-height: 1;
  display: inline-block; transition: transform .15s ease;
}
.exp[open] > summary::before { transform: rotate(90deg); }
.exp > summary:hover { background: var(--sunken); }
.exp__t { font-weight: 500; }
.exp__sp { flex: 1 1 auto; }
.exp__body {
  padding: 2px 14px 14px 32px; font-size: 13px;
  color: var(--ink-soft); max-width: 84ch;
}
.exp__body p { margin: 0 0 9px; }
.exp__body p:last-child { margin-bottom: 0; }
.exp__body strong { color: var(--ink); font-weight: 500; }
.exp__do {
  margin-top: 10px; padding: 9px 12px; background: var(--sunken);
  border-radius: var(--r-md); font-size: 12.5px;
}
.exp__lab {
  font-size: 11px; letter-spacing: .06em; text-transform: uppercase;
  color: var(--ink-mute); margin: 12px 0 5px;
}
.exp__rows { border-top: 1px solid var(--border); }
.exp__row {
  display: flex; gap: 12px; align-items: baseline;
  padding: 6px 0; border-bottom: 1px solid var(--border); font-size: 12.5px;
}
.exp__row b { font-weight: 500; color: var(--ink); }
.exp__row span { margin-left: auto; color: var(--ink-mute); text-align: right; }
.tally { display: flex; gap: 14px; flex-wrap: wrap; margin: 0 0 12px; font-size: 12.5px; color: var(--ink-soft); }
.tally b { font-weight: 600; color: var(--ink); }
.tally i { display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 6px; }
.note {
  border: 1px solid var(--border); border-left: 3px solid var(--ink-mute);
  border-radius: var(--r-lg); padding: 14px 18px; max-width: 78ch;
  background: color-mix(in srgb, var(--sunken) 55%, transparent);
}
.note__label {
  font-size: 10.5px; letter-spacing: .1em; text-transform: uppercase;
  color: var(--ink-mute); font-weight: 500; margin-bottom: 8px;
}
.note p { margin: 0 0 8px; font-size: 12.5px; color: var(--ink-soft); }
.note p:last-child { margin-bottom: 0; }

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
/* Kind colours are set inline from KIND_COLOUR, so the code lives in one
   place and a new kind cannot be added to the model without one. */
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

.tgroup {
  background: var(--surface); border: 1px solid var(--border);
  border-left: 3px solid var(--accent); border-radius: var(--r-lg);
  margin-bottom: 12px; overflow: hidden;
}
.tgroup__head {
  display: flex; align-items: baseline; gap: 12px; flex-wrap: wrap;
  padding: 14px 18px 10px;
}
.tgroup__name { font-size: 15px; font-weight: 600; }
.tgroup__count { font-family: var(--font-mono); font-size: 13px; color: var(--ink-soft); }
.tgroup__share { flex: 1; min-width: 90px; height: 4px; border-radius: var(--r-pill); background: var(--sunken); overflow: hidden; }
.tgroup__share span { display: block; height: 100%; }
.tgroup details { border-top: 1px solid var(--border); }
.tgroup summary {
  cursor: pointer; padding: 10px 18px; font-size: 13px;
  display: flex; align-items: center; gap: 10px; flex-wrap: wrap;
}
.tgroup summary::-webkit-details-marker { display: none; }
.tgroup summary::before {
  content: "›"; display: inline-block; transition: transform 120ms;
  color: var(--ink-mute); font-size: 15px; line-height: 1;
}
.tgroup details[open] > summary::before { transform: rotate(90deg); }
.tgroup summary:hover { background: var(--sunken); }
.tgroup__domain { font-family: var(--font-mono); font-size: 12px; color: var(--ink-mute); }
.tgroup__n { margin-left: auto; font-family: var(--font-mono); font-size: 12px; color: var(--ink-mute); }
.devlist {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 6px 18px; padding: 4px 18px 16px 34px;
}
.dev { font-size: 12.5px; }
.dev span { display: block; font-size: 11px; color: var(--ink-mute); font-family: var(--font-mono); }
.mapwrap { position: relative; background: var(--surface); border: 1px solid var(--border); border-radius: var(--r-lg); overflow: hidden; }
svg.map { display: block; width: 100%; height: clamp(560px, 76vh, 920px); cursor: grab; touch-action: none; }
svg.map.dragging { cursor: grabbing; }
/* Labels: the name and nothing else, with a halo the colour of the surface
   so a name stays legible where it crosses an edge or another label. The
   details live in the popup; a second line under every dot was what made
   the picture hard to read. */
svg.map text {
  font-family: var(--font-sans); fill: var(--ink); pointer-events: none;
  paint-order: stroke fill; stroke: var(--surface); stroke-width: 3.5px; stroke-linejoin: round;
}
svg.map .lbl { font-size: 12.5px; font-weight: 500; }
/* A leaf's name shows when the pointer is near it, when it is the focus or
   a neighbour of the focus, or when the search matched it. Never by zoom
   alone: four hundred names at once are a wall whatever the halo does for
   each one, and that wall was the complaint. */
svg.map .lbl--device { font-size: 11.5px; font-weight: 400; display: none; }
svg.map .node--match .lbl--device, svg.map .is-focus .lbl--device,
svg.map .is-near .lbl--device, svg.map .is-hover .lbl--device { display: inline; }
svg.map .is-hover .node__mark { stroke: var(--ink-mute); stroke-width: 1.5px; }
svg.map .lbl--core { font-size: 15px; font-weight: 600; }
svg.map .lbl--transport { font-size: 13.5px; font-weight: 600; }
svg.map .link { fill: none; stroke-opacity: .38; transition: stroke-opacity .2s; }
svg.map .link--bridge { stroke-opacity: .7; stroke-dasharray: 7 5; }

/* Focus: the clicked node and its neighbours stay, the rest fades, and the
   edges that touch it carry a running dash from the leaf towards the hub,
   which is the direction the data goes. The path is drawn child to parent
   so a negative offset is that direction. */
svg.map.has-focus .node:not(.is-focus):not(.is-near) { opacity: .14; }
svg.map.has-focus .link:not(.flow) { stroke-opacity: .07; }
/* Listed with the intro selector too, so it wins on specificity while the
   reveal class is still on the svg: at equal specificity the later rule
   won, and the later rule was the intro. */
svg.map .link.flow, svg.map.animate .link.flow {
  stroke-opacity: 1; stroke-dasharray: 5 9;
  animation: talos-flow 1.1s linear infinite;
}
@keyframes talos-flow { to { stroke-dashoffset: -14; } }
svg.map .is-focus .node__mark { stroke: var(--ink); stroke-width: 2.5px; }
svg.map .is-focus .lbl, svg.map .is-near .lbl { font-weight: 600; }

.mappopup {
  position: absolute; z-index: 6; width: min(340px, calc(100% - 24px));
  background: var(--surface); border: 1px solid var(--border); border-radius: var(--r-lg);
  box-shadow: 0 10px 30px rgba(0,0,0,.28); padding: 12px 14px 12px;
  font-size: 12.5px; color: var(--ink-soft);
}
.mappopup__head { display: flex; gap: 10px; align-items: baseline; margin-bottom: 8px; }
.mappopup__title { font-weight: 600; font-size: 14px; color: var(--ink); flex: 1; }
.mappopup__kind { font-size: 11px; letter-spacing: .06em; text-transform: uppercase; color: var(--ink-mute); }
.mappopup__close { border: none; background: none; color: var(--ink-mute); font-size: 18px; line-height: 1; cursor: pointer; padding: 0 2px; }
.mappopup dl { display: grid; grid-template-columns: max-content 1fr; gap: 3px 12px; margin: 0; }
.mappopup dt { color: var(--ink-mute); }
.mappopup dd { margin: 0; color: var(--ink); font-family: var(--font-mono); font-size: 12px; word-break: break-word; }
.mappopup__links { margin-top: 10px; border-top: 1px solid var(--border); padding-top: 8px; }
.mappopup__links b { display: block; font-size: 11px; letter-spacing: .06em; text-transform: uppercase; color: var(--ink-mute); margin-bottom: 4px; font-weight: 500; }
.mappopup__links div { display: flex; gap: 8px; padding: 2px 0; }
.mappopup__links div i { width: 8px; height: 8px; border-radius: 50%; flex: none; margin-top: 5px; }
.mappopup__links span { margin-left: auto; color: var(--ink-mute); font-family: var(--font-mono); }
.mappopup .btn { margin-top: 10px; width: 100%; }

/* The reveal walks outwards, one ring at a time, so the structure builds
   rather than appearing all at once. Only on a structural redraw: a drag
   redraws every frame and would restart it forever. */
@keyframes talos-node-in { from { opacity: 0; } to { opacity: 1; } }
@keyframes talos-mark-in {
  from { transform: scale(.2); }
  60%  { transform: scale(1.18); }
  to   { transform: scale(1); }
}
@keyframes talos-link-in { from { stroke-dashoffset: 1; } to { stroke-dashoffset: 0; } }
svg.map.animate .node { animation: talos-node-in 320ms ease-out backwards; }
svg.map.animate .node__mark {
  transform-box: fill-box; transform-origin: center;
  animation: talos-mark-in 380ms cubic-bezier(.2, .9, .3, 1.25) backwards;
}
svg.map.animate .link {
  stroke-dasharray: 1; animation: talos-link-in 420ms ease-out backwards;
}
svg.map.animate .link--bridge { stroke-dasharray: 7 5; animation: talos-node-in 420ms ease-out backwards; }
@media (prefers-reduced-motion: reduce) {
  svg.map.animate .node, svg.map.animate .node__mark, svg.map.animate .link { animation: none; }
  svg.map .link.flow { animation: none; stroke-dasharray: none; }
}
svg.map .node { cursor: grab; }
svg.map.dragging .node { cursor: grabbing; }
svg.map .dim { opacity: .12; }
svg.map .hit { fill: transparent; }
.maptools { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; padding: 12px 16px; border-bottom: 1px solid var(--border); }
.maptools input[type="search"] {
  font: inherit; color: var(--ink); background: var(--bg); border: 1px solid var(--border);
  border-radius: var(--r-md); padding: 7px 10px; min-width: 240px; flex: 1;
}
.maptools .hint { font-size: 11.5px; color: var(--ink-mute); }
.btn--ghost { background: none; color: var(--ink-soft); border: 1px solid var(--border); padding: 7px 12px; }
.detail { display: inline-flex; align-items: center; gap: 8px; }
.detail__level { font-size: 12px; color: var(--ink-soft); min-width: 130px; text-align: center; }
.mapfilters { flex-wrap: wrap; gap: 8px; }
.chip--filter { cursor: pointer; padding: 3px 10px; }
.chip--filter[aria-pressed="true"] { border-color: var(--accent); color: var(--accent-ink); background: var(--accent-soft); }
.scopebadge { display: inline-flex; align-items: center; gap: 8px; margin-left: auto; font-size: 12px; color: var(--ink-soft); }
.scopebadge button { color: var(--accent-ink); text-decoration: underline; }
.maplegend { display: flex; gap: 14px; flex-wrap: wrap; padding: 10px 16px; border-top: 1px solid var(--border); font-size: 11.5px; color: var(--ink-soft); }
.maplegend span { display: inline-flex; align-items: center; gap: 6px; }
.swatch { width: 10px; height: 10px; border-radius: 3px; }
.swatch--round { border-radius: 50%; }

.hub { display: flex; justify-content: space-between; gap: 14px; align-items: baseline;
  padding: 10px 0; border-bottom: 1px solid var(--border); font-size: 13.5px; }
.hub:last-child { border-bottom: none; }
.hub__meta { font-size: 11.5px; color: var(--ink-mute); }

.panel-card {
  background: var(--surface); border: 1px solid var(--border);
  border-radius: var(--r-lg); padding: 18px 20px;
}
.form { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 16px; }
.field { display: flex; flex-direction: column; gap: 6px; }
.field label { font-size: 12.5px; font-weight: 500; }
.field input, .field select {
  font: inherit; color: var(--ink); background: var(--bg);
  border: 1px solid var(--border); border-radius: var(--r-md);
  padding: 8px 10px; width: 100%;
}
.field input:focus, .field select:focus { outline: 2px solid var(--accent); outline-offset: 1px; }
.field .hint { font-size: 11.5px; color: var(--ink-mute); }
.kv { display: grid; grid-template-columns: minmax(180px, auto) 1fr; gap: 6px 18px; font-size: 13px; }
.kv dt { color: var(--ink-mute); }
.kv dd { margin: 0; }
.actions { display: flex; align-items: center; gap: 14px; flex-wrap: wrap; }
.btn {
  padding: 9px 20px; border-radius: var(--r-md); font-size: 13.5px; font-weight: 500;
  background: var(--accent); color: #fff;
}
.btn[disabled] { opacity: .5; cursor: default; }
.status { font-size: 12.5px; color: var(--ink-soft); }
.status[data-tone="error"] { color: var(--alert); }

svg.graph { display: block; min-width: 900px; }
svg.graph text { font-family: var(--font-sans); fill: var(--ink); }
svg.graph .col-title { font-size: 10px; letter-spacing: .11em; text-transform: uppercase; fill: var(--ink-mute); }
svg.graph .n-label { font-size: 11.5px; }
svg.graph .n-sub { font-size: 10px; fill: var(--ink-mute); font-family: var(--font-mono); }
svg.graph .band { fill: color-mix(in srgb, var(--ink) 5%, transparent); }
svg.graph .edge { fill: none; }
`;

const PHONE_HOME = new Set([
  "vendor_cloud", "telemetry", "push_service", "cdn", "nat_traversal", "unknown",
]);
// Inside the house. Drawn so a local branch ends somewhere real, and coloured
// as local so it never reads as egress.
const INTERNAL_KINDS = new Set(["ha_core", "local_broker", "local_hub"]);

/* The colour code, in one place because three views draw the same links.
 * Colour answers "what is at the other end", and never "how bad is it": red
 * is spent on exactly one thing in this file, a device Home Assistant drives
 * locally that was observed reaching its vendor anyway, and nothing else may
 * take it. A local link is drawn in its transport's own colour instead, the
 * same one the map uses, so Zigbee is the same green in both views. */
// The first legend row is what is outside the house, by who is at the other
// end. Inside is the second row, named by transport, so there is no generic
// "local" swatch here: it would sit next to Zigbee's, in the same green,
// saying two different things with one colour.
const LEGEND_KINDS = [
  ["infra", "--k-infra"],
  ["vendor", "--k-vendor"],
  ["tunnel", "--k-tunnel"],
  ["unknown", "--k-unknown"],
];

// Wedge colours. Categorical: they answer "which add-on", nothing more, so
// they borrow the transport palette, which was chosen to be told apart.
const WEDGE_COLOURS = [
  "--t-wifi", "--t-zigbee", "--t-ethernet", "--t-matter", "--t-thread",
  "--t-ble", "--t-zwave", "--k-vendor", "--k-tunnel", "--t-ip",
];

const KIND_COLOUR = {
  ha_core: "--k-local",
  local_broker: "--k-local",
  local_hub: "--k-local",
  ntp: "--k-infra",
  ota_update: "--k-infra",
  cdn: "--k-infra",
  vendor_cloud: "--k-vendor",
  telemetry: "--k-vendor",
  push_service: "--k-vendor",
  nat_traversal: "--k-tunnel",
  unknown: "--k-unknown",
};
const SEVERITY_TONE = { high: "alert", medium: "attention", low: "info" };
// Worst first, so the list opens on the thing that matters most.
const SEVERITY_ORDER = ["high", "medium", "low"];
// What Talos does not look at. Ordered the way someone would work
// through them, not by severity: none of them is Talos's to judge.
const SCOPE_ITEMS = ["segmentation", "credentials", "firmware", "exposure", "doh", "payload"];
// The short guide, ordered by what each step returns for the effort it costs.
const GUIDE_STEPS = [1, 2, 3, 4, 5, 6];

/* Above this many devices carrying a conduit, the first column groups by
 * integration. A hand-laid SVG stays readable at a few dozen nodes and not at
 * a few hundred, and a truncated picture that hides the shape is worse than a
 * grouped one that shows it. */
const GROUP_THRESHOLD = 10;
const MAX_ROWS = 10;
// Devices an integration needs before its name is always on the map.
const MAJOR_INTEGRATION = 5;
// Rows kept for what is inside the house, so a local branch always ends at
// the hub or broker it actually reaches.
const LOCAL_ROWS = 4;

const byName = (a, b) => String(a.name || a.id).localeCompare(String(b.name || b.id));

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
    this._saving = false;
    this._saveStatus = null;
    this._mapQuery = "";
    this._detail = 2;
    this._scope = null;
    this._reheat = 0;
    this._view = { k: 1, x: 0, y: 0 };
    // Reading storage can throw in a private window or with site data blocked.
    try {
      this._langOverride = window.localStorage.getItem("talos.lang") || "";
    } catch (err) {
      this._langOverride = "";
    }
  }

  resolveLang(hass) {
    if (this._langOverride && LANGUAGES[this._langOverride]) return this._langOverride;
    const raw = (hass && ((hass.locale && hass.locale.language) || hass.language)) || "";
    const base = String(raw).toLowerCase().split("-")[0];
    return LANGUAGES[base] ? base : FALLBACK_LANG;
  }

  setLanguage(value) {
    this._langOverride = value === "auto" ? "" : value;
    try {
      if (this._langOverride) window.localStorage.setItem("talos.lang", this._langOverride);
      else window.localStorage.removeItem("talos.lang");
    } catch (err) {
      // A browser that refuses storage still gets the change for this session.
    }
    this._lang = this.resolveLang(this._hass);
    this.ensureLanguage().then(() => this.render());
  }

  /** The fallback table and the active one, fetched once. Awaited before
   *  any render that matters, so the screen never shows raw keys. */
  async ensureLanguage() {
    await Promise.all([loadLanguage(FALLBACK_LANG), loadLanguage(this._lang)]);
  }

  set hass(hass) {
    this._hass = hass;
    this._lang = this.resolveLang(hass);
    if (!this._loaded) {
      this._loaded = true;
      this.load();
    }
  }

  connectedCallback() {
    this.ensureLanguage().then(() => this.render());
  }

  /* ── i18n ────────────────────────────────────────────────────────────── */

  t(key, vars) {
    const table = I18N[this._lang] || I18N[FALLBACK_LANG] || {};
    let text = table[key];
    if (text === undefined) text = (I18N[FALLBACK_LANG] || {})[key];
    if (text === undefined) return key;
    if (!vars) return text;
    return text.replace(/\{(\w+)\}/g, (match, name) =>
      Object.prototype.hasOwnProperty.call(vars, name) ? String(vars[name]) : match
    );
  }

  num(value) {
    if (value == null) return "-";
    return Number(value).toLocaleString(LOCALES[this._lang] || LOCALES[FALLBACK_LANG]);
  }

  /* ── data ────────────────────────────────────────────────────────────── */

  async load({ quiet = false } = {}) {
    this._loading = true;
    await this.ensureLanguage();
    if (!quiet) this.render();
    try {
      const [derived, status, suggested, diagnostics, history] = await Promise.all([
        this._hass.callWS({ type: "talos/derived" }),
        this._hass.callWS({ type: "talos/status" }),
        // Advisory only: an older integration without the command must not
        // take the whole panel down with it.
        this._hass.callWS({ type: "talos/suggest" }).catch(() => ({ suggestions: [] })),
        this._hass.callWS({ type: "talos/diagnostics/last" }).catch(() => ({ run: null })),
        // Advisory: an older integration without the command must not take
        // the panel down, and a fresh install simply has no rows yet.
        this._hass.callWS({ type: "talos/history", limit: 500 }).catch(() => ({ rows: [] })),
      ]);
      this._data = derived;
      // A finished scan supersedes the last save's test result.
      if (this._status && status.generated_at !== this._status.generated_at) {
        this._mqttResult = null;
      }
      this._status = status;
      this._suggestions = (suggested || {}).suggestions || [];
      if (diagnostics && diagnostics.run) this._diagnostics = diagnostics.run;
      this._history = (history && history.rows) || [];
      this._error = null;
    } catch (err) {
      this._error = err && err.message ? err.message : String(err);
    } finally {
      this._loading = false;
      this.render();
    }
  }

  /** What the panel is doing right now, in one place. `ok` clears itself so
   *  a success does not sit on screen forever; an error stays until the next
   *  operation, because it is the only record the user gets of it. */
  setBusy(tone, title, sub) {
    if (this._busyTimer) {
      window.clearTimeout(this._busyTimer);
      this._busyTimer = null;
    }
    this._busy = tone ? { tone, title, sub } : null;
    this.render();
    if (tone === "ok") {
      this._busyTimer = window.setTimeout(() => {
        this._busy = null;
        this._busyTimer = null;
        this.render();
      }, 6000);
    }
  }

  busyBar() {
    // A scan that has been failing since yesterday reads as an idle panel
    // unless the timestamp is put next to the reason.
    const status = this._status || {};
    const busy =
      this._busy ||
      (status.last_update_success === false
        ? {
            tone: "error",
            title: this.t("busy.stale"),
            sub: this.t("busy.stale.sub", {
              when: this.when(status.generated_at),
              reason: status.last_error || "-",
            }),
          }
        : null);
    if (!busy) return "";
    return `<div class="toast" data-tone="${busy.tone}" role="status">
      <span class="toast__dot"></span>
      <span><strong>${esc(busy.title)}</strong>${
        busy.sub ? ` <span class="toast__sub">${esc(busy.sub)}</span>` : ""
      }</span>
    </div>`;
  }

  when(value) {
    return value
      ? new Date(value).toLocaleString(LOCALES[this._lang] || LOCALES[FALLBACK_LANG])
      : this.t("app.never");
  }

  async refresh() {
    if (this._scanning) return;
    this._scanning = true;
    this.setBusy("busy", this.t("busy.scanning"), this.t("busy.scanning.sub"));
    let result = null;
    try {
      result = await this._hass.callWS({ type: "talos/refresh" });
    } catch (err) {
      result = { ok: false, error: err && err.message ? err.message : String(err) };
    }
    await this.load({ quiet: true });
    this._scanning = false;
    if (result && result.ok) {
      this.setBusy(
        "ok",
        this.t("busy.scanOk"),
        this.t("busy.scanOk.sub", { when: this.when(result.generated_at) })
      );
    } else {
      this.setBusy(
        "error",
        this.t("busy.scanError"),
        (result && result.error) || this._error || ""
      );
    }
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
    if (String(id).startsWith("undisclosed:")) {
      // The manifest says the integration needs a cloud service and does not
      // say which host. Named as such rather than invented.
      const integration = (this._data.labels.integrations || {})[String(id).slice(12)] || {};
      return {
        fqdn: this.t("flows.undisclosed"),
        kind: "vendor_cloud",
        vendor: integration.title || "",
        undisclosed: true,
      };
    }
    return (this._data && this._data.labels.destinations[id]) || { fqdn: id, kind: "unknown" };
  }

  /** Integrations whose manifest declares a cloud dependency. */
  cloudIntegrations() {
    return Object.entries((this._data && this._data.labels.integrations) || {})
      .filter(([, integration]) => String(integration.iot_class || "").startsWith("cloud_"))
      .sort((a, b) => (b[1].entity_count || 0) - (a[1].entity_count || 0))
      .map(([id]) => id);
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

    this.stopMap();
    host.innerHTML =
      this.toolbar() +
      `<div class="wrap">` +
      this.busyBar() +
      (this._mode === "base"
        ? this.viewBase()
        : this._mode === "map"
          ? this.viewMap()
          : this._mode === "settings"
            ? this.viewSettings()
            : this._mode === "diagnostics"
              ? this.viewDiagnostics()
              : this.viewAdvanced()) +
      `</div>`;

    host.querySelectorAll("[data-mode]").forEach((button) => {
      button.addEventListener("click", () => {
        this._mode = button.dataset.mode;
        this.render();
      });
    });
    const refresh = host.querySelector("[data-action='refresh']");
    if (refresh) {
      if (this._scanning) refresh.dataset.busy = "1";
      refresh.addEventListener("click", () => this.refresh());
    }

    const diagRun = host.querySelector("[data-action='diag-run']");
    if (diagRun) diagRun.addEventListener("click", () => this.runDiagnostics());

    const mqttSave = host.querySelector("[data-action='mqtt-save']");
    if (mqttSave) mqttSave.addEventListener("click", () => this.saveMqtt(false));
    const mqttClear = host.querySelector("[data-action='mqtt-clear']");
    if (mqttClear) mqttClear.addEventListener("click", () => this.saveMqtt(true));
    const mqttTest = host.querySelector("[data-action='mqtt-test']");
    if (mqttTest) mqttTest.addEventListener("click", () => this.testMqtt());

    this.wireInventory(host);

    host.querySelectorAll("[data-suggest]").forEach((button) => {
      button.addEventListener("click", () => {
        const input = host.querySelector(`#opt-${button.dataset.suggest}`);
        if (!input) return;
        input.value = button.dataset.value;
        input.focus();
      });
    });

    this.wireSections(host);

    const svg = host.querySelector("svg.graph");
    if (svg) this.drawGraph(svg);

    const map = host.querySelector("svg.map");
    if (map) {
      this.drawMap(map, true);
      const search = host.querySelector("[data-action='map-search']");
      if (search) {
        // Redraw only the map, so the field keeps focus while typing.
        search.addEventListener("input", (event) => {
          this._mapQuery = event.target.value;
          this.drawMap(map);
        });
      }
      const setDetail = (delta) => {
        this._detail = Math.min(3, Math.max(1, (this._detail || 2) + delta));
        this._view = { k: 1, x: 0, y: 0 };
        this._mapBox = null;
        this._scope = null;
        this.render();
      };
      host.querySelectorAll("[data-scope]").forEach((button) => {
        button.addEventListener("click", () => {
          const value = button.dataset.scope;
          this._scope =
            value === "all"
              ? null
              : {
                  kind: value.startsWith("r:") ? "role" : "transport",
                  id: value.slice(2),
                };
          this._view = { k: 1, x: 0, y: 0 };
          this._mapBox = null;
          this.render();
        });
      });

      const less = host.querySelector("[data-action='map-less']");
      if (less) less.addEventListener("click", () => setDetail(-1));
      const more = host.querySelector("[data-action='map-more']");
      if (more) more.addEventListener("click", () => setDetail(1));

      const reset = host.querySelector("[data-action='map-reset']");
      if (reset) {
        reset.addEventListener("click", () => {
          this._view = { k: 1, x: 0, y: 0 };
          this._mapBox = null;
          this._mapQuery = "";
          this._detail = 2;
          this._scope = null;
          this.render();
        });
      }
    }

    const language = host.querySelector("[data-action='language']");
    if (language) language.addEventListener("change", (event) => this.setLanguage(event.target.value));
    const save = host.querySelector("[data-action='save']");
    if (save) save.addEventListener("click", () => this.saveOptions());
  }

  /** Every section heading folds its own section away.
   *
   * The key is the view plus the heading's position, which is stable across
   * languages and reloads; the text is not. Kept per browser, like the
   * language, since it is a reading preference and not configuration. */
  /** The reason a value is proposed, in the reader's language. The backend
   *  writes it in English, which stands in only if nothing translates it. */
  suggestionDetail(key, found) {
    const translated = this.t(`sugg.detail.${key}`);
    return translated.startsWith("sugg.detail.") ? found.detail || "" : translated;
  }

  /** Redraw only the inventory, so the search field keeps focus and the
   *  caret while the list under it changes. */
  renderInventory(host) {
    const container = host.querySelector("[data-inventory]");
    if (!container) return;
    // activeElement lives on the shadow root, not on the container div.
    const active = this.shadowRoot.activeElement;
    const focused = active === host.querySelector("[data-action='inv-search']");
    const caret = focused ? active.selectionStart : null;
    container.innerHTML = this.inventory();
    this.wireInventory(host);
    if (focused) {
      const field = host.querySelector("[data-action='inv-search']");
      if (field) {
        field.focus();
        if (caret != null) field.setSelectionRange(caret, caret);
      }
    }
  }

  wireInventory(host) {
    const search = host.querySelector("[data-action='inv-search']");
    if (search) {
      search.addEventListener("input", (event) => {
        this._invQuery = event.target.value;
        this.renderInventory(host);
      });
    }
    host.querySelectorAll("[data-invfilter]").forEach((button) => {
      button.addEventListener("click", () => {
        this._invFilter = button.dataset.invfilter;
        this.renderInventory(host);
      });
    });
  }

  wireSections(host) {
    const collapsed = this._collapsed || (this._collapsed = this.readCollapsed());
    host.querySelectorAll("h2.sec").forEach((heading, index) => {
      const key = `${this._mode}:${index}`;
      const section = heading.parentElement;
      if (!section) return;
      heading.setAttribute("role", "button");
      heading.setAttribute("tabindex", "0");
      heading.setAttribute("title", this.t("section.collapse"));
      if (collapsed.has(key)) section.dataset.collapsed = "1";

      const toggle = () => {
        if (collapsed.has(key)) {
          collapsed.delete(key);
          delete section.dataset.collapsed;
        } else {
          collapsed.add(key);
          section.dataset.collapsed = "1";
        }
        this.writeCollapsed(collapsed);
      };
      heading.addEventListener("click", toggle);
      heading.addEventListener("keydown", (event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          toggle();
        }
      });
    });
  }

  readCollapsed() {
    try {
      return new Set(JSON.parse(window.localStorage.getItem("talos.collapsed") || "[]"));
    } catch (err) {
      return new Set();
    }
  }

  writeCollapsed(collapsed) {
    try {
      window.localStorage.setItem("talos.collapsed", JSON.stringify([...collapsed]));
    } catch (err) {
      // A browser that refuses storage still folds for this session.
    }
  }

  toolbar() {
    const status = this._status || {};
    const when = this.when(status.generated_at);
    return `
      <div class="bar">
        <div>
          <h1>Talos</h1>
          <div class="sub mono">${esc(this.t("app.subtitle", { when }))}</div>
        </div>
        <div class="spacer"></div>
        <div class="seg" role="group">
          <button data-mode="base" aria-pressed="${this._mode === "base"}">${esc(this.t("mode.base"))}</button>
          <button data-mode="map" aria-pressed="${this._mode === "map"}">${esc(this.t("mode.map"))}</button>
          <button data-mode="advanced" aria-pressed="${this._mode === "advanced"}">${esc(this.t("mode.advanced"))}</button>
          <button data-mode="diagnostics" aria-pressed="${this._mode === "diagnostics"}">${esc(this.t("mode.diagnostics"))}</button>
          <button data-mode="settings" aria-pressed="${this._mode === "settings"}">${esc(this.t("mode.settings"))}</button>
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
    // The headline number is declared checks that could not run. The notes
    // about where the collection does not reach are counted next to it, not
    // inside it: they were never checks.
    const notVerified = ((d.checks || {}).unverified || []).filter((item) =>
      String(item.id || "").startsWith("chk.")
    );
    const notes = ((d.checks || {}).unverified || []).length - notVerified.length;
    const unverified = notVerified.length;

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
          }${
            a.entities_unavailable
              ? `<br>${this.t("base.offline.unavailable", {
                  n: this.num(a.entities_unavailable),
                })}`
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
          <div class="stat__note">${this.t("base.unverified.note")}${
            notes ? ` ${this.t("base.unverified.notes", { n: this.num(notes) })}` : ""
          }</div>
        </div>
      </div>

      <div>
        <h2 class="sec">${esc(this.t("base.findings"))}</h2>
        ${this.findings()}
      </div>

      <div>
        <h2 class="sec">${esc(this.t("base.checks"))}</h2>
        ${this.checksSection()}
      </div>

      ${this.historySection()}
    </div>`;
  }

  /* ── shared pieces ───────────────────────────────────────────────────── */

  /** One disclosure block. Every list in the panel that has a detail behind a
   *  summary uses this, so a line you can click looks the same everywhere.
   *  Callers pass escaped markup: the copy carries deliberate emphasis. */
  expander({ tone = "muted", title, chips = [], body, open = false }) {
    return `<details class="exp" data-tone="${tone}"${open ? " open" : ""}>
      <summary><span class="exp__t">${title}</span><span class="exp__sp"></span>${chips.join(
        ""
      )}</summary>
      <div class="exp__body">${body}</div>
    </details>`;
  }

  /** Check copy is written in checks.json, in English, and that stays the
   *  canonical text. A translation wins for display only, and when there is
   *  none the document's own words are shown rather than a key. */
  checkText(item, field) {
    const key = `${item.id}.${field}`;
    const table = I18N[this._lang] || {};
    if (table[key] !== undefined) return table[key];
    const fallback = I18N[FALLBACK_LANG] || {};
    if (fallback[key] !== undefined) return fallback[key];
    return item[field] || "";
  }

  /** The transports the local links in this scan actually use, so the second
   *  legend row names the colours on screen and no others. */
  transportsInUse() {
    const found = new Set();
    (this._data ? this._data.conduits : []).forEach((conduit) => {
      const destination = this.destination(conduit.destination_id);
      if (INTERNAL_KINDS.has(destination.kind) && conduit.protocol) {
        found.add(conduit.protocol);
      }
    });
    return [...found].sort();
  }

  /** The colour of a destination, by what it is. */
  kindColour(kind) {
    return `var(${KIND_COLOUR[kind] || "--k-unknown"})`;
  }

  /** The colour of a link. Inside the house it takes its transport's colour,
   *  outward it takes its destination's, and red is reserved for the one
   *  finding this whole tool exists to show. */
  linkColour(conduit, destination, isKey) {
    if (isKey) return "var(--alert)";
    if (INTERNAL_KINDS.has(destination.kind)) {
      const transport = String(conduit.protocol || "").replace(/[^a-z]/g, "");
      return transport
        ? `var(--t-${transport}, var(--k-local))`
        : "var(--k-local)";
    }
    return this.kindColour(destination.kind);
  }

  severityTone(severity) {
    return severity === "high" ? "alert" : severity === "medium" ? "attention" : "info";
  }

  /** One row per asset a check names, with the evidence that made it a
   *  subject. This is the answer to "who exactly", which is the only part of
   *  a finding that leads to an action. */
  subjectRows(result) {
    const d = this._data;
    const kind = result.subject_kind;
    return result.subjects
      .map((id) => {
        let name = id;
        let meta = "";
        if (kind === "device") {
          const device = d.labels.devices[id] || {};
          name = device.name || id;
          const contacted = this.contactedBy(id);
          meta =
            contacted ||
            [
              device.transport ? this.t(`transport.${device.transport}`) : "",
              device.ip,
              (d.labels.integrations[device.integration_id] || {}).title,
            ]
              .filter(Boolean)
              .join(" · ");
        } else if (kind === "integration") {
          const integration = d.labels.integrations[id] || {};
          name = integration.title || id;
          meta = [
            integration.domain,
            integration.iot_class,
            integration.endpoint,
            integration.state && integration.state !== "loaded" ? this.t("state.notLoaded") : "",
          ]
            .filter(Boolean)
            .join(" · ");
        } else if (kind === "mqtt_client") {
          meta = this.clientTrace(id);
        }
        return `<div class="exp__row"><b>${esc(name)}</b><span class="mono">${esc(meta)}</span></div>`;
      })
      .join("");
  }

  /** What is known about an MQTT client beyond its own name.
   *
   *  A client id is whatever the client called itself, so on its own it is a
   *  string a reader can do nothing with. The address is the handle: it says
   *  where on the network to look, and whether the resolver has seen that
   *  host doing anything else. */
  clientTrace(clientId) {
    const facts = (this._data || {}).mqtt || {};
    const client = (facts.clients || []).find((row) => row.client_id === clientId);
    if (!client) return this.t("mqtt.client.noAddress");
    if (!client.address) return this.t("mqtt.client.noAddress");

    // Plain text, joined rather than interpolated: the caller escapes it, and
    // a template literal here would read as markup being built by hand.
    const device = Object.values(this._data.labels.devices || {}).find(
      (row) => row.ip === client.address
    );
    if (device) return [client.address, device.name].join(" · ");

    // The resolver may have seen the same address, which at least says the
    // host is real and what it has been asking for.
    const queries = this._data.conduits
      .filter(
        (conduit) =>
          conduit.source.kind === "unknown_host" && conduit.source.id === client.address
      )
      .reduce((total, conduit) => total + (conduit.query_count || 0), 0);
    return [
      client.address,
      queries
        ? this.t("mqtt.client.seen", { n: this.num(queries) })
        : this.t("mqtt.client.unseen"),
    ].join(" · ");
  }

  /** Rows for the assets a skipped check could not look at. The entry
   *  carries ids and no kind, so each id is resolved by lookup. */
  blindRows(ids) {
    const d = this._data;
    return ids
      .map((id) => {
        const integration = d.labels.integrations[id];
        if (integration) {
          const meta = [integration.domain, integration.iot_class, integration.endpoint]
            .filter(Boolean)
            .join(" · ");
          return `<div class="exp__row"><b>${esc(integration.title || id)}</b><span class="mono">${esc(meta)}</span></div>`;
        }
        const device = d.labels.devices[id];
        if (device) {
          return `<div class="exp__row"><b>${esc(device.name || id)}</b><span class="mono">${esc(
            [device.transport ? this.t(`transport.${device.transport}`) : "", device.ip].filter(Boolean).join(" · ")
          )}</span></div>`;
        }
        return `<div class="exp__row"><b class="mono">${esc(id)}</b></div>`;
      })
      .join("");
  }

  /** Who a single device was seen resolving, and how insistently. */
  contactedBy(deviceId) {
    const byVendor = new Map();
    this._data.conduits.forEach((conduit) => {
      if (conduit.evidence !== "observed" || conduit.source.id !== deviceId) return;
      const destination = this.destination(conduit.destination_id);
      if (!PHONE_HOME.has(destination.kind)) return;
      const key = destination.vendor || destination.fqdn;
      byVendor.set(key, (byVendor.get(key) || 0) + (conduit.query_count || 0));
    });
    return [...byVendor.entries()]
      .sort((a, b) => b[1] - a[1])
      .map(([vendor, n]) => `${vendor} (${this.t("find.queries", { n: this.num(n) })})`)
      .join(", ");
  }

  /** Why an observed-side section has nothing in it. An empty list and a
   *  blind collector look identical on screen and mean opposite things. */
  observedGap() {
    const d = this._data;
    if (d.observed_available === false) return this.t("evidence.blocked.adguard");
    const c = d.correlation || {};
    if (!c.devices_correlated) return this.t("evidence.blocked.correlation");
    if (c.devices_correlated < c.devices_total) {
      return this.t("evidence.blocked.partial", {
        done: this.num(c.devices_correlated),
        total: this.num(c.devices_total),
      });
    }
    return this.t("evidence.blocked.silent");
  }

  /** The whole check run, grouped and colour coded. Passed is green, the
   *  findings take their severity's colour, and what could not run is grey
   *  on purpose: it is not an outcome and must not read like one. */
  checksSection(includeUnverified = true) {
    const checks = this._data.checks || { failed: [], passed: [], unverified: [] };

    const failed = checks.failed
      .slice()
      .sort((a, b) => SEVERITY_ORDER.indexOf(a.severity) - SEVERITY_ORDER.indexOf(b.severity))
      .map((result) => this.findingCard(result))
      .join("");

    const passed = checks.passed
      .map((result) =>
        this.expander({
          tone: "pass",
          title: esc(this.checkText(result, "title")),
          chips: [`<span class="chip">${esc(this.t("adv.checks.passed"))}</span>`],
          body: `<p>${esc(this.checkText(result, "detail") || this.t("check.passedBody"))}</p>`,
        })
      )
      .join("");

    // Ran, saw part of what it needed, found nothing there. Blue: neither the
    // green that would claim all was seen nor the grey that would claim none.
    const partial = (checks.partial || [])
      .map((result) =>
        this.expander({
          tone: "info",
          title: esc(this.checkText(result, "title")),
          chips: [
            `<span class="chip">${esc(this.t("check.partial"))}</span>`,
            `<span class="chip">${this.num((result.uninspected || []).length)}</span>`,
          ],
          body: `<p>${esc(this.t("check.partialBody"))}</p>
            <div class="exp__lab">${esc(this.t("check.blind"))}</div>
            <div class="exp__rows">${this.blindRows(result.uninspected || [])}</div>
            <div class="exp__lab">${esc(this.t("check.about"))}</div>
            <p>${esc(this.checkText(result, "detail"))}</p>`,
        })
      )
      .join("");

    // A check the engine declared but could not run, versus a note about
    // where the collection itself does not reach. Both are "not an outcome",
    // only the first belongs to the tally of declared checks.
    const isDeclaredCheck = (item) => String(item.id || "").startsWith("chk.");
    const notRun = checks.unverified.filter(isDeclaredCheck);
    const notes = checks.unverified.filter((item) => !isDeclaredCheck(item));
    // A skipped check leads with what is missing and where to get it, one
    // line per unmet precondition. The finding's own description follows as
    // context: it says what the check would look for, which is not why it
    // did not run, and showing only that was how "missing data" came to mean
    // nothing.
    const card = (check) => {
      const missing = (check.missing || []).map(
        (name) => `<p>· ${esc(this.t(`precondition.${name}`))}</p>`
      );
      const blind = this.blindRows(check.subjects || []);
      const body = missing.length
        ? `<div class="exp__lab">${esc(this.t("check.missing"))}</div>${missing.join("")}
           ${
             blind
               ? `<div class="exp__lab">${esc(this.t("check.blind"))}</div>
                  <div class="exp__rows">${blind}</div>`
               : ""
           }
           <div class="exp__lab">${esc(this.t("check.about"))}</div>
           <p>${esc(this.checkText(check, "detail"))}</p>`
        : `<div class="exp__lab">${esc(this.t("check.why"))}</div>
           <p>${esc(this.checkText(check, "detail"))}</p>`;
      return this.expander({
        tone: "muted",
        title: esc(this.checkText(check, "title")),
        chips: [`<span class="chip">${esc(this.t(`reason.${check.reason}`))}</span>`],
        body,
      });
    };

    const group = (label, dot, body, n) =>
      `<div class="exp__lab"><i style="background:${dot}"></i>${esc(label)} · ${n}</div>` +
      (body || `<p class="hint" style="margin:0 0 10px">${esc(this.t("check.none"))}</p>`);

    return `<p class="page-sub" style="margin:0 0 10px">${esc(this.t("base.checks.lead"))}</p>
      <div class="tally">
        <span><i style="background:var(--k-local)"></i><b>${this.num(checks.passed.length)}</b> ${esc(
          this.t("base.checks.tally.passed")
        )}</span>
        <span><i style="background:var(--alert)"></i><b>${this.num(checks.failed.length)}</b> ${esc(
          this.t("base.checks.tally.failed")
        )}</span>
        <span><i style="background:var(--accent)"></i><b>${this.num((checks.partial || []).length)}</b> ${esc(
          this.t("base.checks.tally.partial")
        )}</span>
        <span><i style="background:var(--ink-mute)"></i><b>${this.num(
          notRun.length
        )}</b> ${esc(this.t("base.checks.tally.unverified"))}</span>
        <span class="hint">${esc(this.t("check.expandHint"))}</span>
      </div>
      <p class="hint" style="margin:0 0 14px">${esc(
        this.t("base.checks.total", {
          total: this.num(checks.passed.length + (checks.partial || []).length + checks.failed.length + notRun.length),
          passed: this.num(checks.passed.length),
          partial: this.num((checks.partial || []).length),
          failed: this.num(checks.failed.length),
          notrun: this.num(notRun.length),
          notes: this.num(notes.length),
        })
      )}</p>
      ${group(this.t("checks.group.failed"), "var(--alert)", failed, checks.failed.length)}
      ${group(this.t("checks.group.partial"), "var(--accent)", partial, (checks.partial || []).length)}
      ${group(this.t("checks.group.passed"), "var(--k-local)", passed, checks.passed.length)}
      ${
        includeUnverified
          ? group(
              this.t("checks.group.unverified"),
              "var(--ink-mute)",
              notRun.map(card).join(""),
              notRun.length
            ) +
            group(
              this.t("checks.group.notes"),
              "var(--ink-mute)",
              notes.map(card).join(""),
              notes.length
            )
          : ""
      }`;
  }

  observedBanner() {
    if (!this._data || this._data.observed_available !== false) return "";
    const reason = this._data.observed_error || this.t("banner.noAdguard");
    return `<div class="banner">${this.t("banner.declared", { reason: esc(reason) })}</div>`;
  }

  findingCard(result) {
    const level = this.t(`severity.${result.severity}`);
    const remediation = this.checkText(result, "remediation");
    const rows = this.subjectRows(result);
    return this.expander({
      tone: SEVERITY_TONE[result.severity] || "info",
      title: esc(this.checkText(result, "title")),
      chips: [
        `<span class="chip">${esc(this.t("find.severity", { level }))}</span>`,
        `<span class="chip">${this.num(result.subjects.length)}</span>`,
      ],
      body: `<p>${esc(this.checkText(result, "detail"))}</p>
        ${
          rows
            ? `<div class="exp__lab">${esc(this.t("check.subjects"))}</div>
               <div class="exp__rows">${rows}</div>`
            : ""
        }
        ${remediation ? `<div class="exp__do"><strong>${esc(this.t("check.do"))}.</strong> ${esc(
          remediation
        )}</div>` : ""}`,
    });
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
      cards.push(
        this.expander({
          tone: "attention",
          title: esc(this.t("find.offline.title", { vendor: losses[0].vendor })),
          chips: [`<span class="chip">${this.num(losses.length)}</span>`],
          body: `<p>${esc(this.t("find.offline.body", { list }))}</p>
            <div class="exp__rows">${losses
              .map(
                (l) => `<div class="exp__row"><b>${esc(l.vendor)}</b>
                  <span class="mono">${esc(
                    this.t("find.offline.entities", { n: l.entities, vendor: l.vendor })
                  )}</span></div>`
              )
              .join("")}</div>
            <div class="exp__do">${this.t("find.offline.do")}</div>`,
        })
      );
    }

    if (!cards.length) {
      cards.push(
        this.expander({
          tone: "info",
          title: esc(this.t("find.clean.title")),
          body: `<p>${this.t("find.clean.body", {
            passed: this.num(checks.passed.length),
            unverified: this.num(checks.unverified.length),
          })}</p>
          <div class="exp__lab">${esc(this.t("evidence.how"))}</div>
          <p>${this.t("evidence.how.body")}</p>
          <p>${esc(this.observedGap())}</p>`,
        })
      );
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
        ${this.expander({
          tone: "info",
          title: esc(this.t("evidence.how")),
          body: `<p>${this.t("evidence.how.body")}</p><p>${esc(this.observedGap())}</p>`,
        })}
      </div>

      <div>
        <h2 class="sec">${esc(this.t("adv.flows"))}</h2>
        <div class="card">
          <div class="card__head">
            <div class="legend">
              ${LEGEND_KINDS.map(
                ([key, variable]) =>
                  `<span><span class="dot" style="background:var(${variable})"></span>${esc(
                    this.t(`legend.${key}`)
                  )}</span>`
              ).join("")}
              <span><span class="dot" style="background:var(--alert)"></span>${esc(
                this.t("legend.key")
              )}</span>
            </div>
            <div class="legend">
              <span class="hint">${esc(this.t("legend.inside"))}</span>
              ${this.transportsInUse()
                .map(
                  (transport) =>
                    `<span><span class="dot" style="background:var(--t-${transport.replace(
                      /[^a-z]/g,
                      ""
                    )}, var(--k-local))"></span>${esc(this.t(`transport.${transport}`))}</span>`
                )
                .join("")}
              <span class="hint">${esc(this.t("legend.solid"))}</span>
            </div>
          </div>
          <div class="scroll-x"><svg class="graph" viewBox="0 0 980 560" role="img"
            aria-label="${esc(this.t("adv.flows"))}"></svg></div>
          ${
            d.conduits.length
              ? ""
              : `<p class="hint" style="padding:0 16px 14px;margin:0;max-width:80ch">${esc(
                  this.t("flows.declaredNote")
                )}</p>`
          }
        </div>
      </div>

      <div>
        <h2 class="sec">${esc(this.t("adv.inventory"))} · ${
          Object.keys(d.labels.integrations || {}).length
        }</h2>
        <p class="page-sub" style="margin:0 0 12px">${esc(this.t("adv.inventory.lead"))}</p>
        <div data-inventory>${this.inventory()}</div>
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
            .map((check) =>
              this.expander({
                tone: "muted",
                title: esc(this.checkText(check, "title")),
                chips: [`<span class="chip">${esc(this.t(`reason.${check.reason}`))}</span>`],
                body: `<div class="exp__lab">${esc(this.t("check.why"))}</div>
                  <p>${esc(this.checkText(check, "detail"))}</p>`,
              })
            )
            .join("") ||
          `<div class="check"><div class="check__t">${esc(this.t("adv.unverified.none"))}</div></div>`
        }
      </div>
    </div>`;
  }

  /** Every config entry with what the registry says about it. Nothing here
   *  is a judgement and nothing is probed: it is the declared side, laid out
   *  so it can be read rather than inferred from the map. */
  /** Filters over the inventory. Each one answers a question somebody
   *  actually asks of a list this long: which are broken, which are cloud,
   *  which did I install myself, which one is called something like this. */
  inventoryFilters() {
    const counts = this.inventoryCounts();
    const chip = (id, label, n) =>
      `<button class="chip chip--filter" data-invfilter="${id}"
         aria-pressed="${(this._invFilter || "all") === id}">${esc(label)}
         <span class="mono">${this.num(n)}</span></button>`;
    return `<div class="filters">
      <input type="search" data-action="inv-search" spellcheck="false"
             placeholder="${esc(this.t("filter.search"))}" value="${esc(this._invQuery || "")}">
      ${chip("all", this.t("filter.all"), counts.all)}
      ${chip("notLoaded", this.t("filter.notLoaded"), counts.notLoaded)}
      ${chip("loaded", this.t("filter.loaded"), counts.loaded)}
      ${chip("cloud", this.t("filter.cloud"), counts.cloud)}
      ${chip("custom", this.t("filter.custom"), counts.custom)}
      ${chip("endpoint", this.t("filter.withEndpoint"), counts.endpoint)}
    </div>`;
  }

  inventoryCounts() {
    const all = Object.values((this._data && this._data.labels.integrations) || {});
    const isCloud = (i) => String(i.iot_class || "").startsWith("cloud");
    return {
      all: all.length,
      loaded: all.filter((i) => !i.state || i.state === "loaded").length,
      notLoaded: all.filter((i) => i.state && i.state !== "loaded").length,
      cloud: all.filter(isCloud).length,
      custom: all.filter((i) => i.is_built_in === false).length,
      endpoint: all.filter((i) => i.endpoint).length,
    };
  }

  /** Whether one entry survives the search box and the active chip. */
  inventoryMatches(id, integration) {
    const filter = this._invFilter || "all";
    const loaded = !integration.state || integration.state === "loaded";
    if (filter === "loaded" && !loaded) return false;
    if (filter === "notLoaded" && loaded) return false;
    if (filter === "cloud" && !String(integration.iot_class || "").startsWith("cloud")) return false;
    if (filter === "custom" && integration.is_built_in !== false) return false;
    if (filter === "endpoint" && !integration.endpoint) return false;

    const query = (this._invQuery || "").trim().toLowerCase();
    if (!query) return true;
    return [integration.title, integration.domain, integration.endpoint, integration.iot_class, id]
      .filter(Boolean)
      .some((field) => String(field).toLowerCase().includes(query));
  }

  inventory() {
    const d = this._data;
    const integrations = d.labels.integrations || {};
    const devices = Object.entries(d.labels.devices || {});

    const rows = Object.entries(integrations)
      .filter(([id, integration]) => this.inventoryMatches(id, integration))
      .map(([id, integration]) => {
        const own = devices.filter(([, device]) => device.integration_id === id);
        const origins = [...new Set(own.map(([, device]) => device.origin).filter(Boolean))];
        const transports = [...new Set(own.map(([, device]) => device.transport))];
        const notLoaded = integration.state && integration.state !== "loaded";
        const row = (label, value) =>
          `<div class="exp__row"><b>${esc(label)}</b><span class="mono">${esc(value)}</span></div>`;

        return this.expander({
          tone: notLoaded ? "alert" : "info",
          title: esc(integration.title || id),
          chips: [
            `<span class="chip">${esc(integration.domain || "")}</span>`,
            notLoaded
              ? `<span class="chip chip--alert">${esc(this.t("state.notLoaded"))}</span>`
              : "",
            `<span class="chip">${this.num(own.length)}</span>`,
          ].filter(Boolean),
          body: `<div class="exp__rows">
            ${row(this.t("inv.class"), integration.iot_class || this.t("inv.none"))}
            ${row(
              this.t("inv.role"),
              this.t(`role.${integration.role || "unknown"}`) || this.t("inv.none")
            )}
            ${row(this.t("inv.state"), integration.state || "-")}
            ${row(this.t("inv.endpoint"), integration.endpoint || this.t("inv.none"))}
            ${row(
              this.t("inv.source"),
              integration.is_built_in === false
                ? this.t("inv.source.custom")
                : this.t("inv.source.builtin")
            )}
            ${row(
              this.t("col.transport"),
              transports.map((t) => this.t(`transport.${t}`)).join(", ") || "-"
            )}
            ${origins.length ? row(this.t("inv.origin"), origins.join(", ")) : ""}
            ${row(
              this.t("col.devices"),
              this.t("inv.counts", {
                devices: this.num(own.length),
                entities: this.num(integration.entity_count || 0),
              })
            )}
          </div>`,
        });
      })
      .join("");

    const shown = Object.entries(integrations).filter(([id, integration]) =>
      this.inventoryMatches(id, integration)
    ).length;
    return (
      this.inventoryFilters() +
      `<p class="hint" style="margin:0 0 10px">${esc(
        this.t("filter.count", {
          shown: this.num(shown),
          total: this.num(Object.keys(integrations).length),
        })
      )}</p>` +
      (rows || `<p class="status">${esc(this.t("filter.none"))}</p>`)
    );
  }

  checkList() {
    return this.checksSection(false);
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
          <td><span class="chip" style="color:${this.kindColour(destination.kind)}">
            <span class="dot" style="background:currentColor"></span>${esc(
              this.t(`kind.${destination.kind}`)
            )}</span></td>
          <td class="mono">${
            conduit.protocol
              ? `<span style="color:${this.linkColour(conduit, destination, false)}">${esc(
                  conduit.protocol
                )}</span>`
              : "-"
          }</td>
          <td><span class="ev ev--${esc(conduit.evidence)}">${esc(this.t(`evidence.${conduit.evidence}`))}</span></td>
          <td class="num">${conduit.query_count == null ? "-" : this.num(conduit.query_count)}</td>
          <td>${conduit.filter_status ? esc(conduit.filter_status) : "-"}</td>
        </tr>`;
      })
      .join("");

    return `<table class="data">
      <thead><tr><th>${esc(this.t("table.origin"))}</th><th>${esc(this.t("table.destination"))}</th>
      <th>${esc(this.t("table.kind"))}</th><th>${esc(this.t("table.protocol"))}</th>
      <th>${esc(this.t("table.evidence"))}</th>
      <th class="num">${esc(this.t("table.queries"))}</th><th>${esc(this.t("table.filter"))}</th></tr></thead>
      <tbody>${rows || `<tr><td colspan="7">${esc(this.t("adv.conduits.none"))}</td></tr>`}</tbody>
    </table>`;
  }

  /* ── map ─────────────────────────────────────────────────────────────── */

  /** Devices grouped by transport, and inside that by integration. */
  topology() {
    const devices = (this._data && this._data.labels.devices) || {};
    const byTransport = new Map();
    const children = new Map();

    Object.entries(devices).forEach(([id, device]) => {
      const transport = device.transport || "unknown";
      if (!byTransport.has(transport)) byTransport.set(transport, new Map());
      const integrations = byTransport.get(transport);
      const key = device.integration_id || "?";
      if (!integrations.has(key)) integrations.set(key, []);
      integrations.get(key).push({ id, ...device });

      if (device.via_device_id) {
        if (!children.has(device.via_device_id)) children.set(device.via_device_id, []);
        children.get(device.via_device_id).push(id);
      }
    });

    // Busiest transport first: that is the shape of the install.
    const groups = [...byTransport.entries()]
      .map(([transport, integrations]) => ({
        transport,
        total: [...integrations.values()].reduce((sum, list) => sum + list.length, 0),
        integrations: [...integrations.entries()]
          .map(([id, list]) => {
            const devices = list.slice().sort(byName);
            // An MQTT entry can be fed by Zigbee2MQTT and a SwitchBot bridge
            // at once: the integration is the bus, these are its sources.
            const sources = new Map();
            devices.forEach((device) => {
              const origin = device.origin || null;
              if (!sources.has(origin)) sources.set(origin, []);
              sources.get(origin).push(device);
            });
            return {
              id,
              devices,
              sources: [...sources.entries()]
                .map(([origin, list2]) => ({ origin, devices: list2 }))
                .sort((a, b) => b.devices.length - a.devices.length),
            };
          })
          .sort((a, b) => b.devices.length - a.devices.length),
      }))
      .sort((a, b) => b.total - a.total);

    // A hub owned by another integration is a real, declared link between
    // the two: it is how Zigbee2MQTT hangs off a coordinator entry, or a
    // Bluetooth proxy off ESPHome.
    const bridges = new Map();
    const byDomain = new Map(
      Object.entries((this._data && this._data.labels.integrations) || {}).map(
        ([entryId, integration]) => [integration.domain, entryId]
      )
    );
    Object.entries(devices).forEach(([id, device]) => {
      const parent = device.via_device_id && devices[device.via_device_id];
      if (parent && parent.integration_id !== device.integration_id) {
        const key = `${parent.integration_id}>${device.integration_id}`;
        bridges.set(key, (bridges.get(key) || 0) + 1);
      }
      // The origin names a system that is itself a configured integration:
      // the same devices are reachable two ways, which is a link worth
      // drawing even though no via_device declares it.
      const twin = device.origin && byDomain.get(device.origin);
      if (twin && twin !== device.integration_id) {
        const key = `${twin}>${device.integration_id}`;
        bridges.set(key, (bridges.get(key) || 0) + 1);
      }
    });

    return { groups, children, bridges, total: Object.keys(devices).length };
  }

  viewMap() {
    const { total } = this.topology();
    if (!total) {
      return `<div class="stack"><div>
        <h1 class="page">${esc(this.t("map.title"))}</h1>
        <p class="page-sub">${esc(this.t("map.empty"))}</p>
      </div></div>`;
    }
    return `<div class="stack">
      <div>
        <h1 class="page">${esc(this.t("map.title"))}</h1>
        <p class="page-sub">${esc(this.t("map.lead"))}</p>
      </div>

      <div class="mapwrap">
        <div class="maptools">
          <input type="search" data-action="map-search" placeholder="${esc(this.t("map.search"))}"
                 value="${esc(this._mapQuery || "")}" spellcheck="false">
          <span class="detail">
            <button class="btn btn--ghost" data-action="map-less"
                    title="${esc(this.t("map.detail.less"))}" ${(this._detail || 2) <= 1 ? "disabled" : ""}>&minus;</button>
            <span class="detail__level">${esc(this.t("map.detail"))}: ${esc(
              this.t(`map.detail.${this._detail || 2}`)
            )}</span>
            <button class="btn btn--ghost" data-action="map-more"
                    title="${esc(this.t("map.detail.more"))}" ${(this._detail || 2) >= 3 ? "disabled" : ""}>+</button>
          </span>
          <button class="btn btn--ghost" data-action="map-reset">${esc(this.t("map.reset"))}</button>
          <span class="hint">${esc(this.t("map.hint"))} ${esc(this.t("map.zoomHint"))} ${esc(
            this.t("map.click.integration")
          )}</span>
        </div>
        <div class="maptools mapfilters">
          <span class="hint">${esc(this.t("map.filters"))}</span>
          <button class="chip chip--filter" data-scope="all"
                  aria-pressed="${!this._scope}">${esc(this.t("map.all"))}</button>
          ${this.topology()
            .groups.map(
              (group) => `<button class="chip chip--filter" data-scope="t:${esc(group.transport)}"
                 aria-pressed="${
                   this._scope && this._scope.kind === "transport" && this._scope.id === group.transport
                 }"
                 style="--chip:var(--t-${group.transport.replace(/[^a-z]/g, "") || "unknown"}, var(--t-unknown))">
                 <span class="chip__dot" style="background:var(--chip)"></span>${esc(
                   this.t(`transport.${group.transport}`)
                 )} <span class="mono">${group.total}</span></button>`
            )
            .join("")}
          ${this.roleChips()}
          ${this.scopeBadge()}
        </div>
        <svg class="map" role="img" aria-label="${esc(this.t("map.title"))}"></svg>
        <div class="maplegend">
          <span><span class="swatch" style="background:var(--accent)"></span>${esc(this.t("map.legend.core"))}</span>
          <span><span class="swatch swatch--round" style="background:var(--t-zigbee)"></span>${esc(this.t("map.legend.transport"))}</span>
          <span><span class="swatch swatch--round" style="background:var(--ink-mute)"></span>${esc(this.t("map.legend.integration"))}</span>
          <span><span class="swatch swatch--round" style="background:var(--ink-soft);width:6px;height:6px"></span>${esc(this.t("map.legend.device"))}</span>
          <span><span class="swatch" style="background:none;border:2px dashed var(--ink-soft);border-radius:50%"></span>${esc(this.t("map.legend.origin"))}</span>
          <span><span class="swatch" style="background:none;border:2px solid var(--ink-soft);border-radius:50%"></span>${esc(this.t("map.legend.hub"))}</span>
          <span><span class="swatch" style="height:0;width:16px;border-top:2px dashed var(--ink-mute);border-radius:0"></span>${esc(this.t("map.legend.bridge"))}</span>
        </div>
      </div>

      ${this.meshSection()}
      ${this.mqttClientSection()}
      ${this.hubSection()}

      <div>
        <h2 class="sec">${esc(this.t("map.fullList"))}</h2>
        ${this.topology().groups.map((group) => this.transportGroup(group, total)).join("")}
      </div>
    </div>`;
  }

  /** Roles present in this install, as filter chips. */
  roleChips() {
    const integrations = (this._data && this._data.labels.integrations) || {};
    const roles = [...new Set(Object.values(integrations).map((i) => i.role))].filter(
      (role) => role && role !== "unknown"
    );
    if (!roles.length) return "";
    return (
      `<span class="hint">${esc(this.t("map.roles"))}</span>` +
      roles
        .map(
          (role) => `<button class="chip chip--filter" data-scope="r:${esc(role)}"
             aria-pressed="${this._scope && this._scope.kind === "role" && this._scope.id === role}"
             >${esc(this.t(`role.${role}`))}</button>`
        )
        .join("")
    );
  }

  scopeBadge() {
    const scope = this._scope;
    if (!scope) return "";
    const name =
      scope.kind === "transport"
        ? this.t(`transport.${scope.id}`)
        : scope.kind === "role"
          ? this.t(`role.${scope.id}`)
          : (this._data.labels.integrations[scope.id] || {}).title || scope.id;
    const label = this.t(`map.scope.${scope.kind}`, { name });
    return `<span class="scopebadge">${esc(label)}
      <button data-scope="all">${esc(this.t("map.clearScope"))}</button></span>`;
  }

  /** Every client the broker named, and what could be made of each.
   *
   *  Drawn whether the check passed, failed or could not run, because "which
   *  ones could you not account for" is a question with an answer in all
   *  three cases, and when the answer is "none of them, and here is why" that
   *  is the most useful thing the panel can say. */
  mqttClientSection() {
    const facts = (this._data || {}).mqtt;
    if (!facts) return "";

    const clients = facts.clients || [];
    const matched = clients.filter((client) => client.matched);
    const unmatched = clients.filter((client) => !client.matched);
    const row = (client) =>
      `<div class="exp__row"><b>${esc(client.client_id)}</b>
        <span class="mono">${esc(
          client.matched
            ? [client.address, client.matched].filter(Boolean).join(" · ")
            : this.clientTrace(client.client_id)
        )}</span></div>`;

    const body = facts.available
      ? `${
          unmatched.length
            ? `<div class="exp__lab"><i style="background:var(--alert)"></i>${esc(
                this.t("mqtt.clients.unmatched")
              )} · ${this.num(unmatched.length)}</div>
               <div class="exp__rows">${unmatched.map(row).join("")}</div>`
            : ""
        }
        ${
          matched.length
            ? `<div class="exp__lab"><i style="background:var(--k-local)"></i>${esc(
                this.t("mqtt.clients.matched")
              )} · ${this.num(matched.length)}</div>
               <div class="exp__rows">${matched.map(row).join("")}</div>`
            : ""
        }`
      : `<p>${esc(this.t("mqtt.clients.why", { reason: facts.error || "-" }))}</p>
         <p>${esc(this.t("mqtt.clients.emqx5"))}</p>`;

    return `<div>
      <h2 class="sec">${esc(this.t("mqtt.clients.title"))}${
        facts.available ? ` · ${this.num(clients.length)}` : ""
      }</h2>
      <p class="page-sub" style="margin-bottom:12px">${esc(this.t("mqtt.clients.lead"))}</p>
      ${this.expander({
        tone: facts.available ? (unmatched.length ? "alert" : "pass") : "muted",
        title: esc(
          facts.available
            ? this.t("mqtt.state.ok", {
                clients: this.num(clients.length),
                unmatched: this.num(unmatched.length),
              })
            : this.t("mqtt.clients.none")
        ),
        chips: [
          `<span class="chip">${esc(
            this.t(`mqtt.route.${facts.route || "session"}`)
          )}</span>`,
        ],
        open: !facts.available || unmatched.length > 0,
        body,
      })}
    </div>`;
  }

  /** The Zigbee network as its coordinator reports it. Absent entirely when
   *  no coordinator answered, because an empty panel would read as a network
   *  with nothing in it. */
  meshSection() {
    const zigbee = (this._data || {}).zigbee;
    if (!zigbee || !zigbee.available) return "";
    return `<div>
      <h2 class="sec">${esc(this.t("mesh.title"))}</h2>
      <p class="page-sub" style="margin-bottom:12px">${esc(this.t("mesh.lead"))}</p>
      <div class="panel-card"><dl class="kv">
        <dt>${esc(this.t("mesh.nodes"))}</dt><dd class="mono">${this.num(zigbee.nodes)}</dd>
        <dt>${esc(this.t("mesh.routers"))}</dt><dd class="mono">${this.num(zigbee.routers)}</dd>
        <dt>${esc(this.t("mesh.endDevices"))}</dt><dd class="mono">${this.num(zigbee.end_devices)}</dd>
        ${
          zigbee.channel
            ? `<dt>${esc(this.t("mesh.channel"))}</dt><dd class="mono">${this.num(zigbee.channel)}</dd>`
            : ""
        }
        ${
          zigbee.permit_join != null
            ? `<dt>${esc(this.t("mesh.permitJoin"))}</dt>
               <dd>${
                 zigbee.permit_join
                   ? `<span class="chip chip--alert">${esc(this.t("mesh.permitJoin.on"))}</span>`
                   : esc(this.t("mesh.permitJoin.off"))
               }</dd>`
            : ""
        }
        ${
          zigbee.version
            ? `<dt>${esc(this.t("mesh.version"))}</dt><dd class="mono">${esc(zigbee.version)}</dd>`
            : ""
        }
      </dl></div>
    </div>`;
  }

  hubSection() {
    const d = this._data;
    const { children } = this.topology();
    const hubs = [...children.entries()]
      .map(([id, list]) => ({ id, count: list.length }))
      .sort((a, b) => b.count - a.count)
      .slice(0, 25);

    return `<div>
      <h2 class="sec">${esc(this.t("map.hubs"))}</h2>
      <p class="page-sub" style="margin-bottom:12px">${esc(this.t("map.hubs.lead"))}</p>
      <div class="panel-card">
        ${
          hubs.length
            ? hubs
                .map((hub) => {
                  const device = d.labels.devices[hub.id] || {};
                  const integration = d.labels.integrations[device.integration_id] || {};
                  return `<div class="hub">
                    <div>
                      <div>${esc(device.name || hub.id)}</div>
                      <div class="hub__meta mono">${esc(
                        [integration.domain, device.transport, device.ip].filter(Boolean).join(" · ")
                      )}</div>
                    </div>
                    <span class="chip">${esc(this.t("map.hub.children", { n: hub.count }))}</span>
                  </div>`;
                })
                .join("")
            : `<p class="status">${esc(this.t("map.noHubs"))}</p>`
        }
      </div>
    </div>`;
  }

  /* ── radial layout ───────────────────────────────────────────────────────
   * Deterministic on purpose, not a force simulation: the same house always
   * produces the same picture, which is the only way two people can talk
   * about it. The angular width of a branch is its share of the devices, so
   * the shape of the drawing is the shape of the install.
   */

  mapLayout(stretch = 1) {
    const detail = this._detail || 2;
    const d = this._data;
    const { groups: allGroups, children, bridges, total } = this.topology();
    const query = (this._mapQuery || "").trim().toLowerCase();
    const scope = this._scope || null;

    // A filter removes branches rather than dimming them: the question is
    // "show me only this", and a dimmed hairball still reads as a hairball.
    let groups = allGroups;
    if (scope && scope.kind === "transport") {
      groups = allGroups.filter((group) => group.transport === scope.id);
    } else if (scope && scope.kind === "role") {
      const wanted = (entryId) =>
        ((d.labels.integrations[entryId] || {}).role || "unknown") === scope.id;
      groups = allGroups
        .map((group) => ({
          ...group,
          integrations: group.integrations.filter((entry) => wanted(entry.id)),
        }))
        .filter((group) => group.integrations.length);
    } else if (scope && scope.kind === "integration") {
      groups = allGroups
        .filter((group) => group.integrations.some((entry) => entry.id === scope.id))
        .map((group) => ({
          ...group,
          integrations: group.integrations.filter((entry) => entry.id === scope.id),
        }));
    }

    const matches = (text) => Boolean(query) && String(text || "").toLowerCase().includes(query);

    const nodes = [];
    const links = [];
    const CX = 0;
    const CY = 0;
    const R_TRANSPORT = 170;
    const R_INTEGRATION = 300;
    const R_ORIGIN = 385;
    const R_DEVICE = 480;
    const MAX_DEVICES = (this._detail || 2) >= 3 ? 24 : 60;

    nodes.push({
      id: "core", kind: "core", x: CX, y: CY, label: "Home Assistant",
      colour: "var(--accent)", angle: 0,
    });

    // Angles are allocated by weight, decided at the leaf level. A collapsed
    // integration takes one slot plus a little for its size; an open one takes
    // a slot per device it shows. So opening a branch is what gives it room,
    // and the rest of the circle makes way instead of being squashed.
    const MIN_OPEN_SLOTS = 6;
    const plan = groups.map((group) => {
      const integrations = detail < 2 ? [] : group.integrations.map((entry) => {
        const deviceMatch = entry.devices.some((device) => matches(device.name));
        const integration = d.labels.integrations[entry.id] || {};
        // Level 3 opens every branch; below that, only what was clicked or
        // what the search matched.
        const isolated = Boolean(scope && scope.kind === "integration" && scope.id === entry.id);
        const open = isolated || detail >= 3 || (Boolean(query) && deviceMatch);
        // With one integration to itself there is room for many more of them.
        const budget = isolated ? 200 : MAX_DEVICES;
        // A device query filters rather than dims, so what is left is the answer.
        const pool = query ? entry.devices.filter((device) => matches(device.name) || matches(device.area)) : entry.devices;
        const shown = open ? pool.slice(0, budget) : [];
        return {
          entry,
          integration,
          open,
          shown,
          deviceMatch,
          pool,
          budget,
          weight: open
            ? Math.max(MIN_OPEN_SLOTS, shown.length)
            : 1 + Math.sqrt(entry.devices.length) / 3,
        };
      });
      const weight = integrations.reduce((sum, item) => sum + item.weight, 0);
      return { group, integrations, weight: Math.max(weight, 1) };
    });

    const totalWeight = plan.reduce((sum, item) => sum + item.weight, 0) || 1;

    let cursor = -Math.PI / 2;
    plan.forEach(({ group, integrations, weight }) => {
      const span = (weight / totalWeight) * Math.PI * 2;
      const mid = cursor + span / 2;
      const colour = `var(--t-${group.transport.replace(/[^a-z]/g, "") || "unknown"}, var(--t-unknown))`;

      const tNode = {
        id: `t:${group.transport}`, kind: "transport", angle: mid,
        x: CX + Math.cos(mid) * R_TRANSPORT * stretch, y: CY + Math.sin(mid) * R_TRANSPORT,
        rx: R_TRANSPORT * stretch, ry: R_TRANSPORT, pad: 42,
        label: this.t(`transport.${group.transport}`),
        sub: String(group.total), colour,
        hit: matches(this.t(`transport.${group.transport}`)),
      };
      nodes.push(tNode);
      links.push({ from: "core", to: tNode.id, colour, width: 1 + Math.sqrt(group.total) / 3 });

      let inner = cursor;
      integrations.forEach((item) => {
        const { entry, integration, open, shown, budget } = item;
        const iSpan = span * (item.weight / weight);
        const iMid = inner + iSpan / 2;
        inner += iSpan;

        const label = integration.title || entry.id;
        const iNode = {
          id: `i:${entry.id}`, kind: "integration", angle: iMid,
          x: CX + Math.cos(iMid) * R_INTEGRATION * stretch,
          y: CY + Math.sin(iMid) * R_INTEGRATION,
          rx: R_INTEGRATION * stretch, ry: R_INTEGRATION, pad: 30,
          label,
          // The entry title is whatever Home Assistant called it when it was
          // set up, and it goes stale: an entry created from the Mosquitto
          // add-on keeps saying Mosquitto after it is pointed at EMQX. The
          // address it declares is the thing that is actually true.
          sub: [integration.domain, integration.endpoint].filter(Boolean).join(" · "),
          colour,
          count: entry.devices.length, open, ref: entry.id,
          hit:
            matches(label) ||
            matches(integration.domain) ||
            matches(integration.endpoint) ||
            item.deviceMatch,
        };
        nodes.push(iNode);
        links.push({
          from: tNode.id, to: iNode.id, colour,
          width: 0.8 + Math.sqrt(entry.devices.length) / 4,
        });

        if (!open) return;

        // When the integration is fed by something other than itself, the
        // sources get their own ring: that is the thing worth seeing. Built
        // from the filtered pool, so a search narrows the sources too.
        const bucketed = new Map();
        item.pool.forEach((device) => {
          const origin = device.origin || null;
          if (!bucketed.has(origin)) bucketed.set(origin, []);
          bucketed.get(origin).push(device);
        });
        const buckets = [...bucketed.entries()]
          .map(([origin, list]) => ({ origin, devices: list }))
          .sort((a, b) => b.devices.length - a.devices.length);
        const useOrigins = buckets.some((bucket) => bucket.origin);

        let bucketCursor = iMid - iSpan / 2;
        const totalInBuckets = buckets.reduce((sum, b) => sum + b.devices.length, 0) || 1;
        let drawn = 0;

        buckets.forEach((bucket) => {
          const bSpan = iSpan * (bucket.devices.length / totalInBuckets);
          const bMid = bucketCursor + bSpan / 2;
          bucketCursor += bSpan;

          let parentId = iNode.id;
          if (useOrigins) {
            const originId = `o:${entry.id}:${bucket.origin || "own"}`;
            nodes.push({
              id: originId, kind: "origin", angle: bMid,
              x: CX + Math.cos(bMid) * R_ORIGIN * stretch,
              y: CY + Math.sin(bMid) * R_ORIGIN,
              rx: R_ORIGIN * stretch, ry: R_ORIGIN, pad: 24,
              label: bucket.origin || this.t("map.origin.own"),
              sub: String(bucket.devices.length), colour,
              hit: matches(bucket.origin),
            });
            links.push({ from: iNode.id, to: originId, colour, width: 0.9 });
            parentId = originId;
          }

          const remaining = Math.max(0, budget - drawn);
          const bucketShown = bucket.devices.slice(0, remaining);
          drawn += bucketShown.length;
          const step = bSpan / Math.max(bucketShown.length, 1);
          bucketShown.forEach((device, position) => {
            const angle = bMid - bSpan / 2 + step * (position + 0.5);
            nodes.push({
              id: `d:${device.id}`, kind: "device", angle,
              ref: device.id,
              x: CX + Math.cos(angle) * R_DEVICE * stretch,
              y: CY + Math.sin(angle) * R_DEVICE,
              rx: R_DEVICE * stretch, ry: R_DEVICE, pad: 13,
              label: device.name || device.id,
              sub: device.area || device.ip || "",
              colour, isHub: children.has(device.id),
              hit: matches(device.name) || matches(device.area),
            });
            links.push({ from: parentId, to: `d:${device.id}`, colour, width: 0.7 });
          });
        });

        if (item.pool.length > drawn) {
          const angle = iMid + iSpan / 2;
          nodes.push({
            id: `more:${entry.id}`, kind: "more", angle,
            x: CX + Math.cos(angle) * R_DEVICE * stretch,
            y: CY + Math.sin(angle) * R_DEVICE,
            rx: R_DEVICE * stretch, ry: R_DEVICE, pad: 22,
            label: this.t("map.truncated", { n: item.pool.length - drawn }),
            colour, sub: "",
          });
        }
      });

      cursor += span;
    });

    // Declared links that cross an integration boundary.
    const present = new Set(nodes.map((node) => node.id));
    (bridges || new Map()).forEach((count, key) => {
      const [from, to] = key.split(">");
      if (!present.has(`i:${from}`) || !present.has(`i:${to}`)) return;
      links.push({
        from: `i:${from}`, to: `i:${to}`, colour: "var(--ink-mute)",
        width: 0.8 + Math.sqrt(count) / 3, bridge: true,
      });
    });

    return { nodes, links, query, hits: nodes.filter((n) => n.hit).length };
  }

  /* ── force layout ────────────────────────────────────────────────────────
   * The radial layout above is the starting position; from there the nodes
   * settle under springs and repulsion, the way Obsidian's graph does. Rest
   * lengths shorten with depth, so a leaf hugs its aggregator and the
   * aggregator sits close to its primary node: each integration becomes a
   * tight tuft with a halo of devices, and the trunks stay long.
   *
   * Determinism is kept as far as a simulation allows: the seed is the same
   * radial picture every time, the sway is driven by a seeded generator, and
   * the settle runs a fixed schedule. The same house still gives the same
   * shape, only breathing.
   */

  mapSeeded(seed = 1789) {
    // mulberry32: small, fast, and the same sequence every load.
    let a = seed >>> 0;
    return () => {
      a = (a + 0x6d2b79f5) >>> 0;
      let t = a;
      t = Math.imul(t ^ (t >>> 15), t | 1);
      t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  mapTier(node) {
    return node.kind === "core" ? 0
      : node.kind === "transport" ? 1
      : node.kind === "integration" ? 2
      : node.kind === "origin" ? 3 : 4;
  }

  mapRadius(node) {
    return node.kind === "core" ? 26
      : node.kind === "transport" ? 15
      : node.kind === "integration" ? 10
      : node.kind === "origin" ? 8 : 6;
  }

  /** Build the simulation state from a layout. Called once per structural
   *  redraw; the ticker mutates it in place. */
  mapSimulation(nodes, links) {
    const byId = new Map(nodes.map((node) => [node.id, node]));
    const random = this.mapSeeded();
    nodes.forEach((node) => {
      node.vx = 0;
      node.vy = 0;
      node.r = this.mapRadius(node);
      node.tier = this.mapTier(node);
      node.fx = node.kind === "core" ? 0 : null;
      node.fy = node.kind === "core" ? 0 : null;
      // A hair of noise so two devices on the same spoke do not start on
      // top of one another and shove each other straight outwards.
      node.x += (random() - 0.5) * 6;
      node.y += (random() - 0.5) * 6;
    });
    const springs = links
      .map((link) => {
        const a = byId.get(link.from);
        const b = byId.get(link.to);
        if (!a || !b) return null;
        const child = a.tier >= b.tier ? a : b;
        const parent = child === a ? b : a;
        // Rest length and stiffness by the child's tier: leaves are short
        // and stiff, trunks long and soft.
        const rest = link.bridge ? 230
          : child.tier === 1 ? 200
          : child.tier === 2 ? 125
          : child.tier === 3 ? 62 : 40;
        const strength = link.bridge ? 0.02
          : child.tier === 1 ? 0.1
          : child.tier === 2 ? 0.18
          : child.tier === 3 ? 0.3 : 0.38;
        return { a: child, b: parent, rest, strength };
      })
      .filter(Boolean);
    return { nodes, springs, random, alpha: 1, settled: false };
  }

  /** One step. Alpha scales every displacement, so the same forces settle
   *  the graph quickly at first and barely stir it once at rest. */
  mapTick(sim, alpha) {
    const { nodes, springs, random } = sim;
    const n = nodes.length;
    // Pixels per tick. A node that needs to go further gets there over
    // several ticks, which is what a settle is.
    const MAX_SPEED = 28;

    // Springs.
    springs.forEach(({ a, b, rest, strength }) => {
      let dx = b.x - a.x;
      let dy = b.y - a.y;
      const distance = Math.hypot(dx, dy) || 0.001;
      // The leash: past one and a half rest lengths the pull doubles, so a
      // leaf shoved away from its aggregator is hauled straight back.
      const leash = distance > rest * 1.5 ? 2 : 1;
      // Never more than half the gap in one tick: the stability bound of
      // an explicit step, and the difference between settling and diverging.
      const fraction = Math.max(-0.5, Math.min(0.5, ((distance - rest) / distance) * strength * leash * alpha));
      const force = fraction;
      dx *= force;
      dy *= force;
      a.vx += dx;
      a.vy += dy;
      b.vx -= dx * 0.45;
      b.vy -= dy * 0.45;
    });

    // Repulsion. The reach is capped at REACH, so only pairs within it
    // matter, and a uniform grid with cells of that size finds them without
    // visiting every pair: each node looks at its own cell and the eight
    // around it. On six hundred nodes that is the difference between a tick
    // that costs a frame and one that costs a fraction of it.
    const REACH = 150;
    const REACH2 = REACH * REACH;
    const cells = new Map();
    const key = (cx, cy) => cx * 100003 + cy;
    nodes.forEach((node) => {
      node._cx = Math.floor(node.x / REACH);
      node._cy = Math.floor(node.y / REACH);
      const k = key(node._cx, node._cy);
      const bucket = cells.get(k);
      if (bucket) bucket.push(node);
      else cells.set(k, [node]);
    });
    // Two leaves only mind each other up close; everything else keeps the
    // full reach. That is what lets a tuft form: siblings pack, tufts part.
    const LEAF_REACH2 = 55 * 55;
    const repel = (a, b) => {
      const dx = b.x - a.x;
      const dy = b.y - a.y;
      const d2 = dx * dx + dy * dy;
      const bothLeaves = a.tier === 4 && b.tier === 4;
      if (d2 > (bothLeaves ? LEAF_REACH2 : REACH2) || d2 === 0) return;
      const distance = Math.sqrt(d2);
      // Big nodes push harder; overlapping ones push hardest. Softer than
      // the springs by design: the springs say where a node belongs, the
      // repulsion only keeps it from sitting on a neighbour.
      const minimum = a.r + b.r + 6;
      const base = (a.r + b.r) * 4;
      let force = (base / d2) * alpha;
      if (distance < minimum) force += ((minimum - distance) / distance) * 0.5;
      const fx = dx * force;
      const fy = dy * force;
      a.vx -= fx;
      a.vy -= fy;
      b.vx += fx;
      b.vy += fy;
    };
    for (let i = 0; i < n; i += 1) {
      const a = nodes[i];
      for (let ox = -1; ox <= 1; ox += 1) {
        for (let oy = -1; oy <= 1; oy += 1) {
          const bucket = cells.get(key(a._cx + ox, a._cy + oy));
          if (!bucket) continue;
          for (let j = 0; j < bucket.length; j += 1) {
            const b = bucket[j];
            // Each unordered pair once: by index, so a cell is not doubled.
            if (b === a || (ox === 0 && oy === 0 ? bucket.indexOf(b) < bucket.indexOf(a) : false)) continue;
            if (ox === 0 && oy === 0) {
              repel(a, b);
            } else if (ox > 0 || (ox === 0 && oy > 0)) {
              // Neighbouring cells: visit each cell pair from one side only.
              repel(a, b);
            }
          }
        }
      }
    }

    // Gravity to the centre, so a freed branch drifts back rather than away.
    nodes.forEach((node) => {
      node.vx -= node.x * 0.004 * alpha;
      node.vy -= node.y * 0.004 * alpha;
      if (sim.settled && !this._reducedMotion) {
        // The breathing: a whisper of seeded noise once at rest.
        node.vx += (random() - 0.5) * 0.35;
        node.vy += (random() - 0.5) * 0.35;
      }
    });

    // Integrate with damping; pinned nodes go where they were put.
    nodes.forEach((node) => {
      if (node.fx != null) {
        node.x = node.fx;
        node.y = node.fy;
        node.vx = 0;
        node.vy = 0;
        return;
      }
      node.vx *= 0.6;
      node.vy *= 0.6;
      const speed = Math.hypot(node.vx, node.vy);
      if (speed > MAX_SPEED) {
        node.vx *= MAX_SPEED / speed;
        node.vy *= MAX_SPEED / speed;
      }
      node.x += node.vx;
      node.y += node.vy;
    });
  }

  drawMap(svg, animate = false) {
    const NS = "http://www.w3.org/2000/svg";
    const el = (name, attrs) => {
      const node = document.createElementNS(NS, name);
      Object.entries(attrs || {}).forEach(([key, value]) => node.setAttribute(key, value));
      return node;
    };
    this.stopMap();
    while (svg.firstChild) svg.removeChild(svg.firstChild);
    svg.classList.toggle("animate", Boolean(animate));
    svg.setAttribute("preserveAspectRatio", "xMidYMid meet");
    this._reducedMotion =
      window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    const view = this._view || (this._view = { k: 1, x: 0, y: 0 });
    const root = el("g", {});
    svg.appendChild(root);
    const applyView = () => {
      root.setAttribute("transform", `translate(${view.x},${view.y}) scale(${view.k})`);
      svg.dataset.zoom = view.k >= 2.2 ? "near" : view.k >= 1.4 ? "mid" : "far";
    };
    applyView();

    const rect = svg.getBoundingClientRect();
    const stretch = Math.min(1.7, Math.max(1, (rect.width || 1200) / (rect.height || 620) / 1.25));
    const { nodes, links, query } = this.mapLayout(stretch);
    const byId = new Map(nodes.map((node) => [node.id, node]));
    const dimmed = Boolean(query);
    const sim = this.mapSimulation(nodes, links);
    this._sim = sim;
    this._mapById = byId;
    this._mapLinks = links;

    // Neighbours, for the focus highlight.
    const near = new Map();
    links.forEach((link) => {
      if (!near.has(link.from)) near.set(link.from, new Set());
      if (!near.has(link.to)) near.set(link.to, new Set());
      near.get(link.from).add(link.to);
      near.get(link.to).add(link.from);
    });
    this._mapNear = near;

    const untouched = view.k === 1 && view.x === 0 && view.y === 0;
    if (untouched || !this._mapBox) {
      const pad = 160;
      const xs = nodes.map((node) => node.x);
      const ys = nodes.map((node) => node.y);
      const minX = Math.min(...xs) - pad;
      const minY = Math.min(...ys) - pad;
      this._mapBox = [minX, minY, Math.max(...xs) + pad - minX, Math.max(...ys) + pad - minY];
    }
    svg.setAttribute("viewBox", this._mapBox.join(" "));

    // Build the DOM once. Every frame afterwards only moves what is here.
    const linkLayer = el("g", {});
    root.appendChild(linkLayer);
    const paths = [];
    links.forEach((link) => {
      const from = byId.get(link.from);
      const to = byId.get(link.to);
      if (!from || !to) return;
      // Drawn child to parent, so the flow animation runs towards the hub.
      const child = this.mapTier(from) >= this.mapTier(to) ? from : to;
      const parent = child === from ? to : from;
      const path = el("path", {
        class: link.bridge ? "link link--bridge" : "link",
        stroke: link.colour,
        "stroke-width": link.width,
      });
      path.dataset.from = child.id;
      path.dataset.to = parent.id;
      if (dimmed && !(to.hit || from.hit)) path.classList.add("dim");
      linkLayer.appendChild(path);
      paths.push({ path, child, parent, bridge: Boolean(link.bridge) });
    });

    const groups = [];
    nodes.forEach((node) => {
      const group = el("g", { class: "node", "data-id": node.id });
      if (dimmed && !node.hit) group.classList.add("dim");
      if (node.hit) group.classList.add("node--match");

      let mark = null;
      if (node.kind === "core") {
        mark = el("rect", { class: "node__mark", width: 44, height: 44, rx: 12, fill: node.colour });
      } else if (node.kind !== "more") {
        mark = el("circle", {
          class: "node__mark",
          r: node.r,
          fill:
            node.kind === "origin" || (node.kind === "device" && node.isHub)
              ? "var(--surface)"
              : node.colour,
          stroke: node.colour,
          "stroke-width":
            node.kind === "origin" ? 2 : node.kind === "device" && node.isHub ? 2.5 : 0,
        });
        if (node.kind === "origin") mark.setAttribute("stroke-dasharray", "3 2");
      }
      if (mark) group.appendChild(mark);

      // The name, and only the name. Everything else is a click away.
      const below = node.kind === "core" ? 40
        : node.kind === "transport" ? 27
        : node.kind === "integration" ? 21
        : node.kind === "origin" ? 18 : 15;
      // Always named: the core, the transports, the publishing systems and
      // the integrations big enough to be a tuft. A small integration is
      // named the way a leaf is, on approach, focus or match.
      // By size alone: at the deepest detail every branch is open, and an
      // expanded integration with two devices is still not a tuft.
      const minor =
        node.kind === "device" || node.kind === "more" ||
        (node.kind === "integration" && (node.count || 0) < MAJOR_INTEGRATION);
      const label = el("text", {
        class:
          (node.kind === "core"
            ? "lbl lbl--core"
            : node.kind === "transport"
              ? "lbl lbl--transport"
              : "lbl") + (minor ? " lbl--device" : ""),
        "text-anchor": "middle",
      });
      const text = String(node.label || "");
      label.textContent = text.length > 26 ? `${text.slice(0, 25)}…` : text;
      group.appendChild(label);

      const hit = el("circle", { class: "hit", r: Math.max(14, node.r + 6) });
      group.appendChild(hit);
      group.style.animationDelay = `${node.tier * 110}ms`;

      group.addEventListener("click", (event) => {
        if (this._dragMoved) return;
        event.stopPropagation();
        this.focusMapNode(svg, node.id === this._focus ? null : node.id);
      });

      root.appendChild(group);
      groups.push({ group, mark, label, hit, node, below });
    });

    // Move what is drawn to where the simulation put it.
    const place = () => {
      paths.forEach(({ path, child, parent, bridge }) => {
        const mx = (child.x + parent.x) / 2;
        const my = (child.y + parent.y) / 2;
        // A gentle bow so parallel spokes do not stack into one line.
        const bow = bridge ? 0.25 : 0.08;
        const cx = mx + (parent.y - child.y) * bow;
        const cy = my - (parent.x - child.x) * bow;
        path.setAttribute("d", `M${child.x.toFixed(1)},${child.y.toFixed(1)} Q${cx.toFixed(1)},${cy.toFixed(1)} ${parent.x.toFixed(1)},${parent.y.toFixed(1)}`);
      });
      groups.forEach(({ mark, label, hit, node, below }) => {
        if (mark) {
          if (node.kind === "core") {
            mark.setAttribute("x", node.x - 22);
            mark.setAttribute("y", node.y - 22);
          } else {
            mark.setAttribute("cx", node.x);
            mark.setAttribute("cy", node.y);
          }
        }
        label.setAttribute("x", node.x);
        label.setAttribute("y", node.y + below);
        hit.setAttribute("cx", node.x);
        hit.setAttribute("cy", node.y);
      });
      if (this._focus) this.placeMapPopup(svg);
    };
    this._placeMap = place;
    place();

    // Settle fast, then breathe. Paused while hidden and while dragging.
    const SETTLE = 110;
    let ticks = 0;
    const loop = () => {
      this._mapFrame = 0;
      if (!svg.isConnected) return;
      if (document.hidden) {
        this._mapFrame = requestAnimationFrame(loop);
        return;
      }
      if (!sim.settled) {
        sim.alpha *= 0.965;
        ticks += 1;
        this.mapTick(sim, Math.max(sim.alpha, 0.05));
        if (ticks >= SETTLE) sim.settled = true;
        place();
      } else if (this._dragging || this._reheat > 0) {
        this.mapTick(sim, 0.35);
        if (!this._dragging) this._reheat -= 1;
        place();
      } else if (!this._reducedMotion) {
        // At rest: a light tick every third frame is all the sway needs.
        if (ticks % 3 === 0) {
          this.mapTick(sim, 0.06);
          place();
        }
        ticks += 1;
      } else {
        return; // reduced motion: settle and stop.
      }
      this._mapFrame = requestAnimationFrame(loop);
    };
    this._mapFrame = requestAnimationFrame(loop);

    // The reveal has played by then; keeping the class would keep every
    // link on the intro animation and a re-added one would replay it.
    if (animate) window.setTimeout(() => svg.classList.remove("animate"), 900);

    if (this._focus && byId.has(this._focus)) this.focusMapNode(svg, this._focus, true);
    this.attachMapControls(svg, view, applyView);
  }

  stopMap() {
    if (this._mapFrame) cancelAnimationFrame(this._mapFrame);
    this._mapFrame = 0;
  }

  /** Focus a node: neighbours stay, the rest fades, the touching edges flow,
   *  and the popup opens beside it. Null clears all of it. */
  focusMapNode(svg, id, silent = false) {
    this._focus = id;
    svg.classList.toggle("has-focus", Boolean(id));
    const near = id ? this._mapNear.get(id) || new Set() : new Set();
    svg.querySelectorAll("g.node").forEach((group) => {
      const nodeId = group.dataset.id;
      group.classList.toggle("is-focus", nodeId === id);
      group.classList.toggle("is-near", Boolean(id) && near.has(nodeId));
    });
    svg.querySelectorAll("path.link").forEach((path) => {
      path.classList.toggle("flow", Boolean(id) && (path.dataset.from === id || path.dataset.to === id));
    });
    const wrap = svg.closest(".mapwrap");
    const old = wrap && wrap.querySelector(".mappopup");
    if (old) old.remove();
    if (!id || !wrap) return;
    const popup = document.createElement("div");
    popup.className = "mappopup";
    popup.innerHTML = this.mapPopup(id);
    wrap.appendChild(popup);
    popup.querySelector("[data-action='popup-close']").addEventListener("click", () => this.focusMapNode(svg, null));
    const isolate = popup.querySelector("[data-action='popup-isolate']");
    if (isolate) {
      isolate.addEventListener("click", () => {
        const entryId = isolate.dataset.entry;
        const current = this._scope;
        this._scope =
          current && current.kind === "integration" && current.id === entryId
            ? null
            : { kind: "integration", id: entryId };
        this._view = { k: 1, x: 0, y: 0 };
        this._mapBox = null;
        this._focus = null;
        this.render();
      });
    }
    this.placeMapPopup(svg);
    if (!silent) this._reheat = 0;
  }

  /** Keep the popup beside its node as the node sways or the view moves. */
  placeMapPopup(svg) {
    const wrap = svg.closest(".mapwrap");
    const popup = wrap && wrap.querySelector(".mappopup");
    const node = this._mapById && this._mapById.get(this._focus);
    if (!popup || !node) return;
    const root = svg.firstChild;
    const point = svg.createSVGPoint();
    point.x = node.x;
    point.y = node.y;
    const matrix = root && root.getScreenCTM();
    if (!matrix) return;
    const screen = point.matrixTransform(matrix);
    const box = wrap.getBoundingClientRect();
    const svgBox = svg.getBoundingClientRect();
    let left = screen.x - box.left + 18;
    let top = screen.y - box.top - 12;
    // Flip to the left of the node when it would run off the right edge, and
    // clamp vertically inside the map.
    if (left + popup.offsetWidth > box.width - 8) left = screen.x - box.left - popup.offsetWidth - 18;
    top = Math.max(svgBox.top - box.top + 8, Math.min(top, box.height - popup.offsetHeight - 8));
    popup.style.left = `${Math.max(8, left)}px`;
    popup.style.top = `${top}px`;
  }

  /** Everything known about one node, as the popup shows it. */
  mapPopup(id) {
    const d = this._data;
    const node = this._mapById.get(id);
    if (node.ref == null) node.ref = String(id).replace(/^[a-z]+:/, "");
    const rows = [];
    const row = (label, value) => {
      if (value == null || value === "") return;
      rows.push(`<dt>${esc(label)}</dt><dd>${esc(String(value))}</dd>`);
    };
    let title = node.label;
    let kind = this.t(`map.popup.kind.${node.kind}`);
    let isolate = "";

    if (node.kind === "device") {
      const device = d.labels.devices[node.ref] || {};
      const integration = d.labels.integrations[device.integration_id] || {};
      title = device.name || node.label;
      row(this.t("map.field.transport"), this.t(`transport.${device.transport || "unknown"}`));
      row(this.t("map.field.integration"), integration.title);
      row(this.t("map.field.origin"), device.origin);
      row(this.t("map.field.mesh"), this.t(`mesh.${device.mesh_role || "unknown"}`));
      row(this.t("map.field.area"), device.area);
      row(this.t("map.field.ip"), device.ip);
      row(this.t("map.field.model"), [device.manufacturer, device.model].filter(Boolean).join(" "));
      row(this.t("map.field.entities"), device.entity_count || 0);
      const hub = device.via_device_id && d.labels.devices[device.via_device_id];
      row(this.t("map.field.hub"), hub ? hub.name : null);
      const children = Object.values(d.labels.devices).filter((x) => x.via_device_id === node.ref).length;
      if (children) row(this.t("map.field.children"), children);
    } else if (node.kind === "integration") {
      const integration = d.labels.integrations[node.ref] || {};
      title = integration.title || node.label;
      row(this.t("map.field.domain"), integration.domain);
      row(this.t("map.field.class"), integration.iot_class);
      row(this.t("map.field.role"), this.t(`role.${integration.role || "unknown"}`) || null);
      row(this.t("map.field.state"), integration.state);
      row(this.t("map.field.endpoint"), integration.endpoint);
      row(this.t("map.field.devices"), node.count);
      const active = this._scope && this._scope.kind === "integration" && this._scope.id === node.ref;
      isolate = `<button class="btn btn--ghost" data-action="popup-isolate" data-entry="${esc(node.ref)}">${esc(
        this.t(active ? "map.popup.unisolate" : "map.popup.isolate")
      )}</button>`;
    } else if (node.kind === "transport") {
      row(this.t("map.field.devices"), node.sub);
    } else if (node.kind === "origin") {
      row(this.t("map.field.devices"), node.sub);
    }

    // The conduits this node is the source of, grouped by destination kind.
    let links = "";
    const sourceId = node.kind === "device" ? node.ref : node.kind === "integration" ? node.ref : null;
    if (sourceId) {
      const mine = (d.conduits || []).filter((c) => c.source.id === sourceId);
      if (mine.length) {
        const byDest = new Map();
        mine.forEach((c) => {
          const dest = this.destination(c.destination_id);
          const key = c.destination_id;
          const cur = byDest.get(key) || { dest, n: 0, evidence: c.evidence, protocol: c.protocol };
          cur.n += c.query_count || 1;
          byDest.set(key, cur);
        });
        const top = [...byDest.values()].sort((a, b) => b.n - a.n).slice(0, 6);
        links = `<div class="mappopup__links"><b>${esc(this.t("map.popup.links"))} · ${esc(
          this.t("map.popup.conduits", { n: mine.length })
        )}</b>${top
          .map(
            (item) => `<div><i style="background:${this.kindColour(item.dest.kind)}"></i>${esc(
              item.dest.fqdn
            )}<span>${esc([item.protocol, this.t(`evidence.${item.evidence}`)].filter(Boolean).join(" · "))}</span></div>`
          )
          .join("")}</div>`;
      } else {
        links = `<div class="mappopup__links"><b>${esc(this.t("map.popup.links"))}</b><div>${esc(
          this.t("map.popup.noConduits")
        )}</div></div>`;
      }
    }

    return `<div class="mappopup__head">
        <div><div class="mappopup__kind">${esc(kind)}</div><div class="mappopup__title">${esc(title)}</div></div>
        <button class="mappopup__close" data-action="popup-close" title="${esc(this.t("map.popup.close"))}">×</button>
      </div>
      ${rows.length ? `<dl>${rows.join("")}</dl>` : ""}
      ${links}
      ${isolate}`;
  }

  attachMapControls(svg, view, applyView) {
    this._redrawMap = () => this.drawMap(svg);
    if (svg.dataset.wired === "1") return;
    svg.dataset.wired = "1";

    const root = () => svg.firstChild;
    const toGraph = (event) => {
      const point = svg.createSVGPoint();
      point.x = event.clientX;
      point.y = event.clientY;
      const matrix = root() && root().getScreenCTM();
      return matrix ? point.matrixTransform(matrix.inverse()) : { x: 0, y: 0 };
    };

    svg.addEventListener("wheel", (event) => {
      event.preventDefault();
      const factor = Math.exp(-event.deltaY * 0.0015);
      const next = Math.min(6, Math.max(0.35, view.k * factor));
      const rect = svg.getBoundingClientRect();
      const px = event.clientX - rect.left - rect.width / 2;
      const py = event.clientY - rect.top - rect.height / 2;
      view.x = px - ((px - view.x) * next) / view.k;
      view.y = py - ((py - view.y) * next) / view.k;
      view.k = next;
      applyView();
      if (this._focus) this.placeMapPopup(svg);
    }, { passive: false });

    let panning = null;

    svg.addEventListener("pointerdown", (event) => {
      const target = event.target.closest && event.target.closest("g.node");
      this._dragMoved = false;
      if (target && target.dataset.id) {
        const node = this._mapById.get(target.dataset.id);
        if (node && node.kind !== "core") {
          // Pin it to the pointer; the neighbours follow under the springs.
          this._dragging = node;
          node.fx = node.x;
          node.fy = node.y;
          svg.setPointerCapture(event.pointerId);
          return;
        }
      }
      panning = { x: event.clientX - view.x, y: event.clientY - view.y };
      svg.classList.add("dragging");
      svg.setPointerCapture(event.pointerId);
    });

    // Leaf names near the pointer, the way Obsidian reveals them: the
    // nearest few within a hand's reach, and no more, so the ones shown can
    // be read. Throttled to a frame; the distance test is a cheap scan.
    let hoverFrame = 0;
    const HOVER_REACH = 70;
    const HOVER_MAX = 12;
    const revealNear = (event) => {
      // Cancel and reschedule rather than latch: the latest event wins, and
      // a frame that never fires, a hidden tab, cannot block every reveal
      // that follows it.
      if (hoverFrame) cancelAnimationFrame(hoverFrame);
      hoverFrame = requestAnimationFrame(() => {
        hoverFrame = 0;
        const point = toGraph(event);
        const reach = HOVER_REACH / Math.max(view.k, 0.35);
        const near = [];
        this._sim.nodes.forEach((node) => {
          if (node.kind !== "device") return;
          const distance = Math.hypot(node.x - point.x, node.y - point.y);
          if (distance <= reach) near.push([distance, node.id]);
        });
        near.sort((a, b) => a[0] - b[0]);
        const keep = new Set(near.slice(0, HOVER_MAX).map(([, id]) => id));
        svg.querySelectorAll("g.node.is-hover").forEach((group) => {
          if (!keep.has(group.dataset.id)) group.classList.remove("is-hover");
        });
        keep.forEach((id) => {
          const group = svg.querySelector(`g.node[data-id="${id}"]`);
          if (group) group.classList.add("is-hover");
        });
      });
    };
    this._revealNear = revealNear;

    svg.addEventListener("pointermove", (event) => {
      if (this._dragging) {
        const point = toGraph(event);
        this._dragging.fx = point.x;
        this._dragging.fy = point.y;
        this._dragMoved = true;
        return;
      }
      if (panning) {
        view.x = event.clientX - panning.x;
        view.y = event.clientY - panning.y;
        applyView();
        if (this._focus) this.placeMapPopup(svg);
        return;
      }
      revealNear(event);
    });
    svg.addEventListener("pointerleave", () => {
      svg.querySelectorAll("g.node.is-hover").forEach((group) => group.classList.remove("is-hover"));
    });

    const stop = () => {
      if (this._dragging) {
        // Let go: it settles back under its springs, like the rest.
        this._dragging.fx = null;
        this._dragging.fy = null;
        this._dragging = null;
        this._reheat = 45;
      }
      panning = null;
      svg.classList.remove("dragging");
      setTimeout(() => {
        this._dragMoved = false;
      }, 0);
    };
    svg.addEventListener("pointerup", stop);
    svg.addEventListener("pointercancel", stop);
    svg.addEventListener("pointerleave", stop);

    // Click on empty space clears the focus; Escape too.
    svg.addEventListener("click", (event) => {
      if (this._dragMoved) return;
      if (!(event.target.closest && event.target.closest("g.node"))) this.focusMapNode(svg, null);
    });
    if (!this._escWired) {
      this._escWired = true;
      window.addEventListener("keydown", (event) => {
        if (event.key === "Escape" && this._focus) {
          const map = this.shadowRoot.querySelector("svg.map");
          if (map) this.focusMapNode(map, null);
        }
      });
    }
  }

  transportGroup(group, total) {
    const d = this._data;
    const share = total ? (group.total / total) * 100 : 0;
    const colour = `var(--t-${group.transport.replace(/[^a-z]/g, "") || "unknown"}, var(--t-unknown))`;

    return `<div class="tgroup" style="border-left-color:${colour}">
      <div class="tgroup__head">
        <span class="tgroup__name">${esc(this.t(`transport.${group.transport}`))}</span>
        <span class="tgroup__count">${esc(this.t("map.devices", { n: this.num(group.total) }))}</span>
        <span class="tgroup__share"><span style="width:${share}%;background:${colour}"></span></span>
      </div>
      ${group.integrations
        .map((entry) => {
          const integration = d.labels.integrations[entry.id] || {};
          return `<details>
            <summary>
              <span>${esc(integration.title || entry.id)}</span>
              <span class="tgroup__domain">${esc(integration.domain || "")}</span>
              ${
                integration.iot_class
                  ? `<span class="chip">${esc(integration.iot_class)}</span>`
                  : ""
              }
              ${
                integration.role && integration.role !== "unknown"
                  ? `<span class="chip">${esc(this.t(`role.${integration.role}`))}</span>`
                  : ""
              }
              ${
                integration.state && integration.state !== "loaded"
                  ? `<span class="chip chip--alert">${esc(this.t("state.notLoaded"))}</span>`
                  : ""
              }
              ${integration.is_built_in === false ? `<span class="chip">HACS</span>` : ""}
              ${
                integration.endpoint
                  ? `<span class="tgroup__domain">${esc(integration.endpoint)}</span>`
                  : ""
              }
              <span class="tgroup__n">${entry.devices.length}</span>
            </summary>
            <div class="devlist">
              ${entry.devices
                .map(
                  (device) => `<div class="dev">${esc(device.name || device.id)}
                    <span>${esc(
                      [
                        this.t(`mesh.${device.mesh_role || "unknown"}`),
                        device.area,
                        device.ip || device.model,
                        device.entity_count
                          ? this.t("map.entities", { n: device.entity_count })
                          : "",
                      ]
                        .filter(Boolean)
                        .join(" · ")
                    )}</span></div>`
                )
                .join("")}
            </div>
          </details>`;
        })
        .join("")}
    </div>`;
  }

  /* ── diagnostics ─────────────────────────────────────────────────────── */

  async runDiagnostics() {
    if (this._diagRunning) return;
    const host = this.shadowRoot;
    const field = host.querySelector("#diag-window");
    const window = Number((field || {}).value) || 60;
    this._diagWindow = window;
    this._diagRunning = true;
    this.setBusy("busy", this.t("diag.busy"), this.t("diag.busy.sub", { n: window }));
    try {
      const run = await this._hass.callWS({ type: "talos/diagnostics/run", window });
      this._diagnostics = run;
      this._diagRunning = false;
      this.setBusy(
        "ok",
        this.t("diag.done"),
        this.t("diag.done.sub", { when: this.when(run.finished_at), n: run.window_seconds })
      );
    } catch (err) {
      this._diagRunning = false;
      this.setBusy("error", this.t("diag.failed"), err && err.message ? err.message : String(err));
    }
  }

  diagName(entryId) {
    const labels = (this._diagnostics || {}).labels || {};
    return (labels.titles || {})[entryId] || entryId;
  }

  diagDomain(entryId) {
    const labels = (this._diagnostics || {}).labels || {};
    return (labels.domains || {})[entryId] || "";
  }

  viewDiagnostics() {
    const run = this._diagnostics;
    const window = this._diagWindow || (run && run.window_seconds) || 60;
    const controls = `<div class="panel-card">
      <div class="form">
        <div class="field">
          <label for="diag-window">${esc(this.t("diag.window"))}</label>
          <select id="diag-window">
            ${[30, 60, 120]
              .map(
                (n) => `<option value="${n}" ${n === window ? "selected" : ""}>${esc(
                  this.t("diag.seconds", { n })
                )}</option>`
              )
              .join("")}
          </select>
        </div>
      </div>
      <div class="actions">
        <button class="btn" data-action="diag-run" ${this._diagRunning ? "disabled" : ""}>${esc(
          this._diagRunning ? this.t("diag.running") : this.t("diag.run")
        )}</button>
        ${
          run
            ? `<span class="status">${esc(
                this.t("diag.measured", { when: this.when(run.finished_at) })
              )}</span>`
            : ""
        }
      </div>
    </div>`;

    if (!run) {
      return `<div class="stack">
        <div>
          <h1 class="page">${esc(this.t("diag.title"))}</h1>
          <p class="page-sub">${esc(this.t("diag.lead"))}</p>
        </div>
        ${controls}
        <p class="status">${esc(this.t("diag.none"))}</p>
      </div>`;
    }

    const minutes = Math.max(run.window_seconds, 1) / 60;
    const churn = (run.churn || [])
      .map((row) =>
        this.expander({
          tone: "info",
          title: esc(this.diagName(row.entry_id)),
          chips: [
            `<span class="chip">${esc(this.diagDomain(row.entry_id))}</span>`,
            `<span class="chip">${esc(this.t("diag.churn.perMinute", { n: this.num(row.per_minute) }))}</span>`,
            `<span class="chip">${esc(this.t("diag.churn.entities", { n: this.num(row.entities) }))}</span>`,
          ],
          body: `<div class="exp__lab">${esc(this.t("diag.churn.top"))}</div>
            <div class="exp__rows">${(row.top_entities || [])
              .map(
                ([entityId, count]) =>
                  `<div class="exp__row"><b class="mono">${esc(entityId)}</b><span class="mono">${this.num(
                    count
                  )}</span></div>`
              )
              .join("")}</div>`,
        })
      )
      .join("");

    const blocking = (run.blocking || [])
      .map((row) =>
        this.expander({
          tone: "attention",
          title: esc(row.domain),
          chips: [
            `<span class="chip">${esc(this.t("diag.blocking.count", { n: this.num(row.count) }))}</span>`,
            row.last_seen
              ? `<span class="chip mono">${esc(this.t("diag.blocking.last"))} ${esc(row.last_seen)}</span>`
              : "",
          ].filter(Boolean),
          body: `<div class="exp__lab">${esc(this.t("diag.blocking.sample"))}</div>
            <p class="mono" style="font-size:12px;word-break:break-word">${esc(row.sample)}</p>`,
        })
      )
      .join("");

    const reach = (run.reachability || [])
      .map(
        (row) => `<div class="exp__row">
          <b>${esc(this.diagName(row.entry_id))}</b>
          <span class="mono">${esc(`${row.host}:${row.port}`)} · ${
            row.reachable
              ? `<span style="color:var(--k-local)">${esc(this.t("diag.reach.ok"))}, ${esc(
                  this.t("diag.reach.ms", { n: this.num(row.latency_ms) })
                )}</span>`
              : `<span style="color:var(--alert)">${esc(this.t("diag.reach.fail"))}${
                  row.error ? `, ${esc(row.error)}` : ""
                }</span>`
          }</span>
        </div>`
      )
      .join("");

    return `<div class="stack">
      <div>
        <h1 class="page">${esc(this.t("diag.title"))}</h1>
        <p class="page-sub">${esc(this.t("diag.lead"))}</p>
      </div>
      ${controls}

      <div>
        <h2 class="sec">${esc(this.t("diag.churn"))}</h2>
        <p class="page-sub" style="margin-bottom:10px">${esc(this.t("diag.churn.lead"))}</p>
        <p class="hint" style="margin:0 0 10px">${esc(
          this.t("diag.churn.total", {
            total: this.num(run.total_changes),
            n: run.window_seconds,
            rate: this.num(Math.round(run.total_changes / minutes)),
          })
        )}${
          run.unattributed_changes
            ? ` ${esc(this.t("diag.churn.unattributed", { n: this.num(run.unattributed_changes) }))}`
            : ""
        }</p>
        ${churn || `<p class="status">${esc(this.t("diag.churn.none"))}</p>`}
      </div>

      <div>
        <h2 class="sec">${esc(this.t("diag.blocking"))}</h2>
        <p class="page-sub" style="margin-bottom:10px">${esc(this.t("diag.blocking.lead"))}</p>
        ${blocking || `<p class="status">${esc(this.t("diag.blocking.none"))}</p>`}
      </div>

      <div>
        <h2 class="sec">${esc(this.t("diag.reach"))}</h2>
        <p class="page-sub" style="margin-bottom:10px">${esc(this.t("diag.reach.lead"))}</p>
        ${
          reach
            ? `<div class="panel-card"><div class="exp__rows">${reach}</div></div>`
            : `<p class="status">${esc(this.t("diag.reach.none"))}</p>`
        }
      </div>

      ${this.addonSection(run)}

      ${
        (run.notes || []).length
          ? `<div class="note">
              <div class="note__label">${esc(this.t("diag.notes"))}</div>
              ${run.notes.map((note) => `<p>· ${esc(note)}</p>`).join("")}
            </div>`
          : ""
      }
    </div>`;
  }

  /** A line chart from rows. Series are {key, label, colour}; x is the row
   *  index, y from zero to the largest value across the series, so two
   *  charts of the same kind read against the same baseline. Plain SVG,
   *  nothing this file does not already have. */
  lineChart(rows, series, title) {
    const W = 600, H = 150, L = 34, R = 10, T = 10, B = 18;
    const n = rows.length;
    if (n < 2) return "";
    const max = Math.max(1, ...series.flatMap((s) => rows.map((r) => Number(r[s.key]) || 0)));
    const x = (i) => L + (i / (n - 1)) * (W - L - R);
    const y = (v) => T + (1 - v / max) * (H - T - B);
    const ticks = [0, Math.round(max / 2), max];
    const grid = ticks
      .map((v) => `<line x1="${L}" x2="${W - R}" y1="${y(v).toFixed(1)}" y2="${y(v).toFixed(1)}" stroke="var(--border)" stroke-width="1"/>
        <text x="${L - 4}" y="${(y(v) + 3).toFixed(1)}" text-anchor="end">${v}</text>`)
      .join("");
    const lines = series
      .map((s) => {
        const points = rows.map((r, i) => `${x(i).toFixed(1)},${y(Number(r[s.key]) || 0).toFixed(1)}`).join(" ");
        const last = Number(rows[n - 1][s.key]) || 0;
        return `<polyline points="${points}" fill="none" stroke="${s.colour}" stroke-width="1.8" stroke-linejoin="round"/>
          <circle cx="${x(n - 1).toFixed(1)}" cy="${y(last).toFixed(1)}" r="2.6" fill="${s.colour}"/>`;
      })
      .join("");
    const legend = series
      .map((s) => `<span><i style="background:${s.colour}"></i>${esc(s.label)} <b>${this.num(Number(rows[n - 1][s.key]) || 0)}</b></span>`)
      .join("");
    return `<div class="chart">
      <p class="chart__title">${esc(title)}</p>
      <svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="none" role="img" aria-label="${esc(title)}">${grid}${lines}</svg>
      <div class="chart__legend">${legend}</div>
    </div>`;
  }

  historySection() {
    const rows = this._history || [];
    const body =
      rows.length < 2
        ? `<p class="status">${esc(this.t("history.none"))}</p>`
        : `<p class="hint" style="margin:0 0 10px">${esc(
            this.t("history.scans", { n: this.num(rows.length), from: this.when(rows[0].generated_at) })
          )}</p>
          <div class="charts">
            ${this.lineChart(rows, [
              { key: "failed_high", label: this.t("history.high"), colour: "var(--alert)" },
              { key: "failed_medium", label: this.t("history.medium"), colour: "var(--attention)" },
              { key: "failed_low", label: this.t("history.low"), colour: "var(--accent)" },
              { key: "partial", label: this.t("history.partial"), colour: "var(--k-infra)" },
              { key: "unverified", label: this.t("history.unverified"), colour: "var(--k-unknown)" },
            ], this.t("history.findings"))}
            ${this.lineChart(rows, [
              { key: "entities_local", label: this.t("history.local"), colour: "var(--k-local)" },
              { key: "entities_cloud", label: this.t("history.cloud"), colour: "var(--k-vendor)" },
              { key: "entities_unavailable", label: this.t("history.unavailable"), colour: "var(--k-unknown)" },
            ], this.t("history.entities"))}
            ${this.lineChart(rows, [
              { key: "devices_exposed", label: this.t("history.exposed"), colour: "var(--k-vendor)" },
              { key: "local_egress", label: this.t("history.localEgress"), colour: "var(--alert)" },
            ], this.t("history.exposure"))}
            ${this.lineChart(rows, [
              { key: "unclassified", label: this.t("history.unclassifiedSeries"), colour: "var(--k-unknown)" },
            ], this.t("history.unclassified"))}
            ${this.lineChart(rows, [
              { key: "devices_correlated", label: this.t("history.correlated"), colour: "var(--k-local)" },
            ], this.t("history.correlation"))}
          </div>`;
    return `<div>
      <h2 class="sec">${esc(this.t("history.title"))}</h2>
      <p class="page-sub" style="margin-bottom:10px">${esc(this.t("history.lead"))}</p>
      ${body}
    </div>`;
  }

  /** A donut from a list of {name, percent} slices. Plain SVG arcs, so it
   *  needs nothing this file does not already have. */
  pie(slices, title, note) {
    const rows = (slices || []).filter((s) => s.percent > 0);
    if (!rows.length) {
      return `<div class="pie"><div><p class="pie__title">${esc(title)}</p>
        <p class="pie__note">${esc(this.t("diag.addons.noPie"))}</p></div></div>`;
    }
    const R = 50, r = 30, cx = 56, cy = 56;
    let angle = -Math.PI / 2;
    const arcs = rows.map((slice, index) => {
      const sweep = (Math.min(slice.percent, 100) / 100) * Math.PI * 2;
      const colour = slice.slug === "other"
        ? "var(--sunken)"
        : `var(${WEDGE_COLOURS[index % WEDGE_COLOURS.length]})`;
      // A single full wedge would draw as nothing: two half arcs instead.
      const parts = sweep >= Math.PI * 2 - 1e-6 ? [Math.PI, Math.PI] : [sweep];
      let d = "";
      let start = angle;
      parts.forEach((part) => {
        const end = start + part;
        const large = part > Math.PI ? 1 : 0;
        const x0 = cx + R * Math.cos(start), y0 = cy + R * Math.sin(start);
        const x1 = cx + R * Math.cos(end), y1 = cy + R * Math.sin(end);
        const xi0 = cx + r * Math.cos(end), yi0 = cy + r * Math.sin(end);
        const xi1 = cx + r * Math.cos(start), yi1 = cy + r * Math.sin(start);
        d += `M${x0.toFixed(2)} ${y0.toFixed(2)}A${R} ${R} 0 ${large} 1 ${x1.toFixed(2)} ${y1.toFixed(2)}` +
             `L${xi0.toFixed(2)} ${yi0.toFixed(2)}A${r} ${r} 0 ${large} 0 ${xi1.toFixed(2)} ${yi1.toFixed(2)}Z`;
        start = end;
      });
      angle += sweep;
      return { d, colour, slice };
    });
    return `<div class="pie">
      <svg viewBox="0 0 112 112" role="img" aria-label="${esc(title)}">
        ${arcs.map((a) => `<path d="${a.d}" fill="${a.colour}" stroke="var(--surface)" stroke-width="1"/>`).join("")}
      </svg>
      <div>
        <p class="pie__title">${esc(title)}</p>
        <div class="pie__legend">
          ${arcs
            .map(
              (a) => `<div><i style="background:${a.colour}"></i><b>${esc(
                a.slice.slug === "other" ? this.t("diag.addons.other") : a.slice.name
              )}</b><span>${this.num(Math.round(a.slice.percent * 10) / 10)}%</span></div>`
            )
            .join("")}
        </div>
        ${note ? `<p class="pie__note">${esc(note)}</p>` : ""}
      </div>
    </div>`;
  }

  bytes(value) {
    if (value == null) return "-";
    const units = ["B", "kB", "MB", "GB"];
    let n = Number(value), i = 0;
    while (n >= 1000 && i < units.length - 1) { n /= 1000; i += 1; }
    return `${this.num(Math.round(n * 10) / 10)} ${units[i]}`;
  }

  addonSection(run) {
    const rows = run.addons || [];
    const shares = run.shares || {};
    const list = rows
      .map((row) => {
        const stopped = row.state !== "started";
        const meta = stopped
          ? this.t("diag.addons.stopped")
          : [
              row.cpu_percent != null ? `CPU ${this.num(row.cpu_percent)}%` : "",
              row.memory_bytes != null
                ? `${this.bytes(row.memory_bytes)}${row.memory_percent != null ? ` (${this.num(row.memory_percent)}%)` : ""}`
                : "",
              row.rx_bytes_per_s != null || row.tx_bytes_per_s != null
                ? this.t("diag.addons.rate", {
                    rx: `${this.bytes(row.rx_bytes_per_s || 0)}/s`,
                    tx: `${this.bytes(row.tx_bytes_per_s || 0)}/s`,
                  })
                : "",
            ]
              .filter(Boolean)
              .join(" · ");
        return `<div class="exp__row"><b>${esc(row.name)}</b><span class="mono">${esc(meta)}</span></div>`;
      })
      .join("");

    return `<div>
      <h2 class="sec">${esc(this.t("diag.addons"))}</h2>
      <p class="page-sub" style="margin-bottom:10px">${esc(this.t("diag.addons.lead"))}</p>
      ${
        rows.length
          ? `<div class="panel-card">
              <div class="pies">
                ${this.pie(
                  shares.cpu,
                  this.t("diag.addons.cpu"),
                  run.cpu_count ? this.t("diag.addons.cpuNote", { n: run.cpu_count }) : ""
                )}
                ${this.pie(
                  shares.memory,
                  this.t("diag.addons.memory"),
                  run.memory_total ? this.t("diag.addons.memoryNote", { total: this.bytes(run.memory_total) }) : ""
                )}
                ${this.pie(shares.network, this.t("diag.addons.network"), this.t("diag.addons.networkNote"))}
              </div>
              <div class="exp__rows" style="margin-top:14px">${list}</div>
            </div>`
          : `<p class="status">${esc(this.t("diag.addons.none"))}</p>`
      }
    </div>`;
  }

  /* ── settings ────────────────────────────────────────────────────────── */

  boolField(key) {
    const status = this._status || {};
    const value = (status.options || {})[key];
    const on = value == null ? true : Boolean(value);
    const hint = this.t(`opt.hint.${key}`);
    return `<div class="field">
      <label for="opt-${key}">${esc(this.t(`opt.${key}`))}</label>
      <select id="opt-${key}" data-option="${key}" data-bool="1">
        <option value="1" ${on ? "selected" : ""}>${esc(this.t("settings.value.yes"))}</option>
        <option value="0" ${on ? "" : "selected"}>${esc(this.t("settings.value.no"))}</option>
      </select>
      ${hint.startsWith("opt.hint.") ? "" : `<span class="hint">${esc(hint)}</span>`}
    </div>`;
  }

  retentionSummary() {
    const retention = (this._status || {}).retention || {};
    const sizing = retention.sizing;
    if (!sizing) return "";
    return `<dl class="kv" style="margin-top:12px">
      <dt>${esc(this.t("retention.derived"))}</dt>
      <dd>${esc(
        this.t(sizing.rate_measured ? "retention.rate.measured" : "retention.rate.assumed", {
          n: this.num(Math.round(sizing.rate_per_day)),
        })
      )}</dd>
      <dt>${esc(this.t("retention.days"))}</dt><dd class="mono">${this.num(sizing.observation_days)} d</dd>
      <dt>${esc(this.t("retention.rows"))}</dt><dd class="mono">${this.num(sizing.max_observations)}</dd>
      <dt>${esc(this.t("retention.scans"))}</dt><dd class="mono">${this.num(sizing.scan_history)}</dd>
      <dt>${esc(this.t("retention.estimate"))}</dt>
      <dd class="mono">${
        sizing.estimate_bytes != null ? esc(this.bytes(sizing.estimate_bytes)) : esc(this.t("retention.estimate.none"))
      }</dd>
    </dl>`;
  }

  numberField(key, bounds) {
    const status = this._status || {};
    const value = (status.options || {})[key];
    const range = (status.bounds || {})[key] || bounds || [];
    const hint = this.t(`opt.hint.${key}`);
    return `<div class="field">
      <label for="opt-${key}">${esc(this.t(`opt.${key}`))}</label>
      <input id="opt-${key}" type="number" data-option="${key}" inputmode="numeric"
             ${range.length ? `min="${range[0]}" max="${range[1]}"` : ""}
             value="${value == null ? "" : esc(value)}">
      <span class="hint">${
        range.length ? esc(this.t("settings.range", { min: range[0], max: range[1] })) : ""
      }${hint.startsWith("opt.hint.") ? "" : ` ${esc(hint)}`}</span>
    </div>`;
  }

  textField(key) {
    const value = ((this._status || {}).options || {})[key] || "";
    const hint = this.t(`opt.hint.${key}`);
    return `<div class="field">
      <label for="opt-${key}">${esc(this.t(`opt.${key}`))}</label>
      <input id="opt-${key}" type="text" data-option="${key}" spellcheck="false"
             value="${esc(value)}">
      ${hint.startsWith("opt.hint.") ? "" : `<span class="hint">${esc(hint)}</span>`}
      ${this.suggestionFor(key)}
    </div>`;
  }

  /** What the scan can propose for an option the user left empty. Offered as
   *  a button, never written on its own: Talos saw traffic on a subnet, it
   *  did not decide which of your networks that is. */
  suggestionFor(key) {
    const found = (this._suggestions || []).find((item) => item.option === key);
    if (!found) return "";
    return `<div class="sugg">
      <span>${esc(this.t("sugg.label"))}</span>
      <button type="button" data-suggest="${esc(key)}" data-value="${esc(found.value)}">
        ${esc(this.t("sugg.use"))} <span class="mono">${esc(found.value)}</span></button>
      <span>${esc(this.t("sugg.hosts", { n: this.num(found.hosts) }))}</span>
      <span class="hint">${esc(this.suggestionDetail(key, found))}</span>
    </div>`;
  }

  viewSettings() {
    const status = this._status || {};
    const connection = status.connection || {};
    const mqtt = status.mqtt || {};
    const store = status.store || {};
    const prune = (status.retention || {}).last_prune || {};
    const configured = Boolean(connection.adguard_url);
    const lastScan = status.generated_at
      ? new Date(status.generated_at).toLocaleString(LOCALES[this._lang] || LOCALES[FALLBACK_LANG])
      : this.t("app.never");
    const bytes = store.bytes_used
      ? `${(store.bytes_used / 1048576).toFixed(1)} MB`
      : "-";
    const removed =
      (prune.observations_expired || 0) + (prune.observations_over_cap || 0) + (prune.scans_removed || 0);

    return `<div class="stack">
      <div>
        <h1 class="page">${esc(this.t("settings.title"))}</h1>
        <p class="page-sub">${esc(this.t("settings.lead"))}</p>
      </div>

      <div>
        <h2 class="sec">${esc(this.t("settings.section.language"))}</h2>
        <div class="panel-card">
          <div class="form">
            <div class="field">
              <label for="lang">${esc(this.t("settings.section.language"))}</label>
              <select id="lang" data-action="language">
                <option value="auto" ${this._langOverride ? "" : "selected"}>${esc(
                  this.t("settings.language.auto")
                )}</option>
                ${Object.entries(LANGUAGES)
                  .map(
                    ([code, name]) =>
                      `<option value="${code}" ${this._langOverride === code ? "selected" : ""}>${name}</option>`
                  )
                  .join("")}
              </select>
              <span class="hint">${esc(this.t("settings.language.hint"))}</span>
            </div>
          </div>
        </div>
      </div>

      <div>
        <h2 class="sec">${esc(this.t("settings.section.connection"))}</h2>
        <div class="panel-card">
          ${
            configured
              ? `<dl class="kv">
                   <dt>${esc(this.t("settings.connection.url"))}</dt>
                   <dd class="mono">${esc(connection.adguard_url)}</dd>
                   <dt>${esc(this.t("settings.connection.user"))}</dt>
                   <dd class="mono">${esc(connection.adguard_username || this.t("settings.value.empty"))}</dd>
                   <dt>${esc(this.t("settings.connection.password"))}</dt>
                   <dd>${esc(this.t(connection.has_password ? "settings.value.set" : "settings.value.unset"))}</dd>
                   <dt>${esc(this.t("settings.connection.ssl"))}</dt>
                   <dd>${esc(this.t(connection.verify_ssl ? "settings.value.yes" : "settings.value.no"))}</dd>
                 </dl>`
              : `<p class="status">${esc(this.t("settings.connection.none"))}</p>`
          }
          <p class="hint" style="margin:12px 0 0">${esc(this.t("settings.connection.hint"))}</p>
        </div>
      </div>

      <div>
        <h2 class="sec">${esc(this.t("settings.section.mqtt"))}</h2>
        <div class="panel-card">
          ${
            mqtt.mqtt_username || mqtt.mqtt_host
              ? ""
              : `<p class="status" style="margin:0 0 14px">${esc(this.t("settings.mqtt.none"))}</p>`
          }
          <div class="form">
            <div class="field">
              <label for="mqtt-host">${esc(this.t("mqtt.host"))}</label>
              <input id="mqtt-host" type="text" spellcheck="false"
                     value="${esc(mqtt.mqtt_host || "")}" autocomplete="off">
              <span class="hint">${esc(this.t("mqtt.host.hint"))}</span>
            </div>
            <div class="field">
              <label for="mqtt-port">${esc(this.t("mqtt.port"))}</label>
              <input id="mqtt-port" type="number" min="1" max="65535"
                     value="${esc(mqtt.mqtt_port || 1883)}">
            </div>
            <div class="field">
              <label for="mqtt-user">${esc(this.t("mqtt.user"))}</label>
              <input id="mqtt-user" type="text" spellcheck="false"
                     value="${esc(mqtt.mqtt_username || "")}" autocomplete="off">
            </div>
            <div class="field">
              <label for="mqtt-password">${esc(this.t("mqtt.password"))}</label>
              <input id="mqtt-password" type="password" value="" autocomplete="new-password">
              <span class="hint">${esc(
                this.t(mqtt.has_password ? "mqtt.password.set" : "mqtt.password.unset")
              )}</span>
            </div>
            <div class="field">
              <label for="mqtt-tls">${esc(this.t("mqtt.tls"))}</label>
              <select id="mqtt-tls">
                <option value="0" ${mqtt.mqtt_tls ? "" : "selected"}>${esc(
                  this.t("settings.value.no")
                )}</option>
                <option value="1" ${mqtt.mqtt_tls ? "selected" : ""}>${esc(
                  this.t("settings.value.yes")
                )}</option>
              </select>
            </div>
          </div>
          <div class="form" style="margin-top:4px">
            <div class="field" style="grid-column:1/-1">
              <label for="mqtt-api-url">${esc(this.t("mqtt.api.url"))}</label>
              <input id="mqtt-api-url" type="text" spellcheck="false"
                     placeholder="192.168.50.92:18083"
                     value="${esc(mqtt.mqtt_api_url || "")}" autocomplete="off">
              <span class="hint">${esc(this.t("mqtt.api.url.hint"))}</span>
            </div>
            <div class="field">
              <label for="mqtt-api-key">${esc(this.t("mqtt.api.key"))}</label>
              <input id="mqtt-api-key" type="text" spellcheck="false"
                     value="${esc(mqtt.mqtt_api_key || "")}" autocomplete="off">
            </div>
            <div class="field">
              <label for="mqtt-api-secret">${esc(this.t("mqtt.api.secret"))}</label>
              <input id="mqtt-api-secret" type="password" value="" autocomplete="new-password">
              <span class="hint">${esc(
                this.t(mqtt.has_api_secret ? "mqtt.api.secret.set" : "mqtt.api.secret.unset")
              )}</span>
            </div>
          </div>
          <p class="hint" style="margin:0 0 4px">${esc(this.t("mqtt.api.hint"))}</p>
          <p class="hint" style="margin:0 0 12px">${esc(this.t("mqtt.api.replaces"))}</p>

          <div class="actions">
            <button class="btn" data-action="mqtt-save" ${this._mqttSaving ? "disabled" : ""}>${esc(
              this._mqttSaving ? this.t("mqtt.saving") : this.t("mqtt.save")
            )}</button>
            ${
              mqtt.mqtt_username || mqtt.mqtt_host
                ? `<button class="btn btn--ghost" data-action="mqtt-clear" ${
                    this._mqttSaving ? "disabled" : ""
                  }>${esc(this.t("mqtt.clear"))}</button>`
                : ""
            }
          </div>
          ${this.mqttListener(mqtt)}
          <p class="hint" style="margin:12px 0 0">${esc(this.t("mqtt.acl"))}</p>
          <p class="hint" style="margin:8px 0 0">${esc(this.t("mqtt.noReload"))}</p>
        </div>
      </div>

      <div>
        <h2 class="sec">${esc(this.t("settings.section.collection"))}</h2>
        <div class="panel-card"><div class="form">
          ${this.numberField("scan_interval_minutes")}
          ${this.numberField("page_size")}
          ${this.numberField("max_pages")}
        </div></div>
      </div>

      <div>
        <h2 class="sec">${esc(this.t("settings.section.retention"))}</h2>
        <div class="panel-card">
          <div class="form">
            ${this.numberField("retention_days")}
            ${this.boolField("auto_retention")}
          </div>
          ${
            (((this._status || {}).options || {}).auto_retention ?? true)
              ? this.retentionSummary()
              : `<p class="hint" style="margin:12px 0 4px">${esc(this.t("retention.manual"))}</p>
                 <div class="form">
                   ${this.numberField("observation_days")}
                   ${this.numberField("max_observations")}
                   ${this.numberField("scan_history")}
                 </div>`
          }
        </div>
      </div>

      <div>
        <h2 class="sec">${esc(this.t("settings.section.zones"))}</h2>
        <div class="panel-card"><div class="form">
          ${this.textField("zone_trusted_lan")}
          ${this.textField("zone_iot_vlan")}
          ${this.textField("zone_guest")}
        </div></div>
      </div>

      <div>
        <h2 class="sec">${esc(this.t("settings.section.rules"))}</h2>
        <div class="panel-card"><div class="form">
          ${this.textField("domain_rules_path")}
          ${this.textField("check_rules_path")}
        </div></div>
      </div>

      <div class="actions">
        <button class="btn" data-action="save" ${this._saving ? "disabled" : ""}>${esc(
          this._saving ? this.t("settings.saving") : this.t("settings.save")
        )}</button>
        ${
          this._saveStatus
            ? `<span class="status" data-tone="${this._saveStatus.tone}">${esc(this._saveStatus.text)}</span>`
            : ""
        }
      </div>

      <div>
        <h2 class="sec">${esc(this.t("settings.section.system"))}</h2>
        <div class="panel-card"><dl class="kv">
          <dt>${esc(this.t("settings.system.ha"))}</dt><dd class="mono">${esc(status.ha_version || "-")}</dd>
          <dt>${esc(this.t("settings.system.collector"))}</dt><dd class="mono">${esc(
            (this._data && this._data.observed_available) ? "declared + observed" : "declared"
          )}</dd>
          <dt>${esc(this.t("settings.system.lastScan"))}</dt><dd class="mono">${esc(lastScan)}</dd>
          <dt>${esc(this.t("settings.system.observations"))}</dt><dd class="mono">${this.num(store.observations || 0)}</dd>
          <dt>${esc(this.t("settings.system.oldest"))}</dt><dd class="mono">${esc(store.oldest_observation || "-")}</dd>
          <dt>${esc(this.t("settings.system.dbSize"))}</dt><dd class="mono">${esc(bytes)}</dd>
          <dt>${esc(this.t("settings.system.pruned"))}</dt><dd class="mono">${this.num(removed)}</dd>
        </dl></div>
      </div>

      <div>
        <h2 class="sec">${esc(this.t("settings.section.advice"))}</h2>
        <div class="note">
          <div class="note__label">${esc(this.t("settings.advice.items"))}</div>
          <p>${esc(this.t("settings.advice.lead"))}</p>
          ${SCOPE_ITEMS.map(
            (key) => `<p>· ${esc(this.t(`settings.scope.item.${key}`))}</p>`
          ).join("")}
          <p><strong>${esc(this.t("settings.scope.closing"))}</strong></p>
        </div>
        ${this.expander({
          tone: "info",
          title: esc(this.t("settings.guide")),
          body: `<p>${esc(this.t("settings.guide.lead"))}</p><div class="guide">${GUIDE_STEPS.map(
            (n) => `<h4>${esc(this.t(`settings.guide.h.${n}`))}</h4>
              <p>${esc(this.t(`settings.guide.p.${n}`))}</p>`
          ).join("")}</div>`,
        })}
      </div>
    </div>`;
  }

  async saveOptions() {
    if (this._saving) return;
    const host = this.shadowRoot.lastChild;
    const options = {};
    host.querySelectorAll("[data-option]").forEach((input) => {
      const key = input.dataset.option;
      options[key] = input.dataset.bool === "1"
        ? input.value === "1"
        : input.type === "number" ? Number(input.value) : input.value;
    });

    this._saving = true;
    this._saveStatus = null;
    this.setBusy("busy", this.t("busy.saving"), this.t("busy.saving.sub"));
    try {
      await this._hass.callWS({ type: "talos/options/set", options });
    } catch (err) {
      const reason = err && err.message ? err.message : String(err);
      this._saving = false;
      this._saveStatus = { tone: "error", text: this.t("settings.error", { reason }) };
      this.setBusy("error", this.t("busy.saveError"), reason);
      return;
    }

    // Writing the options reloads the integration, and until it is back up
    // every command answers "not ready". Waiting for it beats a fixed delay
    // that is either too short to work or too long to feel alive.
    this.setBusy("busy", this.t("busy.reloading"), this.t("busy.reloading.sub"));
    const ready = await this.waitForReload();
    this._saving = false;
    if (ready) {
      this._saveStatus = { tone: "ok", text: this.t("settings.saved") };
      this.setBusy("ok", this.t("busy.saveOk"), this.t("busy.saveOk.sub"));
    } else {
      this._saveStatus = { tone: "error", text: this.t("settings.error", { reason: "timeout" }) };
      this.setBusy("error", this.t("busy.saveError"), this.t("busy.reloading.sub"));
    }
  }

  /** The state of the listener, in the card rather than at the top of the
   *  page: which route it is taking, what the last scan got out of it, and
   *  the reason when it got nothing. The toast at the top of the view is not
   *  visible from down here, which is how this card came to look frozen. */
  mqttListener(mqtt) {
    const running = this._mqttSaving;
    // A save is answered before the next scan runs, so for a while the stored
    // status still describes the old route. The test result is newer than it
    // is, and showing the old one here would read as the save not working.
    const fresh = this._mqttResult;
    const source = fresh || mqtt;
    const available = fresh ? Boolean(fresh.ok) : Boolean(mqtt.available);
    const tone = running ? "busy" : available ? "ok" : "error";
    const state = running
      ? this.t("mqtt.saving")
      : available
        ? this.t("mqtt.state.ok", {
            clients: this.num(source.clients || 0),
            unmatched: this.num(source.unmatched || 0),
          })
        : (fresh ? fresh.error : mqtt.error) || this.t("mqtt.state.blocked");
    return `<div class="toast" data-tone="${tone}" style="margin:14px 0 0" role="status">
        <span class="toast__dot"></span>
        <span><strong>${esc(this.t("mqtt.listener"))}</strong>
          <span class="toast__sub">${esc(state)}</span></span>
      </div>
      <dl class="kv" style="margin-top:10px">
        <dt>${esc(this.t("mqtt.route"))}</dt>
        <dd>${esc(
          String(source.route || mqtt.route || "session")
            .split("+")
            .map((name) => this.t(`mqtt.route.${name}`))
            .join(" + ")
        )}${
          mqtt.fallback_from
            ? ` · ${this.t("mqtt.fallback", {
                route: this.t(`mqtt.route.${mqtt.fallback_from}`),
              })}`
            : ""
        }</dd>
        <dt>${esc(this.t("mqtt.lastRun"))}</dt>
        <dd class="mono">${esc(this.when((this._status || {}).generated_at))}</dd>
        ${(mqtt.routes || [])
          .map(
            (route) => `<dt>${esc(this.t(`mqtt.route.${route.name}`))}</dt>
              <dd>${
                route.ok
                  ? esc(this.t("mqtt.route.ok", { n: this.num(route.clients) }))
                  : `<span style="color:var(--alert)">${esc(this.t("mqtt.route.fail"))}${
                      route.error ? `: ${esc(route.error)}` : ""
                    }</span>`
              }</dd>`
          )
          .join("")}
      </dl>
      <div class="actions">
        <button class="btn btn--ghost" data-action="mqtt-test" ${this._mqttSaving ? "disabled" : ""}>${esc(
          this.t("mqtt.test")
        )}</button>
      </div>`;
  }

  /** Write the broker account, testing it on the way in.
   *
   *  An empty password field means "keep the stored one": without that rule,
   *  saving the port would wipe the password every time. */
  async saveMqtt(clear = false) {
    if (this._mqttSaving) return;
    const host = this.shadowRoot;
    const value = (id) => (host.querySelector(id) || {}).value || "";
    // Read the form before anything redraws it. setBusy renders, and a render
    // rebuilds these inputs from the stored status, so reading afterwards
    // would send back what was already saved and drop what was just typed.
    const payload = clear
      ? { type: "talos/mqtt/set", clear: true }
      : {
          type: "talos/mqtt/set",
          mqtt_host: value("#mqtt-host").trim(),
          mqtt_port: Number(value("#mqtt-port")) || 1883,
          mqtt_username: value("#mqtt-user").trim(),
          mqtt_password: value("#mqtt-password"),
          mqtt_tls: value("#mqtt-tls") === "1",
          mqtt_api_url: value("#mqtt-api-url").trim(),
          mqtt_api_key: value("#mqtt-api-key").trim(),
          mqtt_api_secret: value("#mqtt-api-secret"),
        };
    this._mqttSaving = true;
    // Renders the card too, so the listener box switches to busy in place.
    this.setBusy("busy", this.t("mqtt.testing"), this.t("mqtt.testing.sub"));

    let result = null;
    try {
      result = await this._hass.callWS(payload);
    } catch (err) {
      result = { ok: false, error: err && err.message ? err.message : String(err) };
    }

    this._mqttSaving = false;
    // Newer than the stored status until the next scan replaces both.
    this._mqttResult = result && (result.ok || result.error) ? result : null;
    if (!result || !result.ok) {
      this.setBusy("error", this.t("mqtt.failed"), (result && result.error) || "");
      return;
    }
    // Writing the entry reloads the integration, same as saving the options.
    await this.waitForReload();
    if (result.cleared) {
      this.setBusy("ok", this.t("mqtt.cleared"), this.t("mqtt.cleared.sub"));
      return;
    }

    // Saved either way. What the bar reports is whether anything answered,
    // and when nothing did it names each route with its own reason, because
    // "rejected the key" and "no route to host" need different fixes.
    const tried = result.tried || [];
    const working = tried.find((item) => item.ok);
    const failures = tried
      .filter((item) => !item.ok)
      .map((item) => `${this.t(`mqtt.route.${item.route}`)}: ${item.error || "-"}`)
      .join(" · ");

    if (!working) {
      this.setBusy(
        "error",
        this.t("mqtt.savedNotWorking"),
        failures || this.t("mqtt.savedNotWorking.sub")
      );
    } else if (working.route === "api") {
      this.setBusy(
        "ok",
        this.t("mqtt.okApi"),
        [this.t("mqtt.okApi.sub", { n: this.num(working.clients) }), failures]
          .filter(Boolean)
          .join(" · ")
      );
    } else if (working.sys_readable) {
      this.setBusy(
        "ok",
        this.t("mqtt.ok"),
        [this.t("mqtt.ok.sub", { n: this.num(working.clients) }), failures]
          .filter(Boolean)
          .join(" · ")
      );
    } else {
      this.setBusy("ok", this.t("mqtt.okNoSys"), this.t("mqtt.okNoSys.sub"));
    }
  }

  /** Run every configured MQTT route now and show each outcome verbatim. */
  async testMqtt() {
    if (this._mqttSaving) return;
    this._mqttSaving = true;
    this.setBusy("busy", this.t("mqtt.testing.now"), this.t("mqtt.testing.now.sub"));
    let facts = null;
    try {
      facts = await this._hass.callWS({ type: "talos/mqtt/test" });
    } catch (err) {
      this._mqttSaving = false;
      this.setBusy("error", this.t("mqtt.failed"), err && err.message ? err.message : String(err));
      return;
    }
    this._mqttSaving = false;
    // Newer than the stored status: show it until the next scan replaces it.
    this._mqttResult = facts;
    if (this._status) this._status.mqtt = { ...(this._status.mqtt || {}), ...facts, mqtt_api_url: facts.api_url || (this._status.mqtt || {}).mqtt_api_url };
    const lines = (facts.routes || [])
      .map((r) => `${this.t(`mqtt.route.${r.name}`)}: ${r.ok ? this.t("mqtt.route.ok", { n: this.num(r.clients) }) : `${this.t("mqtt.route.fail")}${r.error ? ` (${r.error})` : ""}`}`)
      .join(" · ");
    this.setBusy(facts.available ? "ok" : "error", facts.available ? this.t("mqtt.test.done") : this.t("mqtt.test.none"), lines);
    this.render();
  }

  /** Poll until the integration answers again, then reload the whole panel. */
  async waitForReload(attempts = 20, delayMs = 700) {
    for (let attempt = 0; attempt < attempts; attempt += 1) {
      await new Promise((resolve) => window.setTimeout(resolve, delayMs));
      try {
        await this._hass.callWS({ type: "talos/status" });
        await this.load({ quiet: true });
        return true;
      } catch (err) {
        // Still reloading. The next attempt is the only useful reaction.
      }
    }
    return false;
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

    // A manifest declares that an integration needs a cloud service. That is
    // a real edge even with no query log, so the graph is never empty just
    // because nothing has been observed yet.
    const cloudIntegrations = this.cloudIntegrations();

    const grouped = Object.keys(devices).length > GROUP_THRESHOLD;
    const originOf = (deviceId) =>
      grouped ? (devices[deviceId] || {}).integration_id || "?" : deviceId;

    // Every origin is weighed by what it owns, then by the traffic that was
    // actually seen. Ranking on observations alone drew the house that talks
    // and hid the house that does not: a Zigbee branch has no IP and no query
    // log entry by definition, and leaving it out of a picture of the flows
    // said it was not there rather than that it never leaves the hub.
    const weight = new Map();
    Object.keys(devices).forEach((deviceId) => {
      const key = originOf(deviceId);
      weight.set(key, (weight.get(key) || 0) + 1);
    });
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

    // Egress first, because that is what the view is for, then the hubs and
    // brokers the local links end at. Without those, a Zigbee branch reached
    // the transport column and stopped there, which drew a stub instead of
    // the coordinator it actually talks to.
    // Ranked by what arrives at them: queries where they were observed, and
    // the number of links otherwise. A coordinator with ninety nodes hanging
    // off it should not lose its slot to an endpoint nobody uses.
    const arriving = new Map();
    d.conduits.forEach((conduit) => {
      const id = conduit.destination_id;
      arriving.set(id, (arriving.get(id) || 0) + (conduit.query_count || 1));
    });
    const rank = (ids) => ids.sort((a, b) => (arriving.get(b) || 0) - (arriving.get(a) || 0));

    const seen = new Set();
    const egress = [];
    const internal = [];
    d.conduits.forEach((conduit) => {
      const destination = this.destination(conduit.destination_id);
      if (seen.has(conduit.destination_id)) return;
      if (PHONE_HOME.has(destination.kind)) {
        seen.add(conduit.destination_id);
        egress.push(conduit.destination_id);
      } else if (INTERNAL_KINDS.has(destination.kind)) {
        seen.add(conduit.destination_id);
        internal.push(conduit.destination_id);
      }
    });
    rank(egress);
    rank(internal);
    
    // One undisclosed destination per cloud integration that was never seen
    // reaching anything: the dependency is declared, the host is not.
    const seenIntegrations = new Set(
      d.conduits
        .filter((conduit) => conduit.source.kind === "integration")
        .map((conduit) => conduit.source.id)
    );
    const declaredDestinations = cloudIntegrations
      .filter((entryId) => !seenIntegrations.has(entryId))
      .map((entryId) => `undisclosed:${entryId}`);
    // The hubs and brokers get their own slots. Ranking them against the
    // egress would lose them every time on a house with any traffic at all,
    // and then the local branches would end nowhere again.
    const localRows = internal.slice(0, LOCAL_ROWS);
    const outward = [...egress, ...declaredDestinations].slice(0, MAX_ROWS - localRows.length);
    const destinations = [...outward, ...localRows];

    // Every transport the drawn branches actually use, busiest first, so the
    // column is the shape of the install rather than of its egress.
    const transportWeight = new Map();
    origins.forEach((key) => {
      (members.get(key) || []).forEach((id) => {
        const transport = (devices[id] || {}).transport || "unknown";
        transportWeight.set(transport, (transportWeight.get(transport) || 0) + 1);
      });
    });
    const transports = [...transportWeight.entries()]
      .sort((a, b) => b[1] - a[1])
      .slice(0, 8)
      .map(([transport]) => transport);

    // Cloud integrations that own no device still declare a dependency, so
    // they get a node rather than a destination floating unattached.
    const integrations = grouped
      ? []
      : [
          ...new Set([
            ...origins.map((id) => (devices[id] || {}).integration_id).filter(Boolean),
            ...cloudIntegrations.filter(
              (entryId) => !Object.values(devices).some((device) => device.integration_id === entryId)
            ),
          ]),
        ].slice(0, MAX_ROWS);

    return {
      grouped, origins, members, originOf, destinations, transports, integrations,
      devices, withConduits, declaredOnly: !d.conduits.length,
    };
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

    // Four empty bands look like a broken widget. Say what is missing instead.
    if (!model.origins.length && !model.destinations.length) {
      const note = el("text", {
        class: "n-sub", x: 490, y: 280, "text-anchor": "middle",
      });
      note.textContent = this.t("graph.empty");
      svg.appendChild(note);
      return;
    }

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
      const outward = PHONE_HOME.has(destination.kind);
      // A link to a hub or a broker is drawn too, solid and in the local
      // colour: it is declared, it is inside the house, and without it the
      // radio branches reached the transport column and stopped there.
      if (!outward && !INTERNAL_KINDS.has(destination.kind)) return;
      const to = positions[`destination:${conduit.destination_id}`];
      if (!to) return;

      if (conduit.source.kind === "device") {
        const originId = model.originOf(conduit.source.id);
        const isKey =
          outward &&
          conduit.evidence === "observed" &&
          d.matrix.local_egress.includes(conduit.source.id);
        line(
          positions[`origin:${originId}`],
          to,
          this.linkColour(conduit, destination, isKey),
          outward ? (conduit.evidence === "inherited" ? "1.5 4" : "6 4") : null,
          isKey ? 2 : 1.4
        );
      } else if (conduit.source.kind === "integration") {
        // Grouped, the integration is the origin node itself; ungrouped it has
        // a column of its own. Either way the edge has somewhere to start.
        const from =
          positions[`integration:${conduit.source.id}`] ||
          positions[`origin:${conduit.source.id}`];
        if (from) {
          line(from, to, this.linkColour(conduit, destination, false), null, 1.2);
        }
      }
    });

    // Declared dependencies: solid, because a manifest states them outright.
    model.destinations
      .filter((id) => String(id).startsWith("undisclosed:"))
      .forEach((id) => {
        const entryId = String(id).slice(12);
        const to = positions[`destination:${id}`];
        const from =
          positions[`integration:${entryId}`] || positions[`origin:${entryId}`];
        if (from && to) line(from, to, "var(--k-vendor)", null, 1.6);
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
          sub = [
            integration.iot_class,
            this.t(`role.${integration.role || "unknown"}`),
            integration.state && integration.state !== "loaded"
              ? this.t("state.notLoaded")
              : "",
            integration.endpoint || "",
          ]
            .filter(Boolean)
            .join(" · ");
          colour = (integration.iot_class || "").startsWith("cloud") ? "var(--k-vendor)" : "var(--k-local)";
        } else if (column.key === "destination") {
          const destination = this.destination(id);
          // An undisclosed dependency is named after who needs it, since the
          // host is precisely the thing that is not known.
          label = destination.undisclosed ? destination.vendor : destination.fqdn;
          sub = destination.undisclosed
            ? destination.fqdn
            : this.t(`kind.${destination.kind}`);
          colour = destination.undisclosed
            ? "var(--k-vendor)"
            : this.kindColour(destination.kind);
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
