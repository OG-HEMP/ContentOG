# Hosted Worker Runbook

## Runtime
- Target Python: `3.11+` (`config/runtime.txt`)
- Install dependencies: `python -m pip install -r requirements.txt`

## Required startup sequence
### Manual sequence
1. `python scripts/preflight_check.py`
2. `python scripts/bootstrap_project.py`
3. `python scripts/run_pipeline.py`

### Scheduled worker entrypoint
- `python scripts/run_worker.py`

## Notes
- Worker defaults to strict DB mode (`CONTENTOG_DISABLE_DB_FALLBACK=true`).
- Worker runs a fixed 3-keyword sample from `data/seeds/seed_keywords.json` by default.
- Override keyword count with `CONTENTOG_KEYWORD_LIMIT`.
