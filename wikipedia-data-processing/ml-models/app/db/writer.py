from psycopg2.extras import execute_values

from db.connection import get_connection

_INSERT_SQL = """
INSERT INTO wikipedia_changes (
    id, type, title, timestamp, "user", bot,
    meta_uri, meta_request_id, meta_id, meta_dt, meta_domain, meta_stream,
    wiki, event_time
) VALUES %s
"""


def write_batch_to_postgres(batch_df) -> dict:
    """Collect a Spark micro-batch DataFrame, bulk-insert rows, and return inserted ids."""
    rows = batch_df.collect()
    if not rows:
        return {"count": 0, "ids": []}

    records = [
        (
            row["id"],
            row["type"],
            row["title"],
            row["timestamp"],
            row["user"],
            row["bot"],
            row["meta_uri"],
            row["meta_request_id"],
            row["meta_id"],
            row["meta_dt"],
            row["meta_domain"],
            row["meta_stream"],
            row["wiki"],
            row["event_time"],
        )
        for row in rows
    ]

    conn = get_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                execute_values(cur, _INSERT_SQL, records)
        print(f"[Postgres] Inserted {len(records)} rows.")
        inserted_ids = [row["id"] for row in rows if row["id"] is not None]
        return {"count": len(records), "ids": inserted_ids}
    finally:
        conn.close()
