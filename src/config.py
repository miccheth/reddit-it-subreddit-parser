"""Configurazione dei percorsi e delle variabili d'ambiente operative."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DATA_DIR = PROJECT_ROOT / "data"
DATABASE_DIR = DATA_DIR / "database"
CHUNK_EXPORT_DIR = DATA_DIR / "chunk_export"

SUBREDDIT_LIST_PATH = DATA_DIR / "historical_italian_subreddits_2008_2025.json"
DATABASE_PATH = DATABASE_DIR / "database.duckdb"


@dataclass(frozen=True)
class QbittorrentConfig:
    """Configurazione di connessione a qBittorrent."""

    host: str
    port: int
    username: str
    password: str


@dataclass(frozen=True)
class ScalewayConfig:
    """Configurazione di accesso a Scaleway Object Storage."""

    endpoint_url: str
    access_key: str
    secret_key: str
    bucket: str
    remote_prefix: str


@dataclass(frozen=True)
class Settings:
    """Configurazione operativa completa della pipeline."""

    chunk_target_bytes: int
    qbittorrent: QbittorrentConfig
    scaleway: ScalewayConfig
    torrent_file: str


def _get_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    return int(raw)


def load_settings() -> Settings:
    """Carica le impostazioni dalle variabili d'ambiente con valori di default."""

    load_dotenv(PROJECT_ROOT / ".env")
    
    return Settings(
        chunk_target_bytes=_get_int("REDDIT_CHUNK_TARGET_BYTES", 12884901888),
        qbittorrent=QbittorrentConfig(
            host=os.getenv("QBITTORRENT_HOST", "localhost"),
            port=_get_int("QBITTORRENT_PORT", 8080),
            username=os.getenv("QBITTORRENT_USERNAME", ""),
            password=os.getenv("QBITTORRENT_PASSWORD", ""),
        ),
        scaleway=ScalewayConfig(
            endpoint_url=os.getenv("SCALEWAY_ENDPOINT_URL", ""),
            access_key=os.getenv("SCALEWAY_ACCESS_KEY", ""),
            secret_key=os.getenv("SCALEWAY_SECRET_KEY", ""),
            bucket=os.getenv("SCALEWAY_BUCKET", ""),
            remote_prefix=os.getenv(
                "SCALEWAY_REMOTE_PREFIX",
                "reddit-dataset/dump-subreddit-italia-since-2008",
            ),
        ),
        torrent_file=os.getenv("QBITTORRENT_TORRENT", ""),
    )
