import logging
import json
from collections import Counter
from typing import Dict, List, Any, Optional

from skills.openai_utils import chat_completion_json

logger = logging.getLogger(__name__)


def _cluster_sort_key(cluster_id: str):
    try:
        return (0, int(cluster_id))
    except Exception:
        return (1, cluster_id)


def _cluster_payload(
    clustered_article_titles: Dict[int, List[str]],
    clustered_articles: Dict[int, List[Dict[str, str]]],
) -> List[Dict[str, object]]:
    payload = []
    for cluster_id, titles in clustered_article_titles.items():
        articles = clustered_articles.get(cluster_id, [])
        keyword_freq = Counter(
            str(article.get("keyword", "")).strip()
            for article in articles
            if isinstance(article, dict) and str(article.get("keyword", "")).strip()
        )
        payload.append(
            {
                "cluster_id": str(cluster_id),
                "titles": titles[:12],
                "serp_keywords": dict(keyword_freq),
            }
        )
    return payload


def generate_topics(
    clustered_article_titles: Dict[int, List[str]],
    paa_questions: List[str],
    keywords: List[str],
    clustered_articles: Dict[int, List[Dict[str, str]]] = None,
) -> List[Dict[str, str]]:
    clustered_articles = clustered_articles or {}
    clusters = _cluster_payload(clustered_article_titles, clustered_articles)
    if not clusters:
        return []

    system_prompt = (
        "You are an SEO topic strategist. Return only valid JSON with a top-level key 'topics'. "
        "Each topic must include: cluster_id (string), name (string), description (string). "
        "Use dominant SERP keyword phrasing when appropriate."
    )
    user_prompt = {
        "seed_keywords": keywords,
        "paa_questions": paa_questions[:15],
        "clusters": clusters,
    }
    response = chat_completion_json(
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json.dumps(user_prompt)},
        ],
        model_env_key="OPENAI_REASONING_MODEL",
        default_model="gpt-4o-mini",
        timeout_default=90,
    )
    topics = response.get("topics")
    if not isinstance(topics, list):
        raise RuntimeError(f"LLM topic response missing topics list: {response}")

    normalized = []
    available_cluster_ids = {str(k) for k in clustered_article_titles.keys()}
    ordered_cluster_ids = sorted(available_cluster_ids, key=_cluster_sort_key)
    fallback_index = 0
    seen = set()
    for topic in topics:
        if not isinstance(topic, dict):
            continue
        cluster_id = str(topic.get("cluster_id", "")).strip()
        name = str(topic.get("name", "")).strip()
        description = str(topic.get("description", "")).strip()
        if not name or not description:
            continue
        if cluster_id not in available_cluster_ids:
            if fallback_index >= len(ordered_cluster_ids):
                continue
            cluster_id = ordered_cluster_ids[fallback_index]
            fallback_index += 1
        dedup_key = (cluster_id, name.lower())
        if dedup_key in seen:
            continue
        seen.add(dedup_key)
        normalized.append({"name": name, "description": description, "cluster_id": cluster_id})

    if not normalized:
        raise RuntimeError(f"LLM topic response produced no valid topics: {response}")

    logger.info("Generated %d topic definitions", len(normalized))
    return normalized
