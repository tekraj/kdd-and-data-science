import os
from dotenv import load_dotenv

load_dotenv()

KAFKA_BROKERS = os.getenv("KAFKA_BROKERS", "kafka:9092")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "wikipedia-stream")
OUTPUT_PATH = os.getenv("OUTPUT_PATH", "/app/data/csv")
CHECKPOINT_PATH = os.getenv("CHECKPOINT_PATH", "/app/data/checkpoint")
