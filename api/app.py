from collections import defaultdict
from typing import Any, Dict, List, Sequence, Tuple

from fastapi import FastAPI, HTTPException

from database.db_client import db_client

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
