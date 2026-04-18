# Step 2: Build the Real-Time S3-Triggered Pipeline

## Goal

In this step, you will create an event-driven streaming pipeline. Because Kinesis creation is restricted in this environment, you will use **S3 Event Notifications** and **SQS** to simulate a real-time stream. A Glue Streaming job will "listen" to the SQS queue and move incoming data to your Bronze layer.

**Result:**
1. JSON events dropped by EC2 are detected via SQS.
2. Glue Streaming moves these records to the Bronze folder every 60 seconds.
3. A Glue Crawler creates a queryable table for Athena.

## Naming convention (recommended)

Use consistent names to avoid "Resource Not Found" errors:
1. S3 Bucket: `wiki-knowledge-lake-<your-unique-suffix>`
2. SQS Queue: `wiki-event-queue`
3. Landing folder (Source): `landing/`
4. Bronze folder (Sink): `bronze/`
5. Glue Database: `wiki_db`
6. Raw table: `raw_edits`

> **Note:** S3 bucket names are globally unique. Add a suffix like your student ID or initials.

---

## 1. Prepare the S3 Bucket and Folders

1. Open the **S3 Console**.
2. Create a bucket: `wiki-knowledge-lake-<your-unique-suffix>`.
3. Inside the bucket, create the following folders (prefixes):
   * `landing/` (Where EC2 drops raw events)
   * `bronze/` (Where the streaming job saves processed raw data)
   * `checkpoints/` (For Glue metadata)

## 2. Create the SQS Queue and S3 Event

1. **Create Queue:** Go to **SQS Console** -> **Create Queue**. Name it `wiki-event-queue`. Keep defaults and Create.
2. **Set Notification:** * Go back to your **S3 Bucket** -> **Properties** tab.
   * Scroll to **Event notifications** -> **Create event notification**.
   * **Event name:** `LandingToSQS`.
   * **Prefix:** `landing/` (**CRITICAL:** Do not leave this blank. Restricting it to the landing folder prevents infinite loops).
   * **Event types:** Select `All object create events`.
   * **Destination:** SQS Queue -> Choose `wiki-event-queue`.
```
{
  "Version": "2012-10-17",
  "Id": "__default_policy_ID",
  "Statement": [
    {
      "Sid": "__owner_statement",
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::036628614391:root"
      },
      "Action": "SQS:*",
      "Resource": "arn:aws:sqs:us-east-1:036628614391:wiki-event-queue"
    },
    {
      "Sid": "AllowS3ToPublishMessages",
      "Effect": "Allow",
      "Principal": {
        "Service": "s3.amazonaws.com"
      },
      "Action": "sqs:SendMessage",
      "Resource": "arn:aws:sqs:us-east-1:036628614391:wiki-event-queue",
      "Condition": {
        "ArnLike": {
          "aws:SourceArn": "arn:aws:s3:::wiki-knowledge-lake-*"
        }
      }
    }
  ]
}
```
## 3. Create Glue Streaming ETL job

1. Open **AWS Glue Studio** -> **Jobs** -> Spark Streaming -> **Visual with source and target**.
2. **Source:** Select **Amazon S3**.
3. **Target:** Select **Amazon S3**.

**Configure Source (S3 Streaming):**
1. **S3 Source Type:** Change dropdown to **S3 Streaming**.
2. **S3 source path:** `s3://wiki-knowledge-lake-<suffix>/landing/`.
3. **SQS queue URL:** Paste your `wiki-event-queue` URL.
4. **Data format:** JSON.

**Configure Target (S3):**
1. **Format:** JSON.
2. **S3 Target Path:** `s3://wiki-knowledge-lake-<suffix>/bronze/`.

**Job Details tab:**
1. **IAM Role:** Select the provided lab role (usually `voclabs`).
2. **Type:** Spark Streaming.
3. **Window size:** `60 seconds` (This controls how often Glue writes a file to S3).
4. **Checkpoint location:** `s3://wiki-knowledge-lake-<suffix>/checkpoints/`.

## 4. Start the Pipeline

1. **Save** and **Run** the Glue Job.
2. Ensure your **Step 1 Ingestion (EC2)** script is running and writing JSON files to the `/landing` folder.
3. Wait 3-5 minutes, then check the `/bronze` folder. You should see new JSON files appearing.

## 5. Create and run Glue Crawler

1. Open **Glue -> Crawlers** -> **Create crawler**.
2. **Name:** `wiki-bronze-crawler`.
3. **Data source:** `s3://wiki-knowledge-lake-<suffix>/bronze/`.
4. **Output database:** `wiki_db` (Create it if it doesn't exist).
5. **Run** the crawler and wait for the status to return to `Ready`.

## 6. Verify in Athena

Open the Athena Query Editor and run the following:

```sql
SELECT server_name, COUNT(*) AS edits
FROM wiki_db.bronze
GROUP BY server_name
ORDER BY edits DESC
LIMIT 10;
```
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