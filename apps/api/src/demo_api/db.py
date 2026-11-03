from collections.abc import Iterator
from contextlib import contextmanager

import psycopg
from psycopg.rows import dict_row

from demo_api.settings import Settings


SCHEMA = """
CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY,
    request_id UUID NOT NULL UNIQUE,
    body VARCHAR(200) NOT NULL CHECK (length(trim(body)) > 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS messages_created_at_idx
    ON messages (created_at DESC, id DESC);
"""


@contextmanager
def connection(settings: Settings) -> Iterator[psycopg.Connection]:
    with psycopg.connect(
        host=settings.db_host,
        port=settings.db_port,
        dbname=settings.db_name,
        user=settings.db_user,
        password=settings.db_password,
        connect_timeout=3,
        row_factory=dict_row,
    ) as conn:
        yield conn


def ensure_schema(settings: Settings) -> None:
    with connection(settings) as conn:
        conn.execute(SCHEMA)
