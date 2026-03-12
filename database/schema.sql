-- ContentOG Database Schema
-- Based on requirements.md and antigravity_bootstrap.md

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

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

-- Topic relationships (knowledge graph edges)
CREATE TABLE IF NOT EXISTS topic_relationships (
    id BIGSERIAL PRIMARY KEY,
    topic_id UUID REFERENCES topics(id),
    related_topic_id UUID REFERENCES topics(id),
    weight FLOAT,
    relationship_type TEXT
);

-- Topic coverage by domain
CREATE TABLE IF NOT EXISTS topic_domain_coverage (
    topic_id UUID REFERENCES topics(id),
    domain TEXT,
    article_count INT,
    avg_rank FLOAT,
    PRIMARY KEY (topic_id, domain)
);

-- Indexes for performance and idempotency
CREATE INDEX IF NOT EXISTS idx_articles_url ON articles(url);
CREATE INDEX IF NOT EXISTS idx_keywords_keyword ON keywords(keyword);
CREATE INDEX IF NOT EXISTS idx_paa_questions_question ON paa_questions(question);
CREATE INDEX IF NOT EXISTS idx_topics_name ON topics(name);
CREATE UNIQUE INDEX IF NOT EXISTS idx_cluster_articles_cluster_article ON cluster_articles(cluster_id, article_id);
<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
CREATE UNIQUE INDEX IF NOT EXISTS idx_topic_relationship_unique
    ON topic_relationships(topic_id, related_topic_id, relationship_type);
CREATE INDEX IF NOT EXISTS idx_topic_relationship_topic
    ON topic_relationships(topic_id);
CREATE INDEX IF NOT EXISTS idx_topic_relationship_related
    ON topic_relationships(related_topic_id);
CREATE INDEX IF NOT EXISTS idx_topic_coverage_domain
    ON topic_domain_coverage(domain);
=======
=======
>>>>>>> theirs
=======
>>>>>>> theirs
=======
>>>>>>> theirs
=======
>>>>>>> theirs
=======
>>>>>>> theirs
=======
>>>>>>> theirs

-- Pipeline run tracking
CREATE TABLE IF NOT EXISTS runs (
    id SERIAL PRIMARY KEY,
    started_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,
    status TEXT,
    keyword_count INT DEFAULT 0,
    article_count INT DEFAULT 0,
    cluster_count INT DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_runs_started_at
ON runs(started_at);

CREATE TABLE IF NOT EXISTS clusters (
    id SERIAL PRIMARY KEY,
    run_id INT REFERENCES runs(id),
    cluster_label TEXT,
    cluster_size INT,
    coherence_score FLOAT,
    cluster_signature TEXT
);

CREATE INDEX IF NOT EXISTS idx_clusters_run
ON clusters(run_id);

CREATE TABLE IF NOT EXISTS pipeline_metrics (
    id SERIAL PRIMARY KEY,
    run_id INT REFERENCES runs(id),
    serp_results INT,
    pages_crawled INT,
    valid_articles INT,
    embeddings_generated INT,
    clusters_generated INT,
    topics_generated INT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_pipeline_metrics_run
ON pipeline_metrics(run_id);

-- Topic graph + coverage tables used by strategy/reporting endpoints
CREATE TABLE IF NOT EXISTS topic_relationships (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_topic_id UUID REFERENCES topics(id),
    target_topic_id UUID REFERENCES topics(id),
    relationship_type TEXT,
    weight FLOAT DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE (source_topic_id, target_topic_id, relationship_type)
);

CREATE INDEX IF NOT EXISTS idx_topic_relationships_source
ON topic_relationships(source_topic_id);

CREATE INDEX IF NOT EXISTS idx_topic_relationships_target
ON topic_relationships(target_topic_id);

CREATE TABLE IF NOT EXISTS topic_domain_coverage (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    topic_id UUID REFERENCES topics(id),
    domain TEXT NOT NULL,
    coverage_count INT DEFAULT 0,
    coverage_score FLOAT DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE (topic_id, domain)
);

CREATE INDEX IF NOT EXISTS idx_topic_domain_coverage_topic
ON topic_domain_coverage(topic_id);
<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
>>>>>>> theirs
=======
>>>>>>> theirs
=======
>>>>>>> theirs
=======
>>>>>>> theirs
=======
>>>>>>> theirs
=======
>>>>>>> theirs
=======
>>>>>>> theirs
