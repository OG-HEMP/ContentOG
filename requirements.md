# System Requirements

## Objective

Build an automated SEO intelligence system that analyzes an industry's
content landscape and generates:

• industry topic map • content gap analysis • pillar page opportunities
• cluster article roadmap • SEO content briefs

The system focuses on **content strategy generation**, not article
writing.

------------------------------------------------------------------------

# Core Data Sources

The system collects data from three discovery signals:

1.  Search Engine Results (SERP pages)
2.  People Also Ask questions (PAA)
3.  Target and competitor blog content

------------------------------------------------------------------------

# Discovery Pipeline

seed keywords → SERP discovery → People Also Ask extraction → crawl
pages → generate embeddings → SERP-aligned clustering → LLM topic
reasoning → topic coverage analysis → strategy generation

------------------------------------------------------------------------

# Key Outputs

The system must generate:

1.  Industry topic graph
2.  Topic coverage by domain
3.  Pillar page opportunities
4.  Cluster article ideas
5.  SEO content briefs

------------------------------------------------------------------------

# Database Tables

articles keywords paa_questions topics article_topics pillar_strategies
cluster_articles

------------------------------------------------------------------------

# System Agents

SERP Discovery Agent Crawl Agent Embedding Agent Cluster Agent Topic
Agent Strategy Agent

------------------------------------------------------------------------

# Execution Order

SERP discovery → PAA extraction → crawl pages → embeddings → clustering
→ topic reasoning → strategy generation
