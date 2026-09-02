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
    "adv.cell.localEgress":
      "Comandati localmente, ma osservati risolvere domini del produttore per conto proprio.",
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
      "È questo il limite che tiene a bada la dimensione del database.",
    "opt.hint.zone_trusted_lan":
      "Uno o più intervalli CIDR separati da virgola, per esempio 192.168.50.0/24. Finché restano vuoti, i controlli sulle zone si dichiarano non eseguibili invece di risultare superati.",
    "opt.hint.domain_rules_path":
      "Percorso assoluto a un file JSON o YAML. Le regole si aggiungono a quelle predefinite, non le sostituiscono.",
    "settings.system.ha": "Versione di Home Assistant",
    "settings.system.collector": "Modalità di raccolta",
    "settings.system.lastScan": "Ultima scansione",
    "settings.system.observations": "Osservazioni memorizzate",
    "settings.system.oldest": "Osservazione più vecchia",
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
    "transport.ip": "Rete IP",

    "base.checks": "Controlli eseguiti",
    "base.checks.lead":
      "Talos dichiara un elenco fisso di controlli. Alcuni sono eseguibili con i dati che raccoglie, altri richiedono sorgenti che non ha e restano dichiarati ma non implementati: compaiono fra i non eseguibili con il loro motivo, mai fra i superati.",
    "base.checks.total":
      "{total} controlli dichiarati: {passed} superati, {failed} con rilievi, {notrun} non eseguibili. Oltre a questi, {notes} limiti della raccolta, che non sono controlli e non concorrono ad alcun esito.",
    "checks.group.notes": "Limiti della raccolta",
    "adv.inventory": "Integrazioni",
    "adv.inventory.lead":
      "Tutto quello che Talos ricava dal registry per ogni config entry, senza interrogare nulla: cosa dichiara il manifest, in che stato è la entry, a quale indirizzo dice di collegarsi e che cosa le appartiene.",
    "inv.class": "iot_class dichiarata",
    "inv.role": "Ruolo",
    "inv.state": "Stato della entry",
    "inv.endpoint": "Indirizzo dichiarato",
    "inv.origin": "Sistemi che pubblicano su questa entry",
    "inv.source": "Provenienza",
    "inv.source.builtin": "inclusa in Home Assistant",
    "inv.source.custom": "installata a mano o via HACS",
    "inv.counts": "{devices} dispositivi · {entities} entità",
    "inv.none": "non dichiarato",
    "base.unverified.notes":
      "Elencati a parte anche <strong>{n} limiti della raccolta</strong>: punti in cui i dati non arrivano, che non sono controlli.",
    "base.checks.tally.passed": "superati",
    "base.checks.tally.failed": "con rilievi",
    "base.checks.tally.unverified": "non eseguibili",
    "checks.group.failed": "Con rilievi",
    "checks.group.passed": "Superati",
    "checks.group.unverified": "Non eseguibili",
    "check.subjects": "Elementi interessati",
    "check.do": "Cosa fare",
    "check.why": "Perché non è stato eseguito",
    "check.passedBody":
      "Eseguito su questa scansione senza rilievi. Vale per i dati di questa scansione, non è una garanzia permanente.",
    "check.none": "Nessuno.",
    "check.expandHint": "Clicca una voce per vedere il dettaglio e gli elementi coinvolti.",

    "evidence.how": "Come lo so",
    "evidence.how.body":
      "Chi contatta il produttore non viene stabilito con sonde: Talos legge il query log di AdGuard Home, associa l'IP del client al dispositivo tramite i lease DHCP e classifica il dominio richiesto. Nessuna porta viene scansionata e nessun contenuto viene ispezionato: si sa <strong>quale nome è stato risolto</strong>, non cosa è stato detto.",
    "evidence.blocked.adguard":
      "Questa sezione resta vuota perché AdGuard Home non è raggiungibile. Senza query log non esiste alcuna osservazione, e una casella vuota non significa assenza di traffico.",
    "evidence.blocked.correlation":
      "Il query log è leggibile ma nessun dispositivo è correlato a un indirizzo IP: senza lease DHCP le richieste restano attribuite a host sconosciuti. Attiva il server DHCP di AdGuard Home oppure fornisci i lease del router.",
    "evidence.blocked.partial":
      "Correlati {done} dispositivi su {total}. Su quelli non correlati un eventuale traffico verso il produttore non è visibile, quindi questo elenco è un minimo.",
    "evidence.blocked.silent":
      "Query log leggibile e dispositivi correlati: in questa finestra nessuno ha risolto domini classificati come cloud del produttore.",

    "chk.local_with_egress.title": "Dispositivo locale che contatta il cloud del produttore",
    "chk.local_with_egress.detail":
      "Home Assistant li comanda localmente, ma il query log li ha visti risolvere domini del produttore per conto proprio. Questo dice con chi hanno parlato, non che cosa si sono detti.",
    "chk.local_with_egress.remediation":
      "Cerca nell'app del produttore il servizio cloud che gira in parallelo, spesso chiamato P2P, UID o accesso remoto. Disattivarlo non compromette il controllo locale da Home Assistant.",
    "chk.nat_traversal.title": "Dispositivo che si apre una via di rientro dall'esterno",
    "chk.nat_traversal.detail":
      "Questi dispositivi hanno risolto un server STUN o TURN, oppure un tunnel broker. Su quelli non ci naviga nessuno: sono quello che un dispositivo chiede quando vuole una via di rientro in casa che non passa dalle regole del tuo router. È così che l'app del produttore raggiunge una telecamera dall'altra parte del mondo, e funziona che tu abbia aperto una porta o no.",
    "chk.nat_traversal.remediation":
      "Se è un tunnel che hai messo su tu, Cloudflare, Tailscale, ZeroTier, è roba tua e non c'è niente da sistemare. Se è una telecamera o un elettrodomestico, cerca accesso remoto, P2P o UID nella sua app e disattivalo: il controllo locale da Home Assistant non ne dipende. Bloccare il dominio sul resolver ferma la risoluzione, non un indirizzo scritto nel firmware.",
    "chk.resolver_bypass.title": "Dispositivo che aggira il resolver",
    "chk.resolver_bypass.detail":
      "Ha un lease DHCP ma non ha mai interrogato AdGuard: usa un server DNS scritto nel firmware. Su questo host ogni controllo basato sul DNS è cieco.",
    "chk.resolver_bypass.remediation":
      "Imposta il DNS di rete sul dispositivo, se lo consente. Altrimenti reindirizza la porta 53 sul router. Il DNS over HTTPS resta comunque fuori portata.",
    "chk.integration_not_loaded.title": "Integrazione non caricata",
    "chk.integration_not_loaded.detail":
      "La config entry non è caricata, quindi le sue entità sono non disponibili adesso. Non è una questione di autonomia offline: non funzionano né con connettività né senza. Un broker fermo, un servizio che ha cambiato indirizzo o una migrazione fallita si presentano tutti così.",
    "chk.integration_not_loaded.remediation":
      "Apri Impostazioni, Dispositivi e servizi e leggi l'errore della entry. Se cita un broker o un server, verifica che il servizio sia effettivamente avviato e che l'indirizzo corrisponda ancora: un add-on fermato o rinominato è il caso più comune.",
    "chk.zigbee_permit_join.title": "Rete Zigbee aperta all'accoppiamento",
    "chk.zigbee_permit_join.detail":
      "Il coordinator sta accettando nuovi dispositivi adesso. È lo stato giusto per il minuto che serve ad accoppiare qualcosa e quello sbagliato per tutto il resto del tempo: finché è aperta, qualunque cosa a portata radio che chieda di entrare viene fatta entrare.",
    "chk.zigbee_permit_join.remediation":
      "Disattiva l'accoppiamento da Zigbee2MQTT, dalla dashboard oppure pubblicando false su <base>/bridge/request/permit_join. Se è acceso perché stai accoppiando qualcosa, questo rilievo sparisce da solo quando hai finito.",
    "chk.custom_integration_cloud.title": "Integrazione di terze parti con accesso cloud",
    "chk.custom_integration_cloud.detail":
      "Integrazioni installate a mano o tramite HACS che dialogano con un servizio esterno. Non sono riviste da Home Assistant, e le credenziali che custodiscono passano per codice di terzi.",
    "chk.custom_integration_cloud.remediation":
      "Verifica che il repository sia mantenuto e che l'installazione sia stata una tua scelta. Non è un difetto in sé: è una superficie in più che stai scegliendo di considerare affidabile.",
    "chk.device_on_trusted_lan.title": "Dispositivo che comunica verso l'esterno dalla LAN di fiducia",
    "chk.device_on_trusted_lan.detail":
      "Si trova sulla rete che ospita anche computer e telefoni, e raggiunge l'esterno per conto proprio.",
    "chk.device_on_trusted_lan.remediation":
      "Spostalo sulla VLAN IoT, se ne hai una. Se non ce l'hai, questo controllo è l'argomento migliore per costruirne una.",
    "chk.cloud_declared_silent.title": "Integrazione cloud che non ha contattato nessuno",
    "chk.cloud_declared_silent.detail":
      "Dichiarata cloud dal manifest eppure silenziosa nel query log. Non è un merito: o il dispositivo non è correlato, o usa un resolver proprio, o l'integrazione non sta funzionando.",
    "chk.cloud_declared_silent.remediation":
      "Verifica che il dispositivo sia effettivamente correlato a un IP e che l'integrazione sia caricata. Un cloud che non parla mai di solito segnala un problema.",
    "chk.mqtt_anonymous.title": "Broker MQTT che accetta accessi anonimi",
    "chk.mqtt_anonymous.detail":
      "La config entry MQTT raggiunge il proprio broker senza alcuna credenziale, il che significa che il broker accetta connessioni anonime. Non è una sonda: Home Assistant è già collegato così, quindi la risposta del broker è agli atti. Qualunque cosa sulla stessa rete può pubblicare su qualunque topic, compresi quelli su cui i tuoi dispositivi agiscono.",
    "chk.mqtt_anonymous.remediation":
      "Crea un utente sul broker e assegnalo a Home Assistant. Sull'add-on Mosquitto è una riga nella configurazione dell'add-on, su EMQX è il database integrato sotto Access Control. Poi disattiva l'accesso anonimo, e riconfigura gli altri client che ci facevano affidamento.",
    "chk.mqtt_unknown_client.title": "Client MQTT che non corrisponde ad alcun asset noto",
    "chk.mqtt_unknown_client.detail":
      "Il broker riporta questi client connessi e nessuno corrisponde a una config entry, a un dispositivo o a un add-on che Talos conosca. Un broker ha solo il client id per identificarli, quindi uno senza corrispondenza non è la prova di un intruso, ma è qualcosa che pubblica nei tuoi topic e di cui nulla in Home Assistant rende conto.",
    "chk.mqtt_unknown_client.remediation":
      "Confronta ogni id con quello che fai girare tu: Zigbee2MQTT, un Tasmota, un ESP, uno script su un'altra macchina. Quello che avanza vale la pena inseguirlo. Dare a ogni tuo client un client id esplicito e riconoscibile rende questo controllo utile invece che rumoroso.",
    "chk.rtsp_cleartext.title": "Flusso RTSP in chiaro",
    "chk.rtsp_cleartext.detail":
      "Queste config entry di telecamere dichiarano uno stream RTSP, e RTSP porta in chiaro sia le credenziali sia il video. Chiunque riesca a vedere il traffico sul segmento dove sta la telecamera li legge entrambi. È quello che dichiara la entry, non una cattura: l'indirizzo l'ho letto dalla configurazione, non mi sono collegato a niente e non ho guardato niente.",
    "chk.rtsp_cleartext.remediation":
      "Sposta la telecamera sulla VLAN IoT, così il traffico non attraversa mai la rete dove stanno i tuoi computer. Dove la telecamera offre RTSPS o uno stream HTTPS, usa quelli. Dove non li offre, e le telecamere economiche non li offrono, la segmentazione è tutta la risposta.",

    "unv.manifests_unavailable.title": "iot_class di alcune integrazioni",
    "unv.entities_outside_registry.title": "Entità che non appartengono ad alcuna config entry",
    "unv.entity_registry_unreadable.title": "Registry delle entità",
    "unv.area_registry_unreadable.title": "Registry delle aree",
    "unv.manifest_list_unreadable.title": "Elenco dei manifest",
    "unv.entry_endpoints_unavailable.title": "Indirizzi a cui si collegano le integrazioni",
    "unv.entry_endpoints_unavailable.detail":
      "L'API WebSocket non espone i dati delle config entry, quindi da fuori non si può leggere a quale broker o server punta ciascuna integrazione. Eseguito come integrazione, Talos li legge in processo. Nient'altro è influenzato.",
    "unv.dhcp_leases_unavailable.title": "Lease DHCP non disponibili: il controllo dello zero non è eseguibile",
    "unv.dhcp_leases_unavailable.detail":
      "Il registry di Home Assistant conosce i MAC, il query log conosce gli IP: i lease DHCP sono l'unico punto in cui i due si incontrano. Senza, ogni osservazione resta attribuita a un host sconosciuto, e Talos può dire che qualcuno ha contattato un produttore ma non quale dispositivo fosse. Nemmeno i client del resolver possono essere confrontati con i dispositivi in rete, quindi un apparecchio con DNS scritto nel firmware non emerge mai. Per copertura completa: attiva il server DHCP di AdGuard Home, oppure fornisci i lease del router. Questo controllo non è fallito, non è stato eseguito.",
    "unv.resolver_bypassed.title": "Dispositivi che aggirano il resolver",
    "unv.devices_without_identifier.title": "Dispositivi senza MAC nel registry",
    "unv.unclassified_domains.title": "Domini non classificati",
    "unv.doh.title": "Traffico DNS over HTTPS",
    "unv.doh.detail":
      "Un dispositivo che cifra anche le proprie richieste DNS (DoH, porta 443) è indistinguibile dal traffico ordinario. È un limite strutturale dichiarato: questo approccio non lo copre.",
    "unv.observed_source_unavailable.title": "Lato osservato non disponibile in questa scansione",

    "settings.section.scope": "Ambito dell'analisi",
    "settings.scope.lead":
      "Quello che segue non viene controllato da Talos e resta a carico tuo. Non è un elenco di difetti dell'integrazione: è il confine dichiarato del metodo.",
    "settings.scope.does": "Cosa fa",
    "settings.scope.doesBody":
      "Legge in sola lettura i registry di Home Assistant e il query log di AdGuard Home, li correla tramite i lease DHCP e classifica i domini richiesti. Nessuna scansione di porte, nessun tentativo di credenziali, nessuna ispezione del contenuto del traffico, nessuna modifica alla configurazione.",
    "settings.scope.doesNot": "Cosa non fa, e devi verificare a mano",
    "settings.scope.item.segmentation":
      "Segmentazione della rete: se i dispositivi IoT stiano su una VLAN separata da computer e telefoni.",
    "settings.scope.item.credentials":
      "Credenziali di dispositivi e servizi: password di default, account condivisi, token mai ruotati.",
    "settings.scope.item.firmware": "Aggiornamenti firmware dei dispositivi e degli hub.",
    "settings.scope.item.exposure":
      "Esposizione di Home Assistant verso internet: reverse proxy, port forwarding, accesso remoto.",
    "settings.scope.item.doh":
      "Traffico che cifra anche le proprie richieste DNS: resta indistinguibile e non viene visto.",
    "settings.scope.item.payload":
      "Contenuto del traffico: cosa viene inviato al produttore non è ricavabile dal solo DNS.",
    "settings.scope.closing":
      "Un esito privo di rilievi indica assenza di evidenze, non assenza di rischio.",

    "busy.scanning": "Scansione in corso",
    "busy.scanning.sub": "Sto rileggendo i registry e il query log. I dati a schermo sono quelli della scansione precedente finché non finisce.",
    "busy.saving": "Salvataggio in corso",
    "busy.saving.sub": "Le opzioni vengono scritte e l'integrazione si ricarica. Ci vuole qualche secondo, non è bloccata.",
    "busy.reloading": "Ricaricamento dei dati",
    "busy.reloading.sub": "L'integrazione è ripartita, sto rileggendo lo stato.",
    "busy.scanOk": "Scansione completata",
    "busy.scanOk.sub": "Dati aggiornati alle {when}.",
    "busy.saveOk": "Impostazioni salvate",
    "busy.saveOk.sub": "Applicate alla scansione appena eseguita.",
    "busy.scanError": "Scansione fallita",
    "busy.saveError": "Salvataggio fallito",
    "busy.stale": "L'ultimo tentativo di scansione è fallito",
    "busy.stale.sub": "A schermo ci sono i dati dell'ultima scansione riuscita, del {when}. Motivo: {reason}",

    "filter.search": "Cerca per nome, dominio o indirizzo",
    "filter.all": "Tutte",
    "filter.loaded": "Caricate",
    "filter.notLoaded": "Non caricate",
    "filter.cloud": "Cloud",
    "filter.custom": "HACS",
    "filter.withEndpoint": "Con indirizzo",
    "filter.none": "Nessuna integrazione corrisponde a questo filtro.",
    "filter.count": "{shown} su {total}",

    "sugg.label": "Rilevato dalla scansione:",
    "sugg.use": "Usa",
    "sugg.detail.zone_trusted_lan":
      "La subnet più popolata di questa scansione. Impostala solo se è la rete su cui stanno computer e telefoni, perché è questo che il controllo intende per rete di fiducia.",
    "sugg.detail.zone_iot_vlan":
      "Una seconda subnet con traffico in questa scansione. Se i dispositivi IoT sono quelli che ci stanno sopra, è la VLAN IoT; se non lo sono, lasciala vuota invece di riempirla.",
    "sugg.hosts": "{n} host",

    "settings.section.advice": "Consigli per l'utente",
    "settings.advice.lead":
      "Talos legge in sola lettura i registry di Home Assistant e il query log di AdGuard Home, li correla e classifica i domini richiesti. Non esegue scansioni di porte, non prova credenziali, non ispeziona il contenuto del traffico e non modifica nulla. Quello che segue resta quindi fuori dalla sua portata e a carico tuo: non è un elenco di difetti dell'integrazione, è il confine dichiarato del metodo.",
    "settings.advice.items": "Verifiche a carico dell'utente",
    "settings.guide": "Mini guida: tenere in ordine una rete domotica",
    "settings.guide.lead":
      "Sei cose che nella pratica fanno la differenza, in ordine di quanto rendono rispetto alla fatica che costano.",
    "settings.guide.h.1": "1. Separa le reti prima di tutto il resto",
    "settings.guide.p.1":
      "Una VLAN per i dispositivi IoT e una per computer e telefoni. È l'intervento che rende innocui tutti gli altri problemi: una telecamera compromessa su una VLAN isolata non arriva ai tuoi file. Se il router non fa VLAN, la rete ospiti è un ripiego accettabile per i dispositivi che non devono parlare con nient'altro in casa.",
    "settings.guide.h.2": "2. Metti il DHCP e il DNS sotto il tuo controllo",
    "settings.guide.p.2":
      "Un solo server DHCP che conosce tutti i lease e un solo resolver da cui passano tutte le richieste. Serve a te per sapere chi è chi, e serve a Talos per correlare: senza uno dei due, metà dei controlli si dichiara non eseguibile. Se AdGuard Home fa anche il DHCP, i due dati arrivano già uniti.",
    "settings.guide.h.3": "3. Blocca la porta 53 in uscita sul router",
    "settings.guide.p.3":
      "Molti dispositivi hanno un DNS scritto nel firmware e ignorano quello che gli dai. Reindirizzare la porta 53 verso il tuo resolver li riporta in riga. Chi cifra anche il DNS (DoH sulla 443) resta comunque fuori portata: è un limite, non un difetto da risolvere.",
    "settings.guide.h.4": "4. Preferisci l'integrazione locale a quella cloud",
    "settings.guide.p.4":
      "Quando esistono entrambe scegli la locale, anche se ha meno funzioni. Zigbee, Z-Wave, Matter, ESPHome e Modbus continuano a funzionare con il modem staccato. Un'integrazione cloud smette, e con lei ogni automazione che la usa.",
    "settings.guide.h.5": "5. Dai un'identità a ogni cosa che pubblica",
    "settings.guide.p.5":
      "Client id MQTT espliciti, nomi dei dispositivi coerenti, riservazioni DHCP per quello che conta. Costa dieci minuti e trasforma un elenco di indirizzi anonimi in qualcosa che si legge. È anche la differenza fra un controllo utile e uno rumoroso.",
    "settings.guide.h.6": "6. Aggiorna quello che espone qualcosa, ignora il resto",
    "settings.guide.p.6":
      "Firmware di router, hub, telecamere e qualunque cosa raggiungibile da fuori. Una lampadina Zigbee dietro un bridge non è una priorità. Se qualcosa è esposto su internet, quello viene prima di tutto il resto in questo elenco.",

    "settings.section.mqtt": "Account MQTT di sola lettura",
    "settings.mqtt.none":
      "Nessun account configurato. Talos usa la sessione che l'integrazione MQTT ha già aperta, che funziona finché il broker non riserva $SYS a un utente specifico. Quasi tutti lo fanno, ed è il motivo per cui il controllo sui client sconosciuti di solito si dichiara non eseguibile.",
    "settings.mqtt.state": "Ultima lettura",
    "settings.mqtt.ok": "{clients} client letti, {unmatched} senza corrispondenza",

    "mqtt.host": "Broker",
    "mqtt.host.hint":
      "Lascia vuoto per usare il broker che la config entry MQTT già dichiara. Compilalo solo se vuoi puntare altrove.",
    "mqtt.port": "Porta",
    "mqtt.user": "Utente",
    "mqtt.password": "Password",
    "mqtt.password.set": "impostata, lascia vuoto per non cambiarla",
    "mqtt.password.unset": "nessuna password memorizzata",
    "mqtt.tls": "Il broker usa TLS",
    "mqtt.save": "Salva e prova la connessione",
    "mqtt.saving": "Connessione in corso…",
    "mqtt.clear": "Rimuovi l'account",
    "mqtt.testing": "Provo la connessione al broker",
    "mqtt.testing.sub": "Mi collego, mi sottoscrivo a $SYS e mi disconnetto. Non pubblico nulla.",
    "mqtt.ok": "Account salvato",
    "mqtt.ok.sub": "Broker raggiunto, {n} client letti da $SYS.",
    "mqtt.okNoSys": "Account salvato, ma $SYS non risponde",
    "mqtt.okNoSys.sub":
      "La connessione funziona e le credenziali sono valide, ma questo utente non riesce a leggere $SYS. Serve il permesso di sottoscrivere $SYS/# sul broker. Il controllo sui client resta non eseguibile finché non ce l'ha.",
    "mqtt.failed": "Connessione al broker fallita",
    "mqtt.cleared": "Account rimosso",
    "mqtt.cleared.sub": "Torno a usare la sessione dell'integrazione MQTT.",
    "mqtt.acl":
      "Serve un utente in sola lettura con il permesso di sottoscrivere $SYS/#. Su EMQX: Access Control, Authentication per l'utente e una regola di sola sottoscrizione. Su Mosquitto: una riga topic read $SYS/# nell'acl_file. Talos non pubblica nulla, non si sottoscrive ad altro, e si collega con client id talos-scanner così la sua connessione è riconoscibile nella lista che legge.",

    "mqtt.route": "Sorgente in uso",
    "mqtt.route.api": "API di EMQX",
    "mqtt.route.account": "Account dedicato su $SYS",
    "mqtt.route.session": "Sessione dell'integrazione MQTT",
    "mqtt.state.ok": "{clients} client letti, {unmatched} senza corrispondenza",
    "mqtt.state.blocked": "Nessun client letto",
    "mqtt.lastRun": "Ultima scansione",
    "mqtt.listener": "Stato del listener",
    "mqtt.api": "API EMQX 5",
    "mqtt.api.url": "Indirizzo API",
    "mqtt.api.url.hint":
      "EMQX 5 ha tolto i topic per client da $SYS, quindi la sottoscrizione lì non può rispondere: restano solo contatori. La sua API invece elenca i client connessi adesso, con l'indirizzo da cui si sono collegati, che permette di associarli ai dispositivi e non solo al nome. Metti lo stesso indirizzo che usi nel browser per aprire la dashboard, schema compreso, di norma sulla porta 18083.",
    "mqtt.api.key": "API key",
    "mqtt.api.secret": "API secret",
    "mqtt.api.secret.set": "impostato, lascia vuoto per non cambiarlo",
    "mqtt.api.secret.unset": "nessun secret memorizzato",
    "mqtt.api.hint":
      "Si crea dalla dashboard EMQX, System → API Key → Create. Bastano i permessi di sola lettura. Se compili questo, Talos usa l'API e ignora i campi del broker qui sopra.",
    "mqtt.sub": "Sottoscrizione $SYS",
    "mqtt.okApi": "Account salvato",
    "mqtt.okApi.sub": "API raggiunta, {n} client letti.",
    "mqtt.noReload":
      "Le credenziali del broker vengono rilette a ogni scansione, quindi salvarle non ricarica l'integrazione e non interrompe nulla.",

    "mqtt.fallback": "Ripiego da {route}",
    "mqtt.fallback.why": "La sorgente configurata non ha risposto: {reason}",
    "mqtt.api.replaces":
      "Con una API key configurata Talos non si sottoscrive più a $SYS, e non è una perdita: su EMQX 5 quell'albero contiene solo contatori, mentre l'API elenca i client con il loro indirizzo. Se però l'API non risponde, Talos torna da sola alla sottoscrizione e te lo dice qui sotto invece di restare senza dati.",

    "mesh.coordinator": "Coordinator",
    "mesh.router": "Router",
    "mesh.end_device": "Terminale",
    "mesh.unknown": "",
    "mesh.title": "Rete Zigbee",
    "mesh.lead":
      "Come il coordinator descrive la propria rete, letto dai topic ritenuti di Zigbee2MQTT. I router ripetono per i nodi vicini e stanno a corrente, i terminali dormono e dipendono da un router a portata. Il genitore di ciascun nodo non è dichiarato: saperlo richiede una scansione della mesh, e quella è una sonda.",
    "mesh.nodes": "Nodi",
    "mesh.routers": "Router",
    "mesh.endDevices": "Terminali",
    "mesh.channel": "Canale",
    "mesh.permitJoin": "Accoppiamento",
    "mesh.permitJoin.on": "aperto",
    "mesh.permitJoin.off": "chiuso",
    "mesh.version": "Versione Zigbee2MQTT",
    "map.mesh": "Ruolo nella mesh",

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
    "kind.nat_traversal": "attraversamento NAT",
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
    "adv.cell.localEgress":
      "Driven locally, yet observed resolving vendor domains on their own.",
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
    "transport.ip": "IP network",

    "base.checks": "Checks run",
    "base.checks.lead":
      "Talos declares a fixed list of checks. Some run on the data it collects, the rest need sources it does not have and stay declared but not implemented: they appear among the ones that could not run, with their reason, never among the passes.",
    "base.checks.total":
      "{total} declared checks: {passed} passed, {failed} with findings, {notrun} could not run. On top of those, {notes} collection limits, which are not checks and settle nothing.",
    "checks.group.notes": "Collection limits",
    "adv.inventory": "Integrations",
    "adv.inventory.lead":
      "Everything Talos derives from the registry for each config entry, without asking anything: what the manifest declares, what state the entry is in, which address it says it connects to, and what belongs to it.",
    "inv.class": "declared iot_class",
    "inv.role": "Role",
    "inv.state": "Entry state",
    "inv.endpoint": "Declared address",
    "inv.origin": "Systems publishing through this entry",
    "inv.source": "Source",
    "inv.source.builtin": "shipped with Home Assistant",
    "inv.source.custom": "installed by hand or through HACS",
    "inv.counts": "{devices} devices · {entities} entities",
    "inv.none": "not declared",
    "base.unverified.notes":
      "Listed separately, <strong>{n} collection limits</strong>: places the data does not reach, which were never checks.",
    "base.checks.tally.passed": "passed",
    "base.checks.tally.failed": "with findings",
    "base.checks.tally.unverified": "could not run",
    "checks.group.failed": "With findings",
    "checks.group.passed": "Passed",
    "checks.group.unverified": "Could not run",
    "check.subjects": "Affected",
    "check.do": "What to do",
    "check.why": "Why it did not run",
    "check.passedBody":
      "Ran on this scan with nothing to report. That covers this scan's data, it is not a standing guarantee.",
    "check.none": "None.",
    "check.expandHint": "Click an entry for the detail and the assets involved.",

    "evidence.how": "How this is known",
    "evidence.how.body":
      "Who contacts the vendor is not established by probing: Talos reads the AdGuard Home query log, ties the client IP to a device through the DHCP leases, and classifies the domain that was asked for. No port is scanned and no payload is inspected: what is known is <strong>which name was resolved</strong>, not what was said.",
    "evidence.blocked.adguard":
      "This section stays empty because AdGuard Home is not reachable. With no query log there is no observation at all, and an empty cell does not mean an absence of traffic.",
    "evidence.blocked.correlation":
      "The query log is readable but no device is tied to an IP address: without DHCP leases the queries stay attributed to unknown hosts. Enable AdGuard Home's DHCP server or supply the router's leases.",
    "evidence.blocked.partial":
      "{done} of {total} devices correlated. On the rest, traffic to a vendor would not be visible, so this list is a minimum.",
    "evidence.blocked.silent":
      "Query log readable and devices correlated: in this window none of them resolved a domain classified as vendor cloud.",

    "settings.section.scope": "Scope of the analysis",
    "settings.scope.lead":
      "What follows is not checked by Talos and stays with you. It is not a list of shortcomings: it is the declared boundary of the method.",
    "settings.scope.does": "What it does",
    "settings.scope.doesBody":
      "Reads the Home Assistant registries and the AdGuard Home query log, read-only, correlates them through the DHCP leases and classifies the domains asked for. No port scanning, no credential attempts, no payload inspection, no configuration changes.",
    "settings.scope.doesNot": "What it does not do, and you have to check by hand",
    "settings.scope.item.segmentation":
      "Network segmentation: whether IoT devices sit on a VLAN separate from computers and phones.",
    "settings.scope.item.credentials":
      "Device and service credentials: default passwords, shared accounts, tokens never rotated.",
    "settings.scope.item.firmware": "Firmware updates on devices and hubs.",
    "settings.scope.item.exposure":
      "Home Assistant's own exposure to the internet: reverse proxy, port forwarding, remote access.",
    "settings.scope.item.doh":
      "Traffic that encrypts its DNS queries too: it stays indistinguishable and goes unseen.",
    "settings.scope.item.payload":
      "Payload: what is sent to the vendor cannot be derived from DNS alone.",
    "settings.scope.closing":
      "A clean result means no evidence was found, not that there is no risk.",

    "busy.scanning": "Scan running",
    "busy.scanning.sub": "Reading the registries and the query log again. What is on screen is the previous scan until this finishes.",
    "busy.saving": "Saving",
    "busy.saving.sub": "Writing the options and reloading the integration. It takes a few seconds, it is not stuck.",
    "busy.reloading": "Reloading data",
    "busy.reloading.sub": "The integration is back up, reading its state again.",
    "busy.scanOk": "Scan complete",
    "busy.scanOk.sub": "Data as of {when}.",
    "busy.saveOk": "Settings saved",
    "busy.saveOk.sub": "Applied to the scan that just ran.",
    "busy.scanError": "Scan failed",
    "busy.saveError": "Saving failed",
    "busy.stale": "The last scan attempt failed",
    "busy.stale.sub": "What is on screen is the last scan that worked, from {when}. Reason: {reason}",

    "filter.search": "Search by name, domain or address",
    "filter.all": "All",
    "filter.loaded": "Loaded",
    "filter.notLoaded": "Not loaded",
    "filter.cloud": "Cloud",
    "filter.custom": "HACS",
    "filter.withEndpoint": "With an address",
    "filter.none": "No integration matches this filter.",
    "filter.count": "{shown} of {total}",

    "sugg.label": "Found in this scan:",
    "sugg.use": "Use",
    "sugg.detail.zone_trusted_lan":
      "The busiest subnet in this scan. Set it only if this is the network your computers and phones are on, because that is what the trusted LAN check means by trusted.",
    "sugg.detail.zone_iot_vlan":
      "A second subnet carrying traffic in this scan. If your IoT devices are the ones on it, this is the IoT VLAN; if they are not, leave it empty rather than filling it in.",
    "sugg.hosts": "{n} hosts",

    "settings.section.advice": "Advice",
    "settings.advice.lead":
      "Talos reads the Home Assistant registries and the AdGuard Home query log, read-only, correlates them and classifies the domains asked for. It does not scan ports, try credentials, inspect payloads or change anything. What follows is therefore out of its reach and stays with you: not a list of shortcomings, the declared boundary of the method.",
    "settings.advice.items": "Checks that stay with you",
    "settings.guide": "Short guide: keeping a home automation network in order",
    "settings.guide.lead":
      "Six things that make a difference in practice, ordered by what they return for the effort they cost.",
    "settings.guide.h.1": "1. Separate the networks before anything else",
    "settings.guide.p.1":
      "One VLAN for IoT devices, one for computers and phones. It is the change that makes every other problem survivable: a compromised camera on an isolated VLAN does not reach your files. If the router cannot do VLANs, the guest network is an acceptable stand-in for devices that need to talk to nothing else in the house.",
    "settings.guide.h.2": "2. Own the DHCP and the DNS",
    "settings.guide.p.2":
      "One DHCP server that knows every lease, one resolver every query goes through. You need it to know who is who, and Talos needs it to correlate: without either, half the checks declare themselves unable to run. If AdGuard Home also does the DHCP, the two halves arrive already joined.",
    "settings.guide.h.3": "3. Block outbound port 53 at the router",
    "settings.guide.p.3":
      "Plenty of devices carry a DNS server in firmware and ignore the one you hand them. Redirecting port 53 to your own resolver brings them back in line. Anything that encrypts its DNS too, DoH on 443, stays out of reach: that is a limit, not a fault to fix.",
    "settings.guide.h.4": "4. Prefer the local integration to the cloud one",
    "settings.guide.p.4":
      "When both exist, take the local one even if it has fewer features. Zigbee, Z-Wave, Matter, ESPHome and Modbus keep working with the modem unplugged. A cloud integration stops, and every automation built on it stops with it.",
    "settings.guide.h.5": "5. Give everything that publishes a name",
    "settings.guide.p.5":
      "Explicit MQTT client ids, consistent device names, DHCP reservations for what matters. It costs ten minutes and turns a list of anonymous addresses into something readable. It is also the difference between a useful check and a noisy one.",
    "settings.guide.h.6": "6. Update what is exposed, ignore the rest",
    "settings.guide.p.6":
      "Firmware on routers, hubs, cameras and anything reachable from outside. A Zigbee bulb behind a bridge is not a priority. If something is exposed to the internet, it comes before everything else on this list.",

    "settings.section.mqtt": "Read-only MQTT account",
    "settings.mqtt.none":
      "No account configured. Talos uses the session the MQTT integration already holds, which works until the broker reserves $SYS for a specific user. Most of them do, and that is why the unknown-client check usually declares itself unable to run.",
    "settings.mqtt.state": "Last read",
    "settings.mqtt.ok": "{clients} clients read, {unmatched} unmatched",

    "mqtt.host": "Broker",
    "mqtt.host.hint":
      "Leave empty to use the broker the MQTT config entry already names. Fill it in only to point somewhere else.",
    "mqtt.port": "Port",
    "mqtt.user": "User",
    "mqtt.password": "Password",
    "mqtt.password.set": "stored, leave empty to keep it",
    "mqtt.password.unset": "no password stored",
    "mqtt.tls": "Broker uses TLS",
    "mqtt.save": "Save and test the connection",
    "mqtt.saving": "Connecting…",
    "mqtt.clear": "Remove the account",
    "mqtt.testing": "Testing the broker connection",
    "mqtt.testing.sub": "Connecting, subscribing to $SYS, disconnecting. Nothing is published.",
    "mqtt.ok": "Account saved",
    "mqtt.ok.sub": "Broker reached, {n} clients read from $SYS.",
    "mqtt.okNoSys": "Account saved, but $SYS does not answer",
    "mqtt.okNoSys.sub":
      "The connection works and the credentials are valid, but this user cannot read $SYS. It needs permission to subscribe to $SYS/# on the broker. The client check stays unable to run until it has it.",
    "mqtt.failed": "Could not connect to the broker",
    "mqtt.cleared": "Account removed",
    "mqtt.cleared.sub": "Back to using the MQTT integration's session.",
    "mqtt.acl":
      "It needs a read-only user allowed to subscribe to $SYS/#. On EMQX: Access Control, Authentication for the user and a subscribe-only rule. On Mosquitto: a topic read $SYS/# line in the acl_file. Talos publishes nothing, subscribes to nothing else, and connects with the client id talos-scanner so its own connection is recognisable in the list it reads.",

    "mqtt.route": "Route in use",
    "mqtt.route.api": "EMQX API",
    "mqtt.route.account": "Dedicated account on $SYS",
    "mqtt.route.session": "MQTT integration's session",
    "mqtt.state.ok": "{clients} clients read, {unmatched} unmatched",
    "mqtt.state.blocked": "No client read",
    "mqtt.lastRun": "Last scan",
    "mqtt.listener": "Listener state",
    "mqtt.api": "EMQX 5 API",
    "mqtt.api.url": "API address",
    "mqtt.api.url.hint":
      "EMQX 5 removed the per-client topics from $SYS, so a subscription there cannot answer: only counters are left. Its API does list the clients connected right now, with the address each connected from, which ties them to devices and not just to a name. Use the same address you open the dashboard with in a browser, scheme included, usually on port 18083.",
    "mqtt.api.key": "API key",
    "mqtt.api.secret": "API secret",
    "mqtt.api.secret.set": "stored, leave empty to keep it",
    "mqtt.api.secret.unset": "no secret stored",
    "mqtt.api.hint":
      "Create it in the EMQX dashboard, System, API Key, Create. Read-only permissions are enough. Filling this in makes Talos use the API and ignore the broker fields above.",
    "mqtt.sub": "$SYS subscription",
    "mqtt.okApi": "Account saved",
    "mqtt.okApi.sub": "API reached, {n} clients read.",
    "mqtt.noReload":
      "Broker credentials are read again on every scan, so saving them does not reload the integration and interrupts nothing.",

    "mqtt.fallback": "Fell back from {route}",
    "mqtt.fallback.why": "The configured source did not answer: {reason}",
    "mqtt.api.replaces":
      "With an API key configured Talos stops subscribing to $SYS, and nothing is lost by that: on EMQX 5 the tree holds only counters, while the API lists the clients with their address. If the API does not answer, Talos falls back to the subscription on its own and says so below rather than ending up with nothing.",

    "mesh.coordinator": "Coordinator",
    "mesh.router": "Router",
    "mesh.end_device": "End device",
    "mesh.unknown": "",
    "mesh.title": "Zigbee network",
    "mesh.lead":
      "How the coordinator describes its own network, read from Zigbee2MQTT's retained topics. Routers relay for the nodes around them and are mains powered, end devices sleep and depend on a router being in range. The parent of a node is not stated: knowing it takes a scan of the mesh, and that is a probe.",
    "mesh.nodes": "Nodes",
    "mesh.routers": "Routers",
    "mesh.endDevices": "End devices",
    "mesh.channel": "Channel",
    "mesh.permitJoin": "Joining",
    "mesh.permitJoin.on": "open",
    "mesh.permitJoin.off": "closed",
    "mesh.version": "Zigbee2MQTT version",
    "map.mesh": "Mesh role",

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
    "kind.nat_traversal": "NAT traversal",
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
    --k-local: #52b195; --k-infra: #93a5bd; --k-vendor: #c07dbb; --k-unknown: #8d9799;
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

  async load({ quiet = false } = {}) {
    this._loading = true;
    if (!quiet) this.render();
    try {
      const [derived, status, suggested] = await Promise.all([
        this._hass.callWS({ type: "talos/derived" }),
        this._hass.callWS({ type: "talos/status" }),
        // Advisory only: an older integration without the command must not
        // take the whole panel down with it.
        this._hass.callWS({ type: "talos/suggest" }).catch(() => ({ suggestions: [] })),
      ]);
      this._data = derived;
      // A finished scan supersedes the last save's test result.
      if (this._status && status.generated_at !== this._status.generated_at) {
        this._mqttResult = null;
      }
      this._status = status;
      this._suggestions = (suggested || {}).suggestions || [];
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
      ? new Date(value).toLocaleString(this._lang === "it" ? "it-IT" : "en-GB")
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

    const mqttSave = host.querySelector("[data-action='mqtt-save']");
    if (mqttSave) mqttSave.addEventListener("click", () => this.saveMqtt(false));
    const mqttClear = host.querySelector("[data-action='mqtt-clear']");
    if (mqttClear) mqttClear.addEventListener("click", () => this.saveMqtt(true));

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
    if (I18N[FALLBACK_LANG][key] !== undefined) return I18N[FALLBACK_LANG][key];
    return item[field] || "";
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
        }
        return `<div class="exp__row"><b>${esc(name)}</b><span class="mono">${esc(meta)}</span></div>`;
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

    // A check the engine declared but could not run, versus a note about
    // where the collection itself does not reach. Both are "not an outcome",
    // only the first belongs to the tally of declared checks.
    const isDeclaredCheck = (item) => String(item.id || "").startsWith("chk.");
    const notRun = checks.unverified.filter(isDeclaredCheck);
    const notes = checks.unverified.filter((item) => !isDeclaredCheck(item));
    const card = (check) =>
      this.expander({
        tone: "muted",
        title: esc(this.checkText(check, "title")),
        chips: [`<span class="chip">${esc(this.t(`reason.${check.reason}`))}</span>`],
        body: `<div class="exp__lab">${esc(this.t("check.why"))}</div>
          <p>${esc(this.checkText(check, "detail"))}</p>`,
      });

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
        <span><i style="background:var(--ink-mute)"></i><b>${this.num(
          notRun.length
        )}</b> ${esc(this.t("base.checks.tally.unverified"))}</span>
        <span class="hint">${esc(this.t("check.expandHint"))}</span>
      </div>
      <p class="hint" style="margin:0 0 14px">${esc(
        this.t("base.checks.total", {
          total: this.num(checks.passed.length + checks.failed.length + notRun.length),
          passed: this.num(checks.passed.length),
          failed: this.num(checks.failed.length),
          notrun: this.num(notRun.length),
          notes: this.num(notes.length),
        })
      )}</p>
      ${group(this.t("checks.group.failed"), "var(--alert)", failed, checks.failed.length)}
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

      ${this.meshSection()}
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
      options[key] = input.type === "number" ? Number(input.value) : input.value;
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
        <dd>${esc(this.t(`mqtt.route.${source.route || mqtt.route || "session"}`))}${
          mqtt.fallback_from
            ? ` · ${this.t("mqtt.fallback", {
                route: this.t(`mqtt.route.${mqtt.fallback_from}`),
              })}`
            : ""
        }</dd>
        <dt>${esc(this.t("mqtt.lastRun"))}</dt>
        <dd class="mono">${esc(this.when((this._status || {}).generated_at))}</dd>
        ${
          // A route that fell back still answered, so the box above is green.
          // Why the preferred one did not is the part worth acting on.
          mqtt.fallback_from && mqtt.error
            ? `<dt>${esc(this.t(`mqtt.route.${mqtt.fallback_from}`))}</dt>
               <dd>${esc(this.t("mqtt.fallback.why", { reason: mqtt.error }))}</dd>`
            : ""
        }
      </dl>`;
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
    } else if (result.route === "api") {
      this.setBusy(
        "ok",
        this.t("mqtt.okApi"),
        this.t("mqtt.okApi.sub", { n: this.num(result.clients) })
      );
    } else if (result.sys_readable) {
      this.setBusy("ok", this.t("mqtt.ok"), this.t("mqtt.ok.sub", { n: this.num(result.clients) }));
    } else {
      this.setBusy("ok", this.t("mqtt.okNoSys"), this.t("mqtt.okNoSys.sub"));
    }
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
