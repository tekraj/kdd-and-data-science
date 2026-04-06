# Step 2: Build the Real-Time Kinesis -> S3 Pipeline

## Goal

In this step, you will create a Glue Streaming job that reads events from Kinesis and writes raw JSON files to S3 every 60 seconds.

Result:
1. Kinesis records are continuously moved to S3 (Bronze layer).
2. A Glue Crawler creates a queryable table.
3. Athena can query incoming Wikipedia events.

## Naming convention (recommended)

Use the same names everywhere to avoid confusion:
1. Kinesis stream: `wiki-kinesis-stream`
2. Bronze bucket: `wiki-knowledge-lake-bronze-<your-unique-suffix>`
3. Raw folder: `raw-edits/`
4. Glue database: `wiki_db`
5. Raw table: `raw_edits`

Note: S3 bucket names are globally unique, so add a suffix like your initials or student ID.

## 1. Create S3 Bronze destination

1. Open S3 Console.
2. Create bucket: `wiki-knowledge-lake-bronze-<your-unique-suffix>`.
3. Keep default settings (block public access enabled).
4. Create folder path: `raw-edits/`.

Target path format:

`s3://wiki-knowledge-lake-bronze-<your-unique-suffix>/raw-edits/`

## 2. Create Glue Streaming ETL job

1. Open AWS Glue Studio.
2. Go to Jobs -> Create job.
3. Choose Visual with source and target.
4. Set source to Amazon Kinesis.
5. Set target to Amazon S3.

Configure source (Kinesis):
1. Stream: `wiki-kinesis-stream`
2. Starting position: Latest
3. Infer schema: enabled (for first run)

Configure target (S3):
1. Format: JSON
2. S3 target: `s3://wiki-knowledge-lake-bronze-<your-unique-suffix>/raw-edits/`
3. Compression: optional (GZIP is fine)

Job details:
1. Job type: Streaming
2. IAM role: role with permissions for Kinesis + S3 + Glue
3. Window size: `60 seconds` (important to reduce tiny files)

## 3. Start the streaming job

1. Save the job.
2. Start job run.
3. Wait 2 to 5 minutes.
4. Check S3 `raw-edits/` for new JSON files.

If files are not appearing, confirm Step 1 ingestion container is still running.

## 4. Create and run Glue Crawler

Glue crawler will register schema so Athena can query your data.

1. Open Glue -> Crawlers -> Create crawler.
2. Name: `wiki-bronze-crawler`
3. Data source: `s3://wiki-knowledge-lake-bronze-<your-unique-suffix>/raw-edits/`
4. Output database: `wiki_db` (create if needed)
5. Run crawler.

Expected result:
1. Database: `wiki_db`
2. Table: `raw_edits`

## 5. Verify in Athena

Open Athena and run:

```sql
SELECT server_name, COUNT(*) AS edits
FROM wiki_db.raw_edits
GROUP BY server_name
ORDER BY edits DESC
LIMIT 20;
```

If query returns rows, Step 2 is successful.

## 6. Troubleshooting

No files in S3:
1. Check Glue streaming job status and logs.
2. Check Kinesis has incoming records.
3. Confirm source stream name is correct.

Athena table empty:
1. Ensure crawler ran after files were created.
2. Rerun crawler.
3. Verify Athena is querying the correct database and table.

Too many tiny files:
1. Increase window size (for example, 120 seconds).
2. Keep ingestion stable and avoid frequent job restarts.

## Step 2 checkpoint

You are ready for Step 3 when:
1. S3 receives new raw JSON files continuously.
2. `wiki_db.raw_edits` exists in Glue Data Catalog.
3. Athena query returns results.