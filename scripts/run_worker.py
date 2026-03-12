import argparse
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from scripts.bootstrap_project import bootstrap
from scripts.preflight_check import run_preflight
from scripts.run_pipeline import run_pipeline
from config.config import settings
from scripts.orchestrator import Orchestrator

# Configure structured logging
logging.basicConfig(
    level=settings.log_level,
    format='{"time": "%(asctime)s", "level": "%(levelname)s", "name": "%(name)s", "message": "%(message)s"}'
)
logger = logging.getLogger(__name__)


def _load_seed_keywords(limit: int) -> List[str]:
    seed_path = ROOT_DIR / "data" / "seeds" / "seed_keywords.json"
    if not seed_path.exists():
        return ["content strategy"]
    with open(seed_path, "r", encoding="utf-8") as handle:
        keywords = json.load(handle)
    if not isinstance(keywords, list):
        return ["content strategy"]
    normalized = [str(keyword).strip() for keyword in keywords if str(keyword).strip()]
    if len(normalized) < limit:
        logger.warning("Fewer keywords provided (%d) than requested limit (%d)", len(normalized), limit)
    return normalized[:limit]


def run_worker(mode: str, keyword: Optional[str] = None) -> Dict[str, object]:
    """Execute the worker based on the specified mode."""
    logger.info("Starting worker in mode: %s", mode)
    settings.validate_config()
    
    if mode == "preflight":
        return {"preflight": run_preflight()}
    
    if mode == "bootstrap":
        return {"bootstrap": bootstrap()}
    
    if mode == "keyword-task":
        if not keyword:
            raise ValueError("Mode 'keyword-task' requires a --keyword argument")
        
        task_id = os.getenv("CONTENTOG_TASK_ID")
        logger.info("Executing pipeline for single keyword: %s (Task: %s)", keyword, task_id)
        
        orch = Orchestrator()
        if task_id:
            orch.db._execute(
                "UPDATE keyword_tasks SET status = 'running', started_at = %s WHERE id = %s",
                (datetime.utcnow().isoformat(), task_id)
            )

        try:
            pipeline = run_pipeline(keywords=[keyword], keyword_limit=1)
            if task_id:
                orch.db._execute(
                    "UPDATE keyword_tasks SET status = 'completed', completed_at = %s WHERE id = %s",
                    (datetime.utcnow().isoformat(), task_id)
                )
            return {"pipeline": pipeline}
        except Exception as exc:
            if task_id:
                orch.db._execute(
                    "UPDATE keyword_tasks SET status = 'failed', completed_at = %s, error_message = %s WHERE id = %s",
                    (datetime.utcnow().isoformat(), str(exc), task_id)
                )
            raise

    # Default pipeline core
    limit = settings.keyword_limit
    keywords = _load_seed_keywords(limit)
    
    if mode == "dispatch":
        orch = Orchestrator()
        run_id = orch.create_run(mode="dispatch", keyword_count=len(keywords))
        try:
            orch.publish_tasks(run_id, keywords)
            orch.complete_run(run_id)
            return {"run_id": run_id, "dispatched_keywords": keywords, "count": len(keywords)}
        except Exception as exc:
            orch.complete_run(run_id, status="failed", error=str(exc))
            raise

    if mode == "worker":
        # Full run includes preflight and bootstrap for safety in cloud environment
        preflight = run_preflight()
        boot = bootstrap()
        pipeline = run_pipeline(keywords=keywords, keyword_limit=limit)
        return {
            "preflight": preflight,
            "bootstrap": boot,
            "pipeline": pipeline
        }
    
    if mode == "single-run":
        # Just run the pipeline
        return {"pipeline": run_pipeline(keywords=keywords, keyword_limit=limit)}
        
    raise ValueError(f"Unknown mode: {mode}")


def _main() -> int:
    parser = argparse.ArgumentParser(description="ContentOG Cloud Worker")
    parser.add_argument(
        "--mode", 
        choices=["preflight", "bootstrap", "worker", "single-run", "dispatch", "keyword-task"],
        default="worker",
        help="Run mode for the worker"
    )
    parser.add_argument(
        "--keyword",
        help="Specific keyword to process (required for keyword-task mode)"
    )
    args = parser.parse_args()

    try:
        summary = run_worker(args.mode, args.keyword)
        logger.info("Worker completed successfully in mode: %s", args.mode)
        # Log summary as JSON for cloud logging
        print(json.dumps(summary))
        return 0
    except Exception as exc:
        logger.exception("Worker failed in mode %s: %s", args.mode, exc)
        return 1


if __name__ == "__main__":
    sys.exit(_main())
