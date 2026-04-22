import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class KafkaConfig:
	kafka_brokers: str
	retrain_topic: str
	starting_offsets: str


@dataclass(frozen=True)
class ListenerConfig:
	checkpoint_path: str
	trigger_interval_seconds: int


@dataclass(frozen=True)
class ModelConfig:
	k: int
	decay_factor: float
	model_path: str


@dataclass(frozen=True)
class DatabaseConfig:
	host: str
	port: int
	dbname: str
	user: str
	password: str
	table: str


@dataclass(frozen=True)
class AppConfig:
	kafka: KafkaConfig
	listener: ListenerConfig
	model: ModelConfig
	database: DatabaseConfig


def load_app_config() -> AppConfig:
	return AppConfig(
		kafka=KafkaConfig(
			kafka_brokers=os.getenv("KAFKA_BROKERS", "kafka:9092"),
			retrain_topic=os.getenv("ML_RETRAIN_TOPIC", "ml-retrain-trigger"),
			starting_offsets=os.getenv("ML_RETRAIN_STARTING_OFFSETS", "latest"),
		),
		listener=ListenerConfig(
			checkpoint_path=os.getenv(
				"ML_LISTENER_CHECKPOINT_PATH",
				"/app/data/checkpoint/ml-listener",
			),
			trigger_interval_seconds=int(os.getenv("ML_LISTENER_TRIGGER_SECONDS", "15")),
		),
		model=ModelConfig(
			k=int(os.getenv("ML_KMEANS_K", "5")),
			decay_factor=float(os.getenv("ML_KMEANS_DECAY_FACTOR", "0.5")),
			model_path=os.getenv(
				"ML_MODEL_PATH",
				"/app/data/models",
			),
		),
		database=DatabaseConfig(
			host=os.getenv("POSTGRES_HOST", "db"),
			port=int(os.getenv("POSTGRES_PORT", "5432")),
			dbname=os.getenv("POSTGRES_DB", "wikipedia"),
			user=os.getenv("POSTGRES_USER", "superset"),
			password=os.getenv("POSTGRES_PASSWORD", "superset_pass"),
			table=os.getenv("ML_SOURCE_TABLE", "wikipedia_changes"),
		),
	)


# Compatibility constants for db.connection module.
DB_HOST = os.getenv("POSTGRES_HOST", "db")
DB_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
DB_NAME = os.getenv("POSTGRES_DB", "wikipedia")
DB_USER = os.getenv("POSTGRES_USER", "superset")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "superset_pass")
