"""Entry point CLI della pipeline."""

from __future__ import annotations

import os
import time
from collections import deque
from pathlib import Path

from config import DATABASE_PATH, SUBREDDIT_LIST_PATH, load_settings
from ingest.processor import process_file
from qbittorrent_client import QbittorrentClientWrapper
from storage.duckdb_store import DuckDBStore
from subreddit_list import SubRedditList

POLL_INTERVAL_SECONDS = 5.0
DEFAULT_BATCH_SIZE = 10_000


def run_ingest_loop() -> None:
    """Polling dei file in download e invio al processor quando pronti."""
    settings = load_settings()

    if not settings.torrent_file:
        raise SystemExit(
            "Imposta QBITTORRENT_TORRENT con l'hash o il nome del torrent "
            "da monitorare."
        )

    whitelist = SubRedditList.from_file(SUBREDDIT_LIST_PATH)
    batch_size = int(os.getenv("REDDIT_BATCH_SIZE", DEFAULT_BATCH_SIZE))

    client = QbittorrentClientWrapper(
        host=settings.qbittorrent.host,
        port=settings.qbittorrent.port,
        username=settings.qbittorrent.username,
        password=settings.qbittorrent.password,
    )
    client.login()
    client.select_torrent(settings.torrent_file)

    pending = deque(file.path for file in client.file_states())
    print(f"File in attesa: {len(pending)}")

    with DuckDBStore(DATABASE_PATH) as store:
        while pending:
            ready = client.completed_files()
            ready_paths = {file.path for file in ready}

            still_pending: deque[Path] = deque()
            for path in pending:
                if path in ready_paths:
                    print(f"File pronto, invio al processor: {path}")
                    inserted = process_file(
                        store, path, whitelist, batch_size=batch_size
                    )
                    print(f"File processato ({inserted} record) ed eliminato: {path}")
                else:
                    still_pending.append(path)

            pending = still_pending

            if pending:
                print(f"Attendo il completamento di {len(pending)} file...")
                time.sleep(POLL_INTERVAL_SECONDS)

    print("Tutti i file sono stati processati.")


if __name__ == "__main__":
    run_ingest_loop()
