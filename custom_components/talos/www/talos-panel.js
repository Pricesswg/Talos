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

    "base.title": "Panoramica di sicurezza",
    "base.lead":
      "Due misure indipendenti, tenute separate perché richiedono interventi diversi: la continuità del sistema in assenza di connettività, e le comunicazioni dei dispositivi verso destinazioni esterne.",
    "base.offline.label": "Continuità offline",
    "base.offline.unit": "/{total} entità",
    "base.offline.stops": "<strong>{n} entità</strong> cessano di funzionare.",
    "base.offline.none": "Nessuna entità dipende da servizi cloud.",
    "base.offline.unclassified": "{n} non classificate.",
    "base.exposure.label": "Comunicazioni esterne",
    "base.exposure.unit": "/{total} dispositivi",
    "base.exposure.local":
      "<strong>{n}</strong> risultano locali a Home Assistant ma contattano comunque il produttore.",
    "base.exposure.none": "Nessun dispositivo locale risulta contattare il produttore.",
    "base.exposure.inherited": "{n} esposti tramite un hub.",
    "base.unverified.label": "Controlli non eseguibili",
    "base.unverified.unit": "controlli",
    "base.unverified.note":
      "Non superati e non falliti: i dati disponibili non consentono di esprimersi. <strong>Non vanno conteggiati fra gli esiti positivi.</strong>",
    "base.findings": "Problematiche principali",
    "base.limits.label": "Ambito dell'analisi",
    "base.limits.scope":
      "Talos osserva a quali indirizzi i dispositivi chiedono la risoluzione DNS. Non ispeziona il contenuto del traffico, non ne misura il volume, non esegue scansioni di porte, non tenta credenziali e non modifica alcuna configurazione. Ogni sorgente è interrogata in sola lettura.",
    "base.limits.responsibility":
      "Restano fuori dall'analisi e a carico dell'operatore: la segmentazione della rete, le credenziali dei dispositivi e dei servizi, gli aggiornamenti firmware, l'esposizione di Home Assistant verso internet e il traffico che cifra anche le proprie richieste DNS. Un esito privo di rilievi indica assenza di evidenze, non assenza di rischio.",

    "banner.declared":
      "<strong>Solo dati dichiarati.</strong> {reason}. Questa scansione contiene ciò che Home Assistant dichiara di sé: nessuna colonna “parlano fuori casa” è stata verificata, quindi le caselle vuote non significano assenza di traffico.",
    "banner.noAdguard": "AdGuard Home non è configurato",

    "find.contacted": " Contattati: <strong>{list}</strong>.",
    "find.queries": "{n} query",
    "find.severity": "severità {level}",
    "find.offline.title": "Dipendenza da {vendor} in assenza di connettività",
    "find.offline.body":
      "In assenza di connettività cessano di funzionare {list}. È il comportamento previsto di questi servizi.",
    "find.offline.entities": "{n} entità ({vendor})",
    "find.offline.do":
      "<b>Nessun intervento necessario.</b> Da valutare solo se una di queste entità concorre a una funzione critica, per esempio un allarme allagamento.",
    "find.clean.title": "Nessun rilievo di severità alta o media",
    "find.clean.body":
      "{passed} controlli superati. <strong>{unverified} non erano eseguibili</strong> e non concorrono all'esito.",

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
      "Correlati <strong class=\"mono\">{done}/{total}</strong> dispositivi ({pct}%, metodo <span class=\"mono\">{method}</span>). I non correlati potrebbero avere egress non osservabile: la casella in alto a destra è un <em>minimo</em>, non un totale.",
    "adv.correlation.infra":
      " {n} dispositivi hanno contattato solo servizi di orario o aggiornamento: restano nella colonna silenziosa.",
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
    "graph.empty": "Nessun flusso da disegnare: questa scansione non contiene osservazioni, quindi non ci sono destinazioni note.",
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

    "mode.settings": "Impostazioni",
    "settings.title": "Impostazioni",
    "settings.lead":
      "Parametri di raccolta e ritenzione. Le modifiche vengono applicate alla scansione successiva e comportano un ricaricamento dell'integrazione.",
    "settings.section.language": "Lingua",
    "settings.section.connection": "Connessione ad AdGuard Home",
    "settings.section.collection": "Raccolta",
    "settings.section.retention": "Ritenzione dei dati",
    "settings.section.zones": "Zone di rete",
    "settings.section.rules": "File di regole",
    "settings.section.system": "Sistema",
    "settings.language.auto": "Automatica (segue Home Assistant)",
    "settings.language.hint":
      "La scelta vale solo per questo browser. L'interfaccia dell'integrazione segue invece la lingua di Home Assistant.",
    "settings.connection.hint":
      "Indirizzo e credenziali non sono modificabili da qui. Si cambiano da Impostazioni, Dispositivi e servizi, Talos, menu a tre puntini, Riconfigura: la password non transita mai da questa pagina.",
    "settings.connection.none": "Non configurata: il report resta solo dichiarativo.",
    "settings.connection.url": "Indirizzo",
    "settings.connection.user": "Utente",
    "settings.connection.password": "Password",
    "settings.connection.ssl": "Verifica certificato SSL",
    "settings.value.set": "impostata",
    "settings.value.unset": "non impostata",
    "settings.value.yes": "si",
    "settings.value.no": "no",
    "settings.value.empty": "non impostato",
    "settings.save": "Salva",
    "settings.saving": "Salvataggio in corso",
    "settings.saved": "Impostazioni salvate. Ricaricamento dell'integrazione in corso.",
    "settings.error": "Salvataggio non riuscito: {reason}",
    "settings.range": "da {min} a {max}",
    "opt.scan_interval_minutes": "Intervallo di scansione (minuti)",
    "opt.page_size": "Record per pagina del query log",
    "opt.max_pages": "Pagine massime per scansione",
    "opt.observation_days": "Dimentica le osservazioni dopo (giorni)",
    "opt.max_observations": "Osservazioni massime conservate",
    "opt.scan_history": "Snapshot di scansione conservati",
    "opt.zone_trusted_lan": "Subnet della LAN di fiducia",
    "opt.zone_iot_vlan": "Subnet della VLAN IoT",
    "opt.zone_guest": "Subnet della rete ospiti",
    "opt.domain_rules_path": "File di regole domini aggiuntive",
    "opt.check_rules_path": "File di controlli alternativo",
    "opt.hint.max_observations":
      "E' questo il limite che tiene a bada la dimensione del database.",
    "opt.hint.zone_trusted_lan":
      "Uno o piu' intervalli CIDR separati da virgola, per esempio 192.168.50.0/24. Finche' restano vuoti, i controlli sulle zone si dichiarano non eseguibili invece di risultare superati.",
    "opt.hint.domain_rules_path":
      "Percorso assoluto a un file JSON o YAML. Le regole si aggiungono a quelle predefinite, non le sostituiscono.",
    "settings.system.ha": "Versione di Home Assistant",
    "settings.system.collector": "Modalita' di raccolta",
    "settings.system.lastScan": "Ultima scansione",
    "settings.system.observations": "Osservazioni memorizzate",
    "settings.system.oldest": "Osservazione piu' vecchia",
    "settings.system.dbSize": "Dimensione del database",
    "settings.system.pruned": "Righe rimosse all'ultima potatura",
    "mode.map": "Mappa",
    "map.title": "Mappa dei collegamenti",
    "map.lead":
      "Come i dispositivi arrivano a Home Assistant, raggruppati per trasporto e per integrazione. Questa vista usa solo dati dichiarati dal registry: non richiede AdGuard e non dipende dalle osservazioni.",
    "map.summary": "{devices} dispositivi · {integrations} integrazioni · {transports} trasporti",
    "map.devices": "{n} dispositivi",
    "map.entities": "{n} entita'",
    "map.hubs": "Hub e dispositivi collegati",
    "map.hubs.lead":
      "Dispositivi che ne servono altri. Un figlio non ha un indirizzo proprio: raggiunge la rete attraverso il padre, ed e' da li' che eredita la propria esposizione.",
    "map.hub.children": "{n} collegati",
    "map.empty": "Nessun dispositivo nel registry.",
    "map.noHubs": "Nessuna gerarchia via_device dichiarata dalle integrazioni.",
    "map.showDevices": "Mostra i dispositivi",
    "transport.zigbee": "Zigbee",
    "transport.zwave": "Z-Wave",
    "transport.wifi": "Wi-Fi",
    "transport.ethernet": "Ethernet",
    "transport.thread": "Thread",
    "transport.matter": "Matter",
    "transport.ble": "Bluetooth LE",
    "transport.virtual": "Virtuale",
    "transport.unknown": "Non determinato",
    "map.search": "Cerca un dispositivo o un'integrazione",
    "map.reset": "Reimposta la vista",
    "map.hint":
      "Rotella per lo zoom, trascina per spostarti. Clicca un'integrazione per aprirne i dispositivi.",
    "map.legend.core": "Home Assistant",
    "map.legend.transport": "Trasporto",
    "map.legend.integration": "Integrazione",
    "map.legend.device": "Dispositivo",
    "map.legend.hub": "Hub con dispositivi collegati",
    "map.truncated": "+{n} non disegnati",
    "map.fullList": "Elenco completo per trasporto",
    "map.matches": "{n} corrispondenze",
    "map.noMatches": "Nessuna corrispondenza",
    "map.detail": "Dettaglio",
    "map.detail.less": "Meno dettaglio",
    "map.detail.more": "Piu' dettaglio",
    "map.detail.1": "Trasporti",
    "map.detail.2": "Integrazioni",
    "map.detail.3": "Dispositivi",
    "map.zoomHint": "Le etichette dei dispositivi compaiono avvicinando lo zoom.",
    "map.filters": "Filtra per trasporto",
    "map.all": "Tutti",
    "map.scope.transport": "Solo {name}",
    "map.scope.integration": "Solo i dispositivi di {name}",
    "map.clearScope": "Rimuovi il filtro",
    "map.click.integration": "Clicca un'integrazione per isolarne i dispositivi.",
    "map.filtered": "{n} dispositivi corrispondono",
    "map.origins": "Sorgenti",
    "map.origin.own": "diretto",
    "map.legend.origin": "Sorgente dei dati",
    "map.legend.bridge": "Collegamento fra integrazioni",
    "map.bridges": "{n} collegamenti fra integrazioni",
    "flows.undisclosed": "host non dichiarato",
    "flows.declaredNote":
      "Senza query log restano le sole dipendenze dichiarate dai manifest: si sa che l'integrazione ha bisogno di un servizio esterno, non a quale host si rivolge. Gli archi tratteggiati compariranno quando ci saranno osservazioni.",
    "role.aggregator": "Aggregatore",
    "role.streaming": "Streaming",
    "role.unknown": "",
    "map.roles": "Filtra per ruolo",
    "map.scope.role": "Solo {name}",
    "section.collapse": "Comprimi o espandi",
    "state.notLoaded": "non caricata",
    "base.offline.unavailable":
      "<strong>{n} entità</strong> non sono disponibili adesso: la loro integrazione non è caricata, quindi non funzionano né con internet né senza.",
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

    "base.title": "Security overview",
    "base.lead":
      "Two independent measures, kept apart because they call for different remedies: system continuity without connectivity, and device communications towards external destinations.",
    "base.offline.label": "Offline continuity",
    "base.offline.unit": "/{total} entities",
    "base.offline.stops": "<strong>{n} entities</strong> cease to function.",
    "base.offline.none": "No entity depends on a cloud service.",
    "base.offline.unclassified": "{n} unclassified.",
    "base.exposure.label": "External communications",
    "base.exposure.unit": "/{total} devices",
    "base.exposure.local":
      "<strong>{n}</strong> are local to Home Assistant yet still contact the vendor.",
    "base.exposure.none": "No local device is contacting its vendor.",
    "base.exposure.inherited": "{n} exposed through a hub.",
    "base.unverified.label": "Checks not runnable",
    "base.unverified.unit": "checks",
    "base.unverified.note":
      "Neither passed nor failed: the available data does not allow a verdict. <strong>They must not be counted among the positive results.</strong>",
    "base.findings": "Key findings",
    "base.limits.label": "Scope of the analysis",
    "base.limits.scope":
      "Talos observes which addresses devices ask to resolve. It does not inspect traffic content, does not measure volume, performs no port scanning, attempts no credentials and modifies no configuration. Every source is read only.",
    "base.limits.responsibility":
      "Outside the analysis and the operator's responsibility: network segmentation, device and service credentials, firmware updates, Home Assistant's exposure to the internet, and traffic that encrypts its own DNS queries. A result with no findings indicates an absence of evidence, not an absence of risk.",

    "banner.declared":
      "<strong>Declared data only.</strong> {reason}. This scan holds what Home Assistant declares about itself: no “talking outside” column has been verified, so an empty cell does not mean an absence of traffic.",
    "banner.noAdguard": "AdGuard Home is not configured",

    "find.contacted": " Contacted: <strong>{list}</strong>.",
    "find.queries": "{n} queries",
    "find.severity": "{level} severity",
    "find.offline.title": "Dependency on {vendor} without connectivity",
    "find.offline.body": "Without connectivity {list} cease to function. This is the expected behaviour of these services.",
    "find.offline.entities": "{n} entities ({vendor})",
    "find.offline.do":
      "<b>No action required.</b> Worth reviewing only if one of these entities supports a critical function, for example a water leak alarm.",
    "find.clean.title": "No high or medium severity findings",
    "find.clean.body":
      "{passed} checks passed. <strong>{unverified} could not run</strong> and do not contribute to the result.",

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
    "adv.cell.unclassified": "iot_class calculated, assumed_state or missing: counted neither as local nor as cloud.",
    "adv.correlation":
      "Correlated <strong class=\"mono\">{done}/{total}</strong> devices ({pct}%, method <span class=\"mono\">{method}</span>). The uncorrelated ones may have egress that cannot be observed: the top-right cell is a <em>minimum</em>, not a total.",
    "adv.correlation.infra":
      " {n} devices only reached a time or update service: they stay in the silent column.",
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
    "graph.empty": "Nothing to draw: this scan holds no observations, so there are no known destinations.",
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

    "mode.settings": "Settings",
    "settings.title": "Settings",
    "settings.lead":
      "Collection and retention parameters. Changes take effect on the next scan and reload the integration.",
    "settings.section.language": "Language",
    "settings.section.connection": "AdGuard Home connection",
    "settings.section.collection": "Collection",
    "settings.section.retention": "Data retention",
    "settings.section.zones": "Network zones",
    "settings.section.rules": "Rule files",
    "settings.section.system": "System",
    "settings.language.auto": "Automatic (follows Home Assistant)",
    "settings.language.hint":
      "This choice applies to this browser only. The integration's own interface follows the Home Assistant language.",
    "settings.connection.hint":
      "The address and credentials cannot be changed here. Use Settings, Devices and services, Talos, the three dot menu, Reconfigure: the password never travels through this page.",
    "settings.connection.none": "Not configured: the report stays declared only.",
    "settings.connection.url": "Address",
    "settings.connection.user": "Username",
    "settings.connection.password": "Password",
    "settings.connection.ssl": "Verify the SSL certificate",
    "settings.value.set": "set",
    "settings.value.unset": "not set",
    "settings.value.yes": "yes",
    "settings.value.no": "no",
    "settings.value.empty": "not set",
    "settings.save": "Save",
    "settings.saving": "Saving",
    "settings.saved": "Settings saved. The integration is reloading.",
    "settings.error": "Could not save: {reason}",
    "settings.range": "{min} to {max}",
    "opt.scan_interval_minutes": "Scan interval (minutes)",
    "opt.page_size": "Query log records per page",
    "opt.max_pages": "Maximum pages per scan",
    "opt.observation_days": "Forget observations after (days)",
    "opt.max_observations": "Maximum stored observations",
    "opt.scan_history": "Scan snapshots kept",
    "opt.zone_trusted_lan": "Trusted LAN subnet",
    "opt.zone_iot_vlan": "IoT VLAN subnet",
    "opt.zone_guest": "Guest network subnet",
    "opt.domain_rules_path": "Extra domain rules file",
    "opt.check_rules_path": "Alternative check list file",
    "opt.hint.max_observations":
      "This is the limit that bounds the size of the database.",
    "opt.hint.zone_trusted_lan":
      "One or more comma separated CIDR ranges, for example 192.168.50.0/24. While they are empty, the zone checks declare themselves unrunnable rather than passing.",
    "opt.hint.domain_rules_path":
      "Absolute path to a JSON or YAML file. The rules are added to the built in list, they do not replace it.",
    "settings.system.ha": "Home Assistant version",
    "settings.system.collector": "Collection mode",
    "settings.system.lastScan": "Last scan",
    "settings.system.observations": "Stored observations",
    "settings.system.oldest": "Oldest observation",
    "settings.system.dbSize": "Database size",
    "settings.system.pruned": "Rows removed at the last prune",
    "mode.map": "Map",
    "map.title": "Connection map",
    "map.lead":
      "How devices reach Home Assistant, grouped by transport and by integration. This view uses declared registry data only: it needs no AdGuard and does not depend on observations.",
    "map.summary": "{devices} devices · {integrations} integrations · {transports} transports",
    "map.devices": "{n} devices",
    "map.entities": "{n} entities",
    "map.hubs": "Hubs and the devices behind them",
    "map.hubs.lead":
      "Devices that serve others. A child has no address of its own: it reaches the network through its parent, and that is where its exposure is inherited from.",
    "map.hub.children": "{n} behind it",
    "map.empty": "No devices in the registry.",
    "map.noHubs": "No via_device hierarchy declared by the integrations.",
    "map.showDevices": "Show the devices",
    "transport.zigbee": "Zigbee",
    "transport.zwave": "Z-Wave",
    "transport.wifi": "Wi-Fi",
    "transport.ethernet": "Ethernet",
    "transport.thread": "Thread",
    "transport.matter": "Matter",
    "transport.ble": "Bluetooth LE",
    "transport.virtual": "Virtual",
    "transport.unknown": "Undetermined",
    "map.search": "Search a device or an integration",
    "map.reset": "Reset the view",
    "map.hint":
      "Wheel to zoom, drag to pan. Click an integration to open its devices.",
    "map.legend.core": "Home Assistant",
    "map.legend.transport": "Transport",
    "map.legend.integration": "Integration",
    "map.legend.device": "Device",
    "map.legend.hub": "Hub with devices behind it",
    "map.truncated": "+{n} not drawn",
    "map.fullList": "Full list by transport",
    "map.matches": "{n} matches",
    "map.noMatches": "No match",
    "map.detail": "Detail",
    "map.detail.less": "Less detail",
    "map.detail.more": "More detail",
    "map.detail.1": "Transports",
    "map.detail.2": "Integrations",
    "map.detail.3": "Devices",
    "map.zoomHint": "Device labels appear as you zoom in.",
    "map.filters": "Filter by transport",
    "map.all": "All",
    "map.scope.transport": "{name} only",
    "map.scope.integration": "Devices of {name} only",
    "map.clearScope": "Clear the filter",
    "map.click.integration": "Click an integration to isolate its devices.",
    "map.filtered": "{n} devices match",
    "map.origins": "Sources",
    "map.origin.own": "direct",
    "map.legend.origin": "Data source",
    "map.legend.bridge": "Link between integrations",
    "map.bridges": "{n} links between integrations",
    "flows.undisclosed": "host not declared",
    "flows.declaredNote":
      "Without a query log only the dependencies the manifests declare remain: the integration is known to need an external service, not which host it reaches. Dashed edges appear once there are observations.",
    "role.aggregator": "Aggregator",
    "role.streaming": "Streaming",
    "role.unknown": "",
    "map.roles": "Filter by role",
    "map.scope.role": "{name} only",
    "section.collapse": "Collapse or expand",
    "state.notLoaded": "not loaded",
    "base.offline.unavailable":
      "<strong>{n} entities</strong> are unavailable right now: their integration is not loaded, so they work neither with the internet nor without it.",
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

  --t-zigbee: #2f7d6a;
  --t-zwave: #64768c;
  --t-wifi: #16697f;
  --t-ethernet: #6b5aa0;
  --t-thread: #4a7d3f;
  --t-matter: #2b7f8c;
  --t-ble: #3f6ea0;
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
    --k-local: #52b195; --k-infra: #93a5bd; --k-vendor: #c07dbb; --k-unknown: #8d9799;
    --alert: #ff6f60; --attention: #d5a343;
    --t-zigbee: #52b195; --t-zwave: #93a5bd; --t-wifi: #52b2c8;
    --t-ethernet: #a396d6; --t-thread: #7fbb70; --t-matter: #63c3d1;
    --t-ble: #7ba3d8; --t-virtual: #bdae94; --t-unknown: #8d9799;
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
svg.map text { font-family: var(--font-sans); fill: var(--ink); pointer-events: none; }
svg.map .lbl { font-size: 12px; }
svg.map .lbl--device, svg.map .sub--device { display: none; }
svg.map[data-zoom="mid"] .lbl--device { display: inline; }
svg.map[data-zoom="near"] .lbl--device, svg.map[data-zoom="near"] .sub--device { display: inline; }
svg.map .node--match .lbl--device, svg.map .node--match .sub--device { display: inline; }
svg.map .lbl--core { font-size: 15px; font-weight: 600; }
svg.map .lbl--transport { font-size: 13.5px; font-weight: 500; }
svg.map .sub { font-size: 10px; fill: var(--ink-mute); font-family: var(--font-mono); }
svg.map .link { fill: none; stroke-opacity: .45; }
svg.map .link--bridge { stroke-opacity: .8; stroke-dasharray: 7 5; }

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

const PHONE_HOME = new Set(["vendor_cloud", "telemetry", "push_service", "cdn", "unknown"]);
const SEVERITY_TONE = { high: "alert", medium: "attention", low: "info" };

/* Above this many devices carrying a conduit, the first column groups by
 * integration. A hand-laid SVG stays readable at a few dozen nodes and not at
 * a few hundred, and a truncated picture that hides the shape is worse than a
 * grouped one that shows it. */
const GROUP_THRESHOLD = 10;
const MAX_ROWS = 10;

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
    this._pinned = new Map();
    this._view = { k: 1, x: 0, y: 0 };
    // Reading storage can throw in a private window or with site data blocked.
    try {
      this._langOverride = window.localStorage.getItem("talos.lang") || "";
    } catch (err) {
      this._langOverride = "";
    }
  }

  resolveLang(hass) {
    if (this._langOverride && I18N[this._langOverride]) return this._langOverride;
    const raw = (hass && ((hass.locale && hass.locale.language) || hass.language)) || "";
    const base = String(raw).toLowerCase().split("-")[0];
    return I18N[base] ? base : FALLBACK_LANG;
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
    this.render();
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

    host.innerHTML =
      this.toolbar() +
      `<div class="wrap">` +
      (this._mode === "base"
        ? this.viewBase()
        : this._mode === "map"
          ? this.viewMap()
          : this._mode === "settings"
            ? this.viewSettings()
            : this.viewAdvanced()) +
      `</div>`;

    host.querySelectorAll("[data-mode]").forEach((button) => {
      button.addEventListener("click", () => {
        this._mode = button.dataset.mode;
        this.render();
      });
    });
    const refresh = host.querySelector("[data-action='refresh']");
    if (refresh) refresh.addEventListener("click", () => this.refresh());

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
        this._pinned.clear();
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
          this._pinned.clear();
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
          this._pinned.clear();
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
          <button data-mode="map" aria-pressed="${this._mode === "map"}">${esc(this.t("mode.map"))}</button>
          <button data-mode="advanced" aria-pressed="${this._mode === "advanced"}">${esc(this.t("mode.advanced"))}</button>
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
          <div class="stat__note">${this.t("base.unverified.note")}</div>
        </div>
      </div>

      <div>
        <h2 class="sec">${esc(this.t("base.findings"))}</h2>
        ${this.findings()}
      </div>

      <div class="note">
        <div class="note__label">${esc(this.t("base.limits.label"))}</div>
        <p>${this.t("base.limits.scope")}</p>
        <p>${this.t("base.limits.responsibility")}</p>
      </div>
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
          label, sub: integration.domain || "", colour,
          count: entry.devices.length, open, ref: entry.id,
          hit: matches(label) || matches(integration.domain) || item.deviceMatch,
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

    // A dragged node keeps where it was put, and the rest settle around it.
    nodes.forEach((node) => {
      const pin = this._pinned.get(node.id);
      if (pin) {
        node.x = pin.x;
        node.y = pin.y;
        node.fixed = true;
      }
    });
    this.relax(nodes);

    return { nodes, links, query, hits: nodes.filter((n) => n.hit).length };
  }

  /** Push overlapping nodes apart, then slide them back onto their ring.
   *
   * Deterministic, not a simulation: it runs a fixed number of passes from a
   * fixed starting layout, so the picture settles the same way every time.
   * Pinned and central nodes never move. */
  relax(nodes, iterations = 12) {
    const movable = nodes.filter((node) => !node.fixed && node.kind !== "core" && node.rx);
    if (!movable.length) return;

    for (let pass = 0; pass < iterations; pass += 1) {
      for (let i = 0; i < nodes.length; i += 1) {
        for (let j = i + 1; j < nodes.length; j += 1) {
          const a = nodes[i];
          const b = nodes[j];
          const minimum = (a.pad || 14) + (b.pad || 14);
          let dx = b.x - a.x;
          let dy = b.y - a.y;
          const distance = Math.hypot(dx, dy) || 0.001;
          if (distance >= minimum) continue;
          const push = (minimum - distance) / 2;
          dx /= distance;
          dy /= distance;
          if (!a.fixed && a.kind !== "core") {
            a.x -= dx * push;
            a.y -= dy * push;
          }
          if (!b.fixed && b.kind !== "core") {
            b.x += dx * push;
            b.y += dy * push;
          }
        }
      }
      movable.forEach((node) => {
        const angle = Math.atan2(node.y / node.ry, node.x / node.rx);
        node.x = Math.cos(angle) * node.rx;
        node.y = Math.sin(angle) * node.ry;
      });
    }
  }

  drawMap(svg, animate = false) {
    const NS = "http://www.w3.org/2000/svg";
    const el = (name, attrs) => {
      const node = document.createElementNS(NS, name);
      Object.entries(attrs || {}).forEach(([key, value]) => node.setAttribute(key, value));
      return node;
    };
    while (svg.firstChild) svg.removeChild(svg.firstChild);
    svg.classList.toggle("animate", Boolean(animate));

    svg.setAttribute("preserveAspectRatio", "xMidYMid meet");

    const view = this._view || (this._view = { k: 1, x: 0, y: 0 });
    const root = el("g", {});
    svg.appendChild(root);
    const applyView = () => {
      root.setAttribute("transform", `translate(${view.x},${view.y}) scale(${view.k})`);
      // Label density follows the zoom, the way a map reveals street names.
      // A class swap, so panning stays cheap.
      svg.dataset.zoom = view.k >= 2.2 ? "near" : view.k >= 1.4 ? "mid" : "far";
    };
    applyView();

    const rect = svg.getBoundingClientRect();
    const stretch = Math.min(1.7, Math.max(1, (rect.width || 1200) / (rect.height || 620) / 1.25));
    const { nodes, links, query } = this.mapLayout(stretch);
    const byId = new Map(nodes.map((node) => [node.id, node]));
    const dimmed = Boolean(query);

    // Fit the box to what is actually drawn, so a collapsed map is not a
    // small dot in a large empty square. Once the user has panned or zoomed,
    // the box stays put: refitting under their hands would be maddening.
    const untouched = view.k === 1 && view.x === 0 && view.y === 0 && !this._pinned.size;
    if (untouched || !this._mapBox) {
      const pad = 200;
      const xs = nodes.map((node) => node.x);
      const ys = nodes.map((node) => node.y);
      const minX = Math.min(...xs) - pad;
      const minY = Math.min(...ys) - pad;
      this._mapBox = [minX, minY, Math.max(...xs) + pad - minX, Math.max(...ys) + pad - minY];
    }
    svg.setAttribute("viewBox", this._mapBox.join(" "));

    const linkLayer = el("g", {});
    root.appendChild(linkLayer);
    links.forEach((link) => {
      const from = byId.get(link.from);
      const to = byId.get(link.to);
      if (!from || !to) return;
      // Curved towards the centre so the branches read as branches.
      // A bridge arcs the other way, so it reads as a shortcut across the
      // tree rather than another branch of it.
      const bow = link.bridge ? 1.35 : 0.72;
      const path = el("path", {
        class: link.bridge ? "link link--bridge" : "link",
        d: `M${from.x},${from.y} Q${((from.x + to.x) / 2) * bow},${((from.y + to.y) / 2) * bow} ${to.x},${to.y}`,
        stroke: link.colour,
        "stroke-width": link.width,
        pathLength: "1",
      });
      path.style.animationDelay = `${link.bridge ? 380 : 90}ms`;
      if (dimmed && !(to.hit || from.hit)) path.classList.add("dim");
      linkLayer.appendChild(path);
    });

    nodes.forEach((node) => {
      const group = el("g", { class: "node", "data-id": node.id });
      if (dimmed && !node.hit) group.classList.add("dim");
      if (node.hit) group.classList.add("node--match");

      if (node.kind === "core") {
        group.appendChild(el("rect", {
          x: node.x - 22, y: node.y - 22, width: 44, height: 44, rx: 12,
          fill: node.colour,
        }));
      } else if (node.kind === "more") {
        // Nothing but the label: it is a note, not a thing on the network.
      } else {
        const radius =
          node.kind === "transport" ? 13
          : node.kind === "integration" ? 8
          : node.kind === "origin" ? 6 : 4.5;
        const mark = el("circle", {
          class: "node__mark",
          cx: node.x, cy: node.y, r: radius,
          fill:
            node.kind === "origin" || (node.kind === "device" && node.isHub)
              ? "var(--surface)"
              : node.colour,
          stroke: node.colour,
          "stroke-width":
            node.kind === "origin" ? 2 : node.kind === "device" && node.isHub ? 2.5 : 0,
        });
        if (node.kind === "origin") mark.setAttribute("stroke-dasharray", "3 2");
        group.appendChild(mark);
        if (node.kind === "integration" && node.open) {
          group.appendChild(el("circle", {
            cx: node.x, cy: node.y, r: radius + 4,
            fill: "none", stroke: node.colour, "stroke-width": 1, "stroke-opacity": .5,
          }));
        }
      }

      // Labels sit horizontally under the node. Radial text reads badly on
      // the left half and is worse to scan than a straight line of names.
      const below = node.kind === "core" ? 40
        : node.kind === "transport" ? 26
        : node.kind === "integration" ? 20
        : node.kind === "origin" ? 17 : 13;
      const isDevice = node.kind === "device" || node.kind === "more";

      const label = el("text", {
        class:
          (node.kind === "core"
            ? "lbl lbl--core"
            : node.kind === "transport"
              ? "lbl lbl--transport"
              : "lbl") + (isDevice ? " lbl--device" : ""),
        x: node.x,
        y: node.y + below,
        "text-anchor": "middle",
      });
      const text = String(node.label || "");
      label.textContent = text.length > 24 ? `${text.slice(0, 23)}…` : text;
      group.appendChild(label);

      if (node.sub && node.kind !== "core") {
        const sub = el("text", {
          class: "sub" + (isDevice ? " sub--device" : ""),
          x: node.x,
          y: node.y + below + 12,
          "text-anchor": "middle",
        });
        sub.textContent = node.kind === "integration" ? `${node.sub} · ${node.count}` : node.sub;
        group.appendChild(sub);
      }

      const depth =
        node.kind === "core" ? 0
        : node.kind === "transport" ? 1
        : node.kind === "integration" ? 2
        : node.kind === "origin" ? 3 : 4;
      group.style.animationDelay = `${depth * 110}ms`;

      if (node.kind === "integration") {
        // A generous invisible target: the dot itself is 8px.
        const hit = el("circle", { class: "hit", cx: node.x, cy: node.y, r: 16 });
        group.appendChild(hit);
        group.addEventListener("click", (event) => {
          if (this._dragMoved) return; // a drag, not a click
          event.stopPropagation();
          const current = this._scope;
          this._scope =
            current && current.kind === "integration" && current.id === node.ref
              ? null
              : { kind: "integration", id: node.ref };
          this._view = { k: 1, x: 0, y: 0 };
          this._mapBox = null;
          this._pinned.clear();
          this.render();
        });
      }

      root.appendChild(group);
    });

    this.attachMapControls(svg, view, applyView);
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
      // Zoom towards the pointer rather than the origin.
      const rect = svg.getBoundingClientRect();
      const px = event.clientX - rect.left - rect.width / 2;
      const py = event.clientY - rect.top - rect.height / 2;
      view.x = px - ((px - view.x) * next) / view.k;
      view.y = py - ((py - view.y) * next) / view.k;
      view.k = next;
      applyView();
    }, { passive: false });

    let panning = null;
    let dragging = null;
    let frame = 0;

    svg.addEventListener("pointerdown", (event) => {
      const target = event.target.closest && event.target.closest("g.node");
      this._dragMoved = false;
      if (target && target.dataset.id) {
        // Grab the node itself; the rest of the graph settles around it.
        dragging = { id: target.dataset.id };
        svg.setPointerCapture(event.pointerId);
        return;
      }
      panning = { x: event.clientX - view.x, y: event.clientY - view.y };
      svg.classList.add("dragging");
      svg.setPointerCapture(event.pointerId);
    });

    svg.addEventListener("pointermove", (event) => {
      if (dragging) {
        const point = toGraph(event);
        this._pinned.set(dragging.id, { x: point.x, y: point.y });
        this._dragMoved = true;
        // One redraw per frame: relaxation runs on every one of them.
        if (!frame) {
          frame = requestAnimationFrame(() => {
            frame = 0;
            this._redrawMap();
          });
        }
        return;
      }
      if (!panning) return;
      view.x = event.clientX - panning.x;
      view.y = event.clientY - panning.y;
      applyView();
    });

    const stop = () => {
      panning = null;
      dragging = null;
      svg.classList.remove("dragging");
      // Let the click that follows a real drag through only if it was a tap.
      setTimeout(() => {
        this._dragMoved = false;
      }, 0);
    };
    svg.addEventListener("pointerup", stop);
    svg.addEventListener("pointercancel", stop);
    svg.addEventListener("pointerleave", stop);
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
                      [device.area, device.ip || device.model, device.entity_count
                        ? this.t("map.entities", { n: device.entity_count })
                        : ""]
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

  /* ── settings ────────────────────────────────────────────────────────── */

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
    </div>`;
  }

  viewSettings() {
    const status = this._status || {};
    const connection = status.connection || {};
    const store = status.store || {};
    const prune = (status.retention || {}).last_prune || {};
    const configured = Boolean(connection.adguard_url);
    const lastScan = status.generated_at
      ? new Date(status.generated_at).toLocaleString(this._lang === "it" ? "it-IT" : "en-GB")
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
                <option value="it" ${this._langOverride === "it" ? "selected" : ""}>Italiano</option>
                <option value="en" ${this._langOverride === "en" ? "selected" : ""}>English</option>
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
        <h2 class="sec">${esc(this.t("settings.section.collection"))}</h2>
        <div class="panel-card"><div class="form">
          ${this.numberField("scan_interval_minutes")}
          ${this.numberField("page_size")}
          ${this.numberField("max_pages")}
        </div></div>
      </div>

      <div>
        <h2 class="sec">${esc(this.t("settings.section.retention"))}</h2>
        <div class="panel-card"><div class="form">
          ${this.numberField("observation_days")}
          ${this.numberField("max_observations")}
          ${this.numberField("scan_history")}
        </div></div>
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
    </div>`;
  }

  async saveOptions() {
    if (this._saving) return;
    const host = this.shadowRoot.lastChild;
    const options = {};
    host.querySelectorAll("[data-option]").forEach((input) => {
      const key = input.dataset.option;
      options[key] = input.type === "number" ? Number(input.value) : input.value;
    });

    this._saving = true;
    this._saveStatus = null;
    this.render();
    try {
      await this._hass.callWS({ type: "talos/options/set", options });
      this._saveStatus = { tone: "ok", text: this.t("settings.saved") };
      this._saving = false;
      this.render();
      // Updating the entry reloads the integration, so give it a moment
      // before asking for the new state.
      setTimeout(() => this.load(), 2500);
    } catch (err) {
      const reason = err && err.message ? err.message : String(err);
      this._saveStatus = { tone: "error", text: this.t("settings.error", { reason }) };
      this._saving = false;
      this.render();
    }
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
    if (!withConduits.size) {
      cloudIntegrations.forEach((entryId) => {
        Object.entries(devices).forEach(([id, device]) => {
          if (device.integration_id === entryId) withConduits.add(id);
        });
      });
    }

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
    // With no observations the weights come from the declared side instead,
    // so the first three columns are populated rather than blank.
    if (!weight.size) {
      withConduits.forEach((deviceId) => {
        const key = originOf(deviceId);
        weight.set(key, (weight.get(key) || 0) + 1);
      });
    }

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

    const observedDestinations = [
      ...new Set(
        d.conduits
          .filter((conduit) => PHONE_HOME.has(this.destination(conduit.destination_id).kind))
          .map((conduit) => conduit.destination_id)
      ),
    ];
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
    const destinations = [...observedDestinations, ...declaredDestinations].slice(0, MAX_ROWS);

    const transports = [
      ...new Set(
        origins.flatMap((key) =>
          (members.get(key) || []).map((id) => (devices[id] || {}).transport || "unknown")
        )
      ),
    ].slice(0, 6);

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
