import importlib.util
import json
import logging
import os
import sys
from pathlib import Path
from typing import Dict, List


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from database.db_client import db_client

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

REQUIRED_ENV_VARS = ["SUPABASE_URL", "SUPABASE_KEY", "OPENAI_API_KEY", "SERP_API_KEY"]
REQUIRED_TABLES = [
    "articles",
    "keywords",
    "paa_questions",
    "topics",
    "article_topics",
    "pillar_strategies",
    "cluster_articles",
]
REQUIRED_DEPENDENCIES = {
    "sentence-transformers": "sentence_transformers",
    "hdbscan": "hdbscan",
    "spacy": "spacy",
    "requests": "requests",
    "psycopg2": "psycopg2",
}
SEED_KEYWORDS_FILE = ROOT_DIR / "data" / "seeds" / "seed_keywords.json"


def _check_python_version() -> None:
    if sys.version_info < (3, 10):
        raise RuntimeError("Python 3.10+ is required.")
    logger.info("Python version OK")


def _check_environment_variables() -> None:
    missing = [name for name in REQUIRED_ENV_VARS if not (os.getenv(name) or "").strip()]
    if missing:
        raise RuntimeError(f"Missing required environment variables: {', '.join(missing)}")
    logger.info("Environment variables OK")


def _check_dependencies() -> None:
    missing: List[str] = []
    for package_name, module_name in REQUIRED_DEPENDENCIES.items():
        if importlib.util.find_spec(module_name) is None:
            missing.append(package_name)
    if missing:
        raise RuntimeError(f"Dependency missing: {', '.join(missing)}")
    logger.info("Dependencies OK")


def _check_database_connectivity() -> None:
    conn = db_client.connect()
    if conn is None:
        raise RuntimeError("Supabase connection failed")
    logger.info("Supabase connection OK")


def _check_pgvector_extension() -> None:
    rows = db_client.query("SELECT extname FROM pg_extension WHERE extname='vector';")
    if not rows:
        raise RuntimeError("pgvector extension not installed")
    logger.info("pgvector extension OK")


def _check_required_tables() -> None:
    rows = db_client.query(
        """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public';
        """
    )
    existing = {row.get("table_name") for row in rows}
    missing = [table for table in REQUIRED_TABLES if table not in existing]
    if missing:
        raise RuntimeError(f"Required table(s) missing: {', '.join(missing)}")
    logger.info("Tables verified")


def _check_seed_keywords() -> None:
    if not SEED_KEYWORDS_FILE.exists():
        raise RuntimeError(f"Seed keyword file missing: {SEED_KEYWORDS_FILE}")

    with SEED_KEYWORDS_FILE.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    if isinstance(payload, list):
        keywords = [str(item).strip() for item in payload if str(item).strip()]
    elif isinstance(payload, dict):
        raw_keywords = payload.get("keywords", [])
        keywords = [str(item).strip() for item in raw_keywords if str(item).strip()]
    else:
        keywords = []

    if not keywords:
        raise RuntimeError("No seed keywords found")
    logger.info("Seed keywords loaded")


def _check_serp_api() -> None:
    import requests

    api_key = os.getenv("SERP_API_KEY", "").strip()
    response = requests.get(
        "https://serpapi.com/search.json",
        params={"engine": "google", "q": "content strategy", "api_key": api_key, "num": 1},
        timeout=20,
    )
    if response.status_code != 200:
        raise RuntimeError("SERP API validation failed")

    data = response.json()
    if data.get("error") or not isinstance(data.get("organic_results"), list):
        raise RuntimeError("SERP API validation failed")
    logger.info("SERP API reachable")


def run_preflight() -> Dict[str, str]:
    _check_python_version()
    _check_environment_variables()
    _check_dependencies()
    _check_database_connectivity()
    _check_pgvector_extension()
    _check_required_tables()
    _check_seed_keywords()
    _check_serp_api()

    print("## ContentOG Preflight Report")
    print("Python version OK")
    print("Dependencies OK")
    print("Environment variables OK")
    print("Supabase connection OK")
    print("pgvector extension OK")
    print("Tables verified")
    print("Seed keywords loaded")
    print("SERP API reachable")
    print("All checks passed.")

    return {"status": "ok"}


def _main() -> int:
    try:
        run_preflight()
        return 0
    except Exception as exc:
        logger.error("Preflight failed: %s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(_main())
