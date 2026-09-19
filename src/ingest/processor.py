"""Processor: elaborazione streaming dei dump e inserimento in DuckDB."""

from __future__ import annotations

import io
import json
from collections.abc import Iterator
from pathlib import Path

import zstandard as zstd

from ingest.parsing import parse_comment, parse_submission
from storage.duckdb_store import DuckDBStore
from subreddit_list import SubRedditList


class ProcessingError(Exception):
    """Errore nel processamento di un dump."""


class RecordKind:
    """Tipo logico di un dump."""

    COMMENT = "comment"
    SUBMISSION = "submission"


def infer_kind(path: Path) -> str:
    """Determina il tipo di dump dal nome file.

    Accetta i prefissi:
    - comments / RC_  -> commenti
    - submissions / RS_ -> submission
    """
    name = path.name.upper()
    if name.startswith(("COMMENTS", "RC_")):
        return RecordKind.COMMENT
    if name.startswith(("SUBMISSIONS", "RS_")):
        return RecordKind.SUBMISSION
    raise ProcessingError(f"Impossibile determinare il tipo del dump: {path.name}")


def iter_ndjson(path: Path) -> Iterator[str]:
    """Itera le righe NDJSON del dump decompresso in streaming."""
    with path.open("rb") as file:
        dctx = zstd.ZstdDecompressor(max_window_size=2**31)
        reader = dctx.stream_reader(file)
        text_stream = io.TextIOWrapper(reader, encoding="utf-8", newline="")
        for line in text_stream:
            line = line.strip()
            if not line:
                continue
            yield line


def _parse_record(raw: dict[str, object], kind: str) -> dict[str, object]:
    """Normalizza un record secondo il tipo di dump."""
    if kind == RecordKind.COMMENT:
        return parse_comment(raw)
    return parse_submission(raw)


def _insert_batch(
    store: DuckDBStore, kind: str, batch: list[dict[str, object]]
) -> None:
    if not batch:
        return
    if kind == RecordKind.COMMENT:
        store.insert_comments(batch)
    else:
        store.insert_submissions(batch)


def process_file(
    store: DuckDBStore,
    path: Path,
    whitelist: SubRedditList,
    *,
    batch_size: int = 10_000,
) -> int:
    """Processa un dump in streaming in una singola transazione atomica.

    Restituisce il numero di record inseriti. Il sorgente viene eliminato
    solo dopo il commit riuscito.
    """
    file_path = str(path)
    kind = infer_kind(path)

    store.begin()
    store.begin_processing(file_path)

    inserted = 0
    batch: list[dict[str, object]] = []
    try:
        for line in iter_ndjson(path):
            try:
                raw = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ProcessingError(f"JSON non valido in {path.name}: {exc}") from exc

            if not isinstance(raw, dict):
                continue

            if not whitelist.contains(raw.get("subreddit")):
                continue

            record = _parse_record(raw, kind)
            batch.append(record)

            if len(batch) >= batch_size:
                _insert_batch(store, kind, batch)
                inserted += len(batch)
                batch = []

        if batch:
            _insert_batch(store, kind, batch)
            inserted += len(batch)

        store.mark_completed(file_path)
        store.commit()
    except Exception:
        store.rollback()
        raise

    path.unlink(missing_ok=True)
    return inserted
