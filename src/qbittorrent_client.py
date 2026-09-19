"""Client per qBittorrent: monitoraggio di un torrent e dei suoi file."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from qbittorrentapi import Client as QbittorrentClient


_COMPLETE_THRESHOLD = 1.0


class TorrentNotFoundError(Exception):
    """Il torrent richiesto non esiste in qBittorrent."""


@dataclass(frozen=True)
class TorrentFileState:
    """Stato di un singolo file selezionato all'interno del torrent."""

    path: Path
    size: int
    progress: float

    @property
    def is_complete(self) -> bool:
        """True se il file ha terminato il download."""
        return self.progress >= _COMPLETE_THRESHOLD


def _as_float(value: object, default: float = 0.0) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    return default


def _as_int(value: object, default: int = 0) -> int:
    if isinstance(value, (int, float)):
        return int(value)
    return default


def _as_str(value: object) -> str | None:
    if isinstance(value, str) and value:
        return value
    return None


class QbittorrentClientWrapper:
    """Client applicativo per qBittorrent.

    Seleziona un singolo torrent (per hash o nome) e consente di
    monitorare esclusivamente i file selezionati per il download.
    """

    def __init__(
        self,
        host: str,
        port: int,
        username: str,
        password: str,
        client: QbittorrentClient | None = None,
    ) -> None:
        self._client = client or QbittorrentClient(
            host=host,
            port=port,
            username=username,
            password=password,
        )
        self._torrent_hash: str | None = None
        self._torrent_save_path: Path | None = None

    def login(self) -> None:
        """Effettua il login a qBittorrent."""
        self._client.auth_log_in()

    def select_torrent(self, hash_or_name: str) -> None:
        """Seleziona il torrent da monitorare, per hash o per nome.

        Se il valore coincide con l'hash di un torrent viene usato quello,
        altrimenti viene cercato per nome esatto.
        """
        for torrent in self._client.torrents_info():
            data: Mapping[str, Any] = torrent

            if (
                data.get("hash") == hash_or_name
                or data.get("name") == hash_or_name
            ):
                self._torrent_hash = _as_str(data.get("hash"))
                self._torrent_save_path = Path(
                    _as_str(data.get("save_path")) or ""
                )
                return

        raise TorrentNotFoundError(
            f"Torrent non trovato: {hash_or_name}"
        )

    def file_states(self) -> list[TorrentFileState]:
        """Restituisce lo stato dei soli file selezionati per il download."""
        if self._torrent_hash is None:
            raise RuntimeError(
                "Nessun torrent selezionato: chiamare select_torrent()"
            )

        save_path = self._torrent_save_path or Path()
        states: list[TorrentFileState] = []

        for file in self._client.torrents_files(self._torrent_hash):
            data: Mapping[str, Any] = file

            # qBittorrent usa priority == 0 per i file non selezionati.
            priority = _as_int(data.get("priority"))

            if priority <= 0:
                continue

            name = _as_str(data.get("name"))
            if name is None:
                continue

            states.append(
                TorrentFileState(
                    path=save_path / name,
                    size=_as_int(data.get("size")),
                    progress=_as_float(data.get("progress")),
                )
            )

        return states

    def completed_files(self) -> list[TorrentFileState]:
        """Restituisce i soli file selezionati che hanno completato il download."""
        return [
            file
            for file in self.file_states()
            if file.is_complete
        ]

    def has_finished(self) -> bool:
        """True se tutti i file selezionati sono completati."""
        states = self.file_states()

        return bool(states) and all(
            file.is_complete
            for file in states
        )