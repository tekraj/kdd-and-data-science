from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import from_json, col, to_json, from_unixtime, to_timestamp
from pyspark.sql.types import StructType, ArrayType, MapType
import os
import shutil
import time
from schema import wikimedia_schema
from spark import create_spark_session
from config import (
	KAFKA_BROKERS,
	KAFKA_TOPIC,
	OUTPUT_PATH,
	CHECKPOINT_PATH,
	KAFKA_STARTING_OFFSETS,
	KAFKA_FAIL_ON_DATA_LOSS,
	KAFKA_MAX_OFFSETS_PER_TRIGGER,
	RESET_CHECKPOINT_ON_START,
)
from db.connection import ensure_table_exists
from db.writer import write_batch_to_postgres


def process_stream(spark: SparkSession, kafka_brokers: str, kafka_topic: str) -> DataFrame:
	"""
	Reads a stream from Kafka, processes it, and returns a DataFrame.
	"""
	print("Initializing Kafka stream processing...")
	try:
		stream_reader = (
			spark.readStream.format("kafka")
			.option("kafka.bootstrap.servers", kafka_brokers)
			.option("subscribe", kafka_topic)
			.option("startingOffsets", KAFKA_STARTING_OFFSETS)
			.option("failOnDataLoss", str(KAFKA_FAIL_ON_DATA_LOSS).lower())
		)

		if KAFKA_MAX_OFFSETS_PER_TRIGGER:
			stream_reader = stream_reader.option(
				"maxOffsetsPerTrigger", KAFKA_MAX_OFFSETS_PER_TRIGGER
			)

		stream_df = stream_reader.load()

		# Parse the value from JSON and apply the schema
		json_df = stream_df.select(from_json(col("value").cast("string"), wikimedia_schema).alias("data"))

		print(
			"Successfully read from Kafka stream and parsed JSON. "
			f"startingOffsets={KAFKA_STARTING_OFFSETS}, "
			f"failOnDataLoss={str(KAFKA_FAIL_ON_DATA_LOSS).lower()}"
		)

		# Select, timestamp, and deduplicate events to reduce repeated rows across reconnects.
		processed_df = (
			json_df.select("data.*")
			.withColumn("event_time", to_timestamp(from_unixtime(col("timestamp").cast("long"))))
			.withWatermark("event_time", "10 minutes")
			.dropDuplicates(["id", "event_time"])
		)

		return processed_df
	except Exception as e:
		print(f"An error occurred in process_stream: {e}")
		# Re-raise the exception to see the full traceback in the logs
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
	df: DataFrame, output_path: str, checkpoint_path: str, trigger_interval: int = 10
) -> None:
	"""
	Writes each micro-batch to both CSV files and PostgreSQL.
	"""
	print(f"Attempting to write stream to path: {output_path}")
	try:
		csv_safe_df = prepare_for_csv(df)
		max_attempts = 12
		retry_delay_seconds = 5
		query = None

		def process_batch(batch_df, batch_id):
			try:
				# Write to CSV — preserves the existing file-based output
				(
					batch_df.write
					.mode("append")
					.option("header", "true")
					.csv(output_path)
				)
			except Exception as csv_err:
				print(f"[Batch {batch_id}] CSV write failed: {csv_err}")
				raise

			try:
				# Write to PostgreSQL
				write_batch_to_postgres(batch_df)
			except Exception as db_err:
				print(f"[Batch {batch_id}] PostgreSQL write failed: {db_err}")
				raise

		for attempt in range(1, max_attempts + 1):
			try:
				query = (
					csv_safe_df.writeStream
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


def prepare_for_csv(df: DataFrame) -> DataFrame:
	"""
	Converts unsupported CSV column types into CSV-safe columns.

	- Struct columns are flattened one level with a `<parent>_<child>` naming pattern.
	- Array and map columns are serialized to JSON strings.
	"""
	select_cols = []

	for field in df.schema.fields:
		field_name = field.name
		data_type = field.dataType

		if isinstance(data_type, StructType):
			for nested_field in data_type.fields:
				select_cols.append(
					col(f"{field_name}.{nested_field.name}").alias(f"{field_name}_{nested_field.name}")
				)
		elif isinstance(data_type, (ArrayType, MapType)):
			select_cols.append(to_json(col(field_name)).alias(field_name))
		else:
			select_cols.append(col(field_name))

	return df.select(*select_cols)


def run_pipeline() -> None:
	"""Create Spark session, ensure DB table exists, read from Kafka, and write to CSV + PostgreSQL."""
	ensure_table_exists()
	_reset_checkpoint_if_configured()
	spark = create_spark_session()
	try:
		processed_df = process_stream(spark, KAFKA_BROKERS, KAFKA_TOPIC)
		write_stream(processed_df, OUTPUT_PATH, CHECKPOINT_PATH)
	finally:
		spark.stop()
