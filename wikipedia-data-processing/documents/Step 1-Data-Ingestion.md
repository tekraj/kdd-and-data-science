# Step 1: Data Ingestion (Wikipedia SSE -> AWS Kinesis)

## Goal

In this step, you will run a service that reads live Wikipedia edit events and sends each event to an AWS Kinesis Data Stream.

Pipeline for this step:
1. Connect to Wikipedia EventStreams (SSE).
2. Receive recent-change JSON events.
3. Publish each event into Kinesis using `PutRecord`.

Service folder: `wikipedia-data-processing/data-ingestion`

## What students will build

By the end of Step 1, you should have:
1. A running EC2 instance.
2. A Kinesis stream (`wiki-kinesis-stream`).
3. A Docker container (`wiki-data-ingestion`) publishing events continuously.

## Prerequisites

Before starting:
1. AWS account and access to EC2, IAM, and Kinesis.
2. SSH key pair for EC2 login.
3. This repository URL.
4. Basic terminal knowledge.

## 1. Create a Kinesis stream first

Use a single stream name across all project steps:

`wiki-kinesis-stream`

Option A (Console):
1. Open AWS Console -> Kinesis -> Data Streams.
2. Click Create data stream.
3. Name: `wiki-kinesis-stream`
4. Capacity mode: On-demand (recommended for students).

Option B (CLI):

```bash
aws kinesis create-stream \
  --stream-name wiki-kinesis-stream \
  --stream-mode-details StreamMode=ON_DEMAND
```

## 2. Create IAM role for EC2

Your container needs permission to write to Kinesis.

Create an IAM role for EC2 with this minimum policy (replace placeholders):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "kinesis:PutRecord",
        "kinesis:DescribeStream"
      ],
      "Resource": "arn:aws:kinesis:<region>:<account-id>:stream/wiki-kinesis-stream"
    }
  ]
}
```

Attach this role to your EC2 instance as an instance profile.

## 3. Create and prepare EC2

Recommended settings:
1. AMI: Ubuntu Server 22.04 LTS
2. Type: `t2.micro` (or `t3.micro`)
3. Security Group: allow SSH (TCP 22) from your IP only

SSH into EC2:

```bash
ssh -i /path/to/your-key.pem ubuntu@YOUR_EC2_PUBLIC_IP
```

Install Docker and Git:

```bash
sudo apt update
sudo apt install -y git docker.io
sudo systemctl enable docker
sudo systemctl start docker
sudo usermod -aG docker $USER
```

Log out and login again so Docker group permissions take effect.

## 4. Clone project and move to ingestion folder

```bash
git clone YOUR_REPOSITORY_URL
cd kdd-and-data-science/wikipedia-data-processing/data-ingestion
```

## 5. Configure environment variables

Create `.env` file from template:

```bash
cp .env.example .env
```

Edit `.env` and keep values consistent:

```env
AWS_REGION=us-east-1
KINESIS_STREAM_NAME=wiki-kinesis-stream
WIKIPEDIA_SSE_URL=https://stream.wikimedia.org/v2/stream/recentchange
LOG_EVERY_N_EVENTS=100
```

Important: `KINESIS_STREAM_NAME` and `AWS_REGION` must match your actual stream.

## 6. Build and run the container

Build image:

```bash
docker build -t wiki-data-ingestion:latest .
```

Run container:

```bash
docker run -d \
  --name wiki-data-ingestion \
  --restart unless-stopped \
  --env-file .env \
  wiki-data-ingestion:latest
```

## 7. Validate that ingestion is working

Check running container:

```bash
docker ps
```

Check logs:

```bash
docker logs -f wiki-data-ingestion
```

Expected in logs:
1. Startup configuration (region and stream).
2. Connected to Wikipedia SSE.
3. Events being published periodically.

## 8. Useful operations

```bash
docker stop wiki-data-ingestion
docker start wiki-data-ingestion
docker restart wiki-data-ingestion
docker rm -f wiki-data-ingestion
```

## 9. Common issues

`AccessDeniedException`
1. EC2 role is missing Kinesis permissions.
2. Policy ARN does not match the stream ARN.

`ResourceNotFoundException`
1. Wrong stream name in `.env`.
2. Wrong AWS region.

No events in logs
1. Check internet access from EC2.
2. Check for SSE connection errors in `docker logs`.

## Step 1 checkpoint

You are ready for Step 2 when:
1. Container is running.
2. Logs show published events.
3. Kinesis stream has incoming records.
