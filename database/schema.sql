-- ContentOG Database Schema
-- Based on requirements.md and antigravity_bootstrap.md

-- Enable vector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Keywords Table
CREATE TABLE IF NOT EXISTS keywords (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    keyword TEXT NOT NULL UNIQUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Articles Table
CREATE TABLE IF NOT EXISTS articles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    url TEXT NOT NULL UNIQUE,
    title TEXT,
    content TEXT,
    serp_keyword TEXT,
    serp_rank INTEGER,
    publish_date TIMESTAMP WITH TIME ZONE,
    word_count INTEGER,
    embedding vector(1536), -- Defaulting to 1536 for OpenAI embeddings, can be adjusted
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Safe migration path for existing databases
ALTER TABLE IF EXISTS articles
    ADD COLUMN IF NOT EXISTS serp_keyword TEXT;

ALTER TABLE IF EXISTS articles
    ADD COLUMN IF NOT EXISTS serp_rank INTEGER;

-- PAA Questions Table
CREATE TABLE IF NOT EXISTS paa_questions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    keyword_id UUID REFERENCES keywords(id),
    question TEXT NOT NULL UNIQUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Topics Table
CREATE TABLE IF NOT EXISTS topics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Article-Topics Mapping Table
CREATE TABLE IF NOT EXISTS article_topics (
    article_id UUID REFERENCES articles(id),
    topic_id UUID REFERENCES topics(id),
    relevance_score FLOAT,
    PRIMARY KEY (article_id, topic_id)
);

-- Pillar Strategies Table
CREATE TABLE IF NOT EXISTS pillar_strategies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    topic_id UUID REFERENCES topics(id),
    strategy_details JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Cluster Articles (Analysis Results)
CREATE TABLE IF NOT EXISTS cluster_articles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cluster_id TEXT NOT NULL,
    article_id UUID REFERENCES articles(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for performance and idempotency
CREATE INDEX IF NOT EXISTS idx_articles_url ON articles(url);
CREATE INDEX IF NOT EXISTS idx_keywords_keyword ON keywords(keyword);
CREATE INDEX IF NOT EXISTS idx_paa_questions_question ON paa_questions(question);
CREATE INDEX IF NOT EXISTS idx_topics_name ON topics(name);
CREATE UNIQUE INDEX IF NOT EXISTS idx_cluster_articles_cluster_article ON cluster_articles(cluster_id, article_id);
