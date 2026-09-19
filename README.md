# reddit-it-subreddit-parser

Pipeline ETL per l'ingestione e l'esportazione dei dump storici di tutti i subreddit italiani creati dal 2008 fino al 2025.

I dump vengono scaricati tramite qBittorrent, processati in streaming e filtrati secondo la whitelist dei subreddit italiani. I dati filtrati vengono persistiti in DuckDB e successivamente esportati in chunk `.zst` da circa 10–15 GB e caricati su Scaleway Object Storage.

## Pipeline

```text
qBittorrent
     ↓
torrent/
     ↓
qBittorrent API
     ↓
file ready
     ↓
Processor
     ↓
DuckDB
     ↓
Export
     ↓
chunk-*.zst (~10–15 GB)
     ↓
Scaleway Object Storage
```

## Caratteristiche

* elaborazione dei dump completi `.zst` in streaming;
* nessun file JSON intermedio;
* filtro tramite whitelist di subreddit;
* persistenza in DuckDB;
* processing resumable e idempotente;
* gestione dello stato dei file;
* rilevamento del completamento dei download tramite qBittorrent-api;
* eliminazione dei dump sorgente dopo il processamento riuscito;
* finito di processare tutti i dump in coda;
* export database in chunk `.zst` da ~10–15 GB;
* upload dei chunk su Scaleway Object Storage alla cartella con indirizzo remoto: reddit-dataset/dump-subreddit-italia-since-2008
* possibilità di riprendere un processing o un export interrotto.

## Struttura del progetto

```text
.
├── src/
│   └── ...
├── config/
│   └── historical_italian_subreddits_2008_2025.json
├── data/
│   ├── database/
│   ├── torrent/
│   ├── export/
├── tests/
├── docs/
│   ├── ARCHITECTURE.md
├── README.md
└── ...
```

## Requisiti

Ambiente di riferimento:

* Debian
* Python 3.12+
* DuckDB
* Zstandard
* qBittorrent
* Scaleway Object Storage

## Configurazione

La whitelist dei subreddit è disponibile in questo percorso:

```text
config/historical_italian_subreddits_2008_2025.json
```

Le credenziali e le configurazioni operative non devono essere inserite nel repository.

Utilizzare variabili d'ambiente o un file di configurazione locale escluso dal versionamento.


## Flusso operativo

1. qBittorrent scarica i dump in `data/torrent/`.
2. La pipeline rileva tramite qBittorrent-api quali file sono completati.
3. I file completati vengono segnalati al programma.
4. Il processor legge ogni dump pronto `.zst` in streaming.
5. I record vengono filtrati tramite whitelist.
6. I record validi vengono inseriti in DuckDB.
7. Il file sorgente viene eliminato dopo il completamento della transazione.
8. Quando tutti i file attesi sono stati processati e viene ricevuto il trigger finish da Qbittorrent-api.
9. L'export produce chunk `.zst` da ~10–15 GB.
10. I chunk vengono caricati su Scaleway Object Storage.

## Architettura

La documentazione dettagliata dell'architettura, delle responsabilità dei componenti, del lifecycle dei file, dello stato di recovery e delle condizioni di completamento è disponibile in:

```text
ARCHITECTURE.md
```

## Storage

Lo storage locale è utilizzato come spazio temporaneo per download, processing ed export.

I dump Reddit non vengono mai decompressi integralmente su disco.

Il dataset finale viene trasferito su Scaleway Object Storage.
