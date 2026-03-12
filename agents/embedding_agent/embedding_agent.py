import logging

from database.db_client import db_client
from skills.embeddings.embeddings import generate_embedding

logger = logging.getLogger(__name__)


class EmbeddingAgent:
    def run(self, context):
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
