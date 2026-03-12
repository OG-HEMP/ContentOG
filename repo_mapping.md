# Repository Mapping

Defines how system capabilities map to external repositories.

------------------------------------------------------------------------

## Skill → Repository Mapping

SERP Discovery Custom lightweight module using requests or SERP API

Web Crawling Firecrawl

Content Embeddings sentence-transformers

Topic Clustering HDBSCAN

NLP Extraction spaCy

Topic Reasoning LLM via CrewAI orchestration

Strategy Generation LLM via CrewAI orchestration

Graph Utilities (optional) NetworkX

------------------------------------------------------------------------

## Agent → Repository Dependencies

SERP Discovery Agent uses custom SERP module

PAA Agent uses SERP module

Crawl Agent uses Firecrawl

Embedding Agent uses sentence-transformers

Cluster Agent uses HDBSCAN

Topic Agent uses spaCy + LLM

Strategy Agent uses LLM via CrewAI

Visualization Layer uses NetworkX

------------------------------------------------------------------------

## Directory Layout After Import

repos/ firecrawl/ sentence-transformers/ hdbscan/ spacy/ crewai/
networkx/

skills/ serp_discovery/ crawling/ embeddings/ clustering/ nlp/
reasoning/ strategy/

agents/ serp_agent/ crawl_agent/ embedding_agent/ cluster_agent/
topic_agent/ strategy_agent/

------------------------------------------------------------------------

## Expected Outcome

Antigravity must automatically connect:

skills → repos agents → skills workflow → agents
