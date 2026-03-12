# Antigravity Repo Import Specification

Purpose: This file instructs Antigravity to import and integrate
external repositories required by the system skills.

Antigravity must clone the following repositories into the project
directory:

repos/

------------------------------------------------------------------------

## Repositories to Import

Firecrawl https://github.com/firecrawl/firecrawl

sentence-transformers https://github.com/UKPLab/sentence-transformers

HDBSCAN https://github.com/scikit-learn-contrib/hdbscan

spaCy https://github.com/explosion/spaCy

CrewAI https://github.com/joaomdmoura/crewAI

NetworkX (optional for visualization)
https://github.com/networkx/networkx

------------------------------------------------------------------------

## Import Rules

1.  Clone repositories into:

repos/

2.  Do NOT modify upstream repository code.

3.  Create wrapper modules inside:

skills/

4.  Agents must call wrappers instead of directly calling repository
    code.

5.  Automatically install dependencies required by imported
    repositories.

------------------------------------------------------------------------

## Example Wrapper

skills/embeddings/embedding_service.py

Expose:

generate_embeddings(text)

Internally call sentence-transformers model.

------------------------------------------------------------------------

## Final Goal

Repositories must provide functionality for:

web crawling text embeddings topic clustering nlp extraction agent
orchestration graph utilities
