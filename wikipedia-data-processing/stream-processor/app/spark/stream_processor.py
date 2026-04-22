from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import col, from_json, from_unixtime, to_timestamp
import os
import shutil
import time

from config.config import (
	CHECKPOINT_PATH,
	KAFKA_BROKERS,
	KAFKA_FAIL_ON_DATA_LOSS,
	KAFKA_MAX_OFFSETS_PER_TRIGGER,
	KAFKA_STARTING_OFFSETS,
	KAFKA_TOPIC,
	ML_RETRAIN_BATCH_FREQUENCY,
	ML_RETRAIN_TOPIC,
	RESET_CHECKPOINT_ON_START,
)
from data_preprocessing import preprocess_wikimedia_events
from db.connection import ensure_table_exists
from db.writer import write_batch_to_postgres
from kafka.producer import RetrainModelPublisher
from spark.schema import wikimedia_schema
from spark.spark import create_spark_session


def _create_kafka_stream(spark: SparkSession, kafka_brokers: str, kafka_topic: str) -> DataFrame:
	stream_reader = (
		spark.readStream.format("kafka")
		.option("kafka.bootstrap.servers", kafka_brokers)
		.option("subscribe", kafka_topic)
		.option("startingOffsets", KAFKA_STARTING_OFFSETS)
		.option("failOnDataLoss", str(KAFKA_FAIL_ON_DATA_LOSS).lower())
	)

	if KAFKA_MAX_OFFSETS_PER_TRIGGER:
		stream_reader = stream_reader.option("maxOffsetsPerTrigger", KAFKA_MAX_OFFSETS_PER_TRIGGER)

	return stream_reader.load()


def _transform_events(raw_stream_df: DataFrame) -> DataFrame:
	json_df = raw_stream_df.select(
		from_json(col("value").cast("string"), wikimedia_schema).alias("data")
	)

	base_df = (
		json_df.select("data.*")
		.withColumn("event_time", to_timestamp(from_unixtime(col("timestamp").cast("long"))))
		.withWatermark("event_time", "10 minutes")
		.dropDuplicates(["id", "event_time"])
	)

	# Apply all cleaning/flattening rules before any sink writes.
	return preprocess_wikimedia_events(base_df)


def process_stream(spark: SparkSession, kafka_brokers: str, kafka_topic: str) -> DataFrame:
	"""Read Kafka stream and return transformed events."""
	print("Initializing Kafka stream processing...")
	try:
		raw_stream_df = _create_kafka_stream(spark, kafka_brokers, kafka_topic)
		print(
			"Successfully read from Kafka stream and parsed JSON. "
			f"startingOffsets={KAFKA_STARTING_OFFSETS}, "
			f"failOnDataLoss={str(KAFKA_FAIL_ON_DATA_LOSS).lower()}"
		)
		return _transform_events(raw_stream_df)
	except Exception as e:
		print(f"An error occurred in process_stream: {e}")
		raise


def _is_kafka_offset_out_of_range_error(err: Exception) -> bool:
	err_text = str(err)
	keywords = [
		"OffsetOutOfRangeException",
		"Cannot fetch offset",
		"Some data may have been lost",
		"failOnDataLoss",
	]
	return any(keyword in err_text for keyword in keywords)


def _reset_checkpoint_if_configured() -> None:
	if RESET_CHECKPOINT_ON_START and os.path.isdir(CHECKPOINT_PATH):
		print(f"RESET_CHECKPOINT_ON_START=true, deleting checkpoint path: {CHECKPOINT_PATH}")
		shutil.rmtree(CHECKPOINT_PATH, ignore_errors=True)


def write_stream(
	spark: SparkSession, df: DataFrame, checkpoint_path: str, trigger_interval: int = 10
) -> None:
	"""Write micro-batches to PostgreSQL and publish retrain trigger events."""
	print("Attempting to write stream to PostgreSQL...")
	try:
		max_attempts = 12
		retry_delay_seconds = 5
		query = None
		retrain_publisher = RetrainModelPublisher(
			spark=spark,
			kafka_brokers=KAFKA_BROKERS,
			topic=ML_RETRAIN_TOPIC,
			batch_frequency=ML_RETRAIN_BATCH_FREQUENCY,
		)

		def process_batch(batch_df: DataFrame, batch_id: int) -> None:
			try:
				write_result = write_batch_to_postgres(batch_df)
				inserted_ids = write_result.get("ids", [])
				retrain_publisher.publish_if_ready(inserted_ids)
			except Exception as db_err:
				print(f"[Batch {batch_id}] PostgreSQL write failed: {db_err}")
				raise

		for attempt in range(1, max_attempts + 1):
			try:
				query = (
					df.writeStream
					.foreachBatch(process_batch)
					.option("checkpointLocation", checkpoint_path)
					.trigger(processingTime=f"{trigger_interval} seconds")
					.start()
				)
				break
			except Exception as start_err:
				if attempt == max_attempts:
					raise
				print(
					f"Stream start attempt {attempt}/{max_attempts} failed: {start_err}. "
					f"Retrying in {retry_delay_seconds}s..."
				)
				time.sleep(retry_delay_seconds)

		if query is None:
			raise RuntimeError("Unable to start streaming query after retries.")

		print("Write stream started successfully.")
		query.awaitTermination()
	except Exception as e:
		if _is_kafka_offset_out_of_range_error(e):
			print(
				"Detected Kafka offset out-of-range/data-loss condition. "
				"This typically means checkpointed offsets are older than Kafka retention. "
				"Current config uses failOnDataLoss="
				f"{str(KAFKA_FAIL_ON_DATA_LOSS).lower()}. "
				"If this keeps happening, enable RESET_CHECKPOINT_ON_START=true once "
				"to rebuild consumption state from KAFKA_STARTING_OFFSETS."
			)
		print(f"An error occurred in write_stream: {e}")
		raise


def run_pipeline() -> None:
	"""Create Spark session, ensure DB table exists, read stream, and write to PostgreSQL."""
	ensure_table_exists()
	_reset_checkpoint_if_configured()
	spark = create_spark_session()
	try:
		processed_df = process_stream(spark, KAFKA_BROKERS, KAFKA_TOPIC)
		write_stream(spark, processed_df, CHECKPOINT_PATH)
	finally:
		spark.stop()
