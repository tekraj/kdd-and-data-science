import time

import psycopg2

from config import DB_HOST, DB_NAME, DB_PASSWORD, DB_PORT, DB_USER

_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS wikipedia_changes (
    id              INTEGER,
    type            TEXT,
    title           TEXT,
    timestamp       DOUBLE PRECISION,
    "user"          TEXT,
    bot             BOOLEAN,
    meta_uri        TEXT,
    meta_request_id TEXT,
    meta_id         TEXT,
    meta_dt         TEXT,
    meta_domain     TEXT,
    meta_stream     TEXT,
    wiki            TEXT,
    event_time      TIMESTAMP
);
"""


def get_connection() -> psycopg2.extensions.connection:
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
    )


def ensure_table_exists(max_retries: int = 12, retry_delay: int = 5) -> None:
    """Create wikipedia_changes table if it does not exist, with retries."""
    for attempt in range(1, max_retries + 1):
        try:
            conn = get_connection()
            with conn:
                with conn.cursor() as cur:
                    cur.execute(_CREATE_TABLE_SQL)
            conn.close()
            print("PostgreSQL table ready.")
            return
        except Exception as e:
            if attempt == max_retries:
                raise
            print(
                f"DB connection attempt {attempt}/{max_retries} failed: {e}. "
                f"Retrying in {retry_delay}s..."
            )
            time.sleep(retry_delay)
