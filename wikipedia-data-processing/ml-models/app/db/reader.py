import psycopg2
from pyspark.sql import DataFrame, SparkSession

from config import DatabaseConfig


def get_wikipedia_id_bounds(db_config: DatabaseConfig) -> tuple[int, int] | None:
    """Return min/max id available for training, or None when table is empty."""
    conn = psycopg2.connect(
        host=db_config.host,
        port=db_config.port,
        dbname=db_config.dbname,
        user=db_config.user,
        password=db_config.password,
    )
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT MIN(id), MAX(id) FROM {db_config.table} WHERE id IS NOT NULL"
            )
            min_id, max_id = cur.fetchone()
    finally:
        conn.close()

    if min_id is None or max_id is None:
        return None
    return int(min_id), int(max_id)


def read_wikipedia_window(
    spark: SparkSession,
    db_config: DatabaseConfig,
    first_id: int,
    last_id: int,
) -> DataFrame:
    """Read wikipedia change rows for an id range via psycopg2."""
    conn = psycopg2.connect(
        host=db_config.host,
        port=db_config.port,
        dbname=db_config.dbname,
        user=db_config.user,
        password=db_config.password,
    )
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT id, type, wiki, bot FROM {db_config.table}"
                " WHERE id BETWEEN %s AND %s",
                (int(first_id), int(last_id)),
            )
            rows = cur.fetchall()
    finally:
        conn.close()

    return spark.createDataFrame(rows, ["id", "type", "wiki", "bot"])
