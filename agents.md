# Agents

Agents perform tasks using system skills.

------------------------------------------------------------------------

## SERP Discovery Agent

Purpose Discover URLs ranking for seed keywords.

Skills SERP Discovery

Outputs articles.url

------------------------------------------------------------------------

## PAA Agent

Purpose Extract People Also Ask questions.

Skills People Also Ask Extraction

Outputs paa_questions

------------------------------------------------------------------------

## Crawl Agent

Purpose Download and extract article content.

Skills Web Crawling

Outputs articles table updates

------------------------------------------------------------------------

## Embedding Agent

Purpose Generate embeddings for articles and keywords.

Skills Content Embedding

Outputs embedding vectors

------------------------------------------------------------------------

## Cluster Agent

Purpose Detect topic clusters from article embeddings.

Skills Topic Clustering

Outputs cluster groups

------------------------------------------------------------------------

## Topic Agent

Purpose Convert clusters into semantic topics.

Skills Topic Reasoning

Outputs topics table article_topics mapping

------------------------------------------------------------------------

## Strategy Agent

Purpose Generate content strategy insights.

Skills Strategy Generation

Outputs pillar_strategies cluster_articles
