# Hosted Worker Runbook

## Runtime
- Target Python: `3.12+` (Container uses 3.12-slim)
- Preferred Entrypoint: `scripts/run_worker.py`

## Operational Modes
- **Preflight (`--mode preflight`)**: Validates secrets, database, and APIs.
- **Dispatch (`--mode dispatch`)**: Loads seeds, creates a Run record, and publishes tasks to Pub/Sub.
- **Keyword Task (`--mode keyword-task`)**: Processes a single keyword (requires `--keyword` and `CONTENTOG_TASK_ID` env var).
- **Standard (`--mode worker`)**: Runs the full sequential pipeline (legacy standby).

## Configuration
- Worker uses strict Secret Manager access in Cloud Mode (`GCP_PROJECT_ID` set).
- Tracking happens in `runs` and `keyword_tasks` tables in Supabase.
- Pub/Sub Topic: `contentog-tasks` (override via `CONTENTOG_PUBSUB_TOPIC`).

## Troubleshooting
- Check structured JSON logs in Cloud Logging.
- Ensure the Service Account has `Secret Manager Secret Accessor` and `Pub/Sub Publisher` roles.
