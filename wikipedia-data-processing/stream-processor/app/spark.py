from pyspark.sql import SparkSession

def get_spark_session():
    return (
        SparkSession.builder.appName("WikipediaStreamProcessor")
        .config("spark.jars.packages", "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0")
        .getOrCreate()
    )
