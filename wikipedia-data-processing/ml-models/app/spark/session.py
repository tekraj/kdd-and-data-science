from pyspark.sql import SparkSession


def create_spark_session() -> SparkSession:
    return (
        SparkSession.builder.appName("WikipediaMLRetrainListener")
        .config("spark.sql.shuffle.partitions", "4")
        .getOrCreate()
    )
