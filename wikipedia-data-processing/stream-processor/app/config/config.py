import os
from dotenv import load_dotenv

load_dotenv()

KAFKA_BROKERS = os.getenv("KAFKA_BROKERS", "kafka:9092")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "wikipedia-stream")
ML_RETRAIN_TOPIC = os.getenv("ML_RETRAIN_TOPIC", "ml-retrain-trigger")
ML_RETRAIN_BATCH_FREQUENCY = int(os.getenv("ML_RETRAIN_BATCH_FREQUENCY", "100"))
CHECKPOINT_PATH = os.getenv("CHECKPOINT_PATH", "/app/data/checkpoint")


def _env_bool(name: str, default: bool) -> bool:
	raw = os.getenv(name)
	if raw is None:
		return default
	return raw.strip().lower() in {"1", "true", "yes", "on"}


# Kafka / Spark streaming behavior
KAFKA_STARTING_OFFSETS = os.getenv("KAFKA_STARTING_OFFSETS", "latest")
KAFKA_FAIL_ON_DATA_LOSS = _env_bool("KAFKA_FAIL_ON_DATA_LOSS", False)
KAFKA_MAX_OFFSETS_PER_TRIGGER = os.getenv("KAFKA_MAX_OFFSETS_PER_TRIGGER")

# If enabled, clears Spark checkpoint directory at process startup.
# Use only when you intentionally want to restart consumption state.
RESET_CHECKPOINT_ON_START = _env_bool("RESET_CHECKPOINT_ON_START", False)

# PostgreSQL
DB_HOST = os.getenv("POSTGRES_HOST", "db")
DB_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
DB_NAME = os.getenv("POSTGRES_DB", "wikipedia")
DB_USER = os.getenv("POSTGRES_USER", "superset")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "superset_pass")
