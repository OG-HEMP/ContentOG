-- ContentOG Database Schema
-- Ground Truth aligned with Supabase production schema

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Keywords Table
CREATE TABLE IF NOT EXISTS keywords (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    keyword TEXT NOT NULL UNIQUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    embedding vector(1536)
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
    embedding vector(1536),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

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
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
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

-- Topic Relationships (Similarity Graph)
CREATE TABLE IF NOT EXISTS topic_relationships (
    id BIGSERIAL PRIMARY KEY,
    topic_id UUID REFERENCES topics(id),
    related_topic_id UUID REFERENCES topics(id),
    weight FLOAT,
    relationship_type TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Topic Domain Coverage
CREATE TABLE IF NOT EXISTS topic_domain_coverage (
    topic_id UUID REFERENCES topics(id),
    domain TEXT,
    article_count INT,
    avg_rank FLOAT,
    PRIMARY KEY (topic_id, domain),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Pipeline Run Tracking
CREATE TABLE IF NOT EXISTS runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    mode TEXT NOT NULL,
    status TEXT DEFAULT 'running',
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    keyword_count INT DEFAULT 0,
    article_count INT DEFAULT 0,
    cluster_count INT DEFAULT 0,
    error_summary TEXT,
    target_domain TEXT,
    metadata JSONB
);

-- Individual Keyword Task Tracking
CREATE TABLE IF NOT EXISTS keyword_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID REFERENCES runs(id),
    keyword TEXT NOT NULL,
    status TEXT DEFAULT 'pending',
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    retry_count INT DEFAULT 0,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Performance Indexes
CREATE INDEX IF NOT EXISTS idx_articles_url ON articles(url);
CREATE INDEX IF NOT EXISTS idx_keywords_keyword ON keywords(keyword);
CREATE INDEX IF NOT EXISTS idx_paa_questions_question ON paa_questions(question);
CREATE INDEX IF NOT EXISTS idx_topics_name ON topics(name);
CREATE UNIQUE INDEX IF NOT EXISTS idx_cluster_articles_cluster_article ON cluster_articles(cluster_id, article_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_topic_relationship_unique ON topic_relationships(topic_id, related_topic_id, relationship_type);
CREATE INDEX IF NOT EXISTS idx_topic_relationship_topic ON topic_relationships(topic_id);
CREATE INDEX IF NOT EXISTS idx_topic_coverage_domain ON topic_domain_coverage(domain);
