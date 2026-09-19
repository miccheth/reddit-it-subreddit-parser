"""Caricamento e normalizzazione della whitelist dei subreddit."""

from __future__ import annotations

import json
from pathlib import Path


class SubRedditList:
    """Whitelist dei subreddit italiani con supporto alla membership O(1)."""

    def __init__(self, subreddits: set[str]) -> None:
        self._subreddits = subreddits

    @classmethod
    def from_file(cls, path: Path) -> SubRedditList:
        """Carica la whitelist da un file JSON contenente un array di nomi."""
        with path.open("r", encoding="utf-8") as file:
            raw = json.load(file)

        if not isinstance(raw, list):
            raise ValueError(f"Whitelist non valida in {path}: atteso un array")

        names = {cls.normalize(name) for name in raw}
        return cls(names)

    @staticmethod
    def normalize(subreddit: object) -> str:
        """Normalizza il nome di un subreddit (lowercase e strip)."""
        if not isinstance(subreddit, str):
            raise TypeError(f"Subreddit non valido: {subreddit!r}")
        return subreddit.strip().lower()

    def contains(self, subreddit: object) -> bool:
        """Verifica se il subreddit appartiene alla whitelist."""
        try:
            normalized = self.normalize(subreddit)
        except TypeError:
            return False
        return normalized in self._subreddits

    def __len__(self) -> int:
        return len(self._subreddits)
