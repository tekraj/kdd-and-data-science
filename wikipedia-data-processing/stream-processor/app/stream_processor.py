from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import from_json, col
from app.schema import get_schema


def process_stream(spark: SparkSession, kafka_brokers: str, kafka_topic: str) -> DataFrame:
	"""
	Reads a stream from Kafka, processes it, and returns a DataFrame.
	"""
	print("Initializing Kafka stream processing...")
	try:
		stream_df = (
			spark.readStream.format("kafka")
			.option("kafka.bootstrap.servers", kafka_brokers)
			.option("subscribe", kafka_topic)
			.load()
		)

		# Parse the value from JSON and apply the schema
		json_df = stream_df.select(from_json(col("value").cast("string"), get_schema()).alias("data"))

		print("Successfully read from Kafka stream and parsed JSON.")

		# Select the fields
		processed_df = json_df.select("data.*")

		return processed_df
	except Exception as e:
		print(f"An error occurred in process_stream: {e}")
		# Re-raise the exception to see the full traceback in the logs
		raise


def write_stream(
	df: DataFrame, output_path: str, checkpoint_path: str, trigger_interval: int = 10
) -> None:
	"""
	Writes a DataFrame to a stream.
	"""
	print(f"Attempting to write stream to path: {output_path}")
	try:
		query = (
			df.writeStream.format("csv")
			.option("path", output_path)
			.option("header", "true")
			.option("checkpointLocation", checkpoint_path)
			.trigger(processingTime=f"{trigger_interval} seconds")
			.start()
		)
		print("Write stream started successfully.")
		query.awaitTermination()
	except Exception as e:
		print(f"An error occurred in write_stream: {e}")
		# Re-raise the exception to see the full traceback in the logs
		raise
