"""Persistenza DuckDB: schema, stato file, transazioni e recovery."""

from __future__ import annotations

from pathlib import Path

import duckdb
from typing_extensions import Self

_SCHEMA = """
CREATE TABLE IF NOT EXISTS submissions (
    id                     VARCHAR NOT NULL,
    name                   VARCHAR NOT NULL,
    subreddit              VARCHAR NOT NULL,
    subreddit_id           VARCHAR NOT NULL,
    author                 VARCHAR NOT NULL,
    author_flair_css_class VARCHAR,
    author_flair_text      VARCHAR,
    title                  VARCHAR NOT NULL,
    selftext               VARCHAR NOT NULL,
    selftext_html          VARCHAR,
    url                    VARCHAR NOT NULL,
    permalink              VARCHAR NOT NULL,
    domain                 VARCHAR NOT NULL,
    is_self                BOOLEAN NOT NULL,
    over_18                BOOLEAN NOT NULL,
    hidden                 BOOLEAN NOT NULL,
    clicked                BOOLEAN NOT NULL,
    saved                  BOOLEAN NOT NULL,
    ups                    BIGINT NOT NULL,
    downs                  BIGINT NOT NULL,
    score                  BIGINT NOT NULL,
    num_comments           BIGINT NOT NULL,
    num_reports            BIGINT,
    likes                  BOOLEAN,
    created                BIGINT NOT NULL,
    created_utc            BIGINT NOT NULL,
    edited                 BOOLEAN NOT NULL,
    distinguished          VARCHAR,
    link_flair_css_class   VARCHAR,
    link_flair_text        VARCHAR,
    thumbnail              VARCHAR NOT NULL,
    media                  JSON,
    media_embed            JSON,
    approved_by            VARCHAR,
    banned_by              VARCHAR,
    promoted               BOOLEAN
);

CREATE TABLE IF NOT EXISTS comments (
    id                     VARCHAR NOT NULL,
    name                   VARCHAR NOT NULL,
    subreddit              VARCHAR NOT NULL,
    subreddit_id           VARCHAR NOT NULL,
    author                 VARCHAR NOT NULL,
    author_flair_css_class VARCHAR,
    author_flair_text      VARCHAR,
    body                   VARCHAR NOT NULL,
    parent_id              VARCHAR NOT NULL,
    link_id                VARCHAR NOT NULL,
    created_utc            BIGINT NOT NULL,
    retrieved_on           BIGINT NOT NULL,
    ups                    BIGINT NOT NULL,
    downs                  BIGINT NOT NULL,
    score                  BIGINT NOT NULL,
    gilded                 BIGINT NOT NULL,
    controversiality       BIGINT NOT NULL,
    score_hidden           BOOLEAN NOT NULL,
    archived               BOOLEAN NOT NULL,
    edited                 BOOLEAN NOT NULL,
    distinguished          VARCHAR
);

CREATE TABLE IF NOT EXISTS file_states (
    file_path   VARCHAR PRIMARY KEY,
    state       VARCHAR NOT NULL,
    processed   BIGINT NOT NULL DEFAULT 0
);
"""


class FileState:
    """Stato persistito di un file dump nel ciclo di vita della pipeline."""

    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    FAILED = "FAILED"
    COMPLETED = "COMPLETED"


_COMMENT_COLUMNS = (
    "id",
    "name",
    "subreddit",
    "subreddit_id",
    "author",
    "author_flair_css_class",
    "author_flair_text",
    "body",
    "parent_id",
    "link_id",
    "created_utc",
    "retrieved_on",
    "ups",
    "downs",
    "score",
    "gilded",
    "controversiality",
    "score_hidden",
    "archived",
    "edited",
    "distinguished",
)

_SUBMISSION_COLUMNS = (
    "id",
    "name",
    "subreddit",
    "subreddit_id",
    "author",
    "author_flair_css_class",
    "author_flair_text",
    "title",
    "selftext",
    "selftext_html",
    "url",
    "permalink",
    "domain",
    "is_self",
    "over_18",
    "hidden",
    "clicked",
    "saved",
    "ups",
    "downs",
    "score",
    "num_comments",
    "num_reports",
    "likes",
    "created",
    "created_utc",
    "edited",
    "distinguished",
    "link_flair_css_class",
    "link_flair_text",
    "thumbnail",
    "media",
    "media_embed",
    "approved_by",
    "banned_by",
    "promoted",
)


class DuckDBStore:
    """Wraper sullo storage DuckDB della pipeline."""

    def __init__(self, path: Path) -> None:
        self._conn = duckdb.connect(str(path))
        self._conn.execute(_SCHEMA)

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    @staticmethod
    def _placeholders(count: int) -> str:
        return ", ".join("?" for _ in range(count))

    def _insert_many(
        self, table: str, columns: tuple[str, ...], records: list[dict[str, object]]
    ) -> None:
        if not records:
            return
        col_list = ", ".join(columns)
        placeholders = self._placeholders(len(columns))
        self._conn.executemany(
            f"INSERT INTO {table} ({col_list}) VALUES ({placeholders})",
            [[record[col] for col in columns] for record in records],
        )

    def insert_comments(self, records: list[dict[str, object]]) -> None:
        self._insert_many("comments", _COMMENT_COLUMNS, records)

    def insert_submissions(self, records: list[dict[str, object]]) -> None:
        self._insert_many("submissions", _SUBMISSION_COLUMNS, records)

    def get_file_state(self, file_path: str) -> str | None:
        row = self._conn.execute(
            "SELECT state FROM file_states WHERE file_path = ?", [file_path]
        ).fetchone()
        if row is None:
            return None
        return str(row[0])

    def begin_processing(self, file_path: str) -> None:
        self._conn.execute(
            """
            INSERT INTO file_states (file_path, state, processed)
            VALUES (?, ?, 0)
            ON CONFLICT (file_path) DO UPDATE SET state = ?
            """,
            [file_path, FileState.PROCESSING, FileState.PROCESSING],
        )

    def mark_completed(self, file_path: str) -> None:
        self._conn.execute(
            "UPDATE file_states SET state = ? WHERE file_path = ?",
            [FileState.COMPLETED, file_path],
        )

    def mark_failed(self, file_path: str) -> None:
        self._conn.execute(
            "UPDATE file_states SET state = ? WHERE file_path = ?",
            [FileState.FAILED, file_path],
        )

    def begin(self) -> None:
        self._conn.execute("BEGIN TRANSACTION")

    def commit(self) -> None:
        self._conn.execute("COMMIT")

    def rollback(self) -> None:
        self._conn.execute("ROLLBACK")

    def count_comments(self) -> int:
        row = self._conn.execute("SELECT COUNT(*) FROM comments").fetchone()
        return int(row[0]) if row else 0

    def count_submissions(self) -> int:
        row = self._conn.execute("SELECT COUNT(*) FROM submissions").fetchone()
        return int(row[0]) if row else 0
