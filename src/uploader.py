"""Uploader: caricamento multi-part dei file esportati su Scaleway Object Storage."""

from __future__ import annotations

import queue
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import boto3
from boto3.s3.transfer import TransferConfig

from config import ScalewayConfig

MAX_RETRIES = 3
BACKOFF_SECONDS = 2.0

DEFAULT_MULTIPART_THRESHOLD = 8 * 1024 * 1024
DEFAULT_MULTIPART_CHUNKSIZE = 8 * 1024 * 1024
DEFAULT_MAX_CONCURRENCY = 4


class UploadError(Exception):
    """Errore non recuperabile durante l'upload."""


@dataclass(frozen=True)
class UploadResult:
    """Esito dell'upload di un file."""

    remote_key: str
    size: int


def _is_transient_error(exc: Exception) -> bool:
    """Classifica un errore come temporaneo (retryabile) o permanente."""
    response = getattr(exc, "response", None)
    if response is not None:
        metadata = getattr(response, "ResponseMetadata", {})
        status = metadata.get("HTTPStatusCode")
        if isinstance(status, int) and 500 <= status < 600:
            return True
    return type(exc).__name__ in {
        "ConnectionError",
        "Timeout",
        "EndpointConnectionError",
        "ReadTimeoutError",
    }


class S3Uploader:
    """Carica i file su un bucket S3-compatibile (Scaleway) in multi-part."""

    def __init__(
        self,
        config: ScalewayConfig,
        *,
        client: Any | None = None,
        multipart_threshold: int = DEFAULT_MULTIPART_THRESHOLD,
        multipart_chunksize: int = DEFAULT_MULTIPART_CHUNKSIZE,
        max_concurrency: int = DEFAULT_MAX_CONCURRENCY,
    ) -> None:
        self._config = config
        self._client = client or boto3.client(
            "s3",
            endpoint_url=config.endpoint_url,
            aws_access_key_id=config.access_key,
            aws_secret_access_key=config.secret_key,
        )
        self._transfer_config = TransferConfig(
            multipart_threshold=multipart_threshold,
            multipart_chunksize=multipart_chunksize,
            max_concurrency=max_concurrency,
        )

    def remote_key(self, file_name: str) -> str:
        """Costruisce la chiave remota per un file."""
        return f"{self._config.remote_prefix.rstrip('/')}/{file_name}"

    def upload(self, local_path: Path) -> UploadResult:
        """Carica un file in multi-part con retry su errori temporanei.

        Per file più grandi di `multipart_threshold` l'upload viene
        automaticamente eseguito in multi-part da boto3. Al termine verifica
        il completamento tramite la presenza dell'oggetto remoto.
        """
        file_name = local_path.name
        key = self.remote_key(file_name)
        size = local_path.stat().st_size

        last_error: Exception | None = None
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                self._client.upload_file(
                    str(local_path),
                    self._config.bucket,
                    key,
                    Config=self._transfer_config,
                )
                self._verify(key)
                return UploadResult(remote_key=key, size=size)
            except Exception as exc:
                last_error = exc
                if not _is_transient_error(exc):
                    raise UploadError(
                        f"Errore permanente upload {key}: {exc}"
                    ) from exc
                if attempt < MAX_RETRIES:
                    delay = BACKOFF_SECONDS * (2 ** (attempt - 1))
                    time.sleep(delay)

        raise UploadError(
            f"Upload fallito dopo {MAX_RETRIES} tentativi: {key}"
        ) from last_error

    def _verify(self, key: str) -> None:
        """Verifica che l'oggetto remoto esista dopo l'upload."""
        self._client.head_object(
            Bucket=self._config.bucket,
            Key=key,
        )

    def close(self) -> None:
        """Chiude la connessione del client."""
        self._client.close()


_SENTINEL = object()


@dataclass(frozen=True)
class UploadJob:
    """Incapsula il lavoro di un singolo upload per i worker."""

    path: Path


def upload_worker(
    jobs: queue.Queue[UploadJob | object],
    uploader: S3Uploader,
    *,
    worker_id: int,
    on_result: Callable[[UploadResult], None] | None = None,
    on_error: Callable[[Path, Exception], None] | None = None,
) -> None:
    """Consuma i job dalla coda e li carica in multi-part.

    Esce quando riceve il valore sentinella `_SENTINEL`.
    """
    while True:
        item = jobs.get()
        try:
            if item is _SENTINEL:
                break
            job: UploadJob = item
            result = uploader.upload(job.path)
            if on_result is not None:
                on_result(result)
        except Exception as exc:
            if on_error is not None:
                on_error(job.path, exc)
        finally:
            jobs.task_done()
