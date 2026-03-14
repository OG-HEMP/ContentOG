from collections import defaultdict
from typing import Any, Dict, List, Optional, Sequence, Tuple
import logging

from fastapi import FastAPI, HTTPException, BackgroundTasks

from pydantic import BaseModel
from database.db_client import db_client
from scripts.orchestrator import Orchestrator
from skills.strategy_generation.outline_generation import generate_topic_outline

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
    finally:
        db_client.release(conn)


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
        SELECT id, started_at, completed_at, status, keyword_count, article_count, cluster_count, target_domain
        FROM runs
        ORDER BY started_at DESC
        LIMIT 50;
        """
    )
    return rows


class RunCreate(BaseModel):
    keywords: List[str]
    target_domain: Optional[str] = None


from fastapi import BackgroundTasks

def run_pipeline_task(run_id: str, keywords: List[str], target_domain: Optional[str] = None):
    from scripts.run_pipeline import _run_single_keyword, _run_global_analysis
    from scripts.orchestrator import Orchestrator
    import uuid
    from concurrent.futures import ThreadPoolExecutor
    
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
        
        logger.info(f"Starting parallel background pipeline for run {run_id} with {len(keywords)} keywords")
        
        # Phase 1: Parallel research
        success_count = 0
        with ThreadPoolExecutor(max_workers=min(len(keywords), 10)) as executor:
            futures = [
                executor.submit(_run_single_keyword, kw, task_id=task_ids[kw], orch=orch, run_id=run_id, target_domain=target_domain)
                for kw in keywords
            ]
            for future in futures:
                try:
                    future.result()
                    success_count += 1
                except Exception as e:
                    logger.error(f"Keyword task failed in parallel execution: {e}")

        # Phase 2: Global analysis (Clustering, Topics, Strategy)
        if success_count > 0:
            logger.info(f"Research complete ({success_count}/{len(keywords)}). Starting global analysis...")
            _run_global_analysis(run_id, target_domain=target_domain)
        
        orch.complete_run(run_id)
    except Exception as exc:
        logger.error(f"Pipeline failed for {run_id}: {exc}")
        orch.complete_run(run_id, status="failed", error=str(exc))

@app.post("/tasks/{task_id}/retry")
def retry_task(task_id: str, background_tasks: BackgroundTasks) -> Dict[str, str]:
    from scripts.orchestrator import Orchestrator
    from scripts.run_pipeline import _run_single_keyword, _run_global_analysis
    orch = Orchestrator()
    
    task = _query_rows("SELECT run_id, keyword FROM keyword_tasks WHERE id = %s", (task_id,))
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    run_id = task[0]["run_id"]
    keyword = task[0]["keyword"]
    
    # Increment retry count for manual triggering
    orch.db.increment_task_retry_count(task_id)
    
    def retry_worker():
        try:
            logger.info(f"Manual retry START: {keyword} (Task: {task_id})")
            # Fetch target_domain from run metadata before running the keyword
            run_info = _query_rows("SELECT metadata FROM runs WHERE id = %s", (run_id,))
            td = run_info[0]["metadata"].get("target_domain") if run_info and run_info[0].get("metadata") else None
            _run_single_keyword(keyword, task_id=task_id, orch=orch, run_id=run_id, target_domain=td)
            # Re-run global analysis to update the artifacts for this run
            logger.info(f"Manual retry SUCCESS for {keyword}. Refreshing global analysis for run {run_id}")
            _run_global_analysis(run_id, target_domain=td)
        except Exception as e:
            logger.error(f"Manual retry FAILURE for {keyword}: {e}")
            pass # Already updated in DB by _run_single_keyword

    background_tasks.add_task(retry_worker)
    return {"message": f"Retry started for keyword: {keyword}"}

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
    run_id = orch.create_run(mode="ui-trigger", keyword_count=len(request.keywords), target_domain=request.target_domain)

    try:
        # Schedule the long-running task to run in the background
        background_tasks.add_task(run_pipeline_task, run_id, request.keywords, request.target_domain)
        
        return {"run_id": run_id, "status": "running", "keywords": request.keywords, "target_domain": request.target_domain}
    except Exception as exc:
        orch.complete_run(run_id, status="failed", error=str(exc))
        raise HTTPException(status_code=500, detail=f"Failed to dispatch tasks: {exc}")



@app.get("/runs/{run_id}/tasks")
def get_run_tasks(run_id: str) -> List[Dict[str, Any]]:
    if not _table_exists("public.keyword_tasks"):
        return []
    rows = _query_rows(
        """
        SELECT id, keyword, status, status_message, started_at, completed_at, error_message, retry_count
        FROM keyword_tasks
        WHERE run_id = %s
        ORDER BY created_at ASC;
        """,
        (run_id,)
    )
    return rows


@app.get("/topics")
def list_topics() -> List[Dict[str, Any]]:
    if not _table_exists("public.topics"):
        return []
    rows = _query_rows(
        """
        SELECT id, name, description
        FROM topics;
        """
    )
    return rows


@app.get("/coverage")
def coverage(run_id: str = None, topic_id: str = None):
    if not _table_exists("public.topic_domain_coverage"):
        # Return empty dict for grouped requests, empty list for single-topic requests
        return [] if topic_id else {}

    params: List[Any] = []
    where_clauses: List[str] = []

    if topic_id:
        where_clauses.append("tdc.topic_id = %s")
        params.append(topic_id)

    if run_id:
        where_clauses.append("""
            tdc.topic_id IN (
                SELECT DISTINCT at.topic_id
                FROM article_topics at
                JOIN articles a ON at.article_id = a.id
                JOIN keyword_tasks kt ON a.serp_keyword = kt.keyword
                WHERE kt.run_id = %s
            )
        """)
        params.append(run_id)

    where_sql = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""
    sql = f"""
        SELECT tdc.topic_id, t.name as topic_name, tdc.domain, tdc.article_count, tdc.avg_rank
        FROM topic_domain_coverage tdc
        JOIN topics t ON tdc.topic_id = t.id
        {where_sql};
    """
    rows = _query_rows(sql, tuple(params))

    # When requesting a specific topic, return a flat list directly
    if topic_id:
        return [
            {
                "topic_name": row.get("topic_name"),
                "domain": row.get("domain"),
                "article_count": row.get("article_count"),
                "avg_rank": row.get("avg_rank"),
            }
            for row in rows
        ]

    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        tid = str(row.get("topic_id"))
        grouped[tid].append(
            {
                "topic_name": row.get("topic_name"),
                "domain": row.get("domain"),
                "article_count": row.get("article_count"),
                "avg_rank": row.get("avg_rank"),
            }
        )
    return dict(grouped)


@app.get("/topic-graph")
def topic_graph(run_id: str = None) -> Dict[str, Sequence[Dict[str, Any]]]:
    if not _table_exists("public.topics"):
        return {"nodes": [], "edges": []}
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
def strategies(topic_id: str = None, run_id: str = None) -> List[Dict[str, Any]]:
    if not _table_exists("public.pillar_strategies"):
        return []
    params = []
    where_clauses = []
    
    if topic_id:
        where_clauses.append("topic_id = %s")
        params.append(topic_id)
        
    if run_id:
        # Filter strategies for topics that belong to the specified run
        where_clauses.append("""
            topic_id IN (
                SELECT DISTINCT at.topic_id
                FROM article_topics at
                JOIN articles a ON at.article_id = a.id
                JOIN keyword_tasks kt ON a.serp_keyword = kt.keyword
                WHERE kt.run_id = %s
            )
        """)
        params.append(run_id)

    where_sql = " WHERE " + " AND ".join(where_clauses) if where_clauses else ""
    
    try:
        sql = f"SELECT topic_id, title, description FROM pillar_strategies{where_sql};"
        rows = _query_rows(sql, tuple(params))
    except HTTPException:
        sql = f"""
            SELECT
                topic_id,
                strategy_details ->> 'title' AS title,
                strategy_details ->> 'angle' AS description
            FROM pillar_strategies
            {where_sql};
        """
        rows = _query_rows(sql, tuple(params))
    return rows

@app.get("/topics/{topic_id}/outline")
def get_outline(topic_id: str):
    outline = db_client.get_topic_outline(topic_id)
    if not outline:
        raise HTTPException(status_code=404, detail="Outline not found")
    return outline

@app.post("/topics/{topic_id}/outline")
async def create_outline(topic_id: str):
    # 1. Try to fetch existing outline
    existing = db_client.get_topic_outline(topic_id)
    if existing:
        return existing

    # 2. Fetch Topic Details
    topic_data = db_client._execute(
        "SELECT title, description FROM pillar_strategies WHERE topic_id = %s",
        (topic_id,),
        fetchone=True
    )
    if not topic_data:
        topic_data = db_client._execute(
            "SELECT name as title FROM topics WHERE id = %s",
            (topic_id,),
            fetchone=True
        )
        if not topic_data:
            raise HTTPException(status_code=404, detail="Topic cluster not found")
        topic_data["description"] = "Pillar content strategy"

    # 3. Fetch Articles for Context
    articles = db_client.fetch_articles_by_topic(topic_id, limit=5)
    
    # 4. Generate Outline
    try:
        outline = generate_topic_outline(
            topic_data["title"] or "Strategic Pillar",
            topic_data["description"] or "",
            articles
        )
        
        # 5. Save and return
        db_client.insert_topic_outline(topic_id, outline)
        return outline
    except Exception as exc:
        logger.error(f"Outline generation failed for topic {topic_id}: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


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
               CASE WHEN a.embedding IS NOT NULL THEN true ELSE false END as has_embedding,
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
