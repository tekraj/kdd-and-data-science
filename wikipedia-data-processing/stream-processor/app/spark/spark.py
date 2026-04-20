from pyspark.sql import SparkSession


def create_spark_session() -> SparkSession:
    return (
        SparkSession.builder.appName("WikipediaStreamProcessor")
        .config("spark.jars.packages", "org.apache.spark:spark-sql-kafka-0-10_2.12:3.4.0")
        .getOrCreate()
    )
