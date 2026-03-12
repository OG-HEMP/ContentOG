from skills.web_crawling.web_crawling import crawl_url

class CrawlAgent:
    def run(self):
        print("Agent: Crawl Agent is running...")
        content = crawl_url("http://example.com")
        print("Agent: Web content retrieved.")
