import logging
import json
from typing import Dict, List

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


def generate_strategy(
    topics: List[Dict[str, str]],
    clustered_articles: Dict[int, List[Dict[str, str]]],
    paa_questions: List[str],
) -> Dict[str, List[Dict[str, str]]]:
    pillar_pages = []
    cluster_topics = []
    briefs = []

    for topic in topics:
        inserted_topic = db_client.insert_topic(topic["name"], topic["description"])
        topic_id = inserted_topic.get("id")
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

    logger.info("Generated strategy for %d topics", len(topics))
    return {"pillar_pages": pillar_pages, "cluster_topics": cluster_topics, "content_briefs": briefs}
