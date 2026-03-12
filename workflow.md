# Workflow

Defines the execution order for the system.

------------------------------------------------------------------------

## Phase 1 Discovery

SERP Discovery Agent PAA Agent

Purpose Collect search intent and ranking pages.

------------------------------------------------------------------------

## Phase 2 Content Collection

Crawl Agent

Purpose Retrieve article content.

------------------------------------------------------------------------

## Phase 3 Semantic Processing

Embedding Agent Cluster Agent

Purpose Generate embeddings and detect clusters.

------------------------------------------------------------------------

## Phase 4 Topic Definition

Topic Agent

Purpose Convert clusters into topics.

------------------------------------------------------------------------

## Phase 5 Strategy Generation

Strategy Agent

Purpose Produce pillar opportunities and cluster content roadmap.

------------------------------------------------------------------------

## Scheduling

Industry crawl: monthly Competitor crawl: weekly Site crawl: weekly

------------------------------------------------------------------------

## Idempotency

Agents must avoid duplicate inserts.

Check before insert:

URL exists question exists topic exists
