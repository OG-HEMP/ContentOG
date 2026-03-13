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
    import uuid
    logger = logging.getLogger(__name__)
    
    orch = Orchestrator()
    try:
        # Create tasks in DB so UI sees them and we have their IDs
        task_ids = {}
        for keyword in keywords:
            task_id = str(uuid.uuid4())
            orch.db._execute(
                "INSERT INTO keyword_tasks (id, run_id, keyword, status) VALUES (%s, %s, %s, %s)",
                (task_id, run_id, keyword, "pending")
            )
            task_ids[keyword] = task_id
        
        logger.info(f"Starting localized background pipeline for run {run_id}")
        run_pipeline(keywords=keywords, keyword_limit=len(keywords), task_ids=task_ids)
        orch.complete_run(run_id)
    except Exception as exc:
        logger.error(f"Pipeline failed for {run_id}: {exc}")
        orch.complete_run(run_id, status="failed", error=str(exc))

@app.delete("/runs/{run_id}")
def delete_run(run_id: str) -> Dict[str, str]:
    from scripts.orchestrator import Orchestrator
    orch = Orchestrator()
    orch.delete_run(run_id)
    return {"message": f"Run {run_id} deleted successfully"}

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
        SELECT id, keyword, status, status_message, started_at, completed_at, error_message
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
def coverage(run_id: str = None) -> Dict[str, List[Dict[str, Any]]]:
    if not _table_exists("public.topic_domain_coverage"):
        return {}
    
    if run_id:
        # Filter coverage to topics that have articles in this specific run
        sql = """
            SELECT tdc.topic_id, tdc.domain, tdc.article_count, tdc.avg_rank
            FROM topic_domain_coverage tdc
            WHERE tdc.topic_id IN (
                SELECT DISTINCT at.topic_id
                FROM article_topics at
                JOIN articles a ON at.article_id = a.id
                JOIN keyword_tasks kt ON a.serp_keyword = kt.keyword
                WHERE kt.run_id = %s
            );
        """
        rows = _query_rows(sql, (run_id,))
    else:
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
def topic_graph(run_id: str = None) -> Dict[str, Sequence[Dict[str, Any]]]:
    if run_id:
        topics = _query_rows(
            """
            SELECT DISTINCT t.id AS topic_id, t.name AS topic_name
            FROM topics t
            JOIN article_topics at ON t.id = at.topic_id
            JOIN articles a ON at.article_id = a.id
            JOIN keyword_tasks kt ON a.serp_keyword = kt.keyword
            WHERE kt.run_id = %s;
            """,
            (run_id,)
        )
        relationships = _query_rows(
            """
            SELECT tr.topic_id, tr.related_topic_id, tr.weight
            FROM topic_relationships tr
            WHERE tr.topic_id IN (SELECT topic_id FROM (SELECT DISTINCT t2.id AS topic_id FROM topics t2 JOIN article_topics at2 ON t2.id = at2.topic_id JOIN articles a2 ON at2.article_id = a2.id JOIN keyword_tasks kt2 ON a2.serp_keyword = kt2.keyword WHERE kt2.run_id = %s) s)
              AND tr.related_topic_id IN (SELECT topic_id FROM (SELECT DISTINCT t3.id AS topic_id FROM topics t3 JOIN article_topics at3 ON t3.id = at3.topic_id JOIN articles a3 ON at3.article_id = a3.id JOIN keyword_tasks kt3 ON a3.serp_keyword = kt3.keyword WHERE kt3.run_id = %s) s2);
            """,
            (run_id, run_id)
        )
    else:
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
def list_articles(topic_id: str = None, run_id: str = None) -> List[Dict[str, Any]]:
    if not _table_exists("public.articles"):
        return []
    
    params = []
    where_clauses = []
    
    if topic_id:
        where_clauses.append("at.topic_id = %s")
        params.append(topic_id)
    
    if run_id:
        where_clauses.append("a.serp_keyword IN (SELECT keyword FROM keyword_tasks WHERE run_id = %s)")
        params.append(run_id)
        
    where_sql = " WHERE " + " AND ".join(where_clauses) if where_clauses else ""
    
    sql = f"""
        SELECT DISTINCT a.id, a.url, a.title, a.word_count, a.serp_rank, a.publish_date,
               substring(a.content from 1 for 200) as summary,
               split_part(a.url, '/', 3) as domain
        FROM articles a
        {"JOIN article_topics at ON a.id = at.article_id" if topic_id else ""}
        {where_sql}
        ORDER BY a.id DESC
        LIMIT 100;
    """
    rows = _query_rows(sql, tuple(params))
    return rows
