from collections import defaultdict
from typing import Any, Dict, List, Sequence, Tuple

from fastapi import FastAPI, HTTPException

from pydantic import BaseModel
from database.db_client import db_client
from scripts.orchestrator import Orchestrator

app = FastAPI(title="ContentOG API")


def _query_rows(sql: str, params: Tuple[Any, ...] = ()) -> List[Dict[str, Any]]:
    conn = db_client.connect()
    if conn is None:
        raise HTTPException(status_code=500, detail="Database unavailable")
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
            columns = [col[0] for col in cur.description]
        return [dict(zip(columns, row)) for row in rows]
    except HTTPException:
        raise
    except Exception as exc:
        try:
            conn.rollback()
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f"Database query failed: {exc}") from exc


def _table_exists(table_name: str) -> bool:
    rows = _query_rows("SELECT to_regclass(%s) AS table_name;", (table_name,))
    return bool(rows and rows[0].get("table_name"))


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.get("/runs")
def list_runs() -> List[Dict[str, Any]]:
    if not _table_exists("public.runs"):
        return []
    rows = _query_rows(
        """
        SELECT id, started_at, completed_at, status, keyword_count, article_count, cluster_count
        FROM runs
        ORDER BY started_at DESC
        LIMIT 50;
        """
    )
    return rows


class RunCreate(BaseModel):
    keywords: List[str]


from fastapi import BackgroundTasks

def run_pipeline_task(run_id: str, keywords: List[str]):
    from scripts.run_pipeline import run_pipeline
    from scripts.orchestrator import Orchestrator
    import logging
    logger = logging.getLogger(__name__)
    
    orch = Orchestrator()
    try:
        # Create tasks in DB so UI sees them
        for keyword in keywords:
            orch.db._execute(
                "INSERT INTO keyword_tasks (id, run_id, keyword, status) VALUES (gen_random_uuid(), %s, %s, %s)",
                (run_id, keyword, "pending")
            )
        
        logger.info(f"Starting localized background pipeline for run {run_id}")
        run_pipeline(keywords=keywords, keyword_limit=len(keywords))
        orch.complete_run(run_id)
    except Exception as exc:
        logger.error(f"Pipeline failed for {run_id}: {exc}")
        orch.complete_run(run_id, status="failed", error=str(exc))

@app.post("/runs")
def create_run(request: RunCreate, background_tasks: BackgroundTasks) -> Dict[str, Any]:
    if not request.keywords:
        raise HTTPException(status_code=400, detail="Keywords list cannot be empty")

    orch = Orchestrator()
    run_id = orch.create_run(mode="ui-trigger", keyword_count=len(request.keywords))

    try:
        # Schedule the long-running task to run in the background
        background_tasks.add_task(run_pipeline_task, run_id, request.keywords)
        
        return {"run_id": run_id, "status": "running", "keywords": request.keywords}
    except Exception as exc:
        orch.complete_run(run_id, status="failed", error=str(exc))
        raise HTTPException(status_code=500, detail=f"Failed to dispatch tasks: {exc}")



@app.get("/runs/{run_id}/tasks")
def get_run_tasks(run_id: str) -> List[Dict[str, Any]]:
    if not _table_exists("public.keyword_tasks"):
        return []
    rows = _query_rows(
        """
        SELECT id, keyword, status, started_at, completed_at, error_message
        FROM keyword_tasks
        WHERE run_id = %s
        ORDER BY created_at ASC;
        """,
        (run_id,)
    )
    return rows


@app.get("/topics")
def list_topics() -> List[Dict[str, Any]]:
    rows = _query_rows(
        """
        SELECT id, name, description
        FROM topics;
        """
    )
    return rows


@app.get("/coverage")
def coverage() -> Dict[str, List[Dict[str, Any]]]:
    if not _table_exists("public.topic_domain_coverage"):
        return {}
    rows = _query_rows(
        """
        SELECT topic_id, domain, article_count, avg_rank
        FROM topic_domain_coverage;
        """
    )
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        topic_id = str(row.get("topic_id"))
        grouped[topic_id].append(
            {
                "domain": row.get("domain"),
                "article_count": row.get("article_count"),
                "avg_rank": row.get("avg_rank"),
            }
        )
    return dict(grouped)


@app.get("/topic-graph")
def topic_graph() -> Dict[str, Sequence[Dict[str, Any]]]:
    topics = _query_rows(
        """
        SELECT id AS topic_id, name AS topic_name
        FROM topics;
        """
    )
    if _table_exists("public.topic_relationships"):
        relationships = _query_rows(
            """
            SELECT topic_id, related_topic_id, weight
            FROM topic_relationships;
            """
        )
    else:
        relationships = []
    edges = [
        {
            "source": row.get("topic_id"),
            "target": row.get("related_topic_id"),
            "weight": row.get("weight"),
        }
        for row in relationships
    ]
    return {"nodes": topics, "edges": edges}


@app.get("/strategies")
def strategies() -> List[Dict[str, Any]]:
    try:
        rows = _query_rows(
            """
            SELECT topic_id, title, description
            FROM pillar_strategies;
            """
        )
    except HTTPException:
        # Backward-compatible read for current schema where strategy payload is JSONB.
        rows = _query_rows(
            """
            SELECT
                topic_id,
                strategy_details ->> 'title' AS title,
                strategy_details ->> 'angle' AS description
            FROM pillar_strategies;
            """
        )
    return rows


@app.get("/articles")
def list_articles(topic_id: str = None) -> List[Dict[str, Any]]:
    if not _table_exists("public.articles"):
        return []
    
    if topic_id:
        sql = """
            SELECT a.id, a.url, a.title, a.word_count, a.serp_rank, a.publish_date,
                   substring(a.content from 1 for 200) as summary,
                   split_part(a.url, '/', 3) as domain
            FROM articles a
            JOIN article_topics at ON a.id = at.article_id
            WHERE at.topic_id = %s
            ORDER BY a.created_at DESC
            LIMIT 100;
        """
        rows = _query_rows(sql, (topic_id,))
    else:
        sql = """
            SELECT id, url, title, word_count, serp_rank, publish_date,
                   substring(content from 1 for 200) as summary,
                   split_part(url, '/', 3) as domain
            FROM articles
            ORDER BY created_at DESC
            LIMIT 100;
        """
        rows = _query_rows(sql)
    return rows
