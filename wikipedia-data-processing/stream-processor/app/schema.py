from pyspark.sql.types import (
    StructType,
    StructField,
    StringType,
    IntegerType,
    BooleanType,
    DoubleType,
    TimestampType,
)

wikimedia_schema = StructType(
    [
        StructField("id", IntegerType(), True),
        StructField("type", StringType(), True),
        StructField("title", StringType(), True),
        StructField("timestamp", DoubleType(), True),
        StructField("user", StringType(), True),
        StructField("bot", BooleanType(), True),
        StructField(
            "meta",
            StructType(
                [
                    StructField("uri", StringType(), True),
                    StructField("request_id", StringType(), True),
                    StructField("id", StringType(), True),
                    StructField("dt", StringType(), True),
                    StructField("domain", StringType(), True),
                    StructField("stream", StringType(), True),
                ]
            ),
            True,
        ),
        StructField("wiki", StringType(), True),
    ]
)
