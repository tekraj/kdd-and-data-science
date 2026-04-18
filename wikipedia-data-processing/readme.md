2. The Architecture Flow
Ingestion: A Node.js app listens to Wikipedia SSE and pushes to Redis Streams.

Batching: A local worker (Node/Python) reads from Redis and writes "raw" CSVs to MinIO (Local S3).

Transformation (ETL): Apache Spark reads the raw CSVs, cleans the data (reformatting dates, filtering bots), and writes "clean" Parquet files back to MinIO.

Querying: DuckDB acts as your local "Athena." It can read files directly from your disk or MinIO using standard SQL.

Visualization: Metabase connects to DuckDB or your transformed files to show live charts.