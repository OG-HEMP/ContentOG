import logging
from collections import defaultdict

from database.db_client import db_client
from skills.clustering.clustering import cluster_embeddings

logger = logging.getLogger(__name__)


class ClusterAgent:
    def run(self, context):
        run_id = context.get("run_id")
        
        # 1. Fetch Keyword Anchors
        keyword_anchors = []
        if run_id:
            keyword_anchors = db_client.fetch_keywords_with_embeddings(run_id)
            logger.info("Fetched %d keyword anchors for run %s", len(keyword_anchors), run_id)

        # 2. Fetch Article Embeddings
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
                    "article_id": str(article.get("id") or article.get("article_id") or idx),
                    "title": article.get("title"),
                    "url": article.get("url"),
                    "keyword": article.get("serp_keyword") or article.get("keyword"),
                    "serp_rank": article.get("serp_rank") or article.get("rank"),
                    "type": "article",
                    "embedding": article.get("embedding")
                }
            )

        # 3. Combine with Keyword Anchors
        anchor_data = []
        for kw in keyword_anchors:
            anchor_data.append({
                "article_id": f"kw_{kw['id']}",
                "title": f"ANCHOR: {kw['keyword']}",
                "keyword": kw['keyword'],
                "type": "keyword",
                "embedding": kw['embedding']
            })
            
        combined_data = cluster_articles + anchor_data
        combined_embeddings = [a["embedding"] for a in combined_data]
        
        mapping = cluster_embeddings(combined_embeddings, combined_data)

        # 4. Filter out anchors from final clustered titles/articles (they just guide)
        clustered_titles = defaultdict(list)
        clustered_articles = defaultdict(list)
        keyword_to_cluster = {}

        for article in combined_data:
            article_id = article["article_id"]
            cluster_id = mapping.get(article_id, -1)
            
            if article["type"] == "keyword":
                keyword_to_cluster[article["keyword"]] = cluster_id
                continue

            clustered_titles[cluster_id].append(article.get("title", article.get("url", "untitled")))
            clustered_articles[cluster_id].append(article)

        context["keyword_to_cluster"] = keyword_to_cluster
        context["cluster_mapping"] = mapping
        context["clustered_titles"] = dict(clustered_titles)
        context["clustered_articles"] = dict(clustered_articles)
        logger.info("Clustered %d embeddings", len(mapping))
        return context
