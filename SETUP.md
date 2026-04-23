# Setup Guide: Wikipedia Real-Time Data Processing

This document contains detailed, step-by-step setup and operations instructions for running the project locally.

For architecture and layer internals, see [readme.md](readme.md).

## 1. Prerequisites

Install the following:

- Docker Engine + Docker Compose
- Git
- VS Code (recommended)

Linux example:

```bash
sudo apt-get update
sudo apt-get install -y docker.io docker-compose-plugin
sudo systemctl enable --now docker
sudo usermod -aG docker $USER
```

After adding your user to the docker group, log out and back in.

Verify:

```bash
docker --version
docker compose version
```

## 2. Clone and Enter Project

```bash
git clone https://github.com/tekraj/kdd-and-data-science.git
cd kdd-and-data-science/wikipedia-data-processing
```

## 3. Create Local Data Directories

These paths are bind-mounted by Docker volumes:

```bash
mkdir -p data/checkpoint data/csv data/duckdb data/grafana data/postgres data/models
```

## 4. Configure Environment Variables

Create `.env` from example:

```bash
cp .env.example .env
```

Important defaults:

```dotenv
NODE_ENV=production
KAFKA_BROKERS=kafka:9092
WIKIPEDIA_SSE_URL=https://stream.wikimedia.org/v2/stream/recentchange
KAFKA_TOPIC=wikipedia-stream
CHECKPOINT_PATH=/app/data/checkpoint
KAFKA_STARTING_OFFSETS=latest
KAFKA_FAIL_ON_DATA_LOSS=false

POSTGRES_HOST=db
POSTGRES_PORT=5432
POSTGRES_DB=wikipedia
POSTGRES_USER=superset
POSTGRES_PASSWORD=superset_pass
```

Optional tuning values:

```dotenv
# stream-processor
KAFKA_MAX_OFFSETS_PER_TRIGGER=1000
RESET_CHECKPOINT_ON_START=false
ML_RETRAIN_TOPIC=ml-retrain-trigger
ML_RETRAIN_BATCH_FREQUENCY=100

# ml-models listener
ML_RETRAIN_STARTING_OFFSETS=latest
ML_LISTENER_CHECKPOINT_PATH=/app/data/checkpoint/ml-listener
ML_LISTENER_TRIGGER_SECONDS=15
ML_KMEANS_K=5
ML_KMEANS_DECAY_FACTOR=0.5
ML_MODEL_PATH=/app/data/models
ML_SOURCE_TABLE=wikipedia_changes
```

## 5. Build Images

```bash
docker compose build
```

This builds:

- data ingestion image
- stream processor image
- ml-models image (for API and optional trainer)

## 6. Start the Stack

Foreground mode:

```bash
docker compose up
```

Background mode:

```bash
docker compose up -d
```

Default startup path brings up:

- zookeeper
- kafka
- db
- app (ingestion)
- stream-processor
- ml-insights-api
- grafana

Optional listener-only service is profile-gated:

```bash
docker compose --profile listener-only up -d ml-trainer-service
```

## 7. Validate Services

Check containers:

```bash
docker compose ps
```

Check logs:

```bash
docker compose logs app

docker compose logs stream-processor

docker compose logs ml-insights-api
```

Quick health checks:

- Grafana: `http://localhost:3001` (admin/admin)
- ML API: `http://localhost:8000/docs`
- PostgreSQL port exposed at `localhost:5432`
- Kafka external listener at `localhost:29092`

## 8. Verify Data Flow

1. Confirm ingestion logs show SSE connection and published events.
2. Confirm stream processor logs show micro-batch inserts.
3. Confirm rows exist in PostgreSQL:

```bash
docker exec -it wikipedia_db psql -U superset -d wikipedia -c "SELECT COUNT(*) FROM wikipedia_changes;"
```

4. Confirm ML artifacts are created:

```bash
ls -lah data/models
```

Expected artifacts include:

- `streaming_kmeans/`
- `streaming_kmeans_metadata.json`
- `tfidf_trending_topics.json`

## 9. Configure Grafana

Open `http://localhost:3001` and log in:

- Username: `admin`
- Password: `admin`

Add PostgreSQL datasource:

- Host: `db:5432`
- Database: `wikipedia`
- User: `superset`
- Password: `superset_pass`
- SSL mode: disable

Optional: Add Infinity datasource to call ML endpoints:

- Base URL examples:
  - `http://ml-insights-api:8000/power-editors`
  - `http://ml-insights-api:8000/trending-topics`

## 10. Common Operations

Restart a single service:

```bash
docker compose restart stream-processor
```

View latest logs continuously:

```bash
docker compose logs -f stream-processor
```

Stop all services:

```bash
docker compose down
```

Stop and remove volumes:

```bash
docker compose down -v
```

## 11. Troubleshooting

`stream-processor` exits early:

- Kafka or DB may not be ready yet.
- Run:

```bash
docker compose logs stream-processor
docker compose restart stream-processor
```

No rows in PostgreSQL:

- Check ingestion service logs.
- Verify `.env` has `KAFKA_BROKERS=kafka:9092`.
- Ensure `KAFKA_TOPIC` matches producer/consumer topic.

Kafka offset/data loss errors:

- Keep `KAFKA_FAIL_ON_DATA_LOSS=false` for resilience.
- If checkpoint is stale, one-time reset:

```bash
rm -rf data/checkpoint/*
```

Then restart stack.

ML endpoints return model-not-found:

- Wait for enough data to trigger retraining.
- Check ML listener logs in `ml-insights-api` service.
- Confirm retrain topic and checkpoint env variables.

Port conflicts (`3001`, `5432`, `8000`, `29092`):

- Stop conflicting local services or update host port mappings in [docker-compose.yml](docker-compose.yml).

## 12. Recommended First-Run Sequence

1. `docker compose build`
2. `docker compose up -d`
3. Wait 2-3 minutes
4. Validate with `docker compose ps` and logs
5. Open Grafana and configure datasource
6. Query ML API docs on `http://localhost:8000/docs`
7. Build dashboards and monitor real-time behavior
