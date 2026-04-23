# Lab Task: Real-Time Entity Trend Analysis

## 1. Goal

Build a real-time analytics feature that extracts Named Entities from Wikipedia page titles and identifies the **top 5 trending entities** in a **rolling 10-minute window**.

Target entity types:

- `PERSON`
- `ORG`
- `GPE` (Geo-Political Entity / Location)

The final output should power a dashboard-ready Gold layer table in PostgreSQL.

---

## 2. Context

The streaming pipeline already ingests and processes Wikipedia edit events. For this lab, students will extend the stream processing layer by adding an NLP-based transformation and a windowed aggregation.

Source field:

- `title` from the streamed Wikipedia records (examples: `Elon Musk`, `Microsoft Azure`, `Paris Olympics 2026`)

Additional filter requirement:

- Include only **human-driven edits** (`bot = false`).

---

## 3. Student Sub-Tasks

### Task A: NER Transformation

Create a transformation function that extracts entities from the `title` field.

#### Input

- `title` (string)

#### Processing Requirements

1. Use an NLP library (for example, spaCy) to detect entities in each title.
2. Keep only entities with labels: `PERSON`, `ORG`, `GPE`.
3. Handle titles that contain no valid entity.

#### Constraint

Many Wikipedia titles are not named entities (for example, `List of numbers`).
Students must filter out:

- null/empty titles
- non-entity outputs
- entity types outside `PERSON`, `ORG`, `GPE`

#### Expected Transformation Output

- `entity_name` (text)
- `entity_type` (one of `PERSON`, `ORG`, `GPE`)

---

### Task B: Windowed Aggregation

Using Spark Structured Streaming, compute entity mention frequencies.

#### Aggregation Requirements

1. Use event-time windowing on event timestamp (`event_time`).
2. Window length: **10 minutes**.
3. Slide interval: **2 minutes**.
4. Group by:
	- window
	- `entity_name`
	- `entity_type`
5. Filter source records where `bot = false` before aggregation.

#### Output Metric

- `mention_count` = count of occurrences per (`window`, `entity_name`, `entity_type`)

#### Trending Requirement

For each window, return the **top 5 entities** by `mention_count`.

---

### Task C: Gold Layer Persistence

Store the final windowed top entities in PostgreSQL table `trending_entities`.

Use the following schema:

```sql
CREATE TABLE trending_entities (
	 window_start TIMESTAMP,
	 window_end TIMESTAMP,
	 entity_name TEXT,
	 entity_type TEXT,
	 mention_count INTEGER,
	 PRIMARY KEY (window_start, entity_name)
);
```

#### Write Requirements

1. Persist only the final top-5 rows per window.
2. Ensure idempotent/upsert-safe behavior for repeated micro-batch execution.
3. Keep data types consistent with the schema.

---

## 4. Suggested Implementation Steps

1. Read stream from curated event source (where `title`, `bot`, and `event_time` are available).
2. Add a UDF or map step for NER extraction.
3. Explode/extract valid entities into rows.
4. Filter `bot = false` and invalid entities.
5. Apply sliding window aggregation.
6. Rank entities by `mention_count` per window and keep top 5.
7. Write results into `trending_entities` table.

---
