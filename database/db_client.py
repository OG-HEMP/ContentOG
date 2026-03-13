import logging
import os
import re
import json
from typing import Any, Dict, List, Optional

from config.config import settings
from database.db_connection import get_db

logger = logging.getLogger(__name__)


class DBClient:
    """Shared database utility with idempotent helpers and safe fallbacks."""

    def __init__(self) -> None:
        self._pool = None
        self._memory: Dict[str, List[Dict[str, Any]]] = {
            "keywords": [],
            "articles": [],
            "paa_questions": [],
            "topics": [],
            "article_topics": [],
            "pillar_strategies": [],
            "cluster_articles": [],
            "topic_relationships": [],
            "topic_domain_coverage": [],
        }

    def _get_pool(self):
        if self._pool is not None:
            return self._pool
        
        try:
            from psycopg2.pool import ThreadedConnectionPool
            self._pool = ThreadedConnectionPool(
                minconn=1,
                maxconn=20,
                dsn=settings.postgresql_url,
                sslmode="require"
            )
            return self._pool
        except Exception as exc:
            logger.warning("Database pool unavailable; using in-memory fallback: %s", exc)
            return None

    def connect(self):
        # We now return a connection from the pool
        pool = self._get_pool()
        if pool:
            return pool.getconn()
        return None

    def release(self, conn):
        if self._pool and conn:
            self._pool.putconn(conn)

    def _execute(self, query: str, params: tuple = (), fetchone: bool = False, fetchall: bool = False):
        conn = self.connect()
        if conn is None:
            return None

        cursor = None
        try:
            from psycopg2.extras import RealDictCursor
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            cursor.execute(query, params)
            
            if fetchone:
                row = cursor.fetchone()
                conn.commit()
                return dict(row) if row else None
            
            if fetchall:
                rows = cursor.fetchall()
                conn.commit()
                return [dict(r) for r in rows] if rows else []
            
            conn.commit()
            return True
        except Exception as exc:
            if conn:
                conn.rollback()
            logger.error("Query failed: %s\nQuery: %s\nParams: %s", exc, query, params)
            return None
        finally:
            if cursor:
                cursor.close()
            if conn:
                self.release(conn)

    def query(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        rows = self._execute(query, params=params, fetchall=True)
        return rows or []

    @staticmethod
    def _vector_literal(values: List[float]) -> str:
        return "[" + ",".join(f"{float(v):.10f}" for v in values) + "]"

    @staticmethod
    def _parse_vector(value: Any) -> List[float]:
        if value is None:
            return []
        if isinstance(value, list):
            return [float(v) for v in value]
        if isinstance(value, tuple):
            return [float(v) for v in value]
        text = str(value).strip()
        if text.startswith("[") and text.endswith("]"):
            body = text[1:-1].strip()
            if not body:
                return []
            parts = re.split(r"\s*,\s*", body)
            return [float(p) for p in parts if p]
        return []

    def get_or_create_keyword(self, keyword: str) -> Optional[str]:
        keyword = keyword.strip()
        if not keyword:
            return None

        row = self._execute(
            """
            INSERT INTO keywords(keyword)
            VALUES (%s)
            ON CONFLICT (keyword) DO UPDATE SET keyword = EXCLUDED.keyword
            RETURNING id;
            """,
            (keyword,),
            fetchone=True,
        )
        if row:
            return row["id"]

        existing = next((k for k in self._memory["keywords"] if k["keyword"] == keyword), None)
        if existing:
            return existing["id"]
        key_id = f"kw_{len(self._memory['keywords']) + 1}"
        self._memory["keywords"].append({"id": key_id, "keyword": keyword})
        return key_id

    def insert_article(
        self,
        url: str,
        domain: str,
        title: str,
        content: str,
        serp_keyword: Optional[str] = None,
        serp_rank: Optional[int] = None,
    ):
        row = self._execute(
            """
            INSERT INTO articles(url, title, content, word_count, serp_keyword, serp_rank)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (url) DO UPDATE
            SET title = EXCLUDED.title,
                content = EXCLUDED.content,
                word_count = EXCLUDED.word_count,
                serp_keyword = COALESCE(EXCLUDED.serp_keyword, articles.serp_keyword),
                serp_rank = COALESCE(EXCLUDED.serp_rank, articles.serp_rank),
                updated_at = NOW()
            RETURNING id, url, title, serp_keyword, serp_rank;
            """,
            (url, title, content, len((content or "").split()), serp_keyword, serp_rank),
            fetchone=True,
        )
        if row:
            return row

        existing = next((a for a in self._memory["articles"] if a["url"] == url), None)
        payload = {
            "id": existing["id"] if existing else f"art_{len(self._memory['articles']) + 1}",
            "url": url,
            "domain": domain,
            "title": title,
            "content": content,
            "word_count": len((content or "").split()),
            "serp_keyword": serp_keyword,
            "serp_rank": serp_rank,
        }
        if existing:
            existing.update(payload)
            return existing
        self._memory["articles"].append(payload)
        return payload

    def update_article_embedding(self, article_id: str, embedding: List[float]):
        """Store the vector embedding for an article."""
        vector_str = self._vector_literal(embedding)
        row = self._execute(
            "UPDATE articles SET embedding = %s::vector WHERE id = %s RETURNING id",
            (vector_str, article_id),
            fetchone=True
        )
        if row:
            return row
            
        target = next((a for a in self._memory["articles"] if a.get("id") == article_id), None)
        if target:
            target["embedding"] = [float(v) for v in embedding]
            return {"id": article_id}
        return None

    def update_keyword_embedding(self, keyword: str, embedding: List[float]):
        """Store the vector embedding for a keyword."""
        vector_str = self._vector_literal(embedding)
        row = self._execute(
            "UPDATE keywords SET embedding = %s::vector WHERE keyword = %s RETURNING id",
            (vector_str, keyword),
            fetchone=True
        )
        if row:
            return row
            
        target = next((k for k in self._memory["keywords"] if k.get("keyword") == keyword), None)
        if target:
            target["embedding"] = [float(v) for v in embedding]
            return {"keyword": keyword}
        return None

    def fetch_keywords_with_embeddings(self, run_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Fetch keywords and their embeddings, optionally filtered by run_id."""
        if run_id:
            sql = """
                SELECT DISTINCT k.keyword, k.embedding::text as embedding_text
                FROM keywords k
                JOIN keyword_tasks kt ON k.keyword = kt.keyword
                WHERE kt.run_id = %s AND k.embedding IS NOT NULL;
            """
            rows = self.query(sql, (run_id,))
        else:
            sql = "SELECT keyword, embedding::text as embedding_text FROM keywords WHERE embedding IS NOT NULL;"
            rows = self.query(sql)
            
        payload = []
        for row in rows:
            payload.append({
                "keyword": row["keyword"],
                "embedding": self._parse_vector(row["embedding_text"])
            })
        return payload if payload else [k for k in self._memory["keywords"] if "embedding" in k]

    def fetch_articles_with_embeddings(self, article_ids: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        if article_ids:
            rows = self.query(
                """
                SELECT
                    id,
                    url,
                    title,
                    content,
                    serp_keyword,
                    serp_rank,
                    embedding::text AS embedding_text
                FROM articles
                WHERE embedding IS NOT NULL
                  AND id = ANY(%s::uuid[])
                ORDER BY created_at ASC;
                """,
                (article_ids,),
            )
        else:
            rows = self.query(
                """
                SELECT
                    id,
                    url,
                    title,
                    content,
                    serp_keyword,
                    serp_rank,
                    embedding::text AS embedding_text
                FROM articles
                WHERE embedding IS NOT NULL
                ORDER BY created_at ASC;
                """
            )
        if rows:
            payload = []
            for row in rows:
                payload.append(
                    {
                        "id": row.get("id"),
                        "url": row.get("url"),
                        "title": row.get("title"),
                        "content": row.get("content"),
                        "serp_keyword": row.get("serp_keyword"),
                        "serp_rank": row.get("serp_rank"),
                        "embedding": self._parse_vector(row.get("embedding_text")),
                    }
                )
            return payload

        # In-memory mode
        return [
            dict(article)
            for article in self._memory["articles"]
            if isinstance(article.get("embedding"), list) and article.get("embedding")
        ]

    def insert_paa_question(self, keyword: str, question: str):
        keyword_id = self.get_or_create_keyword(keyword)
        row = self._execute(
            """
            INSERT INTO paa_questions(keyword_id, question)
            VALUES (%s, %s)
            ON CONFLICT (question) DO UPDATE SET question = EXCLUDED.question
            RETURNING id, question;
            """,
            (keyword_id, question.strip()),
            fetchone=True,
        )
        if row:
            return row

        existing = next((q for q in self._memory["paa_questions"] if q["question"] == question.strip()), None)
        if existing:
            return existing
        payload = {
            "id": f"paa_{len(self._memory['paa_questions']) + 1}",
            "keyword_id": keyword_id,
            "question": question.strip(),
        }
        self._memory["paa_questions"].append(payload)
        return payload

    def insert_topic(self, name: str, description: str):
        row = self._execute(
            """
            INSERT INTO topics(name, description)
            VALUES (%s, %s)
            ON CONFLICT (name) DO UPDATE
            SET description = EXCLUDED.description,
                updated_at = NOW()
            RETURNING id, name;
            """,
            (name.strip(), description.strip()),
            fetchone=True,
        )
        if row:
            return row

        existing = next((t for t in self._memory["topics"] if t["name"] == name.strip()), None)
        if existing:
            existing["description"] = description.strip()
            return existing
        payload = {"id": f"topic_{len(self._memory['topics']) + 1}", "name": name.strip(), "description": description.strip()}
        self._memory["topics"].append(payload)
        return payload

    def insert_pillar_strategy(self, topic_id: str, strategy_details: Dict[str, Any]):
        # Keep strategy rows idempotent per topic_id.
        existing = self._execute(
            """
            SELECT id
            FROM pillar_strategies
            WHERE topic_id = %s
            ORDER BY created_at ASC
            LIMIT 1;
            """,
            (topic_id,),
            fetchone=True,
        )
        if existing:
            row = self._execute(
                """
                UPDATE pillar_strategies
                SET strategy_details = %s::jsonb,
                    updated_at = NOW()
                WHERE id = %s
                RETURNING id;
                """,
                (json.dumps(strategy_details), existing["id"]),
                fetchone=True,
            )
            if row:
                return row

        row = self._execute(
            """
            INSERT INTO pillar_strategies(topic_id, strategy_details)
            VALUES (%s, %s::jsonb)
            RETURNING id;
            """,
            (topic_id, json.dumps(strategy_details)),
            fetchone=True,
        )
        if row:
            return row

        existing = next((p for p in self._memory["pillar_strategies"] if p.get("topic_id") == topic_id), None)
        if existing:
            existing["strategy_details"] = strategy_details
            return existing

        payload = {
            "id": f"pillar_{len(self._memory['pillar_strategies']) + 1}",
            "topic_id": topic_id,
            "strategy_details": strategy_details,
        }
        self._memory["pillar_strategies"].append(payload)
        return payload

    def insert_article_topic(self, article_id: str, topic_id: str, relevance_score: float = 1.0):
        row = self._execute(
            """
            INSERT INTO article_topics(article_id, topic_id, relevance_score)
            VALUES (%s, %s, %s)
            ON CONFLICT (article_id, topic_id) DO UPDATE
            SET relevance_score = EXCLUDED.relevance_score
            RETURNING article_id, topic_id;
            """,
            (article_id, topic_id, float(relevance_score)),
            fetchone=True,
        )
        if row:
            return row

        existing = next(
            (
                item
                for item in self._memory["article_topics"]
                if item.get("article_id") == article_id and item.get("topic_id") == topic_id
            ),
            None,
        )
        if existing:
            existing["relevance_score"] = float(relevance_score)
            return existing
        payload = {"article_id": article_id, "topic_id": topic_id, "relevance_score": float(relevance_score)}
        self._memory["article_topics"].append(payload)
        return payload

    def insert_cluster_article(self, cluster_id: str, article_id: str):
        row = self._execute(
            """
            INSERT INTO cluster_articles(cluster_id, article_id)
            SELECT %s, %s
            WHERE NOT EXISTS (
                SELECT 1
                FROM cluster_articles
                WHERE cluster_id = %s AND article_id = %s
            )
            RETURNING id, cluster_id, article_id;
            """,
            (cluster_id, article_id, cluster_id, article_id),
            fetchone=True,
        )
        if row:
            return row

        existing = next(
            (
                c
                for c in self._memory["cluster_articles"]
                if c.get("cluster_id") == cluster_id and c.get("article_id") == article_id
            ),
            None,
        )
        if existing:
            return existing
        payload = {"id": f"ca_{len(self._memory['cluster_articles']) + 1}", "cluster_id": cluster_id, "article_id": article_id}
        self._memory["cluster_articles"].append(payload)
        return payload

    def save_topic_relationship(self, topic_id: str, related_topic_id: str, weight: float, relationship_type: str):
        normalized_topic_id = str(topic_id).strip()
        normalized_related_id = str(related_topic_id).strip()
        normalized_type = str(relationship_type).strip()
        normalized_weight = float(weight)

        row = self._execute(
            """
            INSERT INTO topic_relationships(topic_id, related_topic_id, weight, relationship_type)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (topic_id, related_topic_id, relationship_type) DO NOTHING
            RETURNING id, topic_id, related_topic_id, weight, relationship_type;
            """,
            (normalized_topic_id, normalized_related_id, normalized_weight, normalized_type),
            fetchone=True,
        )
        if row:
            return row

        memory_rel = next(
            (
                rel
                for rel in self._memory["topic_relationships"]
                if rel.get("topic_id") == normalized_topic_id
                and rel.get("related_topic_id") == normalized_related_id
                and rel.get("relationship_type") == normalized_type
            ),
            None,
        )
        if memory_rel:
            return memory_rel
        payload = {
            "id": len(self._memory["topic_relationships"]) + 1,
            "topic_id": normalized_topic_id,
            "related_topic_id": normalized_related_id,
            "weight": normalized_weight,
            "relationship_type": normalized_type,
        }
        self._memory["topic_relationships"].append(payload)
        return payload

    def save_topic_coverage(self, topic_id: str, domain: str, article_count: int, avg_rank: Optional[float]):
        normalized_topic_id = str(topic_id).strip()
        normalized_domain = str(domain).strip().lower()
        normalized_count = int(article_count)
        normalized_avg_rank = None if avg_rank is None else float(avg_rank)

        row = self._execute(
            """
            INSERT INTO topic_domain_coverage(topic_id, domain, article_count, avg_rank)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (topic_id, domain) DO UPDATE
            SET article_count = EXCLUDED.article_count,
                avg_rank = EXCLUDED.avg_rank
            RETURNING topic_id, domain, article_count, avg_rank;
            """,
            (normalized_topic_id, normalized_domain, normalized_count, normalized_avg_rank),
            fetchone=True,
        )
        if row:
            return row

        memory_coverage = next(
            (
                cov
                for cov in self._memory["topic_domain_coverage"]
                if cov.get("topic_id") == normalized_topic_id and cov.get("domain") == normalized_domain
            ),
            None,
        )
        if memory_coverage:
            memory_coverage["article_count"] = normalized_count
            memory_coverage["avg_rank"] = normalized_avg_rank
            return memory_coverage
        payload = {
            "topic_id": normalized_topic_id,
            "domain": normalized_domain,
            "article_count": normalized_count,
            "avg_rank": normalized_avg_rank,
        }
        self._memory["topic_domain_coverage"].append(payload)
        return payload

    def update_task_status(self, task_id: str, status: str, status_message: Optional[str] = None):
        """Update the status and optional status message for a keyword task."""
        if status_message:
            self._execute(
                "UPDATE keyword_tasks SET status = %s, status_message = %s WHERE id = %s",
                (status, status_message, task_id)
            )
        else:
            self._execute(
                "UPDATE keyword_tasks SET status = %s WHERE id = %s",
                (status, task_id)
            )

    def increment_task_retry_count(self, task_id: str):
        """Increment the retry_count for a specific keyword task."""
        self._execute(
            "UPDATE keyword_tasks SET retry_count = COALESCE(retry_count, 0) + 1 WHERE id = %s",
            (task_id,)
        )

    def delete_run(self, run_id: str):
        """Delete a run and its associated tasks."""
        # Deleting associated tasks first due to foreign key constraints if any
        self._execute("DELETE FROM keyword_tasks WHERE run_id = %s", (run_id,))
        self._execute("DELETE FROM runs WHERE id = %s", (run_id,))

    def fetch_articles(self):
        rows = self.query("SELECT id, url, title, content, serp_keyword, serp_rank FROM articles ORDER BY created_at ASC")
        return rows if rows else self._memory["articles"]


db_client = DBClient()
