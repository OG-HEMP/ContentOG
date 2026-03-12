from skills.serp_discovery.serp_discovery import get_serp_urls

class SerpAgent:
    def run(self):
        print("Agent: SERP Discovery Agent is running...")
        # Discovery URLs for seed keywords
        urls = get_serp_urls("placeholder keyword")
        print(f"Agent: Found {len(urls)} URLs")
