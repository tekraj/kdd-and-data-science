# GitHub Copilot Instructions for wikipedia-data-processing

These instructions define how Copilot should generate, edit, and review code in this project.

## 1) Project Context

This repository contains a real-time Wikipedia pipeline:

1. `data-ingestion` (Node.js + TypeScript): consumes Wikimedia SSE and publishes to Kafka.
2. `stream-processor` (PySpark): reads Kafka, transforms events, and writes to PostgreSQL.
3. `ml-models` (FastAPI + PySpark): trains/listens for retrain events and serves insights.
4. Infrastructure: Docker Compose, Kafka, Zookeeper, PostgreSQL, Grafana.

When making changes, preserve this architecture and avoid coupling services unnecessarily.

## 2) Core Engineering Principles

1. Make minimal, focused changes that directly solve the task.
2. Keep backward compatibility for event schema, Kafka topics, DB columns, and API responses unless explicitly requested.
3. Prefer explicit, readable code over clever shortcuts.
4. Fail fast on misconfiguration; do not silently swallow critical errors.
5. Do not hardcode secrets, credentials, hostnames, or absolute local paths.

## 3) Data Contract Safety (Critical)

Any change that touches event parsing, transformation, or writes must preserve contract consistency across:

1. `data-ingestion/src/types/wikimedia.ts`
2. `stream-processor/app/spark/schema.py`
3. `stream-processor/app/data_preprocessing/*`
4. `stream-processor/app/db/writer.py`
5. `ml-models/app/spark/event_parser.py` and related ML listeners

Rules:

1. Keep field names aligned end-to-end (`id`, `type`, `title`, `timestamp`, `user`, `bot`, `meta.*`, `wiki`, `event_time`).
2. Do not rename or remove persisted DB columns without a migration strategy.
3. For new fields, make additions additive and nullable by default.
4. Document any intentional contract change in the relevant README or `documents/` guide.

## 4) Language-Specific Standards

### TypeScript (`data-ingestion`)

1. Use strict typing; avoid `any` unless strongly justified.
2. Use ESM imports consistently (`.js` extension style in TS source as currently used).
3. Validate environment variables at startup in config modules.
4. Keep SSE ingestion logic resilient to reconnects and malformed messages.
5. Use existing scripts and toolchain:
	- `pnpm build`
	- `pnpm typecheck`
	- `pnpm lint`
	- `pnpm format:check`

### Python (`stream-processor`, `ml-models`)

1. Follow PEP 8 and keep functions small and composable.
2. Add type hints for new/changed public functions.
3. Keep Spark transformations deterministic and idempotent where possible.
4. Prefer batch-safe operations and avoid driver-heavy logic in hot paths.
5. Handle Spark/Kafka/Postgres transient failures with bounded retries when appropriate.

## 5) Streaming and Reliability Standards

1. Respect checkpoint behavior:
	- Do not delete checkpoints by default.
	- Use reset flags (such as `RESET_CHECKPOINT_ON_START`) for recovery only.
2. Preserve current offset handling behavior (`KAFKA_STARTING_OFFSETS`, `KAFKA_FAIL_ON_DATA_LOSS`) unless task requires change.
3. Avoid duplicate amplification:
	- Keep de-dup/watermark behavior unless explicitly revisited.
4. Ensure graceful shutdown for long-running consumers/producers.
5. Keep logs actionable (include component and failure context).

## 6) Database and Query Standards

1. Use parameterized SQL or safe bulk helpers (for example `execute_values`).
2. Do not use `SELECT *` in application logic where stable schemas are expected.
3. Keep write paths efficient for micro-batches.
4. Maintain compatibility with existing Grafana dashboards and SQL panels where feasible.

## 7) API Standards (`ml-models`)

1. Keep endpoint contracts stable (`/power-editors`, `/power-editors/raw`, etc.).
2. Return clear HTTP status codes and concise error messages.
3. Do not block API startup on optional background listeners unless required.
4. Keep response payloads JSON-serializable and deterministic.

## 8) Docker and Environment Standards

1. Keep Docker Compose service names and inter-service DNS stable unless explicitly requested.
2. Use `.env.example` as the source of truth for required environment variables.
3. If adding env vars:
	- add them to `.env.example`
	- document defaults and purpose
	- keep sensible local-development defaults
4. Avoid adding heavyweight dependencies without clear need.

## 9) Testing and Validation Expectations

Before finalizing changes, run the smallest relevant checks:

1. TypeScript changes:
	- `pnpm typecheck`
	- `pnpm lint`
	- `pnpm build`
2. Python changes:
	- run targeted module import/syntax checks
	- run available tests if present
3. Integration-impacting changes:
	- verify Docker Compose still builds
	- verify startup path for affected service

If a check cannot be run, clearly state why and what remains unverified.

## 10) Documentation Standards

1. Update docs when changing behavior, config, schema, or operations.
2. Keep examples copy-pastable and Linux-friendly.
3. Prefer concise runbooks over long narrative explanations.

## 11) What Copilot Should Avoid

1. Do not introduce breaking changes without explicit instruction.
2. Do not rewrite large files for minor tasks.
3. Do not add dead code, placeholder TODO blocks, or mock logic in production paths.
4. Do not suppress exceptions without logging and rationale.
5. Do not commit generated secrets, credentials, or local artifacts.

## 12) Preferred Change Style

1. Keep PR-sized changes coherent and reviewable.
2. Mention assumptions explicitly in comments or docstrings when non-obvious.
3. Add small, meaningful comments only where intent is not obvious.
4. Preserve existing naming and module layout unless there is a strong reason to refactor.

When in doubt, prioritize reliability of the live stream pipeline and compatibility with existing dashboards and consumers.
