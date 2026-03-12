# Antigravity Bootstrap Specification

Initialize the SEO intelligence project.

------------------------------------------------------------------------

# Project Root

ai-seo-intelligence

------------------------------------------------------------------------

# Directory Structure

config/ database/ agents/ skills/ workflows/ crawler/ embeddings/
clustering/ analysis/ strategy/ scripts/ visualization/ data/

------------------------------------------------------------------------

# Control Files

requirements.md skills.md agents.md workflow.md

------------------------------------------------------------------------

# Database Initialization

Enable vector extension.

create extension if not exists vector;

------------------------------------------------------------------------

# Tables

articles keywords paa_questions topics article_topics pillar_strategies
cluster_articles

------------------------------------------------------------------------

# Execution Order

SERP discovery → PAA extraction → crawl → embeddings → clustering →
topic reasoning → strategy generation

------------------------------------------------------------------------

# Initial Task

Insert 20 seed keywords into keywords table.

------------------------------------------------------------------------

# Expected Result

Antigravity must create:

• folder structure • database schema • agent scaffolding • workflow
runner
