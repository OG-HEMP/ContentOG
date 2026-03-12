import logging
from pathlib import Path

from database.db_client import db_client
from skills.web_crawling.web_crawling import crawl_page

logger = logging.getLogger(__name__)


class CrawlAgent:
    def run(self, context):
        try:
            import yaml
        except Exception:
            yaml = None

        min_success_count = 1
        if yaml is not None:
            settings_path = Path("config/settings.yaml")
            if settings_path.exists():
                with open(settings_path, "r", encoding="utf-8") as handle:
                    settings = yaml.safe_load(handle) or {}
                min_success_count = int(((settings.get("crawler") or {}).get("min_success_per_keyword")) or 1)

        serp_results = context.get("serp_results", [])
        crawled = []
        for item in serp_results:
            try:
                page = crawl_page(item["url"])
            except Exception as exc:
                logger.warning("Skipping URL due to crawl failure: %s (%s)", item.get("url"), exc)
                continue
            record = db_client.insert_article(
                item["url"],
                item["domain"],
                page["title"],
                page["content"],
                serp_keyword=item.get("keyword"),
                serp_rank=item.get("rank"),
            )
            merged = {**item, **page, "article_id": record.get("id") if isinstance(record, dict) else None}
            crawled.append(merged)
        if len(crawled) < min_success_count:
            raise RuntimeError(
                "CrawlAgent retrieved insufficient article content from SERP results "
                f"(required={min_success_count}, actual={len(crawled)})."
            )
        context["articles"] = crawled
        logger.info("Crawl completed for %d urls", len(crawled))
        return context
