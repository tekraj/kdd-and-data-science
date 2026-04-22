# Wikipedia Real-Time Data Processing Pipeline

A real-time data pipeline that streams Wikipedia edit events via the [Wikimedia SSE stream](https://stream.wikimedia.org/v2/stream/recentchange), processes them with Apache Spark Structured Streaming, stores results in PostgreSQL, and visualizes analytics in Grafana.

**Stack:** Node.js (data ingestion) → Kafka → PySpark (stream processor) → PostgreSQL → Grafana

---

## Prerequisites

Install Docker based on your operating system:

- **Windows / macOS:** [Install Docker Desktop](https://www.docker.com/products/docker-desktop/)
- **Ubuntu/Linux:**
  ```bash
  sudo apt-get update
  sudo apt-get install -y docker.io docker-compose-plugin
  sudo systemctl enable --now docker
  sudo usermod -aG docker $USER   # log out and back in after this
  ```

---

## Getting Started

### 1. Clone the Repository

```bash
git clone https://github.com/tekraj/kdd-and-data-science.git
```

Open the cloned folder in VS Code (`File → Open Folder`, or `code kdd-and-data-science` from the terminal).

---

### 2. Navigate to the Project Directory

Open the integrated VS Code terminal (`Ctrl+`` ` or `Terminal → New Terminal`) and run:

```bash
cd wikipedia-data-processing
```

---

### 3. Create Required Data Directories

The pipeline uses local bind-mounted volumes. Create all required directories:

```bash
mkdir -p data/checkpoint data/csv data/duckdb data/grafana data/postgres data/models
```

---

### 4. Configure Environment Variables

Copy the example environment file and use it as your `.env`:

```bash
cp .env.example .env
```

The default values work out of the box for local development. Open `.env` if you need to customise anything (e.g. Kafka offsets, throttling):

```dotenv
NODE_ENV=production
KAFKA_BROKERS=kafka:9092
WIKIPEDIA_SSE_URL=https://stream.wikimedia.org/v2/stream/recentchange
KAFKA_TOPIC=wikipedia-stream
OUTPUT_PATH=/app/data/csv
CHECKPOINT_PATH=/app/data/checkpoint
KAFKA_STARTING_OFFSETS=latest
KAFKA_FAIL_ON_DATA_LOSS=false

# PostgreSQL
POSTGRES_HOST=db
POSTGRES_PORT=5432
POSTGRES_DB=wikipedia
POSTGRES_USER=superset
POSTGRES_PASSWORD=superset_pass
```

---

### 5. Build the Docker Images

```bash
docker compose build
```

This builds the Node.js data-ingestion image and the PySpark stream-processor image. The first build may take a few minutes as it downloads base images and Python/Spark dependencies.

---

### 6. Start the Pipeline

```bash
docker compose up
```

> Tip: add `-d` to run in detached (background) mode: `docker compose up -d`

Docker Compose will start the following services in order:

| Service            | Description                                         | Port        |
|--------------------|-----------------------------------------------------|-------------|
| `zookeeper`        | Kafka coordination service                          | internal    |
| `kafka`            | Message broker                                      | `29092`     |
| `db`               | PostgreSQL 15 database                              | `5432`      |
| `app`              | Node.js Wikipedia SSE → Kafka producer              | —           |
| `stream-processor` | PySpark consumer → processes events → writes to DB  | —           |
| `grafana`          | Grafana dashboard                                   | `3001`      |

Wait **2–3 minutes** for all services to become healthy and for data to start flowing into PostgreSQL.

---

## Grafana Dashboards

### Open Grafana

Navigate to [http://localhost:3001](http://localhost:3001) in your browser and log in with:

- **Username:** `admin`
- **Password:** `admin`

---

### Add PostgreSQL as a Data Source

1. In the left sidebar go to **Connections → Data sources → Add data source**.
2. Search for and select **PostgreSQL**.
3. Fill in the connection details:

   | Field      | Value          |
   |------------|----------------|
   | Host       | `db:5432`      |
   | Database   | `wikipedia`    |
   | User       | `superset`     |
   | Password   | `superset_pass`|
   | TLS/SSL    | disable        |

4. Click **Save & Test** — you should see *"Database Connection OK"*.

---

### Create a New Dashboard

Go to **Dashboards → New → New Dashboard → Add visualization**, then select the PostgreSQL data source you just added. Use the SQL queries below to build each panel.

---

## Dashboard Panels & SQL Queries

### 1. Total Updates Overview (Time Lapse)

**Goal:** Get a quick at-a-glance summary — how many total edits have been captured, and what is the time span from the very first event recorded to the most recent.

**Visualization:** Stat / Table panel

```sql
SELECT 
    COUNT(*) AS total_updates,
    to_char(MIN(event_time), 'YYYY-MM-DD HH24:MI:SS') AS stream_start,
    to_char(MAX(event_time), 'YYYY-MM-DD HH24:MI:SS') AS stream_end,
    ROUND(EXTRACT(EPOCH FROM (MAX(event_time) - MIN(event_time))) / 3600, 2) AS duration_hours
FROM wikipedia_changes;
```

---

### 2. Most Frequently Updated Pages

**Goal:** Find the pages receiving the most edits in the last hour — a live view of what's trending on Wikipedia right now.

**Visualization:** Horizontal Bar Chart or Table

```sql
SELECT 
    title, 
    COUNT(title) AS total_updates
FROM 
    wikipedia_changes 
WHERE 
    "timestamp" >= extract(epoch FROM (now() - interval '1 hour'))
GROUP BY 
    title
ORDER BY 
    total_updates DESC
LIMIT 20;
```

---

### 3. Most Active Users

**Goal:** Identify the top contributors (humans and bots) over the last 24 hours.

**Visualization:** Horizontal Bar Chart or Table

```sql
SELECT 
    "user", 
    COUNT(*) AS total_updates
FROM 
    wikipedia_changes 
WHERE 
    "timestamp" >= extract(epoch FROM (now() - interval '24 hours'))
GROUP BY 
    "user"
ORDER BY 
    total_updates DESC
LIMIT 20;
```

---

### 4. Activity Distribution by Wiki Project

**Goal:** Identify which Wikipedia language or project (e.g., English vs. German vs. Wikidata) is currently most active.

**Visualization:** Treemap or Horizontal Bar Chart

```sql
SELECT 
    wiki, 
    COUNT(*) AS edit_count 
FROM wikipedia_changes 
WHERE "timestamp" >= extract(epoch FROM (now() - interval '6 hours'))
GROUP BY wiki 
ORDER BY edit_count DESC 
LIMIT 15;
```

---

### 5. Temporal Edit Velocity (Throughput)

**Goal:** See the "heartbeat" of Wikipedia — identify peak usage times or sudden spikes caused by world events.

**Visualization:** Time-Series Line Chart

```sql
SELECT 
    to_timestamp(floor("timestamp" / 300) * 300) AS time_bucket,
    COUNT(*) AS updates
FROM wikipedia_changes 
WHERE "timestamp" >= extract(epoch FROM (now() - interval '12 hours'))
GROUP BY time_bucket 
ORDER BY time_bucket ASC;
```

---

### 6. Contribution Diversity (Human vs. Bot)

**Goal:** Understand the automated nature of different wikis. Some wikis rely almost entirely on bots for maintenance.

**Visualization:** Stacked Bar Chart (X-axis: Wiki, Y-axis: Count, Legend: Bot/Human)

```sql
SELECT 
    wiki,
    bot,
    COUNT(*) AS total_edits
FROM wikipedia_changes 
WHERE wiki IN (
    SELECT wiki FROM wikipedia_changes GROUP BY wiki ORDER BY COUNT(*) DESC LIMIT 10
)
GROUP BY wiki, bot;
```

---

### 7. Change Type Breakdown

**Goal:** Analyse the nature of updates. The `type` column contains values like `edit`, `new`, `log`, or `categorize`.

**Visualization:** Donut Chart

```sql
SELECT 
    type, 
    COUNT(*) AS type_count 
FROM wikipedia_changes 
GROUP BY type 
ORDER BY type_count DESC;
```

---

### 8. Domain Dominance (Knowledge Distribution)

**Goal:** Compare the volume of updates across different top-level domains (e.g., `en.wikipedia.org` vs `commons.wikimedia.org`).

**Visualization:** Packed Bubble Chart

```sql
SELECT 
    meta_domain, 
    COUNT(*) AS volume 
FROM wikipedia_changes 
WHERE meta_domain IS NOT NULL
GROUP BY meta_domain 
ORDER BY volume DESC 
LIMIT 10;
```

> **Data Science Tip:** To calculate *Revert Rates*, look for titles edited and then quickly re-edited by a different user. Pages with high edit frequency but low new content growth often indicate an "edit war." Visualise this as a Scatter Plot where X = unique users, Y = total edits, and colour = bot percentage.

---

### 9. User Experience / Seniority Analysis (Loyalty)

**Goal:** Determine if the stream is driven by "drive-by" editors (one-time) or "power users" (repeat contributors).

**Visualization:** Histogram (X-axis: Number of Edits, Y-axis: Number of Users)

```sql
SELECT 
    edit_bucket, 
    COUNT(*) AS user_count
FROM (
    SELECT 
        "user", 
        COUNT(*) AS total_edits,
        CASE 
            WHEN COUNT(*) = 1 THEN '1 edit'
            WHEN COUNT(*) BETWEEN 2 AND 5 THEN '2-5 edits'
            WHEN COUNT(*) BETWEEN 6 AND 20 THEN '6-20 edits'
            ELSE '20+ edits (Power Users)'
        END AS edit_bucket
    FROM wikipedia_changes
    GROUP BY "user"
) sub
GROUP BY edit_bucket;
```

---

### 10. Collaborative "Hotspots" (User-to-Page Ratio)

**Goal:** Find "controversial" pages. A page with 100 edits and 2 users is a dedicated update; 100 edits by 90 users suggests a trending global event.

**Visualization:** Scatter Plot (X: Unique Users, Y: Total Edits)

```sql
SELECT 
    title, 
    COUNT(*) AS total_edits, 
    COUNT(DISTINCT "user") AS unique_users
FROM wikipedia_changes
GROUP BY title
HAVING COUNT(*) > 5
ORDER BY total_edits DESC
LIMIT 50;
```

> **ML Tip:** Apply K-Means Clustering to this scatter plot:
> - **Cluster 1** — High Edits, Low Users → Bot-maintained pages (lists, weather).
> - **Cluster 2** — High Edits, High Users → Breaking news or high-conflict political pages.
> - **Cluster 3** — Low Edits, High Users → Community-driven niche updates.

---

### 11. Peak-Hour "Bursts" (Heatmap)

**Goal:** Identify which days of the week and hours of the day see the highest edit volume.

**Visualization:** Heatmap (X: Hour of Day, Y: Day of Week)

```sql
SELECT 
    EXTRACT(DOW FROM event_time) AS day_of_week, 
    EXTRACT(HOUR FROM event_time) AS hour_of_day, 
    COUNT(*) AS edit_count
FROM wikipedia_changes
GROUP BY 1, 2
ORDER BY 1, 2;
```

---

### 12. Meta-ID Latency (System Health)

**Goal:** Measure the processing lag between when events happened and when Spark wrote them. Use this to monitor pipeline health.

**Visualization:** Area Chart or Gauge

```sql
SELECT 
    event_time,
    EXTRACT(EPOCH FROM (now() - event_time)) AS latency_seconds
FROM wikipedia_changes
ORDER BY event_time DESC
LIMIT 100;
```

---

### 13. Wiki Language Market Share (Cumulative)

**Goal:** Observe how the market share of different language wikis changes over time.

**Visualization:** Stacked Area Chart (Percentage Basis)

```sql
WITH daily_counts AS (
    SELECT 
        date_trunc('day', event_time) AS day,
        wiki,
        COUNT(*) AS daily_total
    FROM wikipedia_changes
    GROUP BY 1, 2
)
SELECT 
    day,
    wiki,
    daily_total * 100.0 / SUM(daily_total) OVER (PARTITION BY day) AS percentage_share
FROM daily_counts
ORDER BY day, percentage_share DESC;
```
### The "Breaking News" Anomaly Detection (Time Series)
Goal: Detect sudden spikes in activity that exceed the normal range (using a Z-Score logic). This is the best way to spot breaking news events or bot-nets.

Grafana Panel: Time Series (with "Thresholds" set to 2 and 3 standard deviations).

SQL Query:
```sql
WITH stats AS (
    SELECT 
        avg(cnt) as mu, 
        stddev(cnt) as sigma 
    FROM (
        SELECT count(*) as cnt 
        FROM wikipedia_changes 
        WHERE event_time > now() - interval '24 hours'
        GROUP BY date_trunc('minute', event_time)
    ) s
)
SELECT 
    date_trunc('minute', event_time) AS time,
    count(*) AS edit_count,
    (count(*) - (SELECT mu FROM stats)) / NULLIF((SELECT sigma FROM stats), 0) as z_score
FROM wikipedia_changes
WHERE event_time > now() - interval '1 hour'
GROUP BY 1
ORDER BY 1;
```
### Top Pages with Trend Sparklines (Table Panel)
Goal: Instead of just a list, show the page title and a "mini-graph" of its activity over the last hour inside the table.

Grafana Panel: Table (In the "Column Styles" settings, set the trend column to "Sparkline").

SQL Query:
```sql
SELECT 
    title, 
    count(*) as total_edits,
    -- This generates a string of counts for the sparkline transformation
    array_agg(count_per_min ORDER BY minute) as trend 
FROM (
    SELECT 
        title, 
        date_trunc('minute', event_time) as minute, 
        count(*) as count_per_min
    FROM wikipedia_changes
    WHERE event_time > now() - interval '1 hour'
    GROUP BY 1, 2
) sub
GROUP BY title
ORDER BY total_edits DESC
LIMIT 10;
```

### Editor "Newcomer" Ratio (Gauge / Stat Panel)
Goal: Identify if current activity is being driven by established users or brand-new accounts (potential spam wave).

Grafana Panel: Stat Panel (with "Color mode: Background" and a "Sparkline" enabled).

SQL Query:
```sql
SELECT 
    CASE 
        WHEN first_seen > now() - interval '1 hour' THEN 'New User'
        ELSE 'Returning User'
    END as user_type,
    count(*) as edit_count
FROM (
    SELECT "user", min(event_time) as first_seen
    FROM wikipedia_changes
    GROUP BY "user"
) u
JOIN wikipedia_changes w ON w.user = u.user
WHERE w.event_time > now() - interval '1 hour'
GROUP BY 1;
```


### Wiki "DNA" Signature (State Timeline)
Goal: Visualize the "rhythm" of different event types (edit, new, log) for the top 5 Wikis. It looks like a genetic sequence and shows how different wikis operate.

Grafana Panel: State Timeline.

SQL Query:
```sql
SELECT 
    event_time as time,
    wiki,
    type as state
FROM wikipedia_changes
WHERE wiki IN ('enwiki', 'dewiki', 'frwiki', 'wikidatawiki')
  AND event_time > now() - interval '30 minutes'
ORDER BY time ASC;
```

### The "Bot-Heavy" Leaderboard (Bar Gauge)
Goal: A ranked competition showing which Wikipedia projects are currently the most "automated."

Grafana Panel: Bar Gauge (Orientation: Horizontal, Display mode: Retro LCD or Gradient).

SQL Query:
```sql
SELECT 
    wiki,
    (COUNT(CASE WHEN bot = true THEN 1 END) * 100.0 / COUNT(*)) as bot_percentage
FROM wikipedia_changes
WHERE event_time > now() - interval '12 hours'
GROUP BY wiki
HAVING COUNT(*) > 100 -- Ignore low-volume wikis for statistical significance
ORDER BY bot_percentage DESC
LIMIT 15;
```

---


## Troubleshooting

| Problem | Fix |
|---|---|
| `stream-processor` exits immediately | Run `docker compose logs stream-processor` — it may need Kafka to be fully ready. Run `docker compose restart stream-processor`. |
| No data in PostgreSQL | Confirm `app` is running: `docker compose logs app`. Check that `KAFKA_BROKERS=kafka:9092` is set in `.env`. |
| Grafana shows "no data" | The pipeline needs a few minutes of data. Widen the time range in Grafana to **Last 1 hour**. |
| Kafka offset errors | Set `KAFKA_FAIL_ON_DATA_LOSS=false` in `.env` (already the default). For a full reset, delete `data/checkpoint/*` and restart. |
| Port `5432` or `3001` already in use | Stop the conflicting service, or change the host port in `docker-compose.yml`. |

---

## Stopping the Pipeline

```bash
docker compose down
```

To also remove all stored data volumes:

```bash
docker compose down -v
```
