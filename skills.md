# Skills

Skills represent reusable capabilities used by agents.

------------------------------------------------------------------------

## SERP Discovery

Retrieve top search results for a keyword.

Inputs keyword

Outputs list of URLs

------------------------------------------------------------------------

## People Also Ask Extraction

Extract related questions from Google SERP.

Inputs keyword

Outputs list of questions

------------------------------------------------------------------------

## Web Crawling

Download webpage and extract article content.

Inputs URL

Outputs title content publish date word count

Tool Firecrawl

------------------------------------------------------------------------

## Content Embedding

Convert text into semantic vectors.

Inputs article text keyword text

Outputs embedding vector

Tool sentence-transformers

------------------------------------------------------------------------

## Topic Clustering

Detect semantic clusters in embedding space.

Inputs article embeddings SERP keyword tags

Outputs cluster groups

Tool HDBSCAN

------------------------------------------------------------------------

## Topic Reasoning

Interpret clusters and define topics.

Inputs cluster articles keywords PAA questions

Outputs topic name topic description

Tool LLM

------------------------------------------------------------------------

## Strategy Generation

Generate SEO strategy recommendations.

Inputs topics coverage data keyword demand PAA questions

Outputs pillar pages cluster topics content briefs
