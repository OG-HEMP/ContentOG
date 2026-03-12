import logging
import os
import re
from typing import Any, Dict, List, Optional

from database.db_connection import get_db

logger = logging.getLogger(__name__)


class DBClient:
    """Shared database utility with idempotent helpers and safe fallbacks."""

    def __init__(self) -> None:
        self._conn = None
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

    def connect(self):
        if self._conn is not None:
            return self._conn
        try:
            self._conn = get_db()
            return self._conn
        except Exception as exc:  # pragma: no cover - fallback path
            strict_mode = str(os.getenv("CONTENTOG_DISABLE_DB_FALLBACK", "false")).strip().lower() in (
                "1",
                "true",
                "yes",
                "on",
            )
            if strict_mode:
                raise RuntimeError(f"Database unavailable and fallback is disabled: {exc}") from exc
            logger.warning("Database unavailable; using in-memory fallback: %s", exc)
            self._conn = None
            return None

    def _execute(self, query: str, params: tuple = (), fetchone: bool = False, fetchall: bool = False):
        conn = self.connect()
        if conn is None:
            return None

        try:
            from psycopg2.extras import RealDictCursor
            cursor = conn.cursor(cursor_factory=RealDictCursor)
        except Exception:
            cursor = conn.cursor()

        with cursor as cur:
            cur.execute(query, params)
            row = cur.fetchone() if fetchone else None
            rows = cur.fetchall() if fetchall else None
            conn.commit()
            if fetchone:
                return dict(row) if row else None
            if fetchall:
                return [dict(r) for r in rows]
            return None

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

    def update_article_embedding(self, article_id: Optional[str], embedding: List[float], url: Optional[str] = None):
        if not embedding:
            raise ValueError("Embedding vector cannot be empty.")

        vector_literal = self._vector_literal(embedding)
        row = None
        if article_id:
            row = self._execute(
                """
                UPDATE articles
                SET embedding = %s::vector,
                    updated_at = NOW()
                WHERE id = %s
                RETURNING id, url;
                """,
                (vector_literal, article_id),
                fetchone=True,
            )

        if row is None and url:
            row = self._execute(
                """
                UPDATE articles
                SET embedding = %s::vector,
                    updated_at = NOW()
                WHERE url = %s
                RETURNING id, url;
                """,
                (vector_literal, url),
                fetchone=True,
            )

        if row:
            return row

        # In-memory mode
        target = None
        if article_id:
            target = next((a for a in self._memory["articles"] if a.get("id") == article_id), None)
        if target is None and url:
            target = next((a for a in self._memory["articles"] if a.get("url") == url), None)
        if target is None:
            return None
        target["embedding"] = [float(v) for v in embedding]
        return {"id": target.get("id"), "url": target.get("url")}

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
                (__import__("json").dumps(strategy_details), existing["id"]),
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
            (topic_id, __import__("json").dumps(strategy_details)),
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

    def insert_cluster_articles(self, pillar_id: str, title: str):
        row = self._execute(
            """
            INSERT INTO cluster_articles(cluster_id, article_id)
            SELECT %s, id FROM articles WHERE title = %s
            ON CONFLICT DO NOTHING
            RETURNING id;
            """,
            (pillar_id, title),
            fetchone=True,
        )
        if row:
            return row

        existing = next((c for c in self._memory["cluster_articles"] if c.get("cluster_id") == pillar_id and c.get("title") == title), None)
        if existing:
            return existing
        payload = {"id": f"ca_{len(self._memory['cluster_articles']) + 1}", "cluster_id": pillar_id, "title": title}
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

        existing = self._execute(
            """
            SELECT id, topic_id, related_topic_id, weight, relationship_type
            FROM topic_relationships
            WHERE topic_id = %s
              AND related_topic_id = %s
              AND relationship_type = %s
            LIMIT 1;
            """,
            (normalized_topic_id, normalized_related_id, normalized_type),
            fetchone=True,
        )
        if existing:
            return existing

        memory_existing = next(
            (
                rel
                for rel in self._memory["topic_relationships"]
                if rel.get("topic_id") == normalized_topic_id
                and rel.get("related_topic_id") == normalized_related_id
                and rel.get("relationship_type") == normalized_type
            ),
            None,
        )
        if memory_existing:
            return memory_existing
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

        memory_existing = next(
            (
                cov
                for cov in self._memory["topic_domain_coverage"]
                if cov.get("topic_id") == normalized_topic_id and cov.get("domain") == normalized_domain
            ),
            None,
        )
        if memory_existing:
            memory_existing["article_count"] = normalized_count
            memory_existing["avg_rank"] = normalized_avg_rank
            return memory_existing
        payload = {
            "topic_id": normalized_topic_id,
            "domain": normalized_domain,
            "article_count": normalized_count,
            "avg_rank": normalized_avg_rank,
        }
        self._memory["topic_domain_coverage"].append(payload)
        return payload

    def fetch_articles(self):
        rows = self.query("SELECT id, url, title, content, serp_keyword, serp_rank FROM articles ORDER BY created_at ASC")
        return rows if rows else self._memory["articles"]


db_client = DBClient()
