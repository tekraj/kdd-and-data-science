# Step 3: Silver Layer ETL (Spark + Feature Engineering)

## Goal

Transform raw JSON events from Bronze into clean, analytics-ready Parquet data in Silver.

In this step, you will:
1. Clean and standardize key fields.
2. Create useful ML features.
3. Save partitioned Parquet to S3.
4. Query the Silver table in Athena.

## Input and output

Input:
1. Glue catalog table: `wiki_db.raw_edits` (from Step 2)
2. Format: JSON

Output:
1. S3 Silver path: `s3://wiki-knowledge-lake-silver-<your-unique-suffix>/silver-edits/`
2. Format: Parquet
3. Table name example: `silver_edits`

## 1. Create Silver S3 bucket

1. Create bucket: `wiki-knowledge-lake-silver-<your-unique-suffix>`
2. Create folder: `silver-edits/`

## 2. Create Glue Spark job

1. Open AWS Glue -> Jobs -> Create job.
2. Type: Spark script editor.
3. Glue version: latest available in your account.
4. Worker type: `G.1X` (student-friendly default).
5. Number of workers: start with 2.
6. Enable Job Bookmarks (important for processing only new files).

## 3. ETL logic students should implement

Core transformations:
1. Cast and clean fields (`timestamp`, `server_name`, `user`, `comment`).
2. Derive `is_bot` from metadata.
3. Derive `edit_velocity = length.new - length.old`.
4. Derive `is_anonymous` from IP-like usernames.
5. Derive `label_vandalism` from comment keywords.
6. Derive `link_density` from URL count in comments.

Simple labeling rule:

`label_vandalism = 1` if comment contains words like `reverted`, `undid`, `rvv`; otherwise `0`.

## 4. Example Glue PySpark script (student version)

```python
import sys
from awsglue.context import GlueContext
from awsglue.job import Job
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from pyspark.sql import functions as F

args = getResolvedOptions(sys.argv, ["JOB_NAME"])
sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args["JOB_NAME"], args)

# 1) Read Bronze table
df = glueContext.create_dynamic_frame.from_catalog(
    database="wiki_db",
    table_name="raw_edits"
).toDF()

# 2) Clean and feature engineer
clean_df = (
    df
    .withColumn("comment", F.coalesce(F.col("comment"), F.lit("")))
    .withColumn("user", F.coalesce(F.col("user"), F.lit("unknown")))
    .withColumn("server_name", F.coalesce(F.col("server_name"), F.lit("unknown")))
    .withColumn("is_bot", F.coalesce(F.col("bot"), F.lit(False)).cast("boolean"))
    .withColumn("length_new", F.col("length.new").cast("int"))
    .withColumn("length_old", F.col("length.old").cast("int"))
    .withColumn("edit_velocity", F.coalesce(F.col("length_new"), F.lit(0)) - F.coalesce(F.col("length_old"), F.lit(0)))
    .withColumn("comment_lc", F.lower(F.col("comment")))
    .withColumn(
        "label_vandalism",
        F.when(F.col("comment_lc").rlike("reverted|undid|rvv"), F.lit(1)).otherwise(F.lit(0))
    )
    .withColumn("link_density", F.size(F.split(F.col("comment_lc"), "http")) - 1)
    .withColumn("is_anonymous", F.col("user").rlike("^[0-9]{1,3}(\\.[0-9]{1,3}){3}$"))
)

# 3) Partition columns
out_df = (
    clean_df
    .withColumn("event_ts", F.to_timestamp(F.col("timestamp")))
    .withColumn("year", F.year(F.col("event_ts")))
    .withColumn("month", F.month(F.col("event_ts")))
    .withColumn("day", F.dayofmonth(F.col("event_ts")))
)

# 4) Write Silver Parquet
(
    out_df
    .write
    .mode("append")
    .partitionBy("year", "month", "day", "server_name")
    .parquet("s3://wiki-knowledge-lake-silver-<your-unique-suffix>/silver-edits/")
)

job.commit()
```

## 5. Create crawler for Silver data

1. Create another crawler: `wiki-silver-crawler`
2. Path: `s3://wiki-knowledge-lake-silver-<your-unique-suffix>/silver-edits/`
3. Database: `wiki_db`
4. Run crawler

Expected table: `silver_edits`

## 6. Validate with Athena

Run query to check transformed data:

```sql
SELECT
  server_name,
  SUM(label_vandalism) AS vandalism_events,
  AVG(edit_velocity) AS avg_edit_velocity,
  SUM(CASE WHEN is_bot THEN 1 ELSE 0 END) AS bot_events
FROM wiki_db.silver_edits
GROUP BY server_name
ORDER BY vandalism_events DESC
LIMIT 20;
```

## 7. Common mistakes

Null errors in Spark:
1. Use `coalesce` for nullable fields.

Table not updating:
1. Rerun Silver crawler.
2. Check output S3 path is correct.

Repeated old data:
1. Enable Job Bookmarks.
2. Avoid writing with `overwrite` mode for streaming batches.

## Step 3 checkpoint

You are done when:
1. Silver Parquet files are written and partitioned.
2. `wiki_db.silver_edits` is queryable in Athena.
3. Feature columns (`is_bot`, `label_vandalism`, `edit_velocity`) have values.