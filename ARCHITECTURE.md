# Architettura

## Obiettivo

Pipeline per il filtraggio dei dump storici Reddit, mantenendo soltanto i record appartenenti a una whitelist di subreddit italiani.

I dump `comments` e `submissions` vengono scaricati tramite qBittorrent, rilevati dalla pipeline tramite qBittorrent API quando risultano completati, processati in streaming e filtrati secondo una whitelist configurabile di subreddit italiani. Il risultato è un nuovo file `.zst` (con lo stesso nome del sorgente) contenente solo i record in whitelist, che viene caricato su Scaleway Object Storage.

La pipeline non utilizza un database intermedio: ogni dump viene letto, filtrato e riscritto come file `.zst` filtrato in `data/export/`, poi caricato in upload multi-part.

Obiettivi principali:

* processare i dump `.zst` senza decomprimerli integralmente su disco;
* elaborare i record in streaming;
* evitare file JSON intermedi;
* filtrare i record tramite whitelist di subreddit;
* scrivere un file `.zst` filtrato con lo stesso nome del sorgente;
* evitare file vuoti in export quando un dump non contiene subreddit della whitelist;
* eliminare sempre il dump sorgente dopo il processamento;
* rilevare lo stato dei download tramite qBittorrent API;
* caricare i file filtrati su Scaleway Object Storage in upload multi-part;
* attendere il completamento degli upload prima di terminare.

---

## Pipeline

```text
qBittorrent
     │
     │ download
     ▼
torrent (file .zst completati)
     │
     │ qBittorrent API
     │ file completed
     ▼
Processor (loop di ingestione)
     │
     │ Zstd streaming decompression
     │ NDJSON parsing
     │ whitelist filtering
     ▼
data/export/<nome>.zst  (filtrato, stesso nome)
     │
     │ coda upload (queue.Queue)
     ▼
Upload worker (N concorrenti, multi-part)
     │
     ▼
Scaleway Object Storage
remote: reddit-dataset/dump-subreddit-italia-since-2008
```

---

## Input

I dump sono forniti tramite torrent e hanno struttura logica:

```text
comments/
└── RC_YYYY-MM.zst

submissions/
└── RS_YYYY-MM.zst
```

`comments` e `submissions` sono dataset distinti e possono avere schemi differenti. Il processor non assume preventivamente uno schema completo dei dump: è sufficiente che ogni record JSON contenga un campo `subreddit`, usato per il filtro.

---

## Storage locale

Struttura prevista:

```text
data/
├── export/
│   └── <nome>.zst          # file filtrati (transitori)
└── historical_italian_subreddits_2008_2025.json
```

Ambiente di riferimento:

```text
Debian 12
Python 3.12+
Zstandard
qbittorrent-api
boto3 (Scaleway Object Storage)
```

Lo storage locale è temporaneo e viene utilizzato per:

* download dei torrent;
* processamento dei dump;
* generazione dei file `.zst` filtrati in `data/export/`.

I dump Reddit `.zst` **non devono mai essere decompressi integralmente su disco**. La decompressione avviene esclusivamente in streaming.

---

## qBittorrent e rilevamento dei file pronti

qBittorrent è responsabile del download dei dump. La pipeline utilizza qBittorrent API per determinare quali file risultano effettivamente completati.

Il flusso è:

```text
qBittorrent download
        ↓
qBittorrent API
        ↓
file completato
        ↓
Processor
```

Un file viene preso in carico dal processor soltanto quando qBittorrent ne segnala il completamento.

Non è necessario implementare un file watcher basato su `inotify`.

---

## Processing

Ogni dump viene processato interamente in streaming (`processor.filter_dump`):

```text
.zst sorgente
 ↓
Zstandard streaming decompression
 ↓
NDJSON line (lettura a livello di byte)
 ↓
JSON parse
 ↓
extract subreddit
 ↓
whitelist check
 ↓
discard
   oppure
scrivi riga ricompressa
 ↓
.zst filtrato in data/export/
```

Non viene creato un file JSON intermedio. Il processor non carica l'intero dump in memoria.

La lettura avviene a livello di byte in chunk: `io.TextIOWrapper` iterato su `ZstdDecompressor.stream_reader` può restituire righe troncate quando i chunk decompressi non coincidono con i confini di riga. Per questo le righe vengono ricostruite con uno split manuale su `\n`, mantenendo in memoria soltanto la riga corrente.

Il file di output viene scritto soltanto se almeno un record appartiene alla whitelist:

* `kept > 0` → il file `.zst` filtrato resta in `data/export/`;
* `kept == 0` → il file di output viene eliminato (nessun file vuoto).

Il sorgente `.zst` viene **sempre** eliminato dopo il processamento, indipendentemente dal numero di record mantenuti.

---

## Whitelist

Il filtro viene applicato durante il processamento (`subreddit_filter.SubRedditFilter`).

La whitelist dei subreddit è definita esternamente al codice:

```text
data/historical_italian_subreddits_2008_2025.json
```

Il processor deve:

1. estrarre dal record il campo `subreddit`;
2. normalizzare il valore (lowercase e strip);
3. verificare la presenza nella whitelist (membership O(1));
4. scartare i record non appartenenti alla whitelist;
5. scrivere esclusivamente i record validi.

La modifica della whitelist non richiede modifiche al codice del processor.

---

## Coda di upload e worker

Il loop di ingestione (`main.py`) produce, per ogni file filtrato, un job di upload nella `queue.Queue` condivisa. Un pool di worker thread concorrenti consuma la coda e carica ciascun file.

Numero di worker configurabile (`UPLOAD_WORKERS`, default 3).

Il worker:

1. prende un job dalla coda;
2. carica il file in upload multi-part;
3. notifica l'esito (successo o errore).

All'uscita dal loop di ingestione, vengono inviate le sentinelle di stop ai worker e si attende (`queue.join()`) che tutti gli upload in coda siano completati prima di terminare il programma.

---

## Object Storage

I file filtrati vengono caricati su Scaleway Object Storage nel percorso remoto:

```text
reddit-dataset/dump-subreddit-italia-since-2008
```

Ogni file `.zst` filtrato viene caricato come **un singolo oggetto**, con chiave:

```text
reddit-dataset/dump-subreddit-italia-since-2008/<nome>.zst
```

L'upload multi-part è usato esclusivamente come ottimizzazione del trasferimento (dividere l'upload in parti parallele per velocità) e **non** suddivide i dati in più oggetti: il risultato è un unico oggetto nel bucket.

L'upload prevede:

* upload multi-part tramite boto3 `TransferConfig` (threshold e chunk size configurabili);
* retry su errori temporanei con backoff esponenziale;
* gestione degli errori permanenti;
* verifica del completamento tramite `head_object`.

Dopo un upload riuscito, il file viene rimosso da `data/export/`.

---

## Completamento del programma

Il loop di ingestione termina quando:

```text
tutti i file attesi hanno completato il download (has_finished)
+
nessun sorgente .zst pendente su disco
```

Al termine, il programma attende il completamento di tutti gli upload in coda prima di uscire.

---

## Sicurezza e configurazione

Le credenziali per qBittorrent e Scaleway Object Storage non devono essere inserite nel repository.

Le configurazioni operative vengono fornite tramite:

* variabili d'ambiente;
* file `.env` locale escluso dal versionamento.

La whitelist dei subreddit rimane invece un file di configurazione versionato:

```text
data/historical_italian_subreddits_2008_2025.json
```

---

## Responsabilità dei componenti

### qBittorrent

Responsabile di:

* download dei torrent;
* verifica del completamento dei file;
* esposizione dello stato tramite API.

### Processor (`processor.py`)

Responsabile di:

* streaming decompression;
* lettura delle righe NDJSON a livello di byte;
* parsing JSON;
* filtro whitelist;
* scrittura del file `.zst` filtrato in `data/export/`;
* eliminazione del sorgente;
* eliminazione dell'output se nessun record è in whitelist.

### SubRedditFilter (`subreddit_filter.py`)

Responsabile di:

* caricamento della whitelist dal file JSON;
* normalizzazione dei nomi;
* verifica di membership O(1).

### Loop di ingestione (`main.py`)

Responsabile di:

* individuazione dei file completati tramite qBittorrent API;
* invio dei file filtrati alla coda di upload;
* gestione dei worker di upload;
* determinazione della condizione di uscita;
* attesa del completamento degli upload.

### Uploader (`uploader.py`)

Responsabile di:

* upload multi-part su Scaleway Object Storage;
* retry su errori temporanei;
* verifica del completamento;
* worker concorrenti che consumano la coda.

# Ottimizzazione architetturale della pipeline


## Parallelizzazione del processing

Non conviene parallelizzare arbitrariamente il singolo `.zst`: decompressione Zstandard, parsing dei record e ricompressione possono essere parallelizzati solo introducendo un meccanismo di **chunking** appropriato, mentre l’attuale modello che i dump di Reddit ci offrono: “un dump → uno stream → un output `.zst`” è naturalmente seriale.

La prima ottimizzazione sarebbe quindi parallelizzare **tra dump**, non necessariamente dentro il dump. Se qBittorrent ha più file completati, più `Processor` possono lavorare contemporaneamente, ciascuno con il proprio input e output, mentre una coda bounded separa processing e upload. In questo modo l’upload lento non diventa una ragione per continuare a generare file filtrati e saturare il disco.

## Code e backpressure

Introdurre una `processing_queue` e una `upload_queue`, entrambe con capacità limitata. qBittorrent rimane la sorgente dei lavori, ma `main.py` non dovrebbe semplicemente lanciare processing e upload senza controllo: deve applicare **backpressure**.

Se `upload_queue` raggiunge la soglia, significa che il processing sta producendo dati più rapidamente di quanto il cloud remoto riesca a consumarli; a quel punto bisogna ridurre o fermare temporaneamente nuovi processor. Analogamente, se `data/export/` cresce oltre una soglia di sicurezza, lo storage locale deve essere considerato saturo e l’ingestione deve rallentare.

La pipeline diventa quindi:

```text
qBittorrent
    ↓
processing_queue [BOUNDED]
    ↓
processor pool
    ↓
upload_queue [BOUNDED]
    ↓
uploader pool
    ↓
Scaleway
```

La coda non è soltanto una struttura dati, ma il meccanismo con cui il sistema comunica la pressione tra gli stadi. Se `upload_queue` è vuota e i processor sono saturi, aumentare gli upload worker non serve; se invece i processor producono rapidamente e `upload_queue` cresce, il collo di bottiglia è l’upload e bisogna intervenire sull’uploader, non creare ulteriori output. Se anche aumentando la concurrency multipart il throughput non cresce, l’upload ha probabilmente raggiunto il limite effettivo imposto da rete, Object Storage o macchina.

## Concorrenza adattiva

L’ottimizzazione più interessante riguarda l’orchestratore. Anziché configurare semplicemente valori fissi come `PROCESSOR_WORKERS=4` e `UPLOAD_WORKERS=8`, il sistema potrebbe partire da un numero conservativo e osservare **throughput, CPU, I/O wait, RAM, dimensione delle queue e occupazione di `data/export/`**, aumentando progressivamente la concorrenza finché il throughput cresce e fermandosi quando il beneficio marginale scompare.

In pratica, se passando da 2 a 3 processor il throughput aumenta significativamente, si continua; se rimane praticamente invariato, 2 rappresentano già il limite utile; se peggiora, si torna indietro. Lo stesso principio può essere applicato agli upload multipart, ma separatamente: il numero ottimale di processor e quello degli upload worker non devono necessariamente coincidere.

## Osservabilità

Prima di introdurre qualsiasi algoritmo sofisticato, bisogna: **misurare il costo reale di ogni fase**. Ogni dump dovrebbe produrre metriche come:

* `input_size`
* `output_size`
* `records_read`
* `records_kept`
* `processing_seconds`
* `processing_MB/s`
* `compression_ratio`
* `upload_seconds`
* `upload_MB/s`
* eventualmente `peak_export_storage`

Questo permette di distinguere un problema di decompressione/parsing da uno di compressione o rete. Senza queste metriche, un adaptive controller rischia di essere soltanto un termostato con gli occhiali.

## RAM e storage locale

Visto che i dump italiani sono molto piccoli, possiamo tenere i nuovi record compressi in RAM (max utilizzo 80%), usando il disco come riserva in caso si satura la RAM. Così da lì direttamente viene fatto l'upload.

La politica utile riguarda quindi soprattutto lo spazio disponibile in `data/export/`: se lo staging supera una percentuale configurabile del filesystem, il producer dovrebbe rallentare o sospendere nuovi processing finché gli uploader non liberano spazio. Questo è più semplice e più aderente all’architettura rispetto all’introduzione di un ulteriore livello artificiale RAM→SSD.

## Separazione delle responsabilità

A livello di codice, separerei ulteriormente le responsabilità:

```text
main.py
    → orchestratore

processor.py
    → worker puro: input → output

uploader.py
    → worker: output → Object Storage

controller.py
    → eventuale adaptive concurrency + metriche

qbittorrent_client.py
    → osservazione dello stato dei download
```


## Architettura complessiva

```text
                         ┌─────────────────────┐
                         │     CONTROLLER      │
                         │                     │
                         │ CPU / I/O / RAM     │
                         │ throughput          │
                         │ queue depth         │
                         │ disk free           │
                         └───────┬─────────────┘
                                 │
                                 ▼
qBittorrent ──► processing_queue [BOUNDED]
                         │
                ┌────────┼────────┐
                ▼        ▼        ▼
             Processor Processor Processor
                │        │        │
                └────────┼────────┘
                         ▼
                   upload_queue
                     [BOUNDED]
                         │
                ┌────────┼────────┐
                ▼        ▼        ▼
             Uploader  Uploader  Uploader
                │        │        │
                └────────┼────────┘
                         ▼
                 Scaleway Object
                    Storage
```

Ottimizza il flusso complessivo**. Il parametro da massimizzare è il throughput end-to-end sostenibile, mentre queue depth, CPU, RAM, disco e rete diventano segnali di feedback. Questo si integra con il progetto attuale senza stravolgere il processor streaming: lo trasforma da unico collo di bottiglia potenziale in uno stadio scalabile e governato.
