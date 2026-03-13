import json
import logging
import sys
from pathlib import Path
from typing import Dict

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from config.config import settings
from database.db_client import db_client

# Configure structured logging (consistent with worker/preflight)
logging.basicConfig(
    level=settings.log_level,
    format='{"time": "%(asctime)s", "level": "%(levelname)s", "name": "%(name)s", "message": "%(message)s"}'
)
logger = logging.getLogger(__name__)


def bootstrap() -> Dict[str, int]:
    """Verify DB connection, initialize schema, and load seed keywords."""
    logger.info("Initializing ContentOG project")
    conn = db_client.connect()
    if conn is None:
        raise RuntimeError("Live database connection is required for bootstrap.")

    try:
        schema_path = ROOT_DIR / "database" / "schema.sql"
        with open(schema_path, "r", encoding="utf-8") as schema_file:
            schema_sql = schema_file.read()
        with conn.cursor() as cur:
            cur.execute(schema_sql)
            conn.commit()
        logger.info("Schema initialization complete")
    finally:
        db_client.release(conn)

    seed_path = ROOT_DIR / "data" / "seeds" / "seed_keywords.json"
    loaded = []
    if seed_path.exists():
        with open(seed_path, "r", encoding="utf-8") as handle:
            keywords = json.load(handle)
        for keyword in keywords:
            db_client.get_or_create_keyword(str(keyword))
            loaded.append(keyword)

    logger.info("Loaded %d seed keywords", len(loaded))
    return {"seed_keywords_loaded": len(loaded)}


def _main() -> int:
    try:
        result = bootstrap()
        logger.info("Bootstrap summary: %s", result)
        return 0
    except Exception as exc:
        logger.exception("Bootstrap failed: %s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(_main())
