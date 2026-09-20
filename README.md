# reddit-it-subreddit-parser

Pipeline per il filtraggio dei dump storici Reddit, tenendo soltanto i subreddit italiani.

I dump `comments` e `submissions` vengono scaricati tramite qBittorrent, processati in streaming e filtrati secondo una whitelist di subreddit italiani. Il risultato è un nuovo file `.zst` (con lo stesso nome) che contiene solo i record dei subreddit in whitelist, caricato poi su Scaleway Object Storage in upload multi-part.

## Pipeline

```text
qBittorrent
     ↓
file completo .zst
     ↓
Processor (filtro streaming + whitelist)
     ↓
data/export/<nome>.zst (filtrato)
     ↓
coda upload (N worker)
     ↓
Scaleway Object Storage (multi-part)
```

## Caratteristiche

* elaborazione dei dump `.zst` in streaming, senza decompressione integrale su disco;
* nessun file JSON intermedio;
* filtro tramite whitelist di subreddit (`SubRedditFilter`);
* scrittura di un nuovo `.zst` filtrato in `data/export/` con lo stesso nome del sorgente;
* nessun file vuoto in export se un dump non contiene subreddit della whitelist;
* eliminazione sempre del dump sorgente dopo il processamento;
* rilevamento del completamento dei download tramite qbittorrent-api;
* upload multi-part su Scaleway Object Storage con worker concorrenti;
* rimozione del file esportato da `data/export/` dopo un upload riuscito.

## Struttura del progetto

```text
.
├── src/
│   ├── main.py              # loop di ingestione + coda upload
│   ├── processor.py         # filtraggio streaming .zst
│   ├── subreddit_filter.py  # whitelist dei subreddit
│   ├── uploader.py          # upload multi-part e worker
│   ├── qbittorrent_client.py
│   └── config.py
├── data/
│   ├── export/              # .zst filtrati (transitori, rimossi dopo l'upload)
│   └── historical_italian_subreddits_2008_2025.json
├── ARCHITECTURE.md
└── README.md
```

## Requisiti

* Python 3.12+
* Zstandard
* qbittorrent-api
* boto3 (upload S3/Scaleway)

## Configurazione

La whitelist dei subreddit è disponibile in:

```text
data/historical_italian_subreddits_2008_2025.json
```

Le credenziali e le configurazioni operative vengono fornite tramite variabili d'ambiente o un file `.env` locale escluso dal versionamento. Si vedano le variabili in `.env.example`:

* `QBITTORRENT_HOST`, `QBITTORRENT_PORT`, `QBITTORRENT_USERNAME`, `QBITTORRENT_PASSWORD`, `QBITTORRENT_TORRENT`
* `SCALEWAY_ENDPOINT_URL`, `SCALEWAY_ACCESS_KEY`, `SCALEWAY_SECRET_KEY`, `SCALEWAY_BUCKET`, `SCALEWAY_REMOTE_PREFIX`

## Flusso operativo

1. qBittorrent scarica i dump `.zst` (comments e submissions).
2. Il loop di `main.py` interroga qbittorrent-api per individuare i file completati.
3. Per ogni file completo ancora presente su disco, il processor legge il `.zst` in streaming.
4. I record vengono filtrati tramite la whitelist dei subreddit italiani.
5. I record mantenuti vengono scritti, ricompressi, in `data/export/<nome>.zst`.
6. Se nessun record appartiene alla whitelist, l'output viene eliminato (nessun file vuoto).
7. Il sorgente `.zst` viene sempre eliminato.
8. Il file filtrato viene accodato e caricato in multi-part su Scaleway Object Storage da un worker disponibile.
9. Dopo un upload riuscito, il file viene rimosso da `data/export/`.
10. Il programma termina quando tutti i download sono completati e non restano sorgenti pendenti, attendendo il completamento degli upload.

## Architettura

La documentazione dettagliata dell'architettura e delle responsabilità dei componenti è disponibile in:

```text
ARCHITECTURE.md
```

## Storage

Lo storage locale è utilizzato come spazio temporaneo per download, filtraggio ed export.

I dump Reddit non vengono mai decompressi integralmente su disco: la decompressione avviene esclusivamente in streaming.
