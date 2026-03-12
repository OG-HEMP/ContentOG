import logging
import os
import sys
from pathlib import Path
from typing import Dict, List

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from database.db_client import db_client
from skills.embeddings.embeddings import generate_embedding
from skills.paa_extraction.paa_extraction import extract_paa_questions
from skills.serp_discovery.serp_discovery import discover_serp_urls
from skills.web_crawling.web_crawling import crawl_page

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

REQUIRED_ENV_VARS = ["POSTGRESQL", "OPENAI_API_KEY", "SERP_API_KEY"]
REQUIRED_TABLES = [
    "articles",
    "keywords",
    "paa_questions",
    "topics",
    "article_topics",
    "pillar_strategies",
    "cluster_articles",
]


def _check_env() -> Dict[str, bool]:
    result = {}
    for key in REQUIRED_ENV_VARS:
        result[key] = bool((os.getenv(key) or "").strip())
    missing = [key for key, present in result.items() if not present]
    if missing:
        raise RuntimeError(f"Missing required env var(s): {', '.join(missing)}")
    return result


def _check_database() -> Dict[str, int]:
    conn = db_client.connect()
    if conn is None:
        raise RuntimeError("Database connection failed.")

    tables = db_client.query(
        """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema='public';
        """
    )
    existing = {row.get("table_name") for row in tables}
    missing = [name for name in REQUIRED_TABLES if name not in existing]
    if missing:
        raise RuntimeError(f"Missing database tables: {', '.join(missing)}")

    extension_rows = db_client.query("SELECT extname FROM pg_extension WHERE extname='vector';")
    if not extension_rows:
        raise RuntimeError("pgvector extension 'vector' is not installed.")

    return {"table_count": len(existing)}


def _check_providers() -> Dict[str, int]:
    serp_results = discover_serp_urls("content strategy")
    if not serp_results:
        raise RuntimeError("SerpApi health check returned no SERP results.")

    questions = extract_paa_questions("content strategy")
    if not questions:
        raise RuntimeError("SerpApi health check returned no PAA questions.")

    vector = generate_embedding("contentog preflight check")
    if not vector:
        raise RuntimeError("OpenAI embeddings health check returned empty vector.")

    crawled = 0
    for item in serp_results[:3]:
        try:
            payload = crawl_page(item["url"])
            if payload.get("content"):
                crawled += 1
                break
        except Exception:
            continue
    if crawled == 0:
        raise RuntimeError("Web crawling health check failed for top SERP URLs.")

    return {"serp_results": len(serp_results), "paa_questions": len(questions), "embedding_dimensions": len(vector)}


def run_preflight() -> Dict[str, Dict[str, int]]:
    env_status = _check_env()
    db_status = _check_database()
    provider_status = _check_providers()
    return {
        "env": {key: int(value) for key, value in env_status.items()},
        "database": db_status,
        "providers": provider_status,
    }


def _main() -> int:
    try:
        report = run_preflight()
        logger.info("Preflight succeeded: %s", report)
        return 0
    except Exception as exc:
        logger.exception("Preflight failed: %s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(_main())
