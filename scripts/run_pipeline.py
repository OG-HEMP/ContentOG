import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from agents.cluster_agent.cluster_agent import ClusterAgent
from agents.crawl_agent.crawl_agent import CrawlAgent
from agents.embedding_agent.embedding_agent import EmbeddingAgent
from agents.paa_agent.paa_agent import PaaAgent
from agents.serp_agent.serp_agent import SerpAgent
from agents.strategy_agent.strategy_agent import StrategyAgent
from agents.topic_agent.topic_agent import TopicAgent
from config.config import settings
from scripts.preflight_check import run_preflight

# Configure structured logging (consistent with worker/orchestrator)
logging.basicConfig(
    level=settings.log_level,
    format='{"time": "%(asctime)s", "level": "%(levelname)s", "name": "%(name)s", "message": "%(message)s"}'
)
logger = logging.getLogger(__name__)

_DEFAULT_KEYWORD = "content strategy"


def _load_seed_keywords(default: str = _DEFAULT_KEYWORD, limit: Optional[int] = None) -> List[str]:
    if limit is None:
        limit = settings.keyword_limit
    seed_path = ROOT_DIR / "data" / "seeds" / "seed_keywords.json"
    if not seed_path.exists():
        return [default]
    with open(seed_path, "r", encoding="utf-8") as handle:
        keywords = json.load(handle)
    if not isinstance(keywords, list):
        return [default]
    normalized = [str(keyword).strip() for keyword in keywords if str(keyword).strip()]
    if not normalized:
        return [default]
    if len(normalized) < limit:
        raise RuntimeError(
            f"Seed keyword file must contain at least {limit} keyword(s); found {len(normalized)}."
        )
    return normalized[:limit]


def _run_single_keyword(keyword: str, task_id: Optional[str] = None, orch: Optional[Any] = None, run_id: Optional[str] = None, target_domain: Optional[str] = None) -> Dict[str, object]:
    max_retries = 2
    last_exc = None
    
    for attempt in range(max_retries + 1):
        context: Dict[str, object] = {"keyword": keyword, "run_id": run_id, "target_domain": target_domain}
        
        def update_progress(msg: str, status: str = "running"):
            if task_id and orch:
                orch.update_task(task_id, status, msg)
            logger.info(f"[{keyword}] {msg}")

        try:
            if attempt > 0:
                update_progress(f"Retrying (Attempt {attempt}/{max_retries})...")
                if task_id and orch:
                    orch.db.increment_task_retry_count(task_id)

            update_progress("Finding SERP results...")
            context = SerpAgent().run(context)
            
            update_progress("Extracting PAA questions...")
            context = PaaAgent().run(context)
            
            update_progress("Scraping article content...")
            context = CrawlAgent().run(context)
            
            update_progress("Generating embeddings...")
            context = EmbeddingAgent().run(context)
            
            if task_id and orch:
                orch.update_task(task_id, "completed", "Keyword research complete.")
                
            return context
        except Exception as exc:
            last_exc = exc
            logger.error(f"Attempt {attempt} failed for keyword {keyword}: {exc}")
            if attempt < max_retries:
                # Small exponential backoff
                import time
                time.sleep(2 ** attempt)
                continue
            else:
                if task_id and orch:
                    orch.update_task(task_id, "failed", str(exc))
                raise exc

def _run_global_analysis(run_id: str, context_list: List[Dict[str, Any]] = None, target_domain: Optional[str] = None):
    """Run global steps like clustering and strategy generation for a run."""
    from scripts.orchestrator import Orchestrator
    orch = Orchestrator()
    
    logger.info(f"Starting global analysis for run: {run_id}")
    
    # Ideally we'd aggregate context here, but agents usually pull from DB using run_id
    # We pass a generic context that includes the run_id and target_domain
    global_context = {"run_id": run_id, "target_domain": target_domain}
    
    try:
        logger.info("Analyzing topic clusters...")
        global_context = ClusterAgent().run(global_context)
        
        logger.info("Mapping semantic topics...")
        global_context = TopicAgent().run(global_context)
        
        logger.info("Generating strategy insights...")
        global_context = StrategyAgent().run(global_context)
        
        logger.info(f"Global analysis complete for run: {run_id}")
        return global_context
    except Exception as exc:
        logger.error(f"Global analysis failed for run {run_id}: {exc}")
        raise exc


def run_pipeline(keywords: Optional[List[str]] = None, keyword_limit: Optional[int] = None, task_ids: Optional[Dict[str, str]] = None) -> Dict[str, object]:
    """Execute the recovery/discovery pipeline for given keywords."""
    from scripts.orchestrator import Orchestrator
    orch = Orchestrator()
    
    run_preflight()
    limit = keyword_limit if keyword_limit is not None else settings.keyword_limit
    selected_keywords = keywords or _load_seed_keywords(limit=limit)
    logger.info("Starting ContentOG discovery pipeline for %d keyword(s)", len(selected_keywords))

    runs_data: List[Dict[str, object]] = []
    for keyword in selected_keywords:
        task_id = task_ids.get(keyword) if task_ids else None
        logger.info("Running pipeline for keyword: %s (Task: %s)", keyword, task_id)
        
        try:
            context = _run_single_keyword(keyword, task_id=task_id, orch=orch)
            # Add simple run metadata for the summary
            runs_data.append({
                "keyword": keyword,
                "articles_count": len(context.get("articles", [])),
                "topics_count": len(context.get("topics", [])),
            })
        except Exception as exc:
            logger.error(f"Pipeline research failed for keyword {keyword}: {exc}")
            continue

    # Now run global analysis if we have a run_id (which we usually do in orch context)
    # For CLI runs, run_id might need to be fetched or created
    run_id = getattr(orch, "current_run_id", None)
    if not run_id:
        # Fallback to creating a local run record if needed, but usually orch handles this
        pass

    global_context = _run_global_analysis(run_id) if run_id else {}
    
    summary = {
        "keywords": selected_keywords,
        "runs": runs_data,
        "total_articles": sum(int(r["articles_count"]) for r in runs_data),
        "total_topics": sum(int(r["topics_count"]) for r in runs_data),
    }
    logger.info("Pipeline execution complete for %d keyword(s)", len(selected_keywords))
    return summary


def _main() -> int:
    try:
        summary = run_pipeline()
        logger.info(
            "Summary: keywords=%d total_articles=%d total_topics=%d",
            len(summary.get("keywords", [])),
            summary.get("total_articles", 0),
            summary.get("total_topics", 0),
        )
        return 0
    except Exception as exc:
        logger.exception("Pipeline failed: %s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(_main())
