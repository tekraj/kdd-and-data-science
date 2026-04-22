import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pyspark.sql import SparkSession


@dataclass
class RetrainBatchState:
    batch_frequency: int
    pending_batch_count: int = 0
    window_first_id: int | None = None
    window_last_id: int | None = None


class RetrainModelPublisher:
    """Publishes ML retrain window events to Kafka via Spark."""

    def __init__(
        self,
        spark: SparkSession,
        kafka_brokers: str,
        topic: str,
        batch_frequency: int,
    ) -> None:
        if batch_frequency <= 0:
            raise ValueError("ML_RETRAIN_BATCH_FREQUENCY must be greater than 0")

        self._spark = spark
        self._kafka_brokers = kafka_brokers
        self._topic = topic
        self._state = RetrainBatchState(batch_frequency=batch_frequency)

    def publish_if_ready(self, inserted_ids: list[int]) -> None:
        if not inserted_ids:
            return

        if self._state.window_first_id is None:
            self._state.window_first_id = inserted_ids[0]
        self._state.window_last_id = inserted_ids[-1]
        self._state.pending_batch_count += 1

        if (
            self._state.pending_batch_count >= self._state.batch_frequency
            and self._state.window_first_id is not None
            and self._state.window_last_id is not None
        ):
            self._publish_event(
                first_id=self._state.window_first_id,
                last_id=self._state.window_last_id,
                batch_count=self._state.pending_batch_count,
            )
            self._state.pending_batch_count = 0
            self._state.window_first_id = None
            self._state.window_last_id = None

    def _publish_event(
        self,
        first_id: int,
        last_id: int,
        batch_count: int,
    ) -> None:
        try:
            payload = {
                "first_id": int(first_id),
                "last_id": int(last_id),
                "batch_count": int(batch_count),
                "published_at": datetime.now(timezone.utc).isoformat(),
                "event_type": "RETRAIN_CHECK",
            }

            event_json = json.dumps(payload)
            (
                self._spark.createDataFrame([(event_json,)], ["value"])
                .selectExpr("CAST(value AS STRING)")
                .write
                .format("kafka")
                .option("kafka.bootstrap.servers", self._kafka_brokers)
                .option("topic", self._topic)
                .save()
            )
            print(
                "[KAFKA] Sent retrain trigger "
                f"first_id={first_id}, last_id={last_id}, batch_count={batch_count}"
            )
        except Exception as e:
            print(f"[KAFKA] Failed to publish retrain event: {e}")

        
