"""Processor: filtraggio streaming dei dump .zst secondo la whitelist dei subreddit italiani."""

from __future__ import annotations

import json
from pathlib import Path

import io

import zstandard as zstd

from subreddit_filter import SubRedditFilter


class ProcessingError(Exception):
    """Errore nel processamento di un dump."""


def filter_dump(
    source: Path, whitelist: SubRedditFilter, out_dir: Path
) -> int:
    out_path = out_dir / source.name
    out_dir.mkdir(parents=True, exist_ok=True)

    kept = 0
    cctx = zstd.ZstdCompressor()

    with (
        source.open("rb") as in_file,
        out_path.open("wb") as out_file,
    ):
        dctx = zstd.ZstdDecompressor(max_window_size=2**31)

        with (
            dctx.stream_reader(in_file) as zstd_reader,
            cctx.stream_writer(out_file) as writer,
        ):
            # Aggiunge buffering e permette readline()
            reader = io.BufferedReader(zstd_reader)

            while True:
                line = reader.readline()

                if not line:
                    break

                line = line.strip()

                if not line:
                    continue

                record = json.loads(line)

                if whitelist.contains(record.get("subreddit")):
                    writer.write(line + b"\n")
                    kept += 1

    if kept == 0:
        out_path.unlink(missing_ok=True)

    source.unlink()
    return kept