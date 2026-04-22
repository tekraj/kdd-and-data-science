# Wikipedia Real-Time Data Processing and ML Insights

This project builds a real-time data platform on top of Wikimedia recent changes.
It captures live edit events, processes them in streaming mode, stores curated data in PostgreSQL, and serves machine-learning insights through APIs and Grafana.

## 1. Introduction

The system is designed as a layered, production-style streaming architecture:

- Ingestion layer: Node.js service reads Wikimedia Server-Sent Events (SSE) and publishes JSON events to Kafka.
- Processing layer: PySpark Structured Streaming consumes Kafka, applies preprocessing, and writes cleaned rows to PostgreSQL.
- ML layer: Spark-based incremental training jobs update clustering and TF-IDF topic artifacts from processed data.
- Serving and visualization layer: FastAPI serves ML insights; Grafana visualizes SQL and API-backed dashboards.

Core stack:

- Data ingestion: Node.js + TypeScript + KafkaJS
- Stream processing: PySpark Structured Streaming
- Messaging: Apache Kafka + ZooKeeper
- Storage: PostgreSQL
- ML services: Spark MLlib + FastAPI
- Dashboards: Grafana

## 2. End-to-End Pipeline

1. Wikimedia emits edit events on SSE endpoint `https://stream.wikimedia.org/v2/stream/recentchange`.
2. `app` (ingestion service) receives each message, parses JSON, and publishes to Kafka topic `wikipedia-stream`.
3. `stream-processor` reads `wikipedia-stream`, parses schema, deduplicates records, preprocesses fields, and writes micro-batches to `wikipedia_changes` table.
4. After successful DB writes, `stream-processor` publishes retrain triggers (ID windows) to `ml-retrain-trigger`.
5. ML listener consumes retrain events and incrementally retrains:
   - Streaming KMeans model for editor/event behavior clusters.
   - TF-IDF model for trending topic extraction from page titles.
6. `ml-insights-api` exposes artifacts via HTTP endpoints.
7. Grafana reads from PostgreSQL (and optionally Infinity datasource for API endpoints) for operational and analytical dashboards.

## 3. Service Architecture

Defined in [docker-compose.yml](docker-compose.yml):

- `zookeeper`: Kafka coordination
- `kafka`: message broker (`29092` host port)
- `app`: Node ingestion producer (SSE -> Kafka)
- `stream-processor`: Spark stream consumer/processor (Kafka -> Postgres + retrain events)
- `db`: PostgreSQL 15 (`5432`)
- `ml-insights-api`: FastAPI service (`8000`) + embedded retrain listener thread
- `ml-trainer-service` (optional profile `listener-only`): listener-only Spark consumer for retraining
- `grafana`: dashboards (`3001`)

Persisted bind-mounted data directories:

- `data/postgres`
- `data/checkpoint`
- `data/models`
- `data/grafana`

## 4. Ingestion Layer Details

Source code: [data-ingestion/src](data-ingestion/src)

Main behavior:

- Startup connects a Kafka producer and starts an SSE listener.
- Listener subscribes to Wikimedia recent changes SSE stream.
- Each `message` event payload is parsed and forwarded to Kafka.
- Logging tracks connection state and processed event counts (`LOG_EVERY_N_EVENTS`).
- Graceful shutdown handles `SIGINT` and `SIGTERM`.

Important implementation notes:

- Kafka brokers are configured through `KAFKA_BROKERS`.
- SSE endpoint is configured through `WIKIPEDIA_SSE_URL`.
- Events are published as JSON strings to topic `wikipedia-stream`.
- Event schema includes fields like `id`, `type`, `title`, `timestamp`, `user`, `bot`, `wiki`, and nested `meta`.

## 5. Streaming Processing Layer

Source code: [stream-processor/app](stream-processor/app)

### 5.1 Read from Kafka

- Uses Spark Structured Streaming Kafka source.
- Key runtime options:
  - `KAFKA_STARTING_OFFSETS` (default `latest`)
  - `KAFKA_FAIL_ON_DATA_LOSS` (default `false`)
  - optional `KAFKA_MAX_OFFSETS_PER_TRIGGER`
- Supports checkpoint reset via `RESET_CHECKPOINT_ON_START=true` when recovery from stale offsets is needed.

### 5.2 Transform and preprocess

Pipeline steps:

1. Parse Kafka `value` as JSON using explicit schema.
2. Project event fields and create `event_time` from epoch `timestamp`.
3. Apply watermark (`10 minutes`) and deduplicate by `id` + `event_time`.
4. Preprocess records:
   - Validate required columns.
   - Drop rows missing `id` or `timestamp`.
   - Normalize text fields (`type`, `title`, `user`, `wiki`): trim and map empty strings to null.
   - Lowercase `wiki`.
   - Fill defaults (`unknown`, `untitled`, `bot=false`).
   - Flatten nested `meta` into `meta_*` columns.

### 5.3 Save to PostgreSQL

- Ensures `wikipedia_changes` table exists at startup.
- Writes micro-batches through `foreachBatch` and bulk insert (`execute_values`).
- Uses checkpoint location `CHECKPOINT_PATH` to track streaming state.

### 5.4 Emit retrain triggers

After each successful DB batch write:

- Extracts inserted IDs from batch.
- Publishes retrain trigger events to `ML_RETRAIN_TOPIC` (`ml-retrain-trigger`).
- Publishes based on `ML_RETRAIN_BATCH_FREQUENCY` to avoid retraining on every tiny batch.

## 6. ML Model Services

Source code: [ml-models/app](ml-models/app)

The ML layer supports two execution modes:

- `ml-insights-api`: serves HTTP endpoints and runs retrain listener on startup.
- `ml-trainer-service`: dedicated listener worker (when `listener-only` profile is enabled).

### 6.1 Retrain listener workflow

Listener logic ([ml-models/app/spark/listener_runner.py](ml-models/app/spark/listener_runner.py)):

1. Load app config (Kafka, DB, model, checkpoint).
2. Create Spark session.
3. Bootstrap models if artifacts do not exist:
   - Streaming KMeans model
   - TF-IDF trending topics model
4. Subscribe to retrain topic using `subscribePattern` to tolerate late topic creation.
5. For each micro-batch event payload:
   - Parse event window `(first_id, last_id)`.
   - Retrain KMeans on that DB ID window.
   - Retrain TF-IDF topics on that DB ID window.

### 6.2 Clustering model (Streaming KMeans)

Module: [ml-models/app/clustering/streaming_kmeans.py](ml-models/app/clustering/streaming_kmeans.py)

- Reads `(id, type, wiki, bot)` window from PostgreSQL.
- Feature engineering:
  - normalize `wiki`, `type`
  - handle null/empty values
  - `StringIndexer` + `OneHotEncoder`
  - append numeric `bot` feature
- Initializes model with batch KMeans if absent.
- Incrementally updates centers via `StreamingKMeansModel.update` using decay factor.
- Persists artifacts:
  - model directory: `data/models/streaming_kmeans`
  - metadata JSON: `data/models/streaming_kmeans_metadata.json`

### 6.3 TF-IDF trending topics model

Module: [ml-models/app/classification/tf_idf.py](ml-models/app/classification/tf_idf.py)

- Reads `title` values from PostgreSQL by ID window.
- Tokenizes text with stop-word removal and bigram expansion.
- Computes mean TF-IDF style ranking per term.
- Produces top topics with:
  - `topic`
  - `mentions`
  - `score`
  - trend signal vs previous artifact (`new`, `up`, `down`, `stable`)
- Stores artifact at `data/models/tfidf_trending_topics.json`.

### 6.4 API endpoints

Module: [ml-models/app/main.py](ml-models/app/main.py)

- `GET /power-editors`: mapped, dashboard-friendly cluster insights.
- `GET /power-editors/raw`: raw clustering artifact view.
- `GET /trending-topics`: TF-IDF trending topics artifact.

These endpoints are designed for direct use by Grafana Infinity datasource or other internal consumers.

## 7. Data Model

Primary table: `wikipedia_changes`

Columns written by stream processor include:

- `id`, `type`, `title`, `timestamp`, `user`, `bot`, `wiki`, `event_time`
- flattened metadata: `meta_uri`, `meta_request_id`, `meta_id`, `meta_dt`, `meta_domain`, `meta_stream`

## 8. Observability and Dashboards

Grafana is configured in the compose stack and exposed on `http://localhost:3001`.
Typical dashboards include:

- real-time edit throughput
- top pages and top users
- wiki activity distribution
- bot vs human edits
- ML-based cluster and topic insights

For full installation, startup, and dashboard setup instructions, see [SETUP.md](SETUP.md).

## 9. Project Structure

- [data-ingestion](data-ingestion): SSE consumer and Kafka producer
- [stream-processor](stream-processor): Spark streaming ETL and PostgreSQL writer
- [ml-models](ml-models): retraining listeners, clustering, TF-IDF, API serving
- [documents](documents): project notes and step-by-step writeups
- [data](data): bind-mounted runtime data (checkpoint, models, postgres, grafana)

## 10. Setup

Setup instructions were intentionally separated to keep this file architecture-focused.

Read [SETUP.md](SETUP.md) for:

- prerequisites
- environment configuration
- directory initialization
- build and run commands
- health checks
- Grafana datasource and dashboard setup
- troubleshooting and reset operations
