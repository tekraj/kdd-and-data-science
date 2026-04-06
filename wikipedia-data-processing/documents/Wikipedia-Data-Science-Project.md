# Wikipedia Data Science Project

This project teaches students how to build a simple real-time data pipeline on AWS using live Wikipedia edit events.

## 1. What students will build

End-to-end pipeline:
1. Ingest live events from Wikipedia into Kinesis.
2. Stream Kinesis data to S3 Bronze using Glue Streaming.
3. Transform Bronze JSON into Silver Parquet using Glue Spark.
4. Query and analyze in Athena.
5. Optional: train models in SageMaker and build dashboard in Redshift.

## 2. Architecture overview

Layer 1 (Ingestion):
1. Source: Wikipedia EventStreams (SSE)
2. Service: EC2 + Docker (`data-ingestion` service)
3. Output: Kinesis stream (`wiki-kinesis-stream`)

Layer 2 (Bronze):
1. Service: Glue Streaming Job
2. Output: raw JSON files in S3 every 60 seconds
3. Catalog: Glue Crawler creates `wiki_db.raw_edits`

Layer 3 (Silver):
1. Service: Glue Spark batch job
2. Output: cleaned/feature-engineered Parquet in S3
3. Catalog: Glue Crawler creates `wiki_db.silver_edits`

Layer 4 (Analytics and ML):
1. Athena for EDA and anomaly analysis
2. SageMaker for classification (optional)
3. Redshift dashboard for reporting (optional)

## 3. Why this project is good for students

Students learn:
1. Real-time ingestion and cloud streaming basics.
2. Data lake design (Bronze to Silver).
3. Feature engineering with Spark.
4. SQL analytics on semi-structured data.
5. How to convert raw events into ML-ready data.

## 4. Recommended AWS naming convention

Use consistent names in every step:
1. Kinesis stream: `wiki-kinesis-stream`
2. Bronze bucket: `wiki-knowledge-lake-bronze-<suffix>`
3. Silver bucket: `wiki-knowledge-lake-silver-<suffix>`
4. Glue database: `wiki_db`
5. Bronze table: `raw_edits`
6. Silver table: `silver_edits`

## 5. Step-by-step roadmap

1. Step 1: Deploy ingestion service and publish events to Kinesis.
2. Step 2: Build streaming ETL from Kinesis to S3 Bronze and catalog it.
3. Step 3: Run Spark ETL to create Silver Parquet and engineered features.
4. Step 4 (optional): Train model in SageMaker.
5. Step 5 (optional): Build dashboard in Redshift or QuickSight.

## 6. Student project ideas (choose one)

1. Vandalism detector using comment text and edit size.
2. Bot vs human behavior analysis by language wiki (`server_name`).
3. Real-time trend tracker for breaking news pages.
4. Link-spam detector using `link_density` and revert behavior.

## 7. Suggested features for modeling

1. `is_bot`
2. `is_anonymous`
3. `edit_velocity`
4. `link_density`
5. `label_vandalism` (rule-based weak label)

Example weak label rule:
If comment contains `reverted`, `undid`, or `rvv`, set `label_vandalism = 1`, else `0`.

## 8. Validation checklist

Before moving to ML, verify:
1. New records are continuously arriving in Kinesis.
2. Bronze S3 folder receives JSON files every few minutes.
3. Athena can query `wiki_db.raw_edits`.
4. Silver S3 folder contains Parquet partitions.
5. Athena can query `wiki_db.silver_edits` with non-null features.

## 9. Cost and safety tips for students

1. Use on-demand Kinesis for small projects.
2. Use 60 to 120 second Glue windows to reduce tiny files.
3. Stop EC2 when not in use.
4. Delete unused Glue jobs/crawlers after submission.
5. Set AWS billing alerts.

## 10. Final learning outcomes

By completing this project, students can:
1. Build a working real-time data pipeline on AWS.
2. Apply ETL and feature engineering to event data.
3. Perform cloud-based analytics and basic anomaly detection.
4. Prepare data for practical ML experiments.

For implementation details, use these companion guides:
1. `Step 1-Data-Ingestion.md`
2. `Step-2-Building a Real-Time Data Pipeline.md`
3. `Step 3-Spark ETL & Feature Engineering.md`