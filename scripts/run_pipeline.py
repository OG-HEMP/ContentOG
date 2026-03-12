import sys
import os

# Add project root to sys.path for module imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.serp_agent.serp_agent import SerpAgent
from agents.paa_agent.paa_agent import PaaAgent
from agents.crawl_agent.crawl_agent import CrawlAgent
from agents.embedding_agent.embedding_agent import EmbeddingAgent
from agents.cluster_agent.cluster_agent import ClusterAgent
from agents.topic_agent.topic_agent import TopicAgent
from agents.strategy_agent.strategy_agent import StrategyAgent

def run_pipeline():
    """Orchestrates the discovery pipeline execution."""
    print("Starting ContentOG Discovery Pipeline...")

    # Phase 1: Discovery
    print("PHASE 1: Discovery (SERP & PAA)...")
    serp_agent = SerpAgent()
    serp_agent.run()
    
    paa_agent = PaaAgent()
    paa_agent.run()

    # Phase 2: Content Collection
    print("PHASE 2: Content Collection (Crawl)...")
    crawl_agent = CrawlAgent()
    crawl_agent.run()

    # Phase 3: Semantic Processing
    print("PHASE 3: Semantic Processing (Embeddings & Clustering)...")
    embedding_agent = EmbeddingAgent()
    embedding_agent.run()
    
    cluster_agent = ClusterAgent()
    cluster_agent.run()

    # Phase 4: Topic Definition
    print("PHASE 4: Topic Definition (Topic Reasoning)...")
    topic_agent = TopicAgent()
    topic_agent.run()

    # Phase 5: Strategy Generation
    print("PHASE 5: Strategy Generation...")
    strategy_agent = StrategyAgent()
    strategy_agent.run()

    print("Pipeline execution complete.")

if __name__ == "__main__":
    run_pipeline()
