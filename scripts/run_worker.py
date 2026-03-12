import json
import logging
import os
import sys
from pathlib import Path
from typing import Dict, List

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from scripts.bootstrap_project import bootstrap
from scripts.preflight_check import run_preflight
from scripts.run_pipeline import run_pipeline

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

DEFAULT_KEYWORD_LIMIT = 3


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
        raise RuntimeError(
            f"seed_keywords.json must define at least {limit} keyword(s) for scheduled worker runs."
        )
    return normalized[:limit]


def run_worker() -> Dict[str, object]:
    os.environ.setdefault("CONTENTOG_DISABLE_DB_FALLBACK", "true")
    limit = int(os.getenv("CONTENTOG_KEYWORD_LIMIT", str(DEFAULT_KEYWORD_LIMIT)))
    keywords = _load_seed_keywords(limit)

    preflight_report = run_preflight()
    bootstrap_report = bootstrap()
    pipeline_summary = run_pipeline(keywords=keywords, keyword_limit=limit)

    summary = {
        "keywords": keywords,
        "preflight": preflight_report,
        "bootstrap": bootstrap_report,
        "pipeline": {
            "total_articles": pipeline_summary.get("total_articles", 0),
            "total_topics": pipeline_summary.get("total_topics", 0),
            "total_topic_graph_nodes": pipeline_summary.get("total_topic_graph_nodes", 0),
            "total_topic_graph_edges": pipeline_summary.get("total_topic_graph_edges", 0),
            "runs": len(pipeline_summary.get("runs", [])),
        },
    }
    return summary


def _main() -> int:
    try:
        summary = run_worker()
        logger.info("Worker completed: %s", summary)
        return 0
    except Exception as exc:
        logger.exception("Worker failed: %s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(_main())
