import json
import logging
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional

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


def _run_single_keyword(keyword: str) -> Dict[str, object]:
    context: Dict[str, object] = {"keyword": keyword}
    context = SerpAgent().run(context)
    context = PaaAgent().run(context)
    context = CrawlAgent().run(context)
    context = EmbeddingAgent().run(context)
    context = ClusterAgent().run(context)
    context = TopicAgent().run(context)
    context = StrategyAgent().run(context)
    return context


def run_pipeline(keywords: Optional[List[str]] = None, keyword_limit: Optional[int] = None) -> Dict[str, object]:
    """Execute the recovery/discovery pipeline for given keywords."""
    run_preflight()
    limit = keyword_limit if keyword_limit is not None else settings.keyword_limit
    selected_keywords = keywords or _load_seed_keywords(limit=limit)
    logger.info("Starting ContentOG discovery pipeline for %d keyword(s)", len(selected_keywords))

    runs: List[Dict[str, object]] = []
    for keyword in selected_keywords:
        logger.info("Running pipeline for keyword: %s", keyword)
        context = _run_single_keyword(keyword)
        strategy = context.get("strategy", {}) if isinstance(context.get("strategy"), dict) else {}
        topic_graph = strategy.get("industry_topic_graph", {}) if isinstance(strategy.get("industry_topic_graph"), dict) else {}
        coverage = strategy.get("topic_coverage_by_domain", []) if isinstance(strategy.get("topic_coverage_by_domain"), list) else []
        runs.append(
            {
                "keyword": keyword,
                "articles_count": len(context.get("articles", [])),
                "topics_count": len(context.get("topics", [])),
                "cluster_count": len(context.get("clustered_titles", {})),
                "topic_graph_nodes": len(topic_graph.get("nodes", [])) if isinstance(topic_graph, dict) else 0,
                "topic_graph_edges": len(topic_graph.get("edges", [])) if isinstance(topic_graph, dict) else 0,
                "domain_coverage_topics": len(coverage),
                "context": context,
            }
        )

    summary = {
        "keywords": selected_keywords,
        "runs": runs,
        "total_articles": sum(int(run["articles_count"]) for run in runs),
        "total_topics": sum(int(run["topics_count"]) for run in runs),
        "total_topic_graph_nodes": sum(int(run["topic_graph_nodes"]) for run in runs),
        "total_topic_graph_edges": sum(int(run["topic_graph_edges"]) for run in runs),
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
