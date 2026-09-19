"""Uploader: caricamento dei chunk su Scaleway Object Storage (S3)."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import boto3

from config import ScalewayConfig

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
BACKOFF_SECONDS = 2.0


class UploadError(Exception):
    """Errore non recuperabile durante l'upload."""


@dataclass(frozen=True)
class UploadResult:
    """Esito dell'upload di un chunk."""

    remote_key: str
    etag: str


def _is_transient_error(exc: Exception) -> bool:
    """Classifica un errore come temporaneo (retryabile) o permanente."""
    code = getattr(exc, "response", None)
    if code is not None:
        status = getattr(code, "ResponseMetadata", {}).get("HTTPStatusCode")
        if isinstance(status, int) and 500 <= status < 600:
            return True
    name = type(exc).__name__
    return name in {"ConnectionError", "Timeout", "EndpointConnectionError"}


class S3Uploader:
    """Carica i chunk su un bucket S3-compatibile (Scaleway)."""

    def __init__(
        self,
        config: ScalewayConfig,
        client: Any | None = None,
    ) -> None:
        self._config = config
        self._client = client or boto3.client(
            "s3",
            endpoint_url=config.endpoint_url,
            aws_access_key_id=config.access_key,
            aws_secret_access_key=config.secret_key,
        )

    def remote_key(self, chunk_name: str) -> str:
        """Costruisce la chiave remota per un chunk."""
        return f"{self._config.remote_prefix.rstrip('/')}/{chunk_name}"

    def upload_chunk(self, local_path: Path, chunk_name: str) -> UploadResult:
        """Carica un chunk con retry su errori temporanei.

        L'upload multi-part è gestito automaticamente da boto3 per file
        di grandi dimensioni. Verifica il completamento tramite la ETag.
        """
        key = self.remote_key(chunk_name)

        last_error: Exception | None = None
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                response = self._client.upload_file(
                    str(local_path),
                    self._config.bucket,
                    key,
                )
                etag = self._verify_upload(local_path, key)
                logger.info(
                    "Upload completato: %s (tentativo %d)", key, attempt
                )
                return UploadResult(remote_key=key, etag=etag)
            except Exception as exc:
                last_error = exc
                if not _is_transient_error(exc):
                    raise UploadError(f"Errore permanente upload {key}: {exc}") from exc
                if attempt < MAX_RETRIES:
                    delay = BACKOFF_SECONDS * (2 ** (attempt - 1))
                    logger.warning(
                        "Errore temporaneo upload %s (tentativo %d): %s. Retry in %ss",
                        key,
                        attempt,
                        exc,
                        delay,
                    )
                    time.sleep(delay)

        raise UploadError(f"Upload fallito dopo {MAX_RETRIES} tentativi: {key}") from last_error

    def _verify_upload(self, local_path: Path, key: str) -> str:
        """Verifica che l'oggetto sia stato caricato e ne restituisce la ETag."""
        head = self._client.head_object(Bucket=self._config.bucket, Key=key)
        etag = head.get("ETag", "")
        if not etag:
            raise UploadError(f"Verifica fallita: ETag mancante per {key}")
        return etag
