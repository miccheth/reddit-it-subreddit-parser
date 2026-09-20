"""Entry point main"""

from __future__ import annotations

import queue
import threading
import time
from pathlib import Path

from config import EXPORT_DIR, SUBREDDIT_LIST_PATH, load_settings
from processor import filter_dump
from qbittorrent_client import QbittorrentClientWrapper
from subreddit_filter import SubRedditFilter
from uploader import (
    S3Uploader,
    UploadJob,
    UploadResult,
    _SENTINEL,
    upload_worker,
)

POLL_INTERVAL_SECONDS = 1
UPLOAD_WORKERS = 3


def _on_upload_result(result: UploadResult) -> None:
    print(f"Upload completato: {result.remote_key} ({result.size} bytes)")
    local = EXPORT_DIR / Path(result.remote_key).name
    local.unlink(missing_ok=True)
    print(f"    Rimosso da export: {local.name}")


def _on_upload_error(path: Path, exc: Exception) -> None:
    print(f"ERRORE upload {path}: {exc}")


def run_ingest_loop() -> None:
    """Polling dei file completati e filtraggio in data/export fino a fine lavoro."""
    print("Avvio del loop di ingestione...")
    settings = load_settings()
    print("Configurazione caricata.")

    if not settings.torrent_file:
        print("ERRORE: QBITTORRENT_TORRENT non impostato.")
        raise SystemExit(
            "Imposta QBITTORRENT_TORRENT con l'hash o il nome del torrent "
            "da monitorare."
        )
    print(f"Torrent da monitorare: {settings.torrent_file}")

    print(f"Carico la whitelist dei subreddit da {SUBREDDIT_LIST_PATH} ...")
    subreddit_list = SubRedditFilter.from_file(SUBREDDIT_LIST_PATH)
    print(f"Whitelist caricata ({len(subreddit_list)} subreddit).")

    print(
        f"Connessione a qBittorrent {settings.qbittorrent.host}:"
        f"{settings.qbittorrent.port} ..."
    )
    client = QbittorrentClientWrapper(
        host=settings.qbittorrent.host,
        port=settings.qbittorrent.port,
        username=settings.qbittorrent.username,
        password=settings.qbittorrent.password,
    )
    client.login()
    print("Login a qBittorrent riuscito.")

    client.select_torrent(settings.torrent_file)
    print(f"Torrent selezionato: {settings.torrent_file}")

    uploader = S3Uploader(settings.scaleway)
    upload_queue: queue.Queue[UploadJob | object] = queue.Queue()

    workers: list[threading.Thread] = []
    for worker_id in range(UPLOAD_WORKERS):
        worker = threading.Thread(
            target=upload_worker,
            args=(upload_queue, uploader),
            kwargs={
                "worker_id": worker_id,
                "on_result": _on_upload_result,
                "on_error": _on_upload_error,
            },
            daemon=True,
        )
        worker.start()
        workers.append(worker)

    print(f"Avviati {UPLOAD_WORKERS} worker di upload.")

    while True:
        print("Controllo i file completati...")
        all_completed = client.completed_files()
        print(f"File completati da qBittorrent: {len(all_completed)}")

        completed = [
            file
            for file in all_completed
            if file.path.exists()
        ]
        print(f"Di cui ancora presenti su disco da processare: {len(completed)}")

        for file in completed:
            print(f"--> Processo {file.path} ...")
            kept = filter_dump(file.path, subreddit_list, EXPORT_DIR)
            exported = EXPORT_DIR / file.path.name
            print(f"<-- {file.path.name}: {kept} record mantenuti -> {EXPORT_DIR}")
            if exported.exists():
                upload_queue.put(UploadJob(path=exported))
                print(f"    Accodato per upload: {exported.name}")
            else:
                print(f"    Nessun record mantenuto: {exported.name} non caricato.")

        if client.has_finished() and not completed:
            print("Tutti i download completati e nessun sorgente pendente: termino.")
            break

        print(
            f"Non ancora terminato: attendo {POLL_INTERVAL_SECONDS}s "
            "prima del prossimo controllo."
        )
        time.sleep(POLL_INTERVAL_SECONDS)

    for _ in range(UPLOAD_WORKERS):
        upload_queue.put(_SENTINEL)

    print("Attendo il completamento degli upload in coda...")
    upload_queue.join()
    for worker in workers:
        worker.join(timeout=5.0)

    uploader.close()
    print("Tutti i file sono stati processati e caricati.")


if __name__ == "__main__":
    run_ingest_loop()
