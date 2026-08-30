# Talos

**Da dove arrivano i dati della tua casa, dove vanno, e cosa smette di funzionare se salta internet.**

Talos incrocia due cose che nessuno incrocia: quello che Home Assistant **dichiara** sui propri
dispositivi e quello che il resolver DNS **osserva** davvero sulla rete. Il risultato è questa
matrice, che è il contenuto che non esiste in nessuno strumento attuale:

| | Nessun egress osservato | Egress osservato |
|---|---|---|
| **HA locale** (`local_push` / `local_polling`) | Pienamente locale | **Il dispositivo telefona a casa alle spalle di HA** |
| **HA cloud** (`cloud_push` / `cloud_polling`) | Anomalia da indagare | Dipendenza dichiarata, da censire |

`iot_class` descrive **come HA parla col dispositivo**, non come il dispositivo parla con Internet.
Uno Shelly in `local_push` può avere Shelly Cloud attivo in parallelo e HA non ne sa nulla. Le due
dimensioni sono indipendenti e Talos le tiene separate ovunque.

## Cosa NON è

- **Non è un vulnerability scanner.** Nessun matching CVE, nessun probe attivo, nessun port scan.
- **Non misura i volumi di traffico.** Il DNS dice *con chi* un dispositivo parla, non cosa gli dice
  né quanto. Il report dice “dipendenza rilevata”, mai “esfiltrazione dati”.
- **Non modifica nulla.** Sola lettura ovunque, su ogni fonte.

## Due domande, due numeri

Sono **ortogonali** e non vengono mai fusi in un punteggio unico. Una telecamera può mandare
telemetria ogni minuto e funzionare benissimo col router staccato; un'altra può essere silenziosa e
morire appena il cloud del produttore fa i capricci. Un numero solo appiattisce quattro situazioni
diverse, e nessuna delle quattro riceve la correzione che le serve.

- **Autonomia offline** — quante entità e quali automazioni continuano a funzionare senza internet.
- **Esposizione esterna** — quali dispositivi contattano server fuori casa, con quali prove.

Accanto c'è sempre un terzo numero: **i controlli che non è stato possibile eseguire.** Non sono
passati e non sono falliti. Un utente che legge “tutto ok” quando metà dei controlli non erano
eseguibili è stato ingannato, quindi quel conteggio è in prima pagina e non si può nascondere.

## Installazione

### HACS

1. HACS → Integrazioni → menu → *Repository personalizzati*
2. `https://github.com/Pricesswg/Talos`, categoria **Integration**
3. Installa, riavvia Home Assistant
4. *Impostazioni → Dispositivi e servizi → Aggiungi integrazione → Talos*

### Manuale

Copia `custom_components/talos` nella cartella `custom_components` della tua configurazione e riavvia.

## Configurazione

**AdGuard Home è facoltativo.** Senza, Talos risponde comunque alla domanda sull'autonomia offline
usando quello che Home Assistant dichiara di sé. Non può rispondere a quella sull'esposizione, e lo
scrive nel report invece di lasciare la casella vuota.

> ### Le lease DHCP servono davvero
>
> Il registry di Home Assistant conosce i **MAC**. Il query log conosce gli **IP**. Le lease DHCP
> sono l'unico posto in cui i due compaiono insieme.
>
> Senza lease, ogni osservazione resta attribuita a un host sconosciuto: Talos può dire che qualcuno
> ha contattato un produttore, ma **non quale dispositivo sia**, e il quadrante che conta risulta
> vuoto — non perché non ci sia niente, ma perché niente è attribuibile. Non è nemmeno possibile
> confrontare i client del resolver con i dispositivi in rete, quindi un apparecchio con DNS scritto
> nel firmware non emerge.
>
> Per una copertura piena: **attiva il server DHCP di AdGuard Home**, oppure fornisci le lease del
> router. Il report dichiara sempre quale delle due situazioni sta descrivendo.

Nelle opzioni si impostano l'intervallo di scansione, le **subnet** delle zone di rete (finché non le
indichi, i controlli sulle zone si dichiarano non eseguibili invece di risultare superati) e la
**ritenzione**.

### Ritenzione

Il query log produce una riga per ogni coppia client-dominio, quindi il database crescerebbe senza
limite. Due limiti, applicati a ogni scansione, perché da soli fallirebbero entrambi:

| Impostazione | Default | Ruolo |
|---|---|---|
| `observation_days` | 90 | Un dispositivo sostituito mesi fa smette di pesare sul report |
| `max_observations` | 20 000 | **È questo che limita il file.** Circa 4 MB di tetto pratico |
| `scan_history` | 5 | Gli snapshot sono una comodità: lo storico vero sono le osservazioni |

Le pagine liberate vengono davvero restituite al filesystem (`auto_vacuum=INCREMENTAL`): un `DELETE`
da solo non restringe un file SQLite.

## Il pannello

Talos registra un pannello **in barra laterale, solo per amministratori** — non una card. Una card
finisce su una dashboard, e una dashboard finisce sul tablet in cucina o sull'utente ospite. Questo
report elenca indirizzi, MAC e la topologia della casa: non essere incorporabile è una funzionalità.

Due viste, divise per **domanda** e non per densità di dati:

- **Base** — cosa si ferma, chi parla fuori, cosa non ho potuto verificare, con la correzione accanto.
- **Avanzata** — matrice, grafo dei flussi, condotti con la loro prova (`dichiarata` / `osservata` /
  `ereditata`), controlli e limiti.

## Uso da riga di comando

Il core è un pacchetto Python puro, senza dipendenze da `homeassistant.*`, eseguibile fuori banda —
un container su un'altra macchina, un cron, un portatile:

```bash
export TALOS_HA_TOKEN=...            # long lived access token
export TALOS_ADGUARD_PASSWORD=...

talos scan --url ws://homeassistant.local:8123/api/websocket \
           --adguard http://192.168.1.10:3000 \
           --zone-trusted 192.168.1.0/24 \
           --db ~/talos.db --html report.html
```

Le credenziali si leggono dall'ambiente perché una riga di comando finisce nella cronologia della
shell e nella lista dei processi. L'uscita è `1` se ci sono rilievi ad alta severità, così un cron se
ne accorge. Il file HTML è **autoconsistente**: niente script, niente risorse esterne, si apre da un
archivio fra un anno su una macchina senza rete.

Altri comandi: `talos validate scan.json`, `talos report scan.json --html out.html`.

## Estendere senza toccare il codice

- **Domini** — `talos_core/data/domains.json`. Che `*.tuya.com` sia un cloud di produttore lo sa una
  persona, non lo deduce un algoritmo. Le tue regole si sommano a quelle predefinite, non le
  sostituiscono, e i domini non classificati restano **contati e visibili** invece di finire in un
  catch-all.
- **Controlli** — `talos_core/data/checks.json`. Severità e correzioni sono dati. I selettori sono un
  vocabolario piccolo e dichiarato: un DSL abbastanza ricco da esprimere logica arbitraria sarebbe un
  linguaggio di programmazione travestito da file di configurazione.

Entrambi accettano JSON sempre e YAML quando PyYAML è disponibile (dentro Home Assistant lo è).

## Limiti dichiarati

- **DNS su HTTPS.** Un dispositivo che cifra anche le proprie richieste DNS sulla porta 443 è
  indistinguibile dal traffico normale. È un buco strutturale che questo approccio non copre.
- **Esposizione di HA su internet.** Un'istanza non può testare la propria raggiungibilità
  dall'esterno. Marcato non verificabile, non finto.
- **Tabella ARP.** Dentro un container la cache ARP contiene solo i peer con cui HA ha parlato di
  recente, non tutta la LAN. Le lease DHCP restano la fonte migliore.
- **Controlli non ancora implementati** — MQTT anonimo, client MQTT sconosciuti, nodi Z-Wave senza
  S2, RTSP in chiaro: compaiono nella lista dei non verificati con il motivo, invece di essere
  assenti in silenzio.

## Architettura

```
talos_core/                pacchetto Python puro, zero dipendenze, zero homeassistant.*
├── model, validate        modello dati e validatore con codici errore stabili
├── derive, checks         matrice, autonomia, esposizione, motore dei controlli
├── sources/               lato dichiarativo (WebSocket API)
├── observed/              lato osservativo (AdGuard), classificazione, join
└── storage, cli, export   persistenza con ritenzione, CLI, report HTML

custom_components/talos/   wrapper sottile: config flow, coordinator, entità, pannello
```

La separazione non è estetica: il core dev'essere testabile su fixture JSON senza far girare Home
Assistant, altrimenti non si testa più in CI e ogni release di HA diventa un rischio di regressione.

```bash
python3 -m unittest discover -s tests -t .
```

## Licenza

MIT — vedi [LICENSE](LICENSE).
