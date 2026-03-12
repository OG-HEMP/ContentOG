import logging
from collections import defaultdict

from database.db_client import db_client
from skills.clustering.clustering import cluster_embeddings

logger = logging.getLogger(__name__)


class ClusterAgent:
    def run(self, context):
        embedded_articles = context.get("embedded_articles", [])
        if not embedded_articles:
            article_ids = [
                str(article.get("article_id"))
                for article in context.get("articles", [])
                if article.get("article_id")
            ]
            embedded_articles = db_client.fetch_articles_with_embeddings(article_ids=article_ids)
        articles = embedded_articles or context.get("articles", [])
        embeddings = [article.get("embedding", []) for article in articles]
        cluster_articles = []
        for idx, article in enumerate(articles):
            cluster_articles.append(
                {
                    "article_id": article.get("id") or article.get("article_id") or idx,
                    "title": article.get("title"),
                    "url": article.get("url"),
                    "keyword": article.get("serp_keyword") or article.get("keyword"),
                    "serp_rank": article.get("serp_rank") or article.get("rank"),
                }
            )
        mapping = cluster_embeddings(embeddings, cluster_articles)

        clustered_titles = defaultdict(list)
        clustered_articles = defaultdict(list)
        for idx, article in enumerate(cluster_articles):
            article_id = str(article.get("article_id", idx))
            cluster_id = mapping.get(article_id, -1)
            clustered_titles[cluster_id].append(article.get("title", article.get("url", "untitled")))
            clustered_articles[cluster_id].append(article)

        context["cluster_mapping"] = mapping
        context["clustered_titles"] = dict(clustered_titles)
        context["clustered_articles"] = dict(clustered_articles)
        logger.info("Clustered %d embeddings", len(mapping))
        return context
