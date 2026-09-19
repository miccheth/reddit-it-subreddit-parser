"""Parsing e normalizzazione dei record Reddit per l'import in DuckDB."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any


def _to_int(value: object) -> int | None:
    """Normalizza un valore a BIGINT (None se assente o non convertibile)."""
    if value is None:
        return None
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return None
    return None


def _to_required_int(value: object) -> int:
    """Normalizza un valore a BIGINT non-null (0 come fallback)."""
    return _to_int(value) or 0


def _to_optional_int(value: object) -> int | None:
    """Normalizza un valore a BIGINT nullable (None se assente)."""
    return _to_int(value)


def _to_bool(value: object) -> bool:
    """Normalizza a BOOLEAN accettando bool o numerici (edited, is_self, ...)."""
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes"}
    return False


def _to_nullable_bool(value: object) -> bool | None:
    """Normalizza a BOOLEAN nullable (None se assente)."""
    if value is None:
        return None
    return _to_bool(value)


def _to_optional_str(value: object) -> str | None:
    """Normalizza a VARCHAR nullable preservando None/""/valori speciali."""
    if value is None:
        return None
    return str(value)


def _to_required_str(value: object) -> str:
    """Normalizza a VARCHAR non-null."""
    if value is None:
        return ""
    return str(value)


def _to_json(value: object) -> object | None:
    """Mantiene il valore come JSON (media, media_embed)."""
    return value


def _pick(raw: dict[str, Any], *names: str, default: object = None) -> object:
    """Restituisce il primo campo presente e non-None tra i nomi dati."""
    for name in names:
        value = raw.get(name)
        if value is not None:
            return value
    return default


def _build_record(
    raw: dict[str, Any], fields: list[tuple[str, Callable[[object], object]]]
) -> dict[str, object]:
    """Costruisce il dict di destinazione applicando i normalizzatori."""
    return {name: normalizer(raw.get(name)) for name, normalizer in fields}


_COMMENT_FIELDS: list[tuple[str, Callable[[object], object]]] = [
    ("id", _to_required_str),
    ("name", _to_required_str),
    ("subreddit", _to_required_str),
    ("subreddit_id", _to_required_str),
    ("author", _to_required_str),
    ("author_flair_css_class", _to_optional_str),
    ("author_flair_text", _to_optional_str),
    ("body", _to_required_str),
    ("parent_id", _to_required_str),
    ("link_id", _to_required_str),
    ("created_utc", _to_required_int),
    ("retrieved_on", _to_required_int),
    ("ups", _to_required_int),
    ("downs", _to_required_int),
    ("score", _to_required_int),
    ("gilded", _to_required_int),
    ("controversiality", _to_required_int),
    ("score_hidden", _to_bool),
    ("archived", _to_bool),
    ("edited", _to_bool),
    ("distinguished", _to_optional_str),
]


def parse_comment(raw: dict[str, Any]) -> dict[str, object]:
    """Normalizza un record di commento nei campi della tabella comments."""
    return _build_record(raw, _COMMENT_FIELDS)


_SUBMISSION_FIELDS: list[tuple[str, Callable[[object], object]]] = [
    ("id", _to_required_str),
    ("name", _to_required_str),
    ("subreddit", _to_required_str),
    ("subreddit_id", _to_required_str),
    ("author", _to_required_str),
    ("author_flair_css_class", _to_optional_str),
    ("author_flair_text", _to_optional_str),
    ("title", _to_required_str),
    ("selftext", _to_required_str),
    ("selftext_html", _to_optional_str),
    ("url", _to_required_str),
    ("permalink", _to_required_str),
    ("domain", _to_required_str),
    ("is_self", _to_bool),
    ("over_18", _to_bool),
    ("hidden", _to_bool),
    ("clicked", _to_bool),
    ("saved", _to_bool),
    ("ups", _to_required_int),
    ("downs", _to_required_int),
    ("score", _to_required_int),
    ("num_comments", _to_required_int),
    ("num_reports", _to_optional_int),
    ("likes", _to_nullable_bool),
    ("created", _to_required_int),
    ("created_utc", _to_required_int),
    ("edited", _to_bool),
    ("distinguished", _to_optional_str),
    ("link_flair_css_class", _to_optional_str),
    ("link_flair_text", _to_optional_str),
    ("thumbnail", _to_required_str),
    ("media", _to_json),
    ("media_embed", _to_json),
    ("approved_by", _to_optional_str),
    ("banned_by", _to_optional_str),
    ("promoted", _to_nullable_bool),
]


def parse_submission(raw: dict[str, Any]) -> dict[str, object]:
    """Normalizza un record di submission nei campi della tabella submissions."""
    return _build_record(raw, _SUBMISSION_FIELDS)
