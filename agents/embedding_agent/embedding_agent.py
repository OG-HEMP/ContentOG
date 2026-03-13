import logging

from database.db_client import db_client
from skills.embeddings.embeddings import generate_embedding

logger = logging.getLogger(__name__)


class EmbeddingAgent:
    def run(self, context):
        # 1. Embed seed keywords if provided (anchors for clustering)
        seed_keywords = context.get("keywords") or [context.get("keyword")]
        if seed_keywords:
            for kw in seed_keywords:
                if not kw: continue
                kw_vector = generate_embedding(kw)
                db_client.update_keyword_embedding(kw, kw_vector)
            logger.info("Generated embeddings for %d seed keywords", len(seed_keywords))

        # 2. Embed articles
        articles = context.get("articles", [])
        vectors = []
        embedded_ids = []
        for article in articles:
            vector = generate_embedding(article.get("content", ""))
            vectors.append(vector)
            updated = db_client.update_article_embedding(
                article_id=article.get("article_id"),
                embedding=vector,
                url=article.get("url"),
            )
            if isinstance(updated, dict) and updated.get("id"):
                embedded_ids.append(str(updated["id"]))
        context["embeddings"] = vectors
        context["embedded_articles"] = db_client.fetch_articles_with_embeddings(article_ids=embedded_ids)
        logger.info("Generated embeddings for %d articles", len(vectors))
        return context
