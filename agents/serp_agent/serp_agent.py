import logging

from database.db_client import db_client
from skills.serp_discovery.serp_discovery import discover_serp_urls

logger = logging.getLogger(__name__)


class SerpAgent:
    def run(self, context):
        keyword = context.get("keyword", "content strategy")
        urls = discover_serp_urls(keyword)
        for entry in urls:
            db_client.insert_article(
                entry["url"],
                entry["domain"],
                "",
                "",
                serp_keyword=entry.get("keyword", keyword),
                serp_rank=entry.get("rank"),
            )
        context["serp_results"] = urls
        logger.info("SERP discovered %d urls", len(urls))
        return context
