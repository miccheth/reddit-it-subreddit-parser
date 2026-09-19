# Architettura

## Obiettivo

Pipeline ETL per l'ingestione e l'esportazione dei dump storici Reddit relativi ad una lista di subreddit italiani.

I dump `comments` e `submissions` vengono scaricati tramite qBittorrent, rilevati dalla pipeline tramite qBittorrent API quando risultano completati, processati in streaming e filtrati secondo una whitelist configurabile di subreddit italiani.

I record filtrati vengono persistiti in DuckDB. Al termine dell'ingestione, quando tutti i file attesi sono stati processati e viene ricevuto il trigger di fine nella coda dei dump da Qbittorrent-api, il database viene esportato in un unico dataset logico unifico composto da `submissions` e `comments`, suddiviso in chunk `.zst` da circa 10–15 GB e caricato su Scaleway Object Storage.

Obiettivi principali:

* processare i dump `.zst` senza decomprimerli integralmente su disco;
* elaborare i record in streaming;
* evitare file JSON intermedi;
* filtrare i record prima della persistenza;
* garantire processing resumable e idempotente;
* mantenere lo stato di ogni file processato;
* eliminare i dump sorgente dopo il processamento riuscito;
* rilevare lo stato dei download tramite qBittorrent API;
* esportare il dataset finale in chunk indipendenti;
* permettere la ripresa di processing ed export interrotti.

---

## Pipeline

```text
qBittorrent
     │
     │ download
     ▼
data/torrent/
     │
     │ qBittorrent API
     │ file completed
     ▼
Processor
     │
     │ Zstd streaming
     │ NDJSON parsing
     │ whitelist filtering
     ▼
DuckDB
     │
     │ tutti i file attesi processati
     │ + trigger di finish da processare in coda
     ▼
Export
     │
     │ submissions + comments
     │ stream serialization
     │ Zstd chunking
     ▼
chunk-*.zst
     │
     │ upload
     ▼
Scaleway Object Storage
remote: reddit-dataset/dump-subreddit-italia-since-2008
```

---

## Input

I dump sono forniti tramite torrent e hanno struttura logica:

```text
data/
->
torrent/
->
reddit/
├── comments/
│   └── RC_YYYY-MM.zst
└── submissions/
    └── RS_YYYY-MM.zst
```

`comments` e `submissions` sono dataset distinti e possono avere schemi differenti.

### Schema dei record

L'architettura non deve assumere preventivamente uno schema completo dei dump.

I campi effettivamente disponibili devono essere determinati mediante ispezione dei dump reali.

In particolare, devono essere identificati i campi necessari a:

identificare univocamente i record;
determinare il subreddit;
distinguere comments e submissions;
ricostruire durante l'export la relazione tra commenti e submission, se richiesta dal formato finale;
preservare i dati necessari al dataset finale.

Lo schema DuckDB deve essere definito sulla base dello schema reale dei dump e delle esigenze dell'export.L'architettura non deve assumere preventivamente uno schema completo dei dump.

I campi effettivamente disponibili devono essere determinati mediante ispezione dei dump reali.

In particolare, devono essere identificati i campi necessari a:

* identificare univocamente i record, quindi tipo l'ID del comments associato al submissions rimane;
* determinare il subreddit;
* distinguere comments e submissions;
* ricostruire durante l'export la relazione tra commenti e submission, se richiesta dal formato finale;
* preservare i dati necessari al dataset finale.

Lo schema DuckDB deve essere definito sulla base dello schema reale dei dump e delle esigenze dell'export.

Quindi alla fine avremo un unico database con uno schema fuso di dumps e submissions.

---

## Storage locale

Struttura prevista:

```text
data/
├── database/
│   └── database.duckdb
├── torrent/
│   └── ...
├── export/
│   └── chunks/

config/
└── historical_italian_subreddits_2008_2025.json
```

Ambiente attuale di riferimento (ci saranno nuove librerie probabilmente):

```text
Debian 12
Python 3.12+
12 vCPU
24 GB RAM
500 GB storage
DuckDB
Zstandard
qbittorrent-api
Scaleway Object Storage
```

Lo storage locale è temporaneo e viene utilizzato per:

* download dei torrent;
* processamento dei dump;
* generazione temporanea dei chunk durante l'export, quando necessario.

I dump Reddit `.zst` **non devono mai essere decompressi integralmente su disco**.

La decompressione deve avvenire esclusivamente in streaming.

---

## qBittorrent e rilevamento dei file pronti

qBittorrent è responsabile del download dei dump.

La pipeline utilizza qBittorrent API per determinare quali file risultano effettivamente completati.

Il flusso è:

```text
qBittorrent download
        ↓
qBittorrent API
        ↓
dump list files to be downloaded queue
        ↓
torrent completato -> segnale di stop nella queue
        ↓
Processor
```

Un file viene preso in carico dal processor soltanto quando qBittorrent ne segnala il completamento.

Non è necessario implementare un file watcher basato su `inotify` per determinare la disponibilità dei dump.

---

## File lifecycle

Il lifecycle logico di un file è:

```text
DOWNLOAD
   │
   │ qBittorrent API → completed
   ▼
PENDING
   │
   ▼
PROCESSING
   │
   ├──────────────► FAILED
   │
   ▼
COMPLETED
   │
   ▼
source deleted
```

### Regole

* Un file non completato da qBittorrent non deve essere processato.
* Un file già `COMPLETED` non deve essere rielaborato.
* Un file `FAILED` può essere ritentato.
* Non devono essere eseguiti contemporaneamente due worker sullo stesso file.
* Il file sorgente `.zst` deve essere eliminato **solo dopo il commit della transazione DuckDB**.
* Lo stato del file deve rimanere persistito in DuckDB anche dopo la cancellazione del sorgente.
* La cancellazione del sorgente non deve essere utilizzata come indicatore dello stato di processamento.

---

## Processing

Ogni dump viene processato interamente in streaming:

```text
.zst
 ↓
Zstandard streaming decompression
 ↓
NDJSON line
 ↓
JSON parse
 ↓
extract subreddit
 ↓
whitelist check
 ↓
discard
   oppure
batch insert
 ↓
DuckDB
```

Non deve essere creato un file JSON intermedio.

Il processor non deve caricare l'intero dump in memoria.

Il consumo di memoria deve rimanere sostanzialmente indipendente dalla dimensione del dump, utilizzando:

* decompressione streaming;
* parsing record-by-record;
* batch di dimensione configurabile per gli insert in DuckDB.

---

## Whitelist

Il filtro viene applicato prima della persistenza in DuckDB.

La whitelist dei subreddit è definita esternamente al codice:

```text
config/historical_italian_subreddits_2008_2025.json
```

Il processor deve:

1. estrarre dal record il subreddit;
2. normalizzare il valore secondo le regole definite dalla pipeline;
3. verificare la presenza nella whitelist;
4. scartare i record non appartenenti alla whitelist;
5. persistere esclusivamente i record validi.

La modifica della whitelist non deve richiedere modifiche al codice del processor.

---

## DuckDB

Il database locale costituisce lo storage persistente intermedio della pipeline.

Tabelle minime:

gli schemi di `comments` e `submissions` vengono fusi in un unico schema logico.

---

## Stato e recovery

Gli stati principali sono:

```text
PENDING
   ↓
PROCESSING
   ├──→ FAILED
   ↓
COMPLETED
```

Il processamento di un singolo file deve essere atomico rispetto alla persistenza dei dati in DuckDB.

Schema logico:

```text
BEGIN TRANSACTION

    mark file PROCESSING

    read .zst in streaming

    filter records

    insert batches

    mark file COMPLETED

COMMIT
```

Se il processamento fallisce prima del `COMMIT`, le modifiche alla transazione vengono rollbackate.

### Regole di recovery

* `COMPLETED` → il file non viene rielaborato;
* `FAILED` → il file può essere ritentato;
* `PROCESSING` lasciato da un processo terminato in modo anomalo deve poter essere recuperato secondo le informazioni di stato persistite;
* nessun file può essere elaborato contemporaneamente da due worker;
* un retry non deve produrre duplicati;
* il sorgente viene cancellato solo dopo il commit riuscito.

L'idempotenza deve essere garantita a livello di pipeline e non deve dipendere dalla presenza del file sul filesystem.

---

## Completion condition

Quando viene inviato il segnale di trigger stop da Qbittorrent-api alla pipeline queue di Download in corso, cioè che il torrent ha scaricato tutto.


La directory dei torrent vuota non implica il completamento.

Il trigger di stop segnala che qBittorrent ha terminato il ciclo di download previsto e che la pipeline può passare dalla fase di ingestione alla fase di export, purché tutti i file attesi siano stati processati.

---

## Export

L'export viene avviato esclusivamente quando:

```text
all expected files COMPLETED
+
finish trigger stop ricevuto.
```

Il database DuckDB viene esportato in un unico dataset logico composto da:

```text
submissions + comments
```

L'export deve essere eseguito in streaming e non deve creare un file temporaneo contenente l'intero dataset.

Flusso:

```text
DuckDB
   ↓
submissions + comments
   ↓
eventuale ricostruzione delle relazioni
   ↓
stream serialization
   ↓
Zstandard
   ↓
chunk-*.zst
```

La relazione tra `comments` e `submissions` deve essere ricostruita utilizzando gli identificativi effettivamente presenti nei dump e identificati durante l'analisi dello schema.

Non devono essere introdotte assunzioni arbitrarie sui nomi o sulla struttura dei campi.

---

## Chunking

L'export viene suddiviso in chunk `.zst` con dimensione target di circa:

```text
10–15 GB per chunk
```

La dimensione è un target operativo e non deve richiedere la produzione di chunk perfettamente identici.

Ogni chunk deve essere:

* autonomo;
* valido;
* decomprimibile indipendentemente;
* composto esclusivamente da record completi;
* identificato univocamente;
* compatibile con il formato del dataset finale.

Un singolo chunk può contenere sia record `submissions` sia record `comments`.

Il dataset rappresentato dai chunk costituisce un unico dataset logico.

Non deve essere creato un file intermedio contenente l'intero export prima della suddivisione.

---

## Object Storage

I chunk finali vengono caricati su Scaleway Object Storage nel percorso remoto:

```text
reddit-dataset/dump-subreddit-italia-since-2008
```

Struttura logica:

```text
reddit-dataset/
└── dump-subreddit-italia-since-2008/
    ├── chunk-000001.zst
    ├── chunk-000002.zst
    ├── chunk-000003.zst
    └── ...
```

L'upload deve prevedere:

* retry in caso di errore temporaneo;
* gestione degli errori permanenti;
* verifica del completamento dell'upload;
* upload multi-part per velocizzare la velocità di upload.
* possibilità di riprendere un export interrotto;
* identificazione univoca dei chunk.

Un chunk viene considerato completato solo dopo la conferma dell'upload.

---

## Sicurezza e configurazione

Le credenziali per qBittorrent e Scaleway Object Storage non devono essere inserite nel repository.

Le configurazioni operative devono essere fornite tramite:

* variabili d'ambiente;
* file di configurazione locale escluso dal versionamento;
* eventuali secret manager compatibili con l'ambiente di deployment.

La whitelist dei subreddit rimane invece un file di configurazione versionato:

```text
config/historical_italian_subreddits_2008_2025.json
```

---

## Responsabilità dei componenti

### qBittorrent

Responsabile di:

* download dei torrent;
* verifica del completamento dei file;
* esposizione dello stato tramite API.

### Processor

Responsabile di:

* individuazione dei file completati tramite qBittorrent API;
* streaming decompression;
* parsing NDJSON;
* filtro whitelist;
* batch insert;
* gestione dello stato del file;
* recovery e idempotenza;
* eliminazione del sorgente dopo il commit.

### DuckDB

Responsabile di:

* persistenza dei record filtrati;
* stato dei file;
* informazioni necessarie al recovery;
* sorgente dell'export finale.

### Exporter

Responsabile di:

* lettura dei dati da DuckDB;
* costruzione del dataset logico `comments + submissions`;
* serializzazione streaming;
* chunking `.zst`;
* recovery dell'export.

### Object Storage uploader

Responsabile di:

* upload dei chunk;
* retry;
* verifica del completamento;
* recovery degli upload interrotti.

---
