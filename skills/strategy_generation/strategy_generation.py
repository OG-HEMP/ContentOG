import logging
import json
from collections import Counter
from typing import Dict, List, Any, Optional
from urllib.parse import urlparse

from database.db_client import db_client
from skills.openai_utils import chat_completion_json

logger = logging.getLogger(__name__)


def _cluster_articles_for_topic(
    clustered_articles: Dict[int, List[Dict[str, str]]],
    cluster_id: str,
) -> List[Dict[str, str]]:
    if cluster_id in clustered_articles:
        return clustered_articles.get(cluster_id, [])
    try:
        numeric = int(cluster_id)
    except Exception:
        numeric = None
    if numeric is not None and numeric in clustered_articles:
        return clustered_articles.get(numeric, [])
    return []


def _article_domain(article: Dict[str, str]) -> str:
    url = str((article or {}).get("url", "")).strip()
    if not url:
        return ""
    return urlparse(url).netloc.lower()


def _topic_coverage_by_domain(topic_records: List[Dict[str, object]]) -> List[Dict[str, object]]:
    coverage: List[Dict[str, object]] = []
    for record in topic_records:
        linked_articles = record.get("linked_articles", [])
        if not isinstance(linked_articles, list):
            linked_articles = []
        domain_counts: Counter = Counter()
        domain_rank_totals: Dict[str, float] = {}
        domain_rank_counts: Counter = Counter()
        for article in linked_articles:
            if not isinstance(article, dict):
                continue
            domain = _article_domain(article)
            if not domain:
                continue
            domain_counts[domain] += 1
            try:
                rank = float(article.get("serp_rank"))
                if rank > 0:
                    domain_rank_totals[domain] = domain_rank_totals.get(domain, 0.0) + rank
                    domain_rank_counts[domain] += 1
            except Exception:
                continue
        coverage.append(
            {
                "topic_id": str(record.get("topic_id", "")),
                "topic": str(record.get("topic", "")),
                "cluster_id": str(record.get("cluster_id", "")),
                "total_articles": int(sum(domain_counts.values())),
                "domains": [
                    {
                        "domain": domain,
                        "article_count": count,
                        "avg_rank": (
                            round(domain_rank_totals[domain] / domain_rank_counts[domain], 4)
                            if domain_rank_counts[domain]
                            else None
                        ),
                    }
                    for domain, count in sorted(domain_counts.items(), key=lambda item: (-item[1], item[0]))
                ],
            }
        )
    return coverage


def _industry_topic_graph(topic_records: List[Dict[str, object]], keyword_to_cluster: Dict[str, int] = None) -> Dict[str, List[Dict[str, object]]]:
    nodes = [
        {
            "id": str(record.get("topic_id", "")),
            "name": str(record.get("topic", "")),
            "cluster_id": str(record.get("cluster_id", "")),
            "article_count": int(len(record.get("linked_articles", []))),
            "type": "topic",
        }
        for record in topic_records
    ]

    # Add Keyword Anchor Nodes
    edges: List[Dict[str, object]] = []
    if keyword_to_cluster:
        for kw, cluster_id in keyword_to_cluster.items():
            kw_node_id = f"kw_{kw.replace(' ', '_')}"
            nodes.append({
                "id": kw_node_id,
                "name": kw.upper(),
                "type": "keyword",
                "size": 10, # Larger for anchors
            })
            
            # Find the topic that matches this cluster
            matching_topic = next((r for r in topic_records if str(r.get("cluster_id")) == str(cluster_id)), None)
            if matching_topic:
                edges.append({
                    "source": kw_node_id,
                    "target": str(matching_topic["topic_id"]),
                    "strength": 1.0,
                    "relationship_type": "keyword_anchor"
                })

    topic_domains = []
    for record in topic_records:
        domains = {
            _article_domain(article)
            for article in (record.get("linked_articles", []) or [])
            if isinstance(article, dict)
        }
        topic_domains.append({domain for domain in domains if domain})

    for idx in range(len(topic_records)):
        for jdx in range(idx + 1, len(topic_records)):
            overlap = topic_domains[idx].intersection(topic_domains[jdx])
            if not overlap:
                continue
            union = topic_domains[idx].union(topic_domains[jdx])
            strength = float(len(overlap) / len(union)) if union else 0.0
            edges.append(
                {
                    "source": str(topic_records[idx].get("topic_id", "")),
                    "target": str(topic_records[jdx].get("topic_id", "")),
                    "shared_domains": sorted(overlap),
                    "shared_domain_count": len(overlap),
                    "strength": round(strength, 4),
                    "type": "domain_overlap"
                }
            )
    return {"nodes": nodes, "edges": edges}


def _generate_topic_strategy(topic: Dict[str, str], paa_questions: List[str]) -> Dict[str, object]:
    system_prompt = (
        "You are an SEO strategist. Return only valid JSON with keys: "
        "pillar_title, pillar_angle, cluster_article_title, brief_intent, brief_outline."
    )
    user_payload = {
        "topic": topic,
        "paa_questions": paa_questions[:10],
        "requirements": "Output concise and actionable strategy elements.",
    }
    response = chat_completion_json(
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json.dumps(user_payload)},
        ],
        model_env_key="OPENAI_STRATEGY_MODEL",
        default_model="gpt-4o-mini",
        timeout_default=90,
    )
    required = ["pillar_title", "pillar_angle", "cluster_article_title", "brief_intent", "brief_outline"]
    for field in required:
        if field not in response:
            raise RuntimeError(f"LLM strategy response missing '{field}': {response}")
    if not isinstance(response.get("brief_outline"), list):
        raise RuntimeError(f"LLM strategy response brief_outline must be a list: {response}")
    return response


def _topic_keywords(topic: Dict[str, str], linked_articles: List[Dict[str, str]]) -> set:
    values = [str(topic.get("name", "")), str(topic.get("description", ""))]
    for article in linked_articles:
        values.append(str(article.get("keyword", "")))
        values.append(str(article.get("title", "")))
    tokens = set()
    for value in values:
        for token in value.lower().replace("/", " ").replace("-", " ").split():
            token = token.strip(" ,.:;!?()[]{}\"'`")
            if len(token) > 2:
                tokens.add(token)
    return tokens


def _persist_topic_graph_fallback(topic_records: List[Dict[str, object]]):
    if len(topic_records) < 2:
        return

    # If any pair of topics already shares keywords, natural edges exist — skip fallback
    has_overlap = any(
        topic_records[i]["keywords"].intersection(topic_records[j]["keywords"])
        for i in range(len(topic_records))
        for j in range(i + 1, len(topic_records))
    )
    if has_overlap:
        return

    # No natural connections — connect all topic pairs with a low-weight fallback edge
    # so the Topic Universe graph has visible structure
    fallback_edges = 0
    for i in range(len(topic_records)):
        for j in range(i + 1, len(topic_records)):
            db_client.save_topic_relationship(
                str(topic_records[i]["topic_id"]),
                str(topic_records[j]["topic_id"]),
                relationship_type="keyword_overlap",
                weight=0.2,
            )
            fallback_edges += 1

    if fallback_edges:
        logger.info("Added %d fallback topic graph edge(s)", fallback_edges)


def generate_strategy(
    topics: List[Dict[str, str]],
    clustered_articles: Dict[int, List[Dict[str, str]]],
    paa_questions: List[str],
    target_domain: Optional[str] = None,
) -> Dict[str, object]:
    pillar_pages = []
    cluster_topics = []
    briefs = []
    topic_records: List[Dict[str, object]] = []

    for topic in topics:
        inserted_topic = db_client.insert_topic(topic["name"], topic["description"])
        topic_id = str(inserted_topic.get("id") or "")
        cluster_id = str(topic.get("cluster_id", ""))

        generated = _generate_topic_strategy(topic, paa_questions)
        pillar = {
            "topic_id": topic_id,
            "title": str(generated["pillar_title"]).strip(),
            "angle": str(generated["pillar_angle"]).strip(),
        }
        db_client.insert_pillar_strategy(topic_id, pillar)
        pillar_pages.append(pillar)

        cluster_idea_title = str(generated["cluster_article_title"]).strip()
        cluster_topics.append({"cluster_id": cluster_id, "title": cluster_idea_title})

        brief = {
            "topic": topic["name"],
            "intent": str(generated["brief_intent"]).strip(),
            "outline": [str(item).strip() for item in generated["brief_outline"] if str(item).strip()],
        }
        briefs.append(brief)

        linked_articles = _cluster_articles_for_topic(clustered_articles, cluster_id)
        
        # Add to topic_records for relationship mapping
        topic_records.append(
            {
                "topic_id": topic_id,
                "topic": topic["name"],
                "cluster_id": cluster_id,
                "linked_articles": linked_articles,
                "keywords": _topic_keywords(topic, linked_articles),
            }
        )
        
        for article in linked_articles:
            article_id = article.get("article_id")
            if not article_id:
                continue
            rank = article.get("serp_rank")
            try:
                relevance = 1.0 / max(float(rank), 1.0)
            except Exception:
                relevance = 1.0
            db_client.insert_article_topic(str(article_id), str(topic_id), relevance_score=relevance)
            db_client.insert_cluster_article(cluster_id=cluster_id, article_id=str(article_id))

    _persist_topic_graph_fallback(topic_records)

    # NEW: Centroid-based semantic similarity for better clustering in Graph Universe
    _add_semantic_centroid_edges(topic_records)

    logger.info("Generated strategy for %d topics", len(topics))
    coverage_by_domain = _topic_coverage_by_domain(topic_records)
    
    # NEW: Include keyword anchors in the graph
    keyword_to_cluster = getattr(topics[0], "keyword_to_cluster", {}) if topics else {}
    topic_graph = _industry_topic_graph(topic_records, keyword_to_cluster)

    for edge in topic_graph.get("edges", []):
        source_topic_id = str(edge.get("source", "")).strip()
        related_topic_id = str(edge.get("target", "")).strip()
        if not source_topic_id or not related_topic_id:
            continue
        if source_topic_id == related_topic_id:
            continue
        try:
            weight = float(edge.get("strength", 0.0))
        except Exception:
            weight = 0.0
        db_client.save_topic_relationship(
            topic_id=source_topic_id,
            related_topic_id=related_topic_id,
            weight=weight,
            relationship_type="semantic_similarity",
        )

    for coverage in coverage_by_domain:
        topic_id = str(coverage.get("topic_id", "")).strip()
        if not topic_id:
            continue
        domains = coverage.get("domains", [])
        if not isinstance(domains, list):
            continue
        for domain_stats in domains:
            if not isinstance(domain_stats, dict):
                continue
            domain = str(domain_stats.get("domain", "")).strip().lower()
            if not domain:
                continue
            try:
                article_count = int(domain_stats.get("article_count", 0))
            except Exception:
                article_count = 0
            avg_rank_raw = domain_stats.get("avg_rank")
            try:
                avg_rank = None if avg_rank_raw is None else float(avg_rank_raw)
            except Exception:
                avg_rank = None
            db_client.save_topic_coverage(
                topic_id=topic_id,
                domain=domain,
                article_count=article_count,
                avg_rank=avg_rank,
            )

    return {
        "pillar_pages": pillar_pages,
        "cluster_topics": cluster_topics,
        "content_briefs": briefs,
        "topic_coverage_by_domain": coverage_by_domain,
        "industry_topic_graph": topic_graph,
    }
def _add_semantic_centroid_edges(topic_records: List[Dict[str, object]]):
    """Add edges based on cosine similarity of topic centroids."""
    if len(topic_records) < 2:
        return

    # 1. Get centroids for each topic
    topic_centroids = {}
    for record in topic_records:
        linked_articles = record.get("linked_articles", [])
        article_ids = [str(a.get("article_id")) for a in linked_articles if a.get("article_id")]
        
        if not article_ids:
            continue
            
        embeddings = db_client.fetch_articles_with_embeddings(article_ids=article_ids)
        if embeddings:
            # Average the embeddings to get the centroid
            vectors = [e.get("embedding") for e in embeddings if e.get("embedding")]
            if vectors:
                centroid = [sum(col) / len(vectors) for col in zip(*vectors)]
                topic_centroids[record["topic_id"]] = centroid

    # 2. Compare centroids and add semantic edges
    tids = list(topic_centroids.keys())
    for i in range(len(tids)):
        for j in range(i + 1, len(tids)):
            id_a, id_b = tids[i], tids[j]
            vec_a, vec_b = topic_centroids[id_a], topic_centroids[id_b]
            
            # Simple dot product as they are likely normalized from OpenAI
            dot = sum(a * b for a, b in zip(vec_a, vec_b))
            
            if dot > 0.70: # Lowered from 0.85 to increase semantic connection density
                db_client.save_topic_relationship(
                    topic_id=id_a,
                    related_topic_id=id_b,
                    weight=round(float(dot), 4),
                    relationship_type="semantic_centroid_similarity",
                )
                logger.info(f"Added semantic edge between {id_a} and {id_b} (score: {dot:.4f})")
