"""Exporter: serializzazione streaming del dataset e chunking .zst."""

from __future__ import annotations

import io
import json
from pathlib import Path
from typing import Any

import zstandard as zstd

from storage.duckdb_store import DuckDBStore

_CHUNK_PREFIX = "chunk-"
_CHUNK_SUFFIX = ".zst"

_COLUMN_ORDER = (
    "kind",
    "id",
    "subreddit",
    "author",
    "created_utc",
    "body",
    "link_id",
    "parent_id",
    "score",
    "title",
)


def _record_to_dict(values: tuple[str, ...]) -> dict[str, object]:
    """Associa i valori di una riga alle colonne del dataset esportato."""
    return {name: value for name, value in zip(_COLUMN_ORDER, values, strict=True)}


def next_chunk_number(chunk_dir: Path) -> int:
    """Restituisce il numero del prossimo chunk (1-based) per recovery."""
    max_number = 0
    if chunk_dir.exists():
        for path in chunk_dir.glob(f"{_CHUNK_PREFIX}*{_CHUNK_SUFFIX}"):
            stem = path.name[len(_CHUNK_PREFIX) : -len(_CHUNK_SUFFIX)]
            if stem.isdigit():
                max_number = max(max_number, int(stem))
    return max_number + 1


def chunk_path(chunk_dir: Path, number: int) -> Path:
    return chunk_dir / f"{_CHUNK_PREFIX}{number:06d}{_CHUNK_SUFFIX}"


class _ChunkWriter:
    """Gestisce la scrittura incrementale di un singolo chunk .zst."""

    _file: Any
    _writer: Any
    _stream: Any
    size: int

    def __init__(self, path: Path) -> None:
        self._file = path.open("wb")
        self._writer = zstd.ZstdCompressor().stream_writer(self._file)
        self._stream = io.TextIOWrapper(self._writer, encoding="utf-8", newline="")
        self.size = 0

    def write_line(self, line: str) -> None:
        self._stream.write(line + "\n")
        self.size += len(line) + 1

    def close(self) -> None:
        self._stream.flush()
        self._writer.flush()
        self._file.flush()
        self._stream.close()
        self._writer.close()
        self._file.close()


def export_records(
    store: DuckDBStore,
    chunk_dir: Path,
    *,
    target_bytes: int,
    batch_size: int = 10_000,
) -> list[Path]:
    """Esporta il dataset in chunk .zst indipendenti.

    Legge i record in streaming e li distribuisce in chunk che vengono
    chiusi quando superano il target. Restituisce i percorsi dei chunk
    prodotti. I chunk già esistenti vengono saltati (recovery).
    """
    chunk_dir.mkdir(parents=True, exist_ok=True)
    number = next_chunk_number(chunk_dir)
    produced: list[Path] = []

    chunk: _ChunkWriter | None = None

    for values in store.iter_records(batch_size):
        if chunk is None:
            chunk = _ChunkWriter(chunk_path(chunk_dir, number))

        line = json.dumps(_record_to_dict(values), ensure_ascii=False)
        chunk.write_line(line)

        if chunk.size >= target_bytes:
            chunk.close()
            produced.append(chunk_path(chunk_dir, number))
            number += 1
            chunk = None

    if chunk is not None:
        chunk.close()
        produced.append(chunk_path(chunk_dir, number))

    return produced
